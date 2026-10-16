from flask import Flask, request, render_template_string
import os, requests, re, logging
app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "baptist2026")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "[STRIPPED 211 bytes]")
PAGE_ID = os.getenv("PAGE_ID", "1360210040674355")

TAB_HTML = """
<!DOCTYPE html><html dir="rtl" lang="ar"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>كنيسة الكتاب المقدس المعمدانية-القدس</title>
<style>
body{font-family:Tahoma;background:#0f172a;color:#fff;margin:0}
.header{background:linear-gradient(135deg,#1e3a8a,#1e40af);padding:25px;text-align:center;border-bottom:4px solid #fbbf24}
.header h1{margin:0;color:#fbbf24;font-size:26px}
.box{max-width:700px;margin:30px auto;background:#1e293b;border-radius:12px;padding:20px;text-align:center}
</style></head><body>
<div class="header"><h1>كنيسة الكتاب المقدس المعمدانية-القدس</h1></div>
<div class="box">مرحباً بكم في كنيسة الكتاب المقدس المعمدانية-القدس 🙏</div>
</body></html>
"""

@app.route('/')
def home(): return render_template_string(TAB_HTML)

@app.route('/tab')
def tab_page(): return render_template_string(TAB_HTML)

@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get('hub.mode')=='subscribe' and request.args.get('hub.verify_token')==VERIFY_TOKEN:
        return request.args.get('hub.challenge'),200
    return "fail",403

@app.route('/webhook', methods=['POST'])
def hook():
    data=request.get_json()
    if not data or data.get('object')!='page': return "ok",200
    for entry in data.get('entry',[]):
        for ev in entry.get('messaging',[]):
            sid=ev.get('sender',{}).get('id')
            if not sid or sid==PAGE_ID: continue
            txt=ev.get('message',{}).get('text','')
            if txt:
                try:
                    requests.post("https://graph.facebook.com/v21.0/me/messages",
                        params={"access_token":PAGE_ACCESS_TOKEN},
                        json={"recipient":{"id":sid},"message":{"text":txt[:1900]}},
                        timeout=10)
                except: pass
    return "ok",200

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))
