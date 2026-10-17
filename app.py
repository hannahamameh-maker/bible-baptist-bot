"""
Bible Baptist Church - Jerusalem | Messenger Bot
كنيسة الكتاب المقدس المعمدانية - القدس

A Facebook Messenger bot for the church page (ID: 100080177692918).
- Answers visitors in Arabic (and English if they write in English)
- General/doctrinal answers follow conservative Baptist thought
  (v4, 2026-10-17, per Hanna's instruction), documented in DOCTRINE.md.
  Further-reading sources given to visitors (v5): baptistarabic.org for
  Baptist beliefs/practices, and ar.thegospelcoalition.org (TGC Arabic)
  for gospel / Christian-life / biblical-question topics.
- Verse texts come from eBible.org's Arabic Van Dyck edition
  (https://ebible.org/arb-vd), fetched live per chapter and cached
  (v3, 2026-10-17, per Hanna's instruction), with a small locally
  verified list as offline fallback.
- Faith / Bible questions are answered ONLY from a curated library of
  verified answers (v2, 2026-10-17). Free-form Groq answers were removed
  as the default because the model invented inaccurate verse texts and
  references. Groq runs only if ALLOW_GROQ=1, and even then its answer
  is blocked and replaced with a safe hand-off if it quotes a verse or
  cites a reference that is not in the verified list below.
- Built-in answers for: about the church, service time, address,
  coming with family, what happens in a meeting, prayer requests
- v6 (2026-10-17): also replies to questions in comments on Page posts,
  via the webhook "feed" subscription — same curated answers publicly,
  other questions get a short Messenger invitation; the Page's own
  comments and non-question comments are never answered.
- /setup activates the Get Started button, greeting and persistent menu

Required environment variables:
  PAGE_ACCESS_TOKEN   Token for the Facebook Page
  GROQ_KEY            Groq API key (gsk_...)  [GROQ_API_KEY also accepted]
  VERIFY_TOKEN        Webhook verify token   (default: baptist2026)

Optional:
  CHURCH_SERVICE_TIME e.g. "يوم الأحد الساعة 10:30 صباحًا"
  CHURCH_ADDRESS      e.g. exact church address
  GROQ_MODEL          default: openai/gpt-oss-120b
                      (llama-3.3-70b-versatile was shut down by Groq on 2026-08-16)
  APP_SECRET          Facebook app secret (enables signature check)
"""

import hashlib
import hmac
import json
import os

import requests
from flask import Flask, abort, request

app = Flask(__name__)

