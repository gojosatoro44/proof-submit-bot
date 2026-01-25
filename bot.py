import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)

BOT_TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810
CHANNEL = "@TaskByZahid"
CHANNEL_LINK = "https://t.me/TaskByZahid"

logging.basicConfig(level=logging.INFO)

# ===== STORAGE =====
users = {}
payment_methods = {}

# ===== STATES =====
PROOF_PHOTO, PROOF_LINK = range(2)
PM_DETAIL = range(1)

# ===== HELPERS =====
def user(uid):
    users.setdefault(uid, {"balance": 0})

async def joined(bot, uid):
    try:
        m = await bot.get_chat_member(CHANNEL, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ===== KEYBOARDS =====
MAIN_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📤 Submit Proof", callback_data="proof"),
        InlineKeyboardButton("💰 Balance", callback_data="balance")
    ],
    [
        InlineKeyboardButton("🔥 Withdraw", callback_data="withdraw"),
        InlineKeyboardButton("🤯 Payment Method", callback_data="pm")
    ]
])

JOIN_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Join Channel", url=CHANNEL_LINK)],
    [InlineKeyboardButton("🔄 I Joined", callback_data="check")]
])

PM_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("UPI", callback_data="upi"),
        InlineKeyboardButton("VSV", callback_data="vsv"),
        InlineKeyboardButton("FXL", callback_data="fxl")
    ]
])

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await joined(context.bot, uid):
        await update.message.reply_text(
            "🔒 Join channel to use bot",
            reply_markup=JOIN_KB
        )
        return
    user(uid)
    await update.message.reply_text("Choose option 👇", reply_markup=MAIN_KB)

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await joined(context.bot, q.from_user.id):
        await q.message.delete()
        await context.bot.send_message(q.from_user.id, "✅ Access granted", reply_markup=MAIN_KB)
    else:
        await q.answer("Join first", show_alert=True)

# ===== CALLBACKS =====
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    user(uid)

    if q.data == "balance":
        await context.bot.send_message(uid, f"💰 Balance: ₹{users[uid]['balance']}")

    elif q.data == "proof":
        await context.bot.send_message(uid, "📸 Send screenshot (refer link visible)")
        return PROOF_PHOTO

    elif q.data == "pm":
        await context.bot.send_message(uid, "Choose payment method 👇", reply_markup=PM_KB)

    elif q.data in ["upi", "vsv", "fxl"]:
        context.user_data["pm_type"] = q.data
        await context.bot.send_message(uid, "✍️ Send payment details now")
        return PM_DETAIL

    elif q.data == "withdraw":
        if uid not in payment_methods:
            await context.bot.send_message(uid, "❌ Add payment method first")
            return
        await context.bot.send_message(uid, "Withdraw feature coming soon")

# ===== PROOF FLOW =====
async def proof_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Now send your refer link")
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    link = update.message.text

    await context.bot.send_photo(
        ADMIN_ID,
        context.user_data["photo"],
        caption=f"🆕 PROOF\n👤 {uid}\n🔗 {link}"
    )

    await update.message.reply_text("✅ Proof submitted")
    context.user_data.clear()
    return ConversationHandler.END

# ===== PAYMENT METHOD FLOW =====
async def save_pm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    payment_methods[uid] = {
        "type": context.user_data["pm_type"],
        "detail": update.message.text
    }
    context.user_data.clear()
    await update.message.reply_text("✅ Payment method saved")
    return ConversationHandler.END

# ===== CANCEL =====
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    return ConversationHandler.END

# ===== APP =====
app = ApplicationBuilder().token(BOT_TOKEN).build()

conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(menu)],
    states={
        PROOF_PHOTO: [MessageHandler(filters.PHOTO, proof_photo)],
        PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_link)],
        PM_DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_pm)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_user=True,
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(check_join, pattern="check"))
app.add_handler(conv)

print("✅ BOT RUNNING — FIRST RESPONSE GUARANTEED")
app.run_polling()
