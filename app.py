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


def normalize_text(value):
    """یکسان‌سازی نام‌ها برای تطبیق بدون خطا بین فایل‌های مختلف."""
    return (
        str(value or "")
        .replace("ي", "ی")
        .replace("ك", "ک")
        .replace("\u200c", " ")
        .replace("-", " ")
        .strip()
    )


def normalize_key(value):
    return "".join(normalize_text(value).split())


def infer_channel_from_route(route, existing_channel=""):
    if existing_channel:
        return existing_channel

    route = normalize_text(route)

    if "داروخانه" in route:
        return "داروخانه"
    if "گالری" in route:
        return "گالری"
    if "مارکت" in route or "غیر داروخانه" in route:
        return "مارکت"

    return ""


def standardize_customer_record(row):
    """خواندن همزمان فرمت جدید اکسل و فرمت قبلی customers.json."""
    route = row.get("route", row.get("route_title", ""))
    days = row.get("days", row.get("days_since_last_purchase", ""))

    return {
        "manager": normalize_text(row.get("manager", "")),
        "supervisor": normalize_text(row.get("supervisor", "")),
        "seller": normalize_text(row.get("seller", "")),
        "route": normalize_text(route),
        "signboard": normalize_text(row.get("signboard", row.get("shop_sign", ""))),
        "name": normalize_text(row.get("name", row.get("customer_name", ""))),
        "days": str(days if days is not None else ""),
        "avg_purchase": row.get("avg_purchase", ""),
        "status": normalize_text(row.get("status", "خرید نکرده بالای ۹۰ روز")),
        "channel": normalize_text(
            infer_channel_from_route(route, row.get("channel", ""))
        ),
        "grade": normalize_text(row.get("grade", "")),
        "purchase_segment": normalize_text(row.get("purchase_segment", "")),
        "last_buy": normalize_text(row.get("last_buy", "")),
        "had_pack_purchase": normalize_text(row.get("had_pack_purchase", "")),
    }


def load_customers(filename):
    with open(filename, "r", encoding="utf-8") as f:
        raw_customers = json.load(f)

    customers_by_code = {}

    # فرمت جدید: دیکشنری با کلید «کد پایگاه»
    if isinstance(raw_customers, dict):
        for customer_code, row in raw_customers.items():
            if isinstance(row, dict):
                customers_by_code[str(customer_code).strip()] = standardize_customer_record(row)

    # پشتیبانی از فرمت لیستی قبلی، برای جلوگیری از خطا در آپدیت‌های بعدی
    elif isinstance(raw_customers, list):
        for row in raw_customers:
            if not isinstance(row, dict):
                continue

            customer_code = str(row.get("customer_code", row.get("code", ""))).strip()

            if customer_code:
                customers_by_code[customer_code] = standardize_customer_record(row)

    return customers_by_code


customers = load_customers("customers.json")

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


# دکمه‌ها مستقیماً از ستون «سرپرست» فایل خرید نکرده جدید ساخته می‌شوند.
# ردیف‌های فاقد سرپرست به‌عنوان دکمه نمایش داده نمی‌شوند.
EXCLUDED_SUPERVISORS = {"", "نامشخص در فایل جدید"}


def build_supervisors(customers_data):
    names = {
        normalize_text(customer.get("supervisor", ""))
        for customer in customers_data.values()
        if normalize_text(customer.get("supervisor", "")) not in EXCLUDED_SUPERVISORS
    }

    return sorted(names)


supervisors = build_supervisors(customers)

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


