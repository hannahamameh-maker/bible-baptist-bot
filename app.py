from flask import Flask, request
import os
import requests
import re

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "baptist2026")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID", "1360210040674355")

def detect_language(text):
    # Check for Arabic characters
    if re.search(r'[\u0600-\u06FF]', text):
        return 'ar'
    # Check for Hebrew characters
    if re.search(r'[\u0590-\u05FF]', text):
        return 'he'
    return 'en'

def get_reply(user_text, lang, is_comment=False):
    if lang == 'ar':
        if is_comment:
            return f"الرب يباركك! شكراً لتعليقك: '{user_text}' - الكنيسة المعمدانية الكتابية في القدس تحبك! 🙏"
        else:
            return f"الرب يباركك! قلت: {user_text}\n\nأهلاً وسهلاً بك في الكنيسة المعمدانية الكتابية - القدس. كيف يمكننا مساعدتك؟ 🙏\n\nللمزيد: biblebaptistjerusalem.org"
    elif lang == 'he':
        if is_comment:
            return f"אלוהים יברך אותך! תודה על התגובה: '{user_text}' - הכנסייה הבפטיסטית בירושלים אוהבת אותך! 🙏"
        else:
            return f"אלוהים יברך אותך! אמרת: {user_text}\n\nברוכים הבאים לכנסייה הבפטיסטית התנ\"כית - ירושלים. איך נוכל לעזור? 🙏"
    else: # English
        if is_comment:
            return f"God bless you! Thank you for your comment: '{user_text}' - Bible Baptist Church Jerusalem loves you! 🙏"
        else:
            return f"God bless you! You said: {user_text}\n\nWelcome to Bible Baptist Church - Jerusalem. How can we help you? 🙏\n\nMore: biblebaptistjerusalem.org"

@app.route('/')
def home():
    return {
        "page_id": PAGE_ID,
        "status": "Bible Baptist Church Jerusalem Bot Running - Arabic/English/Hebrew + Comments",
        "languages": "ar, en, he",
        "time": "live"
    }

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print("WEBHOOK VERIFIED")
        return challenge, 200
    else:
        return "Verification failed", 403

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    data = request.get_json()
    print(f"Received webhook: {data}")
    
    if data['object'] == 'page':
        for entry in data['entry']:
            # 1. PRIVATE MESSAGES
            if 'messaging' in entry:
                for messaging_event in entry['messaging']:
                    if 'message' in messaging_event:
                        sender_id = messaging_event['sender']['id']
                        if sender_id == PAGE_ID:
                            continue
                        message_text = messaging_event['message'].get('text', '')
                        if message_text:
                            lang = detect_language(message_text)
                            reply = get_reply(message_text, lang, is_comment=False)
                            send_private_message(sender_id, reply)

            # 2. PUBLIC COMMENTS
            if 'changes' in entry:
                for change in entry['changes']:
                    if change['field'] == 'feed':
                        value = change['value']
                        if value.get('item') == 'comment' and value.get('verb') == 'add':
                            comment_id = value.get('comment_id')
                            from_id = value.get('from', {}).get('id')
                            message = value.get('message', '')
                            if from_id == PAGE_ID or not comment_id or not message:
                                continue
                            print(f"New comment ({detect_language(message)}): {message} ID: {comment_id}")
                            lang = detect_language(message)
                            reply = get_reply(message, lang, is_comment=True)
                            reply_to_comment(comment_id, reply)
    return "ok", 200

def send_private_message(recipient_id, message_text):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    r = requests.post("https://graph.facebook.com/v21.0/me/messages", params=params, headers=headers, json=data)
    print(f"Send DM Status: {r.status_code} - {r.text}")

def reply_to_comment(comment_id, message_text):
    url = f"https://graph.facebook.com/v21.0/{comment_id}/comments"
    params = {"access_token": PAGE_ACCESS_TOKEN, "message": message_text}
    r = requests.post(url, params=params)
    print(f"Reply to comment Status: {r.status_code} - {r.text}")
    return r.json()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
