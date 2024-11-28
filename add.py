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
try:
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
except sqlite3.Error as e:
    print(f"خطا در اتصال به پایگاه داده: {e}")

WAITING_FOR_WALLET, SUPPORT_MESSAGE = range(1, 3)

# تابع ثبت دعوت و ارسال پیام تبریک
async def register_referral(user_id, referrer_id):
    try:
        cursor.execute("SELECT referrals, balance, league FROM users WHERE user_id = ?", (referrer_id,))
        referrer_data = cursor.fetchone()
        if not referrer_data:
            return False  # دعوت‌کننده نامعتبر است

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

        # ارسال پیام تبریک
        await application.bot.send_message(
            chat_id=referrer_id,
            text=f"🎉 تبریک! یک زیرمجموعه جدید به لیست شما اضافه شد.\n"
                 f"🔗 تعداد زیرمجموعه‌های شما: {referrals}\n"
                 f"💰 موجودی شما: {balance} دوج‌کوین"
        )
        return True
    except Exception as e:
        print(f"خطا در ثبت دعوت: {e}")
        return False

# تابع شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referrer_id = None
    if context.args:
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            referrer_id = None

    try:
        # ثبت کاربر جدید
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            conn.commit()

            # ثبت دعوت در صورت نیاز
            if referrer_id and referrer_id != user_id:
                member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
                if member.status in ["member", "administrator", "creator"]:
                    await register_referral(user_id, referrer_id)

        # بررسی عضویت در کانال
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not a member")
    except Exception:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}"),
                                          InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]])
        await update.message.reply_text("⛔️ برای استفاده از ربات ابتدا باید عضو کانال زیر شوید:", reply_markup=keyboard)
        return

    # منوی اصلی
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
        [KeyboardButton("💸 برداشت"), KeyboardButton("📊 گزارش وضعیت روز")],
        [KeyboardButton("📞 پشتیبانی"), KeyboardButton("❓ راهنما")]
    ], resize_keyboard=True)
    await update.message.reply_text("✅ خوش آمدید! از دکمه‌های زیر برای استفاده از امکانات ربات استفاده کنید.", reply_markup=keyboard)

# بررسی عضویت
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            await query.message.edit_text("✅ عضویت شما تأیید شد! حالا می‌توانید از ربات استفاده کنید.")
        else:
            await query.answer("⛔️ هنوز عضو کانال نشده‌اید!", show_alert=True)
    except Exception as e:
        print(f"خطا در بررسی عضویت: {e}")
        await query.answer("⛔️ خطا در بررسی عضویت!", show_alert=True)

# پروفایل
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
            await update.message.reply_text("⛔️ اطلاعاتی یافت نشد.")
    except Exception as e:
        print(f"خطا در نمایش پروفایل: {e}")
        await update.message.reply_text("⛔️ خطایی رخ داده است.")

# لینک دعوت
async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        invite_link = f"https://t.me/{context.bot.username}?start={user_id}"
        await update.message.reply_text(f"🔗 لینک دعوت اختصاصی شما:\n\n{invite_link}\n\n"
                                        "هر کاربری که با این لینک وارد شود، به موجودی شما اضافه خواهد شد.")
    except Exception as e:
        print(f"خطا در ایجاد لینک دعوت: {e}")
        await update.message.reply_text("⛔️ خطایی رخ داده است.")

# درخواست برداشت
async def withdrawal_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        if user_data and user_data[0] >= MIN_WITHDRAWAL_AMOUNT:
            await update.message.reply_text("💼 لطفاً آدرس ولت دوج‌کوین خود را وارد کنید:")
            return WAITING_FOR_WALLET
        else:
            await update.message.reply_text(f"⛔️ حداقل موجودی برای برداشت {MIN_WITHDRAWAL_AMOUNT} دوج‌کوین است.")
            return ConversationHandler.END
    except Exception as e:
        print(f"خطا در درخواست برداشت: {e}")
        await update.message.reply_text("⛔️ خطایی رخ داده است.")
        return ConversationHandler.END

# تایید برداشت
async def confirm_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        print(f"خطا در تایید برداشت: {e}")
        await update.message.reply_text("⛔️ خطایی رخ داده است.")
    return ConversationHandler.END

# پشتیبانی
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✉️ لطفاً پیام خود را ارسال کنید.")
    return SUPPORT_MESSAGE

async def receive_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_message = update.message.text
        user_id = update.effective_user.id
        await application.bot.send_message(
            chat_id=YOUR_ADMIN_ID,  # شناسه مدیر
            text=f"پیام جدید از {user_id}:\n\n{user_message}"
        )
        await update.message.reply_text("✅ پیام شما با موفقیت دریافت شد و به زودی بررسی خواهد شد.")
    except Exception as e:
        print(f"خطا در دریافت پیام پشتیبانی: {e}")
        await update.message.reply_text("⛔️ خطایی رخ داده است.")
    return ConversationHandler.END

# راهنما
async def help_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ راهنمای استفاده از ربات:\n\n"
                                    "1️⃣ از لینک دعوت برای درآمدزایی استفاده کنید.\n"
                                    "2️⃣ پروفایل خود را بررسی کنید.\n"
                                    "3️⃣ درخواست برداشت ثبت کنید.\n"
                                    "4️⃣ برای پشتیبانی پیام ارسال کنید.")

# تنظیمات هندلرها
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
application.add_handler(MessageHandler(filters.Text("👤 پروفایل"), profile))
application.add_handler(MessageHandler(filters.Text("🔗 لینک دعوت و درآمدزایی"), referral_link))
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

application.run_polling()
