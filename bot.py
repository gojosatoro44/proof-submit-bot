from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import os

# ===== CONFIG =====
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# ===== KEYBOARDS =====
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Submit Proof", callback_data="submit_proof")],
        [InlineKeyboardButton("💰 Where Is My Payment", url="http://t.me/Bot_Tasks_Payment_Bot")],
        [InlineKeyboardButton("❓ Help", callback_data="help_menu")],
        [InlineKeyboardButton("🆘 Support", url="http://t.me/dtxzahid")]
    ])

def help_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Payment Kaha Milega", callback_data="payment_info")],
        [InlineKeyboardButton("📸 Proof Kaise Bheju", url="https://t.me/BotTaskPayment/2424")]
    ])

def admin_proof_keyboard(user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept|{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject|{user_id}")
        ]
    ])

def cancel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_proof")]
    ])

# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 **Welcome To Proof Submit Bot** 🔥\n\n"
        "📌 **Submit your proof correctly and get paid fast!**\n"
        "⏱ Proof verification takes *5–10 minutes*\n\n"
        "👇 Choose an option below"
    )
    await update.message.reply_text(
        text,
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )

# ===== CALLBACK HANDLER =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "submit_proof":
        context.user_data.clear()
        context.user_data["await_screenshot"] = True
        await query.message.reply_text(
            "📸 **Send Screenshot**\n\n"
            "⚠️ Screenshot must have **Refer Link clearly visible**",
            reply_markup=cancel_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "cancel_proof":
        context.user_data.clear()
        await query.message.reply_text(
            "❌ **Proof submission cancelled**",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "help_menu":
        await query.message.reply_text(
            "❓ **Help Section**",
            reply_markup=help_menu_keyboard(),
            parse_mode="Markdown"
        )

    elif data == "payment_info":
        await query.message.reply_text(
            "💰 **Bhai Proof Submit Kro**\n"
            "⏳ 5–10 min me verify hota hai\n"
            "✅ Payment bot me add ho jata hai",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 Bot", url="http://t.me/Bot_Tasks_Payment_Bot")]
            ]),
            parse_mode="Markdown"
        )

    elif data.startswith("accept|"):
        user_id = int(data.split("|")[1])
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ **Bro apka refer count ho gaya**\n💰 Payment 5–10 min me bot me aa jayega",
            parse_mode="Markdown"
        )
        await query.message.edit_text("✅ **Proof Accepted**")

    elif data.startswith("reject|"):
        user_id = int(data.split("|")[1])
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ **Bro apka refer nahi aaya**\n🚫 Isliye payment nahi milega",
            parse_mode="Markdown"
        )
        await query.message.edit_text("❌ **Proof Rejected**")

# ===== MESSAGE HANDLER =====
async def proof_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    # STEP 1: Screenshot
    if context.user_data.get("await_screenshot"):
        if not update.message.photo:
            await update.message.reply_text(
                "⚠️ **Please send screenshot only**",
                parse_mode="Markdown"
            )
            return

        context.user_data["screenshot"] = update.message.photo[-1].file_id
        context.user_data["await_screenshot"] = False
        context.user_data["await_refer"] = True

        await update.message.reply_text(
            "🔗 **Now send your Refer Link**",
            parse_mode="Markdown"
        )
        return

    # STEP 2: Refer Link
    if context.user_data.get("await_refer"):
        refer_link = update.message.text
        screenshot_file_id = context.user_data.get("screenshot")

        # Send to admin
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=screenshot_file_id,
            caption=(
                f"`{user_id}`\n\n"
                f"🔗 **Refer Link:**\n{refer_link}"
            ),
            reply_markup=admin_proof_keyboard(user_id),
            parse_mode="Markdown"
        )

        context.user_data.clear()

        await update.message.reply_text(
            "✅ **Your proof has been submitted successfully**\n"
            "⏳ Please wait for verification",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

# ===== MAIN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, proof_handler))

    print("🤖 Bot running 24/7...")
    app.run_polling()
