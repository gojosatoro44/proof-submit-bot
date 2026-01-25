import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# ================= CONFIG =================
BOT_TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810
CHANNEL_USERNAME = "TaskByZahid"

logging.basicConfig(level=logging.INFO)

# ================= STATES =================
PROOF_PHOTO, PROOF_LINK = range(2)
PAYMENT_TEXT = 3
W_METHOD, W_DETAIL, W_AMOUNT, W_CONFIRM = range(4, 8)

# ================= FORCE JOIN =================
async def is_joined(update, context):
    try:
        member = await context.bot.get_chat_member(
            f"@{CHANNEL_USERNAME}", update.effective_user.id
        )
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


async def force_join(update, context):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")],
        [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
    ])
    await update.message.reply_text(
        "🚫 **Access Locked**\n\n"
        "You must join our channel to use this bot.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# ================= START =================
async def start(update, context):
    if not await is_joined(update, context):
        return await force_join(update, context)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Submit Proof", callback_data="submit_proof")],
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")
        ],
        [InlineKeyboardButton("💳 Payment Method", callback_data="payment_method")],
    ])

    await update.message.reply_text(
        "✨ **Welcome Back!** ✨\n\nChoose an option below 👇",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def check_join(update, context):
    query = update.callback_query
    await query.answer()
    if await is_joined(update, context):
        await query.message.delete()
        await start(update, context)
    else:
        await query.answer("Join the channel first!", show_alert=True)


# ================= SUBMIT PROOF =================
async def submit_proof_start(update, context):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📸 **Send proof screenshot**\n\n"
        "⚠ Refer link must be visible",
        parse_mode="Markdown"
    )
    return PROOF_PHOTO


async def proof_photo(update, context):
    context.user_data["proof_photo"] = update.message.photo[-1].file_id
    await update.message.reply_text(
        "🔗 **Now send your refer link**",
        parse_mode="Markdown"
    )
    return PROOF_LINK


async def proof_link(update, context):
    user = update.effective_user

    await context.bot.send_photo(
        ADMIN_ID,
        context.user_data["proof_photo"],
        caption=(
            "📥 **New Proof Received**\n\n"
            f"👤 User ID: `{user.id}`\n"
            f"🔗 Refer Link: {update.message.text}"
        ),
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ **Proof submitted successfully**",
        parse_mode="Markdown"
    )
    context.user_data.clear()
    return ConversationHandler.END


# ================= PAYMENT METHOD (FIXED) =================
async def payment_method_start(update, context):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "💳 **Send your payment details**\n\n"
        "Examples:\n"
        "• UPI: yourupi@bank\n"
        "• VSV: 9XXXXXXXXX\n"
        "• FXL: 9XXXXXXXXX",
        parse_mode="Markdown"
    )
    return PAYMENT_TEXT


async def save_payment_method(update, context):
    context.user_data["payment_method"] = update.message.text

    await update.message.reply_text(
        "✅ **Payment method saved successfully**",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# ================= WITHDRAW (UNCHANGED) =================
async def withdraw_start(update, context):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "💸 **Enter withdraw method**\n\n"
        "UPI / VSV / FXL",
        parse_mode="Markdown"
    )
    return W_METHOD


async def withdraw_method(update, context):
    context.user_data["w_method"] = update.message.text.upper()
    await update.message.reply_text(
        "📄 **Send your UPI ID or Number**",
        parse_mode="Markdown"
    )
    return W_DETAIL


async def withdraw_detail(update, context):
    context.user_data["w_detail"] = update.message.text
    await update.message.reply_text(
        "💰 **Enter amount to withdraw**",
        parse_mode="Markdown"
    )
    return W_AMOUNT


async def withdraw_amount(update, context):
    context.user_data["w_amount"] = update.message.text

    text = (
        "📤 **Withdraw Preview**\n\n"
        f"Method: {context.user_data['w_method']}\n"
        f"Detail: {context.user_data['w_detail']}\n"
        f"Amount: ₹{context.user_data['w_amount']}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Proceed", callback_data="w_proceed")],
        [InlineKeyboardButton("❌ Cancel", callback_data="w_cancel")]
    ])

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return W_CONFIRM


async def withdraw_confirm(update, context):
    query = update.callback_query
    await query.answer()

    if query.data == "w_proceed":
        user = query.from_user
        await context.bot.send_message(
            ADMIN_ID,
            (
                "💸 **Withdraw Request**\n\n"
                f"👤 User ID: `{user.id}`\n"
                f"Method: {context.user_data['w_method']}\n"
                f"Detail: {context.user_data['w_detail']}\n"
                f"Amount: ₹{context.user_data['w_amount']}"
            ),
            parse_mode="Markdown"
        )
        await query.message.reply_text(
            "✅ **Withdraw request sent**",
            parse_mode="Markdown"
        )
    else:
        await query.message.reply_text(
            "❌ **Withdraw cancelled**",
            parse_mode="Markdown"
        )

    context.user_data.clear()
    return ConversationHandler.END


# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(submit_proof_start, pattern="submit_proof")],
        states={
            PROOF_PHOTO: [MessageHandler(filters.PHOTO, proof_photo)],
            PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_link)],
        },
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(payment_method_start, pattern="payment_method")],
        states={
            PAYMENT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_payment_method)],
        },
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(withdraw_start, pattern="withdraw")],
        states={
            W_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_method)],
            W_DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_detail)],
            W_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
            W_CONFIRM: [CallbackQueryHandler(withdraw_confirm)],
        },
        fallbacks=[]
    ))

    app.run_polling()


if __name__ == "__main__":
    main()
