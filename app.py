from flask import Flask, request
import os
import requests
import re

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "baptist2026")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID", "1360210040674355")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # اختياري - للذكاء الاصطناعي الكامل

# =========================================================
# الكنيسة المعمدانية الكتابية المستقلة - القدس
# الكتاب المقدس: عربي = سميث وفاندايك فقط
#             إنجليزي = KJV فقط
# =========================================================

CHURCH_NAME_AR = "كنيسة الكتاب المقدس المعمدانية-القدس"
CHURCH_NAME_EN = "Bible Baptist Church-Jerusalem"

# --- العقيدة ---
BIBLE_AR = "نستعمل نسخة سميث وفاندايك فقط في العربية - كلمة الله المحفوظة المعصومة، المرجع الوحيد. 'كُلُّ الْكِتَابِ هُوَ مُوحًى بِهِ مِنَ اللهِ، وَنَافِعٌ لِلتَّعْلِيمِ وَالتَّوْبِيخِ' - 2 تيموثاوس 3:16 (فاندايك). نرفض الترجمات العربية الحديثة المحرفة."
BIBLE_EN = "We use KJV ONLY in English - The preserved, inspired, infallible Word of God. KJV: 'The words of the LORD are pure words: as silver tried in a furnace of earth, purified seven times. Thou shalt keep them, O LORD, thou shalt preserve them from this generation for ever' - Psalm 12:6-7 KJV. We reject NIV, ESV, NASB, NKJV, NLT."

def detect_language(text):
    if re.search(r'[\u0600-\u06FF]', text):
        return 'ar'
    return 'en'

