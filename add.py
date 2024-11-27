from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler
from telegram.ext import filters
import sqlite3
from datetime import datetime

# تنظیمات ربات
BOT_TOKEN = "7832824273:AAHcdtxb1x2FD5Ywwf2IYzR3h6sk81mrCkM"
CHANNEL_USERNAME = "tegaratnegar"  # نام کانال شما (بدون @)
REWARD_PER_REFERRAL = 1  # پاداش به ازای هر زیرمجموعه
BONUS_FOR_20_REFERRALS = 5  # پاداش برای 20 زیرمجموعه
MIN_WITHDRAWAL_AMOUNT = 10  # حداقل مقدار برای برداشت
DAILY_GIFT = 0.5  # هدیه روزانه به ازای هر کاربر

# اتصال به پایگاه داده
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    referrals INTEGER DEFAULT 0,
    balance INTEGER DEFAULT 0,
    last_active DATE DEFAULT NULL
)
""")
conn.commit()

# مراحل درخواست برداشت
WAITING_FOR_WALLET = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referrer_id = None

    # بررسی لینک دعوت
    if context.args:
        referrer_id = int(context.args[0])

    # ثبت کاربر در پایگاه داده
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

    # بررسی هدیه روزانه
    today = datetime.now().date()
    cursor.execute("SELECT last_active, balance FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        last_active = user_data[0]
        balance = user_data[1]

        if last_active != today:
            # افزودن هدیه روزانه
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (DAILY_GIFT, user_id))
            cursor.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (today, user_id))
            conn.commit()
            balance += DAILY_GIFT

            # ارسال پیام به کاربر
            await update.message.reply_text(f"🎉 شما امروز {DAILY_GIFT} دوج‌کوین هدیه گرفتید!\nموجودی شما: {balance} دوج‌کوین")
        else:
            await update.message.reply_text(f"⛔️ شما امروز قبلاً هدیه روزانه خود را دریافت کرده‌اید.\nموجودی شما: {balance} دوج‌کوین")

    # بررسی عضویت در کانال
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not a member")
    except:
        # درخواست عضویت
        keyboard = InlineKeyboardMarkup([[ 
            InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}"),
            InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")
        ]])
        await update.message.reply_text("⛔️ برای استفاده از ربات ابتدا باید عضو کانال زیر شوید:", reply_markup=keyboard)
        return

    # نمایش کیبورد شیشه‌ای
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
        [KeyboardButton("💸 برداشت"), KeyboardButton("📊 گزارش وضعیت روز")]
    ], resize_keyboard=True)
    await update.message.reply_text("✅ خوش آمدید! از دکمه‌های زیر برای استفاده از امکانات ربات استفاده کنید.", reply_markup=keyboard)

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    # بررسی عضویت در کانال
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            # نمایش کیبورد شیشه‌ای
            keyboard = ReplyKeyboardMarkup([
                [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
                [KeyboardButton("💸 برداشت"), KeyboardButton("📊 گزارش وضعیت روز")]
            ], resize_keyboard=True)
            await query.message.edit_text("✅ عضویت شما تأیید شد! حالا می‌توانید از ربات استفاده کنید.", reply_markup=keyboard)
        else:
            raise Exception("Not a member")
    except:
        await query.answer("⛔️ هنوز عضو کانال نیستید!", show_alert=True)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # گرفتن اطلاعات کاربر
    cursor.execute("SELECT referrals, balance FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    referrals = user_data[0] if user_data else 0
    balance = user_data[1] if user_data else 0

    # ارسال اطلاعات پروفایل
    await update.message.reply_text(f"👤 پروفایل شما:\n\n"
                                    f"🔗 تعداد زیرمجموعه‌ها: {referrals}\n"
                                    f"💰 موجودی دوج‌کوین: {balance}")

async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # ارسال لینک دعوت اختصاصی
    invite_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(f"🔗 لینک دعوت اختصاصی شما:\n\n{invite_link}\n\n"
                                    "هر کاربری که با این لینک وارد شود، 1 دوج‌کوین به موجودی شما اضافه می‌شود.")

async def withdrawal_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # گرفتن موجودی کاربر
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    balance = user_data[0] if user_data else 0

    if balance >= MIN_WITHDRAWAL_AMOUNT:
        await update.message.reply_text("💼 لطفاً آدرس ولت دوج‌کوین خود را وارد کنید:")
        return WAITING_FOR_WALLET
    else:
        await update.message.reply_text(f"⛔️ حداقل موجودی برای برداشت {MIN_WITHDRAWAL_AMOUNT} دوج‌کوین است.")
        return ConversationHandler.END

async def confirm_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = update.message.text
    user_id = update.effective_user.id

    # تأیید درخواست برداشت
    await update.message.reply_text(f"✅ درخواست برداشت ثبت شد.\n"
                                    f"آدرس ولت: `{wallet_address}`\n"
                                    f"💰 برداشت شما به زودی انجام خواهد شد.", parse_mode="Markdown")
    return ConversationHandler.END

async def daily_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT referrals, balance, last_active FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        referrals = user_data[0]
        balance = user_data[1]
        last_active = user_data[2]
        await update.message.reply_text(f"📊 وضعیت روزانه شما:\n\n"
                                        f"🔗 تعداد زیرمجموعه‌ها: {referrals}\n"
                                        f"💰 موجودی دوج‌کوین: {balance}\n"
                                        f"📅 تاریخ آخرین فعالیت: {last_active}")
    else:
        await update.message.reply_text("⛔️ شما هنوز در ربات ثبت‌نام نکرده‌اید.")

# تنظیمات اصلی ربات
application = Application.builder().token(BOT_TOKEN).build()

# هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
application.add_handler(MessageHandler(filters.Text("👤 پروفایل"), profile))
application.add_handler(MessageHandler(filters.Text("🔗 لینک دعوت و درآمدزایی"), referral_link))
application.add_handler(MessageHandler(filters.Text("💸 برداشت"), withdrawal_request))
application.add_handler(MessageHandler(filters.Text("📊 گزارش وضعیت روز"), daily_status))

# اضافه کردن کانورزیشن برای برداشت
conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Text("💸 برداشت"), withdrawal_request)],
    states={WAITING_FOR_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_wallet)]},
    fallbacks=[],
)
application.add_handler(conv_handler)

# شروع ربات
application.run_polling()
