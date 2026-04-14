import json
import inspect
from abc import ABC, abstractmethod

class SubModelRateLimitError(Exception):
    """
    SubModel'in çağrısı sırasında (genellikle Groq API) rate limit,
    kota aşımı veya genel bağlantı hatası alındığında tetiklenir.
    BaseModel (Gemini) bu hatayı yakalayarak görevi bizzat kendisi sürdürür.
    """
    def __init__(self, submodel_name: str, tools: list):
        self.submodel_name = submodel_name
        self.tools = tools
        super().__init__(f"[{submodel_name}] API rate limitine veya kritik bır hataya takıldı.")


class SubModel(ABC):
    """
    Tüm SubModel'lerin uyması gereken soyut temel sınıf.
    Her SubModel bir 'mini ajan'dır — kendi tool'ları ve AI modeli vardır.
    """

    def __init__(self, name: str, description: str, model_id: str, api_key: str, tools: list = None):
        """
        Args:
            name: SubModel'in benzersiz adı (registry key).
            description: BaseModel'in bu SubModel'i ne zaman kullanacağını anlaması için açıklama.
            model_id: Kullanılacak AI modeli.
            api_key: API anahtarı.
            tools: Bu SubModel'in kullanabileceği fonksiyonların listesi.
        """
        self.name = name
        self.description = description
        self.model_id = model_id
        self.api_key = api_key
        self.tools = tools or []
        self._tool_map = {func.__name__: func for func in self.tools}

    @abstractmethod
    async def run(self, gorev: str) -> str:
        """
        Görevi alır, kendi AI modeli + tool'ları ile çalıştırır, sonucu döndürür.
        Tool-calling loop implementasyonu alt sınıflarda yapılır.

        Args:
            gorev: BaseModel'den gelen görev açıklaması.

        Returns:
            Görevin sonucu (metin).
        """
        ...

    def _build_tool_schemas(self) -> list[dict]:
        """Tool fonksiyonlarından JSON schema üretir (function calling için)."""
        schemas = []
        for func in self.tools:
            sig = inspect.signature(func)
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                # Parametre tipini al
                annotation = param.annotation
                param_type = "string"  # varsayılan
                if annotation == int:
                    param_type = "integer"
                elif annotation == float:
                    param_type = "number"
                elif annotation == bool:
                    param_type = "boolean"

                properties[param_name] = {"type": param_type}

                # Varsayılanı yok ise zorunlu
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)

            schema = {
                "type": "function",
                "function": {
                    "name": func.__name__,
                    "description": (func.__doc__ or "").strip(),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            }
            schemas.append(schema)

        return schemas

    async def _execute_tool(self, name: str, arguments: dict):
        """İsme göre tool'u çalıştırır (Bloklamadan/Non-blocking)."""
        func = self._tool_map.get(name)
        if func:
            safe_args = arguments if isinstance(arguments, dict) else {}
            print(f"  🔧 [{self.name}] Tool çağrısı: {name}({safe_args})")
            
            if inspect.iscoroutinefunction(func):
                result = await func(**safe_args)
            else:
                import asyncio
                result = await asyncio.to_thread(func, **safe_args)
                
            print(f"  ✅ [{self.name}] Sonuç: {str(result)[:200]}...")
            return result
        else:
            return f"[Hata]: {name} adında bir tool bulunamadı."

    def __repr__(self):
        tool_names = [f.__name__ for f in self.tools]
        return f"<SubModel name='{self.name}' model='{self.model_id}' tools={tool_names}>"


# ─── Global SubModel Registry ───────────────────────────────────────────────

_SUBMODEL_REGISTRY: dict[str, SubModel] = {}


def register_submodel(instance: SubModel):
    """Bir SubModel instance'ını registry'ye kaydeder."""
    _SUBMODEL_REGISTRY[instance.name] = instance
    print(f"  ✅ SubModel kaydedildi: {instance}")


def get_submodel(name: str) -> SubModel:
    """İsme göre kayıtlı SubModel'i döndürür."""
    if name not in _SUBMODEL_REGISTRY:
        available = ", ".join(_SUBMODEL_REGISTRY.keys()) or "(boş)"
        raise KeyError(
            f"'{name}' adında bir SubModel bulunamadı. "
            f"Kayıtlı modeller: {available}"
        )
    return _SUBMODEL_REGISTRY[name]


def list_submodels() -> dict[str, str]:
    """Kayıtlı tüm SubModel isimlerini ve açıklamalarını döndürür."""
    return {name: sm.description for name, sm in _SUBMODEL_REGISTRY.items()}


def get_all_submodels() -> list[SubModel]:
    """Kayıtlı tüm SubModel instance'larını döndürür."""
    return list(_SUBMODEL_REGISTRY.values())
