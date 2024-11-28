from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler
from telegram.ext import filters
import sqlite3
from datetime import datetime

BOT_TOKEN = "7832824273:AAHcdtxb1x2FD5Ywwf2IYzR3h6sk81mrCkM"
CHANNEL_USERNAME = "tegaratnegar"
REWARD_PER_REFERRAL = 1
REWARD_PER_REFERRAL_GOLD = 2  # پاداش لیگ طلایی
BONUS_FOR_20_REFERRALS = 5
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
    league TEXT DEFAULT 'عادی'
)
""")
conn.commit()

WAITING_FOR_WALLET, SUPPORT_MESSAGE = range(1, 3)

# تابع شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referrer_id = None
    if context.args:
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            referrer_id = None

    # بررسی اینکه کاربر جدید است یا خیر
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

        # اعتبارسنجی دعوت‌شونده و ثبت دعوت
        if referrer_id and referrer_id != user_id:
            try:
                member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
                if member.status in ["member", "administrator", "creator"]:
                    cursor.execute("SELECT referrals, balance, league FROM users WHERE user_id = ?", (referrer_id,))
                    referrer_data = cursor.fetchone()
                    if referrer_data:
                        referrals, balance, league = referrer_data
                        referrals += 1
                        reward = REWARD_PER_REFERRAL_GOLD if league == 'طلایی' else REWARD_PER_REFERRAL
                        balance += reward

                        # ارتقاء به لیگ طلایی
                        if referrals >= 10 and league != 'طلایی':
                            league = 'طلایی'

                        cursor.execute(
                            "UPDATE users SET referrals = ?, balance = ?, league = ? WHERE user_id = ?",
                            (referrals, balance, league, referrer_id)
                        )
                        conn.commit()
            except:
                pass  # خطا در بررسی عضویت کاربر

    # بررسی عضویت کاربر در کانال
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

    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
        [KeyboardButton("💸 برداشت"), KeyboardButton("📊 گزارش وضعیت روز")],
        [KeyboardButton("📞 پشتیبانی"), KeyboardButton("❓ راهنما")]
    ], resize_keyboard=True)
    await update.message.reply_text("✅ خوش آمدید! از دکمه‌های زیر برای استفاده از امکانات ربات استفاده کنید.", reply_markup=keyboard)

# بررسی عضویت کاربر
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
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
    referrals = user_data[0] if user_data else 0
    balance = user_data[1] if user_data else 0
    league = user_data[2] if user_data else 'عادی'
    await update.message.reply_text(f"👤 پروفایل شما:\n\n"
                                    f"🔗 تعداد زیرمجموعه‌ها: {referrals}\n"
                                    f"💰 موجودی دوج‌کوین: {balance} دوج‌کوین\n"
                                    f"🏆 سطح: {league}")

# لینک دعوت
async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    invite_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(f"🔗 لینک دعوت اختصاصی شما:\n\n{invite_link}\n\n"
                                    "هر کاربری که با این لینک وارد شود، به موجودی شما اضافه خواهد شد.")

# درخواست برداشت
async def withdrawal_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    balance = user_data[0] if user_data else 0
    if balance >= MIN_WITHDRAWAL_AMOUNT:
        await update.message.reply_text("💼 لطفاً آدرس ولت دوج‌کوین خود را وارد کنید:")
        return WAITING_FOR_WALLET
    else:
        await update.message.reply_text(f"⛔️ حداقل موجودی برای برداشت {MIN_WITHDRAWAL_AMOUNT} دوج‌کوین است.")
        return ConversationHandler.END

# تایید درخواست برداشت
async def confirm_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = update.message.text
    user_id = update.effective_user.id

    # کاهش موجودی کاربر
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    if balance >= MIN_WITHDRAWAL_AMOUNT:
        new_balance = balance - MIN_WITHDRAWAL_AMOUNT
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        conn.commit()

        await update.message.reply_text(f"✅ درخواست برداشت ثبت شد.\n"
                                        f"آدرس ولت: {wallet_address}\n"
                                        f"💰 برداشت شما به زودی انجام خواهد شد.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⛔️ موجودی کافی نیست.")
    return ConversationHandler.END

# سایر هندلرها
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✉️ لطفاً پیام خود را ارسال کنید.")
    return SUPPORT_MESSAGE

async def receive_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ پیام شما با موفقیت دریافت شد.")
    return ConversationHandler.END

async def help_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ راهنمای استفاده از ربات:\n\n"
                                    "1️⃣ از لینک دعوت برای درآمدزایی استفاده کنید.\n"
                                    "2️⃣ پروفایل خود را بررسی کنید تا موجودی خود را مشاهده کنید.\n"
                                    "3️⃣ با حداقل موجودی 10 دوج‌کوین درخواست برداشت ثبت کنید.\n"
                                    "4️⃣ برای پشتیبانی از بخش پشتیبانی استفاده کنید.")

# تنظیمات هندلرها
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
application.add_handler(MessageHandler(filters.Text("👤 پروفایل"), profile))
application.add_handler(MessageHandler(filters.Text("🔗 لینک دعوت و درآمدزایی"), referral_link))
application.add_handler(MessageHandler(filters.Text("💸 برداشت"), withdrawal_request))
application.add_handler(MessageHandler(filters.Text("📊 گزارش وضعیت روز"), profile))  # استفاده از همان پروفایل برای سادگی
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

application.run_polling()
