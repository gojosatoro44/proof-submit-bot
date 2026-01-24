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
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
BOT_TOKEN = "8548363818:AAGBl61ZfCenlQwKhuAzBFPoTqd1Dy2qHN0"
ADMIN_ID = 7112312810
PAYMENT_BOT_LINK = "http://t.me/Bot_Tasks_Payment_Bot"

# ================= STORAGE =================
user_state = {}

# ================= KEYBOARDS =================
main_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📤 Proof Submit")],
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
        reply_markup=main_keyboard,
        parse_mode="Markdown",
    )

# ================= PAYMENT =================
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"**CLICK BELOW FOR PAYMENT STATUS**\n{PAYMENT_BOT_LINK}",
        parse_mode="Markdown",
    )

# ================= PROOF START =================
async def proof_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.effective_user.id] = "awaiting_proof"
    await update.message.reply_text(
        "**PLEASE SEND SCREENSHOT WHERE REFER LINK IS VISIBLE**",
        reply_markup=cancel_keyboard,
        parse_mode="Markdown",
    )

# ================= CANCEL =================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state.pop(update.effective_user.id, None)
    await update.message.reply_text(
        "**PROCESS CANCELLED**",
        reply_markup=main_keyboard,
        parse_mode="Markdown",
    )

# ================= HANDLE PHOTO =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if user_state.get(uid) != "awaiting_proof":
        return

    user_state[uid] = "awaiting_link"
    context.user_data["photo"] = update.message.photo[-1].file_id

    await update.message.reply_text(
        "**NOW SEND YOUR REFER LINK**",
        parse_mode="Markdown",
    )

# ================= HANDLE LINK =================
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if user_state.get(uid) != "awaiting_link":
        return

    refer_link = update.message.text
    photo_id = context.user_data.get("photo")

    buttons = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("✅ Verified", callback_data=f"verify_{uid}"),
            InlineKeyboardButton("❌ Fake", callback_data=f"fake_{uid}")
        ]]
    )

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_id,
        caption=(
            "**NEW PROOF RECEIVED**\n\n"
            f"**USER ID:** `{uid}`\n"
            f"**REFER LINK:** {refer_link}"
        ),
        reply_markup=buttons,
        parse_mode="Markdown",
    )

    user_state.pop(uid, None)
    await update.message.reply_text(
        "**PROOF SUBMITTED SUCCESSFULLY**",
        reply_markup=main_keyboard,
        parse_mode="Markdown",
    )

# ================= ADMIN ACTION =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, uid = query.data.split("_")
    uid = int(uid)

    if action == "verify":
        await query.edit_message_caption(
            caption="**STATUS: VERIFIED ✅**",
            parse_mode="Markdown",
        )
        await context.bot.send_message(
            chat_id=uid,
            text="**YOUR PROOF HAS BEEN VERIFIED ✅**",
            parse_mode="Markdown",
        )

    else:
        await query.edit_message_caption(
            caption="**STATUS: FAKE ❌**",
            parse_mode="Markdown",
        )
        await context.bot.send_message(
            chat_id=uid,
            text="**YOUR PROOF WAS MARKED FAKE ❌**",
            parse_mode="Markdown",
        )

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Text("📤 Proof Submit"), proof_start))
    app.add_handler(MessageHandler(filters.Text("💰 Where Is My Payment"), payment))
    app.add_handler(MessageHandler(filters.Text("❌ Cancel"), cancel))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(admin_action))

    app.run_polling()

if __name__ == "__main__":
    main()
