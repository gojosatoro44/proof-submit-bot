import os
import json
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
FORCE_CHANNEL = "@TaskByZahid"

DATA_FILE = "data.json"

# ------------------ DATA ------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "verified_ids": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# ------------------ STATES ------------------
PROOF_SS, PROOF_LINK = range(2)
W_METHOD, W_DETAIL, W_AMOUNT = range(3)

# ------------------ FORCE JOIN ------------------
async def is_joined(bot, user_id):
    try:
        member = await bot.get_chat_member(FORCE_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joined = await is_joined(context.bot, update.effective_user.id)
    if joined:
        return True
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Join Channel", url="https://t.me/TaskByZahid")],
        [InlineKeyboardButton("🔄 Check Join", callback_data="check_join")]
    ])
    await update.message.reply_text(
        "🚫 You must join our channel to use this bot.",
        reply_markup=keyboard
    )
    return False

async def check_join_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    joined = await is_joined(context.bot, query.from_user.id)
    if joined:
        await query.message.reply_text("✅ Joined successfully. Send /start")
    else:
        await query.message.reply_text("❌ Still not joined.")

# ------------------ START ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join(update, context):
        return

    uid = str(update.effective_user.id)
    if uid not in data["users"]:
        data["users"][uid] = {"balance": 0}
        save_data(data)

    keyboard = [
        ["📤 Submit Proof"],
        ["💰 Balance", "💸 Withdraw"],
        ["🆘 Support"]
    ]
    await update.message.reply_text(
        "👋 Welcome to Task Bot",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ------------------ BALANCE ------------------
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    bal = data["users"].get(uid, {}).get("balance", 0)
    await update.message.reply_text(f"💰 Your Balance: ₹{bal}")

# ------------------ SUPPORT ------------------
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "If you face any issue in proof or withdraw,\n"
        "Contact Owner: @DTXZAHID"
    )

# ------------------ SUBMIT PROOF ------------------
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join(update, context):
        return ConversationHandler.END

    await update.message.reply_text("📸 Send Screenshot Of Bot")
    return PROOF_SS

async def proof_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["screenshot"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Send Your Refer Link To Verify")
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    link = update.message.text

    status = "✅ VERIFIED" if uid in data["verified_ids"] else "❌ UNVERIFIED"

    await context.bot.send_photo(
        ADMIN_ID,
        context.user_data["screenshot"],
        caption=(
            f"📥 New Proof\n\n"
            f"User ID: {uid}\n"
            f"Refer Link: {link}\n"
            f"Status: {status}"
        ),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"proof_ok:{uid}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"proof_no:{uid}")
            ]
        ])
    )

    await update.message.reply_text(
        "✅ Proof has been submitted successfully.\n"
        "Please wait for verification."
    )
    return ConversationHandler.END

async def proof_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, uid = query.data.split(":")

    if action == "proof_ok":
        await context.bot.send_message(
            int(uid),
            "✅ Proof Verified Successfully.\nBalance will be added in 5–10 minutes."
        )
    else:
        await context.bot.send_message(
            int(uid),
            "❌ Proof Rejected due to fake proof / same device."
        )

# ------------------ WITHDRAW ------------------
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Choose Withdraw Method",
        reply_markup=ReplyKeyboardMarkup(
            [["UPI", "VSV", "FXL"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return W_METHOD

async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = update.message.text.upper()
    if method not in ["UPI", "VSV", "FXL"]:
        await update.message.reply_text("Invalid method.")
        return W_METHOD

    context.user_data["method"] = method
    msg = "Send your verified UPI ID" if method == "UPI" else "Send your registered wallet number"
    await update.message.reply_text(msg)
    return W_DETAIL

async def withdraw_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text
    min_amt = "₹5" if context.user_data["method"] == "UPI" else "₹2"
    await update.message.reply_text(f"Enter amount (Minimum {min_amt})")
    return W_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    amount = int(update.message.text)
    bal = data["users"][uid]["balance"]
    min_amt = 5 if context.user_data["method"] == "UPI" else 2

    if amount < min_amt or amount > bal:
        await update.message.reply_text("❌ Invalid amount.")
        return ConversationHandler.END

    data["users"][uid]["balance"] -= amount
    save_data(data)

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw Request\n\n"
        f"User ID: {uid}\n"
        f"Method: {context.user_data['method']}\n"
        f"Detail: {context.user_data['detail']}\n"
        f"Amount: ₹{amount}"
    )

    await update.message.reply_text(
        "✅ Withdraw has been proceeded.\n"
        "Payment will be done soon."
    )
    return ConversationHandler.END

# ------------------ ADMIN VERIFIED IDS ------------------
async def add_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    uid = int(context.args[0])
    if uid not in data["verified_ids"]:
        data["verified_ids"].append(uid)
        save_data(data)
    await update.message.reply_text("✅ ID Added To Verified List")

# ------------------ MAIN ------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addid", add_id))
    app.add_handler(CallbackQueryHandler(check_join_cb, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(proof_action, pattern="proof_"))

    proof_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={
            PROOF_SS: [MessageHandler(filters.PHOTO, proof_ss)],
            PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_link)],
        },
        fallbacks=[]
    )

    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw_start)],
        states={
            W_METHOD: [MessageHandler(filters.TEXT, withdraw_method)],
            W_DETAIL: [MessageHandler(filters.TEXT, withdraw_detail)],
            W_AMOUNT: [MessageHandler(filters.TEXT, withdraw_amount)],
        },
        fallbacks=[]
    )

    app.add_handler(proof_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))

    app.run_polling()

if __name__ == "__main__":
    main()
