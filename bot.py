==============================

TELEGRAM SUBMIT PROOF BOT

python-telegram-bot v20+

Railway + GitHub READY

==============================

import os import json from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, )

==============================

CONFIG (DO NOT CHANGE LOGIC)

==============================

BOT_TOKEN = os.getenv("BOT_TOKEN") or "PASTE_YOUR_BOT_TOKEN" ADMIN_ID = int(os.getenv("ADMIN_ID") or 123456789) FORCE_CHANNEL = "@yourchannel"   # without https

VERIFIED_IDS_FILE = "verified_ids.json"

==============================

FILE HELPERS

==============================

def load_json(path, default): if not os.path.exists(path): return default with open(path, "r") as f: return json.load(f)

def save_json(path, data): with open(path, "w") as f: json.dump(data, f, indent=2)

verified_ids = set(load_json(VERIFIED_IDS_FILE, []))

==============================

FORCE JOIN CHECK

==============================

async def is_joined(bot, user_id): try: member = await bot.get_chat_member(FORCE_CHANNEL, user_id) return member.status in ["member", "administrator", "creator"] except: return False

==============================

START COMMAND

==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id

if not await is_joined(context.bot, user_id):
    btn = [[InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_CHANNEL.replace('@','')}")]]
    await update.message.reply_text(
        "❌ You must join our channel to use this bot",
        reply_markup=InlineKeyboardMarkup(btn)
    )
    return

keyboard = [[InlineKeyboardButton("📤 Submit Proof", callback_data="submit_proof")]]
await update.message.reply_text(
    "✅ Welcome!\nClick below to submit your proof",
    reply_markup=InlineKeyboardMarkup(keyboard)
)

==============================

SUBMIT PROOF BUTTON

==============================

async def submit_proof_btn(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer()

context.user_data["awaiting_proof"] = True
await query.message.reply_text("📸 Send your payment proof (image)")

==============================

RECEIVE PROOF

==============================

async def receive_proof(update: Update, context: ContextTypes.DEFAULT_TYPE): if not context.user_data.get("awaiting_proof"): return

user_id = update.effective_user.id
status = "✅ VERIFIED" if user_id in verified_ids else "❌ UNVERIFIED"

caption = (
    "📩 NEW PROOF SUBMITTED\n\n"
    f"👤 User ID: {user_id}\n"
    f"📌 Status: {status}"
)

if update.message.photo:
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=caption
    )
else:
    await context.bot.send_document(
        chat_id=ADMIN_ID,
        document=update.message.document.file_id,
        caption=caption
    )

context.user_data["awaiting_proof"] = False
await update.message.reply_text("✅ Proof submitted successfully")

==============================

ADMIN: ADD VERIFIED ID

==============================

async def add_verified(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.id != ADMIN_ID: return

if not context.args:
    await update.message.reply_text("Usage: /addid USER_ID")
    return

verified_ids.add(int(context.args[0]))
save_json(VERIFIED_IDS_FILE, list(verified_ids))
await update.message.reply_text("✅ ID added to verified list")

==============================

MAIN

==============================

async def main(): app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addid", add_verified))
app.add_handler(CallbackQueryHandler(submit_proof_btn, pattern="submit_proof"))
app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, receive_proof))

print("Bot started successfully")
await app.run_polling()

if name == "main": import asyncio asyncio.run(main())
