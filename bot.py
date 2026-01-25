import json
import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
DB_FILE = "users.json"

# ---------------- DB ---------------- #

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user(uid):
    db = load_db()
    if str(uid) not in db:
        db[str(uid)] = {
            "balance": 0,
            "payment_method": None,
            "payment_value": None,
        }
        save_db(db)
    return db[str(uid)]

def update_user(uid, data):
    db = load_db()
    db[str(uid)] = data
    save_db(db)

# ---------------- Keyboards ---------------- #

MAIN_KB = ReplyKeyboardMarkup(
    [
        ["📤 Submit Proof"],
        ["💰 Balance", "🔥 Withdraw"],
        ["🤯 Payment Method"],
    ],
    resize_keyboard=True,
)

PAYMENT_KB = ReplyKeyboardMarkup(
    [["VSV", "FXL", "UPI"], ["❌ Cancel"]],
    resize_keyboard=True,
)

# ---------------- Handlers ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    await update.message.reply_text(
        "✅ Bot Ready\n\nUse buttons below 👇",
        reply_markup=MAIN_KB,
    )

# -------- Submit Proof -------- #

async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_proof"] = True
    await update.message.reply_text(
        "📤 Send **Screenshot** then send **Refer Link**",
        parse_mode="Markdown",
    )

async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_proof"):
        return

    if update.message.photo:
        context.user_data["proof_photo"] = update.message.photo[-1].file_id
        await update.message.reply_text("🔗 Now send Refer Link")
        return

    if update.message.text:
        photo = context.user_data.get("proof_photo")
        refer = update.message.text
        uid = update.effective_user.id

        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Accept", callback_data=f"acc_{uid}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}"),
                ]
            ]
        )

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo,
            caption=f"🆔 User: `{uid}`\n🔗 Refer: {refer}",
            parse_mode="Markdown",
            reply_markup=buttons,
        )

        context.user_data.clear()
        await update.message.reply_text(
            "✅ Proof Submitted\n⏳ Wait for verification",
            reply_markup=MAIN_KB,
        )

# -------- Admin Verify -------- #

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, uid = query.data.split("_")
    user = get_user(uid)

    if action == "acc":
        user["balance"] += 1
        update_user(uid, user)
        await context.bot.send_message(uid, "✅ Proof Approved\n💰 +₹1 Added")
        await query.edit_message_caption("✅ Approved")
    else:
        await context.bot.send_message(uid, "❌ Proof Rejected")
        await query.edit_message_caption("❌ Rejected")

# -------- Balance -------- #

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"💰 Your Balance: ₹{user['balance']}",
        reply_markup=MAIN_KB,
    )

# -------- Payment Method -------- #

async def payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["set_payment"] = True
    await update.message.reply_text(
        "🤯 Choose Payment Method",
        reply_markup=PAYMENT_KB,
    )

async def set_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("set_payment"):
        return

    method = update.message.text
    if method == "❌ Cancel":
        context.user_data.clear()
        await update.message.reply_text("❌ Cancelled", reply_markup=MAIN_KB)
        return

    context.user_data["method"] = method
    await update.message.reply_text(f"✍️ Send your {method} ID")

async def save_payment_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "method" not in context.user_data:
        return

    user = get_user(update.effective_user.id)
    user["payment_method"] = context.user_data["method"]
    user["payment_value"] = update.message.text
    update_user(update.effective_user.id, user)

    context.user_data.clear()
    await update.message.reply_text(
        "✅ Payment Method Saved",
        reply_markup=MAIN_KB,
    )

# -------- Withdraw -------- #

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    if not user["payment_method"]:
        await update.message.reply_text(
            "❌ Set payment method first",
            reply_markup=MAIN_KB,
        )
        return

    if user["balance"] <= 0:
        await update.message.reply_text("❌ Insufficient balance")
        return

    context.user_data["withdraw"] = True
    await update.message.reply_text("💸 Enter amount to withdraw")

async def process_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("withdraw"):
        return

    amt = int(update.message.text)
    uid = update.effective_user.id
    user = get_user(uid)

    if amt > user["balance"]:
        await update.message.reply_text("❌ Not enough balance")
        return

    user["balance"] -= amt
    update_user(uid, user)

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw Request\n🆔 {uid}\n₹{amt}\n{user['payment_method']}: {user['payment_value']}",
    )

    context.user_data.clear()
    await update.message.reply_text(
        "✅ Withdraw Request Sent",
        reply_markup=MAIN_KB,
    )

# ---------------- MAIN ---------------- #

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("📤 Submit Proof"), submit_proof))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, receive_proof))

    app.add_handler(CallbackQueryHandler(admin_action))

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("💰 Balance"), balance))

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("🤯 Payment Method"), payment_method))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("VSV|FXL|UPI|❌ Cancel"), set_payment))
    app.add_handler(MessageHandler(filters.TEXT, save_payment_value))

    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("🔥 Withdraw"), withdraw))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\d+$"), process_withdraw))

    print("🤖 Bot Running (Railway Ready)")
    app.run_polling()

if __name__ == "__main__":
    main()
