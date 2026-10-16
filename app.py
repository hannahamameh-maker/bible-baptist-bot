
import os
import time
import logging
import requests

from flask import Flask, request, jsonify

# =========================================
# 1. إعداد التطبيق
# =========================================

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
).strip()

FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv(
    "FACEBOOK_PAGE_ACCESS_TOKEN", ""
).strip()

FACEBOOK_VERIFY_TOKEN = os.getenv(
    "FACEBOOK_VERIFY_TOKEN", ""
).strip()

GROQ_API_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

FACEBOOK_API_VERSION = os.getenv(
    "FACEBOOK_API_VERSION", "v23.0"
)

FACEBOOK_API_URL = (
    f"https://graph.facebook.com/"
    f"{FACEBOOK_API_VERSION}/me/messages"
)

if not GROQ_API_KEY:
    raise RuntimeError(
        "Missing GROQ_API_KEY in Render Environment"
    )

# مهلة الاتصال ومدة انتظار الرد
HTTP_TIMEOUT = (10, 45)

# =========================================
# 2. تعليمات المساعد الكتابي
# =========================================

SYSTEM_INSTRUCTION = """
أنت مساعد كتابي تابع لكنيسة الكتاب المقدس المعمدانية في القدس.

مهمتك مساعدة الناس على فهم الكتاب المقدس والإيمان المسيحي.

التزم بالتعليمات التالية:
- أجب بالعربية الواضحة أو باللهجة الفلسطينية الطبيعية
  حسب طريقة المستخدم وسؤاله.
- كن دقيقًا وأمينًا في تفسير النص الكتابي.
- اذكر اسم السفر والإصحاح والعدد عندما تكون متأكدًا.
- لا تختلق آيات أو مراجع كتابية.
- ميّز بين النص الكتابي والتفسير الشخصي.
- تعامل باحترام مع الأسئلة العقائدية والاختلافات التفسيرية.
- عندما لا تكون متأكدًا، وضّح ذلك ولا تخمّن.
- لا تدّعِ أنك إنسان حقيقي أو راعٍ حقيقي.
- لا تدّعِ أنك تعرف عظات أو مواقف خاصة بالكنيسة
  ما لم تُقدَّم لك معلومات عنها.
- أعطِ إجابات مفيدة ومباشرة، وتجنب الإطالة غير الضرورية.
- أجب عن الأسئلة الروحية والكتابية باحترام ووضوح.
"""

# =========================================
# 3. الاتصال بـ Groq API
# =========================================

session = requests.Session()


def ask_groq(question):
    question = str(question or "").strip()

    if not question:
        return "اكتب سؤالك أولًا."

    if len(question) > 12000:
        return "السؤال طويل جدًا. اختصره وحاول مرة ثانية."

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_INSTRUCTION,
            },
            {
                "role": "user",
                "content": question,
            },
        ],
        "temperature": 0.4,
        "max_completion_tokens": 1800,
    }

    for attempt in range(2):
        try:
            response = session.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=HTTP_TIMEOUT,
            )

            if response.ok:
                result = response.json()

                choices = result.get("choices", [])
                if not choices:
                    logger.error("Groq returned no choices")
                    return (
                        "ما وصلتنا إجابة مكتملة. "
                        "جرّب مرة ثانية."
                    )

                answer = (
                    choices[0]
                    .get("message", {})
                    .get("content", "")
                )

                if isinstance(answer, str) and answer.strip():
                    return answer.strip()

                return (
                    "ما قدرت أحصل على إجابة واضحة. "
                    "جرّب صياغة السؤال بطريقة ثانية."
                )

            status = response.status_code

            logger.warning(
                "Groq API error: status=%s response=%s",
                status,
                response.text[:1000],
            )

            if status in (401, 403):
                return (
                    "في مشكلة بمفتاح Groq API أو صلاحيات الوصول. "
                    "راجع إعدادات Render."
                )

            if status == 429:
                return (
                    "وصلنا إلى حد الاستخدام المسموح حاليًا "
                    "في Groq. جرّب بعد قليل."
                )

            if status == 400:
                return (
                    "تعذّر إرسال السؤال إلى النموذج. "
                    "راجع اسم النموذج وإعدادات الطلب."
                )

            if status == 404:
                return (
                    "النموذج المحدد غير متاح. "
                    "راجع متغير GROQ_MODEL."
                )

            if status >= 500 and attempt == 0:
                time.sleep(2)
                continue

            return (
                "خدمة الإجابات غير متاحة حاليًا. "
                "جرّب مرة ثانية بعد قليل."
            )

        except requests.Timeout:
            logger.warning("Groq API timed out")

            return (
                "تأخرت الإجابة بسبب ضغط الخدمة. "
                "جرّب مرة ثانية."
            )

        except requests.RequestException:
            logger.exception("Groq connection failed")

            return (
                "تعذّر الاتصال بخدمة الإجابات. "
                "تحقق من الاتصال وحاول مرة ثانية."
            )

        except (ValueError, KeyError, TypeError):
            logger.exception("Invalid Groq API response")

            return (
                "وصل رد غير متوقع من الخدمة. "
                "جرّب مرة ثانية."
            )

    return "الخدمة مشغولة حاليًا. جرّب بعد قليل."


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
* { box-sizing: border-box; }