# ---------------------------------------------------------------- config
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "").strip()
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "baptist2026").strip()
GROQ_KEY = (
    os.environ.get("GROQ_KEY", "").strip()
    or os.environ.get("GROQ_API_KEY", "").strip()
)
APP_SECRET = os.environ.get("APP_SECRET", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b").strip()
# v2: Groq is OFF by default. Set ALLOW_GROQ=1 only to experiment;
# curated answers and the verse guard stay in force either way.
ALLOW_GROQ = os.environ.get("ALLOW_GROQ", "0").strip() == "1"
# v6: the bot also replies to questions asked in comments on Page posts
# (Hanna's request, 2026-10-17). Needs the webhook "feed" subscription
# and the pages_manage_engagement permission (see README / APP-REVIEW).
COMMENTS_ENABLED = os.environ.get("COMMENTS_ENABLED", "1").strip() != "0"
PAGE_ID = os.environ.get("PAGE_ID", "100080177692918").strip()

CHURCH_NAME_AR = "كنيسة الكتاب المقدس المعمدانية - القدس"
CHURCH_NAME_EN = "Bible Baptist Church - Jerusalem"
SERVICE_TIME = os.environ.get("CHURCH_SERVICE_TIME", "").strip()
ADDRESS = os.environ.get("CHURCH_ADDRESS", "").strip()

# Graph API version: v21.0 is removed by Meta on 2027-01-21, so the bot
# defaults to v24.0 (available until 2028-02-18). Override with
# GRAPH_API_VERSION in Render if a future migration is needed.
GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v24.0").strip()
GRAPH = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

WELCOME = (
    "أهلا وسهلا فيك باسم يسوع في كنيسة الكتاب المقدس المعمدانية - القدس!\n"
    "يسعدنا تواصلك معنا. كيف بنقدر نساعدك اليوم؟"
)

# In-memory short history per user (resets when the server restarts).
HISTORY = {}
MAX_HISTORY = 6


def service_time_text():
    if SERVICE_TIME:
        return (
            f"اجتماعنا {SERVICE_TIME}. "
            "بنفتح الباب قبل الموعد بربع ساعة، وبعد العبادة في وقت للتعارف والضيافة. أهلا فيك."
        )
    return (
        "أهلا فيك. لمعرفة موعد الاجتماع هذا الأسبوع بالضبط، "
        "اترك رسالتك هون وسنرد عليك بالتأكيد في أقرب وقت. أهلا وسهلا فيك بيننا."
    )


def address_text():
    if ADDRESS:
        return (
            f"عنواننا: {ADDRESS}\n"
            "إذا بتحب، ابعتلنا من وين جاي وبندلّك على أسهل طريق."
        )
    return (
        "أهلا فيك. ابعتلنا من وين جاي، وسنرسل لك العنوان بالضبط وأسهل طريق للوصول إلينا."
    )


FIXED_ANSWERS = {
    "ABOUT_CHURCH": (
        "نحن كنيسة الكتاب المقدس المعمدانية - القدس: عائلة إيمان نجتمع للعبادة، "
        "ونتعلم من كلمة الله، ونصلي لبعضنا البعض، ونشجع بعضنا في رحلة الإيمان.\n"
        "تعال كما أنت، مع أسئلتك وأفراحك وأثقالك. أهلا وسهلا فيك بيننا."
    ),
    "SERVICE_TIME": None,  # filled dynamically
    "ADDRESS": None,       # filled dynamically
    "WITH_FAMILY": (
        "أكيد، أهلا فيك وبعيلتك. وفي وقت للتعارف والضيافة بعد العبادة."
    ),
    "WHAT_HAPPENS": (
        "بنبدأ بالترنيم والعبادة، وبعدها بنسمع كلمة من الكتاب المقدس، "
        "وبنختم بالصلاة. الاجتماع حوالي ساعة، وبعده تعارف وضيافة. "
        "تعال كما أنت، بدون أي التزام."
    ),
    "PRAYER_REQUEST": (
        "يسعدنا نصلي لأجلك. اكتب طلبة الصلاة هون بكلماتك، "
        "وسنرفعها في صلواتنا. الرب يسمع ويستجيب.\n"
        "«لا تهتموا بشيء، بل في كل شيء بالصلاة والدعاء مع الشكر، لتُعلم طلباتكم لدى الله» (فيلبي 4: 6)."
    ),
    "TALK_TO_US": (
        "أسئلتك مرحّب فيها، وهذا أصلا سبب وجودنا. "
        "اكتب سؤالك هون عن الإيمان أو الكتاب المقدس أو الكنيسة، وسنجاوبك. "
        "وإذا حبيت، تقدر تيجي تحضر مرة وتتعرف علينا بدون أي ضغط."
    ),
}

QUICK_REPLIES = [
    {"content_type": "text", "title": "عن الكنيسة", "payload": "ABOUT_CHURCH"},
    {"content_type": "text", "title": "موعد الاجتماع", "payload": "SERVICE_TIME"},
    {"content_type": "text", "title": "العنوان", "payload": "ADDRESS"},
    {"content_type": "text", "title": "طلب صلاة", "payload": "PRAYER_REQUEST"},
    {"content_type": "text", "title": "عندي سؤال", "payload": "TALK_TO_US"},
]

SYSTEM_PROMPT = f"""أنت مساعد صفحة {CHURCH_NAME_AR} ({CHURCH_NAME_EN}) على فيسبوك ماسنجر.
هذا البرومبت يُستخدم فقط عند تفعيل ALLOW_GROQ=1، والقواعد صارمة:

- ممنوع منعا باتا أن تنقل نص أي آية حرفيا أو أن تضع نصا بين علامتي اقتباس
  وتنسبه للكتاب المقدس. النماذج اللغوية تخترع نصوص آيات غير موجودة، وهذا حدث فعلا.
- ممنوع اختراع شاهد كتابي: لا تذكر سفرا وإصحاحا وعددا إلا إذا كنت متأكدا
  تماما أنه موجود، والأفضل أن تحيل الزائر لقراءة الإصحاح بنفسه بدون نقل النص.
- إذا لم تكن متأكدا من الإجابة الدقيقة، قل ذلك بصراحة وقل إن فريق الكنيسة
  سيتابع معه. الاعتراف بعدم المعرفة أفضل من إجابة خاطئة.
- رد بنفس لغة الزائر، باختصار (2-4 جمل)، وبدون آراء لاهوتية مفصّلة:
  اشرح الفكرة العامة فقط وادعُه للمتابعة مع الكنيسة أو لزيارتها بدون ضغط.
- الإطار اللاهوتي الوحيد المسموح: الفكر المعمداني المحافظ — الكتاب المقدس
  السلطة الوحيدة للإيمان والممارسة، الخلاص بالنعمة بالإيمان وحده، معمودية
  المؤمن بالتغطيس، كهنوت جميع المؤمنين. مصادر الأجوبة والقراءة الأوسع:
  baptistarabic.org للمعتقدات المعمدانية، وائتلاف الإنجيل بالعربي
  (ar.thegospelcoalition.org) لمواضيع الإنجيل والحياة المسيحية والأسئلة الكتابية.
  خارج هذا الإطار لا تجب لاهوتيًا، وحوّل السؤال لمتابعة الكنيسة.
- موعد الاجتماع الرسمي: "{SERVICE_TIME or 'غير مُدخل بعد'}" — وعنوان الكنيسة:
  "{ADDRESS or 'غير مُدخل بعد'}" — لا تخترعهما أبدا إذا لم يكونا مُدخلين.
- لا تدّعِ أنك القسيس أو إنسان، ولا تجمع معلومات حساسة أبدا.
"""

# ------------------------------------------------------------ verified texts
# النصوص التالية منقولة حرفيا من ترجمة فان دايك (سميث وفان دايك)،
# وتم التحقق منها قبل إضافتها. هذه هي الآيات الوحيدة المسموح للبوت
# بنقل نصها. لا تُضف أي آية جديدة قبل التحقق من نصها من مصدر موثوق.
VERIFIED_VERSES = {
    "يوحنا 3: 16": "لأنه هكذا أحب الله العالم حتى بذل ابنه الوحيد، لكي لا يهلك كل من يؤمن به، بل تكون له الحياة الأبدية",
    "يوحنا 14: 6": "أنا هو الطريق والحق والحياة. ليس أحد يأتي إلى الآب إلا بي",
    "متى 11: 28": "تعالوا إليّ يا جميع المتعبين والثقيلي الأحمال، وأنا أريحكم",
    "فيلبي 4: 6-7": "لا تهتموا بشيء، بل في كل شيء بالصلاة والدعاء مع الشكر، لتُعلم طلباتكم لدى الله. وسلام الله الذي يفوق كل عقل، يحفظ قلوبكم وأفكاركم في المسيح يسوع",
    "إشعياء 41: 10": "لا تخف لأني معك. لا تتلفت لأني إلهك. قد أيدتك وأعنتك وعضدتك بيمين بري",
    "رومية 10: 9": "لأنك إن اعترفت بفمك بالرب يسوع، وآمنت بقلبك أن الله أقامه من الأموات، خلصت",
    "مزمور 23: 1": "الرب راعيّ فلا يعوزني شيء",
}

# References a (rare, ALLOW_GROQ=1) Groq answer may cite without being blocked.
ALLOWED_REFS = {
    "يوحنا 3:16", "يوحنا 14:6", "متى 11:28", "فيلبي 4:6", "فيلبي 4:7",
    "فيلبي 4:6-7", "إشعياء 41:10", "اشعياء 41:10", "رومية 10:9",
    "مزمور 23:1", "المزامير 23:1",
}


def _v(ref):
    return f"«{VERIFIED_VERSES[ref]}» ({ref})"


def safe_handoff():
    return (
        "سؤالك مهم، وبيستحق جواب دقيق وصحيح — عشان هيك ما رح أعطيك جواب تلقائي ممكن يكون غير دقيق.\n"
        "رسالتك وصلت لفريق الكنيسة من هذه الصفحة، وسيتابعوا معك فيها. "
        "وبينما تنتظر، بقدر أساعدك فورا بموعد الاجتماع أو العنوان أو طلب صلاة من القائمة تحت — "
        "وأهلا فيك تزورنا وتسأل وجهًا لوجه."
    )


# ------------------------------------------------- eBible live verse source
# v3 (2026-10-17, per Hanna's instruction): verse texts are taken from
# eBible.org's Arabic Van Dyck edition — https://ebible.org/arb-vd —
# never from a language model's memory. Chapter pages there are named
# {BOOKCODE}{NN}.htm (Psalms: 3 digits), and each verse is marked
# <span class="verse" id="V{n}">. Chapters are cached in memory, one
# fetch per chapter. If the site is unreachable, the bot falls back to
# the small locally verified list above; if neither works it says so
# instead of inventing a text. The translation is Public Domain.
import html as _htmllib
import re

EBIBLE_BASE = "https://ebible.org/arb-vd"
_CHAPTER_CACHE = {}

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
                           "01234567890123456789")


def _norm_digits(s):
    return s.translate(_AR_DIGITS)


def _norm_ar(s):
    s = re.sub(r"[ً-ْٰـ]", "", s)
    s = s.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا")
    s = s.replace("ى", "ي").replace("ة", "ه")
    return s


