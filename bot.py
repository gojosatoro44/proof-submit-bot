import os
import json
import re
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
FORCE_CHANNEL = "@TaskByZahid"

DATA_FILE = "data.json"

# ================= DATA =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "users": {},
            "verified_ids": {}  # { "7101602737": 2.5 }
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# ================= STATES =================
PROOF_SS, PROOF_LINK = range(2)
ADMIN_ADD_BAL, ADMIN_REM_BAL, ADMIN_ADD_IDS = range(3)

# ================= FORCE JOIN =================
async def is_joined(bot, user_id):
    try:
        member = await bot.get_chat_member(FORCE_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def force_join(update, context):
    joined = await is_joined(context.bot, update.effective_user.id)
    if joined:
        return True

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Join Channel", url="https://t.me/TaskByZahid")],
        [InlineKeyboardButton("🔄 Check Join", callback_data="check_join")]
    ])
    await update.message.reply_text(
        "🚫 You must join our channel to use this bot.",
        reply_markup=keyboard
    )
    return False

async def check_join_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await is_joined(context.bot, q.from_user.id):
        await q.message.reply_text("✅ Joined successfully. Send /start")
    else:
        await q.message.reply_text("❌ Still not joined.")

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join(update, context):
        return

    uid = str(update.effective_user.id)
    if uid not in data["users"]:
        data["users"][uid] = {"balance": 0}
        save_data()

    keyboard = [
        ["📤 Submit Proof"],
        ["💰 Balance", "💸 Withdraw"],
        ["🆘 Support"]
    ]
    await update.message.reply_text(
        "👋 Welcome to Task Bot",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# ================= BALANCE =================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    bal = data["users"][uid]["balance"]
    await update.message.reply_text(f"💰 Your Balance: ₹{bal}")

# ================= SUPPORT =================
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "If you are facing any issue in proof or withdraw,\n"
        "Contact Owner: @DTXZAHID"
    )

# ================= SUBMIT PROOF =================
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join(update, context):
        return ConversationHandler.END

    await update.message.reply_text("📸 Send Screenshot Of Bot")
    return PROOF_SS

async def proof_ss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ss"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔗 Send Your Refer Link To Verify")
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    text = update.message.text

    match = re.search(r"start=(\d+)", text)
    extracted_id = match.group(1) if match else None

    status = "❌ UNVERIFIED"
    added_amt = 0

    if extracted_id and extracted_id in data["verified_ids"]:
        added_amt = data["verified_ids"][extracted_id]
        data["users"][uid]["balance"] += added_amt
        del data["verified_ids"][extracted_id]
        save_data()
        status = "✅ VERIFIED"

        await update.message.reply_text(
            f"✅ Proof verified successfully\n₹{added_amt} added to your balance"
        )
    else:
        await update.message.reply_text(
            "❌ Proof rejected due to\n"
            "Same device / Fake proof / Refer"
        )

    # Send proof to admin (record)
    await context.bot.send_photo(
        ADMIN_ID,
        context.user_data["ss"],
        caption=(
            f"📥 Proof Record\n\n"
            f"User ID: {uid}\n"
            f"Refer ID: {extracted_id}\n"
            f"Status: {status}\n"
            f"Amount Added: ₹{added_amt}"
        )
    )

    return ConversationHandler.END

# ================= ADMIN PANEL =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Balance", callback_data="add_bal")],
        [InlineKeyboardButton("➖ Remove Balance", callback_data="rem_bal")],
        [InlineKeyboardButton("👥 Total Users", callback_data="total_users")],
        [InlineKeyboardButton("📋 Verified IDs", callback_data="ver_ids")]
    ])
    await update.message.reply_text("🔐 Admin Panel", reply_markup=keyboard)

async def admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "add_bal":
        await q.message.reply_text("Send:\nUSER_ID AMOUNT")
        context.user_data["admin"] = "add"
    elif q.data == "rem_bal":
        await q.message.reply_text("Send:\nUSER_ID AMOUNT")
        context.user_data["admin"] = "rem"
    elif q.data == "total_users":
        await q.message.reply_text(f"👥 Total Users: {len(data['users'])}")
    elif q.data == "ver_ids":
        await q.message.reply_text(
            "Send Verified IDs like:\n"
            "7101602737 2.5\n8899001122 3"
        )
        context.user_data["admin"] = "ids"

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    mode = context.user_data.get("admin")
    if not mode:
        return

    lines = update.message.text.strip().splitlines()

    if mode in ["add", "rem"]:
        uid, amt = lines[0].split()
        amt = float(amt)
        if uid not in data["users"]:
            data["users"][uid] = {"balance": 0}

        if mode == "add":
            data["users"][uid]["balance"] += amt
        else:
            data["users"][uid]["balance"] -= amt

        save_data()
        await update.message.reply_text("✅ Balance updated")

    elif mode == "ids":
        for line in lines:
            uid, amt = line.split()
            data["verified_ids"][uid] = float(amt)
        save_data()
        await update.message.reply_text("✅ Verified IDs saved")

    context.user_data["admin"] = None

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(check_join_cb, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(admin_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))

    proof_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={
            PROOF_SS: [MessageHandler(filters.PHOTO, proof_ss)],
            PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_link)],
        },
        fallbacks=[]
    )
    app.add_handler(proof_conv)

    app.run_polling()

if __name__ == "__main__":
    main()