body {
    font-family: Arial, sans-serif;
    background: #f3f5f8;
    color: #202938;
    margin: 0;
    padding: 20px 14px;
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
    line-height: 1.9;
}

textarea {
    display: block;
    width: 100%;
    min-height: 130px;
    padding: 13px;
    margin-top: 18px;
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

.hidden { display: none; }
</style>
</head>

<body>
<main class="container">
    <h1>المساعد الكتابي</h1>

    <p class="intro">
        أهلًا بك. اطرح سؤالك عن الكتاب المقدس
        والإيمان المسيحي.
    </p>

    <textarea id="question"
        maxlength="12000"
        placeholder="اكتب سؤالك هنا..."></textarea>

    <button id="sendButton" onclick="sendQuestion()">
        إرسال السؤال
    </button>

    <div id="answer" class="hidden" aria-live="polite"></div>
</main>

<script>
async function sendQuestion() {
    const question =
        document.getElementById("question").value.trim();

    const button = document.getElementById("sendButton");
    const answer = document.getElementById("answer");

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
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({question})
        });

        const data = await response.json();

        if (!response.ok && !data.answer) {
            throw new Error("Request failed");
        }

        answer.textContent = data.answer || "لم تصل إجابة.";

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
    return jsonify({
        "status": "ok",
        "service": "groq",
        "model": GROQ_MODEL,
    }), 200


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

    answer = ask_groq(question)

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
# 8. إرسال رد إلى Facebook Messenger
# =========================================

def send_facebook_message(recipient_id, text):
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.error("Facebook page token is missing")
        return False

    url = FACEBOOK_API_URL

    try:
        response = session.post(
            url,
            params={
                "access_token": FACEBOOK_PAGE_ACCESS_TOKEN
            },
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text[:2000]},
            },
            timeout=HTTP_TIMEOUT,
        )

        if not response.ok:
            logger.error(
                "Facebook API error: status=%s response=%s",
                response.status_code,
                response.text[:1000],
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
        return jsonify({"error": "Unsupported event"}), 404

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender = event.get("sender", {}).get("id")
            message = event.get("message", {})

            if not sender or not message:
                continue

            # تجاهل رسائل الصفحة نفسها
            if message.get("is_echo"):
                continue

            # تجاهل أحداث لا تحتوي على نص
            text_received = message.get("text", "")

            if not isinstance(text_received, str):
                continue

            text_received = text_received.strip()

            if not text_received:
                continue

            # منع الرد على رسائل أطول من الحد المقبول
            if len(text_received) > 12000:
                send_facebook_message(
                    sender,
                    "السؤال طويل جدًا. اختصره وأرسله مرة ثانية."
                )
                continue

            answer = ask_groq(text_received)

            send_facebook_message(sender, answer)

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