# (code, canonical Arabic name, [name variants as visitors type them])
BOOKS = [
    ("GEN", "التكوين", ["التكوين", "سفر التكوين", "genesis"]),
    ("EXO", "الخروج", ["الخروج", "exodus"]),
    ("LEV", "اللاويين", ["اللاويين"]),
    ("NUM", "العدد", ["العدد"]),
    ("DEU", "التثنية", ["التثنية"]),
    ("JOS", "يشوع", ["يشوع"]),
    ("JDG", "القضاة", ["القضاة"]),
    ("RUT", "راعوث", ["راعوث"]),
    ("1SA", "صموئيل الأول", ["صموئيل الأول", "صموئيل الاول", "1 صموئيل"]),
    ("2SA", "صموئيل الثاني", ["صموئيل الثاني", "2 صموئيل"]),
    ("1KI", "الملوك الأول", ["الملوك الأول", "الملوك الاول", "1 ملوك"]),
    ("2KI", "الملوك الثاني", ["الملوك الثاني", "2 ملوك"]),
    ("1CH", "أخبار الأيام الأول", ["أخبار الأيام الأول", "اخبار الايام الاول"]),
    ("2CH", "أخبار الأيام الثاني", ["أخبار الأيام الثاني", "اخبار الايام الثاني"]),
    ("EZR", "عزرا", ["عزرا"]),
    ("NEH", "نحميا", ["نحميا"]),
    ("EST", "أستير", ["أستير", "استير"]),
    ("JOB", "أيوب", ["أيوب", "ايوب"]),
    ("PSA", "مزمور", ["المزامير", "مزامير", "المزمور", "مزمور", "psalms", "psalm"]),
    ("PRO", "الأمثال", ["الأمثال", "امثال"]),
    ("ECC", "الجامعة", ["الجامعة"]),
    ("SNG", "نشيد الأنشاد", ["نشيد الأنشاد", "نشيد الانشاد", "نشيد سليمان"]),
    ("ISA", "إشعياء", ["إشعياء", "اشعياء", "أشعياء", "isaiah"]),
    ("JER", "إرميا", ["إرميا", "ارميا"]),
    ("LAM", "مراثي إرميا", ["مراثي إرميا", "المراثي", "مراثي"]),
    ("EZK", "حزقيال", ["حزقيال"]),
    ("DAN", "دانيال", ["دانيال", "daniel"]),
    ("HOS", "هوشع", ["هوشع"]),
    ("JOL", "يوئيل", ["يوئيل"]),
    ("AMO", "عاموس", ["عاموس"]),
    ("OBA", "عوبديا", ["عوبديا"]),
    ("JON", "يونان", ["يونان"]),
    ("MIC", "ميخا", ["ميخا"]),
    ("NAM", "ناحوم", ["ناحوم"]),
    ("HAB", "حبقوق", ["حبقوق"]),
    ("ZEP", "صفنيا", ["صفنيا"]),
    ("HAG", "حجي", ["حجي"]),
    ("ZEC", "زكريا", ["زكريا"]),
    ("MAL", "ملاخي", ["ملاخي"]),
    ("MAT", "متى", ["متى", "matthew"]),
    ("MRK", "مرقس", ["مرقس", "mark"]),
    ("LUK", "لوقا", ["لوقا", "luke"]),
    ("JHN", "يوحنا", ["يوحنا", "john"]),
    ("ACT", "أعمال الرسل", ["أعمال الرسل", "اعمال الرسل", "acts"]),
    ("ROM", "رومية", ["رومية", "romans"]),
    ("1CO", "كورنثوس الأولى", ["كورنثوس الأولى", "كورنثوس الاولى", "1 كورنثوس"]),
    ("2CO", "كورنثوس الثانية", ["كورنثوس الثانية", "كورنثوس الثانيه", "2 كورنثوس"]),
    ("GAL", "غلاطية", ["غلاطية"]),
    ("EPH", "أفسس", ["أفسس", "افسس", "ephesians"]),
    ("PHP", "فيلبي", ["فيلبي", "philippians"]),
    ("COL", "كولوسي", ["كولوسي"]),
    ("1TH", "تسالونيكي الأولى", ["تسالونيكي الأولى", "تسالونيكي الاولى"]),
    ("2TH", "تسالونيكي الثانية", ["تسالونيكي الثانية"]),
    ("1TI", "تيموثاوس الأولى", ["تيموثاوس الأولى", "تيموثاوس الاولى"]),
    ("2TI", "تيموثاوس الثانية", ["تيموثاوس الثانية"]),
    ("TIT", "تيطس", ["تيطس"]),
    ("PHM", "فليمون", ["فليمون"]),
    ("HEB", "العبرانيين", ["العبرانيين", "عبرانيين", "hebrews"]),
    ("JAS", "يعقوب", ["يعقوب", "james"]),
    ("1PE", "بطرس الأولى", ["بطرس الأولى", "بطرس الاولى"]),
    ("2PE", "بطرس الثانية", ["بطرس الثانية"]),
    ("1JN", "يوحنا الأولى", ["يوحنا الأولى", "يوحنا الاولى", "1 يوحنا"]),
    ("2JN", "يوحنا الثانية", ["يوحنا الثانية", "2 يوحنا"]),
    ("3JN", "يوحنا الثالثة", ["يوحنا الثالثة", "3 يوحنا"]),
    ("JUD", "يهوذا", ["يهوذا"]),
    ("REV", "رؤيا يوحنا", ["رؤيا يوحنا", "الرؤيا", "رؤيا", "revelation"]),
]
_CANON = {code: name for code, name, _ in BOOKS}
_VARIANTS = []
for _code, _name, _vars in BOOKS:
    for _var in _vars:
        _VARIANTS.append((_norm_ar(_var.lower()), _code))
_VARIANTS.sort(key=lambda x: len(x[0]), reverse=True)
_SINGLE_CHAPTER = {"OBA", "PHM", "2JN", "3JN", "JUD"}


def parse_reference(raw_text):
    """Find a Bible reference in a visitor message.
    Returns (code, chapter, verse_start, verse_end) — verse_start is
    None for a chapter-only request — or None if no reference found."""
    t = _norm_ar(_norm_digits(raw_text).lower())
    for variant, code in _VARIANTS:
        m = re.search(
            rf"{re.escape(variant)}\s*(\d{{1,3}})\s*[:：]\s*(\d{{1,3}})"
            rf"(?:\s*[-–]\s*(\d{{1,3}}))?",
            t,
        )
        if m:
            v_end = int(m.group(3)) if m.group(3) else int(m.group(2))
            return code, int(m.group(1)), int(m.group(2)), v_end
    for variant, code in _VARIANTS:
        m = re.search(rf"{re.escape(variant)}\s*(\d{{1,3}})(?!\s*[:：]?\s*\d)", t)
        if m:
            n = int(m.group(1))
            if code in _SINGLE_CHAPTER and n > 1:
                return code, 1, n, n
            return code, n, None, None
    return None


def fetch_chapter(code, chapter):
    """Download one chapter from eBible arb-vd and parse its verses
    into {verse_number: exact text}. Cached; None on any failure."""
    key = (code, chapter)
    if key in _CHAPTER_CACHE:
        return _CHAPTER_CACHE[key]
    pad = 3 if code == "PSA" else 2
    url = f"{EBIBLE_BASE}/{code}{chapter:0{pad}d}.htm"
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; BibleBaptistBot/3.0)"},
            timeout=20,
        )
        if r.status_code != 200:
            app.logger.error("eBible %s -> HTTP %s", url, r.status_code)
            return None
        page = r.content.decode("utf-8", "replace")
    except requests.RequestException as e:
        app.logger.error("eBible fetch error %s: %s", url, e)
        return None
    spans = list(re.finditer(r'<span class="verse" id="V(\d+)">.*?</span>',
                             page, flags=re.S))
    verses = {}
    for i, m in enumerate(spans):
        start = m.end()
        end = spans[i + 1].start() if i + 1 < len(spans) else len(page)
        seg = re.split(r"</?div", page[start:end], maxsplit=1)[0]
        clean = _htmllib.unescape(re.sub(r"<[^>]+>", " ", seg))
        clean = re.sub(r"\s+", " ", clean.replace("\xa0", " ")).strip()
        if clean:
            verses[int(m.group(1))] = clean
    if not verses:
        return None
    _CHAPTER_CACHE[key] = verses
    return verses


