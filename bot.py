import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810

logging.basicConfig(level=logging.INFO)

# ───────────── MEMORY STORAGE ─────────────
users = {}          # user_id: {balance, payment}
proof_wait = {}     # user_id: step
withdraw_wait = {}  # user_id: step

# ───────────── KEYBOARDS ─────────────
main_kb = ReplyKeyboardMarkup(
    [
        ["📤 Submit Proof"],
        ["💰 Balance", "🔥 Withdraw"],
        ["🤯 Payment Method"]
    ],
    resize_keyboard=True
)

payment_kb = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("VSV", callback_data="pay_vsv"),
        InlineKeyboardButton("FXL", callback_data="pay_fxl"),
        InlineKeyboardButton("UPI", callback_data="pay_upi")
    ],
    [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
])

admin_kb = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("➕ Add Balance", callback_data="admin_add"),
        InlineKeyboardButton("➖ Remove Balance", callback_data="admin_remove")
    ],
    [InlineKeyboardButton("👥 Total Users", callback_data="admin_users")]
])

# ───────────── HELPERS ─────────────
def get_user(uid):
    if uid not in users:
        users[uid] = {"balance": 0, "payment": None}
    return users[uid]

# ───────────── START ─────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    await update.message.reply_text(
        "✅ *Bot Ready*\nUse buttons below 👇",
        reply_markup=main_kb,
        parse_mode="Markdown"
    )

# ───────────── BALANCE ─────────────
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"💰 *Your Balance:* ₹{user['balance']}\nUse Withdraw button to cash out 🤑",
        parse_mode="Markdown"
    )

# ───────────── SUBMIT PROOF ─────────────
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    proof_wait[update.effective_user.id] = "photo"
    await update.message.reply_text(
        "📸 Send screenshot where *refer link is visible*",
        parse_mode="Markdown"
    )

async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if proof_wait.get(uid) == "photo" and update.message.photo:
        proof_wait[uid] = "link"
        context.user_data["proof_photo"] = update.message.photo[-1].file_id
        await update.message.reply_text("🔗 Now send your *refer link*")
    elif proof_wait.get(uid) == "link":
        refer = update.message.text
        photo = context.user_data.get("proof_photo")

        await context.bot.send_photo(
            ADMIN_ID,
            photo=photo,
            caption=f"`{uid}`\n🔗 {refer}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Accept", callback_data=f"proof_ok_{uid}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"proof_no_{uid}")
                ]
            ])
        )

        proof_wait.pop(uid)
        await update.message.reply_text(
            "✅ Proof Submitted\n⏳ Wait for verification"
        )

# ───────────── PROOF ACTION ─────────────
async def proof_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data.split("_")
    uid = int(data[2])

    if data[1] == "ok":
        await context.bot.send_message(uid, "✅ Proof Approved")
    else:
        await context.bot.send_message(uid, "❌ Proof Rejected")

    await q.edit_message_reply_markup(None)

# ───────────── PAYMENT METHOD ─────────────
async def payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤯 Choose Payment Method",
        reply_markup=payment_kb
    )

async def payment_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    method = q.data.replace("pay_", "")
    context.user_data["pay_method"] = method

    msg = "Send UPI ID" if method == "upi" else "Send Registered Number"
    await q.message.reply_text(msg)
    withdraw_wait[uid] = "payment"

async def save_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if withdraw_wait.get(uid) == "payment":
        users[uid]["payment"] = {
            "method": context.user_data["pay_method"],
            "value": update.message.text
        }
        withdraw_wait.pop(uid)
        await update.message.reply_text("✅ Payment Method Saved")

# ───────────── WITHDRAW ─────────────
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)

    if not user["payment"]:
        await update.message.reply_text("❌ Set payment method first")
        return

    withdraw_wait[uid] = "amount"
    await update.message.reply_text("💸 Enter amount to withdraw")

async def handle_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if withdraw_wait.get(uid) == "amount":
        amt = int(update.message.text)
        user = get_user(uid)

        if amt > user["balance"]:
            await update.message.reply_text("❌ Insufficient balance")
            return

        await context.bot.send_message(
            ADMIN_ID,
            f"💸 Withdraw Request\nUser: `{uid}`\nAmount: ₹{amt}\nMethod: {user['payment']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Payment Cleared", callback_data=f"wd_ok_{uid}_{amt}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                ]
            ])
        )
        withdraw_wait.pop(uid)
        await update.message.reply_text("📤 Withdraw request sent")

async def withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, uid, amt = q.data.split("_")
    uid, amt = int(uid), int(amt)

    users[uid]["balance"] -= amt
    await context.bot.send_message(uid, "✅ Your payment has been sent")
    await q.edit_message_reply_markup(None)

# ───────────── ADMIN PANEL ─────────────
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            "🛠 *Admin Panel*",
            reply_markup=admin_kb,
            parse_mode="Markdown"
        )

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "admin_users":
        await q.message.reply_text(f"👥 Total Users: {len(users)}")

# ───────────── RUN ─────────────
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dtx", admin_panel))

app.add_handler(MessageHandler(filters.Regex("Submit Proof"), submit_proof))
app.add_handler(MessageHandler(filters.Regex("Balance"), balance))
app.add_handler(MessageHandler(filters.Regex("Withdraw"), withdraw))
app.add_handler(MessageHandler(filters.Regex("Payment Method"), payment_method))

app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, handle_proof))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_withdraw))
app.add_handler(MessageHandler(filters.TEXT, save_payment))

app.add_handler(CallbackQueryHandler(proof_action, pattern="proof_"))
app.add_handler(CallbackQueryHandler(payment_select, pattern="pay_"))
app.add_handler(CallbackQueryHandler(withdraw_action, pattern="wd_"))
app.add_handler(CallbackQueryHandler(admin_actions, pattern="admin_"))

print("🤖 Bot running...")
app.run_polling()
