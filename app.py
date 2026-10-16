from flask import Flask, request, render_template_string
import os, requests, re, logging
app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "baptist2026")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID", "1360210040674355")

CHURCH_NAME_AR = "كنيسة الكتاب المقدس المعمدانية-القدس"

TAB_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>كنيسة الكتاب المقدس المعمدانية-القدس</title>
<style>
body{font-family:'Segoe UI',Tahoma,sans-serif;background:#0f172a;color:white;margin:0}
.header{background:linear-gradient(135deg,#1e3a8a,#1e40af);padding:25px;text-align:center;border-bottom:4px solid #fbbf24}
.header h1{margin:0;font-size:26px;color:#fbbf24}
.tabs{display:flex;justify-content:center;gap:10px;padding:15px;background:#1e293b}
.tab-btn{padding:10px 20px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;background:#334155;color:white}
.tab-btn.active{background:#fbbf24;color:#0f172a}
.chat-box{max-width:700px;margin:20px auto;background:#1e293b;border-radius:12px;padding:15px;min-height:300px}
.msg{margin:10px 0;padding:12px;border-radius:10px;max-width:80%;line-height:1.6}
.bot{background:#334155;border-right:4px solid #fbbf24}
.user{background:#2563eb;margin-left:auto}
.quick{display:flex;flex-wrap:wrap;gap:8px;margin:15px 0}
.q-btn{background:#0f172a;border:1px solid #fbbf24;color:#fbbf24;padding:8px 12px;border-radius:20px;cursor:pointer}
.input-area{display:flex;gap:10px;margin-top:15px}
.input-area input{flex:1;padding:12px;border-radius:25px;border:none;background:#0f172a;color:white}
.input-area button{background:#fbbf24;border:none;padding:12px 20px;border-radius:25px;font-weight:bold;cursor:pointer}
.footer{text-align:center;padding:15px;color:#64748b;font-size:12px}
</style>
</head>
<body>
<div class="header"><h1>كنيسة الكتاب المقدس المعمدانية-القدس</h1></div>
<div class="tabs">
<button class="tab-btn active" onclick="switchTab('ar',event)">العربية - فاندايك فقط</button>
<button class="tab-btn" onclick="switchTab('en',event)">English - KJV ONLY</button>
</div>
<div class="chat-box" id="chatBox">
<div class="msg bot">مرحباً بكم في كنيسة الكتاب المقدس المعمدانية-القدس 🙏</div>
</div>
<div style="max-width:700px;margin:0 auto;padding:0 15px">
<div class="quick"><button class="q-btn" onclick="ask('كيف أخلص؟')">كيف أخلص؟</button><button class="q-btn" onclick="ask('ما هي المعمودية؟')">ما هي المعمودية؟</button><button class="q-btn" onclick="ask('أوقات الخدمة؟')">أوقات الخدمة؟</button></div>
<div class="input-area"><input id="userInput" placeholder="اكتب سؤالك..."><button onclick="send()">إرسال</button></div>
</div>
<script>
function switchTab(l,e){document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));e.target.classList.add('active')}
function ask(q){document.getElementById('userInput').value=q;send()}
function send(){let i=document.getElementById('userInput');let t=i.value.trim();if(!t)return;let b=document.getElementById('chatBox');let d=document.createElement('div');d.className='msg user';d.innerText=t;b.appendChild(d);i.value='';}
</script>
</body>
</html>
"""

@app.route('/tab')
def tab_page(): return render_template_string(TAB_HTML)
@app.route('/')
def home(): return {"status":"Ready","tab":"/tab"}
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
            if sid and sid!=PAGE_ID:
                txt=ev.get('message',{}).get('text','')
                if txt and PAGE_ACCESS_TOKEN:
                    requests.post(f"https://graph.facebook.com/v21.0/me/messages", params={"access_token":PAGE_ACCESS_TOKEN}, json={"recipient":{"id":sid},"message":{"text":f"من {CHURCH_NAME_AR}: {txt}"}}, timeout=10)
    return "ok",200

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))
