# MarketingApp

AI destekli sosyal medya, icerik uretimi, browser otomasyonu ve Agent Studio paneli.

## Hemen Calistir

```bash
git pull
./run.sh
```

Yeni bilgisayarda ilk kez calistiriyorsan:

```bash
git clone https://github.com/Ahmet2001/BrowserAgent.git
cd BrowserAgent
chmod +x run.sh
./run.sh
```

Panel acildiktan sonra:

```text
http://127.0.0.1:8001/panel
```

## run.sh Ne Yapar?

- `.venv` yoksa olusturur.
- `requirements.txt` icindeki paketleri kurar/gunceller.
- `python -m MarketingApp.main` ile botu ve panel API'sini baslatir.

## Ortam Dosyalari

Bu repo private kabul edildigi icin calisma ayarlari repoda tutulur:

- `.env`: ana model/provider ve Telegram ayarlari
- `.env.local`: yerel override ayarlari
- `.env.secrets`: Pexels gibi ek API anahtarlari

`.env.secrets` bilincli olarak git tarafindan takip edilir. Repo public olursa bu dosyayi tekrar ignore etmek gerekir.

## Notlar

- X otomasyonu icin Chrome kurulu ve X oturumu acil bir profil gerekir.
- X'te gorselli post yayinlamak icin panelde `content_creator_agent` ve `sosyal_medya_agent` aktif olmali.
- PNG/video uretiminde Playwright tarayicisi eksikse bir kere sunu calistir:

```bash
source .venv/bin/activate
playwright install chromium
```
