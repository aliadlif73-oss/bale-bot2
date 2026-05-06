from flask import Flask, request
import json
import requests
from datetime import datetime
import threading
import jdatetime

app = Flask(__name__)

# =========================
# TOKEN
# =========================

TOKEN = "1956867539:Qpq0riwmj0FemRdVwB60QRDGpgDz8txxLmU"

SEND_URL = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"

# =========================
# LOAD CUSTOMERS
# =========================

with open("customers.json", "r", encoding="utf-8") as f:
    customers = json.load(f)

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
# STATES
# =========================

user_states = {}

# =========================
# HELPERS
# =========================

def now_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def jalali_date():

    now = jdatetime.datetime.now()

    return now.strftime("%m/%d")


def format_price(price):

    try:
        return "{:,}".format(int(price))
    except:
        return "0"


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

    requests.post(
        SEND_URL,
        data={
            "chat_id": payload["chat_id"],
            "text": payload["text"],
            "reply_markup": json.dumps(
                payload.get("reply_markup", {}),
                ensure_ascii=False
            )
        }
    )


def save_data(data):

    with file_lock:

        with open("data.json", "a", encoding="utf-8") as f:

            f.write(
                json.dumps(data, ensure_ascii=False) + "\n"
            )


def reset_user(chat_id):

    user_states[chat_id] = {
        "step": "choose_supervisor",
        "data": {}
    }

    keyboard = [[s] for s in supervisors]

    send_message(
        chat_id,
        "👋 سلام\n\nلطفاً سرپرست خود را انتخاب کنید:",
        keyboard
    )


def finish(chat_id):

    data = user_states[chat_id]["data"]

    data["created_at"] = now_time()

    save_data(data)

    shamsi = jalali_date()

    txt = "✅ گزارش با موفقیت ثبت شد\n\n"

    txt += f"👤 سرپرست: {data.get('supervisor')}\n"

    txt += f"📅 تاریخ: {shamsi}\n"

    # =========================
    # NO BUY FLOW SUMMARY
    # =========================

    if data.get("type") == "no_buy":

        txt += "\n"

        if data.get("customer_name"):
            txt += f"🏪 فروشگاه: {data.get('customer_name')}\n"

        txt += f"📌 نتیجه ویزیت: {data.get('result')}\n"

        if data.get("amount"):

            formatted_amount = format_price(
                data.get("amount")
            )

            txt += f"💰 مبلغ فروش:\n{formatted_amount} ریال\n"

        if data.get("reason"):
            txt += f"❌ علت عدم خرید:\n{data.get('reason')}\n"

        if data.get("followup"):
            txt += f"📅 زمان پیگیری:\n{data.get('followup')}\n"

    # =========================
    # PACK FLOW SUMMARY
    # =========================

    if data.get("type") == "pack":

        txt += "\n📦 گزارش پک ثبت شد\n\n"

        txt += f"پک ۱۵ میلیونی: {data.get('pack15', '0')}\n"

        txt += f"پک ۴۵ میلیونی: {data.get('pack45', '0')}\n"

        txt += f"پک ۷۵ میلیونی: {data.get('pack75', '0')}\n"

        txt += f"پک ۱۵۰ میلیونی: {data.get('pack150', '0')}\n"

        txt += f"پک بالای ۱۵۰: {data.get('packplus', '0')}\n"

    keyboard = [
        ["➕ ثبت پایگاه بعدی"],
        ["🔄 شروع مجدد"]
    ]

    send_message(chat_id, txt, keyboard)

    reset_user(chat_id)

# =========================
# HOME
# =========================

@app.route("/")
def home():
    return "Bale Bot Running"

