
import os
import time
import logging

from google import genai
from google.genai import types
from google.genai import errors

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing from environment variables")

client = genai.Client(api_key=GEMINI_API_KEY)

# جرّب الموديل البديل أولًا، ويمكن تغييره من Render لاحقًا.
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION = """
أنت مساعد كتابي تابع لكنيسة الكتاب المقدس المعمدانية في القدس.

أجب عن الأسئلة المتعلقة بالكتاب المقدس والإيمان المسيحي
بأسلوب واضح ودقيق ومحترم، وباللغة التي يستخدمها السائل.

اعتمد على نص الكتاب المقدس وسياقه، واذكر أسماء الأسفار
والإصحاحات والأعداد عندما تكون متأكدًا منها.

ميّز بين النص الكتابي والتفسير أو الاستنتاج.
لا تختلق آيات أو مراجع كتابية.
إذا كان السؤال خارج اختصاصك، وضّح ذلك بأمانة.
لا تدّعِ أنك راعٍ أو إنسان حقيقي.
"""

def ask_gemini(question):
    question = str(question or "").strip()

    if not question:
        return "اكتب سؤالك الكتابي أولًا."

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=question,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    max_output_tokens=1800,
                    temperature=0.4,
                ),
            )

            answer = response.text

            if answer and answer.strip():
                return answer.strip()

            return "ما قدرت أجهّز إجابة واضحة. جرّب صياغة السؤال بطريقة ثانية."

        except errors.ServerError as e:
            # أخطاء الخادم المؤقتة، ومنها 503.
            logger.warning(
                "Gemini server error on attempt %s: %s",
                attempt + 1,
                e,
            )

            if attempt < 2:
                time.sleep(2 * (attempt + 1))
            else:
                return (
                    "خدمة الإجابة الكتابية مشغولة حاليًا. "
                    "جرّب مرة ثانية بعد دقيقة."
                )

        except errors.APIError as e:
            logger.exception("Gemini API error")

            status = getattr(e, "code", None)

            if status == 429:
                return (
                    "وصلنا للحد المؤقت من الطلبات. "
                    "جرّب مرة ثانية بعد قليل."
                )

            if status in (401, 403):
                return (
                    "في مشكلة بإعدادات مفتاح Gemini API. "
                    "يرجى مراجعة إعدادات الخدمة."
                )

            return (
                "صار خطأ أثناء الاتصال بخدمة الإجابات. "
                "جرّب مرة ثانية لاحقًا."
            )

        except Exception:
            logger.exception("Unexpected error while asking Gemini")
            return "صار خطأ غير متوقع. جرّب مرة ثانية لاحقًا."

    return "الخدمة غير متاحة حاليًا. جرّب مرة ثانية لاحقًا."
