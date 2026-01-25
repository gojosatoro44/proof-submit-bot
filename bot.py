import os
import re
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters, CallbackQueryHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

WITHDRAW_METHOD, WITHDRAW_DETAIL, WITHDRAW_AMOUNT = range(3)
VERIFIED_IDS = []  # Add your initial verified IDs here
PENDING_PROOFS = []  # List to store proofs temporarily
USER_BALANCE = {}  # Store user balances

# ---- START ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📤 Submit Proof"],
        ["💰 Balance", "💸 Withdraw"],
        ["🆘 Support"]
    ]
    await update.message.reply_text(
        "👋 Welcome to Task Bot",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ---- BALANCE ----
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bal = USER_BALANCE.get(update.effective_user.id, 0)
    await update.message.reply_text(f"💰 Your Balance: ₹{bal}")

# ---- SUPPORT ----
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "If you face any issue in proof or withdraw,\n"
        "Contact Owner: @DTXZAHID"
    )

# ---- SUBMIT PROOF ----
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send your proof in this format:\n"
        "https://t.me/Bot_Tasks_Payment_Bot?start=UserID\n"
        "Example: https://t.me/Bot_Tasks_Payment_Bot?start=7101602737"
    )
    return "PROOF"

async def proof_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = re.search(r"start=(\d+)", text)
    if not match:
        await update.message.reply_text("❌ Invalid proof format.")
        return "PROOF"

    user_id = int(match.group(1))
    if user_id in VERIFIED_IDS:
        await update.message.reply_text("❌ Proof rejected (Already Verified).")
        # Send to admin as record
        await context.bot.send_message(
            ADMIN_ID,
            f"Rejected Proof Record:\nUser ID: {user_id}\nRefer Link: {text}\nReason: Already Verified"
        )
        return ConversationHandler.END

    # Auto verification
    if user_id in VERIFIED_IDS:
        status = "✅ VERIFIED"
        USER_BALANCE[update.effective_user.id] = USER_BALANCE.get(update.effective_user.id, 0) + 0
        VERIFIED_IDS.remove(user_id)
    else:
        status = "❌ REJECTED"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept", callback_data=f"accept_{user_id}_{text}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}_{text}")]
    ])

    await context.bot.send_message(
        ADMIN_ID,
        f"📥 New Proof\n\nUser ID: {user_id}\nRefer Link: {text}\nStatus: {status}",
        reply_markup=keyboard
    )

    # Instant rejection for users if not valid
    if status == "❌ REJECTED":
        await update.message.reply_text("❌ Proof rejected due to fake/same device/fake refer")
    else:
        await update.message.reply_text("✅ Proof submitted successfully")

    return ConversationHandler.END

# ---- WITHDRAW ----
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter withdraw method\nUPI / VSV / FXL")
    return WITHDRAW_METHOD

async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = update.message.text.upper()
    if method not in ["UPI", "VSV", "FXL"]:
        await update.message.reply_text("Invalid method. Choose UPI / VSV / FXL")
        return WITHDRAW_METHOD

    context.user_data["method"] = method

    if method == "UPI":
        await update.message.reply_text("Send your verified UPI ID")
    else:
        await update.message.reply_text("Send your registered wallet number")

    return WITHDRAW_DETAIL

async def withdraw_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text

    if context.user_data["method"] == "UPI":
        await update.message.reply_text("Enter amount (Minimum ₹5)")
    else:
        await update.message.reply_text("Enter amount (Minimum ₹2)")

    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text)
    except:
        await update.message.reply_text("Enter a valid number")
        return WITHDRAW_AMOUNT

    bal = USER_BALANCE.get(update.effective_user.id, 0)
    method = context.user_data["method"]
    min_amt = 5 if method == "UPI" else 2

    if amount < min_amt:
        await update.message.reply_text("Amount below minimum limit")
        return ConversationHandler.END

    if amount > bal:
        await update.message.reply_text("Insufficient balance")
        return ConversationHandler.END

    USER_BALANCE[update.effective_user.id] = bal - amount

    await update.message.reply_text(
        "Withdraw has been proceeded to owner.\nPayment will be done soon."
    )

    await context.bot.send_message(
        ADMIN_ID,
        f"Withdraw Request\n\nUser ID: {update.effective_user.id}\n"
        f"Method: {method}\nDetail: {context.user_data['detail']}\nAmount: ₹{amount}"
    )

    return ConversationHandler.END

# ---- ADMIN PANEL ----
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        ["Add Balance", "Remove Balance"],
        ["Total Users", "Verified IDs"]
    ]
    await update.message.reply_text(
        "Admin Panel",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ---- CALLBACK HANDLER FOR PROOFS ----
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    # Accept proof
    if data.startswith("accept_"):
        _, user_id, link = data.split("_", 2)
        user_id = int(user_id)
        USER_BALANCE[user_id] = USER_BALANCE.get(user_id, 0) + 2.5  # Example default
        VERIFIED_IDS.remove(user_id)
        await query.edit_message_text(f"✅ Proof Accepted for User ID: {user_id}")
    elif data.startswith("reject_"):
        _, user_id, link = data.split("_", 2)
        await query.edit_message_text(f"❌ Proof Rejected for User ID: {user_id}")

# ---- MAIN ----
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    proof_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={"PROOF": [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_received)]},
        fallbacks=[]
    )

    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw_start)],
        states={
            WITHDRAW_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_method)],
            WITHDRAW_DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_detail)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(proof_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Fix single instance Conflict
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
