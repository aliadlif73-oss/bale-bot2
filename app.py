from flask import Flask, request
import json
import requests
from datetime import datetime
import threading

app = Flask(__name__)

# =========================
# TOKEN
# =========================
TOKEN = "1956867539:Qpq0riwmj0FemRdVwB60QRDGpgDz8txxLmU"

SEND_URL = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"

# =========================
# FILE LOCK
# =========================
file_lock = threading.Lock()

# =========================
# SUPERVISORS
# =========================
supervisors = [
    "حمزه پور",
    "شریفیان",
    "سالاریه",
    "کلانتری",
    "محمدنیا",
    "زمانیان",
    "تقی زاده",
    "ایمانی"
]

# =========================
# USER STATES
# =========================
user_states = {}

# =========================
# HELPERS
# =========================

def now_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def send_message(chat_id, text, keyboard=None, remove_keyboard=False):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if remove_keyboard:
        payload["reply_markup"] = {
            "remove_keyboard": True
        }

    elif keyboard:
        payload["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True
        }

    requests.post(SEND_URL, data={
        "chat_id": payload["chat_id"],
        "text": payload["text"],
        "reply_markup": json.dumps(payload.get("reply_markup", {}), ensure_ascii=False)
    })


def reset_user(chat_id):

    user_states[chat_id] = {
        "step": "choose_supervisor",
        "data": {}
    }

    keyboard = [[s] for s in supervisors]

    keyboard.append(["🔄 شروع مجدد"])

    send_message(
        chat_id,
        "👋 سلام\n\nلطفاً سرپرست خود را انتخاب کنید:",
        keyboard
    )


def save_data(data):

    with file_lock:
        with open("data.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")


def summary_text(data):

    txt = "✅ گزارش با موفقیت ثبت شد\n\n"

    txt += f"👤 سرپرست: {data.get('supervisor','-')}\n"
    txt += f"📋 نوع گزارش: {data.get('type','-')}\n"

    if data.get("type") == "گزارش خرید نکرده":

        txt += f"🏪 کد مشتری: {data.get('customer','-')}\n"
        txt += f"📌 نتیجه: {data.get('result','-')}\n"

        if "amount" in data:
            txt += f"💰 مبلغ خرید: {data.get('amount')}\n"

        if "reason" in data:
            txt += f"❌ علت خرید نکردن: {data.get('reason')}\n"

        if "followup" in data:
            txt += f"📅 زمان پیگیری: {data.get('followup')}\n"

    if data.get("type") == "گزارش پک":

        txt += f"📦 پک ۱۵: {data.get('pack15','0')}\n"
        txt += f"📦 پک ۴۵: {data.get('pack45','0')}\n"
        txt += f"📦 پک ۷۵: {data.get('pack75','0')}\n"
        txt += f"📦 پک ۱۵۰: {data.get('pack150','0')}\n"
        txt += f"📦 بالای ۱۵۰: {data.get('packplus','0')}\n"

    return txt


# =========================
# HOME
# =========================
@app.route("/", methods=["GET"])
def home():
    return "Bale Bot Running"


