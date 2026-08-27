import base64
import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DB_PATH = Path(os.getenv("JADE_DB_PATH", ROOT / "jade_ai.sqlite3"))
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
MAX_IMAGE_BYTES = 8 * 1024 * 1024

SYSTEM_PROMPT = """你是“玉石 AI 顾问”，面向普通玉石消费者提供购买决策辅助。
你的第一原则不是让用户相信你，而是降低信息不对称和购买风险。

必须遵守：
1. 明确区分“AI 初步分析”和“专业鉴定”。任何情况下都不能仅凭照片保证真伪、天然、是否处理、产地或实验室检测结果。
2. 不保证升值，不制造焦虑，不虚构市场价格，不编造证书、检测数据、产地或交易记录。
3. 对不确定信息明确写“无法从当前信息确认”或“需要进一步核实”。
4. 图片分析只讨论可见特征，例如颜色、光泽、透明度表现、纹理、表面状态和可见瑕疵；不要把视觉特征直接等同于材质或真伪结论。
5. 价格只解释影响价格的因素和合理核验方法，除非用户提供可靠的市场/商品信息，否则不要给出伪精确价格。
6. 优先询问缺失的关键变量：产品类型、预算、用途、产地要求、品质要求；已有商品时优先要求图片和商品信息。
7. 回答普通消费者能看懂，专业术语必须解释。
8. 如果用户有明确购买意向，回答结尾给出下一步核验动作，并自然邀请人工咨询。

输出结构尽量包含：
- 初步判断
- 依据
- 风险提示
- 购买建议
- 下一步
"""


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT NOT NULL,
            source TEXT,
            product_interest TEXT,
            budget TEXT,
            location TEXT,
            user_question TEXT,
            image_uploaded INTEGER DEFAULT 0,
            ai_summary TEXT,
            lead_status TEXT DEFAULT 'NEW',
            created_at TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            image_uploaded INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )""")
        db.commit()


def now():
    return datetime.now(timezone.utc).isoformat()


def json_response(handler, status, payload):
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def call_ai(message, profile, image_data_url=None):
    if not AI_API_KEY:
        raise RuntimeError("AI_API_KEY is not configured")
    content = [{"type": "text", "text": json.dumps({"message": message, "profile": profile}, ensure_ascii=False)}]
    if image_data_url:
        content.append({"type": "image_url", "image_url": {"url": image_data_url}})
    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content}
        ],
        "temperature": 0.2
    }
    req = urllib.request.Request(
        f"{AI_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"AI provider error {exc.code}: {detail}") from exc
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("AI provider returned no choices")
    return choices[0].get("message", {}).get("content", "")


def save_conversation(session_id, role, content, image_uploaded=False):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("INSERT INTO conversations(session_id, role, content, image_uploaded, created_at) VALUES(?,?,?,?,?)", (session_id, role, content, int(image_uploaded), now()))
        db.commit()


def extract_profile(message, profile):
    profile = dict(profile or {})
    for key, patterns in {
        "product_interest": [r"翡翠", r"和田玉", r"手镯", r"吊坠", r"玉牌", r"手串", r"戒指"],
        "use": [r"日常", r"佩戴", r"收藏", r"送人"],
    }.items():
        for p in patterns:
            m = re.search(p, message)
            if m:
                profile[key] = m.group(0); break
    budget = re.search(r"(?:预算|大概|约|准备花)\s*([\d,.]+\s*(?:万|元|块))", message)
    if budget:
        profile["budget"] = budget.group(1)
    return profile


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path == "/api/health":
            return json_response(self, 200, {"ok": True, "ai_configured": bool(AI_API_KEY), "model": AI_MODEL})
        if self.path == "/api/admin/summary":
            with sqlite3.connect(DB_PATH) as db:
                today = datetime.now(timezone.utc).date().isoformat()
                consultations = db.execute("SELECT COUNT(DISTINCT session_id) FROM conversations WHERE created_at LIKE ?", (today + "%",)).fetchone()[0]
                leads = db.execute("SELECT COUNT(*) FROM leads WHERE created_at LIKE ?", (today + "%",)).fetchone()[0]
                qualified = db.execute("SELECT COUNT(*) FROM leads WHERE lead_status='QUALIFIED'").fetchone()[0]
                statuses = dict(db.execute("SELECT lead_status, COUNT(*) FROM leads GROUP BY lead_status").fetchall())
            return json_response(self, 200, {"today_consultations": consultations, "new_leads": leads, "qualified_leads": qualified, "statuses": statuses})
        if self.path == "/api/admin/leads":
            with sqlite3.connect(DB_PATH) as db:
                db.row_factory = sqlite3.Row
                rows = [dict(r) for r in db.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 100").fetchall()]
            return json_response(self, 200, {"leads": rows})
        if self.path == "/" or self.path == "/index.html":
            return self.serve_file(WEB / "index.html", "text/html; charset=utf-8")
        safe = (WEB / self.path.lstrip("/")).resolve()
        if WEB.resolve() in safe.parents and safe.is_file():
            content_type = "text/plain; charset=utf-8"
            if safe.suffix == ".css": content_type = "text/css; charset=utf-8"
            if safe.suffix == ".js": content_type = "application/javascript; charset=utf-8"
            return self.serve_file(safe, content_type)
        json_response(self, 404, {"error": "Not found"})

    def serve_file(self, path, content_type):
        raw = path.read_bytes()
        self.send_response(200); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 12 * 1024 * 1024: raise ValueError("Request too large")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_POST(self):
        try:
            data = self.read_json()
            if self.path == "/api/chat":
                message = str(data.get("message", "")).strip()
                if not message: return json_response(self, 400, {"error": "message is required"})
                profile = extract_profile(message, data.get("profile"))
                image = data.get("image")
                if image and (not image.startswith("data:image/") or len(image) > 12 * 1024 * 1024):
                    return json_response(self, 400, {"error": "invalid image payload"})
                session_id = str(data.get("session_id") or "anonymous")[:128]
                answer = call_ai(message, profile, image)
                save_conversation(session_id, "user", message, bool(image)); save_conversation(session_id, "assistant", answer)
                return json_response(self, 200, {"answer": answer, "profile": profile})
            if self.path == "/api/leads":
                contact = str(data.get("contact", "")).strip()
                if not contact: return json_response(self, 400, {"error": "contact is required"})
                with sqlite3.connect(DB_PATH) as db:
                    db.execute("INSERT INTO leads(name,contact,source,product_interest,budget,location,user_question,image_uploaded,ai_summary,lead_status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                        str(data.get("name", ""))[:100], contact[:200], str(data.get("source", "web"))[:50], str(data.get("product_interest", ""))[:200], str(data.get("budget", ""))[:100], str(data.get("location", ""))[:100], str(data.get("user_question", ""))[:2000], int(bool(data.get("image_uploaded"))), str(data.get("ai_summary", ""))[:4000], "NEW", now()))
                    db.commit()
                return json_response(self, 201, {"ok": True, "status": "NEW"})
            return json_response(self, 404, {"error": "Not found"})
        except Exception as exc:
            return json_response(self, 500, {"error": str(exc)})


if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", "8000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
