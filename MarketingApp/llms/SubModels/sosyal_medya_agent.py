"""
Sosyal Medya Agent SubModel — X (Twitter), Instagram ve YouTube otomasyon uzmani.

OpenAI-compatible endpoint uzerinde tool-calling ile calisir.
Tum sosyal medya gorevlerini (post yayinlama, yorum, begeni, takip,
bildirim tarama, piyasa analizi vb.) tek merkezden yonetir.
"""

from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from .base import SubModel, SubModelRateLimitError, register_submodel
from MarketingApp.araclar import SOSYAL_MEDYA_ARACLARI
from MarketingApp.llms.runtime_config import (
    get_base_model_name,
    get_base_reasoning_effort,
    get_model_api_key,
    get_openai_compat_base_url,
    get_provider_display_name,
)


class SosyalMedyaAgentSubModel(SubModel):
    """X (Twitter), Instagram ve YouTube uzerinde icerik uretimi, etkilesim ve analiz uzmani."""

    def __init__(self):
        api_key = get_model_api_key()
        self.provider_name = get_provider_display_name()
        self.reasoning_effort = get_base_reasoning_effort()
        if not api_key:
            print(f"⚠️  UYARI: {self.provider_name} API anahtari bulunamadi!")

        super(SosyalMedyaAgentSubModel, self).__init__(
            name="sosyal_medya_agent",
            description=(
                "X (Twitter), Instagram ve YouTube uzerinde sosyal medya otomasyon uzmani. "
                "Post yayinlama, thread olusturma, yorum yapma, begeni/takip, bildirim tarama, "
                "piyasa snapshot'i alma, trend analizi, profil/post inceleme gibi tum sosyal medya "
                "gorevleri icin bu ajani kullan. Kripto, DeFi, NFT, blockchain icerik uretimi "
                "ve topluluk yonetimi konularinda uzmandir."
            ),
            model_id=get_base_model_name(),
            api_key=api_key,
            tools=SOSYAL_MEDYA_ARACLARI,
        )
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=get_openai_compat_base_url(),
        )

    def _strip_thought_blocks(self, text: str) -> str:
        return re.sub(
            r"<thought>.*?</thought>", "", text or "", flags=re.DOTALL | re.IGNORECASE
        ).strip()

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
            combined = "\n".join(
                part.strip() for part in texts if part and part.strip()
            ).strip()
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

            function_payload = call_payload.get("function") or {}
            function_payload["name"] = (
                function_payload.get("name") or call.function.name
            )
            function_payload["arguments"] = (
                function_payload.get("arguments")
                or call.function.arguments
                or "{}"
            )
            call_payload["function"] = function_payload
            call_payload["id"] = call_payload.get("id") or call.id
            call_payload["type"] = call_payload.get("type") or "function"
            tool_calls.append(call_payload)
        if tool_calls:
            payload["tool_calls"] = tool_calls
        return payload

    def _parse_tool_args(self, raw_args) -> dict:
        if isinstance(raw_args, dict):
            return raw_args
        if not raw_args:
            return {}
        try:
            return json.loads(raw_args)
        except Exception:
            return {}

    async def run(self, gorev: str) -> str:
        print(f"\n📱 [{self.name}] Sosyal medya gorevi baslatiliyor: {gorev[:120]}...")

        from MarketingApp.araclar import rol_oku

        aktif_rol = rol_oku()

        system_prompt = (
            "Sen bir sosyal medya otomasyon uzmansin. X (Twitter), Instagram ve YouTube "
            "platformlarinda icerik uretimi, etkilesim ve analiz gorevlerini yonetirsin.\n\n"
            "CALISMA PRENSIPLERI:\n"
            "1. Once gorev tanimimdaki tum talimatlari dikkatlice oku.\n"
            "2. Gerekli bilgileri toplamak icin uygun araclari kullan "
            "(snapshot_x_feed, get_x_queue, scan_x_notifications vb.).\n"
            "3. Icerik uretirken:\n"
            "   - Her post/yorum tek bir ana fikir tasisin.\n"
            "   - Maksimum 240 karakter sinirini asma.\n"
            "   - Ayni kalibi veya aciyi tekrarlama.\n"
            "   - Spam, manipulatif dil veya bos icerik uretme.\n"
            "4. Aksiyon adimlarini sirayla yap; once durumu oku, sonra karar ver, sonra uygula.\n"
            "5. Her basarili aksiyondan sonra log kaydini workspace dosyalarina yaz "
            "(social/automation_log.md, social/recent_actions.md).\n"
            "6. Basarisiz bir islem olursa hata mesajini raporla, gereksiz tekrarlardan kacin.\n"
            "7. X tarayicisi acik degilse once `launch_x_browser()` veya `launch_social_browser()` cagir.\n"
            "8. Tarayici durumunu `get_browser_status()` ile kontrol edebilirsin.\n"
            "9. Gorev tamamlandiginda kisa ve net bir Turkce ozet ver.\n"
        )

        if not aktif_rol.startswith("⚠️") and not aktif_rol.startswith("❌"):
            system_prompt += (
                "\n=========== MARKETING KISILIGI (ZORUNLU) ===========\n"
                f"{aktif_rol}\n"
                "===================================================\n"
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": gorev},
        ]
        final_response = "Tamamlandi"

        try:
            for _ in range(16):
                create_kwargs = {
                    "model": self.model_id,
                    "messages": messages,
                    "tools": self._build_tool_schemas(),
                    "tool_choice": "auto",
                }
                if self.reasoning_effort:
                    create_kwargs["reasoning_effort"] = self.reasoning_effort

                completion = await self._client.chat.completions.create(
                    **create_kwargs
                )
                message = completion.choices[0].message
                current_text = self._extract_message_text(message)
                tool_calls = getattr(message, "tool_calls", None) or []

                if tool_calls:
                    messages.append(self._assistant_message_payload(message))
                    if current_text:
                        final_response = current_text

                    for call in tool_calls:
                        args = self._parse_tool_args(call.function.arguments)
                        result = await self._execute_tool(
                            call.function.name, args
                        )
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "name": call.function.name,
                                "content": json.dumps(
                                    {"result": str(result)[:6000]},
                                    ensure_ascii=False,
                                ),
                            }
                        )
                    continue

                if current_text:
                    final_response = current_text
                break

        except Exception as e:
            err = str(e)
            if "429" in err or "quota" in err.lower() or "limit" in err.lower():
                print(
                    f"  ⚠️ [{self.name}] {self.provider_name} limit hatasi! BaseModel'e devrediliyor."
                )
                raise SubModelRateLimitError(self.name, self.tools)
            print(f"  ❌ [{self.name}] API Hatasi: {e}")
            return f"Sosyal Medya Agent Hatasi: {e}"

        print(f"  ✅ [{self.name}] Gorev tamamlandi.")
        return final_response


register_submodel(SosyalMedyaAgentSubModel())
