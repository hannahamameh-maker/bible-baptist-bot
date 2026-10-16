from flask import Flask, request, render_template_string
import os
import requests
import re
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "baptist2026")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID", "1360210040674355")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

CHURCH_NAME_AR = "كنيسة الكتاب المقدس المعمدانية-القدس"
CHURCH_NAME_EN = "Bible Baptist Church-Jerusalem"

# --- التاب بعد المسح ---
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
.chat-box { max-width:700px; margin:20px auto; background:#1e293b; border-radius:12px; padding:15px; min-height:350px; }
.msg { margin:10px 0; padding:12px; border-radius:10px; max-width:80%; line-height:1.6; white-space: pre-wrap; }
.user { background:#2563eb; margin-left:auto; text-align:left; }
.bot { background:#334155; border-right:4px solid #fbbf24; }
.quick { display:flex; flex-wrap:wrap; gap:8px; margin:15px 0; }
.q-btn { background:#0f172a; border:1px solid #fbbf24; color:#fbbf24; padding:8px 12px; border-radius:20px; cursor:pointer; font-size:13px; }
.q-btn:hover { background:#fbbf24; color:#0f172a; }
.input-area { display:flex; gap:10px; margin-top:15px; }
.input-area input { flex:1; padding:12px; border-radius:25px; border:none; background:#0f172a; color:white; }
.input-area button { background:#fbbf24; border:none; padding:12px 20px; border-radius:25px; font-weight:bold; cursor:pointer; }
.verse { color:#fbbf24; font-weight:bold; margin-top:8px; display:block; font-size:13px; }
.footer { text-align:center; padding:15px; color:#64748b; font-size:12px; }
</style>
</head>
<body>

<div class="header">
<h1>كنيسة الكتاب المقدس المعمدانية-القدس</h1>
</div>

<div class="tabs">
<button class="tab-btn active" onclick="switchTab('ar', event)">العربية - فاندايك فقط</button>
<button class="tab-btn" onclick="switchTab('en', event)">English - KJV ONLY</button>
</div>

<div class="chat-box" id="chatBox">
<div class="msg bot">مرحباً بكم في <b>كنيسة الكتاب المقدس المعمدانية-القدس</b> 🙏</div>
</div>

<div style="max-width:700px; margin:0 auto; padding:0 15px;">
<div class="quick" id="quickAr">
<button class="q-btn" onclick="ask('كيف أخلص؟')">كيف أخلص؟</button>
<button class="q-btn" onclick="ask('ما هي المعمودية؟')">ما هي المعمودية؟</button>
<button class="q-btn" onclick="ask('هل أفقد خلاصي؟')">هل أفقد خلاصي؟</button>
<button class="q-btn" onclick="ask('أي ترجمة تستخدمون؟')">أي ترجمة؟</button>
<button class="q-btn" onclick="ask('أوقات الخدمة؟')">أوقات الخدمة؟</button>
</div>
<div class="quick" id="quickEn" style="display:none;">
<button class="q-btn" onclick="ask('How to be saved?')">How to be saved?</button>
<button class="q-btn" onclick="ask('What is baptism?')">Baptism?</button>
<button class="q-btn" onclick="ask('Why KJV only?')">Why KJV only?</button>
<button class="q-btn" onclick="ask('Can I lose salvation?')">Eternal security?</button>
</div>

<div class="input-area">
<input type="text" id="userInput" placeholder="اكتب سؤالك من الكتاب المقدس..." onkeypress="if(event.key==='Enter') send()">
<button onclick="send()">إرسال</button>
</div>
</div>

<div class="footer">Bible Baptist Church-Jerusalem | كنيسة الكتاب المقدس المعمدانية-القدس<br>1.6K followers - Arabic and English - KJV Only / فاندايك فقط</div>

<script>
let lang='ar';
const answers={
ar:{
"كيف أخلص": "الخلاص: 'لأَنَّكُمْ بِالنِّعْمَةِ مُخَلَّصُونَ، بِالإِيمَانِ' - أفسس 2:8-9 (فاندايك)\\nKJV: 'For by grace are ye saved through faith' - Eph 2:8 KJV",
"معمودية": "'مَنْ آمَنَ وَاعْتَمَدَ خَلَصَ' - مرقس 16:16 (فاندايك)\\nالمعمودية بالتغطيس للمؤمنين فقط بعد الخلاص",
"خلاصي": "'خِرَافِي تَسْمَعُ صَوْتِي... وَلَنْ تَهْلِكَ إِلَى الأَبَدِ' - يوحنا 10:27-28 (فاندايك)",
"ترجمة": "نستعمل سميث وفاندايك فقط في العربي، وKJV فقط في الإنجليزي.",
"خدمة": "خدمات كنيسة الكتاب المقدس المعمدانية-القدس:\\nالأحد 11:00 صباحاً - عبادة\\nالأربعاء 7:00 مساءً - دراسة كتاب"
},
en:{
"saved": "KJV: 'For by grace are ye saved through faith' - Ephesians 2:8-9 KJV",
"baptism": "KJV: 'He that believeth and is baptized shall be saved' - Mark 16:16 KJV\\nBaptism by immersion for believers only AFTER salvation.",
"kjv": "KJV ONLY: 'The words of the LORD are pure words... Thou shalt keep them' - Psalm 12:6-7 KJV",
"security": "KJV: 'And I give unto them eternal life; and they shall never perish' - John 10:28 KJV"
}
};

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
 t=t.toLowerCase();
 let dict=lang==='ar'?answers.ar:answers.en;
 for(let k in dict){ if(t.includes(k) || k.includes(t)) return dict[k]; }
 return lang==='ar'? "سؤالك: '"+t+"'\\nاسأل: كيف أخلص؟ معمودية؟" : "Your question: '"+t+"'\\nAsk: How to be saved? Baptism? Why KJV?";
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
    return {"status": f"{CHURCH_NAME_AR} - عربي فاندايك فقط | English KJV ONLY - Tab Ready", "tab_url": "/tab"}

@app.route('/tab')
def tab_page():
    return render_template_string(TAB_HTML)

def detect_language(text):
    if re.search(r'[\u0600-\u06FF]', text):
        return 'ar'
    return 'en'

def get_answer(user_text):
    lang = detect_language(user_text)
    t = user_text.lower()
    if any(k in t for k in ['أي ترجمة', 'فاندايك', 'which bible', 'kjv']):
        if lang == 'ar':
            return f"{CHURCH_NAME_AR}\n\nنستعمل: عربي = سميث وفاندايك فقط\nإنجليزي = KJV فقط\n\n'كُلُّ الْكِتَابِ هُوَ مُوحًى بِهِ مِنَ اللهِ' - 2 تيمو 3:16 (فاندايك)"
        else:
            return f"{CHURCH_NAME_EN}\nKJV ONLY in English, Smith & Van Dyke ONLY in Arabic\n2 Tim 3:16 KJV"
    if any(k in t for k in ['مرحبا', 'سلام', 'hello']):
        if lang == 'ar':
            return f"مرحباً بكم في {CHURCH_NAME_AR} 🙏"
        else:
            return f"Welcome to {CHURCH_NAME_EN} 🙏"
    if 'خلاص' in t or 'saved' in t:
        return "فاندايك: 'لأَنَّكُمْ بِالنِّعْمَةِ مُخَلَّصُونَ' - أفسس 2:8-9\nKJV: 'For by grace are ye saved through faith' - Eph 2:8 KJV" if lang=='ar' else "KJV: 'For by grace are ye saved through faith' - Eph 2:8 KJV"
    return f"شكراً: '{user_text}'\nمن {CHURCH_NAME_AR}" if lang=='ar' else f"Thanks: '{user_text}'\nFrom {CHURCH_NAME_EN}"

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        return challenge, 200
    else:
        return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json()
    if not data or data.get('object')!= 'page':
        return "ok", 200
    for entry in data.get('entry', []):
        if 'messaging' in entry:
            for ev in entry['messaging']:
                if 'message' in ev:
                    sid = ev['sender']['id']
                    if sid == PAGE_ID:
                        continue
                    text = ev['message'].get('text', '')
                    if text:
                        reply = get_answer(text)
                        send_message(sid, reply)
        if 'changes' in entry:
            for change in entry['changes']:
                if change['field'] == 'feed':
                    v = change['value']
                    if v.get('item') == 'comment' and v.get('verb') == 'add':
                        cid = v.get('comment_id')
                        fid = v.get('from', {}).get('id')
                        msg = v.get('message', '')
                        if fid == PAGE_ID or not cid or not msg:
                            continue
                        ans = get_answer(msg)
                        if len(ans) > 800:
                            ans = ans[:780] + "..."
                        reply_to_comment(cid, ans)
    return "ok", 200

def send_message(rid, txt):
    if not PAGE_ACCESS_TOKEN:
        app.logger.error("PAGE_ACCESS_TOKEN missing")
        return
    try:
        params = {"access_token": PAGE_ACCESS_TOKEN}
        headers = {"Content-Type": "application/json"}
        if len(txt) > 1900:
            txt = txt[:1900] + "..."
        data = {"recipient": {"id": rid}, "message": {"text": txt}}
        requests.post("https://graph.facebook.com/v21.0/me/messages", params=params, headers=headers, json=data, timeout=10)
    except Exception as e:
        app.logger.error(f"send_message failed: {e}")

def reply_to_comment(cid, txt):
    if not PAGE_ACCESS_TOKEN:
        return
    try:
        url = f"https://graph.facebook.com/v21.0/{cid}/comments"
        if len(txt) > 800:
            txt = txt[:800]
        params = {"access_token": PAGE_ACCESS_TOKEN, "message": txt}
        requests.post(url, params=params, timeout=10)
    except Exception as e:
        app.logger.error(f"reply_to_comment failed: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