def ebible_text(code, chapter, v_start, v_end=None):
    """Exact verse text (or range) from eBible, or None."""
    verses = fetch_chapter(code, chapter)
    if not verses:
        return None
    v_end = v_end or v_start
    parts = []
    for v in range(v_start, v_end + 1):
        if v not in verses:
            return None
        parts.append(verses[v])
    return " ".join(parts)


def _display(code, chapter, v_start=None, v_end=None):
    name = _CANON[code]
    if v_start is None:
        return f"{name} {chapter}"
    if v_end and v_end != v_start:
        return f"{name} {chapter}: {v_start}-{v_end}"
    return f"{name} {chapter}: {v_start}"


def quote_verse(code, chapter, v_start, v_end=None):
    """«verse text» (Reference) — text fetched live from eBible;
    falls back to the locally verified list; None if neither works."""
    text = ebible_text(code, chapter, v_start, v_end)
    display = _display(code, chapter, v_start, v_end)
    if text is None:
        text = VERIFIED_VERSES.get(display)
    if text is None:
        return None
    return f"«{text}» ({display})"


def verse_request_answer(raw_text, parsed):
    code, chapter, v_start, v_end = parsed
    if v_start is None:  # chapter-only, e.g. «مزمور 23»
        verses = fetch_chapter(code, chapter)
        if not verses:
            return None
        ordered = [verses[k] for k in sorted(verses)]
        joined = " ".join(ordered)
        if len(ordered) > 6 or len(joined) > 1500:
            return (
                f"إصحاح {_display(code, chapter)} طويل شوي لرسالة وحدة. "
                "حددلي رقم الآية أو الآيات اللي بدك إياها، مثلا أول آية، وببعتلك نصها بالضبط."
            )
        return (
            f"«{joined}»\n({_display(code, chapter)} كامل)\n"
            "النص من ترجمة فان دايك، من موقع eBible (ebible.org/arb-vd)."
        )
    capped = False
    if v_end and v_end - v_start > 4:
        v_end = v_start + 4
        capped = True
    q = quote_verse(code, chapter, v_start, v_end)
    if q is None:
        return None
    answer = q + "\nالنص من ترجمة فان دايك، من موقع eBible (ebible.org/arb-vd)."
    if capped:
        answer += "\n(بعتّلك أول ٥ آيات من اللي طلبته — حدد الباقي وببعتلك إياه.)"
    if any(k in raw_text for k in ("معنى", "شرح", "تفسير", "يعني", "فسّر", "فسر")):
        answer += (
            "\nهاد هو النص بالضبط كما طلبت. وشرحه بدقة بيتابع معك فيه فريق الكنيسة، "
            "لأن التفسير ما بنرتجله تلقائيا."
        )
    return answer


