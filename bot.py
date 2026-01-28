import os, json, threading, re
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
VERIFIED = f"{DATA}/verified.json"  # {"id": [amount, amount]}
os.makedirs(DATA, exist_ok=True)

file_lock = threading.Lock()

# ================= STATES =================
(
    PROOF_LINK,
    WD_METHOD, WD_DETAIL, WD_AMOUNT,
    ADD_BAL_USER, ADD_BAL_AMOUNT,
    REM_BAL_USER, REM_BAL_AMOUNT,
    ADD_VER_IDS, VER_AMOUNT
) = range(10)

# ================= SAFE FILE OPS =================
def load(path, default):
    with file_lock:
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump(default, f)
        with open(path) as f:
            return json.load(f)

def save(path, data):
    tmp = path + ".tmp"
    with file_lock:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)  # atomic save (NO DATA LOSS)

# ================= UI =================
def menu():
    return ReplyKeyboardMarkup(
        [["📤 Submit Proof"],
         ["💰 Balance", "💸 Withdraw"],
         ["🆘 Support"]],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        [["➕ Add Balance", "➖ Remove Balance"],
         ["📋 Add Verified IDs"],
         ["👥 Total Users", "📊 User Details"],
         ["🏠 Main Menu"]],
        resize_keyboard=True
    )

# ================= HELPERS =================
async def force_join(update, context):
    try:
        m = await context.bot.get_chat_member(
            FORCE_JOIN_CHANNEL, update.effective_user.id
        )
        return m.status in ("member", "administrator", "creator")
    except:
        return False

def is_admin(uid):
    return uid == ADMIN_ID

def is_valid_url(text):
    return bool(re.search(r"(https?://|t\.me/|\?start=|\=)", text))

# ================= START =================
async def start(update, context):
    if not await force_join(update, context):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL[1:]}")],
            [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")]
        ])
        await update.message.reply_text("🚫 Join channel first", reply_markup=kb)
        return

    users = load(USERS, {})
    uid = str(update.effective_user.id)

    if uid not in users:
        users[uid] = {
            "balance": 0,
            "proofs": 0,
            "name": update.effective_user.full_name,
            "username": update.effective_user.username
        }
        save(USERS, users)

    await update.message.reply_text("✅ Bot Ready", reply_markup=menu())

async def check_join_callback(update, context):
    q = update.callback_query
    await q.answer()
    if await force_join(update, context):
        await q.edit_message_text("✅ Joined! Use /start")
    else:
        await q.edit_message_text("❌ Still not joined")

# ================= BALANCE =================
async def balance(update, context):
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    if uid in users:
        await update.message.reply_text(
            f"💰 Balance: ₹{users[uid]['balance']}\n"
            f"📊 Proofs: {users[uid]['proofs']}"
        )

# ================= SUPPORT =================
async def support(update, context):
    await update.message.reply_text("🆘 Support: @DTXZAHID")

# ================= SUBMIT PROOF =================
async def submit_proof(update, context):
    if not await force_join(update, context):
        return ConversationHandler.END

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_proof")]
    ])
    await update.message.reply_text("Send your Refer Link:", reply_markup=kb)
    return PROOF_LINK

async def proof_link(update, context):
    link = update.message.text.strip()
    if not is_valid_url(link):
        await update.message.reply_text("❌ Invalid link")
        return PROOF_LINK

    users = load(USERS, {})
    verified = load(VERIFIED, {})
    uid = str(update.effective_user.id)

    status = "REJECTED"
    added = 0

    for vid, rewards in verified.items():
        if vid in link and rewards:
            added = rewards.pop(0)
            users[uid]["balance"] += added
            users[uid]["proofs"] += 1
            if not rewards:
                del verified[vid]
            status = "VERIFIED"
            break

    save(USERS, users)
    save(VERIFIED, verified)

    await update.message.reply_text(
        f"✅ Verified +₹{added}" if status == "VERIFIED"
        else "❌ Proof rejected",
        reply_markup=menu()
    )
    return ConversationHandler.END

async def cancel_proof_callback(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("❌ Cancelled", reply_markup=menu())
    return ConversationHandler.END

# ================= ADD VERIFIED IDs (FIXED FORMAT SUPPORT) =================
async def add_verified_ids(update, context):
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        "📋 Send text containing User IDs.\n\n"
        "Example:\n"
        "🎉 ₹3 Credited to Your Balance! Invited : 5440721877"
    )
    return ADD_VER_IDS

async def add_ver_ids(update, context):
    text = update.message.text

    # ONLY extract IDs, ignore everything else
    ids = re.findall(r"\d{8,}", text)

    if not ids:
        await update.message.reply_text(
            "❌ No valid User IDs found.\nTry again."
        )
        return ADD_VER_IDS

    context.user_data["ver_ids"] = ids

    preview = "\n".join(ids[:10])
    if len(ids) > 10:
        preview += f"\n... and {len(ids)-10} more"

    await update.message.reply_text(
        f"✅ Extracted {len(ids)} User ID(s):\n\n"
        f"{preview}\n\n"
        f"Now send the amount for EACH ID:"
    )
    return VER_AMOUNT

async def ver_amount(update, context):
    try:
        amount = float(update.message.text)
    except:
        await update.message.reply_text("❌ Enter valid amount")
        return VER_AMOUNT

    verified = load(VERIFIED, {})
    for uid in context.user_data["ver_ids"]:
        verified.setdefault(uid, []).append(amount)

    save(VERIFIED, verified)

    await update.message.reply_text(
        "✅ Verified IDs added successfully",
        reply_markup=admin_menu()
    )
    context.user_data.clear()
    return ConversationHandler.END

# ================= ADMIN =================
async def admin(update, context):
    if is_admin(update.effective_user.id):
        await update.message.reply_text("⚙ Admin Panel", reply_markup=admin_menu())

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(check_join_callback, "^check_join$"))
    app.add_handler(CallbackQueryHandler(cancel_proof_callback, "^cancel_proof$"))

    app.add_handler(MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof))
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))

    proof_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={PROOF_LINK: [MessageHandler(filters.TEXT, proof_link)]},
        fallbacks=[]
    )

    ver_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Add Verified IDs$"), add_verified_ids)],
        states={
            ADD_VER_IDS: [MessageHandler(filters.TEXT, add_ver_ids)],
            VER_AMOUNT: [MessageHandler(filters.TEXT, ver_amount)]
        },
        fallbacks=[]
    )

    app.add_handler(proof_conv)
    app.add_handler(ver_conv)

    print("🤖 Bot Running (DATA SAFE)")
    app.run_polling()

if __name__ == "__main__":
    main()
