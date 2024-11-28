from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler
from telegram.ext import filters
import sqlite3

BOT_TOKEN = "7832824273:AAHcdtxb1x2FD5Ywwf2IYzR3h6sk81mrCkM"
CHANNEL_USERNAME = "tegaratnegar"
REWARD_PER_REFERRAL = 1
MIN_WITHDRAWAL_AMOUNT = 10

# تنظیم پایگاه داده
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    referrals INTEGER DEFAULT 0,
    balance INTEGER DEFAULT 0,
    last_active DATE DEFAULT NULL,
    referrer_id INTEGER DEFAULT NULL,
    league TEXT DEFAULT 'عادی'
)
""")
conn.commit()

WAITING_FOR_WALLET = range(1)

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referrer_id = None

    if context.args:  # اگر لینک دعوت وجود دارد
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            referrer_id = None

    # بررسی عضویت کاربر در دیتابیس
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_exists = cursor.fetchone()

    if not user_exists:
        # ایجاد کاربر جدید
        cursor.execute("INSERT INTO users (user_id, referrer_id) VALUES (?, ?)", (user_id, referrer_id))
        conn.commit()

    # بررسی عضویت در کانال
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not a member")
    except:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}"),
            InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")
        ]])
        await update.message.reply_text("⛔️ برای استفاده از ربات ابتدا باید عضو کانال زیر شوید:", reply_markup=keyboard)
        return

    # نمایش منوی اصلی
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
        [KeyboardButton("💸 برداشت"), KeyboardButton("📊 گزارش وضعیت روز")]
    ], resize_keyboard=True)
    await update.message.reply_text("✅ خوش آمدید! از دکمه‌های زیر برای استفاده از امکانات ربات استفاده کنید.", reply_markup=keyboard)

# بررسی عضویت
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    # بررسی عضویت در کانال
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            # بررسی اینکه آیا کاربر قبلاً دعوت شده است
            cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
            referrer_id = cursor.fetchone()[0]

            if referrer_id:
                # ثبت دعوت و اضافه کردن امتیاز به دعوت‌کننده
                cursor.execute("SELECT referrals, balance FROM users WHERE user_id = ?", (referrer_id,))
                referrer_data = cursor.fetchone()
                if referrer_data:
                    referrals, balance = referrer_data
                    referrals += 1
                    balance += REWARD_PER_REFERRAL
                    cursor.execute(
                        "UPDATE users SET referrals = ?, balance = ? WHERE user_id = ?",
                        (referrals, balance, referrer_id)
                    )
                    conn.commit()

                    # ارسال پیام تبریک به دعوت‌کننده
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 تبریک! یکی از دوستان شما عضو شد و 1 دوج‌کوین به حساب شما اضافه شد."
                    )

            await query.message.edit_text("✅ عضویت شما تأیید شد! حالا می‌توانید از ربات استفاده کنید.")
        else:
            await query.answer("⛔️ هنوز عضو کانال نشده‌اید!", show_alert=True)
    except:
        await query.answer("⛔️ خطا در بررسی عضویت!", show_alert=True)

# پروفایل کاربر
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT referrals, balance, league FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        referrals, balance, league = user_data
        await update.message.reply_text(f"👤 پروفایل شما:\n\n"
                                        f"🔗 تعداد زیرمجموعه‌ها: {referrals}\n"
                                        f"💰 موجودی: {balance} دوج‌کوین\n"
                                        f"🏆 سطح: {league}")
    else:
        await update.message.reply_text("⛔️ شما هنوز در ربات ثبت‌نام نکرده‌اید.")

# لینک دعوت
async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    invite_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(f"🔗 لینک دعوت اختصاصی شما:\n\n{invite_link}\n\n"
                                    "هر کاربری که با این لینک وارد شود، 1 دوج‌کوین به موجودی شما اضافه می‌شود.")

# درخواست برداشت
async def withdrawal_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]

    if balance >= MIN_WITHDRAWAL_AMOUNT:
        await update.message.reply_text("💼 لطفاً آدرس ولت دوج‌کوین خود را وارد کنید:")
        return WAITING_FOR_WALLET
    else:
        await update.message.reply_text(f"⛔️ حداقل موجودی برای برداشت {MIN_WITHDRAWAL_AMOUNT} دوج‌کوین است.")
        return ConversationHandler.END

# تایید برداشت
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
                                        f"💰 موجودی شما: {new_balance} دوج‌کوین.")
    else:
        await update.message.reply_text("⛔️ موجودی کافی نیست.")
    return ConversationHandler.END

# تنظیمات هندلرها
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
application.add_handler(MessageHandler(filters.Text("👤 پروفایل"), profile))
application.add_handler(MessageHandler(filters.Text("🔗 لینک دعوت و درآمدزایی"), referral_link))
application.add_handler(MessageHandler(filters.Text("💸 برداشت"), withdrawal_request))

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Text("💸 برداشت"), withdrawal_request)],
    states={
        WAITING_FOR_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_wallet)],
    },
    fallbacks=[],
)
application.add_handler(conv_handler)

application.run_polling()
