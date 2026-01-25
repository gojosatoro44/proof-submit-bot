import os
from telegram import (
    Update, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
FORCE_JOIN_CHANNEL = "@TaskByZahid"

# ---- STATES ----
(
    PROOF_SCREENSHOT,
    PROOF_REFER,
    WITHDRAW_METHOD,
    WITHDRAW_DETAIL,
    WITHDRAW_AMOUNT
) = range(5)

# ---------------- FORCE JOIN ----------------
async def is_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(
            FORCE_JOIN_CHANNEL, update.effective_user.id
        )
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def force_join_msg(update: Update):
    await update.message.reply_text(
        "❌ You must join our channel to use this bot",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Join Channel", url="https://t.me/TaskByZahid")]]
        )
    )

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_joined(update, context):
        await force_join_msg(update)
        return

    keyboard = [
        ["📤 Submit Proof"],
        ["💰 Balance", "💸 Withdraw"],
        ["🆘 Support"]
    ]
    await update.message.reply_text(
        "👋 Welcome to Task Bot",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ---------------- SUBMIT PROOF ----------------
async def submit_proof_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_joined(update, context):
        await force_join_msg(update)
        return ConversationHandler.END

    await update.message.reply_text("📸 Send Screenshot Of Bot")
    return PROOF_SCREENSHOT

async def proof_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a screenshot image only")
        return PROOF_SCREENSHOT

    context.user_data["proof_photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Send Your Refer Link To Verify")
    return PROOF_REFER

async def proof_refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["refer_link"] = update.message.text

    await update.message.reply_text(
        "✅ Proof has been submitted successfully for verification"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"proof_accept_{update.effective_user.id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"proof_reject_{update.effective_user.id}")
        ]
    ])

    await context.bot.send_photo(
        ADMIN_ID,
        photo=context.user_data["proof_photo"],
        caption=(
            f"📤 New Proof Submitted\n\n"
            f"👤 User ID: {update.effective_user.id}\n"
            f"🔗 Refer Link:\n{context.user_data['refer_link']}"
        ),
        reply_markup=keyboard
    )

    return ConversationHandler.END

# ---------------- PROOF CALLBACK ----------------
async def proof_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split("_")[1:]
    user_id = int(user_id)

    if action == "accept":
        await context.bot.send_message(
            user_id,
            "✅ Proof has been verified successfully.\nBalance will be added in 5–10 minutes."
        )
        await query.edit_message_caption(query.message.caption + "\n\n✅ Accepted")

    else:
        await context.bot.send_message(
            user_id,
            "❌ Owner has rejected your proof due to fake proof / same device."
        )
        await query.edit_message_caption(query.message.caption + "\n\n❌ Rejected")

# ---------------- BALANCE ----------------
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_joined(update, context):
        await force_join_msg(update)
        return

    bal = context.user_data.get("balance", 0)
    await update.message.reply_text(
        f"💰 Your Balance: ₹{bal}\n\nComplete tasks to earn more!"
    )

# ---------------- SUPPORT ----------------
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "If you are facing any issue in submitting proof or withdraw,\n"
        "Contact Owner: @DTXZAHID"
    )

# ---------------- WITHDRAW ----------------
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Choose Withdraw Method",
        reply_markup=ReplyKeyboardMarkup(
            [["UPI", "VSV", "FXL"]], resize_keyboard=True, one_time_keyboard=True
        )
    )
    return WITHDRAW_METHOD

async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = update.message.text.upper()
    if method not in ["UPI", "VSV", "FXL"]:
        await update.message.reply_text("Invalid option")
        return WITHDRAW_METHOD

    context.user_data["method"] = method
    await update.message.reply_text(
        "Send your verified UPI ID" if method == "UPI"
        else "Send your registered wallet number"
    )
    return WITHDRAW_DETAIL

async def withdraw_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text
    await update.message.reply_text(
        "Enter amount\n\nUPI Min ₹5\nVSV/FXL Min ₹2"
    )
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = int(update.message.text)
    bal = context.user_data.get("balance", 0)
    min_amt = 5 if context.user_data["method"] == "UPI" else 2

    if amount < min_amt or amount > bal:
        await update.message.reply_text("❌ Invalid amount")
        return ConversationHandler.END

    context.user_data["balance"] = bal - amount

    await update.message.reply_text(
        "✅ Withdraw has been proceeded to owner.\nPayment will be done soon."
    )

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw Request\n\n"
        f"User ID: {update.effective_user.id}\n"
        f"Method: {context.user_data['method']}\n"
        f"Detail: {context.user_data['detail']}\n"
        f"Amount: ₹{amount}"
    )
    return ConversationHandler.END

# ---------------- ADMIN ----------------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            "Admin Panel\n\nAdd Balance\nRemove Balance\nTotal Users"
        )

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof_start)],
        states={
            PROOF_SCREENSHOT: [MessageHandler(filters.PHOTO, proof_screenshot)],
            PROOF_REFER: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_refer)],
        },
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw_start)],
        states={
            WITHDRAW_METHOD: [MessageHandler(filters.TEXT, withdraw_method)],
            WITHDRAW_DETAIL: [MessageHandler(filters.TEXT, withdraw_detail)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT, withdraw_amount)],
        },
        fallbacks=[]
    ))

    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(MessageHandler(filters.CallbackQuery, proof_decision))

    app.run_polling()

if __name__ == "__main__":
    main()
