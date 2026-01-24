import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

# ================= CONFIG =================
BOT_TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810
PAYMENT_BOT_LINK = "http://t.me/Bot_Tasks_Payment_Bot"

# ================= USER STATES =================
user_data_store = {}

# ================= KEYBOARDS =================
main_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📥 Proof Submit")],
        [KeyboardButton("💰 Where Is My Payment")],
    ],
    resize_keyboard=True,
)

cancel_keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("❌ Cancel")]],
    resize_keyboard=True,
)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "**WELCOME TO PROOF SUBMIT BOT**",
        parse_mode="Markdown",
        reply_markup=main_keyboard,
    )

# ================= PAYMENT BUTTON =================
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"**CLICK BELOW TO CHECK PAYMENT STATUS**\n\n{PAYMENT_BOT_LINK}",
        parse_mode="Markdown",
    )

# ================= PROOF SUBMIT =================
async def proof_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data_store[user_id] = {"step": "photo"}

    await update.message.reply_text(
        "**PLEASE SEND SCREENSHOT WHERE REFER LINK IS VISIBLE**",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard,
    )

# ================= PHOTO HANDLER =================
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_data_store or user_data_store[user_id]["step"] != "photo":
        return

    user_data_store[user_id]["photo"] = update.message.photo[-1].file_id
    user_data_store[user_id]["step"] = "link"

    await update.message.reply_text(
        "**NOW SEND YOUR REFER LINK**",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard,
    )

# ================= TEXT HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text == "❌ Cancel":
        user_data_store.pop(user_id, None)
        await update.message.reply_text(
            "**PROCESS CANCELLED**",
            parse_mode="Markdown",
            reply_markup=main_keyboard,
        )
        return

    if user_id not in user_data_store:
        return

    if user_data_store[user_id]["step"] == "link":
        user_data_store[user_id]["link"] = text
        user_data_store[user_id]["step"] = "confirm"

        await update.message.reply_text(
            "**PLEASE CONFIRM YOUR PROOF**\n\n"
            f"**REFER LINK:** {text}\n\n"
            "**NOTE:** Jis Id Se Proof Submit Kroge Paise Ussi Id Me Add Hoga",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("✅ Submit"), KeyboardButton("❌ Cancel")]],
                resize_keyboard=True,
            ),
        )

    elif text == "✅ Submit" and user_data_store[user_id]["step"] == "confirm":
        data = user_data_store[user_id]

        buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Verified", callback_data=f"verify_{user_id}"),
                    InlineKeyboardButton("❌ Fake", callback_data=f"fake_{user_id}"),
                ]
            ]
        )

        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=data["photo"],
            caption=(
                "**NEW PROOF RECEIVED**\n\n"
                f"**USER ID:** `{user_id}`\n"
                f"**REFER LINK:** {data['link']}"
            ),
            parse_mode="Markdown",
            reply_markup=buttons,
        )

        await update.message.reply_text(
            "**YOUR PROOF HAS BEEN SUBMITTED SUCCESSFULLY ⏳**",
            parse_mode="Markdown",
            reply_markup=main_keyboard,
        )

        user_data_store.pop(user_id, None)

# ================= ADMIN ACTION =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_id = query.data.split("_")
    user_id = int(user_id)

    if action == "verify":
        await context.bot.send_message(
            chat_id=user_id,
            text="**PROOF HAS BEEN SUCCESSFULLY VERIFIED ✅**\n\n**PLEASE CHECK YOUR BOT BALANCE**",
            parse_mode="Markdown",
        )
        await query.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("✅ VERIFIED", callback_data="done")]])
        )

    elif action == "fake":
        await context.bot.send_message(
            chat_id=user_id,
            text="**YOUR PROOF WAS MARKED AS FAKE ❌**",
            parse_mode="Markdown",
        )
        await query.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("❌ FAKE", callback_data="done")]])
        )

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^💰"), payment))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^📥"), proof_submit))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT, text_handler))
    app.add_handler(CallbackQueryHandler(admin_action))

    print("Bot Running 24/7...")
    app.run_polling()

if __name__ == "__main__":
    main()
