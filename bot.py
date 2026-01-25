import os
import re
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters, CallbackQueryHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# States
PROOF_SCREENSHOT, PROOF_LINK = range(2)
WITHDRAW_METHOD, WITHDRAW_DETAIL, WITHDRAW_AMOUNT = range(3)
ADMIN_ADD_BAL, ADMIN_REM_BAL, ADMIN_ADD_IDS = range(3)

# Data storage
USER_BALANCE = {}  # user_id: balance
VERIFIED_IDS = {}  # user_id: amount or None
PENDING_PROOFS = []  # temporary proofs storage

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
    await update.message.reply_text("📸 Send your screenshot of the proof first:")
    return PROOF_SCREENSHOT

async def proof_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a valid screenshot (photo).")
        return PROOF_SCREENSHOT

    context.user_data["proof_screenshot"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Now send the refer link:")
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = re.search(r"start=(\d+)", text)
    if not match:
        await update.message.reply_text("❌ Invalid refer link. Send again.")
        return PROOF_LINK

    refer_id = match.group(1)
    telegram_user_id = update.effective_user.id
    proof_status = "❌ REJECTED"
    amount_added = 0

    # Check verified IDs
    if refer_id in VERIFIED_IDS:
        proof_status = "✅ VERIFIED"
        amt = VERIFIED_IDS[refer_id]
        if amt:
            USER_BALANCE[telegram_user_id] = USER_BALANCE.get(telegram_user_id, 0) + amt
            amount_added = amt
        del VERIFIED_IDS[refer_id]  # remove used ID

        await update.message.reply_text(
            f"✅ Proof verified successfully\n"
            f"Payment/Balance will be added in 5 minutes\n"
            f"Amount Added: ₹{amount_added}" if amount_added else ""
        )
    else:
        await update.message.reply_text(
            "❌ Proof rejected due to same device/fake proof/fake refer"
        )

    # Send proof to admin
    await context.bot.send_photo(
        ADMIN_ID,
        photo=context.user_data["proof_screenshot"],
        caption=(
            f"📥 Proof Record\n"
            f"Telegram User ID: {telegram_user_id}\n"
            f"Refer ID: {refer_id}\n"
            f"Status: {proof_status}\n"
            f"Amount Added: ₹{amount_added}"
        )
    )

    return ConversationHandler.END

# ---- WITHDRAW ----
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup([["UPI", "VSV", "FXL"]], resize_keyboard=True)
    await update.message.reply_text("Choose withdraw method:", reply_markup=keyboard)
    return WITHDRAW_METHOD

async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = update.message.text.upper()
    if method not in ["UPI", "VSV", "FXL"]:
        await update.message.reply_text("❌ Choose from the buttons (UPI/VSV/FXL).")
        return WITHDRAW_METHOD

    context.user_data["method"] = method
    if method == "UPI":
        await update.message.reply_text("Send your verified UPI ID:")
    else:
        await update.message.reply_text("Send your registered wallet number:")
    return WITHDRAW_DETAIL

async def withdraw_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text
    min_amt = 5 if context.user_data["method"] == "UPI" else 2
    await update.message.reply_text(f"Enter amount (Minimum ₹{min_amt}):")
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text)
    except:
        await update.message.reply_text("❌ Enter a valid number")
        return WITHDRAW_AMOUNT

    bal = USER_BALANCE.get(update.effective_user.id, 0)
    method = context.user_data["method"]
    min_amt = 5 if method == "UPI" else 2

    if amount < min_amt:
        await update.message.reply_text("❌ Amount below minimum limit")
        return ConversationHandler.END
    if amount > bal:
        await update.message.reply_text("❌ Insufficient balance")
        return ConversationHandler.END

    USER_BALANCE[update.effective_user.id] = bal - amount
    await update.message.reply_text("✅ Withdraw request submitted. Payment will be processed soon.")

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw Request\nUser ID: {update.effective_user.id}\n"
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

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = update.message.text.strip()
    lines = text.splitlines()

    if lines[0].lower().startswith("verified"):
        # Add Verified IDs with optional amount
        for line in lines[1:]:
            parts = line.split()
            uid = parts[0]
            amt = float(parts[1]) if len(parts) > 1 else None
            VERIFIED_IDS[uid] = amt
        await update.message.reply_text("✅ Verified IDs updated successfully.")
    elif len(lines[0].split()) == 2:
        uid, amt = lines[0].split()
        amt = float(amt)
        USER_BALANCE[int(uid)] = USER_BALANCE.get(int(uid), 0) + amt
        await update.message.reply_text(f"✅ Balance added: ₹{amt} to {uid}")
    elif len(lines[0].split()) == 1:
        uid = lines[0]
        USER_BALANCE[int(uid)] = USER_BALANCE.get(int(uid), 0)
        await update.message.reply_text(f"✅ Balance check/created for {uid}")

# ---- MAIN ----
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    proof_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={
            PROOF_SCREENSHOT: [MessageHandler(filters.PHOTO, proof_screenshot)],
            PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_link)]
        },
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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))

    # Fix single-instance polling
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
