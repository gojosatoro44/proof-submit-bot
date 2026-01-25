from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 123456789  # replace with your Telegram ID
FORCE_JOIN_CHANNEL = "http://t.me/TaskByZahid"

# States
WAIT_SCREENSHOT, WAIT_REFER, WAIT_PAYMENT_METHOD = range(3)

# Temporary in-memory storage
user_data_temp = {}

# User balances
user_balance = {}

# Keyboards
main_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📨 Submit Proof", callback_data="submit_proof")],
    [InlineKeyboardButton("💰 Balance", callback_data="balance"),
     InlineKeyboardButton("🔥 Withdraw", callback_data="withdraw")],
    [InlineKeyboardButton("🤯 Payment Method", callback_data="payment_method")]
])

force_join_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Join Channel", url=FORCE_JOIN_CHANNEL)]
])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Force join check placeholder
    await update.message.reply_text(
        f"Welcome! Please join our channel to use the bot.\n{FORCE_JOIN_CHANNEL}",
        reply_markup=force_join_keyboard
    )

    await update.message.reply_text("Use the buttons below 👇", reply_markup=main_keyboard)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "submit_proof":
        await query.message.reply_text("📸 Send screenshot (refer link visible)")
        return WAIT_SCREENSHOT

    elif query.data == "balance":
        balance = user_balance.get(user_id, 0)
        await query.message.reply_text(f"💰 Your Balance: ₹{balance}")
        return ConversationHandler.END

    elif query.data == "withdraw":
        balance = user_balance.get(user_id, 0)
        if balance <= 0:
            await query.message.reply_text("❌ Your balance is 0, cannot withdraw")
        else:
            await query.message.reply_text("💵 Withdraw function placeholder")
        return ConversationHandler.END

    elif query.data == "payment_method":
        await query.message.reply_text(
            "✍️ Send your payment details now"
        )
        return WAIT_PAYMENT_METHOD


# Proof Flow
async def proof_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data_temp[user_id] = {}
    user_data_temp[user_id]['screenshot'] = update.message.photo[-1].file_id if update.message.photo else update.message.text
    await update.message.reply_text("🔗 Now send your refer link")
    return WAIT_REFER


async def proof_refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    refer_link = update.message.text
    user_data_temp[user_id]['refer_link'] = refer_link

    # Send to admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🆕 PROOF\n👤 User ID: `{user_id}`\n🔗 Refer Link: {refer_link}",
        parse_mode="Markdown"
    )

    await update.message.reply_text("✅ Proof submitted")
    return ConversationHandler.END


# Payment Method Flow
async def payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_balance.setdefault(user_id, 0)
    payment_info = update.message.text
    user_data_temp[user_id] = user_data_temp.get(user_id, {})
    user_data_temp[user_id]['payment_method'] = payment_info

    await update.message.reply_text("✅ Payment method saved")
    return ConversationHandler.END


# Cancel any conversation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action cancelled")
    return ConversationHandler.END


app = ApplicationBuilder().token(TOKEN).build()

# Main ConversationHandler
conv_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: None)],
    states={
        WAIT_SCREENSHOT: [MessageHandler(filters.PHOTO | filters.TEXT, proof_screenshot)],
        WAIT_REFER: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_refer)],
        WAIT_PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_method)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

# Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
app.add_handler(MessageHandler(filters.PHOTO, proof_screenshot))

print("Bot running...")
app.run_polling()
