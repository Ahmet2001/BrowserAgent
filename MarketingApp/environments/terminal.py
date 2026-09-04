"""Mimar icin interaktif terminal yonetim arayuzu."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import shlex
import sys
import time
from datetime import datetime
from typing import Any, Callable

from MarketingApp.environments.automation_runtime import (
    get_automation_snapshot,
    release_automation,
    try_acquire_automation,
)
from MarketingApp.environments.heartbeat import (
    get_heartbeat_jobs_snapshot,
    get_heartbeat_status_snapshot,
    pause_heartbeat_job,
    reload_heartbeat_service,
    resume_heartbeat_job,
    run_heartbeat_job,
)


from MarketingApp.paths import workspace_path

_HISTORY_FILE = workspace_path(".system", "terminal_chat_history.json")
_MAX_HISTORY = 30
_MAX_CONTEXT_MESSAGES = 12
_MAX_CONTEXT_CHARS = 5000


class TerminalManager:
    """Sohbeti ve temel runtime islemlerini tek terminal dongusunde yonetir."""

    def __init__(
        self,
        base_model,
        *,
        telegram_enabled: bool = False,
        discord_enabled: bool = False,
        input_func: Callable[[str], Any] = input,
        output_func: Callable[[str], Any] = print,
        history_file: str = _HISTORY_FILE,
    ):
        self.base_model = base_model
        self.telegram_enabled = bool(telegram_enabled)
        self.discord_enabled = bool(discord_enabled)
        self.input_func = input_func
        self.output_func = output_func
        self.history_file = history_file
        self.history = self._load_history()
        self._original_request_approval = getattr(base_model, "request_approval", None)
        self._use_color = output_func is print and sys.stdout.isatty() and not os.getenv("NO_COLOR")

    async def run(self) -> None:
        self.base_model.request_approval = self._request_terminal_approval
        self._print_banner()
        try:
            while True:
                try:
                    line = await self._read_line(self._color("sen> ", "cyan"))
                except (EOFError, KeyboardInterrupt):
                    self._emit("\nTerminal oturumu kapatiliyor.")
                    return

                if line is None:
                    return
                if not await self.handle_line(str(line)):
                    return
        finally:
            if self._original_request_approval is not None:
                self.base_model.request_approval = self._original_request_approval

    async def handle_line(self, raw_line: str) -> bool:
        line = (raw_line or "").strip()
        if not line:
            return True
        if line.startswith("/"):
            return await self._handle_command(line)
        await self._chat(line)
        return True

    async def _read_line(self, prompt: str) -> str:
        if self.input_func is input:
            return await asyncio.to_thread(input, prompt)
        result = self.input_func(prompt)
        if inspect.isawaitable(result):
            return await result
        return result

    def _emit(self, message: str = "") -> None:
        self.output_func(str(message))

    def _color(self, text: str, color: str) -> str:
        if not self._use_color:
            return text
        codes = {
            "cyan": "\033[96m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "red": "\033[91m",
            "bold": "\033[1m",
        }
        return f"{codes.get(color, '')}{text}\033[0m"

    def _print_banner(self) -> None:
        model = getattr(self.base_model, "model", "bilinmiyor")
        provider = getattr(self.base_model, "provider_name", "bilinmiyor")
        self._emit("")
        self._emit(self._color("MIMAR TERMINAL", "bold"))
        self._emit(f"Model: {model} | Saglayici: {provider}")
        self._emit(
            f"Telegram: {'aktif' if self.telegram_enabled else 'kapali'} | "
            f"Discord: {'aktif' if self.discord_enabled else 'kapali'}"
        )
        self._emit("Mesaj yaz veya komutlari gormek icin /help kullan. Cikmak icin /exit.")
        if self.history:
            self._emit(f"Onceki terminal sohbetinden {len(self.history)} mesaj yuklendi.")
        self._emit("")

    async def _handle_command(self, line: str) -> bool:
        try:
            parts = shlex.split(line)
        except ValueError as exc:
            self._emit(self._color(f"Komut okunamadi: {exc}", "red"))
            return True

        command = parts[0].lower()
        args = parts[1:]

        if command in {"/exit", "/quit", "/q"}:
            self._emit("Mimar kapatiliyor...")
            return False
        if command in {"/help", "/?"}:
            self._print_help()
        elif command == "/status":
            self._print_status()
        elif command == "/agents":
            self._print_agents()
        elif command == "/agent":
            self._manage_agent(args)
        elif command == "/tools":
            self._print_tools(" ".join(args))
        elif command == "/tool":
            self._manage_tool(args)
        elif command == "/logs":
            self._print_logs(args)
        elif command == "/history":
            self._print_history()
        elif command == "/clear":
            self._clear_history()
        elif command == "/reload":
            self._reload_agents()
        elif command == "/heartbeat":
            await self._manage_heartbeat(args)
        else:
            self._emit(self._color(f"Bilinmeyen komut: {command}. /help ile listeyi gorebilirsin.", "yellow"))
        return True

    def _print_help(self) -> None:
        self._emit(
            """
