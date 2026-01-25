import os, re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ─── STATES ───
PROOF_SCREENSHOT, PROOF_LINK = range(2)
WITHDRAW_METHOD, WITHDRAW_DETAIL, WITHDRAW_AMOUNT = range(3)

# ─── STORAGE ───
USER_BALANCE = {}
VERIFIED_IDS = {}      # userid: amount or None
PROOF_SUBMITTED = set()
ALL_USERS = set()
ADMIN_MODE = {}

# ─── MENUS ───
MAIN_MENU = ReplyKeyboardMarkup(
    [["📤 Submit Proof"],
     ["💰 Balance", "💸 Withdraw"],
     ["🆘 Support"]],
    resize_keyboard=True
)

ADMIN_MENU = ReplyKeyboardMarkup(
    [["➕ Add Balance", "➖ Remove Balance"],
     ["📋 Verified IDs", "👥 Total Users"],
     ["🔍 Check Detail"]],
    resize_keyboard=True
)

# ─── HELPERS ───
def is_number(x):
    try:
        float(x)
        return True
    except:
        return False

# ─── START ───
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ALL_USERS.add(update.effective_user.id)
    await update.message.reply_text("👋 Welcome to Task Bot", reply_markup=MAIN_MENU)

# ─── USER ───
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"💰 Balance: ₹{USER_BALANCE.get(update.effective_user.id,0)}")

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆘 Contact admin for support")

# ─── SUBMIT PROOF ───
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Send proof screenshot:")
    return PROOF_SCREENSHOT

async def proof_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Screenshot only")
        return PROOF_SCREENSHOT
    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Send refer link:")
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    m = re.search(r"start=(\d+)", text)
    uid = update.effective_user.id
    PROOF_SUBMITTED.add(uid)

    status = "❌ REJECTED"
    added = 0

    if m:
        ref = m.group(1)
        if ref in VERIFIED_IDS:
            amt = VERIFIED_IDS.pop(ref)
            status = "✅ VERIFIED"
            if amt:
                USER_BALANCE[uid] = USER_BALANCE.get(uid,0) + amt
                added = amt
            await update.message.reply_text(
                "✅ Proof verified\nPayment will be added in 5 minutes"
            )
        else:
            await update.message.reply_text(
                "❌ Proof rejected due to same device/fake proof/refer"
            )
    else:
        await update.message.reply_text("❌ Invalid refer link")

    await context.bot.send_photo(
        ADMIN_ID,
        photo=context.user_data["photo"],
        caption=(
            f"📥 Proof Record\n"
            f"Telegram ID: {uid}\n"
            f"Status: {status}\n"
            f"Amount Added: ₹{added}"
        )
    )
    return ConversationHandler.END

# ─── WITHDRAW ───
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup(
        [["UPI", "VSV", "FXL"], ["❌ Cancel"]],
        resize_keyboard=True
    )
    await update.message.reply_text("Choose withdraw method:", reply_markup=kb)
    return WITHDRAW_METHOD

async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "❌ Cancel":
        await update.message.reply_text("Cancelled", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    context.user_data["method"] = text
    await update.message.reply_text(
        "Send UPI ID:" if text=="UPI" else "Send registered number:"
    )
    return WITHDRAW_DETAIL

async def withdraw_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text
    await update.message.reply_text("Send amount:")
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not is_number(text):
        await update.message.reply_text("❌ Enter valid amount")
        return WITHDRAW_AMOUNT

    amt = float(text)
    uid = update.effective_user.id
    if amt > USER_BALANCE.get(uid,0):
        await update.message.reply_text("❌ Insufficient balance", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    USER_BALANCE[uid] -= amt
    await update.message.reply_text("✅ Withdraw request sent", reply_markup=MAIN_MENU)

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw Request\nUser: {uid}\nAmount: ₹{amt}"
    )
    return ConversationHandler.END

# ─── ADMIN ───
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("Admin Panel", reply_markup=ADMIN_MENU)

async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    ADMIN_MODE[ADMIN_ID] = update.message.text

    if "Balance" in update.message.text:
        await update.message.reply_text("Send: USER_ID AMOUNT")
    elif "Verified" in update.message.text:
        await update.message.reply_text("Send: USER_ID or USER_ID AMOUNT")
    elif "Check" in update.message.text:
        await update.message.reply_text("Send User ID")
    elif "Total" in update.message.text:
        await update.message.reply_text(f"Total Users: {len(ALL_USERS)}")

async def admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID or ADMIN_ID not in ADMIN_MODE:
        return

    parts = update.message.text.split()
    mode = ADMIN_MODE[ADMIN_ID]

    if "Verified" in mode:
        uid = parts[0]
        amt = float(parts[1]) if len(parts)==2 and is_number(parts[1]) else None
        VERIFIED_IDS[uid] = amt
        await update.message.reply_text("✅ Verified ID saved")

    elif "Add" in mode and len(parts)==2 and is_number(parts[1]):
        uid, amt = int(parts[0]), float(parts[1])
        USER_BALANCE[uid] = USER_BALANCE.get(uid,0) + amt
        await update.message.reply_text("✅ Balance added")

    elif "Remove" in mode and len(parts)==2 and is_number(parts[1]):
        uid, amt = int(parts[0]), float(parts[1])
        USER_BALANCE[uid] = max(0, USER_BALANCE.get(uid,0)-amt)
        await update.message.reply_text("✅ Balance removed")

    elif "Check" in mode and parts[0].isdigit():
        uid = int(parts[0])
        await update.message.reply_text(
            f"User ID: {uid}\n"
            f"Balance: ₹{USER_BALANCE.get(uid,0)}\n"
            f"Proof Submitted: {'Yes' if uid in PROOF_SUBMITTED else 'No'}"
        )

# ─── MAIN ───
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))

    app.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
            states={
                PROOF_SCREENSHOT: [MessageHandler(filters.PHOTO, proof_screenshot)],
                PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_link)]
            },
            fallbacks=[]
        )
    )

    app.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw_start)],
            states={
                WITHDRAW_METHOD: [MessageHandler(filters.TEXT, withdraw_method)],
                WITHDRAW_DETAIL: [MessageHandler(filters.TEXT, withdraw_detail)],
                WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT, withdraw_amount)]
            },
            fallbacks=[]
        )
    )

    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), admin_button))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMIN_ID), admin_input))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
