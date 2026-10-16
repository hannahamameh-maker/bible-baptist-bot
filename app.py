
import os
import time
import logging
import requests

from flask import Flask, request, jsonify
from google import genai
from google.genai import types

# -----------------------------
# إعداد التطبيق
# -----------------------------

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN")

if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY environment variable")

client = genai.Client(api_key=GEMINI_API_KEY)

# نستخدم موديلات موثقة، مع الانتقال للموديل التالي عند الحاجة.
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]

SYSTEM_INSTRUCTION = """
أنت مساعد كتابي تابع لكنيسة الكتاب المقدس المعمدانية في القدس.

مهمتك مساعدة الناس على فهم الكتاب المقدس والإيمان المسيحي
وفقًا للنص الكتابي وسياقه، بأسلوب واضح ومحترم ومشجع.

قواعد الإجابة:
1. أجب باللغة التي يستخدمها السائل، واستخدم العربية الواضحة
   أو اللهجة الفلسطينية الطبيعية إذا كانت مناسبة.
2. اذكر المراجع الكتابية بدقة عندما تكون متأكدًا منها.
3. لا تختلق آيات أو أرقام إصحاحات أو أعداد.
4. وضّح الفرق بين النص الكتابي والتفسير الشخصي.
5. تعامل باحترام مع الأسئلة الصعبة والاختلافات العقائدية.
6. إذا لم تكن متأكدًا، قل ذلك بصراحة.
7. لا تدّعِ أنك إنسان أو راعٍ حقيقي.
8. اجعل الإجابة مفيدة ومباشرة، دون إطالة غير ضرورية.
"""


# -----------------------------
# Gemini: إجابات مع تبديل الموديل
# -----------------------------

def is_temporary_error(error):
    message = str(error).lower()

    temporary_markers = [
        "503",
        "unavailable",
        "high demand",
        "overloaded",
        "429",
        "resource_exhausted",
        "deadline exceeded",
        "500",
        "502",
        "504",
    ]

    return any(marker in message for marker in temporary_markers)


def ask_gemini(question):
    question = str(question or "").strip()

    if not question:
        return "اكتب سؤالك أولًا."

    # إزالة التكرار مع المحافظة على ترتيب الموديلات.
    models = list(dict.fromkeys([MODEL_NAME] + FALLBACK_MODELS))
    last_error = None

    for model in models:
        # محاولتان لكل موديل في حال الضغط المؤقت.
        for attempt in range(2):
            try:
                logger.info("Trying Gemini model: %s", model)

                response = client.models.generate_content(
                    model=model,
                    contents=question,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        max_output_tokens=1800,
                        temperature=0.4,
                    ),
                )

                answer = response.text

                if answer and answer.strip():
                    logger.info("Gemini response succeeded with %s", model)
                    return answer.strip()

                logger.warning("Empty response from model %s", model)
                break

            except Exception as error:
                last_error = error

                # نسجل تفاصيل الخطأ في Render Logs للتشخيص.
                logger.warning(
                    "Gemini model %s failed on attempt %s: %s",
                    model,
                    attempt + 1,
                    error,
                )

                message = str(error).lower()

                # أخطاء المفتاح أو الصلاحيات أو الطلب غير الصحيح
                # لن تُحل عادةً بتجربة موديل آخر.
                if any(code in message for code in [
                    "401", "403", "400",
                    "unauthorized", "permission_denied",
                    "api key not valid", "invalid_argument",
                ]):
                    logger.exception("Gemini configuration/request error")
                    return (
                        "في مشكلة بإعدادات Gemini API. "
                        "يرجى مراجعة إعدادات الخدمة."
                    )

                if not is_temporary_error(error):
                    logger.exception("Non-temporary Gemini error")
                    break

                if attempt == 0:
                    time.sleep(1.5)

        logger.warning("Moving to the next Gemini model after %s", model)

    logger.error("All Gemini models failed. Last error: %s", last_error)

    return (
        "خدمة الإجابات الكتابية مشغولة حاليًا. "
        "جرّب مرة ثانية بعد دقيقة."
    )


# -----------------------------
# الصفحة الرئيسية
# -----------------------------

