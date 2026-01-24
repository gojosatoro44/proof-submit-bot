import os
import logging
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

# ========= ENV VARIABLES =========
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# =================================

logging.basicConfig(level=logging.INFO)

users = {}
withdraw_state = {}

# ---------- KEYBOARDS ----------
MAIN_KB = ReplyKeyboardMarkup(
    [
        ["📤 Submit Proof"],
        ["💰 Balance"],
        ["❤️‍🔥 Withdraw"],
        ["🤯 Payment Method"],
        ["📍 Where Is My Payment", "🆘 Support"],
    ],
    resize_keyboard=True,
)

ADMIN_KB = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("➕ Add Balance", callback_data="add_bal")],
        [InlineKeyboardButton("➖ Remove Balance", callback_data="rem_bal")],
        [InlineKeyboardButton("👥 Total Users", callback_data="total_users")],
    ]
)

METHOD_KB = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("VSV", callback_data="method_vsv"),
            InlineKeyboardButton("FXL", callback_data="method_fxl"),
            InlineKeyboardButton("UPI", callback_data="method_upi"),
        ]
    ]
)

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.setdefault(uid, {"balance": 0, "method": None})
    await update.message.reply_text(
        "✨ **Welcome! Bot is Live & Ready** ✨",
        reply_markup=MAIN_KB,
        parse_mode="Markdown",
    )

# ---------- BALANCE ----------
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    bal = users.get(uid, {}).get("balance", 0)
    await update.message.reply_text(
        f"💰 **Your Balance:** ₹{bal}\n\nUse Withdraw button to cash out 🤑",
        parse_mode="Markdown",
    )

# ---------- PAYMENT METHOD ----------
async def payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤯 **Choose Payment Method**",
        reply_markup=METHOD_KB,
        parse_mode="Markdown",
    )

async def set_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    method = q.data.split("_")[1].upper()
    users.setdefault(uid, {"balance": 0, "method": None})

    context.user_data["await_method"] = method

    text = "📨 Send your **UPI ID**" if method == "UPI" else "📞 Send your **Registered Number**"
    await q.message.reply_text(text, parse_mode="Markdown")

async def save_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "await_method" not in context.user_data:
        return

    uid = update.effective_user.id
    method = context.user_data.pop("await_method")
    users[uid]["method"] = f"{method}: {update.message.text}"

    await update.message.reply_text("✅ **Payment Method Saved**", parse_mode="Markdown")

# ---------- WITHDRAW ----------
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = users.get(uid)

    if not user or not user.get("method"):
        await update.message.reply_text("❌ Set payment method first")
        return

    withdraw_state[uid] = "amount"
    await update.message.reply_text("💸 Enter withdraw amount")

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if withdraw_state.get(uid) != "amount":
        return

    try:
        amt = int(update.message.text)
    except:
        await update.message.reply_text("❌ Invalid amount")
        return

    if amt > users[uid]["balance"]:
        await update.message.reply_text("❌ Insufficient balance")
        withdraw_state.pop(uid, None)
        return

    withdraw_state.pop(uid, None)

    await context.bot.send_message(
        ADMIN_ID,
        f"📤 Withdraw Request\n\n👤 `{uid}`\n💰 ₹{amt}\n🏦 {users[uid]['method']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Paid", callback_data=f"pay_ok_{uid}_{amt}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"pay_no_{uid}"),
                ]
            ]
        ),
    )

    await update.message.reply_text("📤 Withdraw request sent")

# ---------- ADMIN ----------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("🛠 **Admin Panel**", reply_markup=ADMIN_KB)

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "total_users":
        await q.message.reply_text(f"👥 Total Users: {len(users)}")
    else:
        context.user_data["admin_action"] = q.data
        await q.message.reply_text("Send:\nUSER_ID AMOUNT")

async def admin_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "admin_action" not in context.user_data:
        return

    try:
        uid, amt = map(int, update.message.text.split())
    except:
        await update.message.reply_text("❌ Invalid format")
        return

    users.setdefault(uid, {"balance": 0, "method": None})

    if context.user_data["admin_action"] == "add_bal":
        users[uid]["balance"] += amt
    else:
        users[uid]["balance"] = max(0, users[uid]["balance"] - amt)

    context.user_data.pop("admin_action")
    await update.message.reply_text("✅ Balance Updated")

# ---------- PAYMENT CONFIRM ----------
async def payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data.startswith("pay_ok"):
        _, uid, amt = q.data.split("_")
        uid, amt = int(uid), int(amt)
        users[uid]["balance"] -= amt
        await context.bot.send_message(uid, "✅ Payment Sent")
        await q.message.edit_text("✅ Paid")

    elif q.data.startswith("pay_no"):
        uid = int(q.data.split("_")[2])
        await context.bot.send_message(uid, "❌ Withdraw Cancelled")
        await q.message.edit_text("❌ Cancelled")

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dtx", admin_panel))

    app.add_handler(MessageHandler(filters.Regex("Balance"), balance))
    app.add_handler(MessageHandler(filters.Regex("Payment Method"), payment_method))
    app.add_handler(MessageHandler(filters.Regex("Withdraw"), withdraw))

    app.add_handler(CallbackQueryHandler(set_method, pattern="^method_"))
    app.add_handler(CallbackQueryHandler(admin_actions))
    app.add_handler(CallbackQueryHandler(payment_done, pattern="^pay_"))

    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), admin_balance))
    app.add_handler(MessageHandler(filters.TEXT, save_method))
    app.add_handler(MessageHandler(filters.TEXT, withdraw_amount))

    app.run_polling()

if __name__ == "__main__":
    main()
