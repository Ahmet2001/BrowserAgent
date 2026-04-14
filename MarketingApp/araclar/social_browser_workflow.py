"""
Tarayıcı tabanlı sosyal etkileşim akışı.

Bu modül düşük hacimli, insan-onaylı yorum okuma ve cevap gönderme akışı sağlar.
Anti-bot mekanizmalarını atlatmaya çalışmaz; mevcut gerçek tarayıcı oturumu üzerinde,
sayfa DOM'unu okuyarak yeni yorumları sıraya alır ve kullanıcı onayıyla cevap yollar.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from datetime import datetime
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .browser_araclari import (
    _get_driver,
    _human_click,
    _human_type,
    browser_baslat,
    browser_git,
    browser_kapat,
    get_browser_runtime_state,
)


_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SOCIAL_DIR = os.path.join(_PROJECT_ROOT, "workspace", "social")
_QUEUE_PATH = os.path.join(_SOCIAL_DIR, "x_reply_queue.json")
_MARKET_STATE_PATH = os.path.join(_SOCIAL_DIR, "market_state.md")
_IDEA_POOL_PATH = os.path.join(_SOCIAL_DIR, "idea_pool.md")
_FEED_SNAPSHOT_PATH = os.path.join(_SOCIAL_DIR, "x_feed_snapshot.json")

_TOPIC_KEYWORDS = {
    "bitcoin": ("bitcoin", "btc", "sats"),
    "ethereum": ("ethereum", "eth", "ether"),
    "solana": ("solana", "sol"),
    "altcoins": ("altcoin", "alts", "altseason", "dominance"),
    "defi": ("defi", "yield", "dex", "staking", "liquidity"),
    "nft": ("nft", "ordinals", "jpeg", "pfp"),
    "web3": ("web3", "wallet", "onchain", "blockchain", "protocol"),
    "regulation": ("sec", "regulation", "compliance", "lawsuit", "etf"),
    "macro": ("fed", "cpi", "rates", "macro", "liquidity", "dxy"),
    "memecoins": ("meme", "memecoin", "doge", "shib", "pepe"),
    "stablecoins": ("stablecoin", "usdt", "usdc", "dai"),
}

_BULLISH_WORDS = (
    "breakout", "up only", "bullish", "bid", "strength", "bounce", "higher",
    "accumulation", "squeeze", "rip", "green",
)
_BEARISH_WORDS = (
    "breakdown", "bearish", "selloff", "dump", "weakness", "lower", "risk off",
    "liquidation", "rejection", "red", "panic",
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_social_dir():
    os.makedirs(_SOCIAL_DIR, exist_ok=True)


def _compact_text(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _write_json(path: str, payload: Any):
    _ensure_social_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _write_text(path: str, content: str):
    _ensure_social_dir()
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _normalize_token(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u")
    text = text.replace("ş", "s").replace("ö", "o").replace("ç", "c")
    return re.sub(r"[^a-z0-9\s#@/$.-]+", " ", text)


def _extract_topics(entries: list[dict[str, Any]]) -> dict[str, int]:
    combined = " ".join(_normalize_token(entry.get("text", "")) for entry in entries)
    counts: dict[str, int] = {}
    for topic, keywords in _TOPIC_KEYWORDS.items():
        counts[topic] = sum(combined.count(keyword) for keyword in keywords)
    return {topic: count for topic, count in counts.items() if count > 0}


def _detect_market_mood(entries: list[dict[str, Any]]) -> str:
    combined = " ".join(_normalize_token(entry.get("text", "")) for entry in entries)
    bullish = sum(combined.count(word) for word in _BULLISH_WORDS)
    bearish = sum(combined.count(word) for word in _BEARISH_WORDS)
    if bullish > bearish + 1:
        return "risk-on / bullish"
    if bearish > bullish + 1:
        return "risk-off / bearish"
    return "mixed / waiting"


def _idea_templates_for_topic(topic: str) -> list[str]:
    return [
        f"{topic} tarafinda kalabaligin neye odaklandigini tek gozlemle acikla.",
        f"{topic} icin piyasanin atladigi tek riski veya firsati sade dille anlat.",
        f"{topic} konusunda bugunun akisindan cikabilecek tek net sonucu yaz.",
        f"{topic} basliginda yeni baslayanlarin yanlis okudugu noktayi duzelt.",
    ]


def _build_market_files(source: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    topics = _extract_topics(entries)
    top_topics = sorted(topics.items(), key=lambda item: (-item[1], item[0]))[:6]
    mood = _detect_market_mood(entries)
    handles = Counter(
        entry.get("handle", "")
        for entry in entries
        if entry.get("handle")
    ).most_common(6)

    samples = []
    for entry in entries[:12]:
        handle = entry.get("handle") or "unknown"
        samples.append(
            f"- @{handle} | {entry.get('tweet_id', '')} | {_compact_text(entry.get('text', ''), 180)}"
        )

    idea_lines = []
    used = set()
    topic_order = [topic for topic, _ in top_topics] or ["crypto", "bitcoin", "ethereum", "web3"]
    for topic in topic_order:
        for template in _idea_templates_for_topic(topic):
            if template in used:
                continue
            idea_lines.append(f"- [fresh] {template}")
            used.add(template)
            if len(idea_lines) >= 12:
                break
        if len(idea_lines) >= 12:
            break

    market_state = "\n".join([
        "# Market State",
        "",
        f"- updated_at: {_now()}",
        f"- source: {source}",
        f"- visible_posts: {len(entries)}",
        f"- market_mood: {mood}",
        f"- top_topics: {', '.join(f'{topic}({count})' for topic, count in top_topics) or 'belirgin tema yok'}",
        f"- active_handles: {', '.join(f'@{handle}({count})' for handle, count in handles) or 'yok'}",
        "",
        "## Feed Samples",
        *samples,
        "",
        "## Usage",
        "- Yeni post veya yorum yazmadan once burayi oku.",
        "- Ayni aciyi ust uste kullanma.",
        "- Tek postta tek bir ana fikir sec.",
    ])

    idea_pool = "\n".join([
        "# Idea Pool",
        "",
        f"- updated_at: {_now()}",
        f"- source: {source}",
        "",
        "## Fresh Angles",
        *idea_lines,
        "",
        "## Rotation Rule",
        "- Aynı etiketi [used] olmadan art arda kullanma.",
        "- Son 10 aksiyonda benzer cümle varsa başka fikre geç.",
    ])

    _write_text(_MARKET_STATE_PATH, market_state)
    _write_text(_IDEA_POOL_PATH, idea_pool)

    return {
        "market_mood": mood,
        "top_topics": top_topics,
        "idea_count": len(idea_lines),
    }


def _load_queue() -> dict[str, Any]:
    _ensure_social_dir()
    if not os.path.exists(_QUEUE_PATH):
        return {"platform": "x", "updated_at": _now(), "items": []}
    try:
        with open(_QUEUE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Queue format bozuk")
        data.setdefault("platform", "x")
        data.setdefault("updated_at", _now())
        data.setdefault("items", [])
        return data
    except Exception:
        return {"platform": "x", "updated_at": _now(), "items": []}


def _save_queue(data: dict[str, Any]):
    _ensure_social_dir()
    data["updated_at"] = _now()
    with open(_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_x_queue() -> dict[str, Any]:
    data = _load_queue()
    data["items"] = sorted(
        data["items"],
        key=lambda item: (item.get("status") == "sent", item.get("discovered_at", "")),
        reverse=False,
    )
    data["summary"] = {
        "total": len(data["items"]),
        "new": sum(1 for item in data["items"] if item.get("status") == "new"),
        "drafted": sum(1 for item in data["items"] if item.get("status") == "drafted"),
        "sent": sum(1 for item in data["items"] if item.get("status") == "sent"),
        "preview": [
            {
                "queue_id": item.get("queue_id", ""),
                "status": item.get("status", ""),
                "author_handle": item.get("author_handle", ""),
                "text": _compact_text(item.get("text", ""), 160),
            }
            for item in data["items"][:12]
        ],
    }
    return data


def get_browser_status() -> dict[str, Any]:
    runtime = get_browser_runtime_state()
    try:
        driver = _get_driver()
        return {
            "ready": True,
            "title": driver.title,
            "url": driver.current_url,
            "window_count": len(driver.window_handles),
            "headless": runtime.get("active_headless"),
            "preferred_headless": runtime.get("preferred_headless"),
            "visibility_label": runtime.get("visibility_label"),
        }
    except Exception as e:
        return {
            "ready": False,
            "error": str(e),
            "title": "",
            "url": "",
            "window_count": 0,
            "headless": runtime.get("active_headless"),
            "preferred_headless": runtime.get("preferred_headless"),
            "visibility_label": runtime.get("visibility_label"),
        }


def launch_x_browser(headless: bool = False, restart_if_needed: bool = True) -> dict[str, Any]:
    """
    X otomasyon tarayıcısını görünür veya headless modda başlatır.
    Gerekirse açık oturumu aynı URL'de yeniden başlatır.

    Args:
        headless: True ise pencere açılmaz, False ise görünür modda açılır
        restart_if_needed: Mod farklıysa açık tarayıcıyı kapatıp yeniden başlat
    """
    desired_headless = bool(headless)
    current_status = get_browser_status()
    current_url = current_status.get("url", "") if current_status.get("ready") else ""
    current_headless = current_status.get("headless")

    if current_status.get("ready"):
        if current_headless == desired_headless:
            return {
                "status": "already_running",
                "message": f"Tarayıcı zaten {'headless' if desired_headless else 'görünür'} modda açık.",
                "browser": current_status,
            }

        if not restart_if_needed:
            return {
                "status": "restart_required",
                "message": "Mod değişikliği için tarayıcıyı yeniden başlatmak gerekiyor.",
                "browser": current_status,
            }

        close_result = browser_kapat()
        start_result = browser_baslat(headless=desired_headless)
        reopen_result = ""
        if start_result.startswith("✅") and current_url.startswith("http"):
            reopen_result = browser_git(current_url)
        return {
            "status": "restarted",
            "message": start_result,
            "close_result": close_result,
            "reopen_result": reopen_result,
            "browser": get_browser_status(),
        }

    start_result = browser_baslat(headless=desired_headless)
    return {
        "status": "started" if start_result.startswith("✅") else "error",
        "message": start_result,
        "browser": get_browser_status(),
    }


def _normalize_x_status_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://x.com{url}"


def _extract_root_status_id(url: str) -> str | None:
    match = re.search(r"/status/(\d+)", url or "")
    return match.group(1) if match else None


def _collect_x_articles(limit: int = 20) -> list[dict[str, Any]]:
    driver = _get_driver()
    js_script = """
    const results = [];
    const articles = [...document.querySelectorAll('article[data-testid="tweet"]')];

    for (const [index, article] of articles.entries()) {
        article.setAttribute('data-mimar-social-id', String(index));

        const statusLink = [...article.querySelectorAll('a[href*="/status/"]')]
            .map((a) => a.getAttribute('href') || '')
            .find((href) => /\\/status\\/\\d+/.test(href));

        if (!statusLink) continue;

        const textNode = article.querySelector('[data-testid="tweetText"]');
        const timeNode = article.querySelector('time');
        const userNameNode = article.querySelector('[data-testid="User-Name"]');
        const replyButton = article.querySelector('[data-testid="reply"]');

        const handleMatch = statusLink.match(/^\\/([^/]+)\\/status\\/(\\d+)/);
        const handle = handleMatch ? handleMatch[1] : '';
        const tweetId = handleMatch ? handleMatch[2] : '';

        let displayName = '';
        if (userNameNode) {
            const spans = [...userNameNode.querySelectorAll('span')].map((s) => (s.textContent || '').trim()).filter(Boolean);
            displayName = spans[0] || '';
        }

        results.push({
            article_index: index,
            tweet_id: tweetId,
            tweet_url: statusLink,
            handle: handle,
            display_name: displayName,
            text: textNode ? (textNode.innerText || '').trim() : '',
            time_text: timeNode ? (timeNode.getAttribute('datetime') || timeNode.textContent || '').trim() : '',
            reply_available: !!replyButton
        });
    }

    return results;
    """
    results = driver.execute_script(js_script)
    return results[: max(1, min(int(limit), 50))]


def _wait_for_x_articles(timeout: int = 12):
    driver = _get_driver()
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet']"))
    )


def _compact_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "tweet_id": entry.get("tweet_id", ""),
        "tweet_url": _normalize_x_status_url(entry.get("tweet_url", "")),
        "handle": entry.get("handle", ""),
        "display_name": entry.get("display_name", ""),
        "text": _compact_text(entry.get("text", ""), 220),
        "time_text": entry.get("time_text", ""),
        "reply_available": bool(entry.get("reply_available")),
    }


def snapshot_x_feed(source: str = "home", limit: int = 12, write_to_file: bool = True) -> dict[str, Any]:
    """
    X akışından küçük bir görünüm alır. Otomasyon görevleri bunu okuyup
    piyasa temasını anlamak ve tekrar etmeyen içerik seçmek için kullanabilir.

    Args:
        source: home, explore, notifications veya mevcut
        limit: En fazla okunacak post sayısı
        write_to_file: true ise kompakt snapshot dosyasını günceller
    """
    driver = _get_driver()
    normalized_source = (source or "home").strip().lower()
    target_url = {
        "home": "https://x.com/home",
        "explore": "https://x.com/explore",
        "notifications": "https://x.com/notifications",
        "mentions": "https://x.com/notifications/mentions",
    }.get(normalized_source, driver.current_url)

    if normalized_source != "mevcut":
        driver.get(target_url)
        _wait_for_x_articles()
        time.sleep(1.2)

    entries = [_compact_entry(entry) for entry in _collect_x_articles(limit=limit)]
    payload = {
        "updated_at": _now(),
        "source": normalized_source,
        "page_url": driver.current_url,
        "count": len(entries),
        "items": entries,
    }
    if write_to_file:
        _write_json(_FEED_SNAPSHOT_PATH, payload)
    return payload


def save_x_market_snapshot(source: str = "home", limit: int = 12) -> dict[str, Any]:
    """
    X akışındaki görünür postlardan küçük bir piyasa durumu ve fikir havuzu üretir.

    Args:
        source: home, explore, notifications veya mevcut
        limit: Örnek alınacak post sayısı
    """
    snapshot = snapshot_x_feed(source=source, limit=limit, write_to_file=True)
    summary = _build_market_files(snapshot.get("page_url", ""), snapshot.get("items", []))
    return {
        "snapshot_count": snapshot.get("count", 0),
        "page_url": snapshot.get("page_url", ""),
        "market_state_path": _MARKET_STATE_PATH,
        "idea_pool_path": _IDEA_POOL_PATH,
        **summary,
    }


def scan_x_page(limit: int = 20) -> dict[str, Any]:
    driver = _get_driver()
    browser = get_browser_status()
    current_url = driver.current_url
    root_status_id = _extract_root_status_id(current_url)
    entries = _collect_x_articles(limit=limit)

    queue = _load_queue()
    by_tweet_id = {item.get("platform_comment_id"): item for item in queue["items"]}

    discovered = 0
    refreshed = 0
    skipped = 0

    for entry in entries:
        tweet_id = entry.get("tweet_id")
        if not tweet_id:
            continue
        if root_status_id and tweet_id == root_status_id:
            skipped += 1
            continue

        normalized_url = _normalize_x_status_url(entry.get("tweet_url", ""))
        existing = by_tweet_id.get(tweet_id)

        payload = {
            "queue_id": f"x-{tweet_id}",
            "platform": "x",
            "platform_comment_id": tweet_id,
            "tweet_url": normalized_url,
            "author_handle": entry.get("handle", ""),
            "author_name": entry.get("display_name", ""),
            "text": entry.get("text", ""),
            "status": "new",
            "reply_available": bool(entry.get("reply_available")),
            "page_url": current_url,
            "discovered_at": _now(),
            "updated_at": _now(),
            "draft_reply": existing.get("draft_reply", "") if existing else "",
            "sent_reply": existing.get("sent_reply", "") if existing else "",
            "last_error": existing.get("last_error", "") if existing else "",
            "time_label": entry.get("time_text", ""),
        }

        if existing:
            existing.update({
                "tweet_url": payload["tweet_url"],
                "author_handle": payload["author_handle"],
                "author_name": payload["author_name"],
                "text": payload["text"],
                "reply_available": payload["reply_available"],
                "page_url": payload["page_url"],
                "time_label": payload["time_label"],
                "updated_at": _now(),
            })
            refreshed += 1
        else:
            queue["items"].append(payload)
            by_tweet_id[tweet_id] = payload
            discovered += 1

    _save_queue(queue)
    queue_summary = get_x_queue().get("summary", {})
    return {
        "browser": browser,
        "source_url": current_url,
        "root_status_id": root_status_id,
        "scanned_count": len(entries),
        "new_items": discovered,
        "refreshed_items": refreshed,
        "skipped_items": skipped,
        "queue_summary": queue_summary,
        "queue": queue,
    }


def scan_x_notifications(limit: int = 20, mentions_only: bool = True) -> dict[str, Any]:
    """
    X bildirimlerini tarar ve reply kuyruğunu günceller.

    Args:
        limit: En fazla okunacak bildirim postu sayısı
        mentions_only: true ise mentions sekmesine gider
    """
    driver = _get_driver()
    target_url = "https://x.com/notifications/mentions" if mentions_only else "https://x.com/notifications"
    driver.get(target_url)
    _wait_for_x_articles()
    time.sleep(1.0)
    result = scan_x_page(limit=limit)
    result["notification_mode"] = "mentions" if mentions_only else "all"
    return result


def _find_queue_item(queue_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    queue = _load_queue()
    for item in queue["items"]:
        if item.get("queue_id") == queue_id:
            return queue, item
    raise KeyError(f"Queue item bulunamadı: {queue_id}")


def update_queue_item(queue_id: str, draft_reply: str | None = None, status: str | None = None, note: str | None = None) -> dict[str, Any]:
    queue, item = _find_queue_item(queue_id)
    if draft_reply is not None:
        item["draft_reply"] = draft_reply.strip()
    if status is not None:
        item["status"] = status
    if note is not None:
        item["note"] = note
    item["updated_at"] = _now()
    _save_queue(queue)
    return item


def _type_into_x_composer(message: str):
    driver = _get_driver()
    wait = WebDriverWait(driver, 12)
    composer = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "[data-testid='tweetTextarea_0']"))
    )
    ActionChains(driver).move_to_element(composer).click().perform()
    _human_type(composer, message)
    return composer


def _submit_x_composer():
    driver = _get_driver()
    wait = WebDriverWait(driver, 12)
    submit = wait.until(
        EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            "button[data-testid='tweetButton']:not([aria-disabled='true']), button[data-testid='tweetButtonInline']:not([aria-disabled='true'])",
        ))
    )
    _human_click(driver, submit)
    time.sleep(1.2)
    return {
        "url": driver.current_url,
        "title": driver.title,
    }


def publish_x_post(text: str) -> dict[str, Any]:
    """
    X üzerinde yeni bir post yayınlar.

    Args:
        text: Yayınlanacak metin. 240 karakteri geçmemesi önerilir.
    """
    message = (text or "").strip()
    if not message:
        raise ValueError("Post metni boş olamaz")
    if len(message) > 240:
        raise ValueError("Post metni 240 karakteri geçemez")

    driver = _get_driver()
    driver.get("https://x.com/compose/post")
    _type_into_x_composer(message)
    result = _submit_x_composer()
    return {
        "status": "posted",
        "length": len(message),
        "text": message,
        **result,
    }


def reply_to_x_post(tweet_url: str, message: str) -> dict[str, Any]:
    """
    Belirli bir X postuna reply yollar.

    Args:
        tweet_url: Hedef post URL'si
        message: Reply metni
    """
    target_url = _normalize_x_status_url(tweet_url)
    reply_text = (message or "").strip()
    if not target_url:
        raise ValueError("Tweet URL boş olamaz")
    if not reply_text:
        raise ValueError("Reply metni boş olamaz")
    if len(reply_text) > 240:
        raise ValueError("Reply metni 240 karakteri geçemez")

    driver = _get_driver()
    driver.get(target_url)
    wait = WebDriverWait(driver, 12)
    reply_button = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='reply']"))
    )
    _human_click(driver, reply_button)
    _type_into_x_composer(reply_text)
    result = _submit_x_composer()
    return {
        "status": "sent",
        "tweet_url": target_url,
        "length": len(reply_text),
        "text": reply_text,
        **result,
    }


def send_x_reply(queue_id: str, message: str | None = None) -> dict[str, Any]:
    queue, item = _find_queue_item(queue_id)

    reply_text = (message or item.get("draft_reply") or "").strip()
    if not reply_text:
        raise ValueError("Gönderilecek reply metni boş olamaz")

    tweet_url = item.get("tweet_url")
    tweet_id = item.get("platform_comment_id")
    if not tweet_url or not tweet_id:
        raise ValueError("Tweet URL veya tweet ID eksik")

    result = reply_to_x_post(tweet_url, reply_text)

    item["status"] = "sent"
    item["sent_reply"] = reply_text
    item["last_error"] = ""
    item["updated_at"] = _now()
    _save_queue(queue)
    return {**item, "result": result}


def mark_queue_item(queue_id: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in {"new", "drafted", "approved", "sent", "skipped", "error"}:
        raise ValueError(f"Geçersiz status: {status}")
    return update_queue_item(queue_id, status=status, note=note)
