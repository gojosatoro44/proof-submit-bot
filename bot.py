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
import os

# ========= CONFIG =========
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# ========= IN-MEMORY DB =========
users = {}          # user_id: {"balance": 0, "payment": {}}
withdraw_states = {}  # user_id: step data
proof_states = {}     # user_id: proof step

# ========= KEYBOARDS =========
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Submit Proof", callback_data="submit_proof")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("❤‍🔥 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🤯 Payment Method", callback_data="payment_method")],
        [InlineKeyboardButton("❓ Help", callback_data="help")],
        [InlineKeyboardButton("💬 Support", url="http://t.me/dtxzahid")],
        [InlineKeyboardButton("💸 Where Is My Payment", url="http://t.me/Bot_Tasks_Payment_Bot")]
    ])

def cancel_btn(tag):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{tag}")]
    ])

def admin_proof_buttons(user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"proof_accept|{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"proof_reject|{user_id}")
        ]
    ])

def withdraw_methods():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 VSV", callback_data="wm_vsv"),
            InlineKeyboardButton("💳 FXL", callback_data="wm_fxl"),
            InlineKeyboardButton("🏦 UPI", callback_data="wm_upi")
        ],
        [InlineKeyboardButton("❌ Cancel Withdraw", callback_data="cancel_withdraw")]
    ])

def withdraw_confirm():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Submit Withdraw", callback_data="withdraw_submit"),
            InlineKeyboardButton("❌ Cancel Withdraw", callback_data="cancel_withdraw")
        ]
    ])

def admin_withdraw_buttons(user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💸 Payment Cleared", callback_data=f"pay_done|{user_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"pay_cancel|{user_id}")
        ]
    ])

def payment_methods():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 VSV", callback_data="pm_vsv"),
            InlineKeyboardButton("💳 FXL", callback_data="pm_fxl"),
            InlineKeyboardButton("🏦 UPI", callback_data="pm_upi")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_pm")]
    ])

# ========= COMMANDS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    users.setdefault(user_id, {"balance": 0, "payment": {}})

    await update.message.reply_text(
        "**👋 Welcome To Proof Submit Bot 🚀**\n\n"
        "**Earn By Submitting Proof & Withdraw Easily 🤑**",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"**👑 Admin Panel**\n\n"
        f"**👥 Total Users:** `{len(users)}`",
        parse_mode="Markdown"
    )

