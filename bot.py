from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import os

# ===== CONFIG =====
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# ===== KEYBOARDS =====
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Submit Proof", callback_data="submit_proof")],
        [InlineKeyboardButton("Where Is My Payment", url="http://t.me/Bot_Tasks_Payment_Bot")],
        [InlineKeyboardButton("Help", callback_data="help")],
        [InlineKeyboardButton("Support", url="http://t.me/dtxzahid")]
    ])

def help_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Payment Kaha Milega", callback_data="payment_info")],
        [InlineKeyboardButton("Proof Kaise Bheju", url="https://t.me/BotTaskPayment/2424")]
    ])

def admin_buttons(user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Accept", callback_data=f"accept:{user_id}"),
            InlineKeyboardButton("Reject", callback_data=f"reject:{user_id}")
        ]
    ])

# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Welcome To The Bot!</b>",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

# ===== CALLBACKS =====
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "submit_proof":
        await q.message.reply_text(
            "<b>Send Screenshot With Refer Link Visible</b>",
            parse_mode="HTML"
        )

    elif q.data == "help":
        await q.message.reply_text(
            "<b>Help Menu</b>",
            reply_markup=help_menu(),
            parse_mode="HTML"
        )

    elif q.data == "payment_info":
        await q.message.reply_text(
            "<b>Bhai Proof Submit Kro Aur 5-10 Min Me Verify Hoke Payment Bot Me Add Ho Jayega</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Bot", url="http://t.me/Bot_Tasks_Payment_Bot")]
            ]),
            parse_mode="HTML"
        )

    elif q.data.startswith("accept:"):
        user_id = int(q.data.split(":")[1])
        await context.bot.send_message(
            chat_id=user_id,
            text="<b>Bro Apka Refer Count Hogya, Payment 5-10 Min Me Bot Me Aayega</b>",
            parse_mode="HTML"
        )
        await q.message.edit_text("<b>Proof Accepted ✅</b>", parse_mode="HTML")

    elif q.data.startswith("reject:"):
        user_id = int(q.data.split(":")[1])
        await context.bot.send_message(
            chat_id=user_id,
            text="<b>Bro Apka Refer Nahi Aaya Hai, Payment Nahi Milega</b>",
            parse_mode="HTML"
        )
        await q.message.edit_text("<b>Proof Rejected ❌</b>", parse_mode="HTML")

# ===== PROOF HANDLER =====
async def proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("<b>Please Send Screenshot Only</b>", parse_mode="HTML")
        return

    user_id = update.message.from_user.id
    caption = update.message.caption or "No Refer Link"

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"<code>User ID: {user_id}</code>\n<b>Refer Link:</b> {caption}",
        reply_markup=admin_buttons(user_id),
        parse_mode="HTML"
    )

    await update.message.reply_text(
        "<b>Proof Submitted Successfully ✅</b>",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

# ===== MAIN =====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.PHOTO, proof))

    print("Bot Running 24/7")
    app.run_polling()
