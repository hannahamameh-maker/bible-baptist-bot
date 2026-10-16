from flask import Flask, request, render_template_string
import os
import requests
import re

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "baptist2026")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID", "1360210040674355")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# الاسم الجديد بالضبط كما طلبت
CHURCH_NAME_AR = "كنيسة الكتاب المقدس المعمدانية-القدس"
CHURCH_NAME_EN = "Bible Baptist Church-Jerusalem"

# --- صفحة التاب المستقلة داخل الفيسبوك ---
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
.header p { margin:5px 0 0; color: #cbd5e1; font-size:14px; }
.tabs { display:flex; justify-content:center; gap:10px; padding:15px; background:#1e293b; }
.tab-btn { padding:10px 20px; border:none; border-radius:8px; cursor:pointer; font-weight:bold; background:#334155; color:white; }
.tab-btn.active { background:#fbbf24; color:#0f172a; }
.chat-box { max-width:700px; margin:20px auto; background:#1e293b; border-radius:12px; padding:15px; min-height:400px; }
.msg { margin:10px 0; padding:12px; border-radius:10px; max-width:80%; line-height:1.6; }
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
<p>الكتاب المقدس: عربي = سميث وفاندايك فقط | English = KJV ONLY - Independent Baptist</p>
<p>أعمال 4:12 - وليس بأحد غيره الخلاص</p>
</div>

<div class="tabs">
<button class="tab-btn active" onclick="switchTab('ar')">العربية - فاندايك فقط</button>
<button class="tab-btn" onclick="switchTab('en')">English - KJV ONLY</button>
</div>

<div class="chat-box" id="chatBox">
<div class="msg bot">مرحباً بكم في <b>كنيسة الكتاب المقدس المعمدانية-القدس</b> 🙏<br><br>أهلاً وسهلاً! أنا مساعد الكتاب المقدس. أسألني أي سؤال من الكتاب المقدس بفكر معمداني مستقل.<br><br>العربي: سميث وفاندايك فقط<br>English: KJV ONLY<br><span class="verse">أعمال 4:12 - وليس بأحد غيره الخلاص</span></div>
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

<div class="footer">كنيسة الكتاب المقدس المعمدانية-القدس | Bible Baptist Church-Jerusalem<br>1.6K followers - Arabic and English - KJV Only / فاندايك فقط</div>

<script>
let lang='ar';
const answers={
ar:{
"كيف أخلص": "الخلاص: 'لأَنَّكُمْ بِالنِّعْمَةِ مُخَلَّصُونَ، بِالإِيمَانِ، وَذلِكَ لَيْسَ مِنْكُمْ. هُوَ عَطِيَّةُ اللهِ. لَيْسَ مِنْ أَعْمَال كَيْلاَ يَفْتَخِرَ أَحَدٌ' - أفسس 2:8-9 (فاندايك)\nKJV: 'For by grace are ye saved through faith' - Eph 2:8 KJV\nتُب وآمن أن يسوع مات لأجلك وقام.",
"معمودية": "'مَنْ آمَنَ وَاعْتَمَدَ خَلَصَ' - مرقس 16:16 (فاندايك)\nKJV: 'He that believeth and is baptized shall be saved' - Mark 16:16 KJV\nالمعمودية بالتغطيس للمؤمنين فقط بعد الخلاص، رمز.",
"خلاصي": "'خِرَافِي تَسْمَعُ صَوْتِي... وَلَنْ تَهْلِكَ إِلَى الأَبَدِ' - يوحنا 10:27-28 (فاندايك)\nKJV: 'they shall never perish' - John 10:28 KJV\nمرة مخلص دائماً مخلص.",
"ترجمة": "نستعمل سميث وفاندايك فقط في العربي، وKJV فقط في الإنجليزي.\nنرفض NIV وESV لأنها تحذف آيات مثل 1 يوحنا 5:7\n'كُلُّ الْكِتَابِ هُوَ مُوحًى بِهِ مِنَ اللهِ' - 2 تيمو 3:16 (فاندايك)\nKJV: 'All scripture is given by inspiration' - 2 Tim 3:16 KJV",
"خدمة": "خدمات كنيسة الكتاب المقدس المعمدانية-القدس:\nالأحد 11:00 صباحاً - عبادة\nالأربعاء 7:00 مساءً - دراسة كتاب (فاندايك)\nالقدس - نرحب بكم!"
},
en:{
"saved": "KJV: 'For by grace are ye saved through faith; and that not of yourselves: it is the gift of God: Not of works, lest any man should boast' - Ephesians 2:8-9 KJV\n(فاندايك): 'لأَنَّكُمْ بِالنِّعْمَةِ مُخَلَّصُونَ' - أفسس 2:8",
"baptism": "KJV: 'He that believeth and is baptized shall be saved' - Mark 16:16 KJV\nBaptism by immersion for believers only AFTER salvation, not for salvation.",
"kjv": "KJV ONLY: 'The words of the LORD are pure words... Thou shalt keep them, O LORD, thou shalt preserve them for ever' - Psalm 12:6-7 KJV\nWe reject NIV, ESV, NASB - they omit 1 John 5:7, Mark 16:9-20\nArabic: Smith & Van Dyke ONLY",
"security": "KJV: 'And I give unto them eternal life; and they shall never perish' - John 10:28 KJV\nOnce saved, always saved."
}
};

function switchTab(l){
lang=l;
document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
event.target.classList.add('active');
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
setTimeout(()=>{ 
let reply=findAnswer(text);
addMsg(reply,'bot');
},500);
}

function findAnswer(t){
t=t.toLowerCase();
let dict=lang==='ar'?answers.ar:answers.en;
for(let k in dict){ if(t.includes(k) || k.includes(t) || t.includes(k.split(' ')[0])) return dict[k]; }
// fallback
if(lang==='ar') return "سؤالك: '"+t+"'\n\nمن كنيسة الكتاب المقدس المعمدانية-القدس (فاندايك فقط + KJV فقط):\n\n'فَتِّشُوا الْكُتُبَ لأَنَّكُمْ تَظُنُّونَ أَنَّ لَكُمْ فِيهَا حَيَاةً أَبَدِيَّةً' - يوحنا 5:39 (فاندايك)\nKJV: 'Search the scriptures' - John 5:39 KJV\n\nاسأل: كيف أخلص؟ معمودية؟ KJV؟";
else return "Your question: '"+t+"'\n\nFrom كنيسة الكتاب المقدس المعمدانية-القدس - KJV ONLY + Van Dyke ONLY:\n\nKJV: 'Search the scriptures; for in them ye think ye have eternal life' - John 5:39 KJV\n\nAsk: How to be saved? Baptism? Why KJV?";
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

# --- باقي كود البوت (المسنجر والتعليقات) ---
def detect_language(text):
    if re.search(r'[\u0600-\u06FF]', text):
        return 'ar'
    return 'en'

def get_answer(user_text):
    lang = detect_language(user_text)
    t = user_text.lower()
    if any(k in t for k in ['أي ترجمة', 'كتاب مقدس', 'فاندايك', 'which bible', 'kjv']):
        if lang == 'ar':
            return f"كنيسة الكتاب المقدس المعمدانية-القدس\n\nنستعمل: عربي = سميث وفاندايك فقط\nإنجليزي = KJV فقط\n\n'كُلُّ الْكِتَابِ هُوَ مُوحًى بِهِ مِنَ اللهِ' - 2 تيمو 3:16 (فاندايك)\nKJV: 'All scripture is given by inspiration' - 2 Tim 3:16 KJV"
        else:
            return f"{CHURCH_NAME_EN}\nKJV ONLY in English, Smith & Van Dyke ONLY in Arabic\nPsalm 12:6-7 KJV - Preservation"
    if any(k in t for k in ['مرحبا', 'سلام', 'hello']):
        if lang == 'ar':
            return f"مرحباً بكم في {CHURCH_NAME_AR} 🙏\n\nأهلاً وسهلاً! الكتاب: فاندايك فقط + KJV فقط\nأعمال 4:12 - وليس بأحد غيره الخلاص\n\nاسألني: كيف أخلص؟ معمودية؟ KJV؟"
        else:
            return f"Welcome to {CHURCH_NAME_EN} 🙏\n\nBible: KJV ONLY + Van Dyke ONLY\nActs 4:12 KJV: Neither is there salvation in any other\n\nAsk: How to be saved? Baptism? KJV?"
    # باقي الأجوبة
    if 'خلاص' in t or 'saved' in t:
        return "فاندايك: 'لأَنَّكُمْ بِالنِّعْمَةِ مُخَلَّصُونَ، بِالإِيمَانِ' - أفسس 2:8-9\nKJV: 'For by grace are ye saved through faith' - Eph 2:8 KJV" if lang=='ar' else "KJV: 'For by grace are ye saved through faith' - Eph 2:8 KJV"
    return f"شكراً: '{user_text}'\nمن {CHURCH_NAME_AR}\nفاندايك فقط + KJV فقط - اسأل: كيف أخلص؟" if lang=='ar' else f"Thanks: '{user_text}'\nFrom {CHURCH_NAME_EN}\nKJV ONLY + Van Dyke ONLY"

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
    if data['object'] == 'page':
        for entry in data['entry']:
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
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    if len(txt) > 1900:
        txt = txt[:1900] + "..."
    data = {"recipient": {"id": rid}, "message": {"text": txt}}
    requests.post("https://graph.facebook.com/v21.0/me/messages", params=params, headers=headers, json=data)

def reply_to_comment(cid, txt):
    url = f"https://graph.facebook.com/v21.0/{cid}/comments"
    if len(txt) > 800:
        txt = txt[:800]
    params = {"access_token": PAGE_ACCESS_TOKEN, "message": txt}
    requests.post(url, params=params)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