def get_answer(user_text):
    lang = detect_language(user_text)
    t = user_text.lower()

    # --- سؤال عن الترجمات ---
    if any(k in t for k in ['أي ترجمة', 'أي نسخة', 'كتاب مقدس', 'فاندايك', 'smith', 'van dyke', 'which bible', 'bible version', 'kjv', 'niv', 'esv']):
        if lang == 'ar':
            return f"{BIBLE_AR}\n\n{BIBLE_EN}\n\nالعربي = سميث وفاندايك فقط\nالإنجليزي = KJV فقط"
        else:
            return f"{BIBLE_EN}\n\n{BIBLE_AR}\n\nArabic = Smith & Van Dyke ONLY\nEnglish = KJV ONLY"

    # --- الخلاص ---
    if any(k in t for k in ['خلاص', 'أخلص', 'كيف أخلص', 'salvation', 'how to be saved']):
        if lang == 'ar':
            return "الخلاص: 'لأَنَّكُمْ بِالنِّعْمَةِ مُخَلَّصُونَ، بِالإِيمَانِ، وَذلِكَ لَيْسَ مِنْكُمْ. هُوَ عَطِيَّةُ اللهِ. لَيْسَ مِنْ أَعْمَال كَيْلاَ يَفْتَخِرَ أَحَدٌ' - أفسس 2:8-9 (فاندايك)\nKJV: 'For by grace are ye saved through faith; and that not of yourselves: it is the gift of God: Not of works, lest any man should boast' - Eph 2:8-9 KJV"
        else:
            return "Salvation: KJV: 'For by grace are ye saved through faith; and that not of yourselves: it is the gift of God: Not of works, lest any man should boast' - Ephesians 2:8-9 KJV\n(فاندايك): 'لأَنَّكُمْ بِالنِّعْمَةِ مُخَلَّصُونَ، بِالإِيمَانِ' - أفسس 2:8-9"

    # --- معمودية ---
    if any(k in t for k in ['معمودية', 'baptism']):
        if lang == 'ar':
            return "'مَنْ آمَنَ وَاعْتَمَدَ خَلَصَ' - مرقس 16:16 (فاندايك)\nKJV: 'He that believeth and is baptized shall be saved' - Mark 16:16 KJV\nالمعمودية بالتغطيس للمؤمنين فقط بعد الخلاص، رمز لا يخلص."
        else:
            return "KJV: 'He that believeth and is baptized shall be saved' - Mark 16:16 KJV\n(فاندايك): 'مَنْ آمَنَ وَاعْتَمَدَ خَلَصَ' - مرقس 16:16\nBaptism by immersion for believers only AFTER salvation."

    # --- أمن أبدي ---
    if any(k in t for k in ['أفقد خلاصي', 'أمان أبدي', 'lose salvation', 'eternal security']):
        if lang == 'ar':
            return "'خِرَافِي تَسْمَعُ صَوْتِي... وَأَنَا أُعْطِيهَا حَيَاةً أَبَدِيَّةً، وَلَنْ تَهْلِكَ إِلَى الأَبَدِ' - يوحنا 10:27-28 (فاندايك)\nKJV: 'And I give unto them eternal life; and they shall never perish' - John 10:28 KJV\nمرة مخلص دائما مخلص."
        else:
            return "KJV: 'And I give unto them eternal life; and they shall never perish, neither shall any man pluck them out of my hand' - John 10:28 KJV\n(فاندايك): 'وَلَنْ تَهْلِكَ إِلَى الأَبَدِ' - يوحنا 10:28\nOnce saved, always saved."

    # --- ترحيب ---
    if any(k in t for k in ['مرحبا', 'سلام', 'hello', 'hi']):
        if lang == 'ar':
            return f"مرحباً! الرب يباركك! 🙏\n\n{CHURCH_NAME_AR}\nالكتاب المقدس: سميث وفاندايك فقط (عربي) + KJV فقط (إنجليزي)\n\nاسألني:\n- كيف أخلص؟\n- ما هي المعمودية؟\n- أي ترجمة تستخدمون؟\n- ما هو الأمن الأبدي؟"
        else:
            return f"Hello! God bless you! 🙏\n\n{CHURCH_NAME_EN}\nBible: KJV ONLY (English) + Smith & Van Dyke ONLY (Arabic)\n\nAsk me:\n- How to be saved?\n- What is baptism?\n- Which Bible version?\n- Eternal security?"

    # --- AI ---
    if OPENAI_API_KEY:
        try:
            ai = ask_ai(user_text, lang)
            if ai:
                return ai
        except:
            pass

    # افتراضي
    if lang == 'ar':
        return f"سؤالك: '{user_text}'\n\nالكتاب المقدس المستعمل: سميث وفاندايك فقط (عربي) و KJV فقط (إنجليزي)\n\n{BIBLE_AR}\n\nاسأل سؤال واضح مثل: كيف أخلص؟ ما هي المعمودية؟"
    else:
        return f"Question: '{user_text}'\n\nBible Used: KJV ONLY (English) + Smith & Van Dyke ONLY (Arabic)\n\n{BIBLE_EN}\n\nAsk clearly: How to be saved? What is baptism?"

def ask_ai(text, lang):
    sys_ar = "أنت مساعد معمداني مستقل KJV فقط. العربي فاندايك فقط، الإنجليزي KJV فقط. ترفض NIV و ESV. استعمل آيات فاندايك (مع ذكر فاندايك) و KJV (مع ذكر KJV). عقيدة: خلاص بالنعمة بالإيمان وحده، أمن أبدي، معمودية تغطيس للمؤمنين فقط. أجب عربي إذا السؤال عربي، إنجليزي إذا إنجليزي، قصير 4 جمل مع آيات."
    sys_en = "You are Independent Baptist KJV ONLY assistant. Arabic = Van Dyke ONLY, English = KJV ONLY. Reject NIV, ESV, NASB. Use KJV verses only in English with KJV citation, Van Dyke in Arabic. Doctrine: salvation by grace through faith alone, eternal security, baptism by immersion for believers only. Answer in user's language, short 4 sentences with verses."
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "gpt-4o-mini", "messages": [{"role": "system", "content": sys_ar if lang=='ar' else sys_en}, {"role": "user", "content": text}], "max_tokens": 400, "temperature": 0.3}
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=15)
    if r.status_code == 200:
        return r.json()['choices'][0]['message']['content']
    return None

@app.route('/')
def home():
    return {"status": f"{CHURCH_NAME_AR} - عربي: فاندايك فقط | English: KJV ONLY - Independent Baptist", "bible_ar": "Smith & Van Dyke ONLY", "bible_en": "KJV ONLY"}

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
                            send_message(sid, get_answer(text))
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
