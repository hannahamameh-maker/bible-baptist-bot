from flask import Flask, request, render_template_string
import os
import requests
import re
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "EAAN5XZCCZCTT4BSrXLBvtWEjL6ZCZBdgs3XvQDuJMrK0QUTFWznDk9a4MqJnVCpwZAhuec7X81RTnZCjcYFDM99uhpCkqLPaE6xxZAKFjY2ZA9vwhnZAVgofnZCcKtcoPxUQt4jmWR73d04iPxXRMhk9ZC7SElfEtcAspZBFAFIq0QFYXv8DOBhy6RsJ0f6LAZCSxByqhfOpRbugZD")
PAGE_ACCESS_TOKEN = os.getenv("EAAN5XZCCZCTT4BSrXLBvtWEjL6ZCZBdgs3XvQDuJMrK0QUTFWznDk9a4MqJnVCpwZAhuec7X81RTnZCjcYFDM99uhpCkqLPaE6xxZAKFjY2ZA9vwhnZAVgofnZCcKtcoPxUQt4jmWR73d04iPxXRMhk9ZC7SElfEtcAspZBFAFIq0QFYXv8DOBhy6RsJ0f6LAZCSxByqhfOpRbugZD")
PAGE_ID = os.getenv("PAGE_ID", "1360210040674355")

CHURCH_NAME_AR = "كنيسة الكتاب المقدس المعمدانية-القدس"
CHURCH_NAME_EN = "Bible Baptist Church-Jerusalem"