# Curated, pastor-safe answers (v3): the explanation is written here,
# and every quoted verse is fetched live from eBible at answer time
# (quote_verse), with the locally verified list as fallback.
# Each entry: (keywords, template with {q0}/{q1}..., [(code, ch, v1, v2)])
TOPIC_ANSWERS = [
(
        ("معمودية", "معموديه", "اتعمد", "أتعمد", "تعميد", "عماد", "baptism", "baptize"),
        (
            "حسب الكتاب المقدس والفكر المعمداني، المعمودية فريضة أمر فيها الرب يسوع، "
            "وبتتم بعد الإيمان الشخصي بالمسيح، وبالتغطيس الكامل في الماء — مش بالرش، "
            "ومش للأطفال، لأنها شهادة علنية عن إيمان حصل قبلها:\n"
            "{q0}\n"
            "وهي رمز لموت المؤمن وقيامته مع المسيح، مش وسيلة للخلاص — الخلاص بالإيمان "
            "وحده، والمعمودية خطوة طاعة وإعلان بعده:\n"
            "{q1}\n"
            "لقراءة أوسع عن معتقدات المعمدانيين: baptistarabic.org\n"
            "وإذا آمنت بالمسيح وحابب تعتمد، احكيلنا هون وبنتابع معك."
        ),
        [("ACT", 8, 36, 37), ("ROM", 6, 3, 4)],
    ),
    (
        ("عشاء رباني", "عشاء الرب", "كسر الخبز", "مائدة الرب", "التناول", "lord's supper", "communion"),
        (
            "العشاء الرباني (كسر الخبز) هو الفريضة الثانية اللي أعطاها الرب يسوع "
            "لكنيسته. بنمارسه تذكارًا لموته من أجلنا إلى أن يجيء — هو ذكرى ورمز "
            "لجسده ودمه المبذولين عنا، مش ذبيحة جديدة، والخبز والكأس ما بيتحولوا فعليًا:\n"
            "{q0}\n"
            "بنحتفل فيه ككنيسة بفحص النفس والصلاة والتوبة، وقلوبنا على الرب اللي بذل نفسه عنا.\n"
            "لقراءة أوسع: baptistarabic.org"
        ),
        [("1CO", 11, 23, 26)],
    ),
    (
        ("يفقد خلاص", "يخسر خلاص", "ضمان الخلاص", "ضمان الأبدي", "يفقد الخلاص", "ارتداد", "يرتد عن", "eternal security", "lose salvation", "once saved"),
        (
            "حسب الفكر المعمداني المحافظ، اللي بيولد من الله ولادة حقيقية وبيؤمن "
            "بالمسيح إيمانًا حقيقيًا، الله بيحفظه بقوته وما بيفقد خلاصه — لأن الخلاص "
            "عطية الله وعمله من أوله لآخره، مش متعلق بثباتنا إحنا:\n"
            "{q0}\n"
            "وهاد مش رخصة للحياة بالخطية، بل طمأنينة بتدفع المؤمن للقداسة والشكر "
            "والثبات. وإذا حابب تحكي بهالموضوع مع القسيس، ابعتلنا وبنتابع معك.\nلقراءة أوسع: baptistarabic.org"
        ),
        [("JHN", 10, 28, 29)],
    ),
    (
        ("أعمالي", "اعمالي", "الأعمال الصالحة بتخلص", "الاعمال تخلص", "الأعمال تخلص", "good works save", "saved by works"),
        (
            "الجواب الكتابي الواضح: الخلاص بالنعمة وحدها، بالإيمان وحده، بالمسيح "
            "وحده — مش بالأعمال الصالحة مهما كثرت، عشان ما حدا يفتخر قدام الله:\n"
            "{q0}\n"
            "والأعمال الصالحة إلها مكانها المهم: هي ثمر الإيمان الحقيقي ودليل حياته، "
            "والمؤمن بيظهر إيمانه بأعماله — بس هي نتيجة الخلاص، مش سبب له.\nلقراءة أوسع: baptistarabic.org"
        ),
        [("EPH", 2, 8, 9)],
    ),
    (
        ("العذراء", "شفاعة", "شفيع", "التشفع", "القديسين", "الاعتراف للكاهن", "اعترف عند", "وسيط بين", "واسطة بيننا", "saints", "intercession", "virgin mary"),
        (
            "بنحترم مريم العذراء كأم الرب يسوع، وبنتعلم من إيمانها وطاعتها، وبنكرم "
            "قديسي الكتاب المقدس — بس الصلاة والعبادة بحسب الكتاب بتتوجه لله وحده، "
            "لأن الوسيط الواحد بين الله والناس هو يسوع المسيح:\n"
            "{q0}\n"
            "وعشان هيك بنروح مباشرة للآب باسم يسوع، وبنعترف بخطايانا لله نفسه، وهو أمين وبيغفر:\n"
            "{q1}\n"
            "القسيس أخ وخادم بيصلي معك وبيرشدك من الكتاب، بس الغفران والوساطة للمسيح وحده.\nلقراءة أوسع: baptistarabic.org"
        ),
        [("1TI", 2, 5, None), ("1JN", 1, 9, None)],
    ),
    (
        ("سلطة الكتاب", "وحي الكتاب", "الكتاب المقدس معصوم", "معصوم", "مصداقية الكتاب", "ليش بتثقوا بالكتاب", "sola scriptura", "inerrancy", "bible authority"),
        (
            "حسب الفكر المعمداني، الكتاب المقدس هو كلمة الله الموحى بها، وهو السلطة "
            "الوحيدة المكتوبة للإيمان والممارسة — فوق التقاليد والآراء البشرية، "
            "وعلى نوره بنختبر كل تعليم:\n"
            "{q0}\n"
            "عشان هيك كرازتنا ودراستنا دايمًا من الكتاب نفسه، وبنشجعك تقرأه بنفسك "
            "وتسألنا عن أي شي فيه.\n"
            "لقراءة أوسع: baptistarabic.org"
        ),
        [("2TI", 3, 16, 17)],
    ),
    (
        ("ثالوث", "أقانيم", "اقانيم", "ثلاثة آلهة", "trinity"),
        (
            "بنؤمن بإله واحد أزلي، قائم بثلاثة أقانيم متساوية بالجوهر: الآب والابن "
            "والروح القدس — مش ثلاثة آلهة، ومش إله واحد بيتنقل بين ثلاثة أدوار. "
            "هاد إعلان الكتاب عن الله، مثلًا بقول الرب يسوع بأمر المعمودية:\n"
            "{q0}\n"
            "هاد سر عظيم ما بتستوعبه عقولنا كليًا، وبنقبله بالإيمان كما أعلنه الله عن نفسه."
        ),
        [("MAT", 28, 19, None)],
    ),
    (
        ("مين هم المعمداني", "من هم المعمداني", "شو يعني معمداني", "ليش اسمكم معمداني", "شو الفرق بين المعمداني", "who are baptists", "what is a baptist"),
        (
            "المعمدانيون مؤمنون بيتمسكوا معًا بمجموعة قناعات من الكتاب المقدس، أهمها: "
            "ربوبية يسوع المسيح، والكتاب المقدس السلطة الوحيدة المكتوبة للإيمان "
            "والممارسة، والخلاص بالنعمة بالإيمان وحده باستجابة شخصية طوعية (توبة "
            "وإيمان)، وكهنوت جميع المؤمنين، ومعمودية المؤمنين بالتغطيس في الماء بعد "
            "إيمانهم، وكنيسة محلية مستقلة إدارتها جماعية، وفريضتين فقط: المعمودية "
            "والعشاء الرباني.\n"
            "والاسم «معمدانيين» مرتبط بالتمسك بمعمودية المؤمنين بالتغطيس كما في الكتاب المقدس.\n"
            "لقراءة موسعة عن معتقدات المعمدانيين وممارساتهم: baptistarabic.org\n"
            "وأهلا فيك تزورنا وتتعرف علينا بنفسك."
        ),
        [],
    ),
    (
        ("كيف اصلي", "كيف أصلي", "علمني اصلي", "علمني أصلي", "how to pray", "teach me to pray"),
        (
            "الصلاة ببساطة هي إنك تحكي مع الله بصدق وبكلماتك أنت.\n"
            "تقدر تبدأ بالشكر، وبعدها تحكيله عن اللي بقلبك وتطلب منه، وبتصلي باسم يسوع.\n"
            "يقول الكتاب: {q0}.\n"
            "وإذا بتحب، اكتب طلبتك هون وبنصلي لأجلك ككنيسة.\nلقراءة أوسع عن الصلاة والحياة المسيحية: ar.thegospelcoalition.org"
        ),
        [("PHP", 4, 6, 7)],
    ),
    (
        ("خلاص", "اخلص", "أخلص", "اغفر", "غفران", "خطاياي", "خطيتي", "السماء", "الحياة الابدية", "الحياة الأبدية", "اتوب", "أتوب", "توبة", "salvation", "be saved", "forgive my sin", "eternal life", "heaven"),
        (
            "الخلاص عطية من الله بالنعمة وبالإيمان بيسوع المسيح — مش بالأعمال الصالحة، "
            "ولا بالمعمودية، ولا بعضوية كنيسة، بل باستجابة شخصية طوعية: توبة عن الخطية وإيمان بالمسيح.\n"
            "{q0}.\n"
            "والطريق ببساطة: {q1}.\n"
            "تقدر هسا تصلي بكلماتك: تعترف بخطيتك، وتطلب الغفران، وتدعو يسوع يكون مخلّصك وربّك. "
            "وإذا عملت هيك أو عندك أسئلة، احكيلنا هون — بنحب نتابع معك ونرحب فيك بالكنيسة.\nلقراءة أوسع عن الإنجيل والخلاص: ar.thegospelcoalition.org"
        ),
        [("JHN", 3, 16, None), ("ROM", 10, 9, None)],
    ),
    (
        ("من هو يسوع", "من يسوع", "مين يسوع", "مين المسيح", "من هو المسيح", "who is jesus", "who is christ"),
        (
            "يسوع المسيح هو ابن الله، جاء ليعطينا حياة وغفرانا، ومات على الصليب لأجل خطايانا وقام من الأموات.\n"
            "قال عن نفسه: {q0}.\n"
            "والله أرسله محبة فينا: {q1}.\n"
            "إذا بتحب تعرف أكتر، احضر اجتماعنا أو ابعتلنا سؤالك ونتابع معك.\nلقراءة أوسع عن يسوع المسيح: ar.thegospelcoalition.org"
        ),
        [("JHN", 14, 6, None), ("JHN", 3, 16, None)],
    ),
    (
        ("الله بيحب", "الله يحبني", "محبة الله", "does god love", "god love me"),
        (
            "نعم، الله بيحبك محبة حقيقية أثبتها بالفعل مش بس بالكلام.\n"
            "{q0}.\n"
            "ومهما حاسس اليوم، دعوته مفتوحة إلك كما أنت.\nلقراءة أوسع: ar.thegospelcoalition.org"
        ),
        [("JHN", 3, 16, None)],
    ),
    (
        ("قلق", "خايف", "خائف", "خوف", "مضغوط", "سلام", "anxiety", "anxious", "afraid", "fear", "worried"),
        (
            "بنفهم شعورك، والله بيعرف اللي بتمر فيه وقريب منك.\n"
            "{q0}.\n"
            "ويدعوك تترك همك عنده بالصلاة: {q1}.\n"
            "إذا بتحب، اكتب طلبة صلاة هون وبنصلي لأجلك اليوم.\nلقراءة أوسع عن السلام والرجاء: ar.thegospelcoalition.org"
        ),
        [("ISA", 41, 10, None), ("PHP", 4, 6, 7)],
    ),
    (
        ("تعبان", "متعب", "تعبت", "اثقال", "أثقال", "راحة", "tired", "weary", "burden", "rest"),
        (
            "دعوة يسوع مفتوحة لكل متعب.\n"
            "قال: {q0}.\n"
            "تعال إليه بالصلاة كما أنت، وأهلا فيك بيننا بالكنيسة لوقت عبادة وراحة وتعارف.\nلقراءة أوسع: ar.thegospelcoalition.org"
        ),
        [("MAT", 11, 28, None)],
    ),
    (
        ("يائس", "يأس", "رجاء", "امل", "أمل", "محبط", "hope", "hopeless", "give up"),
        (
            "حتى بوقت اليأس، إنت مش لحالك والرجاء بالله حقيقي.\n"
            "{q0}.\n"
            "{q1}.\n"
            "احكيلنا شو اللي مثقل قلبك، بنصلي معك ونتابع معك.\nلقراءة أوسع عن الرجاء: ar.thegospelcoalition.org"
        ),
        [("PSA", 23, 1, None), ("ISA", 41, 10, None)],
    ),
]