@app.route("/", methods=["GET"])
def home():
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>المساعد الكتابي</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 760px;
                margin: 35px auto;
                padding: 18px;
                background: #f5f7fa;
                color: #202938;
            }
            .container {
                background: white;
                padding: 22px;
                border-radius: 14px;
                box-shadow: 0 3px 14px #00000010;
            }
            h1 { color: #254b70; }
            textarea {
                width: 100%;
                box-sizing: border-box;
                min-height: 100px;
                padding: 12px;
                font-size: 16px;
                border: 1px solid #ccd3dc;
                border-radius: 8px;
                resize: vertical;
            }
            button {
                margin-top: 12px;
                padding: 12px 22px;
                background: #254b70;
                color: white;
                border: 0;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
            }
            button:disabled { opacity: .6; }
            #answer {
                margin-top: 20px;
                padding: 14px;
                background: #f0f4f8;
                border-radius: 8px;
                white-space: pre-wrap;
                line-height: 1.8;
                overflow-wrap: anywhere;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>المساعد الكتابي</h1>
            <p>اسأل عن الكتاب المقدس والإيمان المسيحي.</p>

            <textarea id="question"
                placeholder="اكتب سؤالك هنا..."></textarea>

            <button id="send" onclick="sendQuestion()">
                أرسل السؤال
            </button>

            <div id="answer" hidden></div>
        </div>

        <script>
            async function sendQuestion() {
                const question =
                    document.getElementById("question").value.trim();
                const button = document.getElementById("send");
                const answer = document.getElementById("answer");

                if (!question) {
                    answer.hidden = false;
                    answer.textContent = "اكتب سؤالك أولًا.";
                    return;
                }

                button.disabled = true;
                answer.hidden = false;
                answer.textContent = "جاري إعداد الإجابة...";

                try {
                    const response = await fetch("/ask", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({question: question})
                    });

                    const data = await response.json();
                    answer.textContent =
                        data.answer || "لم تصل إجابة.";
                } catch (error) {
                    answer.textContent =
                        "تعذر الاتصال بالخدمة. حاول مرة ثانية.";
                } finally {
                    button.disabled = false;
                }
            }
        </script>
    </body>
    </html>
    """


# -----------------------------
# فحص حالة الخدمة
# -----------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# -----------------------------
# واجهة الأسئلة
# -----------------------------

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")

    if not isinstance(question, str) or not question.strip():
        return jsonify({
            "answer": "اكتب سؤالك أولًا."
        }), 400

    answer = ask_gemini(question)

    return jsonify({"answer": answer}), 200


# -----------------------------
# Facebook Messenger Webhook
# -----------------------------

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    verify_token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if (
        mode == "subscribe"
        and FACEBOOK_VERIFY_TOKEN
        and verify_token == FACEBOOK_VERIFY_TOKEN
        and challenge
    ):
        return challenge, 200

    return "Verification failed", 403


def send_facebook_message(recipient_id, message_text):
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.error("Facebook page access token is not configured")
        return False

    url = "https://graph.facebook.com/v23.0/me/messages"

    try:
        response = requests.post(
            url,
            params={"access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": message_text[:2000]},
            },
            timeout=20,
        )

        if not response.ok:
            logger.error(
                "Facebook send failed: status=%s response=%s",
                response.status_code,
                response.text[:1000],
            )
            return False

        return True

    except requests.RequestException:
        logger.exception("Facebook request failed")
        return False


@app.route("/webhook", methods=["POST"])
def facebook_webhook():
    data = request.get_json(silent=True) or {}

    if data.get("object") != "page":
        return jsonify({"error": "Unsupported event"}), 404

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender = event.get("sender", {}).get("id")
            message = event.get("message", {})

            if not sender:
                continue

            # تجاهل رسائل البوت نفسه وأحداث التسليم.
            if message.get("is_echo"):
                continue

            text_received = message.get("text", "").strip()

            if not text_received:
                continue

            answer = ask_gemini(text_received)
            send_facebook_message(sender, answer)

    return "EVENT_RECEIVED", 200


# -----------------------------
# تشغيل التطبيق
# -----------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        debug=False,
    )
