from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ======= CONFIG =======
import os
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# ======= BUTTONS =======
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Submit Proof", callback_data="submit_proof")],
        [InlineKeyboardButton("Where Is My Payment", url="http://t.me/Bot_Tasks_Payment_Bot")],
        [InlineKeyboardButton("Help", callback_data="help_menu")],
        [InlineKeyboardButton("Support", url="http://t.me/dtxzahid")]
    ]
    return InlineKeyboardMarkup(keyboard)

def help_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Payment Kaha Milega", callback_data="payment_info")],
        [InlineKeyboardButton("Proof Kaise Bheju", url="https://t.me/BotTaskPayment/2424")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_proof_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("Accept", callback_data=f"accept|{user_id}"),
         InlineKeyboardButton("Reject", callback_data=f"reject|{user_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def cancel_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data="cancel_proof")]])

# ======= COMMANDS =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("**Welcome To The Bot!**", reply_markup=main_menu_keyboard(), parse_mode="MarkdownV2")

# ======= CALLBACK HANDLERS =======
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "submit_proof":
        await query.message.reply_text("**Please Send Screenshot Of Proof With Refer Link Visible**", reply_markup=cancel_button(), parse_mode="MarkdownV2")

    elif data == "cancel_proof":
        await query.message.reply_text("**Proof Submission Cancelled**", reply_markup=main_menu_keyboard(), parse_mode="MarkdownV2")

    elif data == "help_menu":
        await query.message.reply_text("**Help Menu:**", reply_markup=help_menu_keyboard(), parse_mode="MarkdownV2")

    elif data == "payment_info":
        await query.message.reply_text(
            "**Bhai Proof Submit Kro Aur 5-10 Min Proof Verify Hoti Hai Payment Apka Bot Mai Add Hojayega**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Bot", url="http://t.me/Bot_Tasks_Payment_Bot")]]),
            parse_mode="MarkdownV2"
        )

    elif data.startswith("accept|"):
        user_id = int(data.split("|")[1])
        await context.bot.send_message(chat_id=user_id, text="**Bro Apka Refer Count Hogya Payment 5-10 Min Ma Bot Mai Aayega**", parse_mode="MarkdownV2")
        await query.message.edit_text("**Proof Accepted ✅**")

    elif data.startswith("reject|"):
        user_id = int(data.split("|")[1])
        await context.bot.send_message(chat_id=user_id, text="**Bro Apka Refer Nahi Aaya Hai So Payment Nahi Milega**", parse_mode="MarkdownV2")
        await query.message.edit_text("**Proof Rejected ❌**")

# ======= MESSAGE HANDLER FOR PROOF =======
async def proof_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo or update.message.document:
        user_id = update.message.from_user.id
        # Extract refer link from message text
        refer_link = update.message.caption if update.message.caption else "No Refer Link Provided"

        # Send to admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"`User ID: {user_id}`\n**Refer Link:** {refer_link}",
            reply_markup=admin_proof_keyboard(user_id),
            parse_mode="MarkdownV2"
        )

        # Confirm to user
        await update.message.reply_text("**Your Proof Has Been Submitted ✅**", reply_markup=main_menu_keyboard(), parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("**Please Send A Screenshot Or Document**", parse_mode="MarkdownV2")

# ======= MAIN =======
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, proof_handler))

    print("Bot Is Running 24/7 ...")
    app.run_polling()
