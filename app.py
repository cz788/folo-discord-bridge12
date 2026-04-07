from flask import Flask, request, jsonify
import os
import re
import httpx

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
FILTER_KEYWORDS = [k.strip() for k in os.getenv("FILTER_KEYWORDS", "AI,人工智能").split(",") if k.strip()]
EXCLUDE_KEYWORDS = [k.strip() for k in os.getenv("EXCLUDE_KEYWORDS", "广告").split(",") if k.strip()]

def send_to_discord(entry, feed):
    if not DISCORD_WEBHOOK_URL:
        return False
    title = (entry.get("title") or "无标题")[:256]
    desc = re.sub(r'<[^>]+>', '', entry.get("description") or entry.get("content") or "")[:500]
    payload = {"embeds": [{"title": title, "description": desc, "url": entry.get("url", ""), "color": 3447003, "footer": {"text": f"来源: {feed.get('title', 'Unknown')}"}, "timestamp": entry.get("publishedAt", "")}]}
    try:
        with httpx.Client() as client:
            r = client.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10.0)
            return r.status_code in [200, 204]
    except:
        return False

def should_forward(entry, feed):
    text = f"{entry.get('title', '')} {entry.get('description', '')} {entry.get('content', '')}".lower()
    for k in EXCLUDE_KEYWORDS:
        if k.lower() in text:
            return False, f"排除: {k}"
    if FILTER_KEYWORDS:
        for k in FILTER_KEYWORDS:
            if k.lower() in text:
                return True, f"匹配: {k}"
        return False, "无关键词"
    return True, "全部"

@app.route("/webhook/folo", methods=["POST"])
def receive():
    data = request.get_json() or {}
    entry, feed = data.get("entry", {}), data.get("feed", {})
    ok, reason = should_forward(entry, feed)
    if ok:
        send_to_discord(entry, feed)
    return jsonify({"status": "success" if ok else "skipped", "reason": reason})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/")
def index():
    return jsonify({"service": "Folo Discord Bridge", "version": "1.0"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
