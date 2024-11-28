from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler
from telegram.ext import filters
import sqlite3

# تنظیمات عمومی
BOT_TOKEN = "7832824273:AAHcdtxb1x2FD5Ywwf2IYzR3h6sk81mrCkM"
CHANNEL_USERNAME = "tegaratnegar"
REWARD_PER_REFERRAL = 1
REWARD_PER_REFERRAL_GOLD = 2
MIN_WITHDRAWAL_AMOUNT = 10

# اتصال به پایگاه داده
try:
    conn = sqlite3.connect("bot.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        referrals INTEGER DEFAULT 0,
        balance INTEGER DEFAULT 0,
        league TEXT DEFAULT 'عادی'
    )
    """)
    conn.commit()
except sqlite3.Error as e:
    print(f"خطا در اتصال به پایگاه داده: {e}")

# وضعیت‌ها برای ConversationHandler
WAITING_FOR_WALLET, SUPPORT_MESSAGE = range(2)

# تابع شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    try:
        # بررسی عضویت کاربر در کانال
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            # اگر عضو بود، کیبورد اصلی را نمایش بده
            keyboard = ReplyKeyboardMarkup([
                [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
                [KeyboardButton("💸 برداشت"), KeyboardButton("📊 گزارش وضعیت روز")],
                [KeyboardButton("📞 پشتیبانی"), KeyboardButton("❓ راهنما")]
            ], resize_keyboard=True)
            await update.message.reply_text("✅ به ربات خوش آمدید! از دکمه‌های زیر استفاده کنید.", reply_markup=keyboard)
        else:
            raise Exception("Not a member")
    except:
        # اگر عضو نبود، دکمه عضویت را نمایش بده
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
        ])
        await update.message.reply_text(
            "⛔️ برای استفاده از ربات ابتدا باید عضو کانال زیر شوید:",
            reply_markup=keyboard
        )

# تابع برای اطمینان از ثبت اطلاعات اولیه کاربر
def ensure_user_exists(user_id):
    conn = sqlite3.connect('bot_database.db')  # اتصال به دیتابیس
    cursor = conn.cursor()

    # بررسی وجود کاربر در دیتابیس
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    # اگر کاربر وجود نداشت، اطلاعات پیش‌فرض اضافه شود
    if not user:
        cursor.execute("INSERT INTO users (user_id, balance, invites) VALUES (?, ?, ?)", 
                       (user_id, 0, 0))
        conn.commit()
    
    conn.close()

# تابع برای نمایش پروفایل کاربر
def show_profile(user_id):
    conn = sqlite3.connect('bot_database.db')  # اتصال به دیتابیس
    cursor = conn.cursor()

    # فراخوانی تابع اطمینان از وجود کاربر
    ensure_user_exists(user_id)

    # دریافت اطلاعات کاربر
    cursor.execute("SELECT balance, invites FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()

    # نمایش اطلاعات
    balance, invites = user_data
    return f"👤 پروفایل شما:\n💰 موجودی: {balance}\n👥 تعداد دعوت‌ها: {invites}"


# بررسی عضویت و ثبت دعوت
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    referrer_id = context.user_data.get("referrer_id")

    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            await query.message.edit_text("✅ عضویت شما تأیید شد! حالا می‌توانید از ربات استفاده کنید.")

            # ثبت زیرمجموعه
            if referrer_id:
                await register_referral(user_id, referrer_id)

            # نمایش کیبورد شیشه‌ای
            keyboard = ReplyKeyboardMarkup([
                [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
                [KeyboardButton("💸 برداشت"), KeyboardButton("📊 گزارش وضعیت روز")],
                [KeyboardButton("📞 پشتیبانی"), KeyboardButton("❓ راهنما")]
            ], resize_keyboard=True)
            await query.message.reply_text("✅ از دکمه‌های زیر برای استفاده از امکانات ربات استفاده کنید.", reply_markup=keyboard)
        else:
            await query.answer("⛔️ هنوز عضو کانال نشده‌اید!", show_alert=True)
    except Exception as e:
        print(f"خطا در بررسی عضویت: {e}")
        await query.answer("⛔️ خطا در بررسی عضویت!", show_alert=True)

# ثبت زیرمجموعه
async def register_referral(user_id, referrer_id):
    cursor.execute("SELECT referrals, balance FROM users WHERE user_id = ?", (referrer_id,))
    referrer_data = cursor.fetchone()
    if referrer_data:
        referrals, balance = referrer_data
        referrals += 1
        balance += REWARD_PER_REFERRAL
        cursor.execute("UPDATE users SET referrals = ?, balance = ? WHERE user_id = ?", (referrals, balance, referrer_id))
        conn.commit()
        await application.bot.send_message(
            chat_id=referrer_id,
            text=f"🎉 یک زیرمجموعه جدید اضافه شد!\n"
                 f"🔗 تعداد زیرمجموعه‌ها: {referrals}\n"
                 f"💰 موجودی: {balance} دوج‌کوین"
        )

# پروفایل کاربر
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT referrals, balance, league FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    if user_data:
        referrals, balance, league = user_data
        await update.message.reply_text(f"👤 پروفایل شما:\n\n"
                                        f"🔗 تعداد زیرمجموعه‌ها: {referrals}\n"
                                        f"💰 موجودی دوج‌کوین: {balance}\n"
                                        f"🏆 سطح: {league}")
    else:
        await update.message.reply_text("⛔️ اطلاعاتی یافت نشد. لطفاً ابتدا /start را بزنید.")

# گزارش روزانه
async def daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT referrals, balance, league FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    if user_data:
        referrals, balance, league = user_data
        await update.message.reply_text(f"📊 گزارش روزانه:\n\n"
                                        f"🔗 تعداد زیرمجموعه‌ها: {referrals}\n"
                                        f"💰 موجودی: {balance} دوج‌کوین\n"
                                        f"🏆 سطح: {league}")
    else:
        await update.message.reply_text("⛔️ اطلاعاتی یافت نشد. لطفاً ابتدا /start را بزنید.")

# درخواست لینک دعوت
async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = context.bot.username

    invite_link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(
        f"🔗 لینک دعوت اختصاصی شما:\n\n{invite_link}\n\n"
        "هر کاربری که با این لینک عضو شود، به موجودی شما دوج‌کوین اضافه می‌شود!"
    )

# راهنما
async def help_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ راهنمای استفاده از ربات:\n\n"
                                    "1️⃣از لینک دعوت برای درآمدزایی هر دعوت 1عدد دوج استفاده کنید.\n"
                                    "2️⃣  پروفایل خود را برای دیدن موجودی بررسی کنید.\n"
                                    "3️⃣ درخواست برداشت بعد 10 عدد قابل ثبت است.\n"
                                    "4️⃣ برای پشتیبانی فقط پیام  ارسال کنید بررسی میشود.")

# پشتیبانی
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 برای پشتیبانی پیام خود را ارسال کنید. مدیران به زودی پاسخ خواهند داد."
    )

# تابع مدیریت درخواست برداشت
async def withdrawal_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    if user_data and user_data[0] >= MIN_WITHDRAWAL_AMOUNT:
        await update.message.reply_text("💼 لطفاً آدرس ولت دوج‌کوین خود را وارد کنید:")
        return WAITING_FOR_WALLET
    else:
        await update.message.reply_text(f"⛔️ حداقل موجودی برای برداشت {MIN_WITHDRAWAL_AMOUNT} دوج‌کوین است.")
        return ConversationHandler.END

# تابع برای تأیید آدرس ولت
async def confirm_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = update.message.text
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    if balance >= MIN_WITHDRAWAL_AMOUNT:
        new_balance = balance - MIN_WITHDRAWAL_AMOUNT
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        conn.commit()
        await update.message.reply_text(f"✅ درخواست برداشت ثبت شد.\n"
                                        f"آدرس ولت: {wallet_address}\n"
                                        f"💰 برداشت شما به زودی انجام خواهد شد.")
    else:
        await update.message.reply_text("⛔️ موجودی کافی نیست.")
    return ConversationHandler.END

# تنظیمات اصلی ربات
application = Application.builder().token(BOT_TOKEN).build()

# افزودن هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.Text("🔗 لینک دعوت و درآمدزایی"), referral_link))
application.add_handler(MessageHandler(filters.Text("👤 پروفایل"), profile))
application.add_handler(MessageHandler(filters.Text("📊 گزارش وضعیت روز"), daily_report))
application.add_handler(MessageHandler(filters.Text("📞 پشتیبانی"), support))
application.add_handler(MessageHandler(filters.Text("❓ راهنما"), help_section))
application.add_handler(MessageHandler(filters.Text("💸 برداشت"), withdrawal_request))
application.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))

if __name__ == "__main__":
    print("🚀 ربات اجرا شد.")
    application.run_polling()
