import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)
from telegram.error import BadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
FORCE_JOIN_CHANNEL = "http://t.me/TaskByZahid"

# ---- Withdraw States ----
WITHDRAW_METHOD, WITHDRAW_DETAIL, WITHDRAW_AMOUNT = range(3)

# ---- Force Join Check ----
async def is_user_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=FORCE_JOIN_CHANNEL, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except BadRequest:
        return False

# ---- START ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joined = await is_user_joined(update, context)
    if not joined:
        keyboard = [[InlineKeyboardButton("✅ Join Channel", url=FORCE_JOIN_CHANNEL)]]
        await update.message.reply_text(
            "You must join our channel to use the bot",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
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

# ---- BALANCE ----
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joined = await is_user_joined(update, context)
    if not joined:
        await start(update, context)
        return

    bal = context.user_data.get("balance", 0)
    await update.message.reply_text(f"💰 Your Balance: ₹{bal}")

# ---- SUPPORT ----
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joined = await is_user_joined(update, context)
    if not joined:
        await start(update, context)
        return

    await update.message.reply_text(
        "If you face any issue in proof or withdraw,\n"
        "Contact Owner: @DTXZAHID"
    )

# ---- WITHDRAW ----
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joined = await is_user_joined(update, context)
    if not joined:
        await start(update, context)
        return

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
    method = context.user_data["method"]

    if method == "UPI":
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

    bal = context.user_data.get("balance", 0)
    method = context.user_data["method"]
    min_amt = 5 if method == "UPI" else 2

    if amount < min_amt:
        await update.message.reply_text("Amount below minimum limit")
        return ConversationHandler.END

    if amount > bal:
        await update.message.reply_text("Insufficient balance")
        return ConversationHandler.END

    context.user_data["balance"] = bal - amount

    await update.message.reply_text(
        "Withdraw has been proceeded to owner.\n"
        "Payment will be done soon."
    )

    await context.bot.send_message(
        ADMIN_ID,
        f"Withdraw Request\n\n"
        f"User ID: {update.effective_user.id}\n"
        f"Method: {method}\n"
        f"Detail: {context.user_data['detail']}\n"
        f"Amount: ₹{amount}"
    )

    return ConversationHandler.END

# ---- ADMIN PANEL ----
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "Admin Panel\n\nAdd Balance\nRemove Balance\nTotal Users"
    )

# ---- MAIN ----
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Withdraw Conversation
    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw_start)],
        states={
            WITHDRAW_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_method)],
            WITHDRAW_DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_detail)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
        },
        fallbacks=[]
    )

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(withdraw_conv)

    app.run_polling()

if __name__ == "__main__":
    main()
