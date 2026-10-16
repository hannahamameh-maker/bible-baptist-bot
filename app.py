
import os
import logging
import requests

from flask import Flask, request, jsonify, render_template_string
from google import genai
from google.genai import types

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Gemini settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()

# Facebook settings
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv(
    "FACEBOOK_PAGE_ACCESS_TOKEN", ""
).strip()
FACEBOOK_VERIFY_TOKEN = os.getenv(
    "FACEBOOK_VERIFY_TOKEN", ""
).strip()
FACEBOOK_API_VERSION = os.getenv(
    "FACEBOOK_API_VERSION", "v23.0"
).strip()

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SYSTEM_INSTRUCTION = """
أنت مساعد كتابي لصفحة كنيسة الكتاب المقدس المعمدانية في القدس.

قواعد الإجابة:
1. في أسئلة الإيمان والعقيدة، اعتمد على الكتاب المقدس.
2. التزم بالفكر المعمداني المحافظ، بما في ذلك الخلاص بالنعمة
   بالإيمان بيسوع المسيح، ومعمودية المؤمن، واستقلال الكنيسة المحلية،
   وكهنوت جميع المؤمنين، وسلطان الكتاب المقدس.
3. استخدم العربية الطبيعية والواضحة. استخدم اللهجة الفلسطينية
   إذا سأل المستخدم باللهجة الفلسطينية، والفصحى إذا طلبها.
4. لا تقدم تأملات شخصية أو آراء روحية من عندك.
5. لا تختلق آيات أو اقتباسات أو أرقام أعداد.
6. عند ذكر آية، اذكر المرجع الكتابي إذا كنت متأكدًا منه.
7. لا تدّعِ أن الاقتباس حرفي من ترجمة سميث وفاندايك
   إلا إذا كنت متأكدًا من نصه الحرفي.
8. إذا لم تكن متأكدًا من النص أو المرجع، قل ذلك بوضوح.
9. لا تدّعِ أن لديك نسخة كاملة من الكتاب المقدس للبحث فيها
   إذا لم تكن هذه النسخة متاحة لك.
10. أجب عن السؤال مباشرة وباختصار مناسب، دون حشو.
11. إذا كان السؤال لا يعالجه الكتاب المقدس بوضوح، وضّح ذلك
    ولا تخترع جوابًا أو تنسب رأيك إلى الكتاب المقدس.
"""

def ask_gemini(question):
    if not client:
        return "مفتاح Gemini API غير مضبوط في إعدادات الموقع."

    question = (question or "").strip()
    if not question:
        return "اكتب سؤالك أولًا."

    if len(question) > 10000:
        return "السؤال طويل جدًا. اختصره وحاول مرة ثانية."

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=question,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
                max_output_tokens=1800,
            ),
        )

        answer = getattr(response, "text", None)
        if answer and answer.strip():
            return answer.strip()

        logger.warning("Gemini returned an empty response.")
        return "ما قدرت أطلع إجابة واضحة. جرّب صياغة السؤال بطريقة ثانية."

    except Exception as exc:
        logger.exception("Gemini API error: %s", exc)
        error = str(exc).lower()

        if "429" in error or "resource_exhausted" in error:
            return "وصلنا إلى حد الاستخدام المسموح. تحقّق من الحصة وحاول لاحقًا."

        if "503" in error or "unavailable" in error:
            return "خدمة الذكاء الاصطناعي مشغولة حاليًا. جرّب مرة ثانية بعد قليل."

        if "401" in error or "unauthenticated" in error:
            return "مفتاح Gemini API غير صحيح. راجع إعدادات المفتاح."

        if "403" in error or "permission_denied" in error:
            return "الحساب لا يملك صلاحية استخدام النموذج. راجع إعدادات Google AI Studio."

        if "404" in error or "not found" in error:
            return (
                f"النموذج {GEMINI_MODEL} غير متاح. "
                "تحقّق من اسم النموذج والنماذج المتاحة لحسابك."
            )

        return "صار خطأ أثناء الاتصال بخدمة الذكاء الاصطناعي. راجع سجلات Render."


