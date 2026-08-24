# MarketingApp

AI-powered social media management, content creation, browser automation, and an interactive terminal control interface.

[🇹🇷 Türkçe](#türkçe) | [🇬🇧 English](#english)

---

## 🇬🇧 English

### Quick Start

```bash
git clone https://github.com/Ahmet2001/BrowserAgent.git
cd BrowserAgent
chmod +x run.sh
./run.sh
```

`run.sh` starts an interactive terminal session. Type a message and press enter to chat with the agent, or use one of the built-in commands:

```text
/status                         Show system and channel status
/agents                         List agents
/agent <name> on|off|toggle     Toggle an agent
/tools [query]                  List or filter tools
/tool <name> on|off|toggle      Toggle a tool
/logs [count]                   Show recent logs (default 15)
/heartbeat                      Show scheduler and job status
/heartbeat run|pause|resume <id>
/heartbeat reload               Reload the heartbeat config from disk
/reload                         Reload agent/custom tool config
/history                        Show terminal chat history
/clear                          Clear terminal chat history
/exit                           Shut down safely
```

### What run.sh Does

- Creates `.venv` if it doesn't exist
- Installs/updates packages from `requirements.txt`
- Launches the bot and the interactive terminal via `python -m MarketingApp.main`

### Environment Files

Copy `.env.example` to `.env` and fill in your keys:

- `.env`: main model/provider and Telegram settings
- `.env.local` (optional): local override settings
- `.env.secrets` (optional): additional API keys (Pexels, etc.)

### Features

- **Content Creator Agent** – Text, image, and video content generation
- **Social Media Agent** – X (Twitter) automation, posting, replies
- **Browser Agent** – Playwright/Selenium-based browser automation
- **Research Agent** – Topic research and data gathering
- **System Agent** – System monitoring and computer control (PyAutoGUI)
- **Agent Studio** – Terminal-managed configuration for building and toggling custom agents
- **Agent Packs** – Plug-and-play agent bundles

### Requirements

- Python 3.11+
- Chrome browser (for X automation)
- An active X (Twitter) session in a Chrome profile

For PNG/video rendering, install Playwright browser:

```bash
source .venv/bin/activate
playwright install chromium
```

### License

MIT © 2026 Ahmet Rıfat Öztürk

---

## 🇹🇷 Türkçe

AI destekli sosyal medya, içerik üretimi, browser otomasyonu ve Agent Studio paneli.

### Hemen Çalıştır

```bash
git clone https://github.com/Ahmet2001/BrowserAgent.git
cd BrowserAgent
chmod +x run.sh
./run.sh
```

Panel açıldıktan sonra:

```text
http://127.0.0.1:8001/panel
```

### run.sh Ne Yapar?

- `.venv` yoksa oluşturur
- `requirements.txt` içindeki paketleri kurar/günceller
- `python -m MarketingApp.main` ile botu ve panel API'sini başlatır

### Ortam Dosyaları

`.env.example` dosyasını `.env` olarak kopyalayıp kendi anahtarlarınızı girin:

- `.env`: ana model/provider ve Telegram ayarları
- `.env.local` (opsiyonel): yerel override ayarları
- `.env.secrets` (opsiyonel): Pexels gibi ek API anahtarları

### Özellikler

- **Content Creator Agent** – Metin, görsel ve video içerik üretimi
- **Sosyal Medya Agent** – X (Twitter) otomasyonu, post, yanıt
- **Browser Agent** – Playwright/Selenium tabanlı tarayıcı otomasyonu
- **Araştırma Agent** – Konu araştırması ve veri toplama
- **Sistem Agent** – Sistem izleme ve bilgisayar kontrolü (PyAutoGUI)
- **Agent Studio** – Web panel ile agent yönetimi ve özel agent oluşturma
- **Agent Paketleri** – Tak-çalıştır agent bundle desteği

### Gereksinimler

- Python 3.11+
- Chrome tarayıcı (X otomasyonu için)
- Chrome profilinde aktif X (Twitter) oturumu

PNG/video üretimi için Playwright tarayıcısını kurun:

```bash
source .venv/bin/activate
playwright install chromium
```

### Lisans

MIT © 2026 Ahmet Rıfat Öztürk
