from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler
from telegram.ext import filters
import sqlite3

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

WAITING_FOR_WALLET, SUPPORT_MESSAGE = range(2)

# تابع شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referrer_id = None

    if context.args:
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            referrer_id = None

    # ثبت کاربر جدید در پایگاه داده
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

    if referrer_id and referrer_id != user_id:
        context.user_data["referrer_id"] = referrer_id

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]
    ])
    await update.message.reply_text(
        "⛔️ برای استفاده از ربات ابتدا باید عضو کانال زیر شوید:",
        reply_markup=keyboard
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
                                        f"💰 موجودی دوج‌کوین: {balance} دوج‌کوین\n"
                                        f"🏆 سطح: {league}")
    else:
        await update.message.reply_text("⛔️ اطلاعاتی یافت نشد. لطفاً ابتدا /start را بزنید.")

# گزارش وضعیت روزانه
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


# درخواست برداشت
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

# تأیید برداشت
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

# پشتیبانی
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✉️ لطفاً پیام خود را ارسال کنید.")
    return SUPPORT_MESSAGE

async def receive_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.effective_user.id
    try:
        await application.bot.send_message(
            chat_id="8031568534",
            text=f"پیام جدید از {user_id}:\n\n{user_message}"
        )
        await update.message.reply_text("✅ پیام شما با موفقیت دریافت شد و به زودی بررسی خواهد شد.")
    except Exception as e:
        print(f"خطا در ارسال پیام پشتیبانی: {e}")
        await update.message.reply_text("⛔️ خطایی رخ داده است.")
    return ConversationHandler.END

# راهنما
async def help_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ راهنمای استفاده از ربات:\n\n"
                                    "1️⃣ از لینک دعوت برای درآمدزایی استفاده کنید.\n"
                                    "2️⃣ پروفایل خود را بررسی کنید.\n"
                                    "3️⃣ درخواست برداشت ثبت کنید.\n"
                                    "4️⃣ برای پشتیبانی پیام ارسال کنید.")

# تنظیم هندلرها
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
application.add_handler(MessageHandler(filters.Text("🔗 لینک دعوت و درآمدزایی"), referral_link))
application.add_handler(MessageHandler(filters.Text("👤 پروفایل"), profile))
application.add_handler(MessageHandler(filters.Text("📊 گزارش وضعیت روز"), daily_report))
application.add_handler(MessageHandler(filters.Text("💸 برداشت"), withdrawal_request))
application.add_handler(MessageHandler(filters.Text("📞 پشتیبانی"), support))
application.add_handler(MessageHandler(filters.Text("❓ راهنما"), help_section))

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Text("💸 برداشت"), withdrawal_request),
                  MessageHandler(filters.Text("📞 پشتیبانی"), support)],
    states={
        WAITING_FOR_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_wallet)],
        SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_message)],
    },
    fallbacks=[],
)
application.add_handler(conv_handler)

# اجرای ربات
application.run_polling()
