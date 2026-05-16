from flask import Flask, request, send_file
import json
import requests
import threading
import jdatetime
import csv
import os

app = Flask(__name__)

TOKEN = "1956867539:Qpq0riwmj0FemRdVwB60QRDGpgDz8txxLmU"
SEND_URL = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"


with open("customers.json", "r", encoding="utf-8") as f:
    customers = json.load(f)

with open("remaining_pack.json", "r", encoding="utf-8") as f:
    remaining_pack_customers = json.load(f)


# تبدیل یاقوتی به ایمانی در دیتای خرید نکرده
for customer_code in customers:
    if customers[customer_code].get("supervisor", "") == "عباس یاقوتی":
        customers[customer_code]["supervisor"] = "ایمانی"

    if customers[customer_code].get("manager", "") == "عباس یاقوتی":
        customers[customer_code]["manager"] = "ایمانی"


# تبدیل یاقوتی به ایمانی در دیتای پک باقیمانده
for customer_code in remaining_pack_customers:
    if remaining_pack_customers[customer_code].get("supervisor", "") == "عباس یاقوتی":
        remaining_pack_customers[customer_code]["supervisor"] = "ایمانی"

    if remaining_pack_customers[customer_code].get("manager", "") == "عباس یاقوتی":
        remaining_pack_customers[customer_code]["manager"] = "ایمانی"


file_lock = threading.Lock()

supervisors = [
    "حمزه پور",
    "شریفیان",
    "سالاریه",
    "کلانتری",
    "محمدنیا",
    "زمانیان",
    "تقی زاده",
    "ایمانی",
    "خلفی"
]

user_states = {}


def jalali_date():
    return jdatetime.datetime.now().strftime("%m/%d")


def jalali_datetime():
    return jdatetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")


def format_price(price):
    try:
        return "{:,}".format(int(float(price)))
    except:
        return "0"


def format_percent(value):
    try:
        number = float(value)
        if number <= 1:
            number = number * 100
        return f"{number:.1f}٪"
    except:
        return str(value)


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
            "reply_markup": json.dumps(payload.get("reply_markup", {}), ensure_ascii=False)
        },
        timeout=10
    )


