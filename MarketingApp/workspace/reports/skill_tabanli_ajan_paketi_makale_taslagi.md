# Skill Tabanli Ajan Paketi Uretimi ile Birlikte Calisabilir Ajan Ekosistemleri

## Ozet

Buyuk dil modelleri ile gelistirilen ajan sistemleri son donemde hizla yayginlasmis olsa da,
bu sistemlerin buyuk bolumu ya kapali ve sabit agent mimarilerine dayanmakta ya da yeni
agent ve tool ekleme surecinde yuksek duzeyde manuel muhendislik gerektirmektedir.
Ozellikle son kullanicinin veya yaratici gelistiricinin disarida uretilen bir agent'i,
onunla birlikte gelen tool'lari ve gorev mantigini mevcut bir orkestrasyon katmanina
tak-calistir biciminde baglayabilmesi halen zor bir problemdir. Bu calismada, bu probleme
yonelik olarak skill tabanli bir kontrat yaklasimi onerilmektedir. Onerilen yaklasimda
LLM'e serbest bir kod uretim gorevi verilmek yerine, belirli klasor yapisi, manifest
kurallari, tool kontrati, agent tanim semasi ve dogrulama kontrol listesi iceren bir
`SKILL.md` uzerinden disaridan import edilebilir `Tool Pack`, `Agent Bundle` ve
`Runtime Pack` uretilmesi saglanir. Bu yapi, Agent Studio benzeri bir orkestrasyon paneli
ile birlikte calisarak hem kodsuz agent tasarimini hem de moduler genislemeyi destekler.
Calisma, bu skill tabanli kontrat mekanizmasinin ilk denemede gecerli paket uretme oranini,
entegrasyon basarisini ve insan mudahalesi ihtiyacini iyilestirebilecegini savunmaktadir.
Makale; sistem modelini, mimari bilesenleri, deneysel hipotezleri ve potansiyel ticari ve
akademik etkileri tartismaktadir.

**Anahtar Kelimeler:** agentic systems, interoperability, tool calling, no-code agent design,
contract-guided generation, multi-agent orchestration

## 1. Giris

LLM tabanli arac kullanan ajanlar; icerik uretimi, arastirma, browser otomasyonu ve sosyal
medya operasyonlari gibi alanlarda giderek daha yetkin hale gelmektedir. Buna ragmen pratikte
iki temel darboğaz devam etmektedir. Birincisi, ajanlarin cogu kapali ve sabit mimariler
uzerine kuruludur; yeni bir uzman ajan eklemek veya yeni bir tool'u sisteme baglamak icin
dogrudan kod duzeyinde degisiklik gerekmektedir. Ikincisi, disaridaki baska bir model ya da
gelistirici tarafindan uretilen bir agent paketinin var olan orkestrasyona uyumlu bicimde
baglanmasi icin ortak bir paketleme standardi bulunmamaktadir.

Bu eksiklikler, LLM ajan ekosistemlerinin olgunlasmasinin onundeki temel engellerden biridir.
Bugun bircok sistem "agent builder" veya "custom tool" vaadi sunsa da, ortaya cikan yapilar
genellikle platforma ozel, dokumantasyon-bagimli ve elle toparlanmasi gereken daginik
ciktilar uretmektedir. Bu nedenle son kullanicinin veya teknik olmayan ekiplerin kendi uzman
ajanlarini olusturmasi teoride mumkun gorunse de pratikte yuksek hata orani ve yogun manuel
muhendislik ihtiyaci ortaya cikmaktadir.

Bu calisma, bu sorunu "skill tabanli kontrat" kavrami ile ele almaktadir. Temel fikir,
disaridaki bir LLM'den "bana bir ajan yarat" seklinde serbest bir kod uretimi istemek yerine,
o modele Agent Studio ile uyumlu bir paket nasil olusturulmasi gerektigini anlatan resmi bir
`SKILL.md` vermektir. Bu skill, paket tiplerini, klasor yapisini, manifest semasini, tool
dosya kurallarini, prompt dosyalarini, env beklentilerini ve son dogrulama adimlarini
belirleyen bir uretim kontrati olarak gorev yapar.

Bu sayede sistem sadece agent ureten degil, **birlikte calisabilir agent paketleri
uretilebilen bir ajan ekosistemi** haline gelir.

## 2. Problem Tanimi

Bu calismada ele alinan temel problem su sekilde ifade edilebilir:

> Dogal dil girdisi veya yuksek seviyeli bir gorev tanimi uzerinden, var olan bir orkestrasyon
> katmanina guvenli ve tutarli sekilde baglanabilen import edilebilir agent ve tool paketleri
> nasil uretilebilir?

