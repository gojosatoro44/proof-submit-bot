import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# ================= CONFIG =================
BOT_TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810

CHANNEL_USERNAME = "@TaskByZahid"
CHANNEL_LINK = "https://t.me/TaskByZahid"

# ================= STORAGE =================
users = {}
states = {}
temp = {}
payment_methods = {}

# ================= LOG =================
logging.basicConfig(level=logging.INFO)

# ================= HELPERS =================
def ensure_user(uid):
    if uid not in users:
        users[uid] = {"balance": 0}

def clear(uid):
    states.pop(uid, None)
    temp.pop(uid, None)

async def joined(bot, uid):
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= KEYBOARDS =================
MAIN_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📤 Submit Proof", callback_data="proof"),
        InlineKeyboardButton("💰 Balance", callback_data="balance")
    ],
    [
        InlineKeyboardButton("🔥 Withdraw", callback_data="withdraw"),
        InlineKeyboardButton("🤯 Payment Method", callback_data="pm")
    ]
])

JOIN_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Join Channel", url=CHANNEL_LINK)],
    [InlineKeyboardButton("🔄 I Joined", callback_data="check_join")]
])

ADMIN_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("➕ Add Balance", callback_data="admin_add"),
        InlineKeyboardButton("➖ Remove Balance", callback_data="admin_remove")
    ],
    [
        InlineKeyboardButton("👥 Total Users", callback_data="admin_users")
    ]
])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not await joined(context.bot, uid):
        await update.message.reply_text(
            "🔒 **JOIN REQUIRED**\n\nJoin channel to use the bot 👇",
            reply_markup=JOIN_KB,
            parse_mode="Markdown"
        )
        return

    ensure_user(uid)
    clear(uid)

    await update.message.reply_text(
        "🔥 **WELCOME** 🔥\nChoose an option 👇",
        reply_markup=MAIN_KB,
        parse_mode="Markdown"
    )

# ================= FORCE JOIN =================
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if await joined(context.bot, q.from_user.id):
        await q.message.delete()
        await context.bot.send_message(
            q.from_user.id,
            "✅ **Access Granted**",
            reply_markup=MAIN_KB,
            parse_mode="Markdown"
        )
    else:
        await q.answer("Join channel first!", show_alert=True)

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "🛠 **ADMIN PANEL**",
        reply_markup=ADMIN_KB,
        parse_mode="Markdown"
    )

# ================= CALLBACKS =================
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    ensure_user(uid)

    if data == "balance":
        await context.bot.send_message(
            uid,
            f"💰 **Balance: ₹{users[uid]['balance']}**",
            parse_mode="Markdown"
        )

    elif data == "proof":
        states[uid] = "WAIT_PROOF"
        await context.bot.send_message(
            uid,
            "📸 **Send screenshot (refer link visible)**",
            parse_mode="Markdown"
        )

    elif data == "pm":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("💳 UPI", callback_data="pm_upi"),
                InlineKeyboardButton("📱 VSV", callback_data="pm_vsv"),
                InlineKeyboardButton("📱 FXL", callback_data="pm_fxl")
            ]
        ])
        await context.bot.send_message(uid, "Choose method 👇", reply_markup=kb)

    elif data.startswith("pm_"):
        states[uid] = "WAIT_PM_DETAIL"
        temp[uid] = {"method": data.split("_")[1]}
        await context.bot.send_message(
            uid,
            "✍️ **Send payment details now**",
            parse_mode="Markdown"
        )

    elif data == "withdraw":
        if uid not in payment_methods:
            await context.bot.send_message(
                uid,
                "❌ **Add payment method first**",
                parse_mode="Markdown"
            )
            return

        states[uid] = "WAIT_WITHDRAW"
        await context.bot.send_message(uid, "💸 Enter withdraw amount")

    # ===== ADMIN BUTTONS =====
    elif data == "admin_users" and uid == ADMIN_ID:
        await context.bot.send_message(
            uid,
            f"👥 **Total Users: {len(users)}**",
            parse_mode="Markdown"
        )

# ================= PHOTO HANDLER =================
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if states.get(uid) != "WAIT_PROOF":
        return

    states[uid] = "WAIT_REFER"
    temp[uid] = {"photo": update.message.photo[-1].file_id}

    await update.message.reply_text(
        "🔗 **Now send your refer link**",
        parse_mode="Markdown"
    )

# ================= TEXT HANDLER (CRITICAL FIX) =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    # PAYMENT METHOD SAVE
    if states.get(uid) == "WAIT_PM_DETAIL":
        payment_methods[uid] = {
            "type": temp[uid]["method"],
            "detail": text
        }
        clear(uid)
        await update.message.reply_text("✅ Payment method saved")
        return

    # REFER LINK AFTER PROOF
    if states.get(uid) == "WAIT_REFER":
        await context.bot.send_photo(
            ADMIN_ID,
            temp[uid]["photo"],
            caption=f"🆕 **PROOF**\n\n👤 `{uid}`\n🔗 {text}",
            parse_mode="Markdown"
        )
        clear(uid)
        await update.message.reply_text("✅ Proof submitted")
        return

    # WITHDRAW
    if states.get(uid) == "WAIT_WITHDRAW":
        if not text.isdigit():
            await update.message.reply_text("❌ Enter valid amount")
            return

        amount = int(text)
        if amount > users[uid]["balance"]:
            await update.message.reply_text("❌ Insufficient balance")
            return

        pm = payment_methods[uid]
        clear(uid)

        await context.bot.send_message(
            ADMIN_ID,
            f"💸 **WITHDRAW REQUEST**\n\n"
            f"👤 `{uid}`\n"
            f"₹ {amount}\n"
            f"{pm['type'].upper()}: {pm['detail']}",
            parse_mode="Markdown"
        )

        await update.message.reply_text("✅ Withdraw request sent")

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dtx", admin_panel))

app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
app.add_handler(CallbackQueryHandler(callbacks))

app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("🤖 Bot running (stable)...")
app.run_polling()
