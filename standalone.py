"""Independent chat. The language model can select an approved answer ID only.

Model-written prose and verses are NEVER returned to visitors. Scripture blocks
are assembled on the server from eBible's Van Dyck or KJV chapter HTML.
"""
import hashlib
import json
import os
import re
import threading
import time
from collections import OrderedDict, deque
from html.parser import HTMLParser
from urllib.parse import urlsplit

import requests
from flask import jsonify, render_template, request

BOOK_NAMES = "Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|Ezra|Nehemiah|Esther|Job|Psalms|Proverbs|Ecclesiastes|Song of Solomon|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|1 Corinthians|2 Corinthians|Galatians|Ephesians|Philippians|Colossians|1 Thessalonians|2 Thessalonians|1 Timothy|2 Timothy|Titus|Philemon|Hebrews|James|1 Peter|2 Peter|1 John|2 John|3 John|Jude|Revelation".split("|")
TOPIC_NAMES = ["baptism", "communion", "eternal_security", "works", "intercession", "bible_authority", "trinity", "baptists", "prayer", "salvation", "jesus", "love", "anxiety", "rest", "hope"]
EN_ANSWERS = [
    "Believer's baptism is immersion after personal faith in Christ. It publicly pictures the believer's death and resurrection with Christ. It is an act of obedience, not a means of salvation.",
    "The Lord's Supper remembers Christ's death until He comes. In our Baptist understanding, the bread and cup symbolize His body and blood; they do not become them. Believers participate with prayer and self-examination.",
    "Our Baptist understanding is that God preserves those who are truly born again through faith in Christ. This assurance encourages holiness and gratitude, not permission to continue in sin.",
    "Salvation is by grace through faith in Christ, not earned by good works. Good works are the fruit of living faith, not the cause of salvation.",
    "We honor Mary's faith and the believers described in Scripture. Prayer and worship belong to God, and Jesus Christ alone is the mediator between God and people. We confess our sins to God through Him.",
    "The Bible is God's inspired Word and our written authority for faith and practice. We test human teaching and tradition by Scripture and encourage you to read it for yourself.",
    "We believe in one eternal God: Father, Son, and Holy Spirit, equal in divine nature. They are not three gods, or one person changing roles.",
    "Our church is Independent Baptist. We hold to the authority of Scripture, salvation by grace through faith, believer's baptism by immersion, the priesthood of believers, and the independence of the local church. Baptism and the Lord's Supper are our two ordinances.",
    "Prayer is speaking honestly to God. Thank Him, bring your needs to Him, and pray in Jesus' name. To share a prayer request with the church, use the separate contact link; this chat does not deliver messages to the church team.",
    "Salvation is God's gift of grace, received through repentance and faith in Jesus Christ, who died for our sins and rose again. It is not earned through good works, baptism, or church membership.",
    "Jesus Christ is the Son of God. He died on the cross for our sins and rose from the dead. Through Him we receive forgiveness and eternal life.",
    "God has demonstrated His love by sending His Son. His invitation to trust Christ is open to you.",
    "God knows what you are facing. Bring your worries to Him in prayer. If you would like a person from the church to pray with you, open the separate contact link.",
    "Jesus invites those who are weary and burdened to come to Him. Bring your burdens to Him in prayer. You are welcome to visit the church.",
    "There is hope in God even in difficult times. If you need to talk with someone at the church, use the separate contact link.",
]


