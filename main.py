import os
import requests
from flask import Flask, request
from akinator.async_akinator import Akinator
import asyncio

app = Flask(__name__)

# المتغيرات البيئية من Render
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

# تخزين جلسات اللعب لكل مستخدم
games = {}

@app.route("/", methods=["GET"])
def home():
    return "Akinator Facebook Bot is active!", 200

# 1. التوثيق والتحقق من Webhook الفيسبوك
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    token_sent = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token_sent == VERIFY_TOKEN:
        return challenge, 200
    return "Verification token mismatch", 403

# 2. استقبال الرسائل ومعالجتها
@app.route("/webhook", methods=["POST"])
def handle_messages():
    data = request.get_json()
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"].get("text", "").strip()
                    
                    if message_text:
                        # تشغيل معالجة الرسالة في الحلقة الزمنية
                        asyncio.run(process_user_message(sender_id, message_text))
                        
    return "EVENT_RECEIVED", 200

async def process_user_message(sender_id, text):
    text_lower = text.lower()

    # بدء لعبة جديدة
    if text_lower in ["ابدأ", "start", "/play", "لعب", "المارد الأزرق"]:
        aki = Akinator()
        try:
            q = await aki.start_game(language='ar')
            games[sender_id] = aki
            msg = f"أهلاً بك مع المارد الأزرق! 🧞‍♂️\n\nفكر في شخصية وسأحاول تخمينها.\n\nالسؤال الأول:\n{q}\n\nأجب بـ: (نعم، لا، لا أعرف، ربما، تميل إلى لا)"
            send_fb_message(sender_id, msg)
        except Exception as e:
            send_fb_message(sender_id, "حدث خطأ أثناء الاتصال بأكيناتور، حاول مرة أخرى أريد كلمة: ابدأ")
        return

    # إذا لم تكن اللعبة بدأت بعد
    if sender_id not in games:
        send_fb_message(sender_id, "أهلاً بك! 🧞‍♂️\nلبدء اللعبة معنا، أرسل كلمة: **ابدأ**")
        return

    aki = games[sender_id]
    
    # خريطة الإجابات
    answer_mapping = {
        'نعم': 'y', 'yes': 'y',
        'لا': 'n', 'no': 'n',
        'لا أعرف': 'id', 'dont know': 'id',
        'ربما': 'p', 'maybe': 'p',
        'تميل إلى لا': 'pn', 'probably not': 'pn'
    }

    if text not in answer_mapping:
        send_fb_message(sender_id, "الرجاء الرد بإحدى الإجابات التالية:\n(نعم، لا، لا أعرف، ربما، تميل إلى لا)")
        return

    ans = answer_mapping[text]

    try:
        if aki.step >= 80 or aki.progression >= 80:
            await aki.check_win()
            if aki.first_guess:
                guess = aki.first_guess
                send_fb_message(sender_id, f"تخميني هو: 🧞‍♂️\n**{guess.get('name')}**\n({guess.get('description')})")
                del games[sender_id]
                return

        q = await aki.answer(ans)
        send_fb_message(sender_id, f"سؤال رقم {aki.step + 1}:\n{q}")

    except Exception:
        try:
            await aki.check_win()
            guess = aki.first_guess
            if guess:
                send_fb_message(sender_id, f"شخصيتك هي: **{guess.get('name')}** 🧞‍♂️")
            else:
                send_fb_message(sender_id, "لم أستطع تخمين الشخصية هذه المرة! أرسل 'ابدأ' للعب مجدداً.")
        except:
            send_fb_message(sender_id, "انتهت اللعبة! أرسل 'ابدأ' للعب مرة أخرى.")
        if sender_id in games:
            del games[sender_id]

def send_fb_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN:
        return
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    headers = {"Content-Type": "application/json"}
    requests.post(url, json=payload, headers=headers)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
