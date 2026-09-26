"""Terminal komutlari: /provider (provider/model degistirme) ve /memory (uzun vadeli bellek)."""

import _env  # noqa: F401  (her seyden once)

import os
import unittest
from unittest import mock

import _support as S
from _support import Term


def studio():
    from MarketingApp.llms import agent_studio

    return agent_studio


def bellek():
    from MarketingApp.araclar import bellek_araclari

    return bellek_araclari


def agent_entry(name):
    return next((a for a in studio().load_agents_config()["agents"] if a["name"] == name), None)


_PROVIDER_ENV_KEYS = (
    "MODEL_PROVIDER", "BASE_MODEL_NAME", "SUBMODEL_MODEL_NAME",
    "BROWSER_AGENT_MODEL", "OPENAI_COMPAT_BASE_URL", "GEMINI_API_KEY", "MOONSHOT_API_KEY",
)


class TerminalCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from MarketingApp.environments import automation_runtime

        S.reset_state()
        await automation_runtime.reset_automation_runtime()
        self.addCleanup(S.patch_model_env())
        manager = S.fresh_telemetry()
        self.t = manager.__enter__()
        self.addCleanup(manager.__exit__, None, None, None)
        # /provider set os.environ'a dogrudan yazar; test bitince eski haline don.
        self._env_patcher = mock.patch.dict(os.environ, {}, clear=False)
        self._env_patcher.start()
        self.addCleanup(self._env_patcher.stop)
        self.term = Term()

    async def run_cmd(self, line, term=None):
        return await (term or self.term).run(line)


class ProviderCommandTests(TerminalCase):
    async def test_show_reports_no_pinned_agents_on_fresh_config(self):
        out = await self.run_cmd("/provider")
        self.assertIn("Provider", out)
        self.assertIn("default sentinel", out)

    async def test_show_lists_agents_pinned_to_a_literal_model(self):
        await self.run_cmd("/agent edit content_creator_agent --model gemma-4-26b-a4b-it")
        out = await self.run_cmd("/provider show")
        self.assertIn("1 ajan somut model", out)
        self.assertIn("content_creator_agent: gemma-4-26b-a4b-it", out)

    async def test_set_requires_a_provider_name(self):
        out = await self.run_cmd("/provider set")
        self.assertIn("Kullanim", out)

    async def test_dry_run_writes_nothing(self):
        out = await self.run_cmd("/provider set deepseek --base-model deepseek-chat --dry-run")
        self.assertIn("[dry-run]", out)
        self.assertFalse(studio().MODEL_ENV_PATH.exists())
        self.assertNotIn("deepseek", os.environ.get("MODEL_PROVIDER", ""))

    async def test_set_writes_env_vars_and_applies_immediately(self):
        out = await self.run_cmd(
            "/provider set deepseek --base-model deepseek-chat --base-url https://api.deepseek.com --api-key sk-test"
        )
        self.assertIn("Yazildi", out)
        env_text = studio().MODEL_ENV_PATH.read_text(encoding="utf-8")
        self.assertIn("MODEL_PROVIDER=deepseek", env_text)
        self.assertIn("BASE_MODEL_NAME=deepseek-chat", env_text)
        self.assertIn("MOONSHOT_API_KEY=sk-test", env_text)  # deepseek gemini degil -> moonshot slotu
        self.assertEqual(os.environ["MODEL_PROVIDER"], "deepseek")
        self.assertIn("yeniden baslat", out)  # restart uyarisi

    async def test_gemini_api_key_goes_to_the_gemini_env_var(self):
        await self.run_cmd("/provider set gemini --api-key g-test")
        env_text = studio().MODEL_ENV_PATH.read_text(encoding="utf-8")
        self.assertIn("GEMINI_API_KEY=g-test", env_text)
        self.assertNotIn("MOONSHOT_API_KEY", env_text)

    async def test_reset_pins_restores_default_sentinel(self):
        await self.run_cmd("/agent edit content_creator_agent --model gemma-4-26b-a4b-it")
        await self.run_cmd("/agent edit browser_agent --model gemma-4-26b-a4b-it")
        out = await self.run_cmd("/provider set deepseek --base-model deepseek-chat --reset-pins")
        self.assertIn("2 ajanin model pini", out)
        self.assertEqual(agent_entry("content_creator_agent")["model"], "default")
        self.assertEqual(agent_entry("browser_agent")["model"], "browser_default")

    async def test_without_reset_pins_existing_pins_survive(self):
        await self.run_cmd("/agent edit content_creator_agent --model gemma-4-26b-a4b-it")
        await self.run_cmd("/provider set deepseek --base-model deepseek-chat")
        self.assertEqual(agent_entry("content_creator_agent")["model"], "gemma-4-26b-a4b-it")

    async def test_dry_run_previews_pin_resets_without_applying(self):
        await self.run_cmd("/agent edit content_creator_agent --model gemma-4-26b-a4b-it")
        out = await self.run_cmd("/provider set deepseek --reset-pins --dry-run")
        self.assertIn("content_creator_agent: gemma-4-26b-a4b-it -> default", out)
        self.assertEqual(agent_entry("content_creator_agent")["model"], "gemma-4-26b-a4b-it")

    async def test_unknown_subcommand_is_rejected(self):
        out = await self.run_cmd("/provider frobnicate")
        self.assertIn("Bilinmeyen", out)


class MemoryCommandTests(TerminalCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        bellek()._kaydet_bellek({"notlar": [], "tercihler": {}, "kisiler": {}, "gorevler": []})

    async def test_empty_memory_reports_empty(self):
        out = await self.run_cmd("/memory")
        self.assertIn("boş", out.lower())

    async def test_show_all_and_by_category(self):
        bellek().bellek_yaz("tercihler", "ton", "resmi")
        bellek().bellek_yaz("notlar", "proje", "X kampanyasi")

        out_all = await self.run_cmd("/memory")
        self.assertIn("ton", out_all)
        self.assertIn("proje", out_all)

        out_cat = await self.run_cmd("/memory tercihler")
        self.assertIn("ton", out_cat)
        self.assertNotIn("proje", out_cat)

        out_key = await self.run_cmd("/memory tercihler ton")
        self.assertIn("resmi", out_key)

    async def test_search_finds_matches_across_categories(self):
        bellek().bellek_yaz("tercihler", "ton", "resmi ve ciddi")
        bellek().bellek_yaz("notlar", "kampanya", "resmi lansman notu")
        bellek().bellek_yaz("gorevler", "rapor", "haftalik ozet")

        out = await self.run_cmd("/memory search resmi")
        self.assertIn("2 sonuc", out)
        self.assertIn("tercihler", out)
        self.assertIn("notlar", out)
        self.assertNotIn("rapor", out)

    async def test_search_without_a_match_says_so(self):
        out = await self.run_cmd("/memory search bulunmayan-kelime")
        self.assertIn("bulunamadi", out)

    async def test_delete_requires_explicit_yes(self):
        bellek().bellek_yaz("tercihler", "ton", "resmi")
        out = await self.run_cmd("/memory delete tercihler ton")
        self.assertIn("--yes", out)
        self.assertIn("ton", bellek().bellek_raw()["tercihler"])

    async def test_delete_with_yes_removes_the_entry(self):
        bellek().bellek_yaz("tercihler", "ton", "resmi")
        out = await self.run_cmd("/memory delete tercihler ton --yes")
        self.assertIn("silindi", out)
        self.assertNotIn("ton", bellek().bellek_raw()["tercihler"])


if __name__ == "__main__":
    unittest.main()
