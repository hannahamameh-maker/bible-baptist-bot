from flask import Flask, request
import os
import requests

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "baptist2026")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = os.getenv("PAGE_ID", "1360210040674355")

@app.route('/')
def home():
    return {
        "page_id": PAGE_ID,
        "status": "Bible Baptist Church Jerusalem Bot Running - Messages + Comments",
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
            
            # 1. HANDLE MESSENGER MESSAGES (Private Inbox)
            if 'messaging' in entry:
                for messaging_event in entry['messaging']:
                    if 'message' in messaging_event:
                        sender_id = messaging_event['sender']['id']
                        # Don't reply to page itself
                        if sender_id == PAGE_ID:
                            continue
                        message_text = messaging_event['message'].get('text', '')
                        if message_text:
                            send_private_message(sender_id, f"God bless you! You said: {message_text}\n\nWelcome to Bible Baptist Church - Jerusalem. How can we help you? 🙏")

            # 2. HANDLE PUBLIC COMMENTS (Feed)
            if 'changes' in entry:
                for change in entry['changes']:
                    if change['field'] == 'feed':
                        value = change['value']
                        # Only reply to comments, not posts, likes, etc.
                        if value.get('item') == 'comment' and value.get('verb') == 'add':
                            comment_id = value.get('comment_id')
                            from_id = value.get('from', {}).get('id')
                            message = value.get('message', '')
                            
                            # Don't reply to our own comments (avoid loop)
                            if from_id == PAGE_ID:
                                continue
                            
                            print(f"New comment: {message} ID: {comment_id}")
                            reply_to_comment(comment_id, f"God bless you! Thank you for your comment: '{message}' - Bible Baptist Church Jerusalem loves you! 🙏")
    
    return "ok", 200

def send_private_message(recipient_id, message_text):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    r = requests.post("https://graph.facebook.com/v21.0/me/messages", params=params, headers=headers, json=data)
    print(f"Send DM Status: {r.status_code} - {r.text}")

def reply_to_comment(comment_id, message_text):
    url = f"https://graph.facebook.com/v21.0/{comment_id}/comments"
    params = {
        "access_token": PAGE_ACCESS_TOKEN,
        "message": message_text
    }
    r = requests.post(url, params=params)
    print(f"Reply to comment Status: {r.status_code} - {r.text}")
    return r.json()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
