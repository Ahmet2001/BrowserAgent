# MarketingApp

AI destekli sosyal medya, icerik uretimi, browser otomasyonu ve Agent Studio paneli.

## Hemen Calistir

```bash
git pull
./run.sh
```

Panel acildiktan sonra:

```text
http://127.0.0.1:8001/panel
```

`run.sh` yoksa ya da calisma izni kaybolduysa:

```bash
chmod +x run.sh
./run.sh
```

## Notlar

- `.env`, `.env.local` ve `.env.secrets` proje calisma ayarlari icin kullanilir.
- X otomasyonu icin Chrome kurulu ve X oturumu acil bir profil gerekir.
- PNG/video uretiminde Playwright tarayicisi eksikse bir kere sunu calistir:

```bash
source .venv/bin/activate
playwright install chromium
```
