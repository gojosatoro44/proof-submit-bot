from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ===== CONFIG =====
BOT_TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810

# Users waiting to submit proof
waiting_for_proof = set()

# ===== /start COMMAND =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 SUBMIT PROOF", callback_data="submit_proof")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="cancel")]
    ]

    await update.message.reply_text(
        "**WELCOME 👋**\n\n"
        "**CLICK THE BUTTON BELOW TO SUBMIT YOUR PROOF**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===== BUTTON HANDLER =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "submit_proof":
        waiting_for_proof.add(user_id)
        await query.message.reply_text(
            "**PLEASE SEND YOUR PROOF NOW 📸**\n\n"
            "**YOU CAN SEND IMAGE OR TEXT**",
            parse_mode="Markdown"
        )

    elif query.data == "cancel":
        waiting_for_proof.discard(user_id)
        await query.message.reply_text(
            "**PROCESS CANCELLED ❌**",
            parse_mode="Markdown"
        )

# ===== RECEIVE PROOF =====
async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in waiting_for_proof:
        return

    waiting_for_proof.discard(user_id)

    caption = (
        "**📥 NEW PROOF RECEIVED**\n\n"
        "**USER ID:**\n"
        f"`{user_id}`"
    )

    # Send proof to admin
    if update.message.photo:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=caption,
            parse_mode="Markdown"
        )

    elif update.message.text:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=caption + "\n\n**PROOF TEXT:**\n" + update.message.text,
            parse_mode="Markdown"
        )

    # Confirm to user
    await update.message.reply_text(
        "**✅ YOUR PROOF HAS BEEN SUBMITTED SUCCESSFULLY**",
        parse_mode="Markdown"
    )

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, receive_proof))

    print("Bot is running 24/7...")
    app.run_polling()

if __name__ == "__main__":
    main()
