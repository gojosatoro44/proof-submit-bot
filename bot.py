import os, json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

DATA = "data"
os.makedirs(DATA, exist_ok=True)

USERS = f"{DATA}/users.json"
VERIFIED = f"{DATA}/verified.json"

# ---------- utils ----------
def load(path, default):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(default, f)
    with open(path) as f:
        return json.load(f)

def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def ensure_user(uid):
    users = load(USERS, {})
    users.setdefault(uid, {"balance": 0, "proofs": 0})
    save(USERS, users)
    return users

MAIN_MENU = ReplyKeyboardMarkup(
    [["📤 Submit Proof"],
     ["💰 Balance", "💸 Withdraw"],
     ["🆘 Support"]],
    resize_keyboard=True
)

CANCEL = ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True)

# ---------- states ----------
PROOF_SS, PROOF_LINK, WD_METHOD, WD_DETAIL, WD_AMOUNT = range(5)

# ---------- start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(str(update.effective_user.id))
    context.user_data.clear()
    await update.message.reply_text("👋 Welcome to Task Bot", reply_markup=MAIN_MENU)

# ---------- cancel ----------
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# ---------- support ----------
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "If you face any issue,\nContact Owner: @DTXZAHID",
        reply_markup=MAIN_MENU
    )

# ---------- balance ----------
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    users = ensure_user(uid)
    await update.message.reply_text(f"💰 Balance: ₹{users[uid]['balance']}")

# ---------- submit proof ----------
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Send Screenshot", reply_markup=CANCEL)
    return PROOF_SS

async def proof_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return PROOF_SS
    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Send refer link")
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    ensure_user(uid)

    verified = load(VERIFIED, {})
    users = load(USERS, {})

    added = 0
    status = "REJECTED"

    for vid, amt in list(verified.items()):
        if vid in update.message.text:
            status = "VERIFIED"
            added = float(amt)
            users[uid]["balance"] += added
            users[uid]["proofs"] += 1
            del verified[vid]
            break

    save(USERS, users)
    save(VERIFIED, verified)

    await context.bot.send_photo(
        ADMIN_ID,
        context.user_data["photo"],
        caption=f"Proof from {uid}\nStatus: {status}\nAmount: ₹{added}"
    )

    await update.message.reply_text(
        "✅ Proof verified" if status == "VERIFIED" else "❌ Proof rejected",
        reply_markup=MAIN_MENU
    )
    return ConversationHandler.END

# ---------- withdraw ----------
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("in_withdraw"):
        return
    context.user_data["in_withdraw"] = True

    ensure_user(str(update.effective_user.id))
    kb = ReplyKeyboardMarkup(
        [["UPI", "VSV", "FXL"], ["❌ Cancel"]],
        resize_keyboard=True
    )
    await update.message.reply_text("Select withdraw method", reply_markup=kb)
    return WD_METHOD

async def wd_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text not in ["UPI", "VSV", "FXL"]:
        return WD_METHOD
    context.user_data["method"] = update.message.text
    await update.message.reply_text(
        "Send UPI ID" if update.message.text == "UPI" else "Send registered number",
        reply_markup=CANCEL
    )
    return WD_DETAIL

async def wd_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text
    await update.message.reply_text("Enter amount")
    return WD_AMOUNT

async def wd_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    users = ensure_user(uid)

    if not update.message.text.isdigit():
        return WD_AMOUNT

    amt = int(update.message.text)
    min_amt = 5 if context.user_data["method"] == "UPI" else 2

    if amt < min_amt or users[uid]["balance"] < amt:
        context.user_data.clear()
        await update.message.reply_text("❌ Invalid amount", reply_markup=MAIN_MENU)
        return ConversationHandler.END

    users[uid]["balance"] -= amt
    save(USERS, users)

    await context.bot.send_message(
        ADMIN_ID,
        f"Withdraw Request\nUser: {uid}\nAmount: ₹{amt}\nMethod: {context.user_data['method']}"
    )

    context.user_data.clear()
    await update.message.reply_text("✅ Withdraw request sent", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# ---------- main ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))

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
            WD_AMOUNT: [MessageHandler(filters.TEXT, wd_amount)],
        },
        [MessageHandler(filters.Regex("^❌ Cancel$"), cancel)]
    ))

    app.run_polling()

if __name__ == "__main__":
    main()
