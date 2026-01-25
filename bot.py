import os
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, ConversationHandler, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ---- STATES ----
PROOF_SCREENSHOT, PROOF_LINK = range(2)
WITHDRAW_METHOD, WITHDRAW_DETAIL, WITHDRAW_AMOUNT = range(3)
ADMIN_WAIT_INPUT = 10

# ---- STORAGE ----
USER_BALANCE = {}
VERIFIED_IDS = {}        # user_id(str) : amount(float or None)
PROOF_SUBMITTED = set() # telegram user ids
ALL_USERS = set()

ADMIN_MODE = {}         # admin_id : current action

# ---- START ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ALL_USERS.add(update.effective_user.id)
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
    await update.message.reply_text("📸 Send screenshot first:")
    return PROOF_SCREENSHOT

async def proof_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Send screenshot only.")
        return PROOF_SCREENSHOT

    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Now send refer link:")
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    m = re.search(r"start=(\d+)", text)

    if not m:
        await update.message.reply_text("❌ Invalid refer link.")
        return PROOF_LINK

    ref_id = m.group(1)
    tg_id = update.effective_user.id
    PROOF_SUBMITTED.add(tg_id)

    added = 0
    if ref_id in VERIFIED_IDS:
        amt = VERIFIED_IDS[ref_id]
        if amt:
            USER_BALANCE[tg_id] = USER_BALANCE.get(tg_id, 0) + amt
            added = amt
        del VERIFIED_IDS[ref_id]

        await update.message.reply_text(
            "✅ Proof verified successfully\n"
            "Payment will be added in 5 minutes"
        )
    else:
        await update.message.reply_text(
            "❌ Proof rejected due to same device/fake proof/refer"
        )

    await context.bot.send_photo(
        ADMIN_ID,
        photo=context.user_data["photo"],
        caption=(
            f"📥 Proof Record\n"
            f"User: {tg_id}\n"
            f"Refer ID: {ref_id}\n"
            f"Amount Added: ₹{added}"
        )
    )
    return ConversationHandler.END

# ---- WITHDRAW ----
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup([["UPI", "VSV", "FXL"]], resize_keyboard=True)
    await update.message.reply_text("Choose withdraw method:", reply_markup=kb)
    return WITHDRAW_METHOD

async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["method"] = update.message.text
    await update.message.reply_text("Send payment detail:")
    return WITHDRAW_DETAIL

async def withdraw_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text
    await update.message.reply_text("Send amount:")
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amt = int(update.message.text)
    uid = update.effective_user.id
    bal = USER_BALANCE.get(uid, 0)

    if amt > bal:
        await update.message.reply_text("❌ Insufficient balance")
        return ConversationHandler.END

    USER_BALANCE[uid] = bal - amt
    await update.message.reply_text("✅ Withdraw request sent")

    await context.bot.send_message(
        ADMIN_ID,
        f"Withdraw\nUser: {uid}\nAmount: ₹{amt}"
    )
    return ConversationHandler.END

# ---- ADMIN PANEL ----
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    kb = [
        ["➕ Add Balance", "➖ Remove Balance"],
        ["📋 Verified IDs", "👥 Total Users"],
        ["🔍 Check Detail"]
    ]
    await update.message.reply_text(
        "Admin Panel",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text
    ADMIN_MODE[ADMIN_ID] = text

    if text == "📋 Verified IDs":
        await update.message.reply_text(
            "Send verified IDs:\nUSER_ID\nor\nUSER_ID AMOUNT"
        )
    elif text == "➕ Add Balance":
        await update.message.reply_text("Send: USER_ID AMOUNT")
    elif text == "➖ Remove Balance":
        await update.message.reply_text("Send: USER_ID AMOUNT")
    elif text == "👥 Total Users":
        await update.message.reply_text(f"Total Users: {len(ALL_USERS)}")
    elif text == "🔍 Check Detail":
        await update.message.reply_text("Send User ID")

async def admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    mode = ADMIN_MODE.get(ADMIN_ID)
    parts = update.message.text.split()

    if mode == "📋 Verified IDs":
        uid = parts[0]
        amt = float(parts[1]) if len(parts) == 2 else None
        VERIFIED_IDS[uid] = amt
        await update.message.reply_text("✅ Verified ID saved")

    elif mode == "➕ Add Balance":
        uid, amt = int(parts[0]), float(parts[1])
        USER_BALANCE[uid] = USER_BALANCE.get(uid, 0) + amt
        await update.message.reply_text("✅ Balance added")

    elif mode == "➖ Remove Balance":
        uid, amt = int(parts[0]), float(parts[1])
        USER_BALANCE[uid] = max(0, USER_BALANCE.get(uid, 0) - amt)
        await update.message.reply_text("✅ Balance removed")

    elif mode == "🔍 Check Detail":
        uid = int(parts[0])
        await update.message.reply_text(
            f"User ID: {uid}\n"
            f"Balance: ₹{USER_BALANCE.get(uid,0)}\n"
            f"Proof Submitted: {'Yes' if uid in PROOF_SUBMITTED else 'No'}"
        )

# ---- MAIN ----
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    app.add_handler(MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof))
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw_start))

    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), admin_actions))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), admin_input))

    proof_conv = ConversationHandler(
        entry_points=[],
        states={
            PROOF_SCREENSHOT: [MessageHandler(filters.PHOTO, proof_screenshot)],
            PROOF_LINK: [MessageHandler(filters.TEXT, proof_link)]
        },
        fallbacks=[]
    )

    withdraw_conv = ConversationHandler(
        entry_points=[],
        states={
            WITHDRAW_METHOD: [MessageHandler(filters.TEXT, withdraw_method)],
            WITHDRAW_DETAIL: [MessageHandler(filters.TEXT, withdraw_detail)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT, withdraw_amount)]
        },
        fallbacks=[]
    )

    app.add_handler(proof_conv)
    app.add_handler(withdraw_conv)

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
