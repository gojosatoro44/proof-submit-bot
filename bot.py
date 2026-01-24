import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ========= CONFIG =========
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# ========= MEMORY DB =========
users = {}          # user_id: {balance: int}
proof_state = {}    # user_id: step
proof_data = {}     # user_id: {photo, link}

# ========= KEYBOARDS =========
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Submit Proof", callback_data="submit_proof")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("📍 Where Is My Payment", url="http://t.me/Bot_Tasks_Payment_Bot")],
        [InlineKeyboardButton("🧑‍💻 Support", url="http://t.me/dtxzahid")]
    ])

def cancel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])

def preview_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Submit", callback_data="final_submit"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]
    ])

def admin_kb(uid):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept_{uid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}")
        ]
    ])

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.setdefault(uid, {"balance": 0})

    await update.message.reply_text(
        "✨ **Welcome To Proof Submit Bot** ✨\n\n"
        "📸 Submit Your Proof\n"
        "💰 Check Balance\n\n"
        "⚠️ *Submit Proof On Same ID To Get Payment*",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ========= BUTTON HANDLER =========
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    users.setdefault(uid, {"balance": 0})

    # REMOVE STICKY BUTTONS
    await q.message.edit_reply_markup(None)

    if data == "submit_proof":
        proof_state[uid] = "photo"
        proof_data[uid] = {}
        await q.message.reply_text(
            "📸 **Send Screenshot Where Refer Link Is Visible**",
            parse_mode="Markdown",
            reply_markup=cancel_kb()
        )

    elif data == "balance":
        bal = users[uid]["balance"]
        await q.message.reply_text(
            f"💰 **Balance: ₹{bal}**\n\n"
            "Use Withdraw Button To Withdraw 🤑",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif data == "cancel":
        proof_state.pop(uid, None)
        proof_data.pop(uid, None)
        await q.message.reply_text(
            "❌ **Process Cancelled**",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif data == "final_submit":
        pdata = proof_data.get(uid)
        if not pdata:
            return

        # SEND TO ADMIN
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=pdata["photo"],
            caption=(
                f"`{uid}`\n\n"
                f"🔗 **Refer Link:**\n{pdata['link']}"
            ),
            parse_mode="Markdown",
            reply_markup=admin_kb(uid)
        )

        proof_state.pop(uid, None)
        proof_data.pop(uid, None)

        await q.message.reply_text(
            "✅ **Proof Submitted Successfully**\n"
            "⏳ Wait For Verification",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )

    elif data.startswith("accept_") or data.startswith("reject_"):
        if uid != ADMIN_ID:
            return

        target = int(data.split("_")[1])

        # REMOVE ADMIN BUTTONS
        await q.message.edit_reply_markup(None)

        if data.startswith("accept_"):
            users.setdefault(target, {"balance": 0})
            users[target]["balance"] += 5

            await context.bot.send_message(
                chat_id=target,
                text="🎉 **Proof Verified Successfully**\n"
                     "💰 Payment Will Be Added In 5–10 Minutes",
                parse_mode="Markdown"
            )

            await q.message.reply_text("✅ **Marked As Verified**", parse_mode="Markdown")

        else:
            await context.bot.send_message(
                chat_id=target,
                text="❌ **Proof Rejected**\n"
                     "Refer Not Found So Payment Not Given",
                parse_mode="Markdown"
            )

            await q.message.reply_text("❌ **Marked As Fake**", parse_mode="Markdown")

# ========= MESSAGE HANDLER =========
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid not in proof_state:
        return

    step = proof_state[uid]

    if step == "photo" and update.message.photo:
        proof_data[uid]["photo"] = update.message.photo[-1].file_id
        proof_state[uid] = "link"

        await update.message.reply_text(
            "🔗 **Now Send Your Refer Link**",
            parse_mode="Markdown",
            reply_markup=cancel_kb()
        )

    elif step == "link" and update.message.text:
        proof_data[uid]["link"] = update.message.text

        await update.message.reply_photo(
            photo=proof_data[uid]["photo"],
            caption=(
                "👀 **Preview Your Proof**\n\n"
                f"🔗 {proof_data[uid]['link']}\n\n"
                "⚠️ *Fake Or Same Device Proof = Ban*"
            ),
            parse_mode="Markdown",
            reply_markup=preview_kb()
        )

# ========= MAIN =========
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.ALL, messages))

print("🤖 Bot Running With Polling (Railway Ready)")
app.run_polling()
