import json
import os
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters, CallbackQueryHandler
)

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DATA_DIR = "data"
USERS_FILE = f"{DATA_DIR}/users.json"
VERIFIED_FILE = f"{DATA_DIR}/verified_ids.json"
PROOFS_FILE = f"{DATA_DIR}/proofs.json"

os.makedirs(DATA_DIR, exist_ok=True)

# ===== STATES =====
(
    SUBMIT_SCREENSHOT, SUBMIT_LINK,
    WD_METHOD, WD_DETAILS, WD_AMOUNT,
    ADD_BALANCE, REMOVE_BALANCE,
    ADD_VERIFIED, CHECK_DETAIL
) = range(9)

# ===== HELPERS =====
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["📤 Submit Proof"],
            ["💰 Balance", "💸 Withdraw"],
            ["🆘 Support"]
        ],
        resize_keyboard=True
    )

# ================= WITHDRAW (FULLY FIXED) =================

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("UPI", callback_data="wd_upi"),
            InlineKeyboardButton("VSV", callback_data="wd_vsv"),
            InlineKeyboardButton("FXL", callback_data="wd_fxl"),
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="wd_cancel")]
    ])
    await update.message.reply_text(
        "💸 Choose withdrawal method:",
        reply_markup=kb
    )
    return WD_METHOD

async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "wd_cancel":
        await query.message.reply_text("❌ Cancelled", reply_markup=main_menu())
        return ConversationHandler.END

    method = query.data.replace("wd_", "").upper()
    context.user_data["wd_method"] = method

    if method == "UPI":
        msg = "📲 Send your UPI ID:"
    else:
        msg = "📱 Send your registered number:"

    await query.message.reply_text(msg)
    return WD_DETAILS

async def withdraw_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Cancel":
        await update.message.reply_text("❌ Cancelled", reply_markup=main_menu())
        return ConversationHandler.END

    context.user_data["wd_details"] = update.message.text.strip()

    method = context.user_data["wd_method"]
    min_amt = 5 if method == "UPI" else 2

    await update.message.reply_text(
        f"💰 Enter amount to withdraw\nMinimum ₹{min_amt}:"
    )
    return WD_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("❌ Enter numbers only")
        return WD_AMOUNT

    amt = int(update.message.text)
    method = context.user_data["wd_method"]
    min_amt = 5 if method == "UPI" else 2

    if amt < min_amt:
        await update.message.reply_text(f"❌ Minimum ₹{min_amt} required")
        return WD_AMOUNT

    users = load_json(USERS_FILE, {})
    uid = str(update.effective_user.id)

    if users[uid]["balance"] < amt:
        await update.message.reply_text("❌ Insufficient balance")
        return ConversationHandler.END

    users[uid]["balance"] -= amt
    save_json(USERS_FILE, users)

    details = context.user_data["wd_details"]

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Withdraw Done", callback_data=f"wd_done:{uid}:{amt}"),
            InlineKeyboardButton("❌ Withdraw Rejected", callback_data=f"wd_reject:{uid}:{amt}")
        ]
    ])

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw Request\n\n"
        f"User ID: {uid}\n"
        f"Amount: ₹{amt}\n"
        f"Method: {method}\n"
        f"Details: {details}",
        reply_markup=kb
    )

    await update.message.reply_text(
        "✅ Withdraw request submitted",
        reply_markup=main_menu()
    )
    return ConversationHandler.END

# ===== ADMIN WITHDRAW ACTION =====
async def withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, uid, amt = query.data.split(":")
    uid = int(uid)

    if action == "wd_done":
        msg = "✅ Your withdrawal has been processed successfully."
    else:
        msg = "❌ Your withdrawal was rejected due to some issues."

    await context.bot.send_message(uid, msg)
    await query.message.edit_text("✔ Action completed")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw)],
        states={
            WD_METHOD: [CallbackQueryHandler(withdraw_method)],
            WD_DETAILS: [MessageHandler(filters.TEXT, withdraw_details)],
            WD_AMOUNT: [MessageHandler(filters.TEXT, withdraw_amount)],
        },
        fallbacks=[]
    ))

    app.add_handler(CallbackQueryHandler(withdraw_action, pattern="^wd_"))

    app.run_polling()

if __name__ == "__main__":
    main()
