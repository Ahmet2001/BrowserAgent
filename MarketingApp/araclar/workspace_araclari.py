"""
Playground (Workspace) Araçları — Ajanın karmaşık görevlerde kullanacağı çalışma alanı.
Büyük veri analizlerinde (örn. 100 mail), çok adımlı görevlerde ara sonuçları
dosyalara kaydetmek ve parça parça okumak için kullan.
"""

import os

# Workspace dizini (proje kök dizininde)
WORKSPACE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "workspace"
)


def _ensure_workspace():
    """Workspace dizininin var olduğundan emin olur."""
    os.makedirs(WORKSPACE_DIR, exist_ok=True)


def _resolve_workspace_path(dosya_adi: str) -> tuple[str | None, str]:
    """Workspace içindeki güvenli relatif yolu ve tam yolu döndürür."""
    safe_path = os.path.normpath(dosya_adi).lstrip("/")
    if ".." in safe_path:
        return None, "❌ Hata: '..' kullanılarak üst dizine çıkılamaz."
    filepath = os.path.join(WORKSPACE_DIR, safe_path)
    return safe_path, filepath


def workspace_yaz(dosya_adi: str, icerik: str) -> str:
    """
    Workspace içine bir dosya yazar (mevcut içeriğin üzerine yazar).
    Büyük veri analizlerinde taslak veya ara sonuç kaydetmek için idealdir.

    Args:
        dosya_adi: Dosya adı (örn: 'analiz_sonucu.txt').
        icerik: Yazılacak içerik.
    """
    _ensure_workspace()
    safe_path, filepath_or_error = _resolve_workspace_path(dosya_adi)
    if safe_path is None:
        return filepath_or_error

    filepath = filepath_or_error
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(icerik)
        return f"✅ '{safe_path}' workspace'e kaydedildi ({len(icerik)} karakter)."
    except Exception as e:
        return f"❌ Workspace yazma hatası: {e}"


def workspace_ekle(dosya_adi: str, icerik: str) -> str:
    """
    Workspace içindeki mevcut bir dosyanın SONUNA içerik ekler (append modu).
    100 maili teker teker bir dosyaya biriktirmek gibi işlemlerde kullan.

    Args:
        dosya_adi: Hedef dosya adı.
        icerik: Eklenecek içerik.
    """
    _ensure_workspace()
    safe_path, filepath_or_error = _resolve_workspace_path(dosya_adi)
    if safe_path is None:
        return filepath_or_error

    filepath = filepath_or_error
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(icerik)
        return f"✅ '{safe_path}' dosyasına {len(icerik)} karakter eklendi."
    except Exception as e:
        return f"❌ Workspace ekleme hatası: {e}"


def workspace_oku(dosya_adi: str) -> str:
    """
    Workspace içindeki bir dosyayı okur.
    40.000 karakterden uzunsa ilk 40.000 karakter döndürülür.

    Args:
        dosya_adi: Okunacak dosyanın adı.
    """
    safe_path, filepath_or_error = _resolve_workspace_path(dosya_adi)
    if safe_path is None:
        return filepath_or_error

    filepath = filepath_or_error
    if not os.path.exists(filepath):
        return f"❌ '{safe_path}' workspace içinde bulunamadı."
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            icerik = f.read()
        if len(icerik) > 40000:
            return f"📄 '{safe_path}' (ilk 40.000/{len(icerik)} karakter):\n{icerik[:40000]}\n\n[... devamı kırpıldı ...]"
        return icerik
    except Exception as e:
        return f"❌ Workspace okuma hatası: {e}"


def workspace_sonunu_oku(dosya_adi: str, karakter: int = 6000) -> str:
    """
    Workspace içindeki bir dosyanın son kısmını okur.
    Log, aksiyon geçmişi veya dönen durum dosyalarında context'i küçük tutmak için kullan.

    Args:
        dosya_adi: Okunacak dosyanın adı.
        karakter: Sondan okunacak karakter sayısı.
    """
    safe_path, filepath_or_error = _resolve_workspace_path(dosya_adi)
    if safe_path is None:
        return filepath_or_error

    filepath = filepath_or_error
    if not os.path.exists(filepath):
        return f"❌ '{safe_path}' workspace içinde bulunamadı."

    try:
        karakter = max(200, min(int(karakter), 40000))
    except Exception:
        karakter = 6000

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            icerik = f.read()

        if len(icerik) <= karakter:
            return icerik

        return (
            f"📄 '{safe_path}' (son {karakter}/{len(icerik)} karakter):\n"
            f"[... başı kırpıldı ...]\n{icerik[-karakter:]}"
        )
    except Exception as e:
        return f"❌ Workspace sonunu okuma hatası: {e}"


def workspace_listele() -> str:
    """Workspace içindeki tüm dosyaları boyutlarıyla listeler."""
    _ensure_workspace()
    try:
        files = sorted(os.listdir(WORKSPACE_DIR))
        if not files:
            return "📂 Workspace şu anda boş."
        satirlar = [f"📂 Workspace ({WORKSPACE_DIR}):"]
        for f in files:
            tam_yol  = os.path.join(WORKSPACE_DIR, f)
            boyut    = os.path.getsize(tam_yol)
            boyut_str = f"{boyut} B" if boyut < 1024 else f"{boyut/1024:.1f} KB"
            satirlar.append(f"  📄 {f} ({boyut_str})")
        return "\n".join(satirlar)
    except Exception as e:
        return f"❌ Listeleme hatası: {e}"


def workspace_sil(dosya_adi: str) -> str:
    """
    Workspace içindeki bir dosyayı siler.

    Args:
        dosya_adi: Silinecek dosyanın adı.
    """
    safe_path, filepath_or_error = _resolve_workspace_path(dosya_adi)
    if safe_path is None:
        return filepath_or_error

    filepath = filepath_or_error
    if not os.path.exists(filepath):
        return f"❌ '{safe_path}' workspace'de bulunamadı."
    try:
        os.remove(filepath)
        return f"✅ '{safe_path}' workspace'den silindi."
    except Exception as e:
        return f"❌ Silme hatası: {e}"
