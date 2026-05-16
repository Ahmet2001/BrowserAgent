# Research + Product Thesis

## Kisa Tez

Bu proje sadece sosyal medya icerigi ureten bir bot degil. Asil deger, kalici hafiza, persona, arac kullanan alt ajanlar, otomasyon toparlama akislari ve kodsuz agent tanimi ile calisan bir `memory-native marketing operations system` olmasinda.

Akademik tez:
Sinirli context penceresine sahip, tool-calling kullanan cok ajanli sistemlerde kalici operasyon hafizasi ve rol-temelli yonlendirme; sosyal medya icerik kalitesi, tekrar oranı, gorev basarisi ve insan mudahalesi ihtiyacini anlamli bicimde iyilestirebilir.

Ticari tez:
Pazarlama ekipleri, creator ekipleri ve topluluk yoneticileri; tek bir LLM chatbot degil, marka hafizasi tasiyan, arac baglayabilen, isi parcali uzman alt ajanlara bolebilen ve operasyon kaydi tutan bir sisteme odakli olarak para odemeye daha yakindir.

## Neden Ilginc

Piyasadaki cogu urun su kaliplardan birine sıkisiyor:

- Tek prompt ile icerik uretimi
- Takvim tabanli sosyal medya planlama
- Basit otomasyon
- Ayrik AI chat deneyimi

Bu proje ise su katmanlari birlestiriyor:

- Persona ve rol cekirdegi
- Context paketi ile secici hafiza okuma
- Context aksiyon kaydi ile operasyon izi
- Tool-calling yapan uzman submodel yapisi
- Kodsuz Agent Studio
- Custom tool ekosistemi
- Browser ve sosyal medya otomasyon recovery akislari

Bu kombinasyon hem arastirma hem urun acisindan daha derin bir pozisyon aciyor.

## Akademik Katki Fikri

Ana arastirma sorusu:

Kalici bellek ve rol-temelli ajan orkestrasyonu, sosyal medya gorevlerinde saf prompt-temelli veya hafizasiz tool ajanlara gore daha tutarli ve daha az insan mudahalesi gerektiren sonuclar uretir mi?

Alt sorular:

1. `context_paketi_oku` kullanan ajanlar, kullanmayan ajanlara gore daha az tekrar eden icerik mi uretir?
2. `context_aksiyon_kaydet` ile iz birakan ajanlar, uzun vadede daha yuksek persona tutarliligi saglar mi?
3. Config-driven subagent yapisi, hard-coded ajan yapisina gore daha hizli yeni gorev uyarlamasi saglar mi?
4. Hata toparlama ve API failover mekanizmalari otomasyon basari oranini anlamli sekilde artirir mi?

## Test Edilebilir Hipotezler

H1:
Bellek destekli ajanlarin icerik tekrar orani, hafizasiz bazline'dan daha dusuktur.

H2:
Persona ile kosullanan ajanlarin ton uyumu ve marka uyumu skorlari daha yuksektir.

H3:
Subagent + tool ayrimi olan mimari, tek ajanli sisteme gore gorev tamamlama oraninda daha iyidir.

H4:
Failover ve recovery katmani, browser/API hatalarinda gorev kurtarma oranini artirir.

## Deney Tasarimi

Karsilastirma gruplari:

1. Tek ajan, hafizasiz, sadece prompt
2. Tek ajan, hafizali
3. Cok ajanli, hafizasiz
4. Cok ajanli, hafizali
5. Cok ajanli, hafizali, recovery/failover acik

Gorev seti:

- Verilen market durumuna gore yeni X postu hazirlama
- Son paylasimlarla cakismayan yeni aci secme
- Website iceriginden post paketi uretme
- Stok gorsel ile PNG post hazirlama
- Gorselli X postu yayinlama
- Gelen yoruma marka tonunda yanit hazirlama
- Tarayici veya API hatasi sonrasi gorevi kurtarma

## Olcumler

Nicel metrikler:

- Gorev basari orani
- Ortalama gorev suresi
- Tekrar eden post acisi orani
- Maks karakter sinirini asma orani
- Hata sonrasi toparlanma orani
- Insan mudahalesi ihtiyaci
- Tool cagrisi sayisi
- Context token/karakter verimliligi