def append_csv(filename, headers, row):
    with file_lock:
        file_exists = os.path.isfile(filename)

        with open(filename, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow(headers)

            writer.writerow(row)


def get_allowed_names(selected_supervisor):
    selected_supervisor = selected_supervisor.strip()

    if selected_supervisor == "خلفی":
        return ["خلفی", "فرهاد خلفی", "فرهاد خلفی - گالری", "محمد افشار", "افشار"]

    if selected_supervisor == "ایمانی":
        return ["ایمانی", "آتوسا ایمانی", "عباس یاقوتی"]

    return [selected_supervisor]


def is_customer_allowed(selected_supervisor, customer):
    allowed_names = get_allowed_names(selected_supervisor)

    customer_supervisor = customer.get("supervisor", "").replace(" ", "").strip()
    customer_manager = customer.get("manager", "").replace(" ", "").strip()

    for name in allowed_names:
        clean_name = name.replace(" ", "").strip()

        if clean_name in customer_supervisor:
            return True

        if clean_name in customer_manager:
            return True

    return False


def save_no_buy_report(data):
    headers = [
        "تاریخ",
        "تاریخ و ساعت",
        "سرپرست",
        "کد مشتری",
        "نام مشتری",
        "تعداد روز خرید نکرده",
        "کل خرید ۱۴۰۴",
        "نتیجه ویزیت",
        "مبلغ فروش ریال",
        "علت عدم خرید",
        "زمان پیگیری"
    ]

    row = [
        jalali_date(),
        jalali_datetime(),
        data.get("supervisor", ""),
        data.get("customer_code", ""),
        data.get("customer_name", ""),
        data.get("days", ""),
        data.get("last_buy", ""),
        data.get("result", ""),
        data.get("amount", ""),
        data.get("reason", ""),
        data.get("followup", "")
    ]

    append_csv("report_no_buy.csv", headers, row)


def save_pack_report(data):
    headers = [
        "تاریخ",
        "تاریخ و ساعت",
        "سرپرست",
        "پک ۱۵ میلیونی",
        "پک ۴۵ میلیونی",
        "پک ۷۵ میلیونی",
        "پک ۱۵۰ میلیونی",
        "پک بالای ۱۵۰"
    ]

    row = [
        jalali_date(),
        jalali_datetime(),
        data.get("supervisor", ""),
        data.get("pack15", "0"),
        data.get("pack45", "0"),
        data.get("pack75", "0"),
        data.get("pack150", "0"),
        data.get("packplus", "0")
    ]

    append_csv("report_pack.csv", headers, row)


def save_remaining_pack_report(data):
    headers = [
        "تاریخ",
        "تاریخ و ساعت",
        "سرپرست",
        "کد مشتری",
        "نام مشتری",
        "تارگت ریالی",
        "فروش ناخالص",
        "درصد تحقق",
        "نتیجه پیگیری",
        "پک خریداری شده",
        "علت عدم خرید"
    ]

    row = [
        jalali_date(),
        jalali_datetime(),
        data.get("supervisor", ""),
        data.get("customer_code", ""),
        data.get("customer_name", ""),
        data.get("target", ""),
        data.get("gross_sales", ""),
        data.get("achievement_percent", ""),
        data.get("remaining_result", ""),
        data.get("remaining_pack_type", ""),
        data.get("remaining_reason", "")
    ]

    append_csv("report_remaining_pack.csv", headers, row)


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
    shamsi = jalali_date()

    if data.get("type") == "no_buy":
        save_no_buy_report(data)

    if data.get("type") == "pack":
        save_pack_report(data)

    if data.get("type") == "remaining_pack":
        save_remaining_pack_report(data)

    txt = "✅ گزارش با موفقیت ثبت شد\n\n"
    txt += f"👤 سرپرست: {data.get('supervisor')}\n"
    txt += f"📅 تاریخ: {shamsi}\n"

    if data.get("type") == "no_buy":
        txt += "\n"
        txt += f"🏪 فروشگاه: {data.get('customer_name', '')}\n"
        txt += f"📌 نتیجه ویزیت: {data.get('result', '')}\n"

        if data.get("amount"):
            txt += f"💰 مبلغ فروش:\n{format_price(data.get('amount'))} ریال\n"

        if data.get("reason"):
            txt += f"❌ علت عدم خرید:\n{data.get('reason')}\n"

        if data.get("followup"):
            txt += f"📅 زمان پیگیری:\n{data.get('followup')}\n"

    if data.get("type") == "pack":
        txt += "\n📦 گزارش پک ثبت شد\n\n"
        txt += f"پک ۱۵ میلیونی: {data.get('pack15', '0')}\n"
        txt += f"پک ۴۵ میلیونی: {data.get('pack45', '0')}\n"
        txt += f"پک ۷۵ میلیونی: {data.get('pack75', '0')}\n"
        txt += f"پک ۱۵۰ میلیونی: {data.get('pack150', '0')}\n"
        txt += f"پک بالای ۱۵۰: {data.get('packplus', '0')}\n"

    if data.get("type") == "remaining_pack":
        txt += "\n📦 گزارش پک باقیمانده ثبت شد\n\n"
        txt += f"🏪 مشتری: {data.get('customer_name', '')}\n"
        txt += f"🎯 تارگت ریالی: {format_price(data.get('target', '0'))} ریال\n"
        txt += f"📊 درصد تحقق: {format_percent(data.get('achievement_percent', ''))}\n"
        txt += f"📌 نتیجه پیگیری: {data.get('remaining_result', '')}\n"

        if data.get("remaining_pack_type"):
            txt += f"📦 پک خریداری شده: {data.get('remaining_pack_type')}\n"

        if data.get("remaining_reason"):
            txt += f"❌ علت عدم خرید:\n{data.get('remaining_reason')}\n"

    keyboard = [
        ["➕ ثبت پایگاه بعدی"],
        ["🔄 شروع مجدد"]
    ]

    send_message(chat_id, txt, keyboard)

    user_states[chat_id]["step"] = "after_finish"
    user_states[chat_id]["data"] = {}


@app.route("/")
def home():
    return "Bale Bot Running"


@app.route("/report_no_buy")
def download_no_buy():
    if not os.path.exists("report_no_buy.csv"):
        return "هنوز هیچ گزارش خرید نکرده‌ای ثبت نشده است.", 404

    return send_file("report_no_buy.csv", as_attachment=True)


@app.route("/report_pack")
def download_pack():
    if not os.path.exists("report_pack.csv"):
        return "هنوز هیچ گزارش پکی ثبت نشده است.", 404

    return send_file("report_pack.csv", as_attachment=True)


@app.route("/report_remaining_pack")
def download_remaining_pack():
    if not os.path.exists("report_remaining_pack.csv"):
        return "هنوز هیچ گزارش پک باقیمانده‌ای ثبت نشده است.", 404

    return send_file("report_remaining_pack.csv", as_attachment=True)


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if text == "/start" or text == "🔄 شروع مجدد":
        reset_user(chat_id)
        return "ok"

    if chat_id not in user_states:
        reset_user(chat_id)
        return "ok"

    state = user_states[chat_id]
    step = state["step"]

    if step == "after_finish":
        if text == "➕ ثبت پایگاه بعدی":
            reset_user(chat_id)
            return "ok"

        send_message(
            chat_id,
            "برای ثبت گزارش جدید، روی یکی از گزینه‌ها بزنید:",
            [["➕ ثبت پایگاه بعدی"], ["🔄 شروع مجدد"]]
        )
        return "ok"

    if step == "choose_supervisor":
        if text not in supervisors:
            send_message(chat_id, "❗ لطفاً یکی از سرپرست‌ها را انتخاب کنید.")
            return "ok"

        state["data"]["supervisor"] = text
        state["step"] = "choose_type"

        keyboard = [
            ["📉 گزارش خرید نکرده"],
            ["🎯 گزارش پک"],
            ["📦 پک باقیمانده"],
            ["🔄 شروع مجدد"]
        ]

        send_message(chat_id, "✅ سرپرست ثبت شد\n\nنوع گزارش را انتخاب کنید:", keyboard)
        return "ok"

    if step == "choose_type":
        if text == "📉 گزارش خرید نکرده":
            state["data"]["type"] = "no_buy"
            state["step"] = "customer_code"
            send_message(chat_id, "🧾 کد مشتری را وارد کنید:\n\nفقط عدد وارد شود")
            return "ok"

        if text == "🎯 گزارش پک":
            state["data"]["type"] = "pack"
            state["step"] = "pack15"
            nums = [[str(i) for i in range(11)]]
            send_message(chat_id, "📦 تعداد پک ۱۵ میلیونی:", nums)
            return "ok"

        if text == "📦 پک باقیمانده":
            state["data"]["type"] = "remaining_pack"
            state["step"] = "remaining_customer_code"
            send_message(chat_id, "🧾 کد مشتری را وارد کنید:\n\nفقط عدد وارد شود")
            return "ok"

        send_message(chat_id, "❗ لطفاً نوع گزارش را از دکمه‌ها انتخاب کنید.")
        return "ok"

    if step == "customer_code":
        if not text.isdigit():
            send_message(chat_id, "❗ کد مشتری فقط باید عدد باشد.")
            return "ok"

        if text not in customers:
            send_message(chat_id, "❗ مشتری پیدا نشد.")
            return "ok"

        customer = customers[text]

        if not is_customer_allowed(state["data"]["supervisor"], customer):
            send_message(chat_id, "❌ این مشتری متعلق به سرپرست شما نیست.")
            return "ok"

        state["data"]["customer_code"] = text
        state["data"]["customer_name"] = customer.get("name", "")
        state["data"]["days"] = customer.get("days", "")
        state["data"]["last_buy"] = customer.get("last_buy", "")

        formatted_buy = format_price(customer.get("last_buy", 0))

        info = f"""
🏪 {customer.get('name', '')}

📅 {customer.get('days', '')} روز خرید نداشته

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

        send_message(chat_id, info + "\n📌 نتیجه ویزیت را انتخاب کنید:", keyboard)
        return "ok"

    if step == "remaining_customer_code":
        if not text.isdigit():
            send_message(chat_id, "❗ کد مشتری فقط باید عدد باشد.")
            return "ok"

        if text not in remaining_pack_customers:
            send_message(chat_id, "❗ مشتری در لیست پک باقیمانده پیدا نشد.")
            return "ok"

        customer = remaining_pack_customers[text]

        if not is_customer_allowed(state["data"]["supervisor"], customer):
            send_message(chat_id, "❌ این مشتری متعلق به سرپرست شما نیست.")
            return "ok"

        state["data"]["customer_code"] = text
        state["data"]["customer_name"] = customer.get("name", "")
        state["data"]["target"] = customer.get("target", "")
        state["data"]["gross_sales"] = customer.get("gross_sales", "")
        state["data"]["achievement_percent"] = customer.get("achievement_percent", "")

        info = f"""
🏪 {customer.get('name', '')}

🎯 تارگت ریالی:
{format_price(customer.get('target', 0))} ریال

💰 فروش ناخالص:
{format_price(customer.get('gross_sales', 0))} ریال

📊 درصد تحقق:
{format_percent(customer.get('achievement_percent', ''))}
"""

        keyboard = [
            ["✅ خرید کرد پک"],
            ["❌ خرید نکرد"],
            ["🔄 شروع مجدد"]
        ]

        state["step"] = "remaining_result"

        send_message(chat_id, info + "\n📌 نتیجه پیگیری را انتخاب کنید:", keyboard)
        return "ok"

    if step == "remaining_result":
        if text == "✅ خرید کرد پک":
            state["data"]["remaining_result"] = "خرید کرد پک"
            state["step"] = "remaining_pack_type"

            keyboard = [
                ["پک ۱۵ میلیونی"],
                ["پک ۴۵ میلیونی"],
                ["پک ۷۵ میلیونی"],
                ["پک ۱۵۰ میلیونی"],
                ["🔄 شروع مجدد"]
            ]

            send_message(chat_id, "📦 کدام پک خرید شد؟", keyboard)
            return "ok"

        if text == "❌ خرید نکرد":
            state["data"]["remaining_result"] = "خرید نکرد"
            state["step"] = "remaining_reason"

            send_message(chat_id, "❌ علت خرید نکردن را وارد کنید:")
            return "ok"

        send_message(chat_id, "❗ لطفاً یکی از گزینه‌ها را انتخاب کنید.")
        return "ok"

    if step == "remaining_pack_type":
        valid_packs = [
            "پک ۱۵ میلیونی",
            "پک ۴۵ میلیونی",
            "پک ۷۵ میلیونی",
            "پک ۱۵۰ میلیونی"
        ]

        if text not in valid_packs:
            send_message(chat_id, "❗ لطفاً نوع پک را از دکمه‌ها انتخاب کنید.")
            return "ok"

        state["data"]["remaining_pack_type"] = text
        finish(chat_id)
        return "ok"

    if step == "remaining_reason":
        state["data"]["remaining_reason"] = text
        finish(chat_id)
        return "ok"

    if step == "result":
        valid_results = ["✅ خرید کرد", "🔄 نیاز به پیگیری", "❌ خرید نکرد"]

        if text not in valid_results:
            send_message(chat_id, "❗ لطفاً نتیجه ویزیت را از دکمه‌ها انتخاب کنید.")
            return "ok"

        state["data"]["result"] = text

        if text == "✅ خرید کرد":
            state["step"] = "amount"
            send_message(chat_id, "💰 مبلغ فروش را به ریال وارد کنید\n\nمثال:\n25000000")
            return "ok"

        if text == "🔄 نیاز به پیگیری":
            state["step"] = "followup"

            keyboard = [
                ["📅 ۳ روز آینده"],
                ["📅 تا یک هفته آینده"],
                ["📅 تا آخر ماه"],
                ["🔄 شروع مجدد"]
            ]

            send_message(chat_id, "📌 زمان پیگیری بعدی را انتخاب کنید:", keyboard)
            return "ok"

        if text == "❌ خرید نکرد":
            state["step"] = "reason"
            send_message(chat_id, "❌ علت خرید نکردن را وارد کنید:")
            return "ok"

    if step == "amount":
        clean = text.replace(",", "").replace(" ", "")

        if not clean.isdigit():
            send_message(chat_id, "❗ مبلغ فقط باید عدد باشد.")
            return "ok"

        state["data"]["amount"] = clean
        finish(chat_id)
        return "ok"

    if step == "followup":
        valid_followups = [
            "📅 ۳ روز آینده",
            "📅 تا یک هفته آینده",
            "📅 تا آخر ماه"
        ]

        if text not in valid_followups:
            send_message(chat_id, "❗ لطفاً زمان پیگیری را از دکمه‌ها انتخاب کنید.")
            return "ok"

        state["data"]["followup"] = text
        finish(chat_id)
        return "ok"

    if step == "reason":
        state["data"]["reason"] = text
        finish(chat_id)
        return "ok"

    nums = [str(i) for i in range(11)]

    if step == "pack15":
        if text not in nums:
            send_message(chat_id, "❗ فقط عدد ۰ تا ۱۰ مجاز است.")
            return "ok"

        state["data"]["pack15"] = text
        state["step"] = "pack45"

        send_message(chat_id, "📦 تعداد پک ۴۵ میلیونی:", [nums])
        return "ok"

    if step == "pack45":
        if text not in nums:
            send_message(chat_id, "❗ فقط عدد ۰ تا ۱۰ مجاز است.")
            return "ok"

        state["data"]["pack45"] = text
        state["step"] = "pack75"

        send_message(chat_id, "📦 تعداد پک ۷۵ میلیونی:", [nums])
        return "ok"

    if step == "pack75":
        if text not in nums:
            send_message(chat_id, "❗ فقط عدد ۰ تا ۱۰ مجاز است.")
            return "ok"

        state["data"]["pack75"] = text
        state["step"] = "pack150"

        send_message(chat_id, "📦 تعداد پک ۱۵۰ میلیونی:", [nums])
        return "ok"

    if step == "pack150":
        if text not in nums:
            send_message(chat_id, "❗ فقط عدد ۰ تا ۱۰ مجاز است.")
            return "ok"

        state["data"]["pack150"] = text
        state["step"] = "packplus"

        send_message(chat_id, "📦 تعداد پک بالای ۱۵۰ میلیونی:", [nums])
        return "ok"

    if step == "packplus":
        if text not in nums:
            send_message(chat_id, "❗ فقط عدد ۰ تا ۱۰ مجاز است.")
            return "ok"

        state["data"]["packplus"] = text
        finish(chat_id)
        return "ok"

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