Bu problemin alt zorluklari sunlardir:

1. **Semantik daginiklik:** LLM ayni ihtiyac icin farkli klasor yapilari ve farkli metadata
   formatlari uretebilir.
2. **Kontrat eksikligi:** Tool fonksiyonlari, agent manifestleri ve prompt dosyalari
   arasinda ortak sema olmayinca import katmani kirilgan hale gelir.
3. **Orkestrasyon uyumsuzlugu:** Disarida uretilen agent, mevcut tool registry, memory
   policy veya runtime yukleme akisi ile uyumlu olmayabilir.
4. **Yuksek manuel duzeltme maliyeti:** Kullanici her yeni bundle icin kodu tek tek gozden
   gecirmek ve duzeltmek zorunda kalir.
5. **Guvenlik ve risk yonetimi:** Ozellikle custom Python tool'larin kontrolsuz import'u
   sisteme operasyonel ve guvenlik riskleri tasiyabilir.

Dolayisiyla problem yalnizca "bir agent yaratmak" degil, **import edilebilir, dogrulanabilir,
moduler ve birlikte calisabilir agent paketleri yaratmak**tir.

## 3. Calismanin Katkilari

Bu makalenin temel katkilarini su sekilde ozetliyoruz:

1. **Skill tabanli paket kontrati:** Agent bundle uretimi icin LLM'e verilen resmi bir
   uretim skill'i tanimlanmistir.
2. **Paket tipleri icin acik ayrim:** `Tool Pack`, `Agent Bundle` ve `Runtime Pack`
   kategorileri ile farkli kullanici ve teknik seviye ihtiyaclari ayrilmistir.
3. **Deterministik klasor ve manifest semasi:** LLM tarafindan uretilen ciktilarin parse
   edilebilir olmasi icin zorunlu klasor yapisi ve metadata alanlari tanimlanmistir.
4. **No-code ile agent ekosistemi arasinda kopru:** Son kullanicinin kendi agent sistemini
   disaridaki bir LLM yardimiyla urettirip mevcut orchestrator'a baglayabilmesi hedeflenmistir.
5. **Deneysel olarak test edilebilir hipotezler:** Bu yaklasimin gecerliligi, import basarisi,
   ilk denemede dogruluk ve insan mudahalesi maliyeti gibi olculerle test edilebilir hale
   getirilmistir.

## 4. Sistem Modeli

Onerilen mimari dort ana katmandan olusur:

### 4.1 Orkestrasyon Katmani

Bu katman BaseModel veya ana orchestrator olarak dusunulebilir. Gorevi:

- aktif submodel'lari yuklemek,
- tool schema'larini olusturmak,
- uygun agent'a gorev devretmek,
- memory ve context okuma araclarini yonetmek,
- calisma zamani hata toparlama ve durum loglamasini saglamaktir.

### 4.2 Agent Studio Katmani

Agent Studio, kullanicinin kod yazmadan agent tanimlayabildigi, tool baglayabildigi ve
runtime davranisini yonetebildigi panel katmanidir. Mevcut yapida config-driven agent
tanimi, custom tool ekleme ve agent aktif/pasif yonetimi desteklenmektedir. Bu calisma ile
Agent Studio'nun bir sonraki evrimi olarak import edilebilir paketleri kabul eden bir
`Import Pack Preview` ve `Bind to Orchestrator` akisina gecis hedeflenmektedir.

### 4.3 Skill Tabanli Uretim Katmani

Bu katmanin merkezinde `SKILL.md` bulunur. Skill'in gorevi, disaridaki bir LLM'in
serbest kod uretmesini engelleyip onu belirli bir kontrata baglamaktir. Skill icerigi:

- paket tipleri,
- klasor yapisi,
- manifest kurallari,
- tool fonksiyon kontrati,
- agent manifest semasi,
- prompt dosya konvansiyonlari,
- env kurallari,
- test ve validasyon kontrol listesi

gibi bilesenleri tanimlar.

### 4.4 Import ve Validasyon Katmani

Bu katman gelecekteki runtime baglama surecini yonetecektir. Beklenen gorevleri:

- `plugin.yaml` parse etme,
- agent ve tool entrypoint'lerini dogrulama,
- env ve dependency ihtiyaclarini listeleme,
- risk seviyesini raporlama,
- paketi registry'ye kaydetme,
- aktif hale getirmeden once kullaniciya preview sunma

seklindedir.

## 5. Skill Tabanli Kontrat Yaklasimi

Onerilen yaklasimda `SKILL.md`, klasik anlamda "yardimci dokuman" degil, **programatik
uretim kontrati** olarak rol oynar. Bu kontratin iki yonlu etkisi vardir.