def build_topic_answer(entry):
    _keywords, template, refs = entry
    quotes = {}
    for i, (code, ch, v1, v2) in enumerate(refs):
        q = quote_verse(code, ch, v1, v2)
        quotes[f"q{i}"] = q if q else f"({_display(code, ch, v1, v2)})"
    return template.format(**quotes)


def detect_topic(lowered_text):
    for entry in TOPIC_ANSWERS:
        if any(k in lowered_text for k in entry[0]):
            return entry
    return None


# ---------------------------------------------------------------- helpers
def graph_post(path, payload):
    if not PAGE_ACCESS_TOKEN:
        app.logger.error("PAGE_ACCESS_TOKEN is not set")
        return None
    try:
        r = requests.post(
            f"{GRAPH}/{path}",
            params={"access_token": PAGE_ACCESS_TOKEN},
            json=payload,
            timeout=20,
        )
        if r.status_code >= 400:
            app.logger.error("Graph API %s: %s", r.status_code, r.text[:500])
        return r
    except requests.RequestException as e:
        app.logger.error("Graph API error: %s", e)
        return None


def send_text(recipient_id, text, with_quick_replies=False):
    """Send text, split into Messenger-sized chunks."""
    chunks = [text[i : i + 1900] for i in range(0, len(text), 1900)] or [""]
    for i, chunk in enumerate(chunks):
        payload = {
            "recipient": {"id": recipient_id},
            "messaging_type": "RESPONSE",
            "message": {"text": chunk},
        }
        if with_quick_replies and i == len(chunks) - 1:
            payload["message"]["quick_replies"] = QUICK_REPLIES
        graph_post("me/messages", payload)


def fixed_answer(payload):
    if payload == "SERVICE_TIME":
        return service_time_text()
    if payload == "ADDRESS":
        return address_text()
    if payload == "PRAYER_REQUEST":
        q = quote_verse("PHP", 4, 6, 7)
        base = (
            "يسعدنا نصلي لأجلك. اكتب طلبة الصلاة هون بكلماتك، "
            "وسنرفعها في صلواتنا. الرب يسمع ويستجيب."
        )
        return base + (f"\n{q}." if q else "")
    return FIXED_ANSWERS.get(payload)


import re

_BIBLE_BOOKS = (
    "تكوين|خروج|لاويين|عدد|تثنية|يشوع|قضاة|راعوث|صموئيل|ملوك|اخبار|أخبار|عزرا|"
    "نحميا|استير|أستير|ايوب|أيوب|مزمور|المزامير|امثال|أمثال|جامعة|نشيد|اشعياء|إشعياء|"
    "ارميا|إرميا|مراثي|حزقيال|دانيال|هوشع|يوئيل|عاموس|عوبديا|يونان|ميخا|ناحوم|"
    "حبقوق|صفنيا|حجي|زكريا|ملاخي|متى|مرقس|لوقا|يوحنا|اعمال|أعمال|رومية|كورنثوس|"
    "غلاطية|افسس|أفسس|فيلبي|كولوسي|تسالونيكي|تيموثاوس|تيطس|فليمون|عبرانيين|"
    "يعقوب|بطرس|يهوذا|رؤيا"
)
_REF_RE = re.compile(rf"(?:{_BIBLE_BOOKS})\s*\d+\s*[:：]\s*\d+(?:\s*-\s*\d+)?")
_QUOTE_RE = re.compile(r"«([^»]{20,})»")


def groq_answer_is_safe(answer):
    """Block any Groq answer that cites an unverified reference or
    presents a quoted text that is not one of the verified verses.
    This guard exists because the model previously invented verses."""
    compact_allowed = {a.replace(" ", "") for a in ALLOWED_REFS}
    for m in _REF_RE.finditer(answer):
        ref = m.group(0).replace(" ", "").replace("：", ":")
        if ref not in compact_allowed:
            return False
    verified_compact = {v.replace(" ", "") for v in VERIFIED_VERSES.values()}
    for m in _QUOTE_RE.finditer(answer):
        if m.group(1).replace(" ", "") not in verified_compact:
            return False
    return True


def ask_groq(sender_id, user_text):
    # v2 default: Groq never answers faith/Bible questions freely.
    if not ALLOW_GROQ or not GROQ_KEY:
        return safe_handoff()
    history = HISTORY.get(sender_id, [])
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history[-MAX_HISTORY:]
    messages.append({"role": "user", "content": user_text})
    try:
        r = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 400,
            },
            timeout=30,
        )
        r.raise_for_status()
        answer = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:  # network / quota / bad key -> safe hand-off
        app.logger.error("Groq error: %s", e)
        return safe_handoff()
    if not groq_answer_is_safe(answer):
        app.logger.error("Blocked unverified Groq answer: %s", answer[:300])
        return safe_handoff()
    history = history + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": answer},
    ]
    HISTORY[sender_id] = history[-MAX_HISTORY:]
    return answer


def handle_payload(sender_id, payload):
    if payload in ("GET_STARTED", "WELCOME"):
        send_text(sender_id, WELCOME, with_quick_replies=True)
        return
    answer = fixed_answer(payload)
    if answer:
        send_text(sender_id, answer, with_quick_replies=True)
    else:
        send_text(sender_id, WELCOME, with_quick_replies=True)


