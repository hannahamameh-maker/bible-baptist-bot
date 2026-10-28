'use strict';
const translations = {
  ar: {church:'كنيسة الكتاب المقدس المعمدانية – القدس',location:'بيت حنينا · القدس',eyebrow:'مساحة لأسئلتك',title:'عندك سؤال\nمن الكتاب المقدس؟',intro:'ابدأ بسؤالك، أو اطلب آية. ويسعدنا كمان نعرّفك على الكنيسة ومواعيد اجتماعاتنا.',identity:'كنيسة معمدانية مستقلة',assistant:'مساعد الكنيسة',assistantSub:'محادثة آلية مستقلة',clear:'محادثة جديدة',welcome:'أهلًا وسهلًا فيك. شو بتحب تسأل اليوم؟',welcomeNote:'الآيات تُجلب من eBible: فان دايك بالعربي وKJV بالإنجليزي. وإذا ما عندي جواب موثّق، بوضّح لك.',jesus:'من هو يسوع؟',verse:'اقرأ يوحنا ٣:١٦',schedule:'مواعيد الاجتماعات',inputLabel:'اكتب سؤالك الخاص هنا',note:'هذا مساعد آلي؛ المحادثة لا تُرسَل لفريق الكنيسة. للتواصل الشخصي استخدم الرابط المنفصل.',visitKicker:'أهلًا فيك بيننا',visitTitle:'تعرّف على الكنيسة',visitText:'وقت للعبادة، ودراسة كلمة الله، والصلاة معًا.',address:'العنوان والخريطة',meeting:'شو بصير بالاجتماع؟',family:'بقدر أجي مع عيلتي؟',about:'عن الكنيسة',contactTitle:'حابب تحكي مع شخص؟',contactText:'للمتابعة مع فريق الكنيسة أو مشاركة طلبة صلاة، ابعتلنا رسالة مباشرة.',contactButton:'تواصل مع الكنيسة',contactNote:'يفتح مسنجر · المتابعة من فريق الكنيسة',privacy:'خصوصية المحادثة',thinking:'عم بجهّز الجواب…',slow:'الخدمة عم تستجيب ببطء؛ ممكن تحتاج شوي وقت لتشتغل.',error:'تعذّر الاتصال. سؤالك ما ضاع؛ جرّب مرة ثانية.',rate:'وصلت للحد المؤقت من الأسئلة. انتظر دقيقة وجرّب مجددًا.',retry:'إعادة المحاولة',send:'إرسال السؤال',placeholder:'اكتب سؤالك، ثم اضغط إرسال…',reading:'قراءة إضافية',source:'المصدر',manual:'تواصل مع فريق الكنيسة',ourAddress:'عنوان الكنيسة',openMap:'افتح Google Maps ↗',examples:'هذه أمثلة للبداية؛ تقدر تكتب سؤالك الخاص بالمربع تحت.',sendShort:'إرسال',newWelcome:'بدأت محادثة جديدة. اكتب سؤالك بالمربع تحت.'},
  en: {church:'Bible Baptist Church – Jerusalem',location:'Beit Hanina · Jerusalem',eyebrow:'A place for your questions',title:'A question\nabout the Bible?',intro:'Ask a question, request a verse, or find out about our church and meeting times.',identity:'An Independent Baptist church',assistant:'Church assistant',assistantSub:'Independent automated chat',clear:'New conversation',welcome:'Welcome. What would you like to ask today?',welcomeNote:'Scripture is retrieved from eBible: Arabic Van Dyck and English KJV. If I do not have a verified answer, I will say so.',jesus:'Who is Jesus?',verse:'Read John 3:16',schedule:'Meeting times',inputLabel:'Write your own question here',note:'This is an automated assistant. Messages are not sent to church staff; use the separate link for personal contact.',visitKicker:'You are welcome here',visitTitle:'Meet our church',visitText:'Worship, study God’s Word, and pray together.',address:'Address & map',meeting:'What happens at a meeting?',family:'Can I bring my family?',about:'About the church',contactTitle:'Want to talk to a person?',contactText:'For personal follow-up or a prayer request, contact the church team directly.',contactButton:'Contact the church',contactNote:'Opens Messenger · Church staff follow-up',privacy:'Chat privacy',thinking:'Preparing your answer…',slow:'The service is taking a little longer to respond. It may be starting up.',error:'Could not connect. Your question is still here; please try again.',rate:'You have reached the temporary question limit. Please wait one minute.',retry:'Try again',send:'Send question',placeholder:'Type your question, then press Send…',reading:'Further reading',source:'Source',manual:'Contact the church team',ourAddress:'Church address',openMap:'Open Google Maps ↗',examples:'These are starting examples. Write your own question in the box below.',sendShort:'Send',newWelcome:'A new conversation is ready. Write your question in the box below.'}
};
let lang = 'ar', busy = false, previousTopic = null, activeController = null, generation = 0;
const messages = document.getElementById('messages');
const input = document.getElementById('question');
const form = document.getElementById('chat-form');
const sendButton = document.getElementById('send');
const initialWelcome = document.getElementById('welcome').cloneNode(true);
function local(key) { return translations[lang][key] || key; }
function setLanguage(next) {
  lang = next;
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  document.querySelectorAll('[data-i18n]').forEach(node => { node.textContent = local(node.dataset.i18n); if (node.dataset.i18n === 'title') node.style.whiteSpace = 'pre-line'; });
  document.getElementById('language').textContent = lang === 'ar' ? 'English ↗' : 'العربية ↗';
  document.getElementById('language').setAttribute('aria-label', lang === 'ar' ? 'Switch to English' : 'التبديل للعربية');
  messages.setAttribute('aria-label', lang === 'ar' ? 'المحادثة' : 'Conversation');
  input.placeholder = local('placeholder');
  sendButton.setAttribute('aria-label', local('send'));
}
function scrollDown() { messages.scrollTop = messages.scrollHeight; }
function messageNode(kind, text) {
  const article = document.createElement('article');
  article.className = 'message ' + kind;
  article.dir = 'auto';
  const p = document.createElement('p');
  p.textContent = text;
  article.append(p);
  messages.append(article);
  scrollDown();
  return article;
}
function safeLink(title, url) {
  try {
    const address = new URL(url);
    if (address.protocol !== 'https:') return null;
    const a = document.createElement('a');
    a.href = address.href; a.textContent = title; a.target = '_blank'; a.rel = 'noopener noreferrer';
    return a;
  } catch (_) { return null; }
}
function renderAnswer(data) {
  const article = messageNode('assistant', data.answer);
  for (const verse of data.verses || []) {
    const block = document.createElement('blockquote'); block.className = 'verse'; block.dir = 'auto';
    const p = document.createElement('p'); p.textContent = verse.text; block.append(p);
    const ref = document.createElement('span'); ref.className = 'verse-reference';
    ref.textContent = verse.reference + (verse.translation ? ' · ' + verse.translation : ''); block.append(ref);
    if (verse.note) { const small = document.createElement('span'); small.className = 'verse-note'; small.textContent = verse.note; block.append(small); }
    article.append(block);
  }
  if (data.sources?.length) {
    const links = document.createElement('div'); links.className = 'sources';
    for (const source of data.sources) {
      const a = safeLink((source.kind === 'further_reading' ? local('reading') : local('source')) + ' · ' + source.title, source.url);
      if (a) links.append(a);
    }
    article.append(links);
  }
  if (['unknown','prayer_request'].includes(data.topic)) {
    const links = document.createElement('div'); links.className = 'sources';
    const a = safeLink(local('manual'), data.contact); if (a) links.append(a); article.append(links);
  }
  previousTopic = data.topic || previousTopic;
  scrollDown();
}
function setBusy(value) {
  busy = value; sendButton.disabled = value; input.disabled = value;
  document.querySelectorAll('[data-action],[data-question]').forEach(b => { b.disabled = value; });
}
async function ask(text, action = null, retry = false) {
  if (busy || !text.trim()) return;
  const requestGeneration = ++generation;
  setBusy(true);
  if (!retry) messageNode('user', text);
  input.value = ''; input.style.height = 'auto';
  const pending = messageNode('assistant thinking', local('thinking')); pending.setAttribute('role','status');
  const controller = new AbortController();
  activeController = controller;
  const timeout = setTimeout(() => controller.abort(), 85000);
  const slow = setTimeout(() => { if (pending.isConnected) pending.firstChild.textContent = local('slow'); }, 12000);
  // English questions receive KJV even when the surrounding interface is Arabic.
  const answerLanguage = !action && /[a-z]/i.test(text) && !/[\u0600-\u06ff]/.test(text) ? 'en' : lang;
  try {
    const response = await fetch('/api/chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,action,lang:answerLanguage,previous_topic:previousTopic}),signal:controller.signal});
    if (!response.ok) throw new Error(response.status === 429 ? 'rate' : 'error');
    const data = await response.json();
    if (requestGeneration !== generation) return;
    if (typeof data.answer !== 'string') throw new Error('error');
    pending.remove(); renderAnswer(data);
  } catch (error) {
    if (requestGeneration !== generation) return;
    pending.remove();
    const box = messageNode('assistant error', local(error.message === 'rate' ? 'rate' : 'error'));
    const button = document.createElement('button'); button.type = 'button'; button.className = 'retry'; button.textContent = local('retry');
    button.addEventListener('click', () => { if (!busy) { box.remove(); ask(text,action,true); } }); box.append(button);
    scrollDown();
  } finally {
    clearTimeout(timeout); clearTimeout(slow);
    if (requestGeneration === generation) { activeController = null; setBusy(false); }
  }
}
form.addEventListener('submit', e => { e.preventDefault(); ask(input.value.trim()); });
input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); form.requestSubmit(); } });
input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight,130) + 'px'; });
document.addEventListener('click', e => {
  const button = e.target.closest('[data-action],[data-question]');
  if (!button || busy) return;
  const action = button.dataset.action || null;
  const text = button.dataset.question ? (lang === 'en' ? button.dataset.questionEn : button.dataset.question) : button.textContent.trim();
  ask(text,action);
});
document.getElementById('language').addEventListener('click', () => setLanguage(lang === 'ar' ? 'en' : 'ar'));
document.getElementById('clear').addEventListener('click', () => {
  ++generation;
  activeController?.abort(); activeController = null; setBusy(false);
  previousTopic = null;
  const welcome = initialWelcome.cloneNode(true);
  welcome.querySelector('[data-i18n=welcome]').dataset.i18n = 'newWelcome';
  messages.replaceChildren(welcome);
  input.value = ''; input.style.height = 'auto'; setLanguage(lang); messages.scrollTop = 0;
  input.focus({preventScroll:true});
  form.scrollIntoView({block:'center',behavior:'smooth'});
});
