from flask import Flask, request, render_template_string
import os, requests

app = Flask(__name__)
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "baptist2026")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID", "1360210040674355")

TAB_HTML = """
<!DOCTYPE html><html dir="rtl" lang="ar"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bible Baptist Church Jerusalem</title>
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box}body{margin:0;font-family:'Tajawal',Tahoma;background:#070a12;color:#e2e8f0;min-height:100vh}
.header{height:72px;background:#0f172a;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:center}
.header h1{margin:0;font-size:17px;color:#fff}
.container{display:flex;align-items:center;justify-content:center;padding:40px 20px;min-height:calc(100vh - 72px)}
.card{width:100%;max-width:480px;background:#10182c;border:1px solid #1e293b;border-radius:20px;padding:48px 32px;text-align:center}
.icon{width:48px;height:48px;background:#fbbf24;border-radius:12px;display:flex;align-items:center;justify-content:center;margin:0 auto 20px;color:#000;font-weight:700}
</style></head><body>
<div class="header"><h1>كنيسة الكتاب المقدس المعمدانية - القدس</h1></div>
<div class="container"><div class="card"><div class="icon">✦</div><h2>مرحباً بكم</h2><p style="color:#94a3b8;font-size:14px">Bible Baptist Church Jerusalem</p></div></div>
</body></html>
"""

def get_bible_answer(t):
    s = t.lower()

    if any(k in s for k in ["خلاص","اخلص","salvation","saved","خلصت"]):
        return "الخلاص بالنعمة بالإيمان وحده\nرومية 10:9 فاندايك: لأنك إن اعترفت بفمك بالرب يسوع وآمنت بقلبك أن الله أقامه من الأموات خلصت\nActs 4:12 KJV: Neither is there salvation in any other"

    if any(k in s for k in ["أمن","امان","ضمان","security","أبدي"]):
        return "المؤمن عنده أمن أبدي لا يهلك\nيوحنا 10:28 فاندايك: وأنا أعطيها حياة أبدية ولن تهلك إلى الأبد\nJohn 10:28 KJV: And I give unto them eternal life; and they shall never perish"

    if any(k in s for k in ["معمودية","تغطيس","baptism"]):
        return "المعمودية بالتغطيس بعد الخلاص رمز فقط وليست للخلاص\nأعمال 2:41 قبلوا كلامه واعتمدوا\nMatthew 28:19 KJV: baptizing them"

    if any(k in s for k in ["كنيسة","church"]):
        return "الكنيسة جماعة مؤمنين معمدين مستقلة\nمتى 16:18 فاندايك: على هذه الصخرة أبني كنيستي"

    if any(k in s for k in ["كتاب","kjv","فاندايك","ترجمة"]):
        return "نؤمن بالكتاب المحفوظ فاندايك و KJV فقط\nمزمور 12:6 كلام الرب كلام نقي\nPsalm 12:6 KJV: The words of the LORD are pure words"

    if any(k in s for k in ["ثالوث","trinity","اقانيم"]):
        return "ثالوث واحد: آب وابن وروح قدس\n1 يوحنا 5:7 فاندايك: فإن الذين يشهدون في السماء هم ثلاثة: الآب والكلمة والروح القدس وهؤلاء الثلاثة هم واحد\n1 John 5:7 KJV"

    if any(k in s for k in ["روح قدس","holy spirit","الروح"]):
        return "الروح القدس هو الله، يسكن في المؤمن لحظة الخلاص\nأفسس 1:13 ختمتم بروح الموعد القدوس\nEph 1:13 KJV: sealed with that holy Spirit"

    if any(k in s for k in ["سما","جحيم","hell","heaven","نار"]):
        return "السما للمخلصين، الجحيم للهالكين\nيوحنا 3:36 الذي يؤمن بالابن له حياة أبدية والذي لا يؤمن لن يرى حياة بل يمكث عليه غضب الله\nJohn 3:36 KJV"

    if any(k in s for k in ["مجيء","اختطاف","rapture","مجيء ثاني"]):
        return "الرب سيأتي ويختطف الكنيسة\n1 تسالونيكي 4:16-17 الرب نفسه بهتاف... سنخطف جميعا في السحب\n1 Thess 4:16 KJV"

    if any(k in s for k in ["صلاة","prayer","اصلي"]):
        return "الصلاة باسم يسوع\nيوحنا 14:14 إن سألتم شيئا باسمي فإني أفعله\nJohn 14:14 KJV: If ye shall ask any thing in my name, I will do it"

    if any(k in s for k in ["خطية","ذنب","sin"]):
        return "الجميع أخطأوا\nرومية 3:23 إذ الجميع أخطأوا وأعوزهم مجد الله\nRomans 3:23 KJV: For all have sinned"

    if any(k in s for k in ["توبة","repent"]):
        return "التوبة هي تغيير الفكر والرجوع للرب\nأعمال 20:21 شاهدا... بالتوبة إلى الله والإيمان بربنا يسوع المسيح\nActs 20:21 KJV"

    if any(k in s for k in ["عطاء","giving","عشور"]):
        return "العطاء بسرور وليس فريضة\n2 كورنثوس 9:7 كل واحد كما ينوي بقلبه ليس عن حزن أو اضطرار لأن المعطي المسرور يحبه الله\n2 Cor 9:7 KJV"

    if any(k in s for k in ["مريم","عذراء","mary"]):
        return "مريم مباركة لكنها ليست وسيطة، الوسيط واحد هو المسيح\n1 تيموثاوس 2:5 لأنه يوجد إله واحد ووسيط واحد بين الله والناس الإنسان يسوع المسيح\n1 Tim 2:5 KJV"

    # أي سؤال تاني
    return f"""سؤالك: "{t}"

أقدر أجاوبك على: الخلاص، الأمن الأبدي، المعمودية، الكنيسة، الكتاب KJV فاندايك، الثالوث، الروح القدس، السما والجحيم، الاختطاف، الصلاة، الخطية، التوبة، العطاء.

اسأل بكلمة واحدة مثلا: خلاص، معمودية، ثالوث

آية: أعمال 4:12 وليس بأحد غيره الخلاص
Acts 4:12 KJV Neither is there salvation in any other"""

@app.after_request
def no_cache(r):
    r.headers["Cache-Control"]="no-store, no-cache"; return r

@app.route('/')
@app.route('/tab')
def tab(): return render_template_string(TAB_HTML)

@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get('hub.verify_token')==VERIFY_TOKEN:
        return request.args.get('hub.challenge'),200
    return "fail",403

@app.route('/webhook', methods=['POST'])
def hook():
    data=request.get_json()
    if not data or data.get('object')!='page': return "ok",200
    for entry in data.get('entry',[]):
        for ev in entry.get('messaging',[]):
            sid=ev.get('sender',{}).get('id')
            txt=ev.get('message',{}).get('text','')
            if not sid or sid==PAGE_ID or not txt: continue
            ans=get_bible_answer(txt)
            try:
                requests.post("https://graph.facebook.com/v21.0/me/messages",
                    params={"access_token":PAGE_ACCESS_TOKEN},
                    json={"recipient":{"id":sid},"message":{"text":ans[:1900]}})
            except: pass
    return "ok",200
