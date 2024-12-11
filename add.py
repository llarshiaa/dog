from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler
from telegram.ext import filters
import sqlite3

# تنظیمات عمومی
BOT_TOKEN = "7832824273:AAHcdtxb1x2FD5Ywwf2IYzR3h6sk81mrCkM"
CHANNEL_USERNAME_1 = "tegaratnegar"  # کانال اول
CHANNEL_USERNAME_2 = "dollor_ir"     # کانال دوم
REWARD_PER_REFERRAL = 1
MIN_WITHDRAWAL_AMOUNT = 10
WAITING_FOR_WALLET = range(1)  # وضعیت انتظار آدرس ولت
ADMIN_IDS = [5102021224]  # شناسه تلگرام ادمین‌ها

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

# تابع شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referrer_id = None

    # بررسی اگر لینک دعوت استفاده شده باشد
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

        # ذخیره referrer_id
        if referrer_id and referrer_id != user_id:
            context.user_data["referrer_id"] = referrer_id

    # نمایش کیبورد عضویت
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال اول", url=f"https://t.me/{CHANNEL_USERNAME_1}")],
        [InlineKeyboardButton("📢 عضویت در کانال دوم", url=f"https://t.me/{CHANNEL_USERNAME_2}")],
        [InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership")]
    ])
    await update.message.reply_text(
        "⛔️ برای استفاده از ربات ابتدا باید عضو کانال‌های زیر شوید:",
        reply_markup=keyboard
    )

# بررسی عضویت در هر دو کانال
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    referrer_id = context.user_data.get("referrer_id")

    try:
        # بررسی عضویت در کانال اول
        member_1 = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME_1}", user_id=user_id)
        # بررسی عضویت در کانال دوم
        member_2 = await context.bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME_2}", user_id=user_id)

        if member_1.status in ["member", "administrator", "creator"] and member_2.status in ["member", "administrator", "creator"]:
            await query.message.edit_text("✅ عضویت شما تأیید شد! حالا می‌توانید از ربات استفاده کنید.")

            # ثبت زیرمجموعه
            if referrer_id:
                await register_referral(user_id, referrer_id)

            # نمایش کیبورد اصلی
            keyboard = ReplyKeyboardMarkup([
                [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
                [KeyboardButton("💸 برداشت"), KeyboardButton("📊 گزارش وضعیت روز")],
                [KeyboardButton("📞 پشتیبانی"), KeyboardButton("❓ راهنما")]
            ], resize_keyboard=True)
            await query.message.reply_text("✅ از دکمه‌های زیر برای استفاده از امکانات ربات استفاده کنید.", reply_markup=keyboard)
        else:
            await query.answer("⛔️ لطفاً ابتدا عضو هر دو کانال شوید!", show_alert=True)
    except Exception as e:
        print(f"خطا در بررسی عضویت: {e}")
        await query.answer("⛔️ خطا در بررسی عضویت!", show_alert=True)

            # اضافه کردن دکمه ادمین اگر کاربر ادمین باشد
        if user_id in ADMIN_IDS:
                buttons.append([KeyboardButton("📢 ارسال پیام همگانی")])

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

# درخواست لینک دعوت
async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = context.bot.username

    invite_link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(
        f"🔗 لینک دعوت اختصاصی شما:\n\n{invite_link}\n\n"
        "هر کاربری که با این لینک عضو شود، به موجودی شما دوج‌کوین اضافه می‌شود!"
    )

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

# تایید آدرس ولت
async def confirm_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = update.message.text
    user_id = update.effective_user.id

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    balance = result[0] if result else 0

    if balance >= MIN_WITHDRAWAL_AMOUNT:
        new_balance = balance - MIN_WITHDRAWAL_AMOUNT
        cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        conn.commit()

        await update.message.reply_text(f"✅ درخواست برداشت ثبت شد.\n"
                                        f"آدرس ولت: {wallet_address}\n"
                                        f"💰 موجودی فعلی: {new_balance} دوج‌کوین.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("⛔️ موجودی کافی نیست.")
        return ConversationHandler.END


# پشتیبانی
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📞 برای پشتیبانی پیام خود را ارسال کنید. مدیران به زودی پاسخ خواهند داد.")

# راهنما
async def help_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ راهنمای استفاده از ربات:\n\n"
                                    "1️⃣ از لینک دعوت برای درآمدزایی استفاده کنید.\n"
                                    "2️⃣ پروفایل خود را بررسی کنید.\n"
                                    "3️⃣ درخواست برداشت ثبت کنید.\n"
                                    "4️⃣ برای پشتیبانی پیام ارسال کنید.")

# مراحل مکالمه
ASK_MESSAGE, CONFIRM_SEND = range(2)

# شروع مکالمه برای ارسال پیام همگانی
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔️ شما اجازه این عملیات را ندارید.")
        return ConversationHandler.END

    await update.message.reply_text(
        "📢 لطفاً پیام همگانی خود را ارسال کنید:"
    )
    return ASK_MESSAGE

# دریافت پیام از ادمین
async def ask_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["broadcast_message"] = update.message.text

    await update.message.reply_text(
        f"پیام شما:\n\n{context.user_data['broadcast_message']}\n\nآیا این پیام را برای همه ارسال کنم؟",
        reply_markup=ReplyKeyboardMarkup(
            [["✅ بله", "❌ خیر"]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    return CONFIRM_SEND

# تایید و ارسال پیام
async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "✅ بله":
        message = context.user_data.get("broadcast_message")

        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        success_count = 0
        for user in users:
            try:
                await context.bot.send_message(chat_id=user[0], text=message)
                success_count += 1
            except Exception as e:
                logger.error(f"خطا در ارسال پیام به {user[0]}: {e}")

        await update.message.reply_text(f"✅ پیام شما به {success_count} کاربر ارسال شد.")
    else:
        await update.message.reply_text("❌ ارسال پیام لغو شد.")

    return ConversationHandler.END

# لغو عملیات
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 عملیات لغو شد.")
    return ConversationHandler.END


# تنظیمات اصلی ربات
application = Application.builder().token(BOT_TOKEN).build()

    # هندلرهای ارسال پیام همگانی
application.add_handler(
    ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("📢 ارسال پیام همگانی"), start_broadcast)
        ],  # شروع مکالمه
        states={
            # مرحله دریافت پیام از ادمین
            ASK_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_message)
            ],
            # مرحله تایید نهایی برای ارسال پیام
            CONFIRM_SEND: [
                MessageHandler(filters.Regex("✅ بله|❌ خیر"), confirm_send)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_broadcast)
        ],  # گزینه لغو
    )
)

# افزودن هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.Text("🔗 لینک دعوت و درآمدزایی"), referral_link))
application.add_handler(MessageHandler(filters.Text("👤 پروفایل"), profile))
application.add_handler(MessageHandler(filters.Text("💸 برداشت"), withdrawal_request))
application.add_handler(MessageHandler(filters.Text("📞 پشتیبانی"), support))
application.add_handler(MessageHandler(filters.Text("❓ راهنما"), help_section))
application.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))

# هندلر مکالمه
conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Text("💸 برداشت"), withdrawal_request)],
    states={WAITING_FOR_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_wallet)]},
    fallbacks=[],
)
application.add_handler(conv_handler)

if __name__ == "__main__":
    print("🚀 ربات اجرا شد.")
    application.run_polling()
