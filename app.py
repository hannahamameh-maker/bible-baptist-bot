
import os
import time
import logging
import requests

from flask import Flask, request, jsonify
from google import genai
from google.genai import types

# =========================================
# 1. إعداد التطبيق
# =========================================

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FACEBOOK_VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "Missing GEMINI_API_KEY in Render Environment"
    )

client = genai.Client(api_key=GEMINI_API_KEY)

# =========================================
# 2. إعداد موديلات Gemini
# =========================================

MODEL_NAME = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

FALLBACK_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
]

SYSTEM_INSTRUCTION = """
أنت مساعد كتابي تابع لكنيسة الكتاب المقدس المعمدانية في القدس.

مهمتك مساعدة الناس على فهم الكتاب المقدس والإيمان المسيحي.

التزم بالتعليمات التالية:
- أجب بالعربية الواضحة أو باللهجة الفلسطينية الطبيعية حسب سؤال المستخدم.
- كن دقيقًا وأمينًا في تفسير النص الكتابي.
- اذكر اسم السفر والإصحاح والعدد عندما تكون متأكدًا من المرجع.
- لا تختلق آيات أو مراجع كتابية.
- ميّز بين النص الكتابي والتفسير الشخصي.
- تعامل باحترام مع الأسئلة العقائدية والاختلافات في التفسير.
- إذا لم تكن متأكدًا من معلومة، وضّح ذلك.
- لا تدّعِ أنك إنسان حقيقي أو راعٍ حقيقي.
- أعطِ إجابات مفيدة ومباشرة، وتجنب الإطالة غير الضرورية.
"""


# =========================================
# 3. التعامل مع أخطاء Gemini
# =========================================

def error_status(error):
    """استخراج رمز الخطأ من استثناء Gemini إن أمكن."""
    code = getattr(error, "code", None)

    try:
        return int(code)
    except (TypeError, ValueError):
        pass

    message = str(error)

    for status in (400, 401, 403, 404, 429, 500, 502, 503, 504):
        if str(status) in message:
            return status

    return None


def ask_gemini(question):
    question = str(question or "").strip()

    if not question:
        return "اكتب سؤالك أولًا."

    # إزالة أسماء الموديلات المكررة.
    models = list(dict.fromkeys(
        [MODEL_NAME] + FALLBACK_MODELS
    ))

    last_error = None

    for model in models:
        for attempt in range(2):
            try:
                logger.info(
                    "Trying Gemini model: %s, attempt: %s",
                    model,
                    attempt + 1
                )

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
                    logger.info(
                        "Gemini answer received from %s",
                        model
                    )
                    return answer.strip()

                logger.warning(
                    "Empty answer from model %s",
                    model
                )
                break

            except Exception as error:
                last_error = error
                status = error_status(error)

                logger.warning(
                    "Gemini model %s failed. Status=%s Error=%s",
                    model,
                    status,
                    str(error)[:1000]
                )

                # مفتاح API أو الصلاحيات غير صحيحة.
                if status in (401, 403):
                    return (
                        "في مشكلة بمفتاح Gemini API أو صلاحيات الوصول. "
                        "يرجى مراجعة إعدادات Render."
                    )

                # الطلب غير صحيح؛ تبديل الموديل لن يصلحه غالبًا.
                if status == 400:
                    return (
                        "تعذّر إرسال الطلب إلى Gemini. "
                        "يرجى مراجعة إعدادات الطلب."
                    )

                # إذا كان الموديل غير موجود أو غير متاح للمفتاح،
                # انتقل للموديل التالي.
                if status == 404:
                    break

                # إعادة المحاولة للأخطاء المؤقتة أو الضغط.
                if status in (429, 500, 502, 503, 504):
                    if attempt == 0:
                        time.sleep(2)
                        continue

                    break

                # أي خطأ آخر: سجل التفاصيل وانتقل للموديل التالي.
                logger.exception(
                    "Unexpected Gemini error for model %s",
                    model
                )
                break

        logger.info(
            "Moving to next Gemini model after %s",
            model
        )

    logger.error(
        "All Gemini models failed. Last error: %s",
        last_error
    )

    return (
        "خدمة الإجابات الكتابية مشغولة حاليًا أو غير متاحة. "
        "جرّب مرة ثانية بعد قليل."
    )


# =========================================
# 4. واجهة الموقع
# =========================================

