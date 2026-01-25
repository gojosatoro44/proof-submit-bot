import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ========= ENV VARIABLES =========
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# =================================

ASK_PROOF, ASK_REFERRAL = range(2)

# temporary storage
user_data_store = {}

# ========= MAIN KEYBOARD =========
def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📤 Submit Proof"],
            ["💰 Balance", "❤️ Withdraw"],
            ["🥵 Payment Method"]
        ],
        resize_keyboard=True
    )

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\nUse the buttons below 👇",
        reply_markup=main_keyboard()
    )

# ========= SUBMIT PROOF =========
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Send Screenshot\n(Refer link must be visible)",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_PROOF

async def get_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a screenshot image only")
        return ASK_PROOF

    context.user_data["proof"] = update.message.photo[-1].file_id

    await update.message.reply_text("🔗 Now send your Refer Link")
    return ASK_REFERRAL

async def get_refer_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    refer_link = update.message.text
    proof_photo = context.user_data.get("proof")

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"accept|{user.id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject|{user.id}")
            ]
        ]
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=proof_photo,
        caption=(
            f"📤 **New Proof Submitted**\n\n"
            f"`{user.id}`\n\n"
            f"🔗 Refer Link:\n{refer_link}"
        ),
        parse_mode="Markdown",
        reply_markup=buttons
    )

    await update.message.reply_text(
        "✅ Proof submitted successfully\n⏳ Wait for verification",
        reply_markup=main_keyboard()
    )

    return ConversationHandler.END

# ========= ADMIN ACTION =========
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split("|")
    user_id = int(user_id)

    if action == "accept":
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Bro apka refer count ho gaya\n💸 Payment 5–10 min me bot me aa jayega"
        )
        await query.edit_message_caption("✅ Accepted")

    elif action == "reject":
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Bro apka refer nahi aaya\nPayment nahi milega"
        )
        await query.edit_message_caption("❌ Rejected")

# ========= BALANCE =========
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    bal = user_data_store.get(uid, 0)

    await update.message.reply_text(
        f"💰 Your Balance: ₹{bal}\n\nUse Withdraw button to cash out 💸"
    )

# ========= CANCEL =========
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Cancelled",
        reply_markup=main_keyboard()
    )
    return ConversationHandler.END

# ========= MAIN =========
def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN not set in environment variables")

    app = ApplicationBuilder().token(TOKEN).build()

    proof_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={
            ASK_PROOF: [MessageHandler(filters.PHOTO, get_screenshot)],
            ASK_REFERRAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_refer_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(proof_handler)
    app.add_handler(CallbackQueryHandler(admin_action))
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))

    print("🤖 Bot running with ENV variables (Railway ready)")
    app.run_polling()

if __name__ == "__main__":
    main()
