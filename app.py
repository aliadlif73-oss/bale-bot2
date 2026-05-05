from flask import Flask, request
import json
from datetime import datetime

app = Flask(__name__)

TOKEN = "توکن_ربات_بله_تو"

API_URL = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"

# ====== دیتای اولیه ======
supervisors = [
    "سعید زمانیان",
    "مرتضی سالاریه",
    "عباس یاقوتی"
]

# ====== وضعیت کاربران ======
user_states = {}

# ====== ارسال پیام ======
def send_message(chat_id, text, keyboard=None):
    import requests

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = json.dumps({
            "keyboard": keyboard,
            "resize_keyboard": True
        })

    requests.post(API_URL, data=payload)

# ====== ذخیره دیتا ======
def save_data(data):
    with open("data.json", "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

# ====== webhook ======
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    try:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
    except:
        return "ok"

    if chat_id not in user_states:
        user_states[chat_id] = {"step": "start", "data": {}}

    state = user_states[chat_id]

    # ====== شروع ======
    if text == "/start":
        state["step"] = "choose_supervisor"

        keyboard = [[s] for s in supervisors]

        send_message(chat_id, "سرپرست خود را انتخاب کنید:", keyboard)
        return "ok"

    # ====== انتخاب سرپرست ======
    if state["step"] == "choose_supervisor":
        state["data"]["supervisor"] = text
        state["step"] = "choose_type"

        keyboard = [
            ["📉 گزارش خرید نکرده"],
            ["🎯 گزارش پک"]
        ]

        send_message(chat_id, "نوع گزارش را انتخاب کنید:", keyboard)
        return "ok"

    # ====== انتخاب نوع ======
    if state["step"] == "choose_type":

        # ===== خرید نکرده =====
        if "خرید نکرده" in text:
            state["data"]["type"] = "no_buy"
            state["step"] = "ask_customer"

            send_message(chat_id, "کد مشتری را وارد کنید:")
            return "ok"

        # ===== پک =====
        if "پک" in text:
            state["data"]["type"] = "pack"
            state["step"] = "pack_15"

            keyboard = [[str(i) for i in range(0, 11)]]

            send_message(chat_id, "تعداد پک ۱۵ میلیونی:", keyboard)
            return "ok"

    # ====== فلو خرید نکرده ======
    if state["data"].get("type") == "no_buy":

        # کد مشتری
        if state["step"] == "ask_customer":
            state["data"]["customer"] = text
            state["step"] = "ask_result"

            keyboard = [
                ["خرید کرد"],
                ["نیاز به پیگیری"],
                ["خرید نکرد"]
            ]

            send_message(chat_id, "نتیجه ویزیت:", keyboard)
            return "ok"

        # نتیجه
        if state["step"] == "ask_result":
            state["data"]["result"] = text

            if text == "خرید کرد":
                state["step"] = "ask_amount"
                send_message(chat_id, "مبلغ خرید:")
                return "ok"

            elif "پیگیری" in text:
                state["step"] = "ask_followup"
                send_message(chat_id, "کی برای پیگیری مراجعه می‌کنید؟")
                return "ok"

            elif "نکرد" in text:
                state["step"] = "ask_reason"
                send_message(chat_id, "علت خرید نکردن چیست؟")
                return "ok"

        # مبلغ
        if state["step"] == "ask_amount":
            state["data"]["amount"] = text
            return finish(chat_id, state)

        # علت
        if state["step"] == "ask_reason":
            state["data"]["reason"] = text
            return finish(chat_id, state)

        # پیگیری
        if state["step"] == "ask_followup":
            state["data"]["followup"] = text
            return finish(chat_id, state)

    # ====== فلو پک ======
    if state["data"].get("type") == "pack":

        if state["step"] == "pack_15":
            state["data"]["pack_15"] = text
            state["step"] = "pack_45"
            send_message(chat_id, "تعداد پک ۴۵ میلیونی:", [[str(i) for i in range(0,11)]])
            return "ok"

        if state["step"] == "pack_45":
            state["data"]["pack_45"] = text
            state["step"] = "pack_75"
            send_message(chat_id, "تعداد پک ۷۵ میلیونی:", [[str(i) for i in range(0,11)]])
            return "ok"

        if state["step"] == "pack_75":
            state["data"]["pack_75"] = text
            state["step"] = "pack_150"
            send_message(chat_id, "تعداد پک ۱۵۰ میلیونی:", [[str(i) for i in range(0,11)]])
            return "ok"

        if state["step"] == "pack_150":
            state["data"]["pack_150"] = text
            state["step"] = "pack_150_plus"
            send_message(chat_id, "تعداد پک بالای ۱۵۰ میلیونی:", [[str(i) for i in range(0,11)]])
            return "ok"

        if state["step"] == "pack_150_plus":
            state["data"]["pack_150_plus"] = text
            return finish(chat_id, state)

    return "ok"


# ====== پایان ======
def finish(chat_id, state):
    state["data"]["time"] = str(datetime.now())

    save_data(state["data"])

    keyboard = [["ثبت پایگاه بعدی"]]

    send_message(chat_id, "گزارش ثبت شد ✅", keyboard)

    state["step"] = "choose_supervisor"
    state["data"] = {}

    return "ok"


# ====== اجرا ======
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)