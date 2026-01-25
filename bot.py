from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# ===== CONFIG =====
TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810
CHANNEL_LINK = "http://t.me/TaskByZahid"

# ===== STATES =====
PROOF_SCREENSHOT, PROOF_LINK, PAYMENT_METHOD_FLOW, WITHDRAW_AMOUNT, WITHDRAW_METHOD, WITHDRAW_CONFIRM = range(6)

# ===== STORAGE =====
user_data_store = {}  # {user_id: {"balance": 0, "payment": None}}

# ===== BUTTONS =====
def main_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📸 Submit Proof", callback_data="submit_proof"),
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
            InlineKeyboardButton("💳 Payment Method", callback_data="payment_method")
        ]
    ])

def cancel_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])

def join_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("👉 Join Channel", url=CHANNEL_LINK)]])

# ===== FORCE JOIN CHECK =====
async def check_force_join(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_LINK.split("/")[-1], user_id)
        if member.status in ["left", "kicked"]:
            return False
        return True
    except:
        return False

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await check_force_join(user_id, context):
        await update.message.reply_text(
            "🚨 **Please Join Our Channel To Access The Bot!** 🚨",
            reply_markup=join_button(),
            parse_mode="MarkdownV2"
        )
        return

    if user_id not in user_data_store:
        user_data_store[user_id] = {"balance": 0, "payment": None}

    await update.message.reply_text(
        "🎉 **Welcome! You Can Use The Bot Now.** 🎉",
        reply_markup=main_buttons(),
        parse_mode="MarkdownV2"
    )

# ===== BUTTON HANDLER =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if not await check_force_join(user_id, context):
        await query.message.reply_text(
            "🚨 **You Must Join Our Channel First!** 🚨",
            reply_markup=join_button(),
            parse_mode="MarkdownV2"
        )
        return

    if data == "submit_proof":
        await query.message.reply_text(
            "**Send Screenshot Of Proof With Refer Link Visible**",
            reply_markup=cancel_button(),
            parse_mode="MarkdownV2"
        )
        return PROOF_SCREENSHOT

    elif data == "balance":
        bal = user_data_store.get(user_id, {}).get("balance", 0)
        await query.message.reply_text(
            f"💰 **Balance: ₹{bal}**\nUse 'Withdraw' button to withdraw your balance 🤑",
            parse_mode="MarkdownV2"
        )

    elif data == "withdraw":
        if not user_data_store[user_id].get("payment"):
            await query.message.reply_text(
                "**You Must Add A Payment Method First 💳**",
                parse_mode="MarkdownV2"
            )
            return
        await query.message.reply_text("**Enter Amount You Want To Withdraw:**", parse_mode="MarkdownV2")
        return WITHDRAW_AMOUNT

    elif data == "payment_method":
        keyboard = [
            [
                InlineKeyboardButton("Vsv", callback_data="pay_vsv"),
                InlineKeyboardButton("Fxl", callback_data="pay_fxl"),
                InlineKeyboardButton("Upi", callback_data="pay_upi")
            ]
        ]
        await query.message.reply_text("**Choose Payment Method:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
        return PAYMENT_METHOD_FLOW

    elif data == "cancel":
        await query.message.reply_text("**Operation Cancelled ✅**", reply_markup=main_buttons(), parse_mode="MarkdownV2")
        return ConversationHandler.END

# ===== PAYMENT METHOD =====
async def payment_method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    method = query.data.split("_")[1]
    user_data_store[user_id]["payment"] = method
    await query.message.reply_text(f"**Payment Method Saved ✅ ({method})**", reply_markup=main_buttons(), parse_mode="MarkdownV2")
    return ConversationHandler.END

# ===== WITHDRAW FLOW =====
async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        amount = int(update.message.text)
        balance = user_data_store[user_id]["balance"]
        if amount > balance:
            await update.message.reply_text("**Insufficient Balance ❌**", parse_mode="MarkdownV2")
            return WITHDRAW_AMOUNT
        context.user_data["withdraw_amount"] = amount
        keyboard = [
            [
                InlineKeyboardButton("Vsv", callback_data="w_vsv"),
                InlineKeyboardButton("Fxl", callback_data="w_fxl"),
                InlineKeyboardButton("Upi", callback_data="w_upi")
            ]
        ]
        await update.message.reply_text("**Choose Withdraw Method:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="MarkdownV2")
        return WITHDRAW_METHOD
    except:
        await update.message.reply_text("**Enter A Valid Number ❌**", parse_mode="MarkdownV2")
        return WITHDRAW_AMOUNT

async def withdraw_method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    method = query.data.split("_")[1]
    context.user_data["withdraw_method"] = method
    amount = context.user_data["withdraw_amount"]
    await query.message.reply_text(
        f"**You Are Withdrawing ₹{amount} Via {method}**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Submit Withdraw ✅", callback_data="withdraw_submit"),
             InlineKeyboardButton("Cancel ❌", callback_data="cancel")]
        ]),
        parse_mode="MarkdownV2"
    )
    return WITHDRAW_CONFIRM

async def withdraw_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    amount = context.user_data.get("withdraw_amount")
    method = context.user_data.get("withdraw_method")
    user_data_store[user_id]["balance"] -= amount
    await context.bot.send_message(
        ADMIN_ID,
        f"💰 Withdraw Request\n`User ID: {user_id}`\nAmount: ₹{amount}\nMethod: {method}",
        parse_mode="MarkdownV2"
    )
    await query.message.reply_text("**Withdraw Request Sent ✅**", reply_markup=main_buttons(), parse_mode="MarkdownV2")
    return ConversationHandler.END

# ===== PROOF FLOW =====
async def proof_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not await check_force_join(user_id, context):
        await update.message.reply_text(
            "🚨 **You Must Join Our Channel First!** 🚨",
            reply_markup=join_button(),
            parse_mode="MarkdownV2"
        )
        return
    if update.message.photo or update.message.document:
        context.user_data["proof_file"] = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
        await update.message.reply_text("**Send Your Refer Link Now:**", parse_mode="MarkdownV2")
        return PROOF_LINK
    else:
        await update.message.reply_text("**Send A Screenshot Or Document ❌**", parse_mode="MarkdownV2")
        return PROOF_SCREENSHOT

async def proof_refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    refer_link = update.message.text
    proof_file = context.user_data.get("proof_file")
    if not proof_file:
        await update.message.reply_text("**Send Screenshot First ❌**", parse_mode="MarkdownV2")
        return PROOF_SCREENSHOT
    await context.bot.send_photo(
        ADMIN_ID,
        photo=proof_file,
        caption=f"`User ID: {user_id}`\n**Refer Link:** {refer_link}",
        parse_mode="MarkdownV2"
    )
    await update.message.reply_text("**Proof Submitted ✅**", reply_markup=main_buttons(), parse_mode="MarkdownV2")
    return ConversationHandler.END

# ===== CANCEL =====
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("**Operation Cancelled ✅**", reply_markup=main_buttons(), parse_mode="MarkdownV2")
    return ConversationHandler.END

# ===== MAIN =====
app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(button_handler)],
    states={
        PROOF_SCREENSHOT: [MessageHandler(filters.PHOTO | filters.Document.ALL, proof_screenshot)],
        PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_refer)],
        PAYMENT_METHOD_FLOW: [CallbackQueryHandler(payment_method_choice)],
        WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
        WITHDRAW_METHOD: [CallbackQueryHandler(withdraw_method_choice)],
        WITHDRAW_CONFIRM: [CallbackQueryHandler(withdraw_submit)],
    },
    fallbacks=[CallbackQueryHandler(cancel)]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)

print("Bot Running 24/7 ✅")
app.run_polling()
