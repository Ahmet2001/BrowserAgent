"""
BaseModel — ana orkestrator + browser_agent komutani.

Bu surum OpenAI-compatible chat completion + tool calling akisiyla
Gemini veya Moonshot/Kimi gibi saglayicilari kullanir.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
import time

import speech_recognition as sr
from openai import AsyncOpenAI, RateLimitError

from .SubModels import SubModelRateLimitError, get_all_submodels
from .runtime_config import (
    get_base_model_name,
    get_base_reasoning_effort,
    get_model_api_key,
    get_openai_compat_base_url,
    get_provider_display_name,
)
from MarketingApp.araclar import BASE_ARACLAR, BROWSER_ARACLARI


INPUT_RATE = 16000
SAMPLE_WIDTH = 2
CHANNELS = 1
PROVIDER_FAILURE_COOLDOWN_SECONDS = 10
DEFAULT_TOOL_TIMEOUT_SECONDS = 150.0

SYSTEM_INSTRUCTION = """
Sen "Mimar" projesinin merkezi orkestratorusun.

CALISMA KURALLARI:
1. X (Twitter), Instagram ve YouTube ile ilgili TUM sosyal medya gorevlerini `sosyal_medya_agent` alt ajanina devret. Bu ajan post yayinlama, yorum, begeni, takip, bildirim tarama, piyasa analizi, trend kontrolu ve icerik uretimi gibi tum sosyal medya islemlerini yonetir.
2. Basit dosya ve workspace islemlerinde (okuma, yazma, listeleme) base tool'lari dogrudan kullan.
3. Uzun icerikleri sesli yanit gibi dusunme; metni `metinle_cevapla` veya `ekrana_yazdir` ile ilet.
4. Karmasik gorevlerde adim adim ilerle, gereksiz ajan cagrisi yapma.
5. Yanitlarini Turkce ver.
"""


def _process_stt(audio_data_bytes: bytes, recognizer: sr.Recognizer, rate: int = INPUT_RATE) -> str | None:
    audio_data = sr.AudioData(audio_data_bytes, rate, SAMPLE_WIDTH)
    try:
        return recognizer.recognize_google(audio_data, language="tr-TR")
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"\n[STT API Hatasi]: {e}")
        return None


class BaseModel:
    """OpenAI-compatible bir saglayici uzerinde calisan ana orchestrator."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or get_model_api_key()
        self.model = model or get_base_model_name()
        self.reasoning_effort = get_base_reasoning_effort()
        self.provider_name = get_provider_display_name()
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=get_openai_compat_base_url(),
        )
        self._current_image = None

        _allowed = {"sosyal_medya_agent"}
        if BROWSER_ARACLARI:
            _allowed.add("browser_agent")
        submodels = [sm for sm in get_all_submodels() if sm.name in _allowed]
        self.submodels = submodels
        self._submodel_funcs, self._submodel_func_map = self._build_submodel_functions(submodels)

        self.active_agents = {sm.name: True for sm in submodels}
        self.active_tools = {}
        self.logs = []
        self.metrics = []
        self.pending_actions = {}
        self.start_time = time.time()
        self._provider_blocked_until = 0.0
        self._provider_block_message = ""

        from MarketingApp.araclar import (
            ARAMA_ARACLARI,
            KOD_ARACLARI,
            SISTEM_ARACLARI,
            VLM_ARACLARI,
        )

        all_tool_lists = [BASE_ARACLAR, SISTEM_ARACLARI, ARAMA_ARACLARI, KOD_ARACLARI, VLM_ARACLARI, BROWSER_ARACLARI]
        for tool_list in all_tool_lists:
            for func in tool_list:
                self.active_tools[func.__name__] = True

        for func in self._submodel_func_map.values():
            self.active_tools[func.__name__] = True

        print(f"🧠 BaseModel başlatıldı: {self.model}")
        print(f"   Sağlayıcı: {self.provider_name}")
        if self.reasoning_effort:
            print(f"   Reasoning effort: {self.reasoning_effort}")
        print(f"   SubModel tool'ları: {[f.__name__ for f in self._submodel_funcs]}")

    def _strip_thought_blocks(self, text: str) -> str:
        cleaned = re.sub(r"<thought>.*?</thought>", "", text or "", flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()

    def _is_provider_quota_error(self, exc: Exception) -> bool:
        if isinstance(exc, RateLimitError):
            return True

        err = str(exc).lower()
        quota_markers = (
            "insufficient balance",
            "exceeded_current_quota",
            "quota",
            "rate limit",
            "429",
        )
        return any(marker in err for marker in quota_markers)

    def _format_provider_quota_message(self) -> str:
        return (
            f"⚠️ {self.provider_name} API şu anda kullanılamıyor. Kota, plan veya faturalama "
            "sınırına takılmış olabilir. Sağlayıcı hesabını ve API anahtarını kontrol edin."
        )

    def _is_thought_signature_error(self, exc: Exception) -> bool:
        err = str(exc).lower()
        return "thought_signature" in err or "missing a thought signature" in err

    def _format_thought_signature_message(self) -> str:
        return (
            "⚠️ Gemini tool-calling oturum imzasi eslesemedi. Uygulamayi yeniden baslatip "
            "istegi tekrar deneyin. Sorun surerse ayni oturumdaki eski model yanitlarini temizlemek gerekebilir."
        )

    def _mark_provider_temporarily_unavailable(self, exc: Exception):
        self._provider_blocked_until = time.time() + PROVIDER_FAILURE_COOLDOWN_SECONDS
        self._provider_block_message = self._format_provider_quota_message()
        self.log_message("sistem", f"Model sağlayıcı kota hatası: {exc}")

    def _get_provider_unavailable_message(self) -> str | None:
        remaining = self._provider_blocked_until - time.time()
        if remaining <= 0:
            return None
        if remaining < 60:
            remaining_text = f"yaklaşık {max(1, int(remaining + 0.999))} saniye"
        else:
            remaining_minutes = max(1, int((remaining + 59) // 60))
            remaining_text = f"yaklaşık {remaining_minutes} dakika"

        return (
            f"{self._provider_block_message} Sistem gereksiz tekrar denemeleri azaltmak için "
            f"{remaining_text} boyunca hızlıca bu uyarıyı dönecek."
        )

    def _build_submodel_functions(self, submodels):
        submodel_funcs = []
        submodel_func_map = {}

        for sm in submodels:
            def make_runner(submodel):
                async def runner(gorev: str) -> str:
                    try:
                        return await submodel.run(gorev)
                    except SubModelRateLimitError as e:
                        return f"[SISTEM_MESAJI_GIZLI] {e.submodel_name} rate limit verdi."
                    except Exception as e:
                        return f"[SISTEM_MESAJI_GIZLI] {submodel.name} hatasi: {e}"

                runner.__name__ = submodel.name
                runner.__doc__ = submodel.description + "\n\nArgs:\n    gorev: Bu ajana verilecek gorev aciklamasi."
                return runner

            func = make_runner(sm)
            submodel_funcs.append(func)
            submodel_func_map[sm.name] = func

        return submodel_funcs, submodel_func_map

    def _build_all_tools(self) -> list:
        def ekrana_yazdir(metin: str) -> str:
            """Uzun icerigi kullanici ekranina dogrudan iletir."""
            return "Metin basariyla kullanicinin ekranina gonderildi."

        def metinle_cevapla(cevap: str) -> str:
            """Kullaniciya metin yaniti gonderir."""
            return "Cevap basariyla metin olarak gonderildi."

        tools = [ekrana_yazdir, metinle_cevapla]
        for func in BASE_ARACLAR:
            if self.active_tools.get(func.__name__, True):
                tools.append(func)
        for func in self._submodel_funcs:
            if self.active_agents.get(func.__name__, True) and self.active_tools.get(func.__name__, True):
                tools.append(func)
        return tools

    def _build_full_tool_map(self) -> dict:
        full_map = {func.__name__: func for func in BASE_ARACLAR}
        full_map.update(self._submodel_func_map)
        return full_map

    def _schema_for_callable(self, func) -> dict:
        sig = inspect.signature(func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            annotation = param.annotation
            param_type = "string"
            if annotation == int:
                param_type = "integer"
            elif annotation == float:
                param_type = "number"
            elif annotation == bool:
                param_type = "boolean"

            properties[param_name] = {"type": param_type}
            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": ((func.__doc__ or "").strip() or f"{func.__name__} aracini cagir"),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def _build_tool_schemas(self) -> list[dict]:
        return [self._schema_for_callable(func) for func in self._build_all_tools()]

    def _get_tool_timeout_seconds(self, name: str):
        # Browser agent uzun cok-adimli gorevlerde sure sinirina takilmasin.
        if name == "browser_agent":
            return None
        return DEFAULT_TOOL_TIMEOUT_SECONDS

    def get_hierarchy(self) -> dict:
        from MarketingApp.araclar import BASE_ARACLAR, BROWSER_ARACLARI

        def tool_info(func_list):
            return [{
                "name": func.__name__,
                "desc": func.__doc__.split("\n")[0] if func.__doc__ else "",
                "active": self.active_tools.get(func.__name__, True),
            } for func in func_list]

        hierarchy = {
            "name": "BaseModel",
            "active": True,
            "tools": tool_info(BASE_ARACLAR),
            "submodels": [],
        }

        for sm in self.submodels:
            hierarchy["submodels"].append({
                "name": sm.name,
                "active": self.active_agents.get(sm.name, True),
                "tools": tool_info(BROWSER_ARACLARI if sm.name == "browser_agent" else []),
            })

        return hierarchy

    def log_message(self, type: str, message: str):
        t = time.strftime("%H:%M:%S")
        log_entry = {"time": t, "type": type, "message": message}
        self.logs.append(log_entry)
        if len(self.logs) > 100:
            self.logs.pop(0)
        print(f"[{t}] [{type.upper()}] {message}")

    async def request_approval(self, action_id: str, description: str):
        ev = asyncio.Event()
        self.pending_actions[action_id] = {
            "description": description,
            "event": ev,
            "status": "pending",
        }
        self.log_message("sistem", f"ONAY GEREKLI: {description}")

        try:
            await asyncio.wait_for(ev.wait(), timeout=300.0)
            status = self.pending_actions[action_id]["status"]
            del self.pending_actions[action_id]
            return status == "approved"
        except asyncio.TimeoutError:
            self.log_message("sistem", f"Zaman Asimi: {action_id} onay alinamadigi icin reddedildi.")
            if action_id in self.pending_actions:
                del self.pending_actions[action_id]
            return False

    def _parse_tool_args(self, arguments) -> dict:
        if isinstance(arguments, dict):
            return arguments
        if not arguments:
            return {}
        try:
            return json.loads(arguments)
        except Exception:
            return {}

    def _extract_message_text(self, message) -> str:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return self._strip_thought_blocks(content)
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
                else:
                    maybe_text = getattr(item, "text", None)
                    if maybe_text:
                        texts.append(maybe_text)
            combined = "\n".join(part.strip() for part in texts if part and part.strip()).strip()
            return self._strip_thought_blocks(combined)
        return ""

    def _assistant_message_payload(self, message) -> dict:
        payload = {
            "role": "assistant",
            "content": self._extract_message_text(message),
        }
        tool_calls = []
        for call in getattr(message, "tool_calls", []) or []:
            if isinstance(call, dict):
                call_payload = dict(call)
            elif hasattr(call, "to_dict"):
                call_payload = call.to_dict()
            else:
                call_payload = {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments or "{}",
                    },
                }

            # Gemini OpenAI compatibility katmaninda function calling icin
            # tool_call.extra_content.google.thought_signature alanini oldugu
            # gibi geri dondurmek zorunludur.
            function_payload = call_payload.get("function") or {}
            function_payload["name"] = function_payload.get("name") or call.function.name
            function_payload["arguments"] = function_payload.get("arguments") or call.function.arguments or "{}"
            call_payload["function"] = function_payload
            call_payload["id"] = call_payload.get("id") or call.id
            call_payload["type"] = call_payload.get("type") or "function"
            tool_calls.append(call_payload)
        if tool_calls:
            payload["tool_calls"] = tool_calls
        return payload

    async def _execute_named_tool(self, name: str, args: dict, direct_texts: list, cevap_metinleri: list, on_direct_text=None, on_cevap_metni=None):
        if name == "ekrana_yazdir":
            metin = args.get("metin", "")
            if metin:
                direct_texts.append(metin)
                print("📠 [Sistem Call]: Ekrana yazdiriliyor...")
                if on_direct_text:
                    await on_direct_text(metin)
            return "Basariyla ekrana gonderildi."

        if name == "metinle_cevapla":
            cevap = args.get("cevap", "")
            if cevap:
                cevap_metinleri.append(cevap)
                print(f"💬 [Cevap Call]: Metin yaniti alindi ({len(cevap)} karakter)")
                if on_cevap_metni:
                    await on_cevap_metni(cevap)
            return "Cevap metin olarak gonderildi."

        func = self._build_full_tool_map().get(name)
        if not func:
            return f"[Hata]: {name} adinda bir tool veya submodel bulunamadi."

        is_submodel = name in self._submodel_func_map
        emoji = "🤖" if is_submodel else "🔧"
        label = "submodel" if is_submodel else "tool"

        self.log_message(label, f"{name} cagriliyor... Argumanlar: {args}")
        start_time = time.time()
        start_offset = start_time - getattr(self, "_request_start_time", start_time)

        if on_direct_text:
            await on_direct_text(f"[+{start_offset:.1f}s] {emoji} {name} calistiriliyor...")

        try:
            if inspect.iscoroutinefunction(func):
                timeout_seconds = self._get_tool_timeout_seconds(name)
                if timeout_seconds is None:
                    result = await func(**args)
                else:
                    result = await asyncio.wait_for(func(**args), timeout=timeout_seconds)
            else:
                result = await asyncio.to_thread(func, **args)

            end_time = time.time()
            duration = end_time - start_time
            end_offset = end_time - getattr(self, "_request_start_time", end_time)

            if on_direct_text:
                await on_direct_text(f"[+{end_offset:.1f}s] ✅ {name} bitti ({duration:.1f}s)")

            self.log_message(label, f"{name} bitti ({duration:.1f}s)")
            self.metrics.append({"name": name, "duration": round(duration, 2), "time": time.strftime("%H:%M:%S")})
            if len(self.metrics) > 20:
                self.metrics.pop(0)
            return result
        except asyncio.TimeoutError:
            print(f"⌛ [Timeout]: {name} cok uzun surdugu icin kesildi!")
            timeout_seconds = self._get_tool_timeout_seconds(name) or DEFAULT_TOOL_TIMEOUT_SECONDS
            return f"[SISTEM_MESAJI_GIZLI] {name} araci veya ajani {int(timeout_seconds)}sn zaman asimina ugradi."
        except Exception as e:
            self.log_message(label, f"{name} hatasi: {e}")
            return f"[SISTEM_MESAJI_GIZLI] {name} hatasi: {e}"

    async def _run_chat_loop(self, messages: list[dict], on_direct_text=None, on_cevap_metni=None) -> tuple[bytes, str, list, list]:
        direct_texts = []
        cevap_metinleri = []
        tool_schemas = self._build_tool_schemas()
        self._request_start_time = time.time()
        final_text = ""

        blocked_message = self._get_provider_unavailable_message()
        if blocked_message:
            cevap_metinleri.append(blocked_message)
            if on_cevap_metni:
                await on_cevap_metni(blocked_message)
            return b"", blocked_message, direct_texts, cevap_metinleri

        for _ in range(12):
            try:
                create_kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "tools": tool_schemas,
                    "tool_choice": "auto",
                }
                if self.reasoning_effort:
                    create_kwargs["reasoning_effort"] = self.reasoning_effort

                completion = await self._client.chat.completions.create(
                    **create_kwargs,
                )
            except Exception as e:
                if self._is_thought_signature_error(e):
                    final_text = self._format_thought_signature_message()
                    self.log_message("sistem", f"Thought signature hatasi: {e}")
                    cevap_metinleri.append(final_text)
                    if on_cevap_metni:
                        await on_cevap_metni(final_text)
                    return b"", final_text, direct_texts, cevap_metinleri
                if self._is_provider_quota_error(e):
                    self._mark_provider_temporarily_unavailable(e)
                    final_text = self._get_provider_unavailable_message() or self._format_provider_quota_message()
                    cevap_metinleri.append(final_text)
                    if on_cevap_metni:
                        await on_cevap_metni(final_text)
                    return b"", final_text, direct_texts, cevap_metinleri
                raise

            message = completion.choices[0].message
            current_text = self._extract_message_text(message)
            tool_calls = getattr(message, "tool_calls", None) or []

            if tool_calls:
                messages.append(self._assistant_message_payload(message))
                if current_text:
                    final_text = current_text

                for call in tool_calls:
                    args = self._parse_tool_args(call.function.arguments)
                    result = await self._execute_named_tool(
                        call.function.name,
                        args,
                        direct_texts,
                        cevap_metinleri,
                        on_direct_text=on_direct_text,
                        on_cevap_metni=on_cevap_metni,
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.function.name,
                        "content": json.dumps({"result": str(result)[:4000]}, ensure_ascii=False),
                    })
                continue

            if current_text:
                final_text = current_text
                if not cevap_metinleri:
                    cevap_metinleri.append(current_text)
                    if on_cevap_metni:
                        await on_cevap_metni(current_text)
                return b"", final_text, direct_texts, cevap_metinleri

            break

        if cevap_metinleri:
            final_text = cevap_metinleri[-1]
        elif not final_text:
            final_text = "Yanıt üretilemedi."
            cevap_metinleri.append(final_text)
            if on_cevap_metni:
                await on_cevap_metni(final_text)

        return b"", final_text, direct_texts, cevap_metinleri

    async def text_query(self, user_text: str, context: str = "", image_bytes: bytes = None, on_direct_text=None, on_cevap_metni=None) -> tuple[bytes, str, list, list]:
        self._current_image = image_bytes
        try:
            from MarketingApp.araclar import rol_oku

            aktif_rol = rol_oku()
            system_instruction = SYSTEM_INSTRUCTION
            if not aktif_rol.startswith("⚠️") and not aktif_rol.startswith("❌"):
                system_instruction += (
                    "\n\n=========== SENIN MARKETING KISILIGIN (ZORUNLU) ===========\n"
                    f"{aktif_rol}\n"
                    "========================================================\n"
                )

            user_parts = []
            if context:
                user_parts.append(context)
            if image_bytes:
                user_parts.append("Kullanici bir gorsel de gonderdi; bu gecici metin modunda gorsel bytes modele iletilmiyor.")
            user_parts.append(user_text)

            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": "\n\n".join(part for part in user_parts if part)},
            ]
            return await self._run_chat_loop(messages, on_direct_text=on_direct_text, on_cevap_metni=on_cevap_metni)
        finally:
            self._current_image = None

    async def audio_query(self, pcm_audio: bytes, context: str = "", image_bytes: bytes = None, on_direct_text=None, on_cevap_metni=None) -> tuple[bytes, str, list, list]:
        recognizer = sr.Recognizer()
        user_text = await asyncio.to_thread(_process_stt, pcm_audio, recognizer, INPUT_RATE)
        if not user_text:
            user_text = "Kullanicinin sesli mesaji net cozumlenemedi. Uygun ve kisa bir aciklama ile tekrar istemesini soyle."

        _audio, transcript, direct_texts, cevap_metinleri = await self.text_query(
            user_text=user_text,
            context=context,
            image_bytes=image_bytes,
            on_direct_text=on_direct_text,
            on_cevap_metni=on_cevap_metni,
        )
        return b"", transcript, direct_texts, cevap_metinleri
