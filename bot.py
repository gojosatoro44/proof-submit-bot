import os, json, re, requests
from telegram import (
    Update, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
FORCE_JOIN_CHANNEL = "@TaskByZahid"

DATA = "data"
USERS = f"{DATA}/users.json"
VERIFIED = f"{DATA}/verified.json"
SETTINGS = f"{DATA}/settings.json"
os.makedirs(DATA, exist_ok=True)

# ================= STATES =================
(
    PROOF_SCREEN, PROOF_LINK,
    WD_METHOD, WD_DETAIL, WD_AMOUNT,
    ADD_VER
) = range(6)

# ================= DEFAULT SETTINGS =================
DEFAULT_SETTINGS = {
    "VSV": {"enabled": False, "api": ""},
    "FXL": {"enabled": False, "api": ""}
}

# ================= UTILS =================
def load(p, d):
    if not os.path.exists(p):
        with open(p, "w") as f: json.dump(d, f)
    with open(p) as f: return json.load(f)

def save(p, d):
    with open(p, "w") as f: json.dump(d, f, indent=2)

def menu():
    return ReplyKeyboardMarkup(
        [["📤 Submit Proof"],
         ["💰 Balance", "💸 Withdraw"],
         ["🆘 Support"]],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        [["➕ Add Verified ID"],
         ["⚙ Auto Withdraw Settings"],
         ["👥 Total Users"]],
        resize_keyboard=True
    )

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    users.setdefault(uid, {"balance": 0, "proofs": 0})
    save(USERS, users)
    await update.message.reply_text("👋 Welcome to Task Bot", reply_markup=menu())

# ================= BALANCE =================
async def balance(update, context):
    bal = load(USERS, {})[str(update.effective_user.id)]["balance"]
    await update.message.reply_text(f"💰 Your Balance: ₹{bal}")

# ================= SUPPORT =================
async def support(update, context):
    await update.message.reply_text("🆘 Contact Owner: @DTXZAHID")

# ================= WITHDRAW =================
async def withdraw(update, context):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("UPI", callback_data="upi"),
         InlineKeyboardButton("VSV", callback_data="vsv"),
         InlineKeyboardButton("FXL", callback_data="fxl")]
    ])
    await update.message.reply_text("💸 Select withdraw method", reply_markup=kb)
    return WD_METHOD

async def wd_method(update, context):
    q = update.callback_query; await q.answer()
    context.user_data["method"] = q.data.upper()
    await q.message.reply_text("Send UPI ID / Registered Number")
    return WD_DETAIL

async def wd_detail(update, context):
    context.user_data["detail"] = update.message.text.strip()
    await update.message.reply_text("Enter amount (Minimum ₹5)")
    return WD_AMOUNT

async def wd_amount(update, context):
    if not re.fullmatch(r"\d+", update.message.text):
        await update.message.reply_text("❌ Enter numbers only")
        return WD_AMOUNT

    amt = int(update.message.text)
    uid = str(update.effective_user.id)
    users = load(USERS, {})
    bal = users[uid]["balance"]

    if amt < 5:
        await update.message.reply_text("❌ Minimum withdraw is ₹5")
        return ConversationHandler.END

    if bal < amt:
        await update.message.reply_text("❌ Insufficient balance")
        return ConversationHandler.END

    method = context.user_data["method"]
    settings = load(SETTINGS, DEFAULT_SETTINGS)

    users[uid]["balance"] -= amt
    save(USERS, users)

    # AUTO WITHDRAW
    if method in ("VSV", "FXL") and settings[method]["enabled"]:
        await update.message.reply_text("⏳ Processing automatic withdraw...")
        # 🔴 REAL API CALL GOES HERE (safe placeholder)
        # response = requests.post(settings[method]["api"], data={...})
        await update.message.reply_text("✅ Withdraw successful (Auto)")
    else:
        await context.bot.send_message(
            ADMIN_ID,
            f"💸 Withdraw Request\nUser: {uid}\n₹{amt}\nMethod: {method}\nDetail: {context.user_data['detail']}"
        )
        await update.message.reply_text("✅ Withdraw request sent")

    return ConversationHandler.END

# ================= ADMIN =================
async def admin(update, context):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text("⚙ Admin Panel", reply_markup=admin_menu())

async def auto_settings(update, context):
    s = load(SETTINGS, DEFAULT_SETTINGS)
    await update.message.reply_text(
        f"⚙ Auto Withdraw\n"
        f"VSV: {'ON' if s['VSV']['enabled'] else 'OFF'}\n"
        f"FXL: {'ON' if s['FXL']['enabled'] else 'OFF'}\n\n"
        f"Send:\nVSV ON api_link\nFXL OFF"
    )

async def set_auto(update, context):
    s = load(SETTINGS, DEFAULT_SETTINGS)
    p = update.message.text.split(maxsplit=2)
    if len(p) >= 2:
        key = p[0].upper()
        s[key]["enabled"] = p[1].upper() == "ON"
        if len(p) == 3:
            s[key]["api"] = p[2]
        save(SETTINGS, s)
        await update.message.reply_text("✅ Updated")

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(MessageHandler(filters.Regex("^⚙ Auto Withdraw Settings$"), auto_settings))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^(VSV|FXL)"), set_auto))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw)],
        states={
            WD_METHOD: [CallbackQueryHandler(wd_method)],
            WD_DETAIL: [MessageHandler(filters.TEXT, wd_detail)],
            WD_AMOUNT: [MessageHandler(filters.TEXT, wd_amount)]
        },
        fallbacks=[]
    ))

    app.run_polling()

if __name__ == "__main__":
    main()
