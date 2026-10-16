
import os
import logging

from flask import Flask, request, jsonify
from openai import OpenAI, APIConnectionError, APIStatusError, APITimeoutError

import requests

# =========================================
# 1. إعداد التطبيق
# =========================================

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL", "gpt-4.1-mini"
).strip()

FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv(
    "FACEBOOK_PAGE_ACCESS_TOKEN", ""
).strip()

FACEBOOK_VERIFY_TOKEN = os.getenv(
    "FACEBOOK_VERIFY_TOKEN", ""
).strip()

FACEBOOK_API_VERSION = os.getenv(
    "FACEBOOK_API_VERSION", "v23.0"
).strip()

FACEBOOK_API_URL = (
    f"https://graph.facebook.com/"
    f"{FACEBOOK_API_VERSION}/me/messages"
)

if not OPENAI_API_KEY:
    raise RuntimeError(
        "Missing OPENAI_API_KEY in Render Environment"
    )

client = OpenAI(
    api_key=OPENAI_API_KEY,
    timeout=45.0,
    max_retries=1,
)

http_session = requests.Session()

# =========================================
# 2. تعليمات المساعد الكتابي
# =========================================

SYSTEM_INSTRUCTION = """
أنت مساعد كتابي لكنيسة الكتاب المقدس المعمدانية في القدس.

المرجعية:
- الكتاب المقدس هو المرجع الأعلى والنهائي للإيمان والتعليم.
- اعتمد ترجمة سميث وفاندايك العربية عند الاستشهاد بالآيات.
- التزم بالمنظور المعمداني المحافظ.
- لا تدّعِ أن لديك نسخة مفتوحة من الكتاب المقدس أو
  قاعدة نصوص موثقة ما لم تكن متاحة فعلًا في النظام.

الدقة الكتابية:
- أجب بحسب النص الكتابي وسياقه.
- لا تختلق آيات أو اقتباسات أو مراجع.
- لا تنسب إلى الكتاب المقدس تعليمًا لا يقوله النص.
- لا تقدّم صياغة من الذاكرة باعتبارها اقتباسًا حرفيًا.
- إذا لم تكن متأكدًا من نص الآية أو مرجعها، وضّح ذلك.
- ميّز بين الاقتباس الكتابي وتلخيص معنى النص.
- إذا لم يذكر الكتاب المقدس جوابًا صريحًا عن سؤال ما،
  قل ذلك بوضوح بدل تقديم رأي بشري كأنه تعليم كتابي.

المنظور العقائدي:
- التزم بالفكر المعمداني المحافظ.
- أكّد سلطان الكتاب المقدس وكفايته.
- الخلاص بالنعمة بالإيمان بيسوع المسيح، وليس باستحقاق
  الأعمال البشرية.
- ميّز بين التبرير بالإيمان وثمر الإيمان في الأعمال الصالحة.
- افهم معمودية الماء في إطار معمودية المؤمن الذي أعلن إيمانه.
- لا تقدّم المعمودية باعتبارها استحقاقًا بشريًا للخلاص.
- احترم استقلال الكنيسة المحلية وكهنوت جميع المؤمنين.
- لا تدّعِ أن جميع المعمدانيين يتفقون في كل مسألة خلافية.
- لا تخترع عقائد أو مواقف خاصة بكنيسة القدس.

أسلوب الإجابة:
- أجب عن السؤال مباشرة وبوضوح.
- استشهد بالمراجع الكتابية ذات الصلة عندما تكون متأكدًا منها.
- لا تستخدم آيات خارج سياقها لإثبات فكرة مسبقة.
- لا تضف تأملات روحية شخصية أو انطباعات عاطفية.
- لا تكتب عظة أو صلاة أو رسالة تشجيع إلا إذا طُلب ذلك.
- لا تستخدم عبارات مثل: "أشعر أن الله يقول لك".
- لا تضف آراء شخصية أو تقاليد بشرية باعتبارها نصًا كتابيًا.
- إذا طلب المستخدم تفسيرًا، فاشرح المعنى من النص وسياقه،
  لا من انطباعاتك الشخصية.
- استخدم العربية الواضحة أو اللهجة الفلسطينية الطبيعية
  بحسب لغة المستخدم.
- كن مختصرًا ودقيقًا، ولا تكرر الأفكار بلا داعٍ.
- لا تدّعِ أنك إنسان أو راعٍ حقيقي.
"""

