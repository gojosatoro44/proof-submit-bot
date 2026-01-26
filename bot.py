import os, json
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
os.makedirs(DATA, exist_ok=True)

# ================= STATES =================
(
    PROOF_SCREEN, PROOF_LINK,
    WD_METHOD, WD_DETAIL, WD_AMOUNT,
    ADD_BAL, REM_BAL, ADD_VER, CHECK_USER
) = range(9)

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

async def force_join(update):
    try:
        m = await update.get_bot().get_chat_member(
            FORCE_JOIN_CHANNEL, update.effective_user.id
        )
        return m.status in ("member", "administrator", "creator")
    except:
        return False

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join(update):
        btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL[1:]}")]]
        )
        await update.message.reply_text(
            "🚫 You must join the channel to use this bot.",
            reply_markup=btn
        )
        return

    users = load(USERS, {})
    uid = str(update.effective_user.id)
    users.setdefault(uid, {"balance": 0, "proofs": 0})
    save(USERS, users)

    await update.message.reply_text(
        "👋 Welcome to Task Bot",
        reply_markup=menu()
    )

# ================= BALANCE =================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = load(USERS, {})
    bal = u[str(update.effective_user.id)]["balance"]
    await update.message.reply_text(f"💰 Your Balance: ₹{bal}")

# ================= SUPPORT =================
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 Need help?\nContact owner: @DTXZAHID"
    )

# ================= SUBMIT PROOF =================
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Send screenshot proof")
    return PROOF_SCREEN

async def proof_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Screenshot only")
        return PROOF_SCREEN
    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Now send refer link")
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    uid = str(update.effective_user.id)

    verified = load(VERIFIED, {})
    users = load(USERS, {})

    status = "REJECTED"
    added = 0

    for vid, amt in verified.items():
        if vid in link:
            status = "VERIFIED"
            if amt > 0:
                users[uid]["balance"] += amt
                added = amt
            users[uid]["proofs"] += 1
            del verified[vid]
            break

    save(USERS, users)
    save(VERIFIED, verified)

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

    if status == "VERIFIED" and added == 0:
        msg = "✅ Proof verified\n💰 Payment will be added in 5–10 minutes"
    elif status == "VERIFIED":
        msg = f"✅ Proof verified\n₹{added} added to balance"
    else:
        msg = "❌ Proof rejected (Fake / Same device / Refer mismatch)"

    await update.message.reply_text(msg, reply_markup=menu())
    return ConversationHandler.END

# ================= WITHDRAW =================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("UPI", callback_data="upi"),
         InlineKeyboardButton("VSV", callback_data="vsv"),
         InlineKeyboardButton("FXL", callback_data="fxl")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
    await update.message.reply_text("💸 Choose withdraw method", reply_markup=kb)
    return WD_METHOD

async def wd_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    if q.data == "cancel":
        await q.message.reply_text("❌ Cancelled", reply_markup=menu())
        return ConversationHandler.END

    context.user_data["method"] = q.data.upper()
    await q.message.reply_text(
        "Send UPI ID" if q.data == "upi" else "Send registered number"
    )
    return WD_DETAIL

async def wd_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text
    min_amt = 5 if context.user_data["method"] == "UPI" else 2
    await update.message.reply_text(
        f"Enter amount (Min ₹{min_amt})"
    )
    return WD_AMOUNT

async def wd_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("❌ Numbers only")
        return WD_AMOUNT

    amt = int(update.message.text)
    method = context.user_data["method"]
    min_amt = 5 if method == "UPI" else 2

    users = load(USERS, {})
    uid = str(update.effective_user.id)

    if amt < min_amt or users[uid]["balance"] < amt:
        await update.message.reply_text("❌ Invalid amount")
        return ConversationHandler.END

    users[uid]["balance"] -= amt
    save(USERS, users)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Withdraw Done", callback_data=f"done:{uid}:{amt}"),
         InlineKeyboardButton("❌ Withdraw Rejected", callback_data=f"rej:{uid}")]
    ])

    await context.bot.send_message(
        ADMIN_ID,
        f"💸 Withdraw Request\nUser: {uid}\nAmount: ₹{amt}\nMethod: {method}\nDetail: {context.user_data['detail']}",
        reply_markup=kb
    )

    await update.message.reply_text("✅ Withdraw request sent", reply_markup=menu())
    return ConversationHandler.END

async def wd_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    act, uid, *_ = q.data.split(":")
    msg = (
        "✅ Withdraw processed successfully"
        if act == "done"
        else "❌ Withdraw rejected due to issues"
    )
    await context.bot.send_message(int(uid), msg)
    await q.message.edit_text("✔ Action completed")

# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    kb = ReplyKeyboardMarkup(
        [["➕ Add Balance", "➖ Remove Balance"],
         ["📋 Verified IDs", "👥 Total Users"],
         ["🔍 Check Detail"]],
        resize_keyboard=True
    )
    await update.message.reply_text("⚙ Admin Panel", reply_markup=kb)

async def add_ver(update, context):
    await update.message.reply_text("Send: USER_ID or USER_ID AMOUNT")
    return ADD_VER

async def add_ver_do(update, context):
    p = update.message.text.split()
    v = load(VERIFIED, {})
    v[p[0]] = float(p[1]) if len(p) == 2 else 0
    save(VERIFIED, v)
    await update.message.reply_text("✅ Verified ID saved")
    return ConversationHandler.END

async def total_users(update, context):
    await update.message.reply_text(
        f"👥 Total Users: {len(load(USERS, {}))}"
    )

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(MessageHandler(filters.Regex("^👥 Total Users$"), total_users))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={
            PROOF_SCREEN: [MessageHandler(filters.PHOTO, proof_screen)],
            PROOF_LINK: [MessageHandler(filters.TEXT, proof_link)]
        },
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw)],
        states={
            WD_METHOD: [CallbackQueryHandler(wd_method)],
            WD_DETAIL: [MessageHandler(filters.TEXT, wd_detail)],
            WD_AMOUNT: [MessageHandler(filters.TEXT, wd_amount)]
        },
        fallbacks=[]
    ))

    app.add_handler(CallbackQueryHandler(wd_action, pattern="^(done|rej):"))

    app.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Verified IDs$"), add_ver)],
        states={ADD_VER: [MessageHandler(filters.TEXT, add_ver_do)]},
        fallbacks=[]
    ))

    app.run_polling()

if __name__ == "__main__":
    main()
