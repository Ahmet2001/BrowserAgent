import os
import json
import time
import subprocess
import shutil
import re
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel as PydanticBaseModel
from typing import Optional, Dict, Any

from MarketingApp.enviroments.automation_runtime import (
    release_automation,
    try_acquire_automation,
)
from MarketingApp.enviroments import heartbeat as heartbeat_runtime

app = FastAPI()

_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("PANEL_ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global BaseModel instance
_base_model = None
PANEL_DIR = os.path.dirname(os.path.abspath(__file__))
# Absolute path to workspace
FILE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = os.path.join(FILE_DIR, "workspace")
TARGETS_DIR = os.path.join(WORKSPACE_DIR, "targets")
ROLE_FILE = os.path.join(WORKSPACE_DIR, "role.md")

# Ensure directories exist
os.makedirs(TARGETS_DIR, exist_ok=True)
for d in ["code", "drafts", "reports", "assets", ".system"]:
    os.makedirs(os.path.join(WORKSPACE_DIR, d), exist_ok=True)


def _resolve_safe_path(base_dir: str, user_path: str) -> str:
    """İstenen yolun hedef dizin altında kaldığını doğrular."""
    if not user_path:
        raise HTTPException(status_code=400, detail="Path boş olamaz")

    base_real = os.path.realpath(base_dir)
    candidate = os.path.realpath(os.path.join(base_dir, user_path))

    if os.path.commonpath([base_real, candidate]) != base_real:
        raise HTTPException(status_code=400, detail="Path izin verilen dizin dışında")

    return candidate


def _sanitize_filename(name: str) -> str:
    """Upload ve target isimlerinde dizin kaçışını engeller."""
    cleaned = os.path.basename((name or "").strip())
    if not cleaned or cleaned in {".", ".."}:
        raise HTTPException(status_code=400, detail="Geçersiz dosya adı")
    return cleaned

class ContentUpdate(PydanticBaseModel):
    content: str

class MemoryWrite(PydanticBaseModel):
    category: str
    key: str
    value: str

class MemoryDelete(PydanticBaseModel):
    category: str
    key: str

class CodeExecute(PydanticBaseModel):
    filename: str
    input_data: Optional[str] = ""

class TargetSource(PydanticBaseModel):
    type: str  # 'url' or 'text'
    name: str
    content: str

class SocialScanRequest(PydanticBaseModel):
    limit: int = 20

class SocialReplyUpdate(PydanticBaseModel):
    text: str

class SocialQueueStatusUpdate(PydanticBaseModel):
    status: str
    note: str = ""

class SocialDraftRequest(PydanticBaseModel):
    tone: Optional[str] = "samimi, kısa ve doğal"


class SocialBrowserLaunchRequest(PydanticBaseModel):
    headless: bool = False
    restart_if_needed: bool = True


class HeartbeatToggleRequest(PydanticBaseModel):
    enabled: bool

def set_base_model(bm):
    global _base_model
    _base_model = bm


def _busy_http_detail(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "message": "Otomasyon meşgul",
        "busy_owner": snapshot.get("owner") or "",
        "busy_label": snapshot.get("label") or snapshot.get("job_id") or "",
        "busy_started_at": snapshot.get("started_at"),
        "busy_source": snapshot.get("source") or "",
    }


async def _acquire_panel_mutation(label: str, source: str) -> str:
    job_id = f"panel-{source}-{int(time.time() * 1000)}"
    acquired, snapshot = await try_acquire_automation(
        "panel",
        job_id=job_id,
        label=label,
        source=source,
    )
    if not acquired:
        raise HTTPException(status_code=409, detail=_busy_http_detail(snapshot))
    return job_id


def _load_social_workflow():
    try:
        from MarketingApp.araclar.social_browser_workflow import (
            get_browser_status,
            get_x_queue,
            launch_x_browser,
            mark_queue_item,
            scan_x_page,
            send_x_reply,
            update_queue_item,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sosyal workflow yüklenemedi: {e}")

    return {
        "get_browser_status": get_browser_status,
        "get_x_queue": get_x_queue,
        "launch_x_browser": launch_x_browser,
        "mark_queue_item": mark_queue_item,
        "scan_x_page": scan_x_page,
        "send_x_reply": send_x_reply,
        "update_queue_item": update_queue_item,
    }


def _build_social_snapshot() -> dict[str, Any]:
    try:
        workflow = _load_social_workflow()
        return {
            "browser": workflow["get_browser_status"](),
            "queue": workflow["get_x_queue"](),
        }
    except HTTPException as exc:
        return {
            "browser": {
                "ready": False,
                "title": "",
                "url": "",
                "window_count": 0,
                "error": exc.detail,
            },
            "queue": {
                "platform": "x",
                "updated_at": "",
                "items": [],
            },
        }


def _extract_model_text(result: Any) -> str:
    if isinstance(result, tuple) and len(result) >= 4:
        _audio, transcript, direct_texts, cevap_metinleri = result
        texts = []
        if isinstance(cevap_metinleri, list):
            texts.extend([str(item).strip() for item in cevap_metinleri if str(item).strip()])
        if isinstance(direct_texts, list):
            texts.extend([str(item).strip() for item in direct_texts if str(item).strip()])
        if transcript:
            texts.append(str(transcript).strip())
        if texts:
            return texts[0]
    if isinstance(result, str):
        return result.strip()
    return ""


def _get_heartbeat_config_path() -> str:
    return os.path.join(FILE_DIR, "config", "heartbeat_config.yaml")


def _read_heartbeat_content() -> str:
    config_path = _get_heartbeat_config_path()
    if not os.path.exists(config_path):
        return ""
    with open(config_path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_heartbeat_meta(content: str) -> dict[str, Any]:
    return heartbeat_runtime.summarize_config_content(content)


async def _generate_social_reply(item: dict[str, Any], tone: str) -> str:
    author = item.get("author_name") or item.get("author_handle") or "kullanici"
    comment = (item.get("text") or "").strip()
    if not comment:
        raise HTTPException(status_code=400, detail="Taslak üretmek için yorum metni bulunamadı")

    if _base_model:
        prompt = (
            "Asagidaki sosyal medya yorumuna Turkce bir cevap taslagi yaz. "
            "Cevap en fazla 2 cumle olsun, dogal dursun, karsi tarafin yorumuna direkt baglansin, "
            "fazla kurumsal olmasin, hashtag ve emoji kullanma. "
            f"Istenen ton: {tone or 'samimi, kısa ve doğal'}.\n\n"
            f"Yorum sahibi: {author}\n"
            f"Yorum: {comment}\n\n"
            "Sadece gonderilecek cevap metnini dondur."
        )
        try:
            result = await _base_model.text_query(prompt)
            generated = _extract_model_text(result)
            if generated:
                return generated
        except Exception:
            pass

    if "?" in comment:
        return "Tesekkurler, bunu not aldik. Biraz daha detay paylasirsan net yardimci olabiliriz."
    return "Yorumun icin tesekkurler, bunu gormek guzel. Istersen detayini biraz daha acabiliriz."


@app.get("/panel", include_in_schema=False)
@app.get("/panel/", include_in_schema=False)
async def serve_panel():
    return FileResponse(os.path.join(PANEL_DIR, "index.html"))


@app.get("/panel/{asset_path:path}", include_in_schema=False)
async def serve_panel_assets(asset_path: str):
    safe_asset_path = _resolve_safe_path(PANEL_DIR, asset_path)
    allowed_exts = {".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"}
    if os.path.splitext(safe_asset_path)[1].lower() not in allowed_exts:
        raise HTTPException(status_code=404, detail="Panel asset not found")
    if not os.path.exists(safe_asset_path) or os.path.isdir(safe_asset_path):
        raise HTTPException(status_code=404, detail="Panel asset not found")
    return FileResponse(safe_asset_path)

@app.get("/api/system/status")
async def get_status():
    if not _base_model:
        return {"status": "Offline", "uptime": 0}
    return {
        "status": "Online",
        "uptime": int(time.time() - getattr(_base_model, 'start_time', time.time())),
        "model": getattr(_base_model, 'model', 'Unknown')
    }

@app.get("/api/hierarchy")
async def get_hierarchy():
    if not _base_model:
        return {"tools": [], "submodels": []}
    return _base_model.get_hierarchy()


@app.get("/api/panel/bootstrap")
async def get_panel_bootstrap():
    """Panelin ilk açılışında ihtiyaç duyduğu temel verileri tek istekte döner."""
    return {
        "system": await get_status(),
        "hierarchy": await get_hierarchy(),
        "logs": await get_logs(),
        "stats": await get_stats(),
        "pending_actions": await get_pending_actions(),
        "skills": await get_skills_list(),
        "heartbeat": await get_heartbeat_config(),
        "heartbeat_status": await get_heartbeat_status(),
        "heartbeat_jobs": await get_heartbeat_jobs(),
        "social": _build_social_snapshot(),
    }

@app.post("/api/agents/{name}/toggle")
async def toggle_agent(name: str):
    if not _base_model or not hasattr(_base_model, 'active_agents'):
        raise HTTPException(status_code=500, detail="BaseModel not ready")
    
    if name in _base_model.active_agents:
        current = _base_model.active_agents[name]
        _base_model.active_agents[name] = not current
        return {"name": name, "active": not current}
    raise HTTPException(status_code=404, detail="Agent not found")

@app.post("/api/tools/{name}/toggle")
async def toggle_tool(name: str):
    if not _base_model or not hasattr(_base_model, 'active_tools'):
        raise HTTPException(status_code=500, detail="BaseModel not ready")
    
    if name in _base_model.active_tools:
        current = _base_model.active_tools[name]
        _base_model.active_tools[name] = not current
        return {"name": name, "active": not current}
    raise HTTPException(status_code=404, detail="Tool not found")

# --- SMART MEMORY ---
@app.get("/api/memory/raw")
async def get_memory_raw():
    from MarketingApp.araclar.bellek_araclari import _yukle_bellek
    return _yukle_bellek()

@app.post("/api/memory/raw")
async def set_memory_raw(data: Dict[str, Any]):
    from MarketingApp.araclar.bellek_araclari import _kaydet_bellek
    _kaydet_bellek(data)
    return {"status": "success"}

@app.post("/api/memory/write")
async def write_memory(data: MemoryWrite):
    from MarketingApp.araclar.bellek_araclari import bellek_yaz
    res = bellek_yaz(data.category, data.key, data.value)
    return {"status": "success", "message": res}

@app.post("/api/memory/delete")
async def delete_memory(data: MemoryDelete):
    from MarketingApp.araclar.bellek_araclari import bellek_sil
    res = bellek_sil(data.category, data.key)
    return {"status": "success", "message": res}

@app.get("/api/persona")
async def get_persona():
    if os.path.exists(ROLE_FILE):
        with open(ROLE_FILE, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    return {"content": ""}

@app.post("/api/persona")
async def update_persona(data: ContentUpdate):
    with open(ROLE_FILE, "w", encoding="utf-8") as f:
        f.write(data.content)
    return {"status": "success"}

# --- WORKSPACE & CODE SANDBOX ---

@app.get("/api/workspace/tree")
async def get_workspace_tree():
    def build_tree(path):
        name = os.path.basename(path)
        # Avoid relpath issues on network drives by using string replace
        rel_path = path.replace(WORKSPACE_DIR, "").lstrip(os.sep).lstrip("/")
        item = {"name": name, "path": rel_path if rel_path else "."}
        if os.path.isdir(path):
            item["type"] = "directory"
            item["children"] = [build_tree(os.path.join(path, f)) for f in os.listdir(path)]
        else:
            item["type"] = "file"
            item["size"] = os.path.getsize(path)
        return item
    
    if not os.path.exists(WORKSPACE_DIR): return []
    try:
        nodes = [build_tree(os.path.join(WORKSPACE_DIR, f)) for f in os.listdir(WORKSPACE_DIR)]
        return nodes
    except Exception as e:
        return [{"name": "Error", "type": "file", "path": str(e)}]

@app.get("/api/workspace/read")
async def read_file(path: str):
    full_path = _resolve_safe_path(WORKSPACE_DIR, path)
    if os.path.exists(full_path) and not os.path.isdir(full_path):
        with open(full_path, "r", encoding="utf-8") as f:
            return {"content": f.read()}
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/workspace/execute")
async def execute_code(data: CodeExecute):
    # Kısıtlı sandbox
    full_path = _resolve_safe_path(WORKSPACE_DIR, data.filename)
    if not os.path.exists(full_path) or not full_path.endswith('.py'):
        raise HTTPException(status_code=400, detail="Sadece .py dosyaları çalıştırılabilir.")
    
    try:
        # Use python from env or direct path if needed
        py_cmd = "python"
        process = subprocess.Popen(
            [py_cmd, full_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(full_path)
        )
        stdout, stderr = process.communicate(input=data.input_data, timeout=30)
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": process.returncode
        }
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": process.returncode,
            "error": "Kod çalıştırma zaman aşımına uğradı (30s)"
        }
    except Exception as e:
        return {"error": str(e)}

# --- TARGETS ---
@app.post("/api/workspace/targets/upload")
async def upload_target(file: UploadFile = File(...)):
    safe_name = _sanitize_filename(file.filename)
    file_path = _resolve_safe_path(TARGETS_DIR, safe_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "success", "filename": safe_name}

@app.post("/api/workspace/targets/add")
async def add_target_source(data: TargetSource):
    if data.type not in {"url", "text"}:
        raise HTTPException(status_code=400, detail="Target type sadece 'url' veya 'text' olabilir")

    ext = ".url" if data.type == "url" else ".txt"
    base_name = _sanitize_filename(data.name)
    filename = base_name + ext if not base_name.endswith(ext) else base_name
    file_path = _resolve_safe_path(TARGETS_DIR, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data.content)
    return {"status": "success", "filename": filename}

# --- OTHER ---
@app.get("/api/logs")
async def get_logs():
    if not _base_model or not hasattr(_base_model, 'logs'): return []
    return _base_model.logs[-50:]

@app.get("/api/stats")
async def get_stats():
    if not _base_model or not hasattr(_base_model, 'metrics'): return []
    return _base_model.metrics[-20:]

@app.get("/api/actions/pending")
async def get_pending_actions():
    if not _base_model or not hasattr(_base_model, 'pending_actions'): return []
    return [
        {"id": k, "description": v["description"]}
        for k, v in _base_model.pending_actions.items()
        if v["status"] == "pending"
    ]

@app.post("/api/actions/{action_id}/{decision}")
async def decide_action(action_id: str, decision: str):
    if not _base_model or action_id not in _base_model.pending_actions:
        raise HTTPException(status_code=404, detail="Action not found")
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="Decision 'approve' veya 'reject' olmalı")
    _base_model.pending_actions[action_id]["status"] = "approved" if decision == "approve" else "rejected"
    _base_model.pending_actions[action_id]["event"].set()
    return {"status": "success"}

# --- SKILL PLUGIN SİSTEMİ ---

@app.get("/api/skills")
async def get_skills_list():
    """Tüm yüklü skill'leri listeler."""
    from MarketingApp.araclar.skill_loader import list_skills
    return list_skills()

@app.post("/api/skills/{name}/toggle")
async def toggle_skill(name: str):
    """Bir skill'i etkinleştirir veya devre dışı bırakır."""
    from MarketingApp.araclar.skill_loader import get_skills, enable_skill, disable_skill
    skills = get_skills()
    if name not in skills:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' bulunamadı")
    
    if skills[name]["enabled"]:
        disable_skill(name)
        return {"name": name, "enabled": False}
    else:
        success = enable_skill(name)
        return {"name": name, "enabled": success}

@app.post("/api/skills/reload")
async def reload_skills():
    """Tüm skill'leri yeniden yükler (hot-reload)."""
    from MarketingApp.araclar.skill_loader import load_skills
    loaded = load_skills()
    return {"status": "success", "count": len(loaded)}

# --- HEARTBEAT ---

@app.get("/api/heartbeat/config")
async def get_heartbeat_config():
    """Heartbeat yapılandırmasını döner."""
    content = _read_heartbeat_content()
    return {
        "content": content,
        **_parse_heartbeat_meta(content),
    }

@app.post("/api/heartbeat/config")
async def update_heartbeat_config(data: ContentUpdate):
    """Heartbeat yapılandırmasını günceller."""
    try:
        heartbeat_runtime.parse_config_content(data.content)
    except heartbeat_runtime.HeartbeatConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    config_path = _get_heartbeat_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(data.content)

    runtime_error = None
    try:
        await heartbeat_runtime.reload_heartbeat_service(reason="api_config_update")
    except RuntimeError as exc:
        runtime_error = str(exc)
    except heartbeat_runtime.HeartbeatConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "success",
        "runtime_error": runtime_error,
        **_parse_heartbeat_meta(data.content),
    }


@app.post("/api/heartbeat/toggle")
async def toggle_heartbeat(data: HeartbeatToggleRequest):
    """Heartbeat'i panelden hızlıca açıp kapatır."""
    content = _read_heartbeat_content()
    updated_content = heartbeat_runtime.set_enabled_in_content(content, data.enabled)
    try:
        heartbeat_runtime.parse_config_content(updated_content)
    except heartbeat_runtime.HeartbeatConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    config_path = _get_heartbeat_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(updated_content)

    runtime_error = None
    try:
        await heartbeat_runtime.reload_heartbeat_service(reason="api_toggle")
    except RuntimeError as exc:
        runtime_error = str(exc)
    except heartbeat_runtime.HeartbeatConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "success",
        "content": updated_content,
        "runtime_error": runtime_error,
        **_parse_heartbeat_meta(updated_content),
    }