def handle_message(sender_id, message):
    payload = (message.get("quick_reply") or {}).get("payload")
    if payload:
        handle_payload(sender_id, payload)
        return
    text = (message.get("text") or "").strip()
    if not text:
        send_text(sender_id, "أهلا فيك. ابعتلنا رسالتك كتابة وسنساعدك.", with_quick_replies=True)
        return
    lowered = text.lower()
    # 1) Greetings get the welcome, not an AI answer.
    if lowered.strip(" .!؟?") in ("مرحبا", "مرحبًا", "سلام", "هلا", "اهلا", "أهلا", "hello", "hi", "hey", "shalom"):
        send_text(sender_id, WELCOME, with_quick_replies=True)
        return
    # 2) Explicit verse reference -> exact text from eBible arb-vd.
    parsed = parse_reference(text)
    if parsed:
        answer = verse_request_answer(text, parsed)
        if answer:
            send_text(sender_id, answer, with_quick_replies=True)
            return
        send_text(
            sender_id,
            "طلبت آية بس ما قدرت أوصل لنصها من موقع الكتاب هاللحظة، "
            "وما رح أكتبها من عندي عشان ما تطلع غلط. تأكد من الشاهد وجرّب بعد شوي، "
            "أو ابعت سؤالك وفريق الكنيسة بيتابع معك.",
            with_quick_replies=True,
        )
        return
    # 3) Curated faith topics — verses fetched from eBible, never Groq.
    topic = detect_topic(lowered)
    if topic:
        send_text(sender_id, build_topic_answer(topic), with_quick_replies=True)
        return
    # 4) Church info shortcuts.
    if any(k in lowered for k in ("موعد", "متى", "الساعة", "اجتماع", "service", "time", "when")):
        send_text(sender_id, service_time_text(), with_quick_replies=True)
        return
    if any(k in lowered for k in ("عنوان", "وين", "مكان", "address", "where", "location")):
        send_text(sender_id, address_text(), with_quick_replies=True)
        return
    if any(k in lowered for k in ("صلاة", "صلي", "صلّي", "pray", "prayer", "طلبة")):
        # v2: a prayer request is acknowledged here only. It is visible
        # to the church team in the Page inbox; no AI reply follows it.
        send_text(sender_id, fixed_answer("PRAYER_REQUEST"), with_quick_replies=True)
        return
    # 5) Anything else: safe hand-off (or strictly guarded Groq if enabled).
    send_text(sender_id, ask_groq(sender_id, text), with_quick_replies=True)


