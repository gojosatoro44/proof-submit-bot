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
    ConversationHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810
CHANNEL_USERNAME = "@TaskByZahid"
CHANNEL_LINK = "https://t.me/TaskByZahid"

SUBMIT_PROOF, PAYMENT_METHOD, WITHDRAW = range(3)

user_payment_methods = {}

# ---------------- FORCE JOIN CHECK ----------------
async def is_joined(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


async def force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✅ Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("🔄 I've Joined", callback_data="check_join")]
    ]
    await update.message.reply_text(
        "🚫 **Access Blocked**\n\n"
        "You must join our channel to use this bot.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await is_joined(context.bot, query.from_user.id):
        await query.message.edit_text(
            "✅ **Verified!**\n\nWelcome to the bot 🎉",
            parse_mode="Markdown"
        )
        await start_menu(query.message)
    else:
        await query.answer("❌ You haven't joined yet!", show_alert=True)


# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_joined(context.bot, update.effective_user.id):
        return await force_join(update, context)

    await start_menu(update.message)


async def start_menu(message):
    keyboard = [
        [InlineKeyboardButton("📤 Submit Proof", callback_data="submit_proof")],
        [InlineKeyboardButton("💳 Payment Method", callback_data="payment")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
    ]

    if message.from_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🛠 Admin Panel", callback_data="admin")])

    await message.reply_text(
        "👋 **Welcome!**\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# ---------------- SUBMIT PROOF ----------------
async def proof_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📸 Send your **screenshot proof** now.")
    return SUBMIT_PROOF


async def proof_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await context.bot.send_message(
        ADMIN_ID,
        f"📥 **New Proof Received**\n\n"
        f"👤 User ID: `{user.id}`",
        parse_mode="Markdown"
    )
    await context.bot.send_photo(
        ADMIN_ID,
        update.message.photo[-1].file_id
    )

    await update.message.reply_text("✅ Proof submitted successfully!")
    return ConversationHandler.END


# ---------------- PAYMENT METHOD ----------------
async def payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("💳 Send your payment method details.")
    return PAYMENT_METHOD


async def payment_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_payment_methods[update.effective_user.id] = update.message.text
    await update.message.reply_text("✅ Payment method saved!")
    return ConversationHandler.END


# ---------------- WITHDRAW ----------------
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("💸 Send withdraw request details.")
    return WITHDRAW


async def withdraw_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await context.bot.send_message(
        ADMIN_ID,
        f"💸 **Withdraw Request**\n\n"
        f"👤 User ID: `{user.id}`\n"
        f"📝 {update.message.text}",
        parse_mode="Markdown"
    )
    await update.message.reply_text("✅ Withdraw request sent!")
    return ConversationHandler.END


# ---------------- ADMIN PANEL ----------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    await query.message.reply_text("🛠 Admin panel active.")


# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(proof_start, pattern="submit_proof"))
    app.add_handler(CallbackQueryHandler(payment_start, pattern="payment"))
    app.add_handler(CallbackQueryHandler(withdraw_start, pattern="withdraw"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin"))

    app.add_handler(ConversationHandler(
        entry_points=[],
        states={
            SUBMIT_PROOF: [MessageHandler(filters.PHOTO, proof_receive)],
            PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_receive)],
            WITHDRAW: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_receive)],
        },
        fallbacks=[]
    ))

    print("🤖 Bot started (Polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
