"""
Heartbeat — Proaktif Ajan Daemon.

OpenClaw tarzı zamanlayıcı: Belirli aralıklarla veya saatlerde uyanarak
BaseModel'e görev gönderir ve sonuçları Telegram'a iletir.

Kullanım:
  - main.py içinden: await heartbeat_loop(base_model, telegram_bot, chat_id)
  - Test: python -m MarketingApp.enviroments.heartbeat --test-tick
"""

import asyncio
import os
import time
from datetime import datetime, timedelta

try:
    import yaml
    _YAML_IMPORT_ERROR = None
except ImportError as yaml_import_error:
    yaml = None
    _YAML_IMPORT_ERROR = yaml_import_error


# ─── Config ──────────────────────────────────────────────────────────────────

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "heartbeat_config.yaml"
)


def _resolve_telegram_target(telegram_bot=None, chat_id: int | None = None):
    """Varsa heartbeat ciktisi icin Telegram bot/chat hedefini cozer."""
    resolved_bot = telegram_bot
    resolved_chat_id = chat_id

    if resolved_chat_id is None:
        env_chat_id = os.getenv("HEARTBEAT_CHAT_ID") or os.getenv("DEFAULT_CHAT_ID")
        if env_chat_id:
            try:
                resolved_chat_id = int(env_chat_id)
            except ValueError:
                resolved_chat_id = None

    if resolved_bot is None or resolved_chat_id is None:
        try:
            from MarketingApp.araclar.vlm_araclari import get_registered_bot
            registered_bot, registered_chat_id = get_registered_bot()
            if resolved_bot is None:
                resolved_bot = registered_bot
            if resolved_chat_id is None:
                resolved_chat_id = registered_chat_id
        except Exception:
            pass

    return resolved_bot, resolved_chat_id


def load_config() -> dict:
    """heartbeat_config.yaml dosyasını yükler."""
    if yaml is None:
        print(f"⚠️ [Heartbeat] PyYAML yüklü değil, heartbeat devre dışı: {_YAML_IMPORT_ERROR}")
        return {"enabled": False, "interval_minutes": 30, "tasks": []}
    if not os.path.exists(_CONFIG_PATH):
        print(f"⚠️ [Heartbeat] Config bulunamadı: {_CONFIG_PATH}")
        return {"enabled": False, "interval_minutes": 30, "tasks": []}
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"enabled": False, "interval_minutes": 30, "tasks": []}


# ─── Cron Değerlendirme ─────────────────────────────────────────────────────

def _should_run_task(cron: str, now: datetime, last_runs: dict, task_idx: int) -> bool:
    """
    Basit cron formatını değerlendirir:
      "startup"  → Sadece başlangıçta (zaten ayrı ele alınıyor)
      "HH:MM"    → Günde bir kez, belirli saat-dakika
      "*/N"      → Her N dakikada bir
    """
    if cron == "startup":
        return False  # startup görevleri ayrıca ele alınır

    key = f"task_{task_idx}"

    # "*/N" formatı: Her N dakikada
    if cron.startswith("*/"):
        try:
            interval = int(cron[2:])
        except ValueError:
            return False
        last = last_runs.get(key)
        if last is None:
            return True
        return (now - last).total_seconds() >= interval * 60

    # "HH:MM" formatı: Günde bir kez
    if ":" in cron:
        try:
            h, m = map(int, cron.split(":"))
        except ValueError:
            return False
        target_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
        # ±2 dakikalık pencere
        diff = abs((now - target_time).total_seconds())
        if diff > 120:
            return False
        # Bugün zaten çalıştıysa tekrar çalıştırma
        last = last_runs.get(key)
        if last and last.date() == now.date():
            return False
        return True

    return False


# ─── Görev Çalıştırıcı ──────────────────────────────────────────────────────