@app.get("/api/heartbeat/status")
async def get_heartbeat_status():
    return heartbeat_runtime.get_heartbeat_status_snapshot()


@app.get("/api/heartbeat/jobs")
async def get_heartbeat_jobs():
    return heartbeat_runtime.get_heartbeat_jobs_snapshot()


@app.post("/api/heartbeat/reload")
async def reload_heartbeat():
    try:
        status = await heartbeat_runtime.reload_heartbeat_service(reason="api_reload")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except heartbeat_runtime.HeartbeatConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "status": "success",
        "heartbeat_status": status,
        "heartbeat_jobs": heartbeat_runtime.get_heartbeat_jobs_snapshot(),
    }


@app.post("/api/heartbeat/jobs/{job_id}/pause")
async def pause_heartbeat_job_endpoint(job_id: str):
    try:
        job = await heartbeat_runtime.pause_heartbeat_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Heartbeat job bulunamadi")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"status": "success", "job": job}


@app.post("/api/heartbeat/jobs/{job_id}/resume")
async def resume_heartbeat_job_endpoint(job_id: str):
    try:
        job = await heartbeat_runtime.resume_heartbeat_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Heartbeat job bulunamadi")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"status": "success", "job": job}


@app.post("/api/heartbeat/jobs/{job_id}/run")
async def run_heartbeat_job_endpoint(job_id: str):
    try:
        result = await heartbeat_runtime.run_heartbeat_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Heartbeat job bulunamadi")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return result

# --- SOCIAL BROWSER WORKFLOW ---

@app.get("/api/social/browser/status")
async def get_social_browser_status():
    workflow = _load_social_workflow()
    return workflow["get_browser_status"]()


@app.post("/api/social/browser/launch")
async def launch_social_browser(data: SocialBrowserLaunchRequest):
    lease_id = await _acquire_panel_mutation("Panel tarayici baslatma", "social_browser_launch")
    workflow = _load_social_workflow()
    try:
        return workflow["launch_x_browser"](
            headless=data.headless,
            restart_if_needed=data.restart_if_needed,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Tarayici baslatilamadi: {e}")
    finally:
        await release_automation("panel", job_id=lease_id)


@app.get("/api/social/x/queue")
async def get_social_x_queue():
    workflow = _load_social_workflow()
    return workflow["get_x_queue"]()


@app.post("/api/social/x/scan")
async def social_scan_x_page(data: SocialScanRequest):
    lease_id = await _acquire_panel_mutation("Panel X tarama", "social_x_scan")
    workflow = _load_social_workflow()
    limit = max(1, min(int(data.limit or 20), 50))
    try:
        return workflow["scan_x_page"](limit=limit)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"X sayfasi taranamadi: {e}")
    finally:
        await release_automation("panel", job_id=lease_id)


