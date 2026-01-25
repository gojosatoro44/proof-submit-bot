import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ================= CONFIG =================
BOT_TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810

CHANNEL_USERNAME = "@TaskByZahid"
CHANNEL_LINK = "https://t.me/TaskByZahid"

# ================= STORAGE =================
users = {}              # {uid: {"balance": int}}
states = {}             # {uid: state}
payment_methods = {}    # {uid: {"type": str, "detail": str}}
temp_data = {}          # {uid: {...}}

# ================= LOG =================
logging.basicConfig(level=logging.INFO)

# ================= HELPERS =================
def get_user(uid):
    if uid not in users:
        users[uid] = {"balance": 0}
    return users[uid]

def clear_state(uid):
    states.pop(uid, None)
    temp_data.pop(uid, None)

async def is_joined(bot, uid):
    try:
        m = await bot.get_chat_member(CHANNEL_USERNAME, uid)
        return m.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= KEYBOARDS =================
main_kb = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📤 Submit Proof", callback_data="submit_proof"),
        InlineKeyboardButton("💰 Balance", callback_data="balance")
    ],
    [
        InlineKeyboardButton("🔥 Withdraw", callback_data="withdraw"),
        InlineKeyboardButton("🤯 Payment Method", callback_data="pay_method")
    ]
])

join_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Join Channel", url=CHANNEL_LINK)],
    [InlineKeyboardButton("🔄 I Joined", callback_data="check_join")]
])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not await is_joined(context.bot, uid):
        await update.message.reply_text(
            "🔒 **JOIN REQUIRED**\n\nJoin channel to use bot 👇",
            reply_markup=join_kb,
            parse_mode="Markdown"
        )
        return

    get_user(uid)
    clear_state(uid)

    await update.message.reply_text(
        "🔥 **WELCOME** 🔥\nChoose an option 👇",
        reply_markup=main_kb,
        parse_mode="Markdown"
    )

# ================= FORCE JOIN =================
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if await is_joined(context.bot, q.from_user.id):
        await q.message.delete()
        await context.bot.send_message(
            q.from_user.id,
            "✅ **Access Granted**",
            reply_markup=main_kb,
            parse_mode="Markdown"
        )
    else:
        await q.answer("Join channel first!", show_alert=True)

# ================= BALANCE =================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    bal = get_user(q.from_user.id)["balance"]

    await context.bot.send_message(
        q.from_user.id,
        f"💰 **Balance: ₹{bal}**",
        parse_mode="Markdown"
    )

# ================= PAYMENT METHOD =================
async def pay_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💳 UPI", callback_data="pm_upi"),
            InlineKeyboardButton("📱 VSV", callback_data="pm_vsv"),
            InlineKeyboardButton("📱 FXL", callback_data="pm_fxl")
        ]
    ])

    await context.bot.send_message(
        q.from_user.id,
        "🤯 **Choose payment method**",
        reply_markup=kb,
        parse_mode="Markdown"
    )

async def pm_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    method = q.data.split("_")[1]

    states[uid] = "await_pm_detail"
    temp_data[uid] = {"method": method}

    await context.bot.send_message(
        uid,
        f"✍️ **Send your {method.upper()} details now**",
        parse_mode="Markdown"
    )

# ================= WITHDRAW =================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    if uid not in payment_methods:
        await context.bot.send_message(
            uid,
            "❌ **Add payment method first**",
            parse_mode="Markdown"
        )
        return

    states[uid] = "await_withdraw_amount"

    await context.bot.send_message(
        uid,
        "💸 **Enter withdraw amount**",
        parse_mode="Markdown"
    )

# ================= SUBMIT PROOF =================
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    states[q.from_user.id] = "await_screenshot"

    await context.bot.send_message(
        q.from_user.id,
        "📸 **Send screenshot (refer link visible)**",
        parse_mode="Markdown"
    )

# ================= PHOTO =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if states.get(uid) == "await_screenshot":
        states[uid] = "await_refer_link"
        temp_data[uid] = {"photo": update.message.photo[-1].file_id}

        await update.message.reply_text(
            "🔗 **Now send your refer link**",
            parse_mode="Markdown"
        )

# ================= TEXT HANDLER (ALL LOGIC HERE) =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    # PAYMENT METHOD SAVE
    if states.get(uid) == "await_pm_detail":
        method = temp_data[uid]["method"]
        payment_methods[uid] = {"type": method, "detail": text}
        clear_state(uid)

        await update.message.reply_text(
            "✅ **Payment method saved successfully**",
            parse_mode="Markdown"
        )
        return

    # REFER LINK AFTER SCREENSHOT
    if states.get(uid) == "await_refer_link":
        photo_id = temp_data[uid]["photo"]

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"acc_{uid}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}")
            ]
        ])

        await context.bot.send_photo(
            ADMIN_ID,
            photo_id,
            caption=f"🆕 **PROOF RECEIVED**\n\n👤 `{uid}`\n🔗 {text}",
            parse_mode="Markdown",
            reply_markup=kb
        )

        clear_state(uid)

        await update.message.reply_text(
            "✅ **Proof submitted successfully**",
            parse_mode="Markdown"
        )
        return

    # WITHDRAW AMOUNT
    if states.get(uid) == "await_withdraw_amount":
        if not text.isdigit():
            await update.message.reply_text("❌ Enter valid amount")
            return

        amount = int(text)
        bal = get_user(uid)["balance"]

        if amount > bal:
            await update.message.reply_text("❌ Insufficient balance")
            return

        pm = payment_methods[uid]

        await context.bot.send_message(
            ADMIN_ID,
            f"💸 **WITHDRAW REQUEST**\n\n"
            f"👤 `{uid}`\n"
            f"₹ Amount: {amount}\n"
            f"💳 {pm['type'].upper()}\n"
            f"📄 {pm['detail']}",
            parse_mode="Markdown"
        )

        clear_state(uid)

        await update.message.reply_text(
            "✅ **Withdraw request sent to admin**",
            parse_mode="Markdown"
        )

# ================= ADMIN =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = int(q.data.split("_")[1])

    if q.data.startswith("acc"):
        await context.bot.send_message(uid, "✅ **Proof accepted**")
    else:
        await context.bot.send_message(uid, "❌ **Proof rejected**")

    await q.message.delete()

# ================= APP =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
app.add_handler(CallbackQueryHandler(balance, pattern="balance"))
app.add_handler(CallbackQueryHandler(pay_method, pattern="pay_method"))
app.add_handler(CallbackQueryHandler(pm_select, pattern="pm_"))
app.add_handler(CallbackQueryHandler(withdraw, pattern="withdraw"))
app.add_handler(CallbackQueryHandler(submit_proof, pattern="submit_proof"))
app.add_handler(CallbackQueryHandler(admin_action, pattern="acc_|rej_"))

app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🤖 Bot running...")
app.run_polling()