Birinci etki, LLM uretimini belirli kisitlara baglayarak ciktiyi standardize etmesidir.
Boylece modelin keyfi klasor yapisi, tutarsiz metadata ya da agent ve tool arasinda kopuk
referanslar uretme olasiligi azalir.

Ikinci etki, import katmaninin da ne beklemesi gerektigini netlestirmesidir. Cunku skill ile
belirlenen sema, daha sonra runtime tarafinda manifest parser, tool loader ve registry katmani
icin resmi bir giris formatina donusur.

Bu nedenle `SKILL.md`, yalnizca LLM'i yonlendiren bir prompt artefakti degil; ayni zamanda
gelecekteki plugin ekosisteminin semantik protokoludur.

### 5.1 Paket Tipleri

**Tool Pack:** Sadece tool saglar. Mevcut agent'larin kapasitesini genisletmek icin idealdir.

**Agent Bundle:** Config tabanli ajan + secili tool listesi saglar. Varsayilan ve onerilen
paket tipidir.

**Runtime Pack:** Ozel Python submodel mantigi gerektiren, ileri seviye ve daha riskli
paket tipidir.

Bu ayrim, farkli teknik yetkinlik duzeyleri icin farkli giris noktalarina izin verir.

### 5.2 Deterministik Dosya Yapisi

Her paketin asgari olarak `plugin.yaml`, `README.md`, `env.example`, `tools/`, `agents/`,
`prompts/` ve `tests/` bilesenlerine sahip olmasi istenir. Bu sayede hem insan incelemesi
hem de otomatik validasyon ayni sabit giris noktalari uzerinden calisabilir.

### 5.3 Tool Kontrati

Tool'lar icin tekil fonksiyon export'u, ad eslesmesi, tip anotasyonu ve yan etki sinirlari
tanimlanmistir. Bu, LLM tarafindan uretilebilecek daginik veya side-effect agir kodun
azaltilmasina yardimci olur.

### 5.4 Agent Manifesti

Config-driven agent tanimi; model secimi, system prompt yolu, tool listesi, memory araclari
ve etiketler gibi alanlarla desteklenir. Boylece yeni bir uzman ajan, mevcut orchestrator'a
uyumlu bir metadata ile tarif edilir.

## 6. Arastirma Hipotezleri

Bu yaklasim icin asagidaki hipotezler kurulabilir:

**H1:** Skill tabanli kontrat ile yonlendirilen LLM'ler, serbest formatta uretilen paketlere
gore daha yuksek ilk denemede gecerli paket uretme oranina sahiptir.

**H2:** Skill tabanli paket uretimi, eksik manifest, bozuk dosya yapisi ve uydurma tool ismi
gibi yapisal hatalari anlamli bicimde azaltir.

**H3:** Skill tabanli paketler, orkestrasyon sistemine baglanmadan once daha az manuel
duzeltme gerektirir.

**H4:** Skill tabanli uretilmis bundle'larin import sonrasi gorev basari orani, serbest
formatta uretilmis bundle'lardan daha yuksektir.

**H5:** Paket tipi ayrimi (`Tool Pack`, `Agent Bundle`, `Runtime Pack`), son kullanici ile
gelistirici arasindaki teknik esigi dusurur ve farkli yetkinlik profillerinde daha yuksek
kullanilabilirlik saglar.

## 7. Deney Tasarimi

### 7.1 Karsilastirma Kurulumu

Uc ana deney grubu kurgulanabilir:

1. **Serbest Uretim Grubu:** LLM'den yalnizca dogal dil ile bundle uretmesi istenir.
2. **Dokumantasyon Grubu:** LLM'e yalnizca genel teknik gereksinimler verilir.
3. **Skill Tabanli Grup:** LLM'e resmi `SKILL.md` verilerek bundle uretmesi istenir.

### 7.2 Gorevler

Her grup icin benzer zorlukta su gorevler verilebilir:

- yeni bir haber cekme tool'u uretmek,
- yeni bir content agent bundle'i uretmek,
- memory okuyan bir social analysis agent'i tanimlamak,
- env gerektiren bir dis API tool'u eklemek,
- prompt + manifest + tool uyumu olan import edilebilir bir bundle hazirlamak.

### 7.3 Olcumler

Nicel olculer:

- first-pass valid package rate
- import success rate
- schema compliance score
- manual correction count
- time-to-integration
- unresolved dependency count
- hallucinated tool name count

Nitel olculer:

- dosya yapisinin okunabilirligi
- manifestlerin anlasilabilirligi
- agent ve tool arasindaki tutarlilik
- son kullanici tarafindan algilanan kurulum kolayligi

### 7.4 Sonraki Asama Olcumu

