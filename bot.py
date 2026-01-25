import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.filters import Command
import aiosqlite

BOT_TOKEN = "8548363818:AAGiZ81aDQrBz3Eva2rXB4Pp6fp4RkFimBE"
ADMIN_ID = 7112312810
FORCE_CHANNEL = "@TaskByZahid"

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ---------- DATABASE ----------
async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
        """)
        await db.commit()

asyncio.get_event_loop().run_until_complete(init_db())

# ---------- FORCE JOIN ----------
async def is_joined(user_id):
    try:
        member = await bot.get_chat_member(FORCE_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def join_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Join Channel", url="http://t.me/TaskByZahid")],
        [InlineKeyboardButton(text="🔄 Check Join", callback_data="check_join")]
    ])

# ---------- START ----------
@dp.message(Command("start"))
async def start(msg: Message):
    if not await is_joined(msg.from_user.id):
        await msg.answer("❌ You must join channel to use bot", reply_markup=join_button())
        return

    async with aiosqlite.connect("bot.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (msg.from_user.id,))
        await db.commit()

    await msg.answer(
        "Welcome to Task Bot 👋",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                ["📸 Submit Proof", "💰 Balance"],
                ["💸 Withdraw", "🆘 Support"]
            ],
            resize_keyboard=True
        )
    )

@dp.callback_query(F.data == "check_join")
async def check_join(cb: CallbackQuery):
    if await is_joined(cb.from_user.id):
        await cb.message.delete()
        await start(cb.message)
    else:
        await cb.answer("❌ Still not joined", show_alert=True)

# ---------- SUBMIT PROOF ----------
@dp.message(F.text == "📸 Submit Proof")
async def submit_proof(msg: Message):
    await msg.answer("📸 Send Screenshot of bot")
    dp.message.register(get_screenshot)

async def get_screenshot(msg: Message):
    if not msg.photo:
        await msg.answer("❌ Send screenshot only")
        return
    dp.message.unregister(get_screenshot)
    dp.message.register(get_refer, photo=msg.photo[-1].file_id)
    await msg.answer("🔗 Send your refer link to verify")

async def get_refer(msg: Message, photo):
    refer = msg.text
    dp.message.unregister(get_refer)

    await bot.send_photo(
        ADMIN_ID,
        photo,
        caption=f"""
📸 NEW PROOF SUBMITTED

👤 User ID: {msg.from_user.id}
🔗 Refer Link: {refer}
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Accept", callback_data=f"proof_ok:{msg.from_user.id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"proof_no:{msg.from_user.id}")
            ]
        ])
    )

    await msg.answer("✅ Proof has been submitted successfully for verification")

@dp.callback_query(F.data.startswith("proof_"))
async def proof_action(cb: CallbackQuery):
    action, uid = cb.data.split(":")
    uid = int(uid)

    if action == "proof_ok":
        await bot.send_message(uid, "✅ Proof verified successfully\nBalance will be added in 5-10 minutes")
    else:
        await bot.send_message(uid, "❌ Proof rejected due to fake proof / same device")

    await cb.message.edit_reply_markup()

# ---------- BALANCE ----------
@dp.message(F.text == "💰 Balance")
async def balance(msg: Message):
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (msg.from_user.id,))
        bal = (await cur.fetchone())[0]
    await msg.answer(f"💰 Your Balance: ₹{bal}\nKeep completing tasks!")

# ---------- WITHDRAW ----------
@dp.message(F.text == "💸 Withdraw")
async def withdraw(msg: Message):
    await msg.answer(
        "Select Withdraw Method",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="VSV", callback_data="wd_VSV"),
             InlineKeyboardButton(text="FXL", callback_data="wd_FXL"),
             InlineKeyboardButton(text="UPI", callback_data="wd_UPI")]
        ])
    )

@dp.callback_query(F.data.startswith("wd_"))
async def wd_method(cb: CallbackQuery):
    method = cb.data.split("_")[1]
    await cb.message.answer(f"Send your {method} Wallet / UPI ID")
    dp.message.register(wd_amount, method=method)

async def wd_amount(msg: Message, method):
    wallet = msg.text
    dp.message.unregister(wd_amount)
    await msg.answer(
        f"Send withdraw amount\nMinimum:\nUPI ₹5\nVSV/FXL ₹2"
    )
    dp.message.register(wd_confirm, wallet=wallet, method=method)

async def wd_confirm(msg: Message, wallet, method):
    amount = int(msg.text)
    min_amt = 5 if method == "UPI" else 2

    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (msg.from_user.id,))
        bal = (await cur.fetchone())[0]

    if amount < min_amt or amount > bal:
        await msg.answer("❌ Invalid amount")
        return

    await bot.send_message(
        ADMIN_ID,
        f"""
💸 WITHDRAW REQUEST

User ID: {msg.from_user.id}
Method: {method}
Detail: {wallet}
Amount: ₹{amount}
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Withdraw Cleared", callback_data=f"wd_ok:{msg.from_user.id}:{amount}"),
                InlineKeyboardButton(text="❌ Withdraw Rejected", callback_data=f"wd_no:{msg.from_user.id}")
            ]
        ])
    )
    await msg.answer("✅ Withdraw request sent to owner")

# ---------- SUPPORT ----------
@dp.message(F.text == "🆘 Support")
async def support(msg: Message):
    await msg.answer(
        "If you are facing any issue,\nContact Owner: @DTXZAHID"
    )

# ---------- ADMIN PANEL ----------
@dp.message(Command("admin"))
async def admin(msg: Message):
    if msg.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect("bot.db") as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total = (await cur.fetchone())[0]

    await msg.answer(f"👑 Admin Panel\n👥 Total Users: {total}")

# ---------- RUN ----------
async def main():
    await dp.start_polling(bot)

asyncio.run(main())
