import os, json, time
from telegram import (
    Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

DATA = "data"
os.makedirs(DATA, exist_ok=True)

USERS = f"{DATA}/users.json"
VERIFIED = f"{DATA}/verified.json"
SETTINGS = f"{DATA}/settings.json"
PROOFS = f"{DATA}/proofs.json"

# ========= STATES =========
(
    PROOF_SS, PROOF_LINK,
    WD_METHOD, WD_DETAIL, WD_AMOUNT,
    ADD_BAL, REM_BAL, ADD_VER, CHECK_USER
) = range(9)

# ========= UTILS =========
def load(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)
    with open(path) as f:
        return json.load(f)

def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def main_menu():
    return ReplyKeyboardMarkup(
        [
            ["📤 Submit Proof"],
            ["💰 Balance", "💸 Withdraw"],
            ["🆘 Support"]
        ],
        resize_keyboard=True
    )

def cancel_menu():
    return ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True)

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    users.setdefault(uid, {"balance": 0, "proofs": 0})
    save(USERS, users)

    await update.message.reply_text(
        "👋 Welcome to Task Bot",
        reply_markup=main_menu()
    )

# ========= CANCEL =========
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled", reply_markup=main_menu())
    return ConversationHandler.END

# ========= SUPPORT =========
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "If you face any issue,\nContact Owner: @DTXZAHID"
    )

# ========= BALANCE =========
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load(USERS, {})
    bal = users[str(update.effective_user.id)]["balance"]
    await update.message.reply_text(f"💰 Balance: ₹{bal}")

# ========= SUBMIT PROOF =========
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Send Screenshot Proof",
        reply_markup=cancel_menu()
    )
    return PROOF_SS

async def proof_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return PROOF_SS
    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Now send refer link")
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    uid = str(update.effective_user.id)

    users = load(USERS, {})
    verified = load(VERIFIED, {})
    proofs = load(PROOFS, [])

    status = "REJECTED"
    added = 0

    for vid, amt in list(verified.items()):
        if vid in link:
            status = "VERIFIED"
            added = float(amt)
            users[uid]["balance"] += added
            users[uid]["proofs"] += 1
            del verified[vid]
            break

    save(USERS, users)
    save(VERIFIED, verified)

    proofs.append({
        "uid": uid,
        "link": link,
        "status": status,
        "amount": added
    })
    save(PROOFS, proofs)

    await context.bot.send_photo(
        ADMIN_ID,
        context.user_data["photo"],
        caption=(
            f"📥 Proof\n"
            f"User: {uid}\n"
            f"Status: {status}\n"
            f"Amount: ₹{added}\n"
            f"Link: {link}"
        )
    )

    if status == "VERIFIED":
        await update.message.reply_text(
            "✅ Proof verified\n💰 Amount will be added in 5 minutes",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "❌ Proof rejected due to fake/same device",
            reply_markup=main_menu()
        )

    return ConversationHandler.END

# ========= WITHDRAW =========
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup(
        [["UPI", "VSV", "FXL"], ["❌ Cancel"]],
        resize_keyboard=True
    )
    await update.message.reply_text("Choose withdraw method", reply_markup=kb)
    return WD_METHOD

async def wd_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    method = update.message.text
    if method not in ["UPI", "VSV", "FXL"]:
        return WD_METHOD

    context.user_data["method"] = method
    msg = "Send UPI ID" if method == "UPI" else "Send registered number"
    await update.message.reply_text(msg, reply_markup=cancel_menu())
    return WD_DETAIL

async def wd_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text
    method = context.user_data["method"]
    min_amt = 5 if method == "UPI" else 2
    await update.message.reply_text(
        f"Enter amount\nMinimum ₹{min_amt}"
    )
    return WD_AMOUNT