TAB_HTML = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>كنيسة الكتاب المقدس المعمدانية-القدس</title>
<style>
body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: white; margin:0; padding:0; }
.header { background: linear-gradient(135deg, #1e3a8a, #1e40af); padding: 20px; text-align:center; border-bottom: 4px solid #fbbf24; }
.header h1 { margin:0; font-size: 26px; color: #fbbf24; }
.tabs { display:flex; justify-content:center; gap:10px; padding:15px; background:#1e293b; }
.tab-btn { padding:10px 20px; border:none; border-radius:8px; cursor:pointer; font-weight:bold; background:#334155; color:white; }
.tab-btn.active { background:#fbbf24; color:#0f172a; }
.chat-box { max-width:700px; margin:20px auto; background:#1e293b; border-radius:12px; padding:15px; min-height:400px; overflow-y:auto; }
.msg { margin:10px 0; padding:12px; border-radius:10px; max-width:80%; line-height:1.6; white-space: pre-wrap; }
.user { background:#2563eb; margin-left:auto; text-align:left; }
.bot { background:#334155; border-right:4px solid #fbbf24; }
.quick { display:flex; flex-wrap:wrap; gap:8px; margin:15px 0; }
.q-btn { background:#0f172a; border:1px solid #fbbf24; color:#fbbf24; padding:8px 12px; border-radius:20px; cursor:pointer; font-size:13px; }
.q-btn:hover { background:#fbbf24; color:#0f172a; }
.input-area { display:flex; gap:10px; margin-top:15px; }
.input-area input { flex:1; padding:12px; border-radius:25px; border:none; background:#0f172a; color:white; }
.input-area button { background:#fbbf24; border:none; padding:12px 20px; border-radius:25px; font-weight:bold; cursor:pointer; }
.footer { text-align:center; padding:15px; color:#64748b; font-size:12px; }
</style>
</head>
<body>
<div class="header">
<h1>كنيسة الكتاب المقدس المعمدانية-القدس</h1>
<p>Bible Baptist Church-Jerusalem</p>
</div>

<div class="tabs">
<button class="tab-btn active" onclick="switchTab('ar', event)">العربية - فاندايك فقط</button>
<button class="tab-btn" onclick="switchTab('en', event)">English - KJV ONLY</button>
</div>

<div class="chat-box" id="chatBox">
<div class="msg bot">مرحباً بكم في <b>كنيسة الكتاب المقدس المعمدانية-القدس</b> 🙏<br><br>أهلاً وسهلاً! أنا مساعد الكتاب المقدس. أسألني أي سؤال من الكتاب المقدس بفكر معمداني مستقل.</div>
</div>

<div style="max-width:700px; margin:0 auto; padding:0 15px;">
<div class="quick" id="quickAr">
<button class="q-btn" onclick="ask('كيف أخلص؟')">كيف أخلص؟</button>
<button class="q-btn" onclick="ask('ما هي المعمودية؟')">ما هي المعمودية؟</button>
<button class="q-btn" onclick="ask('هل أفقد خلاصي؟')">هل أفقد خلاصي؟</button>
<button class="q-btn" onclick="ask('أي ترجمة تستخدمون؟')">أي ترجمة؟</button>
</div>
<div class="quick" id="quickEn" style="display:none;">
<button class="q-btn" onclick="ask('How to be saved?')">How to be saved?</button>
<button class="q-btn" onclick="ask('What is baptism?')">Baptism?</button>
<button class="q-btn" onclick="ask('Why KJV only?')">Why KJV only?</button>
</div>
<div class="input-area">
<input type="text" id="userInput" placeholder="اكتب سؤالك من الكتاب المقدس..." onkeypress="if(event.key==='Enter') send()">
<button onclick="send()">إرسال</button>
</div>
</div>

<script>
let lang='ar';
function switchTab(l, e){
 lang=l;
 document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
 e.target.classList.add('active');
 document.getElementById('quickAr').style.display=l==='ar'?'flex':'none';
 document.getElementById('quickEn').style.display=l==='en'?'flex':'none';
 document.getElementById('userInput').placeholder=l==='ar'?'اكتب سؤالك من الكتاب المقدس...':'Ask a Bible question...';
}
function ask(q){ document.getElementById('userInput').value=q; send(); }
function send(){
 let input=document.getElementById('userInput');
 let text=input.value.trim();
 if(!text) return;
 addMsg(text,'user');
 input.value='';
 setTimeout(()=>{ addMsg(findAnswer(text),'bot'); }, 400);
}
function findAnswer(t){ 
 // نفس منطقك القديم - تقدر تطوره لاحقا
 t=t.toLowerCase();
 if(t.includes('خلص') || t.includes('saved')) return "فاندايك: 'لأَنَّكُمْ بِالنِّعْمَةِ مُخَلَّصُونَ' - أفسس 2:8\\nKJV: 'For by grace are ye saved through faith' - Eph 2:8";
 return "من "+ (lang==='ar'?"كنيسة الكتاب المقدس المعمدانية-القدس - فاندايك فقط":"Bible Baptist Church-Jerusalem - KJV ONLY") + "\\n'فَتِّشُوا الْكُتُبَ' - يوحنا 5:39";
}
function addMsg(txt,type){
 let box=document.getElementById('chatBox');
 let div=document.createElement('div');
 div.className='msg '+type;
 div.innerText=txt;
 box.appendChild(div);
 box.scrollTop=box.scrollHeight;
}
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return {"status": f"{CHURCH_NAME_AR} - Ready", "tab_url": "/tab"}

@app.route('/tab')
def tab_page():
    return render_template_string(TAB_HTML)

def detect_language(text):
    return 'ar' if re.search(r'[\u0600-\u06FF]', text) else 'en'

def get_answer(user_text):
    lang = detect_language(user_text)
    t = user_text.lower()
    if any(k in t for k in ['أي ترجمة', 'فاندايك', 'which bible', 'kjv']):
        return f"{CHURCH_NAME_AR}\nعربي = سميث وفاندايك فقط\nEnglish = KJV ONLY\n2 تيمو 3:16" if lang=='ar' else f"{CHURCH_NAME_EN}\nKJV ONLY + Van Dyke ONLY\n2 Tim 3:16 KJV"
    if 'خلاص' in t or 'saved' in t:
        return "فاندايك: 'لأَنَّكُمْ بِالنِّعْمَةِ مُخَلَّصُونَ' - أفسس 2:8-9\nKJV: Eph 2:8" if lang=='ar' else "KJV: 'For by grace are ye saved through faith' - Eph 2:8 KJV"
    return f"شكراً: '{user_text}'\nمن {CHURCH_NAME_AR}\nفاندايك فقط + KJV فقط" if lang=='ar' else f"Thanks: '{user_text}'\nFrom {CHURCH_NAME_EN}\nKJV ONLY"

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
            if not sid or sid == PAGE_ID: continue
            text = ev.get('message', {}).get('text', '')
            if text:
                reply = get_answer(text)
                send_message(sid, reply)
        for change in entry.get('changes', []):
            if change.get('field') == 'feed':
                v = change.get('value', {})
                if v.get('item') == 'comment' and v.get('verb') == 'add':
                    cid, fid, msg = v.get('comment_id'), v.get('from', {}).get('id'), v.get('message','')
                    if not cid or not msg or fid == PAGE_ID: continue
                    ans = get_answer(msg)[:780]
                    reply_to_comment(cid, ans)
    return "ok", 200

def send_message(rid, txt):
    if not PAGE_ACCESS_TOKEN: 
        app.logger.error("PAGE_ACCESS_TOKEN missing")
        return
    try:
        requests.post("https://graph.facebook.com/v21.0/me/messages",
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={"recipient": {"id": rid}, "message": {"text": txt[:1900]}},
            timeout=10).raise_for_status()
    except Exception as e:
        app.logger.error(f"send_message failed: {e}")

def reply_to_comment(cid, txt):
    if not PAGE_ACCESS_TOKEN: return
    try:
        requests.post(f"https://graph.facebook.com/v21.0/{cid}/comments",
            params={"access_token": PAGE_ACCESS_TOKEN, "message": txt[:780]},
            timeout=10).raise_for_status()
    except Exception as e:
        app.logger.error(f"reply_to_comment failed: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