# ========= CALLBACK HANDLER =========
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    users.setdefault(uid, {"balance": 0, "payment": {}})

    data = q.data

    # ---- BALANCE ----
    if data == "balance":
        bal = users[uid]["balance"]
        await q.message.reply_text(
            f"**💰 Balance: ₹{bal}\n\n"
            "Use 'Withdraw' Button To Withdraw Your Balance 🤑**",
            parse_mode="Markdown"
        )

    # ---- SUBMIT PROOF ----
    elif data == "submit_proof":
        proof_states[uid] = {"step": "photo"}
        await q.message.reply_text(
            "**📸 Send Screenshot Where Refer Link Is Visible**",
            reply_markup=cancel_btn("proof"),
            parse_mode="Markdown"
        )

    # ---- WITHDRAW ----
    elif data == "withdraw":
        withdraw_states[uid] = {"step": "amount"}
        await q.message.reply_text(
            "**💸 Enter Amount You Want To Withdraw**",
            reply_markup=cancel_btn("withdraw"),
            parse_mode="Markdown"
        )

    # ---- PAYMENT METHOD ----
    elif data == "payment_method":
        await q.message.reply_text(
            "**🤯 Select Payment Method**",
            reply_markup=payment_methods(),
            parse_mode="Markdown"
        )

    # ---- PAYMENT METHOD SAVE ----
    elif data.startswith("pm_"):
        method = data.split("_")[1]
        withdraw_states[uid] = {"step": "save_pm", "method": method}
        await q.message.reply_text(
            "**📥 Send Your UPI ID Or Registered Number**",
            reply_markup=cancel_btn("pm"),
            parse_mode="Markdown"
        )

    # ---- WITHDRAW METHOD ----
    elif data.startswith("wm_"):
        withdraw_states[uid]["method"] = data.split("_")[1]
        withdraw_states[uid]["step"] = "confirm"
        info = withdraw_states[uid]
        await q.message.reply_text(
            f"**📄 Withdraw Preview**\n\n"
            f"**Amount:** ₹{info['amount']}\n"
            f"**Method:** {info['method'].upper()}**",
            reply_markup=withdraw_confirm(),
            parse_mode="Markdown"
        )

    # ---- SUBMIT WITHDRAW ----
    elif data == "withdraw_submit":
        info = withdraw_states.pop(uid)
        await context.bot.send_message(
            ADMIN_ID,
            f"**💸 Withdraw Request**\n\n"
            f"`{uid}`\n"
            f"**Amount:** ₹{info['amount']}\n"
            f"**Method:** {info['method'].upper()}\n"
            f"**Detail:** {users[uid]['payment'].get(info['method'], 'N/A')}**",
            reply_markup=admin_withdraw_buttons(uid),
            parse_mode="Markdown"
        )
        await q.message.reply_text("**✅ Withdraw Request Sent To Admin**", parse_mode="Markdown")

    # ---- CANCELS ----
    elif data.startswith("cancel"):
        proof_states.pop(uid, None)
        withdraw_states.pop(uid, None)
        await q.message.reply_text("**❌ Cancelled**", reply_markup=main_menu(), parse_mode="Markdown")

    # ---- ADMIN ACTIONS ----
    elif data.startswith("proof_accept"):
        tuid = int(data.split("|")[1])
        users[tuid]["balance"] += 10
        await context.bot.send_message(
            tuid,
            "**✅ Proof Verified!\nPayment Will Be Added In 5-10 Minutes 💰**",
            parse_mode="Markdown"
        )

    elif data.startswith("proof_reject"):
        tuid = int(data.split("|")[1])
        await context.bot.send_message(
            tuid,
            "**❌ Proof Rejected!\nPayment Not Added**",
            parse_mode="Markdown"
        )

    elif data.startswith("pay_done"):
        tuid = int(data.split("|")[1])
        await context.bot.send_message(
            tuid,
            "**💸 Your Payment Has Been Sent To Your Registered Method**",
            parse_mode="Markdown"
        )

# ========= MESSAGE HANDLER =========
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text if update.message.text else ""

    # ---- PROOF FLOW ----
    if uid in proof_states:
        state = proof_states[uid]

        if state["step"] == "photo" and update.message.photo:
            state["photo"] = update.message.photo[-1].file_id
            state["step"] = "link"
            await update.message.reply_text(
                "**🔗 Now Send Your Refer Link**",
                reply_markup=cancel_btn("proof"),
                parse_mode="Markdown"
            )

        elif state["step"] == "link":
            await context.bot.send_photo(
                ADMIN_ID,
                state["photo"],
                caption=f"`{uid}`\n**Refer Link:** {text}**",
                reply_markup=admin_proof_buttons(uid),
                parse_mode="Markdown"
            )
            proof_states.pop(uid)
            await update.message.reply_text("**✅ Proof Submitted Successfully**", parse_mode="Markdown")

    # ---- WITHDRAW FLOW ----
    elif uid in withdraw_states:
        ws = withdraw_states[uid]

        if ws["step"] == "amount":
            amt = int(text)
            if amt > users[uid]["balance"]:
                await update.message.reply_text("**❌ Insufficient Balance**", parse_mode="Markdown")
                return
            ws["amount"] = amt
            ws["step"] = "method"
            await update.message.reply_text(
                "**💳 Select Withdraw Method**",
                reply_markup=withdraw_methods(),
                parse_mode="Markdown"
            )

        elif ws["step"] == "save_pm":
            users[uid]["payment"][ws["method"]] = text
            withdraw_states.pop(uid)
            await update.message.reply_text("**✅ Payment Method Saved**", parse_mode="Markdown")

# ========= MAIN =========
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dtx", admin_panel))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.ALL, messages))

    print("Bot Running...")
    app.run_polling()