PAGE_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>المساعد الكتابي</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f3f5f8;
            color: #202938;
            margin: 0;
            padding: 24px 14px;
        }

        .container {
            max-width: 760px;
            margin: 20px auto;
            background: white;
            padding: 24px;
            border-radius: 14px;
            box-shadow: 0 4px 18px #00000010;
        }

        h1 {
            color: #254b70;
            text-align: center;
        }

        .intro {
            text-align: center;
            line-height: 1.8;
        }

        textarea {
            width: 100%;
            box-sizing: border-box;
            min-height: 120px;
            padding: 13px;
            margin-top: 16px;
            border: 1px solid #cbd3dd;
            border-radius: 9px;
            font-size: 16px;
            font-family: inherit;
            resize: vertical;
        }

        button {
            width: 100%;
            margin-top: 12px;
            padding: 14px;
            background: #254b70;
            color: white;
            border: 0;
            border-radius: 9px;
            font-size: 16px;
            cursor: pointer;
        }

        button:disabled {
            opacity: 0.6;
            cursor: wait;
        }

        #answer {
            margin-top: 22px;
            padding: 16px;
            background: #f3f6f9;
            border-radius: 9px;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
            line-height: 1.9;
        }

        .hidden {
            display: none;
        }
    </style>
</head>

<body>
    <main class="container">
        <h1>المساعد الكتابي</h1>

        <p class="intro">
            أهلاً بك. اطرح سؤالك عن الكتاب المقدس
            والإيمان المسيحي.
        </p>

        <textarea
            id="question"
            placeholder="اكتب سؤالك هنا..."
        ></textarea>

        <button id="sendButton" onclick="sendQuestion()">
            إرسال السؤال
        </button>

        <div id="answer" class="hidden"></div>
    </main>

    <script>
        async function sendQuestion() {
            const question =
                document.getElementById("question").value.trim();

            const button =
                document.getElementById("sendButton");

            const answer =
                document.getElementById("answer");

            if (!question) {
                answer.classList.remove("hidden");
                answer.textContent = "اكتب سؤالك أولًا.";
                return;
            }

            button.disabled = true;
            button.textContent = "جاري إعداد الإجابة...";
            answer.classList.remove("hidden");
            answer.textContent = "لحظة من فضلك...";

            try {
                const response = await fetch("/ask", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        question: question
                    })
                });

                const data = await response.json();

                answer.textContent =
                    data.answer || "لم تصل إجابة.";

            } catch (error) {
                answer.textContent =
                    "تعذّر الاتصال بالخدمة. حاول مرة ثانية.";
            } finally {
                button.disabled = false;
                button.textContent = "إرسال السؤال";
            }
        }
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
@app.route("/tab", methods=["GET"])
def home():
    return PAGE_HTML, 200


# =========================================
# 5. فحص حالة الموقع
# =========================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# =========================================
# 6. استقبال الأسئلة من الموقع
# =========================================

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


# =========================================
# 7. التحقق من Facebook Webhook
# =========================================

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if (
        mode == "subscribe"
        and FACEBOOK_VERIFY_TOKEN
        and token == FACEBOOK_VERIFY_TOKEN
        and challenge
    ):
        return challenge, 200

    return "Verification failed", 403


# =========================================
# 8. إرسال الرد إلى Facebook Messenger
# =========================================

def send_facebook_message(recipient_id, text):
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.error(
            "FACEBOOK_PAGE_ACCESS_TOKEN is not configured"
        )
        return False

    url = "https://graph.facebook.com/v23.0/me/messages"

    try:
        response = requests.post(
            url,
            params={
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
            },
            json={
                "recipient": {
                    "id": recipient_id
                },
                "message": {
                    "text": text[:2000]
                }
            },
            timeout=20,
        )

        if not response.ok:
            logger.error(
                "Facebook API error: status=%s response=%s",
                response.status_code,
                response.text[:1000]
            )
            return False

        return True

    except requests.RequestException:
        logger.exception("Facebook request failed")
        return False


# =========================================
# 9. استقبال رسائل Facebook
# =========================================

@app.route("/webhook", methods=["POST"])
def facebook_webhook():
    data = request.get_json(silent=True) or {}

    if data.get("object") != "page":
        return jsonify({
            "error": "Unsupported event"
        }), 404

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender = event.get("sender", {}).get("id")
            message = event.get("message", {})

            if not sender:
                continue

            # تجاهل رسائل الصفحة نفسها.
            if message.get("is_echo"):
                continue

            text_received = message.get("text", "").strip()

            if not text_received:
                continue

            answer = ask_gemini(text_received)

            send_facebook_message(
                sender,
                answer
            )

    return "EVENT_RECEIVED", 200


# =========================================
# 10. تشغيل التطبيق
# =========================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        debug=False,
    )