@app.route("/", methods=["GET"])
def home():
    return render_template_string("""
<!doctype html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>المساعد الكتابي</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      max-width: 760px;
      margin: 35px auto;
      padding: 16px;
      background: #f5f6f8;
      color: #202124;
    }
    .panel {
      background: white;
      border-radius: 12px;
      padding: 22px;
      box-shadow: 0 2px 12px #00000010;
    }
    textarea {
      width: 100%;
      min-height: 120px;
      box-sizing: border-box;
      padding: 12px;
      font: inherit;
      border: 1px solid #ccc;
      border-radius: 8px;
      resize: vertical;
    }
    button {
      margin-top: 12px;
      padding: 12px 20px;
      border: 0;
      border-radius: 8px;
      background: #174a70;
      color: white;
      font: inherit;
      cursor: pointer;
    }
    button:disabled { opacity: .6; }
    #answer {
      white-space: pre-wrap;
      line-height: 1.9;
      margin-top: 20px;
      overflow-wrap: anywhere;
    }
  </style>
</head>
<body>
  <div class="panel">
    <h2>المساعد الكتابي</h2>
    <p>اكتب سؤالك الكتابي أو العقائدي.</p>
    <form id="ask-form">
      <textarea id="question" maxlength="10000"
        placeholder="اكتب سؤالك هنا..." required></textarea>
      <button id="submit" type="submit">إرسال السؤال</button>
    </form>
    <div id="answer" aria-live="polite"></div>
  </div>
  <script>
    const form = document.getElementById("ask-form");
    const question = document.getElementById("question");
    const answer = document.getElementById("answer");
    const button = document.getElementById("submit");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const q = question.value.trim();
      if (!q) return;

      button.disabled = true;
      answer.textContent = "جاري إعداد الإجابة...";

      try {
        const response = await fetch("/ask", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({question: q})
        });
        const data = await response.json();
        answer.textContent = data.answer || data.error || "لم تصل إجابة.";
      } catch (error) {
        answer.textContent = "تعذّر الاتصال بالموقع. حاول مرة ثانية.";
      } finally {
        button.disabled = false;
      }
    });
  </script>
</body>
</html>
""")


@app.route("/tab", methods=["GET"])
def tab():
    return home()


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "model": GEMINI_MODEL,
        "gemini_key_configured": bool(GEMINI_API_KEY),
        "facebook_configured": bool(FACEBOOK_PAGE_ACCESS_TOKEN),
    })


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")

    if not isinstance(question, str) or not question.strip():
        return jsonify({"error": "اكتب سؤالك أولًا."}), 400

    return jsonify({"answer": ask_gemini(question)})


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode", "")
    token = request.args.get("hub.verify_token", "")
    challenge = request.args.get("hub.challenge", "")

    if (
        mode == "subscribe"
        and FACEBOOK_VERIFY_TOKEN
        and token == FACEBOOK_VERIFY_TOKEN
    ):
        return challenge, 200

    return "Verification failed", 403


def send_facebook_message(recipient_id, message_text):
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.error("Facebook page access token is missing.")
        return False

    url = (
        f"https://graph.facebook.com/"
        f"{FACEBOOK_API_VERSION}/me/messages"
    )
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text[:2000]},
        "messaging_type": "RESPONSE",
    }

    try:
        response = requests.post(
            url,
            params={"access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
            json=payload,
            timeout=20,
        )

        if not response.ok:
            logger.error(
                "Facebook send failed: %s %s",
                response.status_code,
                response.text[:1000],
            )
            return False

        return True

    except requests.RequestException:
        logger.exception("Facebook request failed.")
        return False


@app.route("/webhook", methods=["POST"])
def facebook_webhook():
    data = request.get_json(silent=True) or {}

    if data.get("object") != "page":
        return jsonify({"status": "ignored"}), 200

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = (event.get("sender") or {}).get("id")
            recipient_id = (event.get("recipient") or {}).get("id")
            message = event.get("message") or {}

            if not sender_id or sender_id == recipient_id:
                continue

            if message.get("is_echo"):
                continue

            if event.get("delivery") or event.get("read"):
                continue

            text = (message.get("text") or "").strip()

            if not text:
                send_facebook_message(
                    sender_id,
                    "ابعث سؤالك كتابةً، وأنا بحاول أساعدك بإجابة كتابية."
                )
                continue

            answer = ask_gemini(text)
            send_facebook_message(sender_id, answer)

    return jsonify({"status": "received"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
