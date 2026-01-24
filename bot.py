from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

import os

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

users = {}
proof_state = {}
withdraw_state = {}
admin_state = {}

# ================= KEYBOARDS =================

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📸 Submit Proof", callback_data="submit_proof")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("❤️‍🔥 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🤯 Payment Method", callback_data="payment_method")],
        [InlineKeyboardButton("🆘 Support", url="http://t.me/dtxzahid")],
        [InlineKeyboardButton("💸 Where Is My Payment", url="http://t.me/Bot_Tasks_Payment_Bot")]
    ])

def cancel_btn(back="menu"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{back}")]
    ])

def payment_methods():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 VSV", callback_data="pm|VSV"),
            InlineKeyboardButton("💳 FXL", callback_data="pm|FXL"),
            InlineKeyboardButton("🏦 UPI", callback_data="pm|UPI")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel|menu")]
    ])

def admin_proof_buttons(uid):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"proof_accept|{uid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"proof_reject|{uid}")
        ]
    ])

def admin_withdraw_buttons(uid):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💸 Payment Cleared", callback_data=f"wd_paid|{uid}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"wd_cancel|{uid}")
        ]
    ])

def admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Total Users", callback_data="admin_users")],
        [
            InlineKeyboardButton("➕ Add Balance", callback_data="admin_add"),
            InlineKeyboardButton("➖ Remove Balance", callback_data="admin_remove")
        ]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.setdefault(uid, {"balance": 0, "payment": {}})
    await update.message.reply_text(
        "**🔥 Welcome To Proof Submit Bot 🔥**\n\n"
        "**Complete Task → Submit Proof → Get Paid 💰**",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ================= CALLBACK HANDLER =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    users.setdefault(uid, {"balance": 0, "payment": {}})

    # CANCEL
    if data.startswith("cancel"):
        await q.message.edit_text("**🏠 Main Menu**", reply_markup=main_menu(), parse_mode="Markdown")
        proof_state.pop(uid, None)
        withdraw_state.pop(uid, None)
        return

    # SUBMIT PROOF
    if data == "submit_proof":
        proof_state[uid] = {"step": "photo"}
        await q.message.edit_text(
            "**📸 Send Screenshot With Refer Link Visible**",
            reply_markup=cancel_btn("menu"),
            parse_mode="Markdown"
        )

    # BALANCE
    elif data == "balance":
        bal = users[uid]["balance"]
        await q.message.edit_text(
            f"**💰 Balance: ₹{bal}**\n\n"
            "**Use Withdraw Button To Withdraw Your Balance 🤑**",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )

    # PAYMENT METHOD
    elif data == "payment_method":
        await q.message.edit_text(
            "**🤯 Select Payment Method**",
            reply_markup=payment_methods(),
            parse_mode="Markdown"
        )

    elif data.startswith("pm|"):
        method = data.split("|")[1]
        users[uid]["pm_temp"] = method
        await q.message.edit_text(
            "**📩 Send Your UPI ID Or Registered Number**",
            reply_markup=cancel_btn("menu"),
            parse_mode="Markdown"
        )

    # WITHDRAW
    elif data == "withdraw":
        if not users[uid]["payment"]:
            await q.message.edit_text(
                "**❌ No Payment Method Linked**\n\n"
                "**Please Add Payment Method First 🤯**",
                reply_markup=main_menu(),
                parse_mode="Markdown"
            )
            return
        withdraw_state[uid] = {"step": "amount"}
        await q.message.edit_text(
            "**💸 Enter Amount You Want To Withdraw**",
            reply_markup=cancel_btn("menu"),
            parse_mode="Markdown"
        )

    # ADMIN PANEL
    elif data == "admin_users":
        await q.message.edit_text(
            f"**👥 Total Users: {len(users)}**",
            reply_markup=admin_panel(),
            parse_mode="Markdown"
        )

    elif data in ["admin_add", "admin_remove"]:
        admin_state[uid] = data
        await q.message.edit_text(
            "**✏️ Send UserID Amount**\nExample: `123456 50`",
            reply_markup=cancel_btn("menu"),
            parse_mode="Markdown"
        )

    # PROOF ACTION
    elif data.startswith("proof_accept"):
        tuid = int(data.split("|")[1])
        users[tuid]["balance"] += 10
        await context.bot.send_message(
            tuid,
            "**✅ Bro Apka Refer Count Hogya\nPayment 5–10 Min Me Bot Me Aayega**",
            parse_mode="Markdown"
        )
        await q.message.edit_text("**✅ Proof Accepted**", parse_mode="Markdown")

    elif data.startswith("proof_reject"):
        tuid = int(data.split("|")[1])
        await context.bot.send_message(
            tuid,
            "**❌ Bro Apka Refer Nahi Aaya\nPayment Nahi Milega**",
            parse_mode="Markdown"
        )
        await q.message.edit_text("**❌ Proof Rejected**", parse_mode="Markdown")

    # WITHDRAW ACTION
    elif data.startswith("wd_paid"):
        tuid = int(data.split("|")[1])
        await context.bot.send_message(
            tuid,
            "**💸 Your Payment Has Been Sent To Your Registered Method**",
            parse_mode="Markdown"
        )
        await q.message.edit_text("**✅ Payment Cleared**", parse_mode="Markdown")

    elif data.startswith("wd_cancel"):
        await q.message.edit_text("**❌ Withdraw Cancelled**", parse_mode="Markdown")

# ================= MESSAGE HANDLER =================

async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    users.setdefault(uid, {"balance": 0, "payment": {}})
    text = update.message.text

    # PROOF FLOW
    if uid in proof_state:
        if proof_state[uid]["step"] == "photo" and update.message.photo:
            proof_state[uid]["photo"] = update.message.photo[-1].file_id
            proof_state[uid]["step"] = "link"
            await update.message.reply_text(
                "**🔗 Now Send Refer Link**",
                reply_markup=cancel_btn("menu"),
                parse_mode="Markdown"
            )
            return

        if proof_state[uid]["step"] == "link":
            await context.bot.send_photo(
                ADMIN_ID,
                proof_state[uid]["photo"],
                caption=f"`{uid}`\n\n**🔗 Refer Link:** {text}",
                reply_markup=admin_proof_buttons(uid),
                parse_mode="Markdown"
            )
            proof_state.pop(uid)
            await update.message.reply_text(
                "**✅ Proof Submitted Successfully**",
                reply_markup=main_menu(),
                parse_mode="Markdown"
            )
            return

    # PAYMENT METHOD SAVE
    if "pm_temp" in users[uid]:
        users[uid]["payment"][users[uid]["pm_temp"]] = text
        users[uid].pop("pm_temp")
        await update.message.reply_text(
            "**✅ Payment Method Saved**",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )
        return

    # WITHDRAW AMOUNT
    if uid in withdraw_state:
        amt = int(text)
        if amt > users[uid]["balance"]:
            await update.message.reply_text(
                "**❌ Insufficient Balance**",
                reply_markup=main_menu(),
                parse_mode="Markdown"
            )
            withdraw_state.pop(uid)
            return

        users[uid]["balance"] -= amt
        await context.bot.send_message(
            ADMIN_ID,
            f"**💸 Withdraw Request**\n\n`{uid}`\n₹{amt}\n{users[uid]['payment']}",
            reply_markup=admin_withdraw_buttons(uid),
            parse_mode="Markdown"
        )
        withdraw_state.pop(uid)
        await update.message.reply_text(
            "**📤 Withdraw Request Sent**",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )

    # ADMIN ADD / REMOVE
    if uid == ADMIN_ID and uid in admin_state:
        u, amt = map(int, text.split())
        users.setdefault(u, {"balance": 0, "payment": {}})
        if admin_state[uid] == "admin_add":
            users[u]["balance"] += amt
        else:
            users[u]["balance"] = max(0, users[u]["balance"] - amt)
        admin_state.pop(uid)
        await update.message.reply_text("**✅ Balance Updated**", parse_mode="Markdown")

# ================= ADMIN COMMAND =================

async def dtx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text(
            "**👑 Admin Panel**",
            reply_markup=admin_panel(),
            parse_mode="Markdown"
        )

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dtx", dtx))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, messages))
app.run_polling()
