from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler
from telegram.ext import filters
import sqlite3
from datetime import datetime

# تنظیمات عمومی ربات
BOT_TOKEN = "7832824273:AAHcdtxb1x2FD5Ywwf2IYzR3h6sk81mrCkM"
CHANNEL_USERNAME = "tegaratnegar"
REWARD_PER_REFERRAL = 1
REWARD_PER_REFERRAL_GOLD = 2  # پاداش لیگ طلایی
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

# وضعیت‌ها برای ConversationHandler
WAITING_FOR_WALLET, SUPPORT_MESSAGE = range(2)

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

# تابع شروع ربات
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

            # ذخیره شناسه دعوت‌کننده
            if referrer_id and referrer_id != user_id:
                context.user_data["referrer_id"] = referrer_id

        # بررسی عضویت در کانال
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status not in ["member", "administrator", "creator"]:
            raise Exception("Not a member")
    except Exception:
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}"),
                                          InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership")]])
        await update.message.reply_text("⛔️ برای استفاده از ربات ابتدا باید عضو کانال زیر شوید:", reply_markup=keyboard)
        return

    # نمایش منوی اصلی
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
        [KeyboardButton("💸 برداشت"), KeyboardButton("📊 گزارش وضعیت روز")],
        [KeyboardButton("📞 پشتیبانی"), KeyboardButton("❓ راهنما")]
    ], resize_keyboard=True)
    await update.message.reply_text("✅ خوش آمدید! از دکمه‌های زیر برای استفاده از امکانات ربات استفاده کنید.", reply_markup=keyboard)

# بررسی عضویت و ثبت دعوت
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    referrer_id = context.user_data.get("referrer_id")

    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            await query.message.edit_text("✅ عضویت شما تأیید شد! حالا می‌توانید از ربات استفاده کنید.")

            # ثبت دعوت پس از تأیید عضویت
            if referrer_id:
                await register_referral(user_id, referrer_id)

            # نمایش منوی اصلی
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

# ارسال لینک دعوت
async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        invite_link = f"https://t.me/{context.bot.username}?start={user_id}"
        await update.message.reply_text(f"🔗 لینک دعوت اختصاصی شما:\n\n{invite_link}\n\n"
                                        "هر کاربری که با این لینک وارد شود، به موجودی شما اضافه خواهد شد.")
    except Exception as e:
        print(f"خطا در ایجاد لینک دعوت: {e}")
        await update.message.reply_text("⛔️ خطایی رخ داده است.")

# پروفایل کاربر
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

# تنظیم هندلرها
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
application.add_handler(MessageHandler(filters.Text("🔗 لینک دعوت و درآمدزایی"), referral_link))
application.add_handler(MessageHandler(filters.Text("👤 پروفایل"), profile))
application.add_handler(MessageHandler(filters.Text("📞 پشتیبانی"), support))
application.add_handler(MessageHandler(filters.Text("❓ راهنما"), help_section))

conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Text("📞 پشتیبانی"), support)],
    states={
        SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_message)],
    },
    fallbacks=[],
)
application.add_handler(conv_handler)

application.run_polling()
