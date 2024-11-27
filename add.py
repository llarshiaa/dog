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
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    referrals INTEGER DEFAULT 0,
    balance INTEGER DEFAULT 0,
    username TEXT DEFAULT ''
)
""")
conn.commit()

# مراحل درخواست برداشت
WAITING_FOR_WALLET = range(1)

# شروع ربات
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

        # اگر کاربر با لینک دعوت وارد شده
        if referrer_id and referrer_id != user_id:
            cursor.execute("SELECT referrals FROM users WHERE user_id = ?", (referrer_id,))
            ref_data = cursor.fetchone()
            if ref_data:
                referrals = ref_data[0] + 1
                cursor.execute("UPDATE users SET referrals = ? WHERE user_id = ?", (referrals, referrer_id))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                               (REWARD_PER_REFERRAL, referrer_id))
                conn.commit()

                # ارسال پیام تبریک به معرف
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎉 زیرمجموعه جدید اضافه شد! موجودی شما: {REWARD_PER_REFERRAL} دوج‌کوین افزایش یافت."
                )
                if referrals == 20:  # بررسی پاداش 20 زیرمجموعه
                    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                                   (BONUS_FOR_20_REFERRALS, referrer_id))
                    conn.commit()
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text="🎁 تبریک! شما به 20 زیرمجموعه رسیدید و 5 دوج‌کوین هدیه گرفتید."
                    )

    # نمایش گزینه‌های عضویت
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✅ تایید عضویت", callback_data="confirm_membership")],
        [InlineKeyboardButton("👤 پروفایل", callback_data="profile")],
        [InlineKeyboardButton("🔗 لینک دعوت", callback_data="referral_link")]
    ])
    await update.message.reply_text(
        "⛔️ برای استفاده از ربات ابتدا باید عضو کانال زیر شوید. پس از عضویت، لطفاً دکمه تایید عضویت را بزنید:",
        reply_markup=keyboard
    )


async def confirm_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id

    # ثبت و تایید عضویت
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        await update.callback_query.answer("عضویت شما تایید شد. موفق باشید!")
        await update.callback_query.edit_message_text(
            "✅ عضویت شما تایید شد! اکنون می‌توانید از ربات استفاده کنید."
        )
    else:
        await update.callback_query.answer("شما ابتدا باید در کانال عضو شوید.")
    
    await update.callback_query.edit_message_text(
        "✅ عضویت شما تایید شد! اکنون می‌توانید از ربات استفاده کنید."
    )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    cursor.execute("SELECT referrals, balance FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        referrals, balance = user_data
        profile_text = f"👤 پروفایل شما:\n\n" \
                       f"💸 موجودی: {balance} دوج‌کوین\n" \
                       f"👥 زیرمجموعه‌ها: {referrals}\n" \
                       f"🔗 لینک دعوت شما: https://t.me/{context.bot.username}?start={user_id}"

        await update.callback_query.edit_message_text(profile_text)
    else:
        await update.callback_query.answer("شما هنوز ثبت‌نام نکرده‌اید.")

async def referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id
    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"

    await update.callback_query.edit_message_text(f"🔗 لینک دعوت شما: {referral_link}")


async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user_balance = cursor.fetchone()
    
    if user_balance and user_balance[0] >= MIN_WITHDRAWAL_AMOUNT:
        await update.message.reply_text("لطفاً آدرس کیف پول خود را وارد کنید:")
        return WAITING_FOR_WALLET
    else:
        await update.message.reply_text("برای برداشت باید حداقل مبلغ 10 دوج‌کوین داشته باشید.")
        return ConversationHandler.END

async def wallet_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet_address = update.message.text

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user_balance = cursor.fetchone()
    
    if user_balance and user_balance[0] >= MIN_WITHDRAWAL_AMOUNT:
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", 
                       (MIN_WITHDRAWAL_AMOUNT, user_id))
        conn.commit()
        await update.message.reply_text(f"برداشت موفقیت‌آمیز! مبلغ {MIN_WITHDRAWAL_AMOUNT} دوج‌کوین به آدرس {wallet_address} ارسال شد.")
    else:
        await update.message.reply_text("موجودی شما کافی نیست.")
    
    return ConversationHandler.END


# ثبت دستورات و وضعیت‌ها
application = Application.builder().token(BOT_TOKEN).build()

start_handler = CommandHandler("start", start)
application.add_handler(start_handler)

confirm_handler = CallbackQueryHandler(confirm_membership, pattern="^confirm_membership$")
application.add_handler(confirm_handler)

profile_handler = CallbackQueryHandler(profile, pattern="^profile$")
application.add_handler(profile_handler)

referral_link_handler = CallbackQueryHandler(referral_link, pattern="^referral_link$")
application.add_handler(referral_link_handler)

withdraw_handler = CommandHandler("withdraw", withdraw)
application.add_handler(withdraw_handler)

wallet_received_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_received)
application.add_handler(wallet_received_handler)

# راه‌اندازی ربات
application.run_polling()
