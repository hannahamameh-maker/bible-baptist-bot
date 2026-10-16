import os
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# إعدادات كنيسة الكتاب المقدس المعمدانية - القدس
# Page ID: 100080177692918 - Bible Baptist Church-Jerusalem
SYSTEM_PROMPT = """
أنت خادم النعمة، المساعد الروحي الرسمي لكنيسة الكتاب المقدس المعمدانية - القدس.
Page ID: 100080177692918

تتكلم عربي فلسطيني محب، كتابي 100%، بفكر معمداني مستقل:
- الكتاب المقدس وحده المرجع المعصوم
- الخلاص بالنعمة بالإيمان وحده بدم يسوع (أفسس 2:8-9)
- الأمن الأبدي (يوحنا 10:28)
- استقلالية الكنيسة المحلية
- معمودية المؤمن بالتغطيس
- التبشير وربح النفوس

أسلوبك: ترحيب باسم يسوع، آية، شرح قصير، سؤال: تحب أصلي معك؟
إذا طلب خلاص: قدم خطة الخلاص الأربع
إذا طلب صلاة: صلي معه
إذا طلب خادم: حوله للخادم
"""

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "baptist2026")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
GROQ_KEY = os.getenv("GROQ_KEY")

def ai_reply(user_msg):
    if not GROQ_KEY:
        return "الرب يباركك! البوت بده إعداد GROQ_KEY في Render"
    try:
        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.5,
            "max_tokens": 400,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ]
        }
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=25)
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"AI Error: {e}")
        return "حبيبي، صار ضغط بسيط، جرب بعد ثانية والرب معك 🙏"

def send_message(recipient_id, text, quick_replies=None):
    if not PAGE_ACCESS_TOKEN:
        return
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": text[:1900]}}
    if quick_replies:
        payload["message"]["quick_replies"] = quick_replies
    requests.post(url, json=payload, timeout=10)

def send_typing(recipient_id):
    if not PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    requests.post(url, json={"recipient": {"id": recipient_id}, "sender_action": "typing_on"}, timeout=5)

def setup_profile():
    if not PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v20.0/me/messenger_profile?access_token={PAGE_ACCESS_TOKEN}"
    profile = {
        "get_started": {"payload": "GET_STARTED"},
        "greeting": [{"locale": "default", "text": "أهلا وسهلا في كنيسة الكتاب المقدس المعمدانية - القدس! أنا خادم النعمة، كيف بقدر أصلي معك اليوم؟"}],
        "persistent_menu": [{
            "locale": "default",
            "composer_input_disabled": False,
            "call_to_actions": [
                {"type": "postback", "title": "🙏 اطلب صلاة", "payload": "PRAYER"},
                {"type": "postback", "title": "✝️ كيف أخلص؟", "payload": "SALVATION"},
                {"type": "postback", "title": "📍 أوقات الاجتماعات", "payload": "TIMES"},
                {"type": "postback", "title": "👨‍🏫 احكي مع خادم", "payload": "HUMAN"}
            ]
        }]
    }
    requests.post(url, json=profile, timeout=10)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Bible Baptist Church Jerusalem Bot Running", "page_id": "100080177692918", "time": str(datetime.now())})

@app.route("/setup", methods=["GET"])
def setup():
    setup_profile()
    return "✅ تم تفعيل قائمة البوت والترحيب لكنيسة الكتاب المقدس المعمدانية - القدس"

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if data.get("object") != "page":
        return "ok", 200
    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender = event["sender"]["id"]
            if event.get("message", {}).get("is_echo"):
                continue
            if event.get("postback"):
                p = event["postback"]["payload"]
                if p == "GET_STARTED":
                    send_message(sender, "أهلا وسهلا فيك باسم يسوع في كنيسة الكتاب المقدس المعمدانية - القدس! ❤️ أنا خادم النعمة، هون لأساعدك. كيف بقدر أخدمك؟", [{"content_type":"text","title":"اطلب صلاة","payload":"PRAYER"},{"content_type":"text","title":"كيف أخلص","payload":"SALVATION"}])
                    continue
                elif p == "PRAYER":
                    send_message(sender, "أكيد بصلي معك. شاركني بطلبك؟")
                    continue
                elif p == "SALVATION":
                    send_message(sender, ai_reply("اشرح كيف أخلص حسب الإنجيل"))
                    continue
                elif p == "TIMES":
                    send_message(sender, "⛪ اجتماعات كنيسة الكتاب المقدس المعمدانية - القدس:\nالأحد 10ص - العبادة\nالأربعاء 7م - دراسة كتاب\nالجمعة 6م - اجتماع الشباب\nأهلا وسهلا فيك!")
                    continue
                elif p == "HUMAN":
                    send_message(sender, "تمام، وصلت رسالتك للخادم، رح يتواصل معك قريباً. الرب يباركك 🙏")
                    continue
            if "message" in event and "text" in event["message"]:
                send_typing(sender)
                reply = ai_reply(event["message"]["text"])
                send_message(sender, reply, [{"content_type":"text","title":"🙏 صلاة","payload":"PRAYER"},{"content_type":"text","title":"👨‍🏫 خادم","payload":"HUMAN"}])
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
