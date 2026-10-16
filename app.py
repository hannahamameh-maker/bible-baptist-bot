from flask import Flask, request, render_template_string
import os
import requests
import re
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "baptist2026")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "[STRIPPED 211 bytes]")
PAGE_ID = os.getenv("PAGE_ID", "1360210040674355")

CHURCH_NAME_AR = "كنيسة الكتاب المقدس المعمدانية-القدس"

TAB_HTML = """
<!DOCTYPE html><html dir="rtl" lang="ar"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>كنيسة الكتاب المقدس المعمدانية-القدس</title>
<style>
body{font-family:Tahoma;background:#0f172a;color:#fff;margin:0}
.header{background:linear-gradient(135deg,#1e3a8a,#1e40af);padding:25px;text-align:center;border-bottom:4px solid #fbbf24}
.header h1{margin:0;color:#fbbf24;font-size:26px}
.tabs{display:flex;justify-content:center;gap:10px;padding:15px;background:#1e293b}
.tab-btn{padding:10px 20px;border:none;border-radius:8px;background:#334155;color:#fff;font-weight:bold}
.tab-btn.active{background:#fbbf24;color:#0f172a}
.box{max-width:700px;margin:20px auto;background:#1e293b;border-radius:12px;padding:15px}
.msg{padding:12px;border-radius:10px;background:#334155;border-right:4px solid #fbbf24}
</style></head><body>
<div class="header"><h1>كنيسة الكتاب المقدس المعمدانية-القدس</h1></div>
<div class="tabs"><button class="tab-btn active">العربية - فاندايك فقط</button><button class="tab-btn">English - KJV ONLY</button></div>
<div class="box"><div class="msg">مرحباً بكم في كنيسة الكتاب المقدس المعمدانية-القدس 🙏</div></div>
</body></html>
"""

@app.after_request
def no_cache(r):
    r.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return r

@app.route('/')
def home(): return render_template_string(TAB_HTML)

@app.route('/tab')
def tab_page(): return render_template_string(TAB_HTML)

def detect_language(text):
    return 'ar' if re.search(r'[\u0600-\u06FF]', text) else 'en'

def get_answer(text):
    lang = detect_language(text)
    if 'خلاص' in text.lower() or 'saved' in text.lower():
        return "فاندايك: لأَنَّكُمْ بِالنِّعْمَةِ مُخَلَّصُونَ - أفسس 2:8" if lang=='ar' else "KJV: For by grace are ye saved - Eph 2:8"
    return f"من {CHURCH_NAME_AR}: {text}"

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge'), 200
    return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json()
    if not data or data.get('object') != 'page':
        return "ok", 200
    for entry in data.get('entry', []):
        for ev in entry.get('messaging', []):
            sid = ev.get('sender', {}).get('id')
            if not sid or sid == PAGE_ID:
                continue
            txt = ev.get('message', {}).get('text', '')
            if txt:
                try:
                    requests.post("https://graph.facebook.com/v21.0/me/messages",
                        params={"access_token": PAGE_ACCESS_TOKEN},
                        json={"recipient": {"id": sid}, "message": {"text": get_answer(txt)[:1900]}},
                        timeout=10)
                except Exception as e:
                    app.logger.error(e)
    return "ok", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