Import edilen paketler daha sonra gercek gorevlerde de olculmelidir:

- agent gorevi tamamlayabiliyor mu,
- yalnizca tanimlandigi tool'lari kullaniyor mu,
- memory policy'ye uyuyor mu,
- hata durumlarinda beklenen sinirlarda kaliyor mu.

## 8. Tartisma

Bu calismanin onemli bir iddiasi, LLM ekosistemlerinde standardizasyonun yalnizca runtime
katmaninda degil, **uretim asamasinda** da kurulmasi gerektigidir. Geleneksel yazilim
muhendisliginde API semalari, interface'ler ve package manager'lar nasil birlikte
calisabilirligi sagliyorsa, agent ekosistemlerinde de benzer bir role `SKILL.md` gibi
kontrat belgeleri ustlenebilir.

Bu yaklasim ayrica no-code ve low-code agent tasarimi alanina da yeni bir katkida bulunur.
Cunku burada kullanici agent'i dogrudan elle kodlamaz; fakat tamamen serbest de birakilmaz.
Onun yerine, standardize edilmis bir uretim protokolu kullanan ikinci bir zekaya is devreder.
Bu model, insan-LMM-LMM isbirliginin dikkat cekici bir ornegidir.

Ticari acidan bakildiginda bu fikir, yalnizca "agent builder" degil, **agent marketplace**
veya **importable bundle ecosystem** gibi daha buyuk bir urun stratejisine kapı acar.
Akademik acidan ise birlikte calisabilirlik, kontrat tabanli uretim ve moduler ajan
ekosistemleri gibi guncel arastirma alanlariyla kesismektedir.

## 9. Sinirliliklar

Bu calismanin bazi sinirliliklari vardir:

1. Skill tabanli kontrat, modeli tamamen hatasiz hale getirmez; yalnizca hata uzayini daraltir.
2. Runtime Pack gibi ileri seviye paketlerde guvenlik ve sandbox ihtiyaci daha belirgindir.
3. Paket formatinin cok katı hale gelmesi yaratici esnekligi azaltabilir.
4. Import validasyonu guclu olmadigi surece tek basina `SKILL.md` yeterli olmaz.
5. Paket dogrulugu ile gercek gorev basarisi her zaman ayni sey degildir; iyi paketlenen bir
   agent yine de zayif davranis sergileyebilir.

Bu nedenle skill tabanli kontrat, tek basina cozum degil; **uretim standardi + import
validasyonu + runtime guardrails** ucgeninin ilk bilesenidir.

## 10. Etik ve Guvenlik Boyutu

Disaridan import edilen tool ve agent'larin calisma zamani riskleri goz ardi edilmemelidir.
Ozellikle Python tabanli custom tool'lar dosya sistemi, ag erisimi veya otomasyon yuzeyleri
uzerinden beklenmeyen etkiler olusturabilir. Bu nedenle:

- risk seviyelendirmesi,
- dependency ve env gorunurlugu,
- trusted vs sandboxed package ayrimi,
- acik aktiflestirme adimi,
- audit log ve action trace

gibi mekanizmalar import mimarisinin ayrilmaz parcasi olmalidir.

## 11. Sonuc

Bu makalede, LLM tabanli agent ekosistemleri icin skill tabanli kontratlarla disaridan
import edilebilir ajan paketleri uretme yaklasimi sunulmustur. Onerilen model, sadece yeni
ajan tanimlamayi degil, bu ajanlari birlikte calisabilir, parse edilebilir ve orchestration
katmanina baglanabilir yapilar olarak ele alir. `SKILL.md` burada yardimci bir prompttan
daha fazlasi olarak, agent bundle uretiminin resmi protokolu haline gelir.

Bu cerceve hem akademik olarak birlikte calisabilir agent sistemleri, kontrat tabanli kod
uretimi ve no-code agent engineering alanlarina katkida bulunabilir; hem de ticari olarak
Agent Studio benzeri platformlari daha acik, moduler ve olceklenebilir hale getirebilir.

Gelecek calismalarin odagi, paket import preview, otomatik validasyon, plugin registry ve
runtime sandbox katmanlarini tamamlarken; skill tabanli kontratin gercekten entegrasyon
basarisini ne kadar artirdigini deneysel olarak gostermek olmalidir.

## 12. Olası Genisletmeler

Bu taslak asagidaki yonlerde genisletilebilir:

- IEEE veya ACM formatina donusturme
- Ingilizce versiyon olusturma
- literatur taramasi ve ilgili calismalar bolumu ekleme
- deney protokolu ve benchmark veri seti ekleme
- Agent Studio import mekanizmasi tamamlandiktan sonra gercek sonuclarla guncelleme

