import asyncio
import os
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # 🔥 fallback FIX
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
        [KeyboardButton(text="📸 Submit Proof"), KeyboardButton(text="💰 Balance")],
        [KeyboardButton(text="💸 Withdraw"), KeyboardButton(text="🆘 Support")]
    ],
    resize_keyboard=True
)

# ================= START =================
@dp.message(Command("start"))
async def start_cmd(msg: Message):
    if not await is_joined(msg.from_user.id):
        await msg.answer("❌ You must join our channel", reply_markup=join_markup())
        return

    async with aiosqlite.connect("bot.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (msg.from_user.id,)
        )
        await db.commit()

    await msg.answer("👋 Welcome to Task Bot", reply_markup=main_keyboard)

@dp.callback_query(F.data == "check_join")
async def check_join(cb: CallbackQuery):
    if await is_joined(cb.from_user.id):
        await cb.message.delete()
        await start_cmd(cb.message)
    else:
        await cb.answer("Join channel first", show_alert=True)

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
        f"Complete tasks to earn more 🔥"
    )

# ================= SUPPORT =================
@dp.message(F.text == "🆘 Support")
async def support(msg: Message):
    await msg.answer(
        "If you face any issue in proof or withdraw,\n"
        "Contact Owner: @DTXZAHID"
    )

# ================= PROOF SUBMIT =================
user_proof = {}

@dp.message(F.text == "📸 Submit Proof")
async def submit_proof(msg: Message):
    await msg.answer("📸 Send Screenshot of Bot")

@dp.message(F.photo)
async def receive_screenshot(msg: Message):
    user_proof[msg.from_user.id] = {"photo": msg.photo[-1].file_id}
    await msg.answer("🔗 Send your refer link to verify")

@dp.message(F.text & ~F.text.startswith("/"))
async def receive_refer(msg: Message):
    if msg.from_user.id not in user_proof:
        return

    data = user_proof.pop(msg.from_user.id)
    refer = msg.text

    await bot.send_photo(
        ADMIN_ID,
        data["photo"],
        caption=(
            f"📸 NEW PROOF\n\n"
            f"👤 User ID: {msg.from_user.id}\n"
            f"🔗 Refer: {refer}"
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✅ Accept", callback_data=f"proof_ok:{msg.from_user.id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"proof_no:{msg.from_user.id}")
            ]]
        )
    )

    await msg.answer("✅ Proof submitted successfully for verification")

@dp.callback_query(F.data.startswith("proof_"))
async def proof_action(cb: CallbackQuery):
    action, uid = cb.data.split(":")
    uid = int(uid)

    if action == "proof_ok":
        await bot.send_message(uid, "✅ Proof verified\nBalance will be added in 5–10 minutes")
    else:
        await bot.send_message(uid, "❌ Proof rejected due to fake/same device")

    await cb.message.edit_reply_markup()

# ================= WITHDRAW =================
withdraw_cache = {}

@dp.message(F.text == "💸 Withdraw")
async def withdraw(msg: Message):
    await msg.answer(
        "Select withdraw method",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="VSV", callback_data="wd:VSV"),
                InlineKeyboardButton(text="FXL", callback_data="wd:FXL"),
                InlineKeyboardButton(text="UPI", callback_data="wd:UPI")
            ]]
        )
    )

@dp.callback_query(F.data.startswith("wd:"))
async def wd_method(cb: CallbackQuery):
    method = cb.data.split(":")[1]
    withdraw_cache[cb.from_user.id] = {"method": method}
    await cb.message.answer(
        "Send UPI ID" if method == "UPI" else "Send wallet number"
    )

@dp.message()
async def wd_amount(msg: Message):
    uid = msg.from_user.id
    if uid not in withdraw_cache:
        return

    cache = withdraw_cache[uid]

    if "wallet" not in cache:
        cache["wallet"] = msg.text
        await msg.answer(
            "Enter amount\n\n"
            "UPI min ₹5\nVSV/FXL min ₹2"
        )
        return

    amount = int(msg.text)
    min_amt = 5 if cache["method"] == "UPI" else 2

    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (uid,)
        )
        bal = (await cur.fetchone())[0]

    if amount < min_amt or amount > bal:
        await msg.answer("❌ Invalid amount or insufficient balance")
        return

    await bot.send_message(
        ADMIN_ID,
        f"💸 WITHDRAW\n\nUser: {uid}\nMethod: {cache['method']}\n"
        f"Detail: {cache['wallet']}\nAmount: ₹{amount}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="✅ Cleared", callback_data=f"wd_ok:{uid}"),
                InlineKeyboardButton(text="❌ Rejected", callback_data=f"wd_no:{uid}")
            ]]
        )
    )

    withdraw_cache.pop(uid)
    await msg.answer("✅ Withdraw request sent to owner")

@dp.callback_query(F.data.startswith("wd_"))
async def wd_action(cb: CallbackQuery):
    action, uid = cb.data.split(":")
    uid = int(uid)

    if action == "wd_ok":
        await bot.send_message(uid, "✅ Withdraw successful, please check ☑️")
    else:
        await bot.send_message(uid, "❌ Withdraw rejected due to fake refers / issue")

    await cb.message.edit_reply_markup()

# ================= RUN =================
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
