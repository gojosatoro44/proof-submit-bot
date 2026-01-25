import asyncio
import os
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # set in Railway Variables
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # set in Railway Variables
FORCE_CHANNEL = "@TaskByZahid"
# =========================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
        """)
        await db.commit()

# ================= FORCE JOIN =================
async def is_joined(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(FORCE_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

def join_markup():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Join Channel", url="http://t.me/TaskByZahid")],
            [InlineKeyboardButton(text="🔄 Check Join", callback_data="check_join")]
        ]
    )

# ================= MAIN KEYBOARD =================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📸 Submit Proof"),
            KeyboardButton(text="💰 Balance")
        ],
        [
            KeyboardButton(text="💸 Withdraw"),
            KeyboardButton(text="🆘 Support")
        ]
    ],
    resize_keyboard=True
)

# ================= START =================
@dp.message(Command("start"))
async def start_cmd(msg: Message):
    if not await is_joined(msg.from_user.id):
        await msg.answer(
            "❌ You must join our channel to use this bot",
            reply_markup=join_markup()
        )
        return

    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (msg.from_user.id,)
        )
        await db.commit()

    await msg.answer(
        "👋 Welcome to Task Bot",
        reply_markup=main_keyboard
    )

@dp.callback_query(F.data == "check_join")
async def check_join(cb: CallbackQuery):
    if await is_joined(cb.from_user.id):
        await cb.message.delete()
        await start_cmd(cb.message)
    else:
        await cb.answer("❌ Please join the channel first", show_alert=True)

# ================= PROOF SUBMIT =================
user_proof = {}

@dp.message(F.text == "📸 Submit Proof")
async def submit_proof(msg: Message):
    await msg.answer("📸 Send Screenshot of bot")

@dp.message(F.photo)
async def receive_screenshot(msg: Message):
    user_proof[msg.from_user.id] = {
        "photo": msg.photo[-1].file_id
    }
    await msg.answer("🔗 Send your refer link to verify")

@dp.message(F.text)
async def receive_refer(msg: Message):
    if msg.from_user.id not in user_proof:
        return

    user_proof[msg.from_user.id]["refer"] = msg.text

    data = user_proof.pop(msg.from_user.id)

    await bot.send_photo(
        ADMIN_ID,
        data["photo"],
        caption=(
            f"📸 NEW PROOF SUBMITTED\n\n"
            f"👤 User ID: {msg.from_user.id}\n"
            f"🔗 Refer Link: {data['refer']}"
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Accept",
                        callback_data=f"proof_accept:{msg.from_user.id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Reject",
                        callback_data=f"proof_reject:{msg.from_user.id}"
                    )
                ]
            ]
        )
    )

    await msg.answer("✅ Proof has been submitted successfully for verification")

@dp.callback_query(F.data.startswith("proof_"))
async def proof_action(cb: CallbackQuery):
    action, uid = cb.data.split(":")
    uid = int(uid)

    if action == "proof_accept":
        await bot.send_message(
            uid,
            "✅ Proof has been verified successfully\nBalance will be added in 5–10 minutes"
        )
    else:
        await bot.send_message(
            uid,
            "❌ Owner has rejected your proof due to fake proof / same device"
        )

    await cb.message.edit_reply_markup()

# ================= BALANCE =================
@dp.message(F.text == "💰 Balance")
async def balance(msg: Message):
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (msg.from_user.id,)
        )
        bal = (await cur.fetchone())[0]

    await msg.answer(
        f"💰 Your Balance: ₹{bal}\n\n"
        f"Keep completing tasks to earn more 💸"
    )

# ================= WITHDRAW =================
@dp.message(F.text == "💸 Withdraw")
async def withdraw(msg: Message):
    await msg.answer(
        "Select withdraw method",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="VSV", callback_data="wd:VSV"),
                    InlineKeyboardButton(text="FXL", callback_data="wd:FXL"),
                    InlineKeyboardButton(text="UPI", callback_data="wd:UPI")
                ]
            ]
        )
    )

withdraw_cache = {}

@dp.callback_query(F.data.startswith("wd:"))
async def wd_method(cb: CallbackQuery):
    method = cb.data.split(":")[1]
    withdraw_cache[cb.from_user.id] = {"method": method}

    if method == "UPI":
        await cb.message.answer("💳 Please send your verified UPI ID")
    else:
        await cb.message.answer("💼 Send your registered wallet number")

@dp.message()
async def wd_amount(msg: Message):
    if msg.from_user.id not in withdraw_cache:
        return

    cache = withdraw_cache[msg.from_user.id]

    if "wallet" not in cache:
        cache["wallet"] = msg.text
        await msg.answer(
            "💰 How much amount you want to withdraw?\n\n"
            "Minimum:\n"
            "• UPI ₹5\n"
            "• VSV/FXL ₹2"
        )
        return

    amount = int(msg.text)
    min_amt = 5 if cache["method"] == "UPI" else 2

    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (msg.from_user.id,)
        )
        bal = (await cur.fetchone())[0]

    if amount < min_amt or amount > bal:
        await msg.answer("❌ Invalid amount or insufficient balance")
        return

    await bot.send_message(
        ADMIN_ID,
        (
            f"💸 WITHDRAW REQUEST\n\n"
            f"User ID: {msg.from_user.id}\n"
            f"Method: {cache['method']}\n"
            f"Detail: {cache['wallet']}\n"
            f"Amount: ₹{amount}"
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Withdraw Cleared",
                        callback_data=f"wd_ok:{msg.from_user.id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Withdraw Rejected",
                        callback_data=f"wd_no:{msg.from_user.id}"
                    )
                ]
            ]
        )
    )

    withdraw_cache.pop(msg.from_user.id)
    await msg.answer("✅ Withdraw request has been sent to owner")

@dp.callback_query(F.data.startswith("wd_"))
async def wd_action(cb: CallbackQuery):
    action, uid = cb.data.split(":")
    uid = int(uid)

    if action == "wd_ok":
        await bot.send_message(
            uid,
            "✅ Your withdraw has been successfully proceeded. Please check ☑️"
        )
    else:
        await bot.send_message(
            uid,
            "❌ Your withdraw has been rejected due to fake refers / other issue"
        )

    await cb.message.edit_reply_markup()

# ================= SUPPORT =================
@dp.message(F.text == "🆘 Support")
async def support(msg: Message):
    await msg.answer(
        "If you are facing any issue in proof or withdraw,\n"
        "Contact Owner: @DTXZAHID"
    )

# ================= ADMIN PANEL =================
@dp.message(Command("admin"))
async def admin_panel(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total = (await cur.fetchone())[0]

    await msg.answer(
        f"👑 Admin Panel\n\n"
        f"👥 Total Users: {total}"
    )

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
