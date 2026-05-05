from flask import Flask, request
import json
import requests
from datetime import datetime

app = Flask(__name__)

TOKEN = "1956867539:Qpq0riwmj0FemRdVwB60QRDGpgDz8txxLmU"
API_URL = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"

user_states = {}

supervisors = [
    "سعید زمانیان",
    "مرتضی سالاریه",
    "عباس یاقوتی"
]

def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True
        }

    requests.post(API_URL, json=payload)


def save_data(data):
    with open("data.json", "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


@app.route('/', methods=['GET'])
def home():
    return "Bot is running"


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    print(data)  # برای لاگ

    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    if chat_id not in user_states:
        user_states[chat_id] = {"step": "start", "data": {}}

    state = user_states[chat_id]

    # START
    if text == "/start":
        state["step"] = "choose_supervisor"

        keyboard = [[s] for s in supervisors]

        send_message(chat_id, "سرپرست را انتخاب کن:", keyboard)
        return "ok"

    # انتخاب سرپرست
    if state["step"] == "choose_supervisor":
        state["data"]["supervisor"] = text
        state["step"] = "choose_type"

        keyboard = [
            ["گزارش خرید نکرده"],
            ["گزارش پک"]
        ]

        send_message(chat_id, "نوع گزارش:", keyboard)
        return "ok"

    # انتخاب نوع
    if state["step"] == "choose_type":

        if "خرید نکرده" in text:
            state["data"]["type"] = "no_buy"
            state["step"] = "customer"

            send_message(chat_id, "کد مشتری را وارد کن:")
            return "ok"

        if "پک" in text:
            state["data"]["type"] = "pack"
            state["step"] = "pack15"

            send_message(chat_id, "تعداد پک ۱۵ میلیونی (۰ تا ۱۰):")
            return "ok"

    # خرید نکرده
    if state["data"].get("type") == "no_buy":

        if state["step"] == "customer":
            state["data"]["customer"] = text
            state["step"] = "result"

            keyboard = [
                ["خرید کرد"],
                ["نیاز به پیگیری"],
                ["خرید نکرد"]
            ]

            send_message(chat_id, "نتیجه:", keyboard)
            return "ok"

        if state["step"] == "result":
            state["data"]["result"] = text

            if text == "خرید کرد":
                state["step"] = "amount"
                send_message(chat_id, "مبلغ:")
                return "ok"

            if "پیگیری" in text:
                state["step"] = "follow"
                send_message(chat_id, "زمان پیگیری:")
                return "ok"

            if "نکرد" in text:
                state["step"] = "reason"
                send_message(chat_id, "علت:")
                return "ok"

        if state["step"] == "amount":
            state["data"]["amount"] = text
            return finish(chat_id, state)

        if state["step"] == "follow":
            state["data"]["follow"] = text
            return finish(chat_id, state)

        if state["step"] == "reason":
            state["data"]["reason"] = text
            return finish(chat_id, state)

    # پک
    if state["data"].get("type") == "pack":

        if state["step"] == "pack15":
            state["data"]["p15"] = text
            state["step"] = "pack45"
            send_message(chat_id, "پک ۴۵:")
            return "ok"

        if state["step"] == "pack45":
            state["data"]["p45"] = text
            state["step"] = "pack75"
            send_message(chat_id, "پک ۷۵:")
            return "ok"

        if state["step"] == "pack75":
            state["data"]["p75"] = text
            state["step"] = "pack150"
            send_message(chat_id, "پک ۱۵۰:")
            return "ok"

        if state["step"] == "pack150":
            state["data"]["p150"] = text
            state["step"] = "packplus"
            send_message(chat_id, "پک بالای ۱۵۰:")
            return "ok"

        if state["step"] == "packplus":
            state["data"]["pplus"] = text
            return finish(chat_id, state)

    return "ok"


def finish(chat_id, state):
    state["data"]["time"] = str(datetime.now())
    save_data(state["data"])

    send_message(chat_id, "ثبت شد ✅\nثبت پایگاه بعدی؟", [["بله"]])

    state["step"] = "choose_supervisor"
    state["data"] = {}

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