@app.post("/api/social/x/queue/{queue_id}/draft")
async def social_generate_x_draft(queue_id: str, data: SocialDraftRequest):
    lease_id = await _acquire_panel_mutation("Panel taslak uretimi", "social_x_draft")
    workflow = _load_social_workflow()
    try:
        queue = workflow["get_x_queue"]()
        item = next((entry for entry in queue.get("items", []) if entry.get("queue_id") == queue_id), None)
        if not item:
            raise HTTPException(status_code=404, detail="Queue item bulunamadi")

        draft_text = await _generate_social_reply(item, data.tone or "")
        updated = workflow["update_queue_item"](queue_id, draft_reply=draft_text, status="drafted")
        return {"status": "success", "item": updated, "draft": draft_text}
    finally:
        await release_automation("panel", job_id=lease_id)


@app.post("/api/social/x/queue/{queue_id}/update")
async def social_update_x_draft(queue_id: str, data: SocialReplyUpdate):
    lease_id = await _acquire_panel_mutation("Panel taslak guncelleme", "social_x_update")
    workflow = _load_social_workflow()
    try:
        status = "drafted" if data.text.strip() else "new"
        item = workflow["update_queue_item"](queue_id, draft_reply=data.text, status=status)
        return {"status": "success", "item": item}
    except KeyError:
        raise HTTPException(status_code=404, detail="Queue item bulunamadi")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Taslak guncellenemedi: {e}")
    finally:
        await release_automation("panel", job_id=lease_id)


