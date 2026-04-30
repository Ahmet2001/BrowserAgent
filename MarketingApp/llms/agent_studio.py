"""Config-driven agent and custom tool helpers for Agent Studio."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except Exception:  # pragma: no cover - handled at runtime
    yaml = None


APP_DIR = Path(__file__).resolve().parents[1]
CONFIG_DIR = APP_DIR / "config"
WORKSPACE_DIR = APP_DIR / "workspace"
CUSTOM_TOOLS_DIR = WORKSPACE_DIR / "custom_tools"
SUBMODELS_DIR = APP_DIR / "llms" / "SubModels"
SUBMODELS_INIT_PATH = SUBMODELS_DIR / "__init__.py"
AGENTS_CONFIG_PATH = CONFIG_DIR / "agents.yaml"
CUSTOM_TOOLS_CONFIG_PATH = CONFIG_DIR / "custom_tools.yaml"
MODEL_ENV_PATH = APP_DIR.parent / ".env.model"

AGENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,80}$")
VALID_AGENT_TYPES = {"builtin", "config"}
VALID_TOOL_MODES = {"default", "custom"}
RECOMMENDED_MEMORY_TOOLS = ["context_paketi_oku", "context_aksiyon_kaydet"]
AGENT_STUDIO_BUILTIN_MARKER = "# Agent Studio generated builtin submodel"

DEFAULT_BUILTIN_AGENTS = [
    {
        "name": "sosyal_medya_agent",
        "type": "builtin",
        "enabled": True,
        "description": "X, Instagram ve YouTube uzerinde yayinlama, etkilesim, bildirim tarama ve sosyal operasyon ajani.",
        "model": "default",
        "tool_mode": "default",
        "system_prompt": "",
        "tools": [],
    },
    {
        "name": "content_creator_agent",
        "type": "builtin",
        "enabled": True,
        "description": "Caption, medya arama, website icerigi, HTML/CSS PNG post ve MP4 video uretim ajani.",
        "model": "default",
        "tool_mode": "default",
        "system_prompt": "",
        "tools": [],
    },
    {
        "name": "browser_agent",
        "type": "builtin",
        "enabled": True,
        "description": "Selenium tabanli web gezinme, DOM okuma ve form etkilesimi ajani.",
        "model": "browser_default",
        "tool_mode": "default",
        "system_prompt": "",
        "tools": [],
    },
]
BUILTIN_AGENT_NAMES = {item["name"] for item in DEFAULT_BUILTIN_AGENTS}


def _builtin_module_path(name: str) -> Path:
    return SUBMODELS_DIR / f"{validate_agent_name(name)}.py"


def _is_scaffolded_builtin_agent(name: str) -> bool:
    try:
        path = _builtin_module_path(name)
        return path.exists() and AGENT_STUDIO_BUILTIN_MARKER in path.read_text(encoding="utf-8")[:500]
    except Exception:
        return False


def is_known_builtin_agent_name(name: str) -> bool:
    return name in BUILTIN_AGENT_NAMES or _is_scaffolded_builtin_agent(name)


def _runtime_system_prompt_note() -> str:
    return (
        "\n\n[Not: Runtime sirasinda role.md marketing kisiligi uygunsa bu prompt'un sonuna "
        "dinamik olarak eklenir.]"
    )


def default_system_prompt_placeholder(agent: dict[str, Any] | None = None) -> str:
    name = (agent or {}).get("name") or ""
    agent_type = (agent or {}).get("type") or "config"
    try:
        if name == "content_creator_agent":
            from .SubModels.content_creator_agent import DEFAULT_SYSTEM_PROMPT

            return DEFAULT_SYSTEM_PROMPT + _runtime_system_prompt_note()
        if name == "sosyal_medya_agent":
            from .SubModels.sosyal_medya_agent import DEFAULT_SYSTEM_PROMPT

            return DEFAULT_SYSTEM_PROMPT + _runtime_system_prompt_note()
        if name == "browser_agent":
            from .SubModels.browser_agent import DEFAULT_SYSTEM_PROMPT

            return DEFAULT_SYSTEM_PROMPT + _runtime_system_prompt_note()
        if agent_type == "builtin" and _is_scaffolded_builtin_agent(name):
            module_name = f"MarketingApp.llms.SubModels.{name}"
            module = importlib.import_module(module_name)
            prompt = getattr(module, "DEFAULT_SYSTEM_PROMPT", "")
            if prompt:
                return str(prompt)
        if agent_type == "config":
            from .SubModels.generic_config_agent import build_generic_config_system_prompt

            return build_generic_config_system_prompt("")
    except Exception:
        pass
    return "Agent rolünü, karar kurallarını ve tool kullanım ilkelerini yaz."


class AgentStudioError(ValueError):
    """Raised for user-facing Agent Studio validation errors."""


def _yaml_available() -> bool:
    return yaml is not None


def _ensure_yaml():
    if not _yaml_available():
        raise AgentStudioError("PyYAML yuklu degil; Agent Studio YAML config okuyamiyor.")


def _read_yaml(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    _ensure_yaml()
    if not path.exists():
        return dict(fallback)
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        raise AgentStudioError(f"{path.name} okunamadi: {exc}") from exc
    if not isinstance(data, dict):
        raise AgentStudioError(f"{path.name} kok verisi dict olmali.")
    return data


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    _ensure_yaml()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def _default_agents_config() -> dict[str, Any]:
    return {
        "version": 1,
        "global_disabled_tools": [],
        "agents": [dict(item) for item in DEFAULT_BUILTIN_AGENTS],
    }


def _default_custom_tools_config() -> dict[str, Any]:
    return {"version": 1, "custom_tools": []}


def ensure_agent_studio_files() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    if not AGENTS_CONFIG_PATH.exists():
        _write_yaml(AGENTS_CONFIG_PATH, _default_agents_config())
    if not CUSTOM_TOOLS_CONFIG_PATH.exists():
        _write_yaml(CUSTOM_TOOLS_CONFIG_PATH, _default_custom_tools_config())


def validate_agent_name(name: str) -> str:
    normalized = (name or "").strip()
    if not AGENT_NAME_RE.fullmatch(normalized):
        raise AgentStudioError("Agent adi sadece kucuk harf, rakam ve '_' icerebilir; harfle baslamali.")
    return normalized


def validate_tool_name(name: str) -> str:
    normalized = (name or "").strip()
    if not TOOL_NAME_RE.fullmatch(normalized):
        raise AgentStudioError("Tool adi sadece kucuk harf, rakam ve '_' icerebilir; harfle baslamali.")
    return normalized


def validate_env_name(name: str) -> str:
    normalized = (name or "").strip().upper()
    if not ENV_NAME_RE.fullmatch(normalized):
        raise AgentStudioError("Env adi buyuk harf, rakam ve '_' icermeli; harfle baslamali.")
    return normalized


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized = []
    seen = set()
    for item in value:
        text = str(item or "").strip()
        if text and text not in seen:
            normalized.append(text)
            seen.add(text)
    return normalized


def _normalize_env_var_names(value: Any) -> list[str]:
    names = []
    raw_items = value.keys() if isinstance(value, dict) else value
    if isinstance(raw_items, str):
        raw_items = [raw_items]
    if not isinstance(raw_items, list) and not hasattr(raw_items, "__iter__"):
        return []
    seen = set()
    for item in raw_items:
        try:
            name = validate_env_name(str(item))
        except AgentStudioError:
            continue
        if name not in seen:
            names.append(name)
            seen.add(name)
    return names


def normalize_agent_entry(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise AgentStudioError("Agent entry dict olmali.")
    agent_type = str(raw.get("type") or "config").strip().lower()
    if agent_type not in VALID_AGENT_TYPES:
        raise AgentStudioError("Agent type 'builtin' veya 'config' olmali.")
    name = validate_agent_name(str(raw.get("name") or ""))
    if agent_type == "builtin" and not is_known_builtin_agent_name(name):
        raise AgentStudioError("Builtin agent sadece kodda kayitli hazir submodel icin kullanilabilir.")
    tool_mode = str(raw.get("tool_mode") or ("custom" if raw.get("tools") and agent_type == "config" else "default")).strip().lower()
    if tool_mode not in VALID_TOOL_MODES:
        tool_mode = "default"
    return {
        "name": name,
        "type": agent_type,
        "enabled": bool(raw.get("enabled", True)),
        "description": str(raw.get("description") or "").strip(),
        "model": str(raw.get("model") or "default").strip() or "default",
        "tool_mode": tool_mode,
        "system_prompt": str(raw.get("system_prompt") or ""),
        "tools": _normalize_string_list(raw.get("tools")),
    }


def load_agents_config() -> dict[str, Any]:
    ensure_agent_studio_files()
    errors: list[dict[str, Any]] = []
    try:
        data = _read_yaml(AGENTS_CONFIG_PATH, _default_agents_config())
    except AgentStudioError as exc:
        data = _default_agents_config()
        errors.append({"scope": "agents", "message": str(exc)})

    raw_agents = data.get("agents")
    if not isinstance(raw_agents, list):
        raw_agents = []
        errors.append({"scope": "agents", "message": "agents listesi bulunamadi; varsayilanlar kullaniliyor."})

    normalized: list[dict[str, Any]] = []
    seen = set()
    for raw in raw_agents:
        try:
            item = normalize_agent_entry(raw)
        except AgentStudioError as exc:
            errors.append({"scope": "agents", "message": str(exc), "entry": raw})
            continue
        if item["name"] in seen:
            errors.append({"scope": "agents", "message": f"Tekrarlanan agent atlandi: {item['name']}"})
            continue
        normalized.append(item)
        seen.add(item["name"])

    for default_agent in DEFAULT_BUILTIN_AGENTS:
        if default_agent["name"] not in seen:
            normalized.append(dict(default_agent))
            seen.add(default_agent["name"])

    disabled_tools = _normalize_string_list(data.get("global_disabled_tools"))
    return {
        "version": int(data.get("version") or 1),
        "global_disabled_tools": disabled_tools,
        "agents": normalized,
        "errors": errors,
        "path": str(AGENTS_CONFIG_PATH),
    }


def save_agents_config(agents: list[dict[str, Any]], global_disabled_tools: list[str] | None = None) -> None:
    normalized = [normalize_agent_entry(item) for item in agents]
    data = {
        "version": 1,
        "global_disabled_tools": _normalize_string_list(global_disabled_tools or []),
        "agents": normalized,
    }
    _write_yaml(AGENTS_CONFIG_PATH, data)


def _agent_class_name(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_") if part) + "SubModel"


def _builtin_scaffold_source(agent: dict[str, Any]) -> str:
    name = agent["name"]
    class_name = _agent_class_name(name)
    description = agent.get("description") or "Agent Studio ile uretilmis builtin alt ajan."
    model = agent.get("model") or "default"
    prompt = (agent.get("system_prompt") or "").strip() or (
        "Sen Agent Studio ile uretilmis dosya tabanli bir builtin alt ajansin. "
        "Sana baglanan araclari kullanarak gorevi denetlenebilir sekilde tamamla."
    )
    return f'''"""Agent Studio generated builtin submodel: {name}."""

from __future__ import annotations

{AGENT_STUDIO_BUILTIN_MARKER}

from MarketingApp.llms.SubModels.base import register_submodel
from MarketingApp.llms.SubModels.generic_config_agent import (
    GenericConfigAgent,
    build_generic_config_system_prompt,
)


DEFAULT_SYSTEM_PROMPT = {prompt!r}


class {class_name}(GenericConfigAgent):
    """{description}"""

    def __init__(self):
        super().__init__(
            {{
                "name": {name!r},
                "type": "builtin",
                "enabled": True,
                "description": {description!r},
                "model": {model!r},
                "tool_mode": "custom",
                "system_prompt": DEFAULT_SYSTEM_PROMPT,
                "tools": [],
            }},
            tools=[],
        )

    def _build_system_prompt(self) -> str:
        prompt = DEFAULT_SYSTEM_PROMPT
        try:
            from MarketingApp.llms.agent_studio import load_agents_config

            for agent in load_agents_config().get("agents", []):
                if agent.get("name") == self.name:
                    prompt = (agent.get("system_prompt") or "").strip() or DEFAULT_SYSTEM_PROMPT
                    break
        except Exception:
            pass
        return build_generic_config_system_prompt(prompt)


register_submodel({class_name}())
'''


def _ensure_submodels_init_import(name: str) -> None:
    SUBMODELS_INIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    import_line = f"from . import {name}  # Agent Studio builtin\n"
    if SUBMODELS_INIT_PATH.exists():
        text = SUBMODELS_INIT_PATH.read_text(encoding="utf-8")
    else:
        text = ""
    if import_line.strip() in text:
        return
    if text and not text.endswith("\n"):
        text += "\n"
    SUBMODELS_INIT_PATH.write_text(text + import_line, encoding="utf-8")


def import_scaffolded_builtin_submodel(name: str) -> None:
    normalized_name = validate_agent_name(name)
    if not _is_scaffolded_builtin_agent(normalized_name):
        raise AgentStudioError(f"{normalized_name} icin Agent Studio builtin dosyasi bulunamadi.")
    module_name = f"MarketingApp.llms.SubModels.{normalized_name}"
    importlib.invalidate_caches()
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


def import_scaffolded_builtin_submodels() -> list[str]:
    loaded = []
    if not SUBMODELS_DIR.exists():
        return loaded
    for path in sorted(SUBMODELS_DIR.glob("*.py")):
        name = path.stem
        if name.startswith("_") or name in {"base", "generic_config_agent"}:
            continue
        if _is_scaffolded_builtin_agent(name):
            import_scaffolded_builtin_submodel(name)
            loaded.append(name)
    return loaded


def create_builtin_agent_scaffold(entry: dict[str, Any]) -> dict[str, Any]:
    raw = dict(entry or {})
    raw["type"] = "builtin"
    name = validate_agent_name(str(raw.get("name") or ""))
    if name in BUILTIN_AGENT_NAMES:
        raise AgentStudioError("Hazir builtin agent yeniden olusturulamaz.")
    if _is_scaffolded_builtin_agent(name):
        raise AgentStudioError(f"{name} builtin submodel dosyasi zaten var.")

    config = load_agents_config()
    if any(item["name"] == name for item in config["agents"]):
        raise AgentStudioError(f"{name} zaten agents.yaml icinde var.")

    agent = {
        "name": name,
        "type": "builtin",
        "enabled": bool(raw.get("enabled", True)),
        "description": str(raw.get("description") or "Agent Studio ile uretilmis builtin alt ajan.").strip(),
        "model": str(raw.get("model") or "default").strip() or "default",
        "tool_mode": "custom",
        "system_prompt": str(raw.get("system_prompt") or "").strip(),
        "tools": _normalize_string_list(raw.get("tools")),
    }

    path = _builtin_module_path(name)
    if path.exists():
        raise AgentStudioError(f"{path.name} zaten var; var olan dosyanin ustune yazilmadi.")
    path.write_text(_builtin_scaffold_source(agent), encoding="utf-8")
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
        _ensure_submodels_init_import(name)
        normalized = normalize_agent_entry(agent)
        save_agents_config(config["agents"] + [normalized], config["global_disabled_tools"])
        import_scaffolded_builtin_submodel(name)
    except Exception as exc:
        raise AgentStudioError(f"Builtin submodel scaffold olusturulamadi: {exc}") from exc

    return {
        "agent": normalized,
        "path": str(path),
        "init_path": str(SUBMODELS_INIT_PATH),
    }


def upsert_agent_config(entry: dict[str, Any], *, create: bool = False) -> dict[str, Any]:
    incoming = normalize_agent_entry(entry)
    if create and incoming["type"] == "builtin":
        raise AgentStudioError("Yeni builtin agent panelden olusturulamaz; yeni ajanlar config tipinde olmali.")
    config = load_agents_config()
    agents = list(config["agents"])
    index = next((i for i, item in enumerate(agents) if item["name"] == incoming["name"]), None)
    if create and index is not None:
        raise AgentStudioError(f"{incoming['name']} zaten var.")
    if index is None:
        agents.append(incoming)
    else:
        existing_type = agents[index].get("type") or "config"
        if existing_type == "builtin" and incoming["type"] != "builtin":
            raise AgentStudioError("Builtin agent type degistirilemez.")
        agents[index] = {**agents[index], **incoming, "type": existing_type if existing_type == "builtin" else incoming["type"]}
    save_agents_config(agents, config["global_disabled_tools"])
    return incoming


def delete_agent_config(name: str) -> dict[str, Any]:
    normalized_name = validate_agent_name(name)
    config = load_agents_config()
    agents = list(config["agents"])
    target = next((item for item in agents if item["name"] == normalized_name), None)
    if not target:
        raise AgentStudioError(f"{normalized_name} bulunamadi.")
    if target.get("type") == "builtin":
        raise AgentStudioError("Builtin agent silinemez; pasife alabilirsin.")
    agents = [item for item in agents if item["name"] != normalized_name]
    save_agents_config(agents, config["global_disabled_tools"])
    return target


def set_agent_enabled(name: str, enabled: bool) -> bool:
    normalized_name = validate_agent_name(name)
    config = load_agents_config()
    changed = False
    for item in config["agents"]:
        if item["name"] == normalized_name:
            item["enabled"] = bool(enabled)
            changed = True
            break
    if not changed:
        raise AgentStudioError(f"{normalized_name} bulunamadi.")
    save_agents_config(config["agents"], config["global_disabled_tools"])
    return bool(enabled)


def set_global_tool_active(name: str, active: bool) -> bool:
    normalized_name = validate_tool_name(name)
    config = load_agents_config()
    disabled = set(config["global_disabled_tools"])
    if active:
        disabled.discard(normalized_name)
    else:
        disabled.add(normalized_name)
    save_agents_config(config["agents"], sorted(disabled))
    return bool(active)


def load_custom_tools_config() -> dict[str, Any]:
    ensure_agent_studio_files()
    errors: list[dict[str, Any]] = []
    try:
        data = _read_yaml(CUSTOM_TOOLS_CONFIG_PATH, _default_custom_tools_config())
    except AgentStudioError as exc:
        data = _default_custom_tools_config()
        errors.append({"scope": "custom_tools", "message": str(exc)})

    raw_tools = data.get("custom_tools")
    if not isinstance(raw_tools, list):
        raw_tools = []
        errors.append({"scope": "custom_tools", "message": "custom_tools listesi bulunamadi."})

    normalized = []
    seen = set()
    for raw in raw_tools:
        if not isinstance(raw, dict):
            errors.append({"scope": "custom_tools", "message": "Custom tool entry dict olmali.", "entry": raw})
            continue
        try:
            name = validate_tool_name(str(raw.get("name") or ""))
        except AgentStudioError as exc:
            errors.append({"scope": "custom_tools", "message": str(exc), "entry": raw})
            continue
        if name in seen:
            errors.append({"scope": "custom_tools", "message": f"Tekrarlanan custom tool atlandi: {name}"})
            continue
        file_name = os.path.basename(str(raw.get("file") or f"{name}.py"))
        normalized.append(
            {
                "name": name,
                "enabled": bool(raw.get("enabled", False)),
                "description": str(raw.get("description") or "").strip(),
                "file": file_name,
                "params_note": str(raw.get("params_note") or "").strip(),
                "env_vars": _normalize_env_var_names(raw.get("env_vars")),
            }
        )
        seen.add(name)

    return {
        "version": int(data.get("version") or 1),
        "custom_tools": normalized,
        "errors": errors,
        "path": str(CUSTOM_TOOLS_CONFIG_PATH),
    }


def save_custom_tools_config(entries: list[dict[str, Any]]) -> None:
    normalized = []
    for entry in entries:
        name = validate_tool_name(str(entry.get("name") or ""))
        normalized.append(
            {
                "name": name,
                "enabled": bool(entry.get("enabled", False)),
                "description": str(entry.get("description") or "").strip(),
                "file": os.path.basename(str(entry.get("file") or f"{name}.py")),
                "params_note": str(entry.get("params_note") or "").strip(),
                "env_vars": _normalize_env_var_names(entry.get("env_vars")),
            }
        )
    _write_yaml(CUSTOM_TOOLS_CONFIG_PATH, {"version": 1, "custom_tools": normalized})


def _custom_tool_path(file_name: str) -> Path:
    CUSTOM_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    candidate = (CUSTOM_TOOLS_DIR / os.path.basename(file_name)).resolve()
    root = CUSTOM_TOOLS_DIR.resolve()
    if os.path.commonpath([str(root), str(candidate)]) != str(root):
        raise AgentStudioError("Custom tool dosya yolu izin verilen dizin disinda.")
    return candidate


def read_model_env_vars() -> dict[str, str]:
    values: dict[str, str] = {}
    if not MODEL_ENV_PATH.exists():
        return values
    for raw_line in MODEL_ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = value.strip().strip('"').strip("'")
    return values


def load_model_env_file() -> dict[str, str]:
    values = read_model_env_vars()
    for key, value in values.items():
        os.environ[key] = value
    return values


def update_model_env_vars(env_vars: dict[str, Any] | None) -> list[str]:
    if not env_vars:
        return []
    existing = read_model_env_vars()
    updated_names = []
    for raw_key, raw_value in env_vars.items():
        key = validate_env_name(str(raw_key))
        value = str(raw_value or "")
        if value == "":
            continue
        existing[key] = value
        os.environ[key] = value
        updated_names.append(key)
    if updated_names:
        MODEL_ENV_PATH.write_text(
            "\n".join(f"{key}={value}" for key, value in sorted(existing.items())) + "\n",
            encoding="utf-8",
        )
    return updated_names


def upsert_custom_tool(
    name: str,
    description: str,
    code: str,
    *,
    enabled: bool = True,
    params_note: str = "",
    env_vars: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_name = validate_tool_name(name)
    file_name = f"{normalized_name}.py"
    path = _custom_tool_path(file_name)
    path.write_text(code or "", encoding="utf-8")
    env_var_names = update_model_env_vars(env_vars)

    config = load_custom_tools_config()
    entries = list(config["custom_tools"])
    entry = {
        "name": normalized_name,
        "enabled": bool(enabled),
        "description": description.strip(),
        "file": file_name,
        "params_note": params_note.strip(),
        "env_vars": _normalize_env_var_names(env_var_names or env_vars or []),
    }
    index = next((i for i, item in enumerate(entries) if item["name"] == normalized_name), None)
    if index is None:
        entries.append(entry)
    else:
        entries[index] = entry
    save_custom_tools_config(entries)
    return {**entry, "path": str(path)}


def read_custom_tool_code(entry: dict[str, Any]) -> str:
    try:
        return _custom_tool_path(entry.get("file") or f"{entry.get('name')}.py").read_text(encoding="utf-8")
    except Exception:
        return ""


def load_custom_tool_callable(entry: dict[str, Any], *, include_disabled: bool = False) -> tuple[Callable | None, str | None]:
    if not include_disabled and not entry.get("enabled", False):
        return None, "Custom tool pasif."
    try:
        name = validate_tool_name(entry["name"])
        path = _custom_tool_path(entry.get("file") or f"{name}.py")
        if not path.exists():
            return None, f"{path.name} bulunamadi."
        load_model_env_file()
        module_name = f"marketingapp_custom_tool_{name}_{path.stat().st_mtime_ns}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if not spec or not spec.loader:
            return None, "Python module spec olusturulamadi."
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        func = getattr(module, name, None)
        if not callable(func):
            return None, f"{name} fonksiyonu export edilmemis."
        if not (func.__doc__ or "").strip() and entry.get("description"):
            func.__doc__ = entry["description"]
        return func, None
    except Exception as exc:
        return None, str(exc)


def load_custom_tools(*, include_disabled: bool = False) -> dict[str, Any]:
    config = load_custom_tools_config()
    tools: dict[str, Callable] = {}
    entries = []
    errors = list(config["errors"])
    for entry in config["custom_tools"]:
        func, error = load_custom_tool_callable(entry, include_disabled=include_disabled)
        status = {**entry, "path": str(_custom_tool_path(entry.get("file") or f"{entry['name']}.py")), "error": error, "code": read_custom_tool_code(entry)}
        entries.append(status)
        if error:
            errors.append({"scope": "custom_tools", "name": entry["name"], "message": error})
            continue
        if func:
            tools[entry["name"]] = func
    return {"tools": tools, "entries": entries, "errors": errors}


def _tool_description(func: Callable) -> str:
    doc = (getattr(func, "__doc__", "") or "").strip().splitlines()
    return doc[0].strip() if doc else ""


def _category_for_tool(name: str, group: str, source: str = "builtin") -> str:
    if source == "custom":
        return "system"
    if name in RECOMMENDED_MEMORY_TOOLS or name.startswith("bellek_") or name.startswith("rol_"):
        return "memory"
    if name.startswith("workspace_"):
        return "workspace"
    if name.startswith("browser_") or name in {"click_mouse", "type_text", "press_key", "scroll_up", "scroll_down"}:
        return "browser"
    if name == "web_arama" or "website_" in name or name.startswith("pexels_"):
        return "web" if name == "web_arama" else "content"
    if "instagram" in name or "youtube" in name or "_x_" in name or name.startswith(("publish_x", "reply_to_x", "send_x", "scan_x", "get_x", "launch_x", "open_x", "close_x")):
        return "social"
    if group in {"content_creator_agent"}:
        return "content"
    if group in {"sosyal_medya_agent"}:
        return "social"
    if group in {"browser_agent", "vlm_agent"}:
        return "browser"
    if name.startswith("terminal_") or "system" in name or group in {"sistem_agent", "kod_agent"}:
        return "system"
    return "workspace"


def _risk_for_tool(name: str, category: str, source: str = "builtin") -> str:
    if source == "custom":
        return "high"
    high_markers = (
        "terminal",
        "sil",
        "publish_",
        "send_",
        "reply_to_",
        "follow_",
        "like_",
        "repost_",
        "quote_",
        "comment_",
        "subscribe_",
        "browser_click",
        "browser_type",
        "browser_deger",
        "browser_dosya",
        "browser_sekme_kapat",
        "browser_kapat",
    )
    if any(marker in name for marker in high_markers):
        return "high"
    medium_markers = ("workspace_yaz", "workspace_ekle", "rol_guncelle", "bellek_yaz", "html_css", "video_post", "website_iceriginden")
    if any(marker in name for marker in medium_markers):
        return "medium"
    if category in {"browser", "social", "web", "content"}:
        return "medium"
    return "low"


def _builtin_tool_groups() -> dict[str, list[Callable]]:
    from MarketingApp import araclar

    return {
        "base": list(araclar.BASE_ARACLAR),
        "sosyal_medya_agent": list(araclar.SOSYAL_MEDYA_ARACLARI),
        "content_creator_agent": list(araclar.CONTENT_CREATOR_ARACLARI),
        "sistem_agent": list(araclar.SISTEM_ARACLARI),
        "arastirma_agent": list(araclar.ARAMA_ARACLARI),
        "kod_agent": list(araclar.KOD_ARACLARI),
        "vlm_agent": list(araclar.VLM_ARACLARI),
        "browser_agent": list(araclar.BROWSER_ARACLARI),
    }


def load_available_tools(*, include_custom: bool = True) -> dict[str, Any]:
    tools: dict[str, Callable] = {}
    groups_for_tool: dict[str, set[str]] = {}
    for group, funcs in _builtin_tool_groups().items():
        for func in funcs:
            name = getattr(func, "__name__", "")
            if not name:
                continue
            tools.setdefault(name, func)
            groups_for_tool.setdefault(name, set()).add(group)

    errors: list[dict[str, Any]] = []
    custom_entries: list[dict[str, Any]] = []
    if include_custom:
        loaded_custom = load_custom_tools(include_disabled=False)
        errors.extend(loaded_custom["errors"])
        custom_entries = loaded_custom["entries"]
        for name, func in loaded_custom["tools"].items():
            tools[name] = func
            groups_for_tool.setdefault(name, set()).add("custom")

    return {
        "tools": tools,
        "groups": {name: sorted(groups) for name, groups in groups_for_tool.items()},
        "errors": errors,
        "custom_entries": custom_entries,
    }


def build_tool_registry() -> dict[str, Any]:
    config = load_agents_config()
    loaded = load_available_tools(include_custom=True)
    disabled = set(config["global_disabled_tools"])
    registry = []
    for name, func in sorted(loaded["tools"].items()):
        groups = loaded["groups"].get(name, [])
        source = "custom" if "custom" in groups else "builtin"
        primary_group = next((group for group in groups if group != "custom"), groups[0] if groups else "base")
        category = _category_for_tool(name, primary_group, source)
        registry.append(
            {
                "name": name,
                "description": _tool_description(func),
                "category": category,
                "risk": _risk_for_tool(name, category, source),
                "source": source,
                "groups": groups,
                "active": name not in disabled,
                "recommended": name in RECOMMENDED_MEMORY_TOOLS,
                "signature": str(inspect.signature(func)),
            }
        )
    return {
        "tools": registry,
        "errors": loaded["errors"] + config["errors"],
        "recommended_memory_tools": list(RECOMMENDED_MEMORY_TOOLS),
    }


def load_agent_studio_catalog() -> dict[str, Any]:
    agents = load_agents_config()
    custom = load_custom_tools(include_disabled=True)
    registry = build_tool_registry()
    agent_entries = [
        {**agent, "system_prompt_placeholder": default_system_prompt_placeholder(agent)}
        for agent in agents["agents"]
    ]
    return {
        "agents": agent_entries,
        "global_disabled_tools": agents["global_disabled_tools"],
        "tools": registry["tools"],
        "custom_tools": custom["entries"],
        "recommended_memory_tools": list(RECOMMENDED_MEMORY_TOOLS),
        "default_config_system_prompt_placeholder": default_system_prompt_placeholder({"type": "config"}),
        "paths": {
            "agents_config": str(AGENTS_CONFIG_PATH),
            "custom_tools_config": str(CUSTOM_TOOLS_CONFIG_PATH),
            "custom_tools_dir": str(CUSTOM_TOOLS_DIR),
            "submodels_dir": str(SUBMODELS_DIR),
            "submodels_init": str(SUBMODELS_INIT_PATH),
            "model_env": str(MODEL_ENV_PATH),
        },
        "errors": agents["errors"] + registry["errors"] + custom["errors"],
    }