# =========================
# WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.json

    print(data)

    if "message" not in data:
        return "ok"

    message = data["message"]

    chat_id = message["chat"]["id"]

    text = message.get("text", "").strip()

    # =========================
    # START / RESET
    # =========================
    if text == "/start" or text == "🔄 شروع مجدد":

        reset_user(chat_id)

        return "ok"

    # =========================
    # CREATE STATE
    # =========================
    if chat_id not in user_states:

        reset_user(chat_id)

        return "ok"

    state = user_states[chat_id]

    step = state["step"]

    # =========================
    # CHOOSE SUPERVISOR
    # =========================
    if step == "choose_supervisor":

        if text not in supervisors:

            send_message(
                chat_id,
                "❗ لطفاً فقط یکی از سرپرست‌ها را انتخاب کنید."
            )

            return "ok"

        state["data"]["supervisor"] = text

        state["step"] = "choose_type"

        keyboard = [
            ["📉 گزارش خرید نکرده"],
            ["🎯 گزارش پک"],
            ["🔄 شروع مجدد"]
        ]

        send_message(
            chat_id,
            "✅ سرپرست ثبت شد\n\n📋 نوع گزارش را انتخاب کنید:",
            keyboard
        )

        return "ok"

    # =========================
    # CHOOSE TYPE
    # =========================
    if step == "choose_type":

        if text == "📉 گزارش خرید نکرده":

            state["data"]["type"] = "گزارش خرید نکرده"

            state["step"] = "customer"

            send_message(
                chat_id,
                "🧾 مرحله ۱ از ۳\n\nکد مشتری را وارد کنید:"
            )

            return "ok"

        elif text == "🎯 گزارش پک":

            state["data"]["type"] = "گزارش پک"

            state["step"] = "pack15"

            nums = [[str(i) for i in range(11)]]

            send_message(
                chat_id,
                "📦 مرحله ۱ از ۵\n\nتعداد پک ۱۵ میلیونی:",
                nums
            )

            return "ok"

        else:

            send_message(
                chat_id,
                "❗ لطفاً یکی از گزینه‌ها را انتخاب کنید."
            )

            return "ok"

    # =========================
    # NO BUY FLOW
    # =========================
    if state["data"].get("type") == "گزارش خرید نکرده":

        # CUSTOMER
        if step == "customer":

            state["data"]["customer"] = text

            state["step"] = "result"

            keyboard = [
                ["✅ خرید کرد"],
                ["🔄 نیاز به پیگیری"],
                ["❌ خرید نکرد"],
                ["🔄 شروع مجدد"]
            ]

            send_message(
                chat_id,
                "🧾 مرحله ۲ از ۳\n\nنتیجه ویزیت را انتخاب کنید:",
                keyboard
            )

            return "ok"

        # RESULT
        if step == "result":

            valid_results = [
                "✅ خرید کرد",
                "🔄 نیاز به پیگیری",
                "❌ خرید نکرد"
            ]

            if text not in valid_results:

                send_message(
                    chat_id,
                    "❗ لطفاً فقط یکی از گزینه‌ها را انتخاب کنید."
                )

                return "ok"

            state["data"]["result"] = text

            # BUY
            if text == "✅ خرید کرد":

                state["step"] = "amount"

                send_message(
                    chat_id,
                    "💰 مبلغ خرید را وارد کنید:\n\nمثال: 2500000"
                )

                return "ok"

            # FOLLOWUP
            if text == "🔄 نیاز به پیگیری":

                state["step"] = "followup"

                send_message(
                    chat_id,
                    "📅 چه زمانی برای پیگیری مراجعه می‌کنید؟"
                )

                return "ok"

            # NO BUY
            if text == "❌ خرید نکرد":

                state["step"] = "reason"

                send_message(
                    chat_id,
                    "❌ علت خرید نکردن را وارد کنید:"
                )

                return "ok"

        # AMOUNT
        if step == "amount":

            clean = text.replace(",", "").replace(" ", "")

            if not clean.isdigit():

                send_message(
                    chat_id,
                    "❗ مبلغ باید فقط عدد باشد.\n\nمثال: 2500000"
                )

                return "ok"

            state["data"]["amount"] = clean

            finish(chat_id)

            return "ok"

        # REASON
        if step == "reason":

            state["data"]["reason"] = text

            finish(chat_id)

            return "ok"

        # FOLLOWUP
        if step == "followup":

            state["data"]["followup"] = text

            finish(chat_id)

            return "ok"

    # =========================
    # PACK FLOW
    # =========================
    if state["data"].get("type") == "گزارش پک":

        nums = [str(i) for i in range(11)]

        # PACK 15
        if step == "pack15":

            if text not in nums:

                send_message(
                    chat_id,
                    "❗ فقط عدد بین ۰ تا ۱۰ انتخاب کنید."
                )

                return "ok"

            state["data"]["pack15"] = text

            state["step"] = "pack45"

            keyboard = [nums]

            send_message(
                chat_id,
                "📦 مرحله ۲ از ۵\n\nتعداد پک ۴۵ میلیونی:",
                keyboard
            )

            return "ok"

        # PACK 45
        if step == "pack45":

            if text not in nums:

                send_message(
                    chat_id,
                    "❗ فقط عدد بین ۰ تا ۱۰ انتخاب کنید."
                )

                return "ok"

            state["data"]["pack45"] = text

            state["step"] = "pack75"

            keyboard = [nums]

            send_message(
                chat_id,
                "📦 مرحله ۳ از ۵\n\nتعداد پک ۷۵ میلیونی:",
                keyboard
            )

            return "ok"

        # PACK 75
        if step == "pack75":

            if text not in nums:

                send_message(
                    chat_id,
                    "❗ فقط عدد بین ۰ تا ۱۰ انتخاب کنید."
                )

                return "ok"

            state["data"]["pack75"] = text

            state["step"] = "pack150"

            keyboard = [nums]

            send_message(
                chat_id,
                "📦 مرحله ۴ از ۵\n\nتعداد پک ۱۵۰ میلیونی:",
                keyboard
            )

            return "ok"

        # PACK 150
        if step == "pack150":

            if text not in nums:

                send_message(
                    chat_id,
                    "❗ فقط عدد بین ۰ تا ۱۰ انتخاب کنید."
                )

                return "ok"

            state["data"]["pack150"] = text

            state["step"] = "packplus"

            keyboard = [nums]

            send_message(
                chat_id,
                "📦 مرحله ۵ از ۵\n\nتعداد پک بالای ۱۵۰ میلیونی:",
                keyboard
            )

            return "ok"

        # PACK PLUS
        if step == "packplus":

            if text not in nums:

                send_message(
                    chat_id,
                    "❗ فقط عدد بین ۰ تا ۱۰ انتخاب کنید."
                )

                return "ok"

            state["data"]["packplus"] = text

            finish(chat_id)

            return "ok"

    return "ok"


# =========================
# FINISH
# =========================
def finish(chat_id):

    state = user_states[chat_id]

    state["data"]["created_at"] = now_time()

    save_data(state["data"])

    summary = summary_text(state["data"])

    keyboard = [
        ["➕ ثبت پایگاه بعدی"],
        ["🔄 شروع مجدد"]
    ]

    send_message(
        chat_id,
        summary,
        keyboard
    )

    state["step"] = "choose_supervisor"

    state["data"] = {}


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