async def wd_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return WD_AMOUNT

    amt = int(update.message.text)
    method = context.user_data["method"]
    min_amt = 5 if method == "UPI" else 2

    users = load(USERS, {})
    uid = str(update.effective_user.id)

    if amt < min_amt or users[uid]["balance"] < amt:
        await update.message.reply_text("❌ Invalid amount", reply_markup=main_menu())
        return ConversationHandler.END

    users[uid]["balance"] -= amt
    save(USERS, users)

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw Request\n"
        f"User: {uid}\n"
        f"Method: {method}\n"
        f"Detail: {context.user_data['detail']}\n"
        f"Amount: ₹{amt}"
    )

    await update.message.reply_text(
        "✅ Withdraw request sent",
        reply_markup=main_menu()
    )
    return ConversationHandler.END

# ========= ADMIN =========
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

# ========= ADMIN ACTIONS =========
async def add_bal(update, context):
    await update.message.reply_text("Send: USER_ID AMOUNT")
    return ADD_BAL

async def add_bal_do(update, context):
    uid, amt = update.message.text.split()
    users = load(USERS, {})
    users.setdefault(uid, {"balance": 0, "proofs": 0})
    users[uid]["balance"] += float(amt)
    save(USERS, users)
    await update.message.reply_text("✅ Added", reply_markup=main_menu())
    return ConversationHandler.END

async def ver_ids(update, context):
    await update.message.reply_text("Send: USER_ID or USER_ID AMOUNT")
    return ADD_VER

async def ver_ids_do(update, context):
    parts = update.message.text.split()
    vid = parts[0]
    amt = float(parts[1]) if len(parts) > 1 else 0
    v = load(VERIFIED, {})
    v[vid] = amt
    save(VERIFIED, v)
    await update.message.reply_text("✅ Saved", reply_markup=main_menu())
    return ConversationHandler.END

async def total_users(update, context):
    users = load(USERS, {})
    await update.message.reply_text(f"👥 Total Users: {len(users)}")

async def check_user(update, context):
    await update.message.reply_text("Send User ID")
    return CHECK_USER

async def check_user_do(update, context):
    users = load(USERS, {})
    uid = update.message.text
    if uid in users:
        u = users[uid]
        await update.message.reply_text(
            f"User: {uid}\nBalance: ₹{u['balance']}\nProofs: {u['proofs']}"
        )
    else:
        await update.message.reply_text("❌ Not found")
    return ConversationHandler.END

# ========= MAIN =========
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(MessageHandler(filters.Regex("^👥 Total Users$"), total_users))
    app.add_handler(MessageHandler(filters.Regex("^❌ Cancel$"), cancel))

    app.add_handler(ConversationHandler(
        [MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        {PROOF_SS: [MessageHandler(filters.PHOTO, proof_ss)],
         PROOF_LINK: [MessageHandler(filters.TEXT, proof_link)]},
        [MessageHandler(filters.Regex("^❌ Cancel$"), cancel)]
    ))

    app.add_handler(ConversationHandler(
        [MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw)],
        {
            WD_METHOD: [MessageHandler(filters.TEXT, wd_method)],
            WD_DETAIL: [MessageHandler(filters.TEXT, wd_detail)],
            WD_AMOUNT: [MessageHandler(filters.TEXT, wd_amount)]
        },
        [MessageHandler(filters.Regex("^❌ Cancel$"), cancel)]
    ))

    app.add_handler(ConversationHandler(
        [MessageHandler(filters.Regex("^➕ Add Balance$"), add_bal)],
        {ADD_BAL: [MessageHandler(filters.TEXT, add_bal_do)]},
        []
    ))

    app.add_handler(ConversationHandler(
        [MessageHandler(filters.Regex("^📋 Verified IDs$"), ver_ids)],
        {ADD_VER: [MessageHandler(filters.TEXT, ver_ids_do)]},
        []
    ))

    app.add_handler(ConversationHandler(
        [MessageHandler(filters.Regex("^🔍 Check Detail$"), check_user)],
        {CHECK_USER: [MessageHandler(filters.TEXT, check_user_do)]},
        []
    ))

    app.run_polling()

if __name__ == "__main__":
    main()
