from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler
import logging

# تنظیمات ربات
BOT_TOKEN = "7832824273:AAHcdtxb1x2FD5Ywwf2IYzR3h6sk81mrCkM"
CHANNEL_USERNAME = "tegaratnegar"  # نام کانال شما (بدون @)

# راه‌اندازی لاگ‌ها برای پیگیری خطاها
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# اطلاعات کاربر ذخیره‌شده
user_data = {}

# شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # نمایش گزینه‌ها برای عضویت
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✅ تایید عضویت", callback_data="confirm_membership")]
    ])
    
    await update.message.reply_text(
        "⛔️ برای استفاده از ربات ابتدا باید عضو کانال زیر شوید. سپس دکمه تایید عضویت را بزنید:",
        reply_markup=keyboard
    )

# تایید عضویت
async def confirm_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.callback_query.from_user.id

    # استفاده از get_chat_member برای بررسی عضویت کاربر در کانال
    chat_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
    
    if chat_member.status == 'member':  # اگر کاربر عضو کانال بود
        # ارسال پیام تایید عضویت
        await update.callback_query.answer("عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.")
        
        # نمایش کیبورد شیشه‌ای بعد از تایید عضویت
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("👤 پروفایل")]
        ], resize_keyboard=True)
        
        await update.callback_query.edit_message_text(
            "✅ عضویت شما تایید شد! اکنون می‌توانید از ربات استفاده کنید.",
            reply_markup=keyboard
        )
        
        # ارسال پیام تبریک به دعوت‌کننده و افزودن پاداش دوج‌کوین به دعوت‌کننده
        if 'referrer_id' in context.user_data:
            referrer_id = context.user_data['referrer_id']
            # اضافه کردن 1 دوج‌کوین به دعوت‌کننده
            if 'dogecoin' not in user_data.get(referrer_id, {}):
                user_data[referrer_id] = {'dogecoin': 0}  # اگر موجودی نداشت، ایجاد کنیم
            user_data[referrer_id]['dogecoin'] += 1  # افزایش 1 دوج‌کوین
            await context.bot.send_message(referrer_id, "🎉 کاربر شما به ربات پیوست! تبریک می‌گوییم! شما 1 دوج‌کوین پاداش دریافت کردید.")
    else:
        # اگر کاربر هنوز عضو کانال نیست
        await update.callback_query.answer("شما ابتدا باید در کانال عضو شوید.")

# ذخیره ID دعوت‌کننده
async def handle_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if 'referrer_id' not in context.user_data:
        context.user_data['referrer_id'] = user_id  # ذخیره ID دعوت‌کننده
    
    # نمایش پیامی برای شروع عضویت
    await update.message.reply_text(
        "برای استفاده از ربات ابتدا باید عضو کانال شوید و سپس تایید عضویت را بزنید."
    )
    
    # نمایش دکمه‌های عضویت
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✅ تایید عضویت", callback_data="confirm_membership")]
    ])
    
    await update.message.reply_text(
        "⛔️ ابتدا باید در کانال عضو شوید. سپس دکمه تایید عضویت را بزنید:",
        reply_markup=keyboard
    )

# پروفایل و لینک دعوت و درآمدزایی
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    invite_link = f"https://t.me/{context.bot.username}?start={update.effective_user.id}"
    
    # موجودی دوج‌کوین
    dogecoin = user_data.get(user.id, {}).get('dogecoin', 0)

    profile_text = (
        f"🔹 پروفایل شما\n\n"
        f"نام: {user.first_name} {user.last_name if user.last_name else ''}\n"
        f"شناسه کاربری: {user.username if user.username else 'ندارد'}\n"
        f"شناسه کاربری تلگرام: @{user.username}\n"
        f"شناسه کاربری ربات: {user.id}\n\n"
        f"🔗 لینک دعوت شما: {invite_link}\n\n"
        f"💰 موجودی دوج‌کوین شما: {dogecoin} DOGE"
    )
    
    # نمایش کیبورد شیشه‌ای با گزینه‌های پروفایل و درآمدزایی
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("💸 برداشت")]
    ], resize_keyboard=True)
    
    await update.message.reply_text(profile_text, reply_markup=keyboard)

# برداشت دوج‌کوین
async def withdraw_funds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    dogecoin = user_data.get(user_id, {}).get('dogecoin', 0)
    
    if dogecoin >= 10:
        # درخواست آدرس کیف پول
        await update.message.reply_text("💸 برای برداشت دوج‌کوین، لطفاً آدرس کیف پول خود را وارد کنید.")
        # تغییر وضعیت به حالت گرفتن آدرس کیف پول
        context.user_data['awaiting_wallet_address'] = True
    else:
        await update.message.reply_text("💸 برای برداشت، باید حداقل 10 دوج‌کوین داشته باشید.")

# دریافت آدرس کیف پول
async def handle_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # بررسی اینکه کاربر در حال وارد کردن آدرس کیف پول است
    if context.user_data.get('awaiting_wallet_address', False):
        wallet_address = update.message.text
        
        # ذخیره آدرس کیف پول (در واقع اینجا فقط نمایش داده می‌شود)
        context.user_data['wallet_address'] = wallet_address
        
        # ارسال پیام به کاربر
        await update.message.reply_text(f"✅ درخواست شما ثبت شد! به زودی واریز دوج‌کوین به آدرس کیف پول {wallet_address} انجام خواهد شد.")
        
        # ارسال پیام برای تایید به کاربر
        await update.message.reply_text("💸 به زودی دوج‌کوین به کیف پول شما واریز می‌شود.")

        # غیرفعال کردن حالت گرفتن آدرس کیف پول
        context.user_data['awaiting_wallet_address'] = False

# ثبت دستورات
application = Application.builder().token(BOT_TOKEN).build()

# اضافه کردن دستورات
start_handler = CommandHandler("start", start)
application.add_handler(start_handler)

# اضافه کردن دستور ورود از طریق لینک دعوت
application.add_handler(CommandHandler("invite", handle_invite))

# اضافه کردن هنده برای تایید عضویت
confirm_handler = CallbackQueryHandler(confirm_membership, pattern="^confirm_membership$")
application.add_handler(confirm_handler)

# اضافه کردن دستورات پروفایل و برداشت
application.add_handler(MessageHandler(lambda message: message.text == "👤 پروفایل", show_profile))
application.add_handler(MessageHandler(lambda message: message.text == "💸 برداشت", withdraw_funds))

# اضافه کردن هنده برای دریافت آدرس کیف پول
application.add_handler(MessageHandler(lambda message: message.text.startswith("0x") or message.text.startswith("1") or message.text.startswith("3"), handle_wallet_address))

# شروع ربات
application.run_polling()
