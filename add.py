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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS join_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT NOT NULL
        )
    """)
    conn.commit()
except sqlite3.Error as e:
    print(f"خطا در اتصال به پایگاه داده: {e}")

# اتصال به دیتابیس
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS join_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT NOT NULL
)
""")
conn.commit()


# تابع شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referrer_id = None

    # بررسی لینک دعوت
    if context.args:
        try:
            referrer_id = int(context.args[0])
        except ValueError:
            pass

    # ثبت کاربر جدید
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

        if referrer_id and referrer_id != user_id:
            context.user_data["referrer_id"] = referrer_id

    # ایجاد دکمه‌ها
    buttons = [
        [KeyboardButton("🔗 لینک دعوت و درآمدزایی"), KeyboardButton("👤 پروفایل")],
        [KeyboardButton("💸 برداشت"), KeyboardButton("📞 پشتیبانی")],
        [KeyboardButton("❓ راهنما")]
    ]

    if user_id in ADMIN_IDS:
        buttons.append([KeyboardButton("📢 ارسال پیام همگانی"), KeyboardButton("📊 بخش آمار")])
        buttons.append([KeyboardButton("⚙️ تنظیم لینک‌ها"), KeyboardButton("🔗 مشاهده لینک‌ها")])
        buttons.append([KeyboardButton("🗑 حذف لینک‌ها")])

    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text("✅ از دکمه‌های زیر استفاده کنید:", reply_markup=reply_markup)

    # بررسی لینک‌های عضویت
    join_links = get_join_links()  # دریافت لینک‌ها از جدول
    if join_links:
        keyboard_buttons = [
            [InlineKeyboardButton(f"📢 عضویت در کانال {i + 1}", url=link)] for i, link in enumerate(join_links)
    ]
    keyboard_buttons.append([InlineKeyboardButton("✅ تایید عضویت", callback_data="check_membership")])

    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    await update.message.reply_text(
        "⛔️ برای استفاده از امکانات پیشرفته ربات ابتدا باید عضو کانال‌های زیر شوید:",
        reply_markup=keyboard
    )


# بررسی عضویت
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    join_links = get_join_links()
    if not join_links:
        await query.answer("⛔️ لینک‌های عضویت تنظیم نشده‌اند!", show_alert=True)
        return

    for link in join_links:
        # استخراج یوزرنیم کانال از لینک
        channel_username = link.split("/")[-1]
        try:
            member = await context.bot.get_chat_member(chat_id=f"@{channel_username}", user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                await query.answer("⛔️ لطفاً ابتدا عضو کانال‌ها شوید.", show_alert=True)
                return
        except Exception as e:
            print(f"خطا در بررسی عضویت: {e}")
            await query.answer("⛔️ مشکلی در بررسی عضویت وجود دارد.", show_alert=True)
            return

    await query.message.edit_text("✅ عضویت شما تأیید شد!")


# مدیریت لینک‌ها توسط ادمین
async def manage_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔️ شما اجازه دسترسی به این بخش را ندارید.")
        return

    links = get_join_links()
    if links:
        links_text = "\n".join([f"🔗 {link}" for link in links])
        await update.message.reply_text(f"📃 لینک‌های تنظیم‌شده:\n{links_text}")
    else:
        await update.message.reply_text("⛔️ هیچ لینکی تنظیم نشده است.")


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

    if not context.user_data.get("is_verified"):
        await update.message.reply_text("⛔️ لطفاً ابتدا عضویت خود را تأیید کنید.")
        return

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

    if not context.user_data.get("is_verified"):
        await update.message.reply_text("⛔️ لطفاً ابتدا عضویت خود را تأیید کنید.")
        return

# راهنما
async def help_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ راهنمای استفاده از ربات:\n\n"
                                    "1️⃣ از لینک دعوت برای درآمدزایی استفاده کنید.\n"
                                    "2️⃣ پروفایل خود را بررسی کنید.\n"
                                    "3️⃣ درخواست برداشت ثبت کنید.\n"
                                    "4️⃣ برای پشتیبانی پیام ارسال کنید.")

# مراحل مکالمه
ASK_MESSAGE, CONFIRM_SEND = range(2)
SET_LINK_COUNT, ADD_LINKS = range(2)

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

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # بررسی اینکه آیا کاربر ادمین است
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔️ شما اجازه دسترسی به این بخش را ندارید.")
        return

    try:
        # شمارش تعداد کاربران
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        # ارسال آمار به ادمین
        await update.message.reply_text(
            f"📊 آمار ربات:\n\n👥 تعداد کاربران ثبت‌شده: {user_count} نفر"
        )
    except Exception as e:
        logger.error(f"خطا در دریافت آمار: {e}")
        await update.message.reply_text("❌ خطایی در دریافت آمار رخ داد.")

