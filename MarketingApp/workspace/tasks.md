# Görev Planı: HEARTBEAT OTOMATİK SOSYAL MEDYA İZLEME

Bu, periyodik olarak tetiklenen bir sosyal medya izleme görevidir. Görevin başarılı bir şekilde tamamlanabilmesi için aktif hesapların ve gerekli kimlik doğrulama bilgilerinin (API anahtarları veya oturum bilgileri) tanımlanması gerekmektedir.

## Adımlar:
- [ ] 1. **Bellek ve Çalışma Alanı Kontrolü (@sistem_agent):** Yapılandırılmış sosyal medya hesapları, kimlik bilgileri ve izleme tercihleri için `bellek` ve `workspace/targets/` dizinlerinin kontrol edilmesi.
- [ ] 2. **Kimlik Doğrulama ve Oturum Açma (@browser_agent):** Tanımlanan aktif sosyal medya platformlarında oturum açma veya API bağlantılarını sağlama.
- [ ] 3. **Bildirimleri ve Etkileşimleri Toplama (@browser_agent / @arastirma_agent):** Hesaplara gelen son bildirimlerin taranması (beğeni, yorum, doğrudan mesaj vb.).
- [ ] 4. **Eşik Analizi (@sistem_agent):** Etkileşimlerin belirlenen eşiği (+10 beğeni, yorum, DM) aşıp aşmadığının analizi.
- [ ] 5. **Raporlama (@sistem_agent):** Önemli etkileşimlerin `reports/social_media_report.md` dosyasına kaydedilmesi ve Telegram üzerinden kullanıcıya bildirilmesi.

## Mevcut Durum:
Adım 1'de kalınmıştır. Aktif sosyal medya hesaplarına ait yapılandırma veya oturum bilgileri bellekte veya çalışma alanında bulunmamaktadır. Göreve devam edebilmek için hangi platformların (Twitter/X, Instagram, YouTube vb.) izleneceğinin ve bu platformlara erişim yönteminin (API veya yuksek seviyeli sosyal workflow araclari ile oturum) tanımlanması gerekmektedir.
