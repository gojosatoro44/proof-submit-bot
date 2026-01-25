import json
import os
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ===== CONFIG =====
BOT_TOKEN = "PASTE_BOT_TOKEN"
ADMIN_ID = 123456789  # int only

DATA_DIR = "data"
USERS_FILE = f"{DATA_DIR}/users.json"
VERIFIED_FILE = f"{DATA_DIR}/verified_ids.json"
PROOFS_FILE = f"{DATA_DIR}/proofs.json"

os.makedirs(DATA_DIR, exist_ok=True)

# ===== STATES =====
(
    SUBMIT_SCREENSHOT, SUBMIT_LINK,
    ADD_BALANCE, REMOVE_BALANCE,
    ADD_VERIFIED, CHECK_DETAIL,
    WITHDRAW_AMOUNT
) = range(7)

# ===== HELPERS =====
def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_user(uid):
    users = load_json(USERS_FILE, {})
    if str(uid) not in users:
        users[str(uid)] = {
            "balance": 0,
            "proofs": 0
        }
        save_json(USERS_FILE, users)
    return users

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_user(update.effective_user.id)

    kb = ReplyKeyboardMarkup([
        ["📤 Submit Proof"],
        ["💰 Balance", "💸 Withdraw"],
        ["🆘 Support"]
    ], resize_keyboard=True)

    await update.message.reply_text(
        "👋 Welcome to Task Bot",
        reply_markup=kb
    )

# ===== BALANCE =====
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_json(USERS_FILE, {})
    bal = users.get(str(update.effective_user.id), {}).get("balance", 0)
    await update.message.reply_text(f"💰 Balance: ₹{bal}")

# ===== WITHDRAW =====
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter withdraw amount:")
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Enter numbers only")
        return WITHDRAW_AMOUNT

    amt = int(text)
    users = load_json(USERS_FILE, {})
    uid = str(update.effective_user.id)

    if users[uid]["balance"] < amt:
        await update.message.reply_text("❌ Insufficient balance")
        return ConversationHandler.END

    users[uid]["balance"] -= amt
    save_json(USERS_FILE, users)

    await update.message.reply_text("✅ Withdraw request submitted")
    return ConversationHandler.END

# ===== SUBMIT PROOF =====
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Send screenshot proof")
    return SUBMIT_SCREENSHOT

async def proof_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Send screenshot only")
        return SUBMIT_SCREENSHOT

    context.user_data["proof_photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Now send refer link")
    return SUBMIT_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    uid = update.effective_user.id

    verified = load_json(VERIFIED_FILE, {})
    users = load_json(USERS_FILE, {})
    proofs = load_json(PROOFS_FILE, [])

    status = "REJECTED"
    added = 0

    for vid, amt in verified.items():
        if vid in link:
            status = "VERIFIED"
            added = float(amt)
            users[str(uid)]["balance"] += added
            users[str(uid)]["proofs"] += 1
            del verified[vid]
            break

    save_json(VERIFIED_FILE, verified)
    save_json(USERS_FILE, users)

    proofs.append({
        "user": uid,
        "link": link,
        "status": status,
        "amount": added
    })
    save_json(PROOFS_FILE, proofs)

    await context.bot.send_message(
        ADMIN_ID,
        f"📥 Proof Record\n"
        f"Telegram ID: {uid}\n"
        f"Status: {'✅ VERIFIED' if status=='VERIFIED' else '❌ REJECTED'}\n"
        f"Amount Added: ₹{added}"
    )

    await update.message.reply_text(
        "✅ Proof verified, payment added"
        if status == "VERIFIED"
        else "❌ Proof rejected"
    )

    return ConversationHandler.END

# ===== ADMIN =====
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    kb = ReplyKeyboardMarkup([
        ["➕ Add Balance", "➖ Remove Balance"],
        ["📋 Verified IDs", "👥 Total Users"],
        ["🔍 Check Detail"]
    ], resize_keyboard=True)

    await update.message.reply_text("Admin Panel", reply_markup=kb)

# ===== ADD BALANCE =====
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send: USER_ID AMOUNT")
    return ADD_BALANCE

async def add_balance_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid, amt = update.message.text.split()
        amt = float(amt)
    except:
        await update.message.reply_text("❌ Format wrong")
        return ADD_BALANCE

    users = load_json(USERS_FILE, {})
    if uid not in users:
        users[uid] = {"balance": 0, "proofs": 0}

    users[uid]["balance"] += amt
    save_json(USERS_FILE, users)

    await update.message.reply_text("✅ Balance added")
    return ConversationHandler.END

# ===== REMOVE BALANCE =====
async def remove_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send: USER_ID AMOUNT")
    return REMOVE_BALANCE

async def remove_balance_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid, amt = update.message.text.split()
        amt = float(amt)
    except:
        await update.message.reply_text("❌ Format wrong")
        return REMOVE_BALANCE

    users = load_json(USERS_FILE, {})
    if uid in users:
        users[uid]["balance"] = max(0, users[uid]["balance"] - amt)
        save_json(USERS_FILE, users)

    await update.message.reply_text("✅ Balance removed")
    return ConversationHandler.END

# ===== VERIFIED IDS =====
async def verified_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send: USER_ID or USER_ID AMOUNT")
    return ADD_VERIFIED

async def verified_ids_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split()
    vid = parts[0]
    amt = float(parts[1]) if len(parts) == 2 else 0

    verified = load_json(VERIFIED_FILE, {})
    verified[vid] = amt
    save_json(VERIFIED_FILE, verified)

    await update.message.reply_text("✅ Verified ID saved")
    return ConversationHandler.END

# ===== CHECK DETAIL =====
async def check_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send User ID")
    return CHECK_DETAIL

async def check_detail_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.text.strip()
    users = load_json(USERS_FILE, {})

    if uid not in users:
        await update.message.reply_text("❌ User not found")
    else:
        u = users[uid]
        await update.message.reply_text(
            f"🆔 {uid}\n"
            f"💰 Balance: ₹{u['balance']}\n"
            f"📤 Proofs: {u['proofs']}"
        )
    return ConversationHandler.END

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw)],
        states={WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT, withdraw_amount)]},
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={
            SUBMIT_SCREENSHOT: [MessageHandler(filters.PHOTO, proof_screenshot)],
            SUBMIT_LINK: [MessageHandler(filters.TEXT, proof_link)]
        },
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Add Balance$"), add_balance)],
        states={ADD_BALANCE: [MessageHandler(filters.TEXT, add_balance_do)]},
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➖ Remove Balance$"), remove_balance)],
        states={REMOVE_BALANCE: [MessageHandler(filters.TEXT, remove_balance_do)]},
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Verified IDs$"), verified_ids)],
        states={ADD_VERIFIED: [MessageHandler(filters.TEXT, verified_ids_do)]},
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔍 Check Detail$"), check_detail)],
        states={CHECK_DETAIL: [MessageHandler(filters.TEXT, check_detail_do)]},
        fallbacks=[]
    ))

    app.run_polling()

if __name__ == "__main__":
    main()