# شروع ثبت لینک
async def start_add_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔️ شما اجازه دسترسی به این بخش را ندارید.")
        return

    await update.message.reply_text(
        "🔗 لطفاً لینک‌های مورد نظر خود را یکی‌یکی ارسال کنید.\n"
        "📌 وقتی تمام لینک‌ها را اضافه کردید، دستور `/done` را ارسال کنید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ برگشت به منو", callback_data="admin_menu")]
        ])
    )
    return ADD_LINKS


# ثبت لینک‌ها
async def add_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    if not link.startswith("http"):
        await update.message.reply_text("⛔️ لطفاً یک لینک معتبر ارسال کنید.")
        return ADD_LINKS

    cursor.execute("INSERT INTO join_links (link) VALUES (?)", (link,))
    conn.commit()
    await update.message.reply_text(f"✅ لینک اضافه شد: {link}")
    return ADD_LINKS


# مشاهده لینک‌ها
async def view_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔️ شما اجازه دسترسی به این بخش را ندارید.")
        return

    cursor.execute("SELECT * FROM join_links")
    links = cursor.fetchall()
    if not links:
        await update.message.reply_text("⛔️ هیچ لینکی ثبت نشده است.")
        return

    links_text = "\n".join([f"{i + 1}. {link[1]}" for i, link in enumerate(links)])
    await update.message.reply_text(
        f"📃 لینک‌های ثبت‌شده:\n\n{links_text}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ برگشت به منو", callback_data="admin_menu")]
        ])
    )


# شروع حذف لینک‌ها
async def start_delete_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔️ شما اجازه دسترسی به این بخش را ندارید.")
        return

    cursor.execute("SELECT * FROM join_links")
    links = cursor.fetchall()
    if not links:
        await update.message.reply_text("⛔️ هیچ لینکی برای حذف وجود ندارد.")
        return

    keyboard_buttons = [
        [InlineKeyboardButton(f"🗑 حذف {link[1]}", callback_data=f"delete_link:{link[0]}")]
        for link in links
    ]
    keyboard_buttons.append([InlineKeyboardButton("↩️ برگشت به منو", callback_data="admin_menu")])

    await update.message.reply_text(
        "🗑 برای حذف لینک، یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard_buttons)
    )
    return DELETE_LINKS


# حذف لینک‌ها
async def delete_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split(":")
    if data[0] == "delete_link":
        link_id = int(data[1])
        cursor.execute("DELETE FROM join_links WHERE id = ?", (link_id,))
        conn.commit()
        await query.message.edit_text(
            "✅ لینک حذف شد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ برگشت به منو", callback_data="admin_menu")]
            ])
        )


# منوی ادمین
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.edit_text(
        "⚙️ منوی مدیریت:\n\n"
        "🔗 ثبت لینک‌های عضویت اجباری\n"
        "🔍 مشاهده لینک‌های تنظیم‌شده\n"
        "🗑 حذف لینک‌های ثبت‌شده",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ ثبت لینک", callback_data="add_links")],
            [InlineKeyboardButton("🔗 مشاهده لینک‌ها", callback_data="view_links")],
            [InlineKeyboardButton("🗑 حذف لینک‌ها", callback_data="delete_links")]
        ])
    )

# تنظیمات اصلی ربات
application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(ConversationHandler(
    entry_points=[CallbackQueryHandler(start_add_links, pattern="add_links")],
    states={
        ADD_LINKS: [CommandHandler("done", admin_menu), CallbackQueryHandler(admin_menu, pattern="admin_menu"),
                    CommandHandler("cancel", admin_menu), MessageHandler(filters.TEXT & ~filters.COMMAND, add_links)],
    },
    fallbacks=[CallbackQueryHandler(admin_menu, pattern="admin_menu")]
))

# افزودن هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.Text("🔗 لینک دعوت و درآمدزایی"), referral_link))
application.add_handler(MessageHandler(filters.Text("👤 پروفایل"), profile))
application.add_handler(MessageHandler(filters.Text("💸 برداشت"), withdrawal_request))
application.add_handler(MessageHandler(filters.Text("📞 پشتیبانی"), support))
application.add_handler(MessageHandler(filters.Text("❓ راهنما"), help_section))
application.add_handler(CallbackQueryHandler(check_membership, pattern="check_membership"))
application.add_handler(MessageHandler(filters.Text("📊 بخش آمار") & filters.User(ADMIN_IDS), show_stats))
application.add_handler(CallbackQueryHandler(view_links, pattern="view_links"))
application.add_handler(CallbackQueryHandler(start_delete_links, pattern="delete_links"))
application.add_handler(CallbackQueryHandler(delete_links, pattern="delete_link:*"))
application.add_handler(CallbackQueryHandler(admin_menu, pattern="admin_menu"))

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