# =========================
# WEBHOOK
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.json

    if "message" not in data:
        return "ok"

    message = data["message"]

    chat_id = message["chat"]["id"]

    text = message.get("text", "").strip()

    # =========================
    # START
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
                "❗ لطفاً یکی از سرپرست‌ها را انتخاب کنید."
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
            "✅ سرپرست ثبت شد\n\nنوع گزارش را انتخاب کنید:",
            keyboard
        )

        return "ok"

    # =========================
    # CHOOSE TYPE
    # =========================

    if step == "choose_type":

        if text == "📉 گزارش خرید نکرده":

            state["data"]["type"] = "no_buy"

            state["step"] = "customer_code"

            send_message(
                chat_id,
                "🧾 کد مشتری را وارد کنید:\n\nفقط عدد وارد شود"
            )

            return "ok"

        if text == "🎯 گزارش پک":

            state["data"]["type"] = "pack"

            state["step"] = "pack15"

            nums = [[str(i) for i in range(11)]]

            send_message(
                chat_id,
                "📦 تعداد پک ۱۵ میلیونی:",
                nums
            )

            return "ok"

    # =========================
    # CUSTOMER CODE
    # =========================

    if step == "customer_code":

        if not text.isdigit():

            send_message(
                chat_id,
                "❗ کد مشتری فقط باید عدد باشد."
            )

            return "ok"

        if text not in customers:

            send_message(
                chat_id,
                "❗ مشتری پیدا نشد."
            )

            return "ok"

        customer = customers[text]

        # =========================
        # VALIDATE SUPERVISOR
        # =========================

        selected_supervisor = (
            state["data"]["supervisor"]
            .replace(" ", "")
            .strip()
        )

        customer_supervisor = (
            customer.get("supervisor", "")
            .replace(" ", "")
            .strip()
        )

        if selected_supervisor not in customer_supervisor:

            send_message(
                chat_id,
                "❌ این مشتری متعلق به سرپرست شما نیست."
            )

            return "ok"

        state["data"]["customer_code"] = text

        state["data"]["customer_name"] = customer["name"]

        formatted_buy = format_price(
            customer["last_buy"]
        )

        info = f"""
🏪 {customer['name']}

📅 {customer['days']} روز خرید نداشته

💰 کل خرید ۱۴۰۴:
{formatted_buy} ریال
"""

        keyboard = [
            ["✅ خرید کرد"],
            ["🔄 نیاز به پیگیری"],
            ["❌ خرید نکرد"],
            ["🔄 شروع مجدد"]
        ]

        state["step"] = "result"

        send_message(
            chat_id,
            info + "\n📌 نتیجه ویزیت را انتخاب کنید:",
            keyboard
        )

        return "ok"

    # =========================
    # RESULT
    # =========================

    if step == "result":

        state["data"]["result"] = text

        # BUY
        if text == "✅ خرید کرد":

            state["step"] = "amount"

            send_message(
                chat_id,
                "💰 مبلغ فروش را به ریال وارد کنید\n\nمثال:\n25,000,000"
            )

            return "ok"

        # FOLLOWUP
        if text == "🔄 نیاز به پیگیری":

            state["step"] = "followup"

            keyboard = [
                ["📅 ۳ روز آینده"],
                ["📅 تا یک هفته آینده"],
                ["📅 تا آخر ماه"]
            ]

            send_message(
                chat_id,
                "📌 زمان پیگیری بعدی را انتخاب کنید:",
                keyboard
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

    # =========================
    # AMOUNT
    # =========================

    if step == "amount":

        clean = (
            text
            .replace(",", "")
            .replace(" ", "")
        )

        if not clean.isdigit():

            send_message(
                chat_id,
                "❗ مبلغ فقط باید عدد باشد."
            )

            return "ok"

        state["data"]["amount"] = clean

        finish(chat_id)

        return "ok"

    # =========================
    # FOLLOWUP
    # =========================

    if step == "followup":

        state["data"]["followup"] = text

        finish(chat_id)

        return "ok"

    # =========================
    # REASON
    # =========================

    if step == "reason":

        state["data"]["reason"] = text

        finish(chat_id)

        return "ok"

    # =========================
    # PACK FLOW
    # =========================

    nums = [str(i) for i in range(11)]

    if step == "pack15":

        if text not in nums:

            send_message(
                chat_id,
                "❗ فقط عدد ۰ تا ۱۰ مجاز است."
            )

            return "ok"

        state["data"]["pack15"] = text

        state["step"] = "pack45"

        send_message(
            chat_id,
            "📦 تعداد پک ۴۵ میلیونی:",
            [nums]
        )

        return "ok"

    if step == "pack45":

        if text not in nums:

            send_message(
                chat_id,
                "❗ فقط عدد ۰ تا ۱۰ مجاز است."
            )

            return "ok"

        state["data"]["pack45"] = text

        state["step"] = "pack75"

        send_message(
            chat_id,
            "📦 تعداد پک ۷۵ میلیونی:",
            [nums]
        )

        return "ok"

    if step == "pack75":

        if text not in nums:

            send_message(
                chat_id,
                "❗ فقط عدد ۰ تا ۱۰ مجاز است."
            )

            return "ok"

        state["data"]["pack75"] = text

        state["step"] = "pack150"

        send_message(
            chat_id,
            "📦 تعداد پک ۱۵۰ میلیونی:",
            [nums]
        )

        return "ok"

    if step == "pack150":

        if text not in nums:

            send_message(
                chat_id,
                "❗ فقط عدد ۰ تا ۱۰ مجاز است."
            )

            return "ok"

        state["data"]["pack150"] = text

        state["step"] = "packplus"

        send_message(
            chat_id,
            "📦 تعداد پک بالای ۱۵۰ میلیونی:",
            [nums]
        )

        return "ok"

    if step == "packplus":

        if text not in nums:

            send_message(
                chat_id,
                "❗ فقط عدد ۰ تا ۱۰ مجاز است."
            )

            return "ok"

        state["data"]["packplus"] = text

        finish(chat_id)

        return "ok"

    return "ok"

# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