Komutlar
  /status                         Sistem ve kanal durumunu goster
  /agents                         Ajanlari listele
  /agent <ad> on|off|toggle       Ajan durumunu degistir
  /tools [arama]                  Tool'lari listele veya filtrele
  /tool <ad> on|off|toggle        Tool durumunu degistir
  /logs [adet]                    Son loglari goster (varsayilan 15)
  /heartbeat                      Zamanlayici ve gorev durumunu goster
  /heartbeat run <id>             Bir heartbeat gorevini simdi calistir
  /heartbeat pause|resume <id>    Gorevi duraklat veya devam ettir
  /heartbeat reload               Config'i diskten yeniden yukle
  /reload                         Ajan ve custom tool config'ini yenile
  /history                        Terminal sohbet gecmisini goster
  /clear                          Terminal sohbet gecmisini temizle
  /exit                           Uygulamayi guvenli sekilde kapat

Slash ile baslamayan her satir Mimar'a mesaj olarak gonderilir.
""".strip()
        )

    def _print_status(self) -> None:
        uptime = max(0, int(time.time() - getattr(self.base_model, "start_time", time.time())))
        heartbeat = get_heartbeat_status_snapshot()
        automation = get_automation_snapshot()
        self._emit(self._color("Sistem durumu", "bold"))
        self._emit(f"  Model      : {getattr(self.base_model, 'model', '-')}")
        self._emit(f"  Saglayici  : {getattr(self.base_model, 'provider_name', '-')}")
        self._emit(f"  Uptime     : {self._format_duration(uptime)}")
        self._emit(f"  Telegram   : {'aktif' if self.telegram_enabled else 'kapali'}")
        self._emit(f"  Discord    : {'aktif' if self.discord_enabled else 'kapali'}")
        self._emit(
            f"  Heartbeat  : {'calisiyor' if heartbeat.get('running') else 'kapali'} "
            f"({heartbeat.get('job_count', 0)} gorev)"
        )
        if automation.get("busy"):
            self._emit(
                f"  Otomasyon  : mesgul - {automation.get('owner') or '-'} / "
                f"{automation.get('label') or automation.get('job_id') or '-'}"
            )
        else:
            self._emit("  Otomasyon  : hazir")

    def _print_agents(self) -> None:
        agents = self.base_model.get_hierarchy().get("submodels", [])
        self._emit(self._color(f"Ajanlar ({len(agents)})", "bold"))
        for agent in agents:
            state = "ON " if agent.get("active") else "OFF"
            self._emit(
                f"  [{state}] {agent.get('name')} | {agent.get('model') or '-'} | "
                f"{agent.get('tool_count', len(agent.get('tools') or []))} tool"
            )

    def _manage_agent(self, args: list[str]) -> None:
        if len(args) != 2:
            self._emit("Kullanim: /agent <ad> on|off|toggle")
            return
        name, action = args[0], args[1].lower()
        current = getattr(self.base_model, "active_agents", {}).get(name)
        if current is None:
            self._emit(self._color(f"Ajan bulunamadi: {name}", "red"))
            return
        try:
            target = self._resolve_switch(action, current)
            active = self.base_model.set_agent_active(name, target)
            self._emit(self._color(f"{name}: {'aktif' if active else 'pasif'}", "green"))
        except ValueError as exc:
            self._emit(str(exc))

    def _all_tools(self) -> list[dict]:
        hierarchy = self.base_model.get_hierarchy()
        tools = list(hierarchy.get("tools", []))
        for agent in hierarchy.get("submodels", []):
            tools.extend(agent.get("tools", []))
        unique = {}
        for tool in tools:
            unique.setdefault(tool.get("name"), tool)
        return [tool for name, tool in sorted(unique.items()) if name]

    def _print_tools(self, query: str = "") -> None:
        needle = query.strip().lower()
        tools = [
            tool for tool in self._all_tools()
            if not needle or needle in tool.get("name", "").lower() or needle in tool.get("desc", "").lower()
        ]
        self._emit(self._color(f"Tool'lar ({len(tools)})", "bold"))
        if not tools:
            self._emit("  Eslesen tool yok.")
            return
        for tool in tools:
            state = "ON " if tool.get("active", True) else "OFF"
            self._emit(f"  [{state}] {tool.get('name')}")

    def _manage_tool(self, args: list[str]) -> None:
        if len(args) != 2:
            self._emit("Kullanim: /tool <ad> on|off|toggle")
            return
        name, action = args[0], args[1].lower()
        current = getattr(self.base_model, "active_tools", {}).get(name)
        if current is None:
            self._emit(self._color(f"Tool bulunamadi: {name}", "red"))
            return
        try:
            target = self._resolve_switch(action, current)
            active = self.base_model.set_tool_active(name, target)
            self._emit(self._color(f"{name}: {'aktif' if active else 'pasif'}", "green"))
        except ValueError as exc:
            self._emit(str(exc))

    def _print_logs(self, args: list[str]) -> None:
        try:
            count = min(100, max(1, int(args[0]))) if args else 15
        except ValueError:
            self._emit("Kullanim: /logs [adet]")
            return
        logs = list(getattr(self.base_model, "logs", []))[-count:]
        self._emit(self._color(f"Son loglar ({len(logs)})", "bold"))
        for item in logs:
            self._emit(f"  {item.get('time', '--:--:--')} [{item.get('type', 'log')}] {item.get('message', '')}")

    def _print_history(self) -> None:
        if not self.history:
            self._emit("Sohbet gecmisi bos.")
            return
        self._emit(self._color(f"Sohbet gecmisi ({len(self.history)})", "bold"))
        for item in self.history:
            label = "Sen" if item.get("role") == "user" else "Mimar"
            self._emit(f"  {item.get('time', '--:--')} {label}: {item.get('content', '')}")

    def _clear_history(self) -> None:
        self.history = []
        self._save_history()
        self._emit(self._color("Terminal sohbet gecmisi temizlendi.", "green"))

    def _reload_agents(self) -> None:
        hierarchy = self.base_model.reload_agent_studio()
        self._emit(
            self._color(
                f"Runtime yenilendi: {len(hierarchy.get('submodels', []))} ajan, "
                f"{len(hierarchy.get('tools', []))} base tool.",
                "green",
            )
        )

    async def _manage_heartbeat(self, args: list[str]) -> None:
        if not args:
            status = get_heartbeat_status_snapshot()
            jobs = get_heartbeat_jobs_snapshot()
            self._emit(self._color("Heartbeat", "bold"))
            self._emit(
                f"  Servis: {'calisiyor' if status.get('running') else 'kapali'} | "
                f"Config: {'aktif' if status.get('enabled') else 'pasif'} | {len(jobs)} gorev"
            )
            for job in jobs:
                self._emit(
                    f"  [{'RUN' if job.get('running') else 'ON ' if not job.get('paused') else 'OFF'}] "
                    f"{job.get('job_id')} | {job.get('name') or '-'} | sonraki: {job.get('next_run_at') or '-'}"
                )
            return

        action = args[0].lower()
        try:
            if action == "reload" and len(args) == 1:
                result = await reload_heartbeat_service(reason="terminal_reload")
            elif action in {"run", "pause", "resume"} and len(args) == 2:
                job_id = args[1]
                operations = {
                    "run": run_heartbeat_job,
                    "pause": pause_heartbeat_job,
                    "resume": resume_heartbeat_job,
                }
                result = await operations[action](job_id)
            else:
                self._emit("Kullanim: /heartbeat [reload|run <id>|pause <id>|resume <id>]")
                return
            self._emit(self._color(f"Heartbeat islemi tamamlandi: {result}", "green"))
        except Exception as exc:
            self._emit(self._color(f"Heartbeat hatasi: {exc}", "red"))

    async def _chat(self, user_text: str) -> None:
        job_id = f"terminal-chat-{time.time_ns()}"
        acquired, snapshot = await try_acquire_automation(
            "terminal",
            job_id=job_id,
            label="Terminal sohbet istegi",
            source="terminal",
        )
        if not acquired:
            owner = snapshot.get("owner") or "otomasyon"
            label = snapshot.get("label") or snapshot.get("job_id") or "aktif gorev"
            self._emit(self._color(f"Sistem mesgul: {owner} / {label}", "yellow"))
            return

        context = self._build_context()
        self._add_history("user", user_text)
        self._emit(self._color("Mimar dusunuyor...", "yellow"))

        async def on_direct_text(text: str):
            cleaned = (text or "").strip()
            if cleaned:
                self._emit(f"  ↳ {cleaned}")

        try:
            result = await self.base_model.text_query(
                user_text,
                context=context,
                on_direct_text=on_direct_text,
            )
            answer = self._extract_result_text(result)
            self._add_history("assistant", answer)
            self._emit("")
            self._emit(self._color("Mimar>", "green"))
            self._emit(answer)
            self._emit("")
        except Exception as exc:
            self._emit(self._color(f"Model hatasi: {exc}", "red"))
        finally:
            await release_automation("terminal", job_id=job_id)

    async def _request_terminal_approval(self, action_id: str, description: str) -> bool:
        self._emit("")
        self._emit(self._color("ONAY GEREKLI", "yellow"))
        self._emit(f"  {description}")
        try:
            answer = await self._read_line("  Onayliyor musun? [e/H]: ")
        except (EOFError, KeyboardInterrupt):
            return False
        approved = (answer or "").strip().lower() in {"e", "evet", "y", "yes"}
        self.base_model.log_message(
            "sistem",
            f"Terminal onayi: {action_id} -> {'onaylandi' if approved else 'reddedildi'}",
        )
        return approved

    def _build_context(self) -> str:
        selected = self.history[-_MAX_CONTEXT_MESSAGES:]
        rendered = []
        total_chars = 0
        for item in reversed(selected):
            role = "Kullanici" if item.get("role") == "user" else "Asistan"
            line = f"{role}: {item.get('content', '')}"
            if rendered and total_chars + len(line) > _MAX_CONTEXT_CHARS:
                break
            rendered.append(line)
            total_chars += len(line)
        if not rendered:
            return ""
        return "=== TERMINAL KONUSMA GECMISI ===\n" + "\n".join(reversed(rendered)) + "\n\n=== YENI MESAJ ==="

    @staticmethod
    def _extract_result_text(result: Any) -> str:
        if isinstance(result, tuple):
            if len(result) > 1 and str(result[1] or "").strip():
                return str(result[1]).strip()
            if len(result) > 3 and result[3]:
                return str(result[3][-1]).strip()
            if len(result) > 2 and result[2]:
                return str(result[2][-1]).strip()
        if isinstance(result, str) and result.strip():
            return result.strip()
        return "Islem tamamlandi ancak metin yaniti uretilmedi."

    @staticmethod
    def _resolve_switch(action: str, current: bool) -> bool:
        if action in {"on", "ac", "aktif"}:
            return True
        if action in {"off", "kapat", "pasif"}:
            return False
        if action in {"toggle", "degistir"}:
            return not current
        raise ValueError("Durum on, off veya toggle olmali.")

    @staticmethod
    def _format_duration(seconds: int) -> str:
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}s {minutes}dk {secs}sn"
        if minutes:
            return f"{minutes}dk {secs}sn"
        return f"{secs}sn"

    def _load_history(self) -> list[dict]:
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if not isinstance(raw, list):
                return []
            return [
                item for item in raw
                if isinstance(item, dict)
                and item.get("role") in {"user", "assistant"}
                and str(item.get("content") or "").strip()
            ][-_MAX_HISTORY:]
        except Exception:
            return []

    def _save_history(self) -> None:
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        temporary = f"{self.history_file}.tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(self.history[-_MAX_HISTORY:], handle, ensure_ascii=False, indent=2)
            os.replace(temporary, self.history_file)
        except Exception as exc:
            self._emit(self._color(f"Gecmis kaydedilemedi: {exc}", "yellow"))

    def _add_history(self, role: str, content: str) -> None:
        cleaned = (content or "").strip()
        if not cleaned:
            return
        self.history.append(
            {
                "role": role,
                "content": cleaned,
                "time": datetime.now().strftime("%H:%M"),
            }
        )
        self.history = self.history[-_MAX_HISTORY:]
        self._save_history()


async def run_terminal_manager(base_model, *, telegram_enabled: bool = False, discord_enabled: bool = False):
    manager = TerminalManager(
        base_model,
        telegram_enabled=telegram_enabled,
        discord_enabled=discord_enabled,
    )
    await manager.run()
