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
<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box}body{margin:0;font-family:'Tajawal',Tahoma;background:#070a12;color:#e2e8f0;min-height:100vh}
.header{height:72px;background:#0f172a;border-bottom:1px solid #1e293b;display:flex;align-items:center;justify-content:center;position:sticky;top:0}
.header h1{margin:0;font-size:16px;color:#fff;letter-spacing:.3px}
.container{display:flex;align-items:center;justify-content:center;padding:40px 20px;min-height:calc(100vh - 72px)}
.card{width:100%;max-width:480px;background:#10182c;border:1px solid #1e293b;border-radius:20px;padding:40px 32px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.4)}
.icon{width:52px;height:52px;background:#fbbf24;border-radius:14px;display:flex;align-items:center;justify-content:center;margin:0 auto 18px;color:#000;font-size:22px;font-weight:800}
.card h2{margin:0 0 6px;font-size:23px;color:#fff}
.sub{color:#94a3b8;font-size:13px;margin-bottom:24px}
.divider{height:1px;background:#1e293b;margin:24px 0}
.welcome{color:#fbbf24;font-size:15px;font-weight:700;margin-bottom:10px}
.topics{color:#64748b;font-size:12.5px;line-height:1.6}
</style></head><body>
<div class="header"><h1>كنيسة الكتاب المقدس المعمدانية - القدس</h1></div>
<div class="container">
<div class="card">
<div class="icon">✦</div>
<h2>مرحباً بكم</h2>
<div class="sub">Bible Baptist Church Jerusalem</div>
<div class="divider"></div>
<div class="welcome">نرحب بأسئلتكم الكتابية 🙏</div>
<div class="topics">اسأل عن: الخلاص، المعمودية، الكتاب المقدس، الثالوث، الاختطاف</div>
</div>
</div>
</body></html>
"""

def get_bible_answer(t):
    s=t.lower()
    if any(k in s for k in ["خلاص","اخلص","salvation","saved"]): return 'الخلاص بالنعمة بالإيمان وحده\nرومية 10:9 "إن اعترفت بفمك بالرب يسوع وآمنت بقلبك أن الله أقامه من الأموات خلصت"\nActs 4:12 KJV: Neither is there salvation in any other'
    if any(k in s for k in ["أمن","امان","أبدي","security"]): return 'أمن أبدي - يوحنا 10:28 وأنا أعطيها حياة أبدية ولن تهلك إلى الأبد\nJohn 10:28 KJV: they shall never perish'
    if any(k in s for k in ["معمودية","تغطيس","baptism"]): return 'المعمودية بالتغطيس بعد الخلاص رمز فقط\nأعمال 2:41 واعتمدوا\nMatthew 28:19 KJV baptizing them'
    if any(k in s for k in ["كتاب","kjv","فاندايك"]): return 'فاندايك و KJV فقط محفوظ\nمزمور 12:6 كلام الرب نقي\nPsalm 12:6 KJV pure words'
    if any(k in s for k in ["ثالوث","trinity"]): return 'ثالوث: آب وابن وروح قدس إله واحد\n1 يوحنا 5:7 ثلاثة يشهدون في السماء\n1 John 5:7 KJV'
    if any(k in s for k in ["سما","جحيم","hell","heaven"]): return 'السما للمخلصين والجحيم للهالكين\nيوحنا 3:36 الذي يؤمن له حياة أبدية'
    if any(k in s for k in ["اختطاف","مجيء","rapture"]): return 'الاختطاف قريب\n1 تسالونيكي 4:16 الرب نفسه ينزل وسنخطف في السحب\n1 Thess 4:16 KJV'
    return f'سؤالك: "{t}"\nأقدر أجاوبك على: الخلاص، الأمن الأبدي، المعمودية، KJV فاندايك، الثالوث، السما والجحيم، الاختطاف\nآية: أعمال 4:12 وليس بأحد غيره الخلاص'

@app.after_request
def no_cache(r): r.headers["Cache-Control"]="no-store, no-cache"; return r
@app.route('/')
@app.route('/tab')
def tab(): return render_template_string(TAB_HTML)
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get('hub.verify_token')==VERIFY_TOKEN: return request.args.get('hub.challenge'),200
    return "fail",403
@app.route('/webhook', methods=['POST'])
def hook():
    data=request.get_json()
    if not data or data.get('object')!='page': return "ok",200
    for entry in data.get('entry',[]):
        for ev in entry.get('messaging',[]):
            sid=ev.get('sender',{}).get('id'); txt=ev.get('message',{}).get('text','')
            if not sid or sid==PAGE_ID or not txt: continue
            ans=get_bible_answer(txt)
            try: requests.post("https://graph.facebook.com/v21.0/me/messages",params={"access_token":PAGE_ACCESS_TOKEN},json={"recipient":{"id":sid},"message":{"text":ans[:1900]}})
            except: pass
    return "ok",200
