"""
Örnek Skill Modülü — Hava Durumu.

Bu dosya skill plugin sisteminin nasıl çalıştığını gösterir.
Yeni bir skill eklemek için:
  1. Bu dosya gibi bir Python modülü yazın
  2. araclar/skills/ dizinine bir .yaml tanım dosyası ekleyin
  3. Uygulamayı yeniden başlatın (veya skill_loader.load_skills() çağırın)
"""


def hava_durumu_sorgula(sehir: str) -> str:
    """
    Belirtilen şehir için anlık hava durumu bilgisi çeker.
    
    Args:
        sehir: Hava durumu sorgulanacak şehir adı (Türkçe).
    
    Returns:
        Hava durumu özeti.
    """
    # Bu örnek bir stub'dır. Gerçek implementasyonda bir API çağrısı yapılır.
    return f"🌤️ {sehir} için hava durumu: Açık, 22°C (Bu bir örnek skill çıktısıdır)"