class VerseHTML(HTMLParser):
    """Retain scripture text, excluding verse numbers, notes and navigation."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.verses = {}
        self.current = None
        self.marker = False
        self.skip_tag = None
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = a.get("class", "").split()
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth += 1
            return
        if tag in ("script", "style", "ul", "footer") or any(c in classes for c in ("footnote", "footnotes", "tnav", "copyright")):
            self.skip_tag, self.skip_depth = tag, 1
            self.current = None
            return
        if tag == "a":
            self.skip_tag, self.skip_depth = tag, 1
            return
        if tag == "span" and "verse" in classes:
            m = re.fullmatch(r"V(\d+)", a.get("id", ""))
            self.current = int(m[1]) if m and int(m[1]) > 0 else None
            if self.current:
                self.verses[self.current] = []
            self.marker = True
        elif tag in ("div", "p", "br") and self.current and not self.marker:
            self.verses[self.current].append(" ")

    def handle_endtag(self, tag):
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_depth -= 1
                if self.skip_depth == 0:
                    self.skip_tag = None
            return
        if tag == "span" and self.marker:
            self.marker = False

    def handle_data(self, data):
        if self.current and not self.marker and not self.skip_tag:
            self.verses[self.current].append(data)

    def result(self):
        return {n: re.sub(r"\s+", " ", "".join(parts)).strip().lstrip("¶ ")
                for n, parts in self.verses.items() if "".join(parts).strip()}


_chapter_cache = OrderedDict()
_lock = threading.Lock()
_limits = OrderedDict()


def chapter_text(code, chapter, lang):
    key = (code, chapter, lang)
    with _lock:
        cached = _chapter_cache.get(key)
        if cached:
            _chapter_cache.move_to_end(key)
            return cached
    edition = "eng-kjv" if lang == "en" else "arb-vd"
    url = f"https://ebible.org/{edition}/{code}{chapter:0{3 if code == 'PSA' else 2}d}.htm"
    r = requests.get(url, timeout=(10, 15))
    r.raise_for_status()
    parser = VerseHTML()
    parser.feed(r.content.decode("utf-8-sig"))
    result = parser.result()
    if not result:
        raise ValueError("Scripture source did not contain verse markers")
    with _lock:
        _chapter_cache[key] = (result, url)
        if len(_chapter_cache) > 128:
            _chapter_cache.popitem(last=False)
    return result, url


def allowed_request(ip):
    """Single Render worker, bounded in-memory limits; no message persistence."""
    now = time.monotonic()
    key = hashlib.sha256(ip.encode()).hexdigest()
    with _lock:
        for bucket, maximum in ((key, 20), ("global", 160)):
            hits = _limits.setdefault(bucket, deque())
            while hits and hits[0] < now - 60:
                hits.popleft()
            if len(hits) >= maximum:
                return False
        _limits[key].append(now)
        _limits["global"].append(now)
        _limits.move_to_end(key)
        if len(_limits) > 4000:
            # Always retain the global bucket.
            oldest = next(k for k in _limits if k != "global")
            del _limits[oldest]
    return True


def install_web_chat(app, b):
    app.config["MAX_CONTENT_LENGTH"] = 16384
    public_url = os.environ.get("PUBLIC_URL", "https://bible-baptist-bot.onrender.com").rstrip("/")
    english_names = dict(zip((x[0] for x in b.BOOKS), BOOK_NAMES))
    variants = [(b._norm_ar(name.lower()), code) for code, name, aliases in b.BOOKS for name in [name, *aliases]]
    variants += [(name.lower(), code) for code, name in english_names.items()]
    variants += [("psalm", "PSA"), ("song of songs", "SNG")]
    variants.sort(key=lambda pair: len(pair[0]), reverse=True)

    def parse_ref(text):
        norm = b._norm_ar(b._norm_digits(text).lower()).replace("ٱ", "ا")
        for alias, code in variants:
            m = re.search(rf"(?<!\w){re.escape(alias)}\s*(\d{{1,3}})(?:\s*[:：]\s*(\d{{1,3}})(?:\s*[-–]\s*(\d{{1,3}}))?)?(?!\d)", norm)
            if m:
                ch, start, end = int(m[1]), int(m[2] or 0), int(m[3] or m[2] or 0)
                if not (1 <= ch <= 150) or (m[2] is not None and start < 1) or end < start or end > 176:
                    return None
                return code, ch, start or None, end or None
        return None

    def verse_blocks(refs, lang):
        blocks, sources = [], []
        for code, ch, first, last in refs:
            name = english_names[code] if lang == "en" else b._CANON[code]
            label = f"{name} {ch}" + (f":{first}" if first else "")
            last = last or first
            if first and last != first:
                label += f"–{min(last, first + 4)}"
            try:
                verses, url = chapter_text(code, ch, lang)
                numbers = list(range(first, min(last, first + 4) + 1)) if first else sorted(verses)[:5]
                if not numbers or any(n not in verses for n in numbers):
                    raise ValueError("Reference not present in chapter")
                content = " ".join(verses[n] for n in numbers)
                if len(content) > 6000:
                    raise ValueError("Verse range too long")
                blocks.append({"reference": label, "text": content, "translation": "KJV" if lang == "en" else "فان دايك", "url": url})
                if not first or (last - first > 4):
                    blocks[-1]["note"] = "First five verses at most; open the source for the full passage." if lang == "en" else "نعرض حتى أول خمس آيات؛ افتح المصدر لقراءة النص كاملًا."
                sources.append({"title": f"eBible · {label}", "url": url})
            except (requests.RequestException, ValueError, UnicodeError):
                blocks.append({"reference": label, "unavailable": True, "text": "I could not retrieve this passage. No verse text has been generated." if lang == "en" else "تعذّر جلب هذا النص من eBible. لم نكتب نص الآية من عندنا."})
        return blocks, sources

    def normalized(text):
        return b._norm_ar(text.lower()).replace("ٱ", "ا")

    def choose_topic(text, previous_topic=None):
        norm = normalized(text)
        # Never interpret a theological when/where question as church details.
        church = bool(re.search(r"كنيس|اجتماع|عباد|درس الكتاب|\b(church|service|meeting|bible study)\b", norm))
        if re.fullmatch(r"(موعد الاجتماع|مواعيد الاجتماعات|العنوان|طلب صلاه|عن الكنيسه)", norm):
            church = True
        if church and any(k in norm for k in ("موعد", "مواعيد", "متي", "ساع", "امتي", "when", "time", "schedule")):
            return "schedule"
        if norm == "العنوان" or (church and any(k in norm for k in ("عنوان", "وين", "اين", "مكان", "where", "address", "location"))):
            return "address"
        if church and any(k in norm for k in ("عيل", "عائل", "اطفال", "family", "children")):
            return "family"
        if church and any(k in norm for k in ("شو بصير", "ماذا يحدث", "what happens", "what to expect")):
            return "meeting"
        if norm in ("عن الكنيسه", "about the church", "about church"):
            return "about"
        if any(k in norm for k in ("طلب صلاه", "صلوا لاجلي", "صلي لاجلي", "prayer request", "pray for me")):
            return "prayer_request"
        if any(k in norm for k in ("مين هو يسوع", "من هو يسوع", "مين يسوع", "who is jesus")):
            return "jesus"
        for i, (keywords, template, refs) in enumerate(b.TOPIC_ANSWERS):
            for keyword in keywords:
                key = normalized(keyword)
                if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", norm):
                    return TOPIC_NAMES[i]
        # Groq only selects an ID. It never supplies visitor-visible text.
        if os.environ.get("WEB_AI_ENABLED", "1") == "1" and b.GROQ_KEY:
            labels = TOPIC_NAMES + ["schedule", "address", "family", "meeting", "about", "prayer_request", "unknown"]
            r = None
            try:
                payload = {
                    "model": b.GROQ_MODEL,
                    "messages": [{"role": "system", "content": "Classify a church visitor's question. Return ONLY JSON {\"topic\":\"ID\"}. Choose one ID from " + json.dumps(labels) + ". Use church schedule/address ONLY when explicitly asking about THIS church. Never map Bible events or people to church information. If no category answers the actual question choose unknown. Previous topic (optional context only): " + str(previous_topic)}, {"role": "user", "content": text}],
                    "temperature": 0, "max_completion_tokens": 1024,
                    "response_format": {"type": "json_object"},
                }
                if b.GROQ_MODEL in ("openai/gpt-oss-20b", "openai/gpt-oss-120b"):
                    # Reasoning tokens count toward the budget. A 50-token cap
                    # can exhaust it before the final JSON object is produced.
                    payload["reasoning_effort"] = "low"
                    payload["response_format"] = {"type": "json_schema", "json_schema": {
                        "name": "church_topic", "strict": True, "schema": {
                            "type": "object", "properties": {"topic": {"type": "string", "enum": labels}},
                            "required": ["topic"], "additionalProperties": False,
                        },
                    }}
                r = requests.post(b.GROQ_URL, headers={"Authorization": f"Bearer {b.GROQ_KEY}"}, json=payload, timeout=(4, 12))
                r.raise_for_status()
                choice = json.loads(r.json()["choices"][0]["message"]["content"]).get("topic")
                if choice in labels:
                    # Hard boundary against church-info misclassification.
                    if choice in ("schedule", "address", "family", "meeting", "about") and not church:
                        return "unknown"
                    return choice
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as error:
                # Log diagnostic metadata only: no question, key or model text.
                app.logger.warning("Web question classification unavailable: %s HTTP=%s", type(error).__name__, r.status_code if r is not None else "none")
        return "unknown"

    def make_answer(text, lang, action=None, previous_topic=None):
        output = {"answer": "", "verses": [], "sources": [], "topic": None, "contact": f"https://m.me/{b.PAGE_ID}"}
        if action == "verse":
            text = "John 3:16" if lang == "en" else "يوحنا 3:16"
        ref = parse_ref(text)
        if ref and not action:
            output["verses"], output["sources"] = verse_blocks([ref], lang)
            output["answer"] = "Scripture from eBible; translation: KJV." if lang == "en" else "نص الكتاب المقدس من eBible، ترجمة فان دايك."
            if any(k in normalized(text) for k in ("شرح", "تفسير", "معني", "explain", "meaning")):
                output["answer"] += " For interpretation, please contact the church." if lang == "en" else " لتفسير النص بدقة، تواصل مع الكنيسة من الرابط المنفصل."
            return output
        if not action and normalized(text).strip(" .!؟?") in ("مرحبا", "سلام", "هلا", "اهلا", "hello", "hi"):
            output["answer"] = "Welcome. Ask a Bible question, request a verse, or choose church information below." if lang == "en" else "أهلًا وسهلًا فيك. اسأل عن الكتاب المقدس، اطلب آية بالشاهد، أو اختَر مواعيد الاجتماعات والعنوان."
            return output
        topic = action if action in ("schedule", "address", "about", "family", "meeting", "prayer_request", "verse") else choose_topic(text, previous_topic)
        if topic == "verse":
            output["verses"], output["sources"] = verse_blocks([parse_ref(text)], lang)
            output["answer"] = "From eBible · KJV" if lang == "en" else "من eBible · فان دايك"
            return output
        output["topic"] = topic
        if topic in TOPIC_NAMES:
            i = TOPIC_NAMES.index(topic)
            keywords, template, refs = b.TOPIC_ANSWERS[i]
            # Preserve existing Arabic explanations, separating scripture into
            # source-only blocks and removing misleading inbox promises.
            explanation = re.sub(r"\{q\d+\}", "", template)
            explanation = re.sub(r"لقراءة[^\n]*", "", explanation)
            explanation = explanation.replace("اكتب طلبتك هون وبنصلي لأجلك ككنيسة", "تواصل مع الكنيسة من الرابط المنفصل لمشاركة طلبة صلاة")
            explanation = explanation.replace("ابعتلنا", "تواصل مع الكنيسة").replace("احكيلنا هون", "تواصل مع الكنيسة من الرابط المنفصل")
            output["answer"] = EN_ANSWERS[i] if lang == "en" else re.sub(r"\n\s*\n", "\n", explanation).strip()
            output["verses"], output["sources"] = verse_blocks(refs, lang)
            if "baptistarabic.org" in template:
                output["sources"].append({"title": "قراءة إضافية · معتقدات المعمدانيين", "url": "https://www.baptistarabic.org/", "kind": "further_reading"})
            if "ar.thegospelcoalition.org" in template:
                output["sources"].append({"title": "قراءة إضافية · ائتلاف الإنجيل", "url": "https://ar.thegospelcoalition.org/", "kind": "further_reading"})
        elif topic == "schedule":
            output["answer"] = b.service_time_text()
            if lang == "en":
                if b.SERVICE_TIME == b.DEFAULT_SERVICE_TIME:
                    output["answer"] = "Sunday at 10:30 a.m. — Worship service\nThursday at 6:00 p.m. — Bible study and prayer\nThe doors open fifteen minutes before the meeting. You are welcome to join us."
                else:
                    output["answer"] = "Our church meeting schedule (as provided by the church):\n" + b.service_time_text()
        elif topic == "address":
            output["answer"] = b.address_text()
            if lang == "en" and b.ADDRESS == "شارع اسكندر الخوري 6، بيت حنينا، القدس":
                output["answer"] = "6 Iskandar al-Khouri Street, Beit Hanina, Jerusalem. Open the map below for directions."
            output["sources"] = [{"title": "Google Maps", "url": b.MAPS_URL}] if b.MAPS_URL.startswith("https://") else []
        elif topic == "prayer_request":
            output["answer"] = "You can share a prayer request with the church through the separate contact link. This chat does not deliver messages to the church team." if lang == "en" else "يسعد فريق الكنيسة يصلّي لأجلك. لمشاركة طلبة الصلاة، افتح رابط التواصل مع الكنيسة. هذه المحادثة مستقلة ولا ترسل طلبتك إلى الفريق تلقائيًا."
        elif topic in ("about", "family", "meeting"):
            output["answer"] = b.FIXED_ANSWERS[{"about": "ABOUT_CHURCH", "family": "WITH_FAMILY", "meeting": "WHAT_HAPPENS"}[topic]]
            if lang == "en":
                output["answer"] = {
                    "about": "Welcome to Bible Baptist Church – Jerusalem, an Independent Baptist church. We worship Jesus Christ, study God's Word, and pray together. You are welcome to visit with your questions.",
                    "family": "Yes, you and your family are welcome. There is time to get acquainted after worship.",
                    "meeting": "Our meeting includes singing and worship, a message from the Bible, and prayer. It lasts about an hour, followed by time to meet one another. You are welcome to visit without any obligation.",
                }[topic]
        elif normalized(text).strip(" .!؟?") in ("مرحبا", "سلام", "هلا", "اهلا", "hello", "hi"):
            output["answer"] = "Welcome. Ask a Bible question, request a verse, or choose church information below." if lang == "en" else "أهلًا وسهلًا فيك. اسأل عن الكتاب المقدس، اطلب آية بالشاهد، أو اختَر مواعيد الاجتماعات والعنوان."
        else:
            output["answer"] = "I do not have a verified answer to this question in the current library. You can contact the church through the separate link. Your question has not been sent to the church." if lang == "en" else "ما عندي جواب موثّق لهذا السؤال ضمن مكتبة الأجوبة الحالية. تقدر تتواصل مع الكنيسة من الرابط المنفصل لمتابعته. سؤالك لم يُرسَل إلى فريق الكنيسة تلقائيًا."
        return output

    @app.get("/")
    def chat_page():
        return render_template("chat.html", public_url=public_url, church=b.CHURCH_NAME_AR, page_id=b.PAGE_ID)

    @app.post("/api/chat")
    def web_chat():
        origin = request.headers.get("Origin")
        if origin and urlsplit(origin).netloc not in (urlsplit(public_url).netloc, request.host):
            return jsonify(error="origin_not_allowed"), 403
        if not request.is_json:
            return jsonify(error="json_required"), 415
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify(error="invalid_request"), 400
        text, action, lang = data.get("message", ""), data.get("action"), data.get("lang", "ar")
        if not isinstance(text, str) or not text.strip() or len(text) > 1500 or lang not in ("ar", "en"):
            return jsonify(error="invalid_message"), 400
        if action is not None and action not in ("schedule", "address", "about", "family", "meeting", "prayer_request", "verse"):
            return jsonify(error="invalid_action"), 400
        ip = request.remote_addr or "unknown"
        # Render terminates HTTPS and sets X-Forwarded-For. Only opt in on a
        # trusted proxy; never trust arbitrary forwarded headers by default.
        if os.environ.get("TRUST_RENDER_PROXY", "0") == "1":
            ip = request.headers.get("X-Forwarded-For", ip).split(",")[-1].strip()
        if not allowed_request(ip):
            return jsonify(error="rate_limit"), 429, {"Retry-After": "60"}
        prev = data.get("previous_topic")
        prev = prev if isinstance(prev, str) and prev in TOPIC_NAMES else None
        # Deliberately do not log visitor questions or model responses.
        result = make_answer(text.strip(), lang, action, prev)
        return jsonify(result)

    @app.after_request
    def chat_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/chat-privacy")
    def chat_privacy():
        return render_template("chat_privacy.html", church=b.CHURCH_NAME_AR, page_id=b.PAGE_ID)

    # Exposed for unit tests without performing HTTP requests to Facebook.
    app.extensions["web_answer"] = make_answer
    app.extensions["web_parse_reference"] = parse_ref
