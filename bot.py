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

# ───────── STORAGE ─────────
users = {}          # uid: {balance, payment}
states = {}         # uid: current_state
temp = {}           # uid: temp data

# ───────── KEYBOARDS ─────────
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

# ───────── HELPERS ─────────
def get_user(uid):
    if uid not in users:
        users[uid] = {"balance": 0, "payment": None}
    return users[uid]

def clear_state(uid):
    states.pop(uid, None)
    temp.pop(uid, None)

# ───────── START ─────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)
    clear_state(update.effective_user.id)
    await update.message.reply_text(
        "✅ *Bot Ready*\nUse buttons below 👇",
        reply_markup=main_kb,
        parse_mode="Markdown"
    )

# ───────── BALANCE ─────────
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"💰 *Your Balance:* ₹{user['balance']}\nUse Withdraw button to cash out 🤑",
        parse_mode="Markdown"
    )

# ───────── SUBMIT PROOF ─────────
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    clear_state(uid)
    states[uid] = "WAIT_PROOF_PHOTO"
    await update.message.reply_text(
        "📸 Send screenshot where *refer link is visible*",
        parse_mode="Markdown"
    )

# ───────── PAYMENT METHOD ─────────
async def payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    clear_state(uid)
    await update.message.reply_text(
        "🤯 Choose Payment Method",
        reply_markup=payment_kb
    )

async def payment_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    method = q.data.replace("pay_", "")
    temp[uid] = {"method": method}
    states[uid] = "WAIT_PAYMENT_VALUE"

    if method == "upi":
        msg = "🔗 Send your *UPI ID*"
    else:
        msg = "📱 Send your *Registered Number*"

    await q.message.reply_text(msg, parse_mode="Markdown")

# ───────── WITHDRAW ─────────
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)

    if not user["payment"]:
        await update.message.reply_text("❌ Set payment method first")
        return

    clear_state(uid)
    states[uid] = "WAIT_WITHDRAW_AMOUNT"
    await update.message.reply_text("💸 Enter amount to withdraw")

# ───────── MAIN TEXT HANDLER (FIXED CORE) ─────────
async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    state = states.get(uid)

    # ── Proof: Refer link ──
    if state == "WAIT_PROOF_LINK":
        photo = temp[uid]["photo"]

        await context.bot.send_photo(
            ADMIN_ID,
            photo=photo,
            caption=f"`{uid}`\n🔗 {text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Accept", callback_data=f"proof_ok_{uid}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"proof_no_{uid}")
                ]
            ])
        )

        clear_state(uid)
        await update.message.reply_text(
            "✅ Proof Submitted\n⏳ Wait for verification"
        )
        return

    # ── Save Payment ──
    if state == "WAIT_PAYMENT_VALUE":
        users[uid]["payment"] = {
            "method": temp[uid]["method"],
            "value": text
        }
        clear_state(uid)
        await update.message.reply_text("✅ Payment Method Saved Successfully")
        return

    # ── Withdraw Amount ──
    if state == "WAIT_WITHDRAW_AMOUNT":
        if not text.isdigit():
            await update.message.reply_text("❌ Enter a valid number")
            return

        amount = int(text)
        user = get_user(uid)

        if amount > user["balance"]:
            await update.message.reply_text("❌ Insufficient balance")
            return

        await context.bot.send_message(
            ADMIN_ID,
            f"💸 Withdraw Request\nUser: `{uid}`\nAmount: ₹{amount}\nMethod: {user['payment']}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ Payment Cleared",
                        callback_data=f"wd_ok_{uid}_{amount}"
                    ),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                ]
            ])
        )

        clear_state(uid)
        await update.message.reply_text("📤 Withdraw request sent")
        return

# ───────── PHOTO HANDLER (PROOF FIXED) ─────────
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if states.get(uid) == "WAIT_PROOF_PHOTO":
        temp[uid] = {"photo": update.message.photo[-1].file_id}
        states[uid] = "WAIT_PROOF_LINK"
        await update.message.reply_text("🔗 Now send your *refer link*")

# ───────── PROOF ACTION ─────────
async def proof_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action, uid = q.data.split("_")[1:]
    uid = int(uid)

    if action == "ok":
        await context.bot.send_message(uid, "✅ Proof Approved")
    else:
        await context.bot.send_message(uid, "❌ Proof Rejected")

    await q.edit_message_reply_markup(None)

# ───────── WITHDRAW ACTION ─────────
async def withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, uid, amt = q.data.split("_")
    uid, amt = int(uid), int(amt)

    users[uid]["balance"] -= amt
    await context.bot.send_message(
        uid, "✅ Your payment has been sent to your registered method"
    )
    await q.edit_message_reply_markup(None)

# ───────── ADMIN PANEL ─────────
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

# ───────── RUN ─────────
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dtx", admin_panel))

app.add_handler(MessageHandler(filters.Regex("Submit Proof"), submit_proof))
app.add_handler(MessageHandler(filters.Regex("Balance"), balance))
app.add_handler(MessageHandler(filters.Regex("Withdraw"), withdraw))
app.add_handler(MessageHandler(filters.Regex("Payment Method"), payment_method))

app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

app.add_handler(CallbackQueryHandler(payment_select, pattern="pay_"))
app.add_handler(CallbackQueryHandler(proof_action, pattern="proof_"))
app.add_handler(CallbackQueryHandler(withdraw_action, pattern="wd_"))
app.add_handler(CallbackQueryHandler(admin_actions, pattern="admin_"))

print("🤖 Bot running (stable build)...")
app.run_polling()
