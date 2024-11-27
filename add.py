from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler
from telegram.ext import filters
import sqlite3

# تنظیمات ربات
BOT_TOKEN = "7832824273:AAHcdtxb1x2FD5Ywwf2IYzR3h6sk81mrCkM"
CHANNEL_USERNAME = "tegaratnegar"  # نام کانال شما (بدون @)
REWARD_PER_REFERRAL = 1  # پاداش به ازای هر زیرمجموعه
BONUS_FOR_20_REFERRALS = 5  # پاداش برای 20 زیرمجموعه
MIN_WITHDRAWAL_AMOUNT = 10  # حداقل مقدار برای برداشت

# اتصال به پایگاه داده
conn = sqlite3.connect('database.db')

# ایجاد یک cursor برای اجرای دستورات SQL
cursor = conn.cursor()

# حالا می‌توانید دستور SQL را اجرا کنید
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    referrals INTEGER DEFAULT 0,
    balance INTEGER DEFAULT 0,
    is_member INTEGER DEFAULT 0
)
""")

# اعمال تغییرات و بستن اتصال
conn.commit()
conn.close()

# مراحل درخواست برداشت
WAITING_FOR_WALLET = range(1)

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    query = update.message.text

    # بررسی لینک دعوت
    referrer_id = None
    if context.args:
        referrer_id = int(context.args[0])

    # ثبت کاربر در پایگاه داده
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

    # بررسی عضویت در کانال
    try:
        member = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)

        if member.status in ["member", "administrator", "creator"]:
            # اگر عضو شده باشد، تایید عضویت و ارسال پیام خوش‌آمد
            cursor.execute("UPDATE users SET is_member = 1 WHERE user_id = ?", (user_id,))
            conn.commit()

            # نمایش دکمه‌های شیشه‌ای برای لینک دعوت
            if referrer_id:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("عضویت", url=f"https://t.me/{CHANNEL_USERNAME}")],
                    [InlineKeyboardButton("عضو شدم", callback_data=f"check_membership_{user_id}")]
                ])
                await update.message.reply_text("لطفاً یکی از گزینه‌ها را انتخاب کنید:\n\n"
                                                "1. عضویت - برای عضویت در کانال\n"
                                                "2. عضو شدم - برای تایید عضویت خود", reply_markup=keyboard)
            else:
                # اگر کاربر از لینک دعوت نیست، فقط خوش آمدگویی
                keyboard = ReplyKeyboardMarkup([ 
                    [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
                    [KeyboardButton("💸 برداشت")]
                ], resize_keyboard=True)
                await update.message.reply_text("✅ خوش آمدید! از دکمه‌های زیر برای استفاده از امکانات ربات استفاده کنید.", reply_markup=keyboard)

        else:
            # اگر کاربر عضو نشده باشد، ارسال پیام و دکمه‌های عضویت
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("عضویت", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton("عضو شدم", callback_data=f"check_membership_{user_id}")]
            ])
            await update.message.reply_text("⛔️ شما هنوز در کانال عضو نشده‌اید. لطفاً ابتدا عضو شوید.",
                                            reply_markup=keyboard)
            return

    except Exception as e:
        # در صورت بروز هرگونه خطا
        await update.message.reply_text(f"⛔️ مشکلی پیش آمد: {e}")

# نمایش پروفایل کاربر
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

# ارسال لینک دعوت
async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # ارسال لینک دعوت اختصاصی
    invite_link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(f"🔗 لینک دعوت اختصاصی شما:\n\n{invite_link}\n\n"
                                    "هر کاربری که با این لینک وارد شود، 1 دوج‌کوین به موجودی شما اضافه می‌شود.")

# درخواست برداشت
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

# تأیید آدرس ولت برای برداشت
async def confirm_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = update.message.text
    user_id = update.effective_user.id

    # تأیید درخواست برداشت
    await update.message.reply_text(f"✅ درخواست برداشت ثبت شد.\n"
                                    f"آدرس ولت: `{wallet_address}`\n"
                                    f"💰 برداشت شما به زودی انجام خواهد شد.", parse_mode="Markdown")
    return ConversationHandler.END


# تنظیمات اصلی ربات
application = Application.builder().token(BOT_TOKEN).build()

# هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(check_membership, pattern=r"^check_membership_\d+$"))
application.add_handler(MessageHandler(filters.Text("👤 پروفایل"), profile))
application.add_handler(MessageHandler(filters.Text("🔗 لینک دعوت و درآمدزایی"), referral_link))

# هندلر برای بخش برداشت
withdrawal_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Text("💸 برداشت"), withdrawal_request)],
    states={WAITING_FOR_WALLET: [MessageHandler(filters.TEXT, confirm_wallet)]},
    fallbacks=[]
)
application.add_handler(withdrawal_handler)

# اجرای ربات
application.run_polling()