Nitel metrikler:

- Persona uyumu
- Marka tonu uyumu
- Fayda/ozgunluk algisi
- Spam/klişe algisi
- Kullanici guveni

Hakemleme yontemi:

- Uzman degerlendirme rubrigi
- Kor hakemle ciftli puanlama
- Gerekirse LLM-as-judge yardimci puanlama, ama birincil metrik olarak degil

## Olası Makale Basliklari

- Memory-Aware Multi-Agent Social Media Orchestration Under Context Constraints
- Configurable Tool-Using Agent Architectures for Marketing Operations
- Persistent Operational Memory for Social Media LLM Agents
- Recovery-Aware Autonomous Browser Workflows for Marketing Automation

## Ticari Konumlama

Urun kategorisi:

AI social operations platform

Daha iyi isimlendirme:

- Memory-native marketing OS
- Agentic brand operations layer
- Configurable marketing agent studio

En guclu deger onerisi:

Markanin tonunu, onceki hareketlerini ve operasyon hafizasini tasiyan ajanlar; icerik uretimi, gorsel hazirlama, yorum operasyonu ve otomasyonu tek panelde yonetir.

## Musteri Segmentleri

- Kucuk ve orta olcekli pazarlama ajanslari
- Web3/kripto topluluk ekipleri
- Solopreneur creator'lar
- Startup growth ekipleri
- Topluluk ve sosyal medya operasyon ekipleri

## MVP Olarak Satilabilecek Sey

MVP paketinde su kombinasyon yeterince kuvvetli:

- Agent Studio ile ozel ajan kurma
- Marka/persona hafizasi
- Website to post pipeline
- Pexels destekli gorselli post uretimi
- X yorum/reply operasyon paneli
- Yayin oncesi veya yayin sonrasi otomasyon kaydi

Bu paket, "icerik yazan AI" gibi degil, "operasyon yapan ama denetlenebilir AI ekip arkadasi" gibi sunulmali.

## Gelir Modelleri

- Aylik SaaS lisansi
- Ajan/adet veya workspace bazli ucretlendirme
- Takim koltugu bazli lisans
- Enterprise setup + custom tool integration
- Ajanslara white-label panel

## Ayriştirici Ozellikler

- Kalici hafiza + persona cekirdegi
- Kodsuz subagent builder
- Custom tool ekleme
- Social/browser recovery mekanizmasi
- Denetlenebilir action log
- Marka baglamini kaybetmeden uzun sureli operasyon

## 90 Gunluk Yol Haritasi

Ilk 30 gun:

- Tek bir use-case sec: X icin marka tonunda gorselli post + reply ops
- Baseline ve hafizali sistem karsilastirmasi kur
- Tekrarlama, ton uyumu ve basari metriği topla
- Demo dataset ve test senaryolari hazirla

31-60 gun:

- Recovery/failover olcumleri ekle
- Agent Studio ile farkli ajan konfigurasyonlari dene
- 5-10 erken kullanici veya ajans gorusmesi yap
- Landing anlatisi degil, dogrudan demo akisi hazirla

61-90 gun:

- Kisa paper draft veya tez proposal cikar
- 1 dikey odak sec: Web3, creator ops veya ajans workflow
- Fiyatlandirma hipotezi test et
- 2-3 pilot kullanici ile gercek is akisina koy

## Hemen Yapilabilecek Somut Ciktilar

1. Deney protokolu dokumani
2. Persona uyum rubrigi
3. Post tekrar olcumu icin benchmark scripti
4. Demo senaryosu
5. 2 sayfalik product thesis deck
6. Kisa akademik abstract

## En Guclu Hikaye

Bu projenin en guclu hikayesi "bir AI araci yaptik" degil.

Asil hikaye su:

`Marka hafizasini, operasyon kaydini ve uzman alt ajanlari birlestiren; insan mudahalesini sifirlamaya degil, minimuma indirmeye calisan yeni bir marketing systems layer tasarliyoruz.`

Bu hikaye hem akademide ciddiye alinabilir hem ticari tarafta satilabilir.
