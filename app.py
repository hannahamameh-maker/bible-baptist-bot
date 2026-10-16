from flask import Flask, request, jsonify
import os
import google.generativeai as genai
import requests

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_secret_jesus_2024")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# إعداد Gemini المجاني
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        system_instruction="""
أنت مساعد كتابي رسمي لكنيسة الكتاب المقدس المعمدانية - القدس.
- جاوب فقط من الكتاب المقدس (KJV / فاندايك)
- عقيدتك معمدانية محافظة، لا تفتي خارج الكتاب
- اذا السؤال ليس كتابياً اعتذر بلطف وارجع للكتاب
- جاوب بنفس لغة المستخدم (عربي أو إنجليزي)
- اذكر الشاهد الكتابي دائماً
- كن محترماً ومحباً
"""
    )

# صفحة التاب اللي بتفتح من زر Learn More
TAB_HTML = """
<!DOCTYPE html>
<html dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>كنيسة الكتاب المقدس</title>
<style>
body{font-family:system-ui;background:#f8f6f0;margin:0;padding:20px}
.card{max-width:600px;margin:0 auto;background:white;border-radius:16px;padding:20px;box-shadow:0 4px 12px rgba(0,0,0,.1)}
h1{color:#7a1c1c;text-align:center}
#chat{height:350px;overflow-y:auto;border:1px solid #eee;border-radius:12px;padding:10px;margin:15px 0}
.msg{margin:8px 0;padding:10px 14px;border-radius:12px;max-width:85%}
.user{background:#7a1c1c;color:white;margin-left:auto}
.bot{background:#f0e6d3;color:#333}
input{width:75%;padding:12px;border-radius:10px;border:1px solid #ddd}
button{width:22%;padding:12px;background:#7a1c1c;color:white;border:none;border-radius:10px}
</style>
</head>
<body>
<div class="card">
<h1>مرحباً بكم في كنيسة الكتاب المقدس المعمدانية - القدس</h1>
<p style="text-align:center">نرحب بأسئلتكم الكتابية</p>
<div id="chat"><div class="msg bot">سلام المسيح! اسأل أي سؤال كتابي وسأجاوبك من الكتاب المقدس.</div></div>
<div style="display:flex;gap:6px">
<input id="q" placeholder="اكتب سؤالك هنا...">
<button onclick="ask()">إرسال</button>
</div>
</div>
<script>
async function ask(){
 let i=document.getElementById('q');
 let q=i.value.trim(); if(!q) return;
 let c=document.getElementById('chat');
 c.innerHTML+=`<div class=msg user>${q}</div>`; i.value='';
 c.scrollTop=c.scrollHeight;
 let r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})});
 let d=await r.json();
 c.innerHTML+=`<div class=msg bot>${d.answer}</div>`;
 c.scrollTop=c.scrollHeight;
}
document.getElementById('q').addEventListener('keypress',e=>{if(e.key==='Enter') ask()});
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return "Bot is Live - Bible Baptist Jerusalem"

@app.route("/tab")
def tab():
    return TAB_HTML

@app.route("/ask", methods=["POST"])
def ask_gemini():
    try:
        data = request.get_json()
        question = data.get("question","")
        if not GEMINI_API_KEY:
            return jsonify({"answer": "المفتاح غير مضبوط، راجع Render Environment"})
        response = model.generate_content(question)
        return jsonify({"answer": response.text})
    except Exception as e:
        return jsonify({"answer": f"حدث خطأ، حاول مرة أخرى: {str(e)}"})

# ويب هوك ماسنجر فيسبوك
@app.route("/webhook", methods=["GET","POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Token invalid", 403
    # POST - رسائل ماسنجر
    body = request.get_json()
    if body.get("object") == "page":
        for entry in body.get("entry", []):
            for msg in entry.get("messaging", []):
                if "message" in msg and "text" in msg["message"]:
                    sender = msg["sender"]["id"]
                    text = msg["message"]["text"]
                    if GEMINI_API_KEY:
                        try:
                            ai = model.generate_content(text)
                            reply = ai.text
                        except:
                            reply = "سلام المسيح، حاول مرة أخرى"
                        # إرسال الرد لماسنجر
                        requests.post(
                            f"https://graph.facebook.com/v18.0/{PAGE_ID}/messages?access_token={PAGE_ACCESS_TOKEN}",
                            json={"recipient":{"id":sender},"message":{"text":reply}}
                        )
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
