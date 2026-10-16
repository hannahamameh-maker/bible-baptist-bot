
from flask import Flask, request, jsonify
import os
import requests
from google import genai
from google.genai import types

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

SYSTEM_INSTRUCTION = """
أنت مساعد كتابي رسمي لكنيسة الكتاب المقدس المعمدانية - القدس.
أجب عن الأسئلة الكتابية بالاستناد إلى الكتاب المقدس،
وبالترجمات العربية فاندايك والإنجليزية KJV عند الحاجة.
التزم بالتوجه المعمداني المحافظ، وميّز بين نص الكتاب
والتفسير. لا تنسب إلى الكتاب المقدس كلامًا غير موجود فيه.
اذكر الشاهد الكتابي عندما يكون ذلك مناسبًا.
أجب بلغة السائل، وبأسلوب واضح ومحترم.
إذا كان السؤال خارج اختصاصك، وضّح ذلك بأمانة.
"""

client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"Gemini initialized with model: {MODEL_NAME}")
    except Exception as e:
        print(f"Gemini initialization failed: {e}")


def generate_answer(question):
    if not client:
        raise RuntimeError("Gemini client is not configured")

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=question,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
            max_output_tokens=800,
        ),
    )

    answer = response.text
    if not answer:
        raise RuntimeError("Gemini returned an empty response")

    return answer.strip()


TAB_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>كنيسة الكتاب المقدس المعمدانية - القدس</title>
<style>
body {
  font-family: system-ui, sans-serif;
  background: #f8f6f0;
  margin: 0;
  padding: 20px;
}
.card {
  max-width: 600px;
  margin: 0 auto;
  background: white;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0,0,0,.1);
}
h1 {
  color: #7a1c1c;
  text-align: center;
  font-size: 22px;
}
#chat {
  height: 350px;
  overflow-y: auto;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 10px;
  margin: 15px 0;
}
.msg {
  margin: 8px 0;
  padding: 10px 14px;
  border-radius: 12px;
  max-width: 85%;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.user {
  background: #7a1c1c;
  color: white;
  margin-right: auto;
}
.bot {
  background: #f0e6d3;
  color: #333;
}
form {
  display: flex;
  gap: 6px;
}
input {
  flex: 1;
  min-width: 0;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid #ddd;
}
button {
  padding: 12px 18px;
  background: #7a1c1c;
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
}
button:disabled {
  opacity: .6;
}
</style>
</head>
<body>
<div class="card">
  <h1>كنيسة الكتاب المقدس المعمدانية - القدس</h1>
  <p style="text-align:center">نرحب بأسئلتكم الكتابية</p>

  <div id="chat" aria-live="polite">
    <div class="msg bot">سلام المسيح! اسأل أي سؤال كتابي.</div>
  </div>

  <form id="ask-form">
    <input id="q" maxlength="2000"
      placeholder="اكتب سؤالك..." autocomplete="off" required>
    <button id="send" type="submit">إرسال</button>
  </form>
</div>

<script>
const form = document.getElementById("ask-form");
const input = document.getElementById("q");
const chat = document.getElementById("chat");
const send = document.getElementById("send");

function addMessage(text, role) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  // Use textContent to prevent HTML/JavaScript injection.
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const question = input.value.trim();
  if (!question || send.disabled) return;

  addMessage(question, "user");
  input.value = "";
  send.disabled = true;

  const waiting = addMessage("لحظة من فضلك...", "bot");

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question})
    });

    const data = await response.json();
    waiting.textContent = data.answer || "لم يصل جواب.";
  } catch (error) {
    waiting.textContent = "تعذّر الاتصال. حاول مرة أخرى.";
  } finally {
    send.disabled = false;
    input.focus();
    chat.scrollTop = chat.scrollHeight;
  }
});
</script>
</body>
</html>"""


@app.route("/")
def home():
    return "Biblical Bot is Live", 200


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "gemini_configured": client is not None,
        "model": MODEL_NAME,
    })


@app.route("/tab")
def tab():
    return TAB_HTML


@app.route("/ask", methods=["POST"])
def ask_gemini():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")

    if not isinstance(question, str) or not question.strip():
        return jsonify({"answer": "اكتب سؤالك أولًا."}), 400

    if len(question) > 2000:
        return jsonify({"answer": "السؤال طويل جدًا. اختصره من فضلك."}), 400

    if not client:
        return jsonify({
            "answer": "البوت غير جاهز حاليًا. يرجى المحاولة لاحقًا."
        }), 503

    try:
        answer = generate_answer(question.strip())
        return jsonify({"answer": answer})

    except Exception:
        app.logger.exception("Gemini request failed")
        return jsonify({
            "answer": "حدث خطأ أثناء إعداد الإجابة. حاول مرة أخرى لاحقًا."
        }), 502


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if not VERIFY_TOKEN:
            return "Webhook verification token not configured", 500

        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge", ""), 200

        return "Token invalid", 403

    body = request.get_json(silent=True) or {}

    if body.get("object") != "page":
        return jsonify({"error": "Unsupported event"}), 404

    if not client or not PAGE_ACCESS_TOKEN:
        app.logger.error("Gemini or Facebook token is not configured")
        return "Service not configured", 503

    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            message = event.get("message", {})
            sender = event.get("sender", {}).get("id")
            text = message.get("text")

            # Ignore non-text events and messages sent by the page itself.
            if not sender or not isinstance(text, str) or not text.strip():
                continue
            if message.get("is_echo"):
                continue

            try:
                answer = generate_answer(text.strip())[:2000]

                result = requests.post(
                    "https://graph.facebook.com/v23.0/me/messages",
                    params={"access_token": PAGE_ACCESS_TOKEN},
                    json={
                        "recipient": {"id": sender},
                        "message": {"text": answer},
                    },
                    timeout=15,
                )

                if not result.ok:
                    app.logger.error(
                        "Facebook send failed: %s %s",
                        result.status_code,
                        result.text[:500],
                    )

            except Exception:
                app.logger.exception("Failed to process Facebook message")

    return "ok", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
    )
