"""
Araçlar — Tüm core tool'ların merkezi import noktası.

Tool grupları:
  BASE_ARACLAR      → BaseModel'in doğrudan kullandığı
  SISTEM_ARACLARI   → sistem_agent (workspace, terminal, bellek)
  ARAMA_ARACLARI    → arastirma_agent (web araması + workspace)
  KOD_ARACLARI      → kod_agent (terminal, workspace)
  BROWSER_ARACLARI  → browser_agent (Selenium web etkileşimi)
"""

from .sistem_araclari import (
    get_system_status as sistem_get_system_status,
    terminal_komut_calistir,
)
from .workspace_araclari import (
    workspace_yaz,
    workspace_oku,
    workspace_sonunu_oku,
    workspace_listele,
    workspace_sil,
    workspace_ekle,
)
from .bellek_araclari import bellek_yaz, bellek_oku, bellek_sil, rol_oku, rol_guncelle


def _missing_tool(tool_name: str, error: Exception):
    """Opsiyonel bağımlılık eksik olduğunda yer tutucu tool üretir."""

    def _tool(*args, **kwargs):
        return f"❌ '{tool_name}' aracı kullanılamıyor: {error}"

    _tool.__name__ = tool_name
    _tool.__doc__ = f"Opsiyonel bağımlılık eksik olduğu için geçici olarak devre dışı: {error}"
    return _tool


try:
    from .arama_araclari import web_arama
except Exception as arama_import_error:
    web_arama = _missing_tool("web_arama", arama_import_error)


try:
    from .vlm_araclari import (
        take_screenshot,
        click_mouse,
        type_text,
        press_key,
        scroll_up,
        scroll_down,
        double_click_mouse,
        right_click_mouse,
        get_system_status as vlm_get_system_status,
        get_screenshot_bytes,
        look_closer,
        hover_mouse,
        get_pixel_color,
    )
except Exception as vlm_import_error:
    take_screenshot = _missing_tool("take_screenshot", vlm_import_error)
    click_mouse = _missing_tool("click_mouse", vlm_import_error)
    type_text = _missing_tool("type_text", vlm_import_error)
    press_key = _missing_tool("press_key", vlm_import_error)
    scroll_up = _missing_tool("scroll_up", vlm_import_error)
    scroll_down = _missing_tool("scroll_down", vlm_import_error)
    double_click_mouse = _missing_tool("double_click_mouse", vlm_import_error)
    right_click_mouse = _missing_tool("right_click_mouse", vlm_import_error)
    vlm_get_system_status = _missing_tool("get_system_status", vlm_import_error)
    get_screenshot_bytes = _missing_tool("get_screenshot_bytes", vlm_import_error)
    look_closer = _missing_tool("look_closer", vlm_import_error)
    hover_mouse = _missing_tool("hover_mouse", vlm_import_error)
    get_pixel_color = _missing_tool("get_pixel_color", vlm_import_error)


try:
    from .social_browser_workflow import (
        get_x_queue,
        get_browser_status,
        scan_x_page,
        scan_x_notifications,
        snapshot_x_feed,
        save_x_market_snapshot,
        update_queue_item,
        send_x_reply,
        publish_x_post,
        reply_to_x_post,
        mark_queue_item,
    )
except Exception as social_import_error:
    get_x_queue = _missing_tool("get_x_queue", social_import_error)
    get_browser_status = _missing_tool("get_browser_status", social_import_error)
    scan_x_page = _missing_tool("scan_x_page", social_import_error)
    scan_x_notifications = _missing_tool("scan_x_notifications", social_import_error)
    snapshot_x_feed = _missing_tool("snapshot_x_feed", social_import_error)
    save_x_market_snapshot = _missing_tool("save_x_market_snapshot", social_import_error)
    update_queue_item = _missing_tool("update_queue_item", social_import_error)
    send_x_reply = _missing_tool("send_x_reply", social_import_error)
    publish_x_post = _missing_tool("publish_x_post", social_import_error)
    reply_to_x_post = _missing_tool("reply_to_x_post", social_import_error)
    mark_queue_item = _missing_tool("mark_queue_item", social_import_error)


try:
    from .browser_araclari import (
        browser_baslat,
        browser_baglan,
        browser_chrome_baslat,
        browser_git,
        browser_dom_oku,
        browser_hizli_durum_oku,
        browser_ilgili_bolumleri_getir,
        browser_bul,
        browser_click_text,
        browser_click_role,
        browser_click_id,
        browser_click_css,
        browser_type_placeholder,
        browser_type_id,
        browser_type_css,
        browser_enter_bas,
        browser_geri,
        browser_scroll,
        browser_select_sec,
        browser_deger_ata,
        browser_eleman_bekle,
        browser_bekle,
        browser_cookie_kaydet,
        browser_cookie_yukle,
        browser_yeni_sekme,
        browser_sekme_degistir,
        browser_sekme_listele,
        browser_sekme_kapat,
        browser_dosya_yukle,
        browser_screenshot,
        browser_vlm_yardim,
        browser_kapat,
    )