async def _execute_heartbeat_task(
    base_model,
    gorev: str,
    telegram_bot=None,
    chat_id: int = None
):
    """Tek bir heartbeat görevini BaseModel üzerinde çalıştırır."""
    print(f"💓 [Heartbeat] Görev çalıştırılıyor: {gorev[:60]}...")
    telegram_bot, chat_id = _resolve_telegram_target(telegram_bot, chat_id)

    collected_texts = []

    async def on_text(metin: str):
        collected_texts.append(metin)

    async def on_cevap(cevap: str):
        collected_texts.append(cevap)

    try:
        _audio, transcript, direct_texts, cevap_metinleri = await base_model.text_query(
            user_text=f"[HEARTBEAT OTOMATİK GÖREV] {gorev}",
            on_direct_text=on_text,
            on_cevap_metni=on_cevap
        )

        # Tüm çıktıları birleştir
        all_output = []
        if cevap_metinleri:
            all_output.extend(cevap_metinleri)
        if direct_texts:
            all_output.extend(direct_texts)
        if transcript and not all_output:
            all_output.append(transcript)
        # Callback ile toplananları da ekle (zaten yukarıdakilerle aynı olabilir ama emin olalım)
        for t in collected_texts:
            if t not in all_output:
                all_output.append(t)

        # Telegram'a gönder
        if telegram_bot and chat_id and all_output:
            for text in all_output:
                parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for part in parts:
                    try:
                        await telegram_bot.send_message(
                            chat_id=chat_id,
                            text=f"💓 *Heartbeat*\n\n{part}",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        # Markdown hatası olursa düz metin
                        await telegram_bot.send_message(
                            chat_id=chat_id,
                            text=f"💓 Heartbeat\n\n{part}"
                        )

        print(f"✅ [Heartbeat] Görev tamamlandı.")
        return True

    except Exception as e:
        print(f"❌ [Heartbeat] Görev hatası: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─── Ana Döngü ──────────────────────────────────────────────────────────────

async def heartbeat_loop(
    base_model,
    telegram_bot=None,
    chat_id: int = None
):
    """
    Ana heartbeat döngüsü. main.py içinde asyncio.gather() ile çalıştırılır.
    
    Args:
        base_model: BaseModel instance
        telegram_bot: telegram.Bot instance (mesaj göndermek için)
        chat_id: Hedef Telegram chat ID'si
    """
    last_runs: dict[str, datetime] = {}
    was_enabled = None
    startup_tasks_ran = False

    while True:
        config = load_config()
        enabled = bool(config.get("enabled", False))
        interval = max(1, int(config.get("interval_minutes", 30) or 30))
        tasks = config.get("tasks", [])
        check_interval = min(interval, 1) * 60

        if not enabled:
            if was_enabled is not False:
                print("⏸️ [Heartbeat] Devre dışı (config: enabled=false)")
            was_enabled = False
            startup_tasks_ran = False
            last_runs = {}
            await asyncio.sleep(check_interval)
            continue

        if not tasks:
            if was_enabled is not True or startup_tasks_ran:
                print("⚠️ [Heartbeat] Görev listesi boş, beklemede.")
            was_enabled = True
            startup_tasks_ran = False
            last_runs = {}
            await asyncio.sleep(check_interval)
            continue

        if was_enabled is not True:
            print(f"💓 [Heartbeat] Başlatıldı — {len(tasks)} görev, kontrol aralığı: {interval} dk")
            last_runs = {}

        if not startup_tasks_ran:
            for idx, task in enumerate(tasks):
                if task.get("cron") == "startup":
                    await _execute_heartbeat_task(
                        base_model, task["gorev"], telegram_bot, chat_id
                    )
                    last_runs[f"task_{idx}"] = datetime.now()
            startup_tasks_ran = True

        was_enabled = True
        now = datetime.now()

        for idx, task in enumerate(tasks):
            cron = task.get("cron", "")
            gorev = task.get("gorev", "")

            if not gorev or cron == "startup":
                continue

            if _should_run_task(cron, now, last_runs, idx):
                print(f"💓 [Heartbeat] Tetiklendi: Task #{idx} (cron={cron})")
                success = await _execute_heartbeat_task(
                    base_model, gorev, telegram_bot, chat_id
                )
                if success:
                    last_runs[f"task_{idx}"] = now

        await asyncio.sleep(check_interval)


# ─── Tek Tick Test ───────────────────────────────────────────────────────────

async def test_tick():
    """Config'deki ilk görevi çalıştırarak heartbeat'i test eder."""
    config = load_config()
    tasks = config.get("tasks", [])

    if not tasks:
        print("❌ Config'de görev bulunamadı.")
        return

    print(f"🧪 [Heartbeat Test] {len(tasks)} görev bulundu, ilk görev çalıştırılıyor...")
    print(f"   Config yolu: {_CONFIG_PATH}")
    print(f"   Görevler:")
    for i, t in enumerate(tasks):
        print(f"     [{i}] cron={t.get('cron')} → {t.get('gorev', '')[:60]}...")

    # BaseModel olmadan sadece config'i doğrula
    print("\n✅ [Heartbeat Test] Config geçerli. BaseModel ile entegre test için main.py'den çalıştırın.")


if __name__ == "__main__":
    import sys
    if "--test-tick" in sys.argv:
        asyncio.run(test_tick())
    else:
        print("Kullanım: python -m MarketingApp.enviroments.heartbeat --test-tick")