@app.post("/api/social/x/queue/{queue_id}/status")
async def social_mark_x_queue_item(queue_id: str, data: SocialQueueStatusUpdate):
    lease_id = await _acquire_panel_mutation("Panel queue durum guncelleme", "social_x_status")
    workflow = _load_social_workflow()
    try:
        item = workflow["mark_queue_item"](queue_id, data.status, note=data.note)
        return {"status": "success", "item": item}
    except KeyError:
        raise HTTPException(status_code=404, detail="Queue item bulunamadi")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Queue item guncellenemedi: {e}")
    finally:
        await release_automation("panel", job_id=lease_id)


@app.post("/api/social/x/queue/{queue_id}/send")
async def social_send_x_reply(queue_id: str, data: Optional[SocialReplyUpdate] = None):
    lease_id = await _acquire_panel_mutation("Panel X reply gonderimi", "social_x_send")
    workflow = _load_social_workflow()
    reply_text = data.text if data and data.text is not None else None
    try:
        item = workflow["send_x_reply"](queue_id, message=reply_text)
        return {"status": "success", "item": item}
    except KeyError:
        raise HTTPException(status_code=404, detail="Queue item bulunamadi")
    except Exception as e:
        try:
            workflow["mark_queue_item"](queue_id, "error", note=str(e))
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=f"Reply gonderilemedi: {e}")
    finally:
        await release_automation("panel", job_id=lease_id)