# تطبیق نام کامل جدید با نام‌های کوتاه یا قبلیِ موجود در remaining_pack.json
SUPERVISOR_ALIASES = {
    "امیر حمزه پور": ["امیر حمزه پور", "امیرحمزه پور", "حمزه پور"],
    "آتوسا ایمانی": ["آتوسا ایمانی", "ایمانی", "عباس یاقوتی"],
    "حسام الدین انتظاری": ["حسام الدین انتظاری", "حسام‌الدین انتظاری", "انتظاری"],
    "حمید تقی زاده": ["حمید تقی زاده", "تقی زاده", "تقی‌زاده"],
    "ساسان محمد نیای مردخه": [
        "ساسان محمد نیای مردخه",
        "ساسان محمدنیا",
        "ساسان محمد نیا",
        "محمدنیا",
        "ساسان",
    ],
    "سعید شریفیان بجستانی": [
        "سعید شریفیان بجستانی",
        "شریفیان بجستانی",
        "شریفیان",
    ],
    "محمد حاجی غلامعلی": ["محمد حاجی غلامعلی", "حاجی غلامعلی"],
    "مرتضی تن آرای": ["مرتضی تن آرای", "تن آرای", "تن‌آرای"],
    "مرتضی سالاریه": ["مرتضی سالاریه", "سالاریه"],
    "میلاد کلانتری": ["میلاد کلانتری", "کلانتری"],
}


def get_allowed_names(selected_supervisor):
    selected_supervisor = normalize_text(selected_supervisor)
    return SUPERVISOR_ALIASES.get(selected_supervisor, [selected_supervisor])


def is_customer_allowed(selected_supervisor, customer):
    allowed_names = get_allowed_names(selected_supervisor)
    customer_supervisor = normalize_key(customer.get("supervisor", ""))
    customer_manager = normalize_key(customer.get("manager", ""))

    for name in allowed_names:
        clean_name = normalize_key(name)

        if clean_name and (
            clean_name in customer_supervisor
            or clean_name in customer_manager
        ):
            return True

    return False



def save_no_buy_report(data):
    headers = [
        "تاریخ",
        "تاریخ و ساعت",
        "سرپرست",
        "مدیر",
        "فروشنده",
        "کد مشتری",
        "نام مشتری",
        "نام تابلو",
        "عنوان مسیر",
        "کانال",
        "درجه",
        "سگمنت خرید",
        "روز غیاب",
        "میانگین خرید ریال",
        "وضعیت",
        "پک خرید داشته؟",
        "نتیجه ویزیت",
        "مبلغ فروش ریال",
        "علت عدم خرید",
        "زمان پیگیری"
    ]

    row = [
        jalali_date(),
        jalali_datetime(),
        data.get("supervisor", ""),
        data.get("manager", ""),
        data.get("seller", ""),
        data.get("customer_code", ""),
        data.get("customer_name", ""),
        data.get("signboard", ""),
        data.get("route", ""),
        data.get("channel", ""),
        data.get("grade", ""),
        data.get("purchase_segment", ""),
        data.get("days", ""),
        data.get("avg_purchase", ""),
        data.get("status", ""),
        data.get("had_pack_purchase", ""),
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
        state["data"]["avg_purchase"] = customer.get("avg_purchase", "")
        state["data"]["last_buy"] = customer.get("last_buy", "")
        state["data"]["manager"] = customer.get("manager", "")
        state["data"]["seller"] = customer.get("seller", "")
        state["data"]["route"] = customer.get("route", "")
        state["data"]["signboard"] = customer.get("signboard", "")
        state["data"]["channel"] = customer.get("channel", "")
        state["data"]["grade"] = customer.get("grade", "")
        state["data"]["purchase_segment"] = customer.get("purchase_segment", customer.get("last_buy", ""))
        state["data"]["status"] = customer.get("status", "")
        state["data"]["had_pack_purchase"] = customer.get("had_pack_purchase", "")

        info = f"""
🏪 {customer.get('name', '')}
🏷 نام تابلو: {customer.get('signboard', '')}

👤 فروشنده: {customer.get('seller', '')}
🛣 مسیر: {customer.get('route', '')}

📅 {customer.get('days', '')} روز غیاب
💰 میانگین خرید: {format_price(customer.get('avg_purchase', 0))} ریال
📊 وضعیت: {customer.get('status', '')}
🧩 سگمنت خرید: {customer.get('purchase_segment', customer.get('last_buy', ''))}
🏪 کانال: {customer.get('channel', '')}
⭐ درجه: {customer.get('grade', '')}
🎁 پک خرید داشته؟ {customer.get('had_pack_purchase', '')}
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
    ["پک بالای ۱۵۰ میلیونی"],
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
    "پک ۱۵۰ میلیونی",
    "پک بالای ۱۵۰ میلیونی"
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
