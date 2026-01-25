import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

# ================= CONFIG =================
BOT_TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810

CHANNEL_USERNAME = "@TaskByZahid"
CHANNEL_LINK = "https://t.me/TaskByZahid"
PAYMENT_BOT = "https://t.me/Bot_Tasks_Payment_Bot"

# ================= STORAGE (IN-MEMORY) =================
users = {}
states = {}
payment_methods = {}

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)

# ================= UTIL =================
def get_user(uid):
    if uid not in users:
        users[uid] = {"balance": 0}
    return users[uid]

def clear_state(uid):
    states.pop(uid, None)

async def is_joined(bot, uid):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, uid)
        return member.status in ["member", "administrator", "creator"]
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
    [InlineKeyboardButton("✅ JOIN CHANNEL", url=CHANNEL_LINK)],
    [InlineKeyboardButton("🔄 I Joined", callback_data="check_join")]
])

admin_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("👥 Total Users", callback_data="total_users")],
    [
        InlineKeyboardButton("➕ Add Balance", callback_data="add_bal"),
        InlineKeyboardButton("➖ Remove Balance", callback_data="rem_bal")
    ]
])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not await is_joined(context.bot, uid):
        await update.message.reply_text(
            "🔒 **ACCESS LOCKED** 🔒\n\n"
            "🚀 *Join our official channel to continue*\n\n"
            "👇 Click below & then press **I Joined**",
            reply_markup=join_kb,
            parse_mode="Markdown"
        )
        return

    get_user(uid)
    clear_state(uid)

    await update.message.reply_text(
        "🔥 **WELCOME BACK LEGEND** 🔥\n\n"
        "Choose an option below 👇",
        reply_markup=main_kb,
        parse_mode="Markdown"
    )

# ================= FORCE JOIN CHECK =================
async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if await is_joined(context.bot, uid):
        get_user(uid)
        clear_state(uid)
        await q.message.delete()
        await context.bot.send_message(
            uid,
            "✅ **ACCESS GRANTED**\n\nEnjoy the bot 👇",
            reply_markup=main_kb,
            parse_mode="Markdown"
        )
    else:
        await q.answer("❌ Join channel first!", show_alert=True)

# ================= BALANCE =================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    bal = get_user(uid)["balance"]

    await context.bot.send_message(
        uid,
        f"💰 **Balance: ₹{bal}**\n\n"
        "Use **Withdraw** button to withdraw 🤑",
        parse_mode="Markdown"
    )

# ================= SUBMIT PROOF =================
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    states[q.from_user.id] = "await_ss"

    await context.bot.send_message(
        q.from_user.id,
        "📸 **Send Screenshot**\n\n"
        "⚠️ Refer link must be visible",
        parse_mode="Markdown"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if states.get(uid) == "await_ss":
        states[uid] = "await_link"
        context.user_data["ss"] = update.message.photo[-1].file_id

        await update.message.reply_text(
            "🔗 **Now send your REFER LINK**",
            parse_mode="Markdown"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if states.get(uid) == "await_link":
        ss = context.user_data.get("ss")
        link = update.message.text

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"acc_{uid}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{uid}")
            ]
        ])

        await context.bot.send_photo(
            ADMIN_ID,
            ss,
            caption=(
                f"🆕 **NEW PROOF RECEIVED**\n\n"
                f"👤 `User ID:` `{uid}`\n\n"
                f"🔗 **Refer Link:**\n{link}"
            ),
            parse_mode="Markdown",
            reply_markup=kb
        )

        clear_state(uid)
        await update.message.reply_text(
            "✅ **Proof submitted successfully**",
            parse_mode="Markdown"
        )

# ================= ADMIN ACTION =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    data = q.data
    uid = int(data.split("_")[1])

    if data.startswith("acc"):
        await context.bot.send_message(
            uid,
            "✅ **Bro apka refer count ho gaya**\n\n"
            "💸 Payment 5–10 min me bot me aayega",
            parse_mode="Markdown"
        )
    else:
        await context.bot.send_message(
            uid,
            "❌ **Bro apka refer nahi aaya**\n\n"
            "Isliye payment nahi milega",
            parse_mode="Markdown"
        )

    await q.message.delete()

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
        "🤯 **Choose Payment Method**",
        reply_markup=kb,
        parse_mode="Markdown"
    )

async def pm_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    method = q.data.split("_")[1]
    states[uid] = f"pm_{method}"

    await context.bot.send_message(
        uid,
        f"✍️ **Send your {method.upper()} details**",
        parse_mode="Markdown"
    )

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "🛠 **ADMIN PANEL**",
        reply_markup=admin_kb,
        parse_mode="Markdown"
    )

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await context.bot.send_message(
        ADMIN_ID,
        f"👥 **Total Users:** {len(users)}",
        parse_mode="Markdown"
    )

# ================= APP =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("dtx", admin_panel))

app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
app.add_handler(CallbackQueryHandler(submit_proof, pattern="submit_proof"))
app.add_handler(CallbackQueryHandler(balance, pattern="balance"))
app.add_handler(CallbackQueryHandler(pay_method, pattern="pay_method"))
app.add_handler(CallbackQueryHandler(pm_select, pattern="pm_"))
app.add_handler(CallbackQueryHandler(admin_action, pattern="acc_|rej_"))
app.add_handler(CallbackQueryHandler(admin_stats, pattern="total_users"))

app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🤖 Bot is running...")
app.run_polling()