# ---------------------------------------------------------------- routes
@app.get("/")
def home():
    return {
        "status": "ok",
        "bot": CHURCH_NAME_EN,
        "page_id": PAGE_ID,
        "groq_configured": bool(GROQ_KEY),
        "groq_enabled": ALLOW_GROQ,
        "answer_mode": "curated+groq-guarded" if ALLOW_GROQ else "curated-only",
        "comments_enabled": COMMENTS_ENABLED,
        "verse_source": EBIBLE_BASE,
        "verse_mode": "ebible-live-with-local-fallback",
        "answer_sources": [
            "https://ebible.org/arb-vd (verse texts, Van Dyck)",
            "https://www.baptistarabic.org (Baptist beliefs)",
            "https://ar.thegospelcoalition.org (gospel & Christian life)",
        ],
        "page_token_configured": bool(PAGE_ACCESS_TOKEN),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ------------------------------------------------- public legal pages
# Meta App Review / Live mode require a public Privacy Policy URL and
# Data Deletion instructions. Serving them from the bot itself means
# Hanna needs no separate website: once the bot is on Render, the URLs
# are simply  <render-url>/privacy  and  <render-url>/data-deletion .

_PRIVACY_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Privacy Policy — Bible Baptist Church–Jerusalem Messenger Bot</title>
</head><body style="font-family:sans-serif;max-width:42em;margin:2em auto;line-height:1.6">
<h1>Privacy Policy — Bible Baptist Church–Jerusalem Messenger Bot</h1>
<p><i>Effective: 16 October 2026</i></p>
<p>This policy covers the Messenger bot on our Facebook Page,
<strong>Bible Baptist Church-Jerusalem</strong> (Page ID: 100080177692918),
run by Bible Baptist Church–Jerusalem.</p>
<ul>
<li>This bot replies to messages sent to our Facebook Page.</li>
<li>We process the text of messages you send us only to answer you.
Conversation context is held in server memory temporarily and is not
stored in a database, sold, or shared with advertisers.</li>
<li>Prayer requests you type are visible to our church team in the Page
inbox so we can pray for you and follow up if you ask us to.</li>
<li>You can stop using the bot at any time by not messaging the Page,
and you can ask us through the Page to delete a conversation
(see <a href="/data-deletion">data deletion instructions</a>).</li>
<li>Contact: through the Facebook Page inbox.</li>
</ul>
<h2 dir="rtl" lang="ar">سياسة الخصوصية — بوت ماسنجر كنيسة الكتاب المقدس المعمدانية – القدس</h2>
<div dir="rtl" lang="ar">
<ul>
<li>هذا البوت يرد على الرسائل المرسلة إلى صفحة الكنيسة على فيسبوك.</li>
<li>نعالج نص الرسائل التي ترسلها إلينا فقط لكي نجيبك. يُحفظ سياق المحادثة
في ذاكرة الخادم مؤقتًا، ولا يُخزَّن في قاعدة بيانات، ولا يُباع ولا
يُشارك مع المعلنين.</li>
<li>طلبات الصلاة التي تكتبها تظهر لفريق الكنيسة في صندوق وارد الصفحة
لكي نصلي لأجلك ونتابع معك إذا طلبت ذلك.</li>
<li>يمكنك التوقف عن استخدام البوت في أي وقت بعدم مراسلة الصفحة، ويمكنك
أن تطلب منا عبر الصفحة حذف محادثتك.</li>
<li>للتواصل: عبر صندوق وارد صفحة الفيسبوك.</li>
</ul>
</div>
</body></html>"""

_DELETION_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Data Deletion — Bible Baptist Church–Jerusalem Messenger Bot</title>
</head><body style="font-family:sans-serif;max-width:42em;margin:2em auto;line-height:1.6">
<h1>Data Deletion Instructions</h1>
<p>The Messenger bot of <strong>Bible Baptist Church-Jerusalem</strong>
does not keep a database of user data. Conversation context exists only
in server memory during a chat and is cleared when the server restarts.</p>
<p>To have a conversation removed from the Page inbox, send our Facebook
Page a message saying <i>"Please delete my conversation"</i>
(Arabic: «احذفوا محادثتي»). Our church team will delete the conversation
from the Page inbox, normally within 7 days, and confirm to you in the Page.</p>
<p>لا يحتفظ بوت كنيسة الكتاب المقدس المعمدانية – القدس بأي قاعدة بيانات
للمستخدمين. لحذف محادثتك من صندوق وارد الصفحة، أرسل إلى صفحتنا رسالة
تقول «احذفوا محادثتي»، وسيحذفها فريق الكنيسة عادة خلال ٧ أيام ويؤكد لك
ذلك عبر الصفحة.</p>
</body></html>"""


@app.get("/privacy")
def privacy():
    return _PRIVACY_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.get("/data-deletion")
def data_deletion():
    return _DELETION_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.get("/webhook")
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge", "")
    # The verify token is a handshake word, not a password. Compare
    # case-insensitively and trimmed (2026-10-17): a capitalised first
    # letter typed in Render vs lowercase in Facebook caused repeated
    # "Verification token mismatch" failures for Hanna; this ends that.
    if mode == "subscribe" and token.strip().lower() == VERIFY_TOKEN.strip().lower():
        return challenge, 200
    return "Verification token mismatch", 403


# ------------------------------------------------------- comment replies
_seen_comments = set()
_seen_comments_order = []


def _remember_comment(comment_id):
    if comment_id in _seen_comments:
        return False
    _seen_comments.add(comment_id)
    _seen_comments_order.append(comment_id)
    if len(_seen_comments_order) > 500:
        old = _seen_comments_order.pop(0)
        _seen_comments.discard(old)
    return True


def _looks_like_question(text):
    if "؟" in text or "?" in text:
        return True
    starters = ("كيف", "ليش", "لماذا", "وين", "أين", "متى", "شو", "هل ",
                "ممكن", "بدي أعرف", "مين هو", "من هو")
    t = (text or "").strip()
    return any(t.startswith(s) or (" " + s) in t[:40] for s in starters)


def _comment_reply_for(text):
    """Answer for a public comment, or None to stay silent.
    Mirrors the Messenger flow (verse reference -> curated topic ->
    church info); an unmatched question gets a short, warm pointer to
    Messenger instead of an invented answer."""
    ans = None
    parsed = parse_reference(text)
    if parsed:
        ans = verse_request_answer(text, parsed)
    if not ans:
        topic = detect_topic(text.lower())
        if topic:
            ans = build_topic_answer(topic)
    if not ans:
        lowered = text.lower()
        if any(k in lowered for k in ("موعد", "متى", "الساعة", "اجتماع", "service", "time", "when")):
            ans = service_time_text()
        elif any(k in lowered for k in ("عنوان", "وين الكنيسة", "مكان الكنيسة", "address", "location")):
            ans = address_text()
    if ans:
        if len(ans) > 950:
            ans = ans[:945].rstrip() + "…\n(الجواب كامل على الماسنجر، ابعتلنا رسالة.)"
        return ans
    if _looks_like_question(text):
        return (
            "شكرًا لسؤالك! يسعدنا نجاوبك بالتفصيل — ابعتلنا سؤالك برسالة "
            "على الماسنجر من زر «إرسال رسالة» بصفحة الكنيسة، وسنرد عليك. "
            "«تَعَالَوْا إِلَيَّ يَا جَمِيعَ الْمُتْعَبِينَ» (متى 11: 28)."
        )
    return None


def reply_to_comment(comment_id, text):
    if not PAGE_ACCESS_TOKEN:
        return
    try:
        requests.post(
            f"{GRAPH}/{comment_id}/comments",
            data={"message": text, "access_token": PAGE_ACCESS_TOKEN},
            timeout=20,
        )
    except requests.RequestException:
        pass


def handle_feed_change(change):
    if not COMMENTS_ENABLED or change.get("field") != "feed":
        return
    v = change.get("value") or {}
    if v.get("item") != "comment" or v.get("verb") != "add":
        return
    if str(v.get("sender_id", "")) == PAGE_ID:
        return  # never reply to the Page's own comments (loop guard)
    comment_id = v.get("comment_id")
    text = (v.get("message") or "").strip()
    if not comment_id or not text:
        return
    if not _remember_comment(comment_id):
        return
    reply = _comment_reply_for(text)
    if reply:
        reply_to_comment(comment_id, reply)


@app.post("/webhook")
def webhook():
    if APP_SECRET:
        signature = request.headers.get("X-Hub-Signature-256", "")
        digest = hmac.new(
            APP_SECRET.encode(), request.get_data(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(f"sha256={digest}", signature):
            abort(403)
    data = request.get_json(silent=True) or {}
    if data.get("object") != "page":
        return "OK", 200
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            handle_feed_change(change)
        for event in entry.get("messaging", []):
            sender_id = (event.get("sender") or {}).get("id")
            if not sender_id:
                continue
            if "postback" in event:
                handle_payload(sender_id, event["postback"].get("payload", ""))
            elif "message" in event and not event["message"].get("is_echo"):
                handle_message(sender_id, event["message"])
    return "OK", 200


@app.get("/setup")
def setup():
    """Activate greeting, Get Started button and the persistent menu."""
    if not PAGE_ACCESS_TOKEN:
        return {
            "ok": False,
            "error": "PAGE_ACCESS_TOKEN is not set yet. Add it in Render > Environment, then open /setup again.",
        }, 400
    profile = {
        "greeting": [
            {
                "locale": "default",
                "text": "أهلا وسهلا فيك باسم يسوع، {{user_first_name}}! نحن "
                + CHURCH_NAME_AR
                + ".",
            }
        ],
        "get_started": {"payload": "GET_STARTED"},
        "persistent_menu": [
            {
                "locale": "default",
                "composer_input_disabled": False,
                "call_to_actions": [
                    {"type": "postback", "title": "عن الكنيسة", "payload": "ABOUT_CHURCH"},
                    {"type": "postback", "title": "موعد الاجتماع", "payload": "SERVICE_TIME"},
                    {"type": "postback", "title": "العنوان / كيف أوصل", "payload": "ADDRESS"},
                    {"type": "postback", "title": "أجي مع عيلتي؟", "payload": "WITH_FAMILY"},
                    {"type": "postback", "title": "طلب صلاة", "payload": "PRAYER_REQUEST"},
                ],
            }
        ],
    }
    r = graph_post("me/messenger_profile", profile)
    if r is not None and r.status_code < 400:
        msg = "✅ تم تفعيل القائمة الاحترافية ورسالة الترحيب بنجاح لصفحة " + CHURCH_NAME_AR
        # Also subscribe the app to the Page for messages AND post
        # comments (feed), so comment questions reach the bot too.
        try:
            s = requests.post(
                f"{GRAPH}/{PAGE_ID}/subscribed_apps",
                params={"access_token": PAGE_ACCESS_TOKEN},
                data={"subscribed_fields": "messages,messaging_postbacks,feed"},
                timeout=20,
            )
            if s.status_code < 400:
                msg += "\n✅ تم الاشتراك بحدث التعليقات (feed) كمان — البوت رح يجاوب على أسئلة الكومنتات."
            else:
                msg += "\n(تنبيه: اشتراك التعليقات ما تم تلقائيًا — فعّل حدث feed من إعدادات Webhooks بالتطبيق.)"
        except requests.RequestException:
            msg += "\n(تنبيه: اشتراك التعليقات ما تم تلقائيًا — فعّل حدث feed من إعدادات Webhooks بالتطبيق.)"
        return msg
    return {
        "ok": False,
        "error": "Facebook rejected the setup. Check that PAGE_ACCESS_TOKEN belongs to the church page and the app has Messenger permission.",
        "details": (r.text[:500] if r is not None else "no response"),
    }, 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