except Exception as browser_import_error:
    browser_baslat = _missing_tool("browser_baslat", browser_import_error)
    browser_baglan = _missing_tool("browser_baglan", browser_import_error)
    browser_chrome_baslat = _missing_tool("browser_chrome_baslat", browser_import_error)
    browser_git = _missing_tool("browser_git", browser_import_error)
    browser_dom_oku = _missing_tool("browser_dom_oku", browser_import_error)
    browser_hizli_durum_oku = _missing_tool("browser_hizli_durum_oku", browser_import_error)
    browser_ilgili_bolumleri_getir = _missing_tool("browser_ilgili_bolumleri_getir", browser_import_error)
    browser_bul = _missing_tool("browser_bul", browser_import_error)
    browser_click_text = _missing_tool("browser_click_text", browser_import_error)
    browser_click_role = _missing_tool("browser_click_role", browser_import_error)
    browser_click_id = _missing_tool("browser_click_id", browser_import_error)
    browser_click_css = _missing_tool("browser_click_css", browser_import_error)
    browser_type_placeholder = _missing_tool("browser_type_placeholder", browser_import_error)
    browser_type_id = _missing_tool("browser_type_id", browser_import_error)
    browser_type_css = _missing_tool("browser_type_css", browser_import_error)
    browser_enter_bas = _missing_tool("browser_enter_bas", browser_import_error)
    browser_geri = _missing_tool("browser_geri", browser_import_error)
    browser_scroll = _missing_tool("browser_scroll", browser_import_error)
    browser_select_sec = _missing_tool("browser_select_sec", browser_import_error)
    browser_deger_ata = _missing_tool("browser_deger_ata", browser_import_error)
    browser_eleman_bekle = _missing_tool("browser_eleman_bekle", browser_import_error)
    browser_bekle = _missing_tool("browser_bekle", browser_import_error)
    browser_cookie_kaydet = _missing_tool("browser_cookie_kaydet", browser_import_error)
    browser_cookie_yukle = _missing_tool("browser_cookie_yukle", browser_import_error)
    browser_yeni_sekme = _missing_tool("browser_yeni_sekme", browser_import_error)
    browser_sekme_degistir = _missing_tool("browser_sekme_degistir", browser_import_error)
    browser_sekme_listele = _missing_tool("browser_sekme_listele", browser_import_error)
    browser_sekme_kapat = _missing_tool("browser_sekme_kapat", browser_import_error)
    browser_dosya_yukle = _missing_tool("browser_dosya_yukle", browser_import_error)
    browser_screenshot = _missing_tool("browser_screenshot", browser_import_error)
    browser_vlm_yardim = _missing_tool("browser_vlm_yardim", browser_import_error)
    browser_kapat = _missing_tool("browser_kapat", browser_import_error)


try:
    from .skill_loader import load_skills, get_active_skills, list_skills
except Exception as skill_loader_import_error:
    _SKILL_LOADER_IMPORT_ERROR = skill_loader_import_error

    def load_skills() -> dict[str, dict]:
        print(f"⚠️ [Skill Loader] Devre dışı: {_SKILL_LOADER_IMPORT_ERROR}")
        return {}

    def get_active_skills(agent: str = None) -> list:
        return []

    def list_skills() -> list[dict]:
        return []


BASE_ARACLAR = [
    terminal_komut_calistir,
    workspace_yaz,
    workspace_oku,
    workspace_sonunu_oku,
    workspace_listele,
    rol_oku,
    rol_guncelle,
    get_browser_status,
    get_x_queue,
    scan_x_page,
    scan_x_notifications,
    snapshot_x_feed,
    save_x_market_snapshot,
    update_queue_item,
    send_x_reply,
    publish_x_post,
    reply_to_x_post,
    mark_queue_item,
]

SISTEM_ARACLARI = [
    terminal_komut_calistir,
    sistem_get_system_status,
    workspace_yaz,
    workspace_oku,
    workspace_sonunu_oku,
    workspace_listele,
    workspace_sil,
    workspace_ekle,
    bellek_yaz,
    bellek_oku,
    bellek_sil,
]

ARAMA_ARACLARI = [
    web_arama,
    workspace_yaz,
    workspace_oku,
    workspace_sonunu_oku,
    workspace_ekle,
    workspace_listele,
]

KOD_ARACLARI = [
    terminal_komut_calistir,
    workspace_yaz,
    workspace_oku,
    workspace_sonunu_oku,
    workspace_ekle,
]

VLM_ARACLARI = [
    take_screenshot,
    press_key,
    scroll_up,
    scroll_down,
    vlm_get_system_status,
    get_screenshot_bytes,
    look_closer,
    hover_mouse,
    get_pixel_color,
]

BROWSER_ARACLARI = [
    browser_baslat,
    browser_baglan,
    browser_chrome_baslat,
    browser_git,
    browser_dom_oku,
    browser_hizli_durum_oku,
    browser_ilgili_bolumleri_getir,
    browser_bul,
    browser_click_text,
    browser_click_role,
    browser_click_id,
    browser_click_css,
    browser_type_placeholder,
    browser_type_id,
    browser_type_css,
    browser_enter_bas,
    browser_geri,
    browser_scroll,
    browser_select_sec,
    browser_deger_ata,
    browser_eleman_bekle,
    browser_bekle,
    browser_cookie_kaydet,
    browser_cookie_yukle,
    browser_yeni_sekme,
    browser_sekme_degistir,
    browser_sekme_listele,
    browser_sekme_kapat,
    browser_dosya_yukle,
    browser_screenshot,
    browser_vlm_yardim,
    browser_kapat,
]

TUM_ARACLAR = BASE_ARACLAR

_loaded_skills = load_skills()

_AGENT_TOOL_MAP = {
    "base": BASE_ARACLAR,
    "sistem_agent": SISTEM_ARACLARI,
    "arastirma_agent": ARAMA_ARACLARI,
    "kod_agent": KOD_ARACLARI,
    "vlm_agent": VLM_ARACLARI,
    "browser_agent": BROWSER_ARACLARI,
}

for agent_name, tool_list in _AGENT_TOOL_MAP.items():
    skills = get_active_skills(agent=agent_name)
    if skills:
        tool_list.extend(skills)
        print(f"🧩 [Boot] {agent_name} için {len(skills)} skill enjekte edildi.")
