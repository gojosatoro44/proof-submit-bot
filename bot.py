import json
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ===== CONFIG (VARIABLE BASED) =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN or ADMIN_ID == 0:
    raise RuntimeError("BOT_TOKEN or ADMIN_ID missing in environment variables")

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

def ensure_user(uid):
    users = load_json(USERS_FILE, {})
    if str(uid) not in users:
        users[str(uid)] = {"balance": 0, "proofs": 0}
        save_json(USERS_FILE, users)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user.id)

    kb = ReplyKeyboardMarkup(
        [
            ["📤 Submit Proof"],
            ["💰 Balance", "💸 Withdraw"],
            ["🆘 Support"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text("👋 Welcome to Task Bot", reply_markup=kb)

# ===== USER =====
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_json(USERS_FILE, {})
    bal = users.get(str(update.effective_user.id), {}).get("balance", 0)
    await update.message.reply_text(f"💰 Balance: ₹{bal}")

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 Support\nContact @DTXZAHID for any issue"
    )

# ===== WITHDRAW =====
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter withdraw amount:")
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("❌ Enter numbers only")
        return WITHDRAW_AMOUNT

    amt = int(update.message.text)
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
    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Now send refer link")
    return SUBMIT_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    uid = update.effective_user.id

    verified = load_json(VERIFIED_FILE, {})
    users = load_json(USERS_FILE, {})
    proofs = load_json(PROOFS_FILE, [])

    status = "REJECTED"
    amount = 0

    for vid, amt in list(verified.items()):
        if vid in link:
            status = "VERIFIED"
            amount = float(amt)
            users[str(uid)]["balance"] += amount
            users[str(uid)]["proofs"] += 1
            del verified[vid]
            break

    save_json(VERIFIED_FILE, verified)
    save_json(USERS_FILE, users)

    proofs.append({
        "user": uid,
        "link": link,
        "status": status,
        "amount": amount
    })
    save_json(PROOFS_FILE, proofs)

    await context.bot.send_message(
        ADMIN_ID,
        f"📥 Proof Record\n"
        f"User: {uid}\n"
        f"Status: {status}\n"
        f"Amount: ₹{amount}"
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

    kb = ReplyKeyboardMarkup(
        [
            ["➕ Add Balance", "➖ Remove Balance"],
            ["📋 Verified IDs", "👥 Total Users"],
            ["🔍 Check Detail"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text("Admin Panel", reply_markup=kb)

async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_json(USERS_FILE, {})
    await update.message.reply_text(f"👥 Total Users: {len(users)}")

# ===== ADMIN ACTIONS =====
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send: USER_ID AMOUNT")
    return ADD_BALANCE

async def add_balance_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid, amt = update.message.text.split()
    amt = float(amt)

    users = load_json(USERS_FILE, {})
    users.setdefault(uid, {"balance": 0, "proofs": 0})
    users[uid]["balance"] += amt
    save_json(USERS_FILE, users)

    await update.message.reply_text("✅ Balance added")
    return ConversationHandler.END

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
            f"🆔 {uid}\n💰 Balance: ₹{u['balance']}\n📤 Proofs: {u['proofs']}"
        )
    return ConversationHandler.END

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(MessageHandler(filters.Regex("^👥 Total Users$"), total_users))

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