# =========================================
# 3. توليد الإجابة باستخدام OpenAI
# =========================================

def ask_openai(question):
    question = str(question or "").strip()

    if not question:
        return "اكتب سؤالك أولًا."

    if len(question) > 12000:
        return "السؤال طويل جدًا. اختصره وحاول مرة ثانية."

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
            temperature=0.3,
            max_tokens=1800,
        )

        if not response.choices:
            logger.error("OpenAI returned no choices")
            return "لم تصل إجابة واضحة. حاول مرة ثانية."

        answer = response.choices[0].message.content

        if answer and answer.strip():
            return answer.strip()

        return "لم تصل إجابة واضحة. حاول مرة ثانية."

    except APITimeoutError:
        logger.warning("OpenAI API timed out")
        return (
            "تأخرت الإجابة. حاول مرة ثانية بعد قليل."
        )

    except APIConnectionError:
        logger.exception("OpenAI connection error")
        return (
            "تعذّر الاتصال بخدمة الإجابات. حاول مرة ثانية."
        )

    except APIStatusError as error:
        status = error.status_code

        logger.error(
            "OpenAI API error: status=%s request_id=%s response=%s",
            status,
            getattr(error, "request_id", None),
            str(error)[:1000],
        )

        if status == 401:
            return (
                "مفتاح OpenAI API غير صحيح. "
                "راجع OPENAI_API_KEY في Render."
            )

        if status == 403:
            return (
                "لا توجد صلاحية للوصول إلى النموذج. "
                "راجع إعدادات حساب OpenAI."
            )

        if status == 404:
            return (
                "اسم النموذج غير صحيح أو غير متاح. "
                "راجع OPENAI_MODEL في Render."
            )

        if status == 429:
            return (
                "وصل الحساب إلى حد الاستخدام أو لا يوجد رصيد كافٍ. "
                "راجع حدود الاستخدام والفوترة في OpenAI."
            )

        if status >= 500:
            return (
                "خدمة الإجابات تواجه مشكلة مؤقتة. "
                "حاول مرة ثانية بعد قليل."
            )

        return (
            "تعذّر إكمال الطلب. راجع سجلات Render."
        )

    except Exception:
        logger.exception("Unexpected OpenAI error")
        return (
            "حدث خطأ غير متوقع أثناء إعداد الإجابة."
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

.hidden {
    display: none;
}
</style>
</head>

<body>
<main class="container">
    <h1>المساعد الكتابي</h1>

    <p class="intro">
        أهلًا بك. اطرح سؤالك عن الكتاب المقدس
        والإيمان المسيحي.
    </p>

    <textarea
        id="question"
        maxlength="12000"
        placeholder="اكتب سؤالك هنا..."
    ></textarea>

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
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        if (!response.ok && !data.answer) {
            throw new Error("Request failed");
        }

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
    return jsonify({
        "status": "ok",
        "provider": "OpenAI",
        "model": OPENAI_MODEL,
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

    if len(question) > 12000:
        return jsonify({
            "answer": "السؤال طويل جدًا. اختصره وحاول مرة ثانية."
        }), 400

    answer = ask_openai(question)

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
# 8. إرسال رسالة إلى Facebook Messenger
# =========================================

def send_facebook_message(recipient_id, text):
    if not FACEBOOK_PAGE_ACCESS_TOKEN:
        logger.error(
            "FACEBOOK_PAGE_ACCESS_TOKEN is not configured"
        )
        return False

    try:
        response = http_session.post(
            FACEBOOK_API_URL,
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
            timeout=(10, 20),
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
        return jsonify({
            "error": "Unsupported event"
        }), 404

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender = event.get("sender", {}).get("id")
            message = event.get("message", {})

            if not sender or not message:
                continue

            # تجاهل الرسائل الصادرة من الصفحة نفسها
            if message.get("is_echo"):
                continue

            # تجاهل الرسائل التي لا تحتوي على نص
            text_received = message.get("text", "")

            if not isinstance(text_received, str):
                continue

            text_received = text_received.strip()

            if not text_received:
                continue

            if len(text_received) > 12000:
                send_facebook_message(
                    sender,
                    "السؤال طويل جدًا. اختصره وأرسله مرة ثانية."
                )
                continue

            answer = ask_openai(text_received)

            send_facebook_message(sender, answer)

    return "EVENT_RECEIVED", 200


# =========================================
# 10. تشغيل التطبيق محليًا
# =========================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        debug=False,
    )
