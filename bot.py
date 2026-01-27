import os, json
import threading
import re
from telegram import (
    Update, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
FORCE_JOIN_CHANNEL = "@TaskByZahid"

DATA = "data"
USERS = f"{DATA}/users.json"
VERIFIED = f"{DATA}/verified.json"
AUTO_AMOUNT = f"{DATA}/auto_amount.json"
os.makedirs(DATA, exist_ok=True)

# Thread lock for file operations
file_lock = threading.Lock()

# ================= STATES =================
(
    PROOF_LINK,
    WD_METHOD, WD_DETAIL, WD_AMOUNT,
    ADD_BAL_USER, ADD_BAL_AMOUNT,
    REM_BAL_USER, REM_BAL_AMOUNT,
    ADD_VER_IDS, AUTO_AMOUNT_INPUT
) = range(10)

# ================= UTILS =================
def load(p, d):
    with file_lock:
        if not os.path.exists(p):
            with open(p, "w") as f: 
                json.dump(d, f)
        with open(p) as f: 
            return json.load(f)

def save(p, d):
    with file_lock:
        with open(p, "w") as f: 
            json.dump(d, f, indent=2)

def menu():
    return ReplyKeyboardMarkup(
        [["📤 Submit Proof"],
         ["💰 Balance", "💸 Withdraw"],
         ["🆘 Support"]],
        resize_keyboard=True
    )

def admin_menu():
    return ReplyKeyboardMarkup(
        [["➕ Add Balance", "➖ Remove Balance"],
         ["📋 Add Verified IDs", "🤖 Set Auto Amount"],
         ["👥 Total Users", "📊 User Details"],
         ["🏠 Main Menu"]],
        resize_keyboard=True
    )

async def force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_member = await context.bot.get_chat_member(
            FORCE_JOIN_CHANNEL, 
            update.effective_user.id
        )
        return chat_member.status in ("member", "administrator", "creator")
    except:
        return False

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_valid_url(url):
    """
    Check if the input is a valid URL.
    Supports http, https, and common app referral links.
    """
    url = url.strip()
    
    # Common URL patterns
    url_patterns = [
        r'^https?://',  # http:// or https://
        r'^www\.',      # www.domain.com
        r'^[a-zA-Z0-9]+://',  # protocol://
    ]
    
    # Check if it matches any URL pattern
    for pattern in url_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    
    # Check for common referral link patterns
    referral_patterns = [
        r'^[a-zA-Z0-9]{8,}$',  # Short codes (at least 8 chars)
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',  # Email format
        r'^[a-zA-Z0-9]+=[a-zA-Z0-9]+',  # key=value format
        r'^ref/[a-zA-Z0-9]+',  # ref/CODE format
        r'^invite/[a-zA-Z0-9]+',  # invite/CODE format
        r'^[a-zA-Z0-9]{5,}/[a-zA-Z0-9]{5,}',  # code1/code2 format
    ]
    
    for pattern in referral_patterns:
        if re.fullmatch(pattern, url, re.IGNORECASE):
            return True
    
    # Check if it contains common domain words (for user-friendly messages)
    domain_words = ['.com', '.in', '.org', '.net', '.co', '.io', '.me', '.app']
    for word in domain_words:
        if word in url.lower():
            return True
    
    return False

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join(update, context):
        btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Join Channel", url=f"https://t.me/{FORCE_JOIN_CHANNEL[1:]}")],
             [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")]]
        )
        await update.message.reply_text(
            "🚫 Join our channel first to use this bot!",
            reply_markup=btn
        )
        return

    users = load(USERS, {})
    uid = str(update.effective_user.id)
    if uid not in users:
        users[uid] = {
            "balance": 0, 
            "proofs": 0, 
            "name": update.effective_user.full_name,
            "username": update.effective_user.username
        }
    save(USERS, users)

    await update.message.reply_text(
        f"👋 Welcome {update.effective_user.first_name}!\n"
        "✅ You can now submit proofs and withdraw earnings.",
        reply_markup=menu()
    )

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not await force_join(update, context):
        await query.edit_message_text("❌ Still not in channel. Join and try /start")
        return
    
    await query.edit_message_text("✅ Join verified! Use /start to begin.")

# ================= BALANCE =================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join(update, context):
        await update.message.reply_text("❌ Join channel first using /start")
        return
    
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    
    if uid not in users:
        await update.message.reply_text("❌ User not found. Use /start")
        return
    
    bal = users[uid]["balance"]
    proofs = users[uid]["proofs"]
    await update.message.reply_text(
        f"💰 Balance: ₹{bal}\n"
        f"📊 Proofs Submitted: {proofs}"
    )

# ================= SUPPORT =================
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🆘 Support: @DTXZAHID")

# ================= SUBMIT PROOF =================
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join(update, context):
        await update.message.reply_text("❌ Join channel first using /start")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Bro Send Your Refer Link/Bhai Apna Refer Link Bhejo!\n"
        "\n"
        "[Example:-https://t.me/Abc?start=123456789]"
    )
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    uid = str(update.effective_user.id)
    
    # Validate the link
    if not is_valid_url(link):
        await update.message.reply_text(
            "❌ Invalid link format!\n\n"
            "Please send a valid referral link.\n"
            "Example: https://t.me/Abc?start=123456789"
        )
        return PROOF_LINK
    
    # Load all data
    verified = load(VERIFIED, [])
    users = load(USERS, {})
    auto_amount = load(AUTO_AMOUNT, {"amount": 0})
    
    # Initialize user if not exists
    if uid not in users:
        users[uid] = {
            "balance": 0, 
            "proofs": 0, 
            "name": update.effective_user.full_name,
            "username": update.effective_user.username
        }
    
    status = "REJECTED"
    added = 0
    used_verified_id = None
    
    # Check if link contains any verified ID
    for vid in verified:
        if str(vid) in link:
            status = "VERIFIED"
            used_verified_id = vid
            
            # Use auto amount if set
            if auto_amount["amount"] > 0:
                added = auto_amount["amount"]
            
            # Add to user's balance
            users[uid]["balance"] += added
            users[uid]["proofs"] += 1
            
            # Remove used verified ID from list
            if vid in verified:
                verified.remove(vid)
            break
    
    save(USERS, users)
    save(VERIFIED, verified)
    
    # Send to admin
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"📥 New Proof\n"
            f"👤 {users[uid]['name']}\n"
            f"🆔 {uid}\n"
            f"✅ {status}\n"
            f"💰 +₹{added}\n"
            f"🔗 {link[:100]}{'...' if len(link) > 100 else ''}"
        )
    except:
        pass
    
    # Respond to user
    if status == "VERIFIED":
        if added > 0:
            msg = f"✅ Proof verified!\n💰 ₹{added} added to balance."
        else:
            msg = "✅ Proof verified! No auto amount set."
    else:
        msg = "❌ Proof rejected! (Invalid/Fake/Used link)"
    
    await update.message.reply_text(msg, reply_markup=menu())
    return ConversationHandler.END

# ================= WITHDRAW =================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join(update, context):
        await update.message.reply_text("❌ Join channel first using /start")
        return ConversationHandler.END
    
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    
    if uid not in users or users[uid]["balance"] <= 0:
        await update.message.reply_text("❌ Insufficient balance")
        return ConversationHandler.END
    
    context.user_data.clear()
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("VSV (Wallet)", callback_data="vsv"),
         InlineKeyboardButton("FXL", callback_data="fxl")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
    
    await update.message.reply_text(
        f"💸 Withdraw Method\n\n"
        f"💰 Balance: ₹{users[uid]['balance']}\n"
        f"📋 Minimum:\n• VSV (Wallet): ₹2\n• FXL: ₹5",
        reply_markup=kb
    )
    return WD_METHOD

async def wd_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.message.reply_text("❌ Cancelled", reply_markup=menu())
        return ConversationHandler.END
    
    context.user_data["method"] = query.data.upper()
    method_name = "VSV (Wallet) number" if query.data == "vsv" else "FXL details"
    
    await query.message.edit_text(f"Send your {method_name}:")
    return WD_DETAIL

async def wd_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["detail"] = update.message.text.strip()
    
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    bal = users[uid]["balance"]
    
    await update.message.reply_text(
        f"Enter amount to withdraw\n\n"
        f"💰 Available: ₹{bal}\n"
        f"📋 Minimum: ₹{'2' if context.user_data['method'] == 'VSV' else '5'}"
    )
    return WD_AMOUNT

async def wd_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text)
    except:
        await update.message.reply_text("❌ Enter valid amount")
        return WD_AMOUNT
    
    method = context.user_data["method"]
    min_amt = 2.0 if method == "VSV" else 5.0
    
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    
    if uid not in users:
        await update.message.reply_text("❌ User not found")
        return ConversationHandler.END
    
    if amt < min_amt:
        await update.message.reply_text(f"❌ Minimum is ₹{min_amt}")
        return ConversationHandler.END
    
    if amt > users[uid]["balance"]:
        await update.message.reply_text("❌ Insufficient balance")
        return ConversationHandler.END
    
    # Deduct balance
    users[uid]["balance"] -= amt
    save(USERS, users)
    
    # Send to admin
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"done:{uid}:{amt}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"rej:{uid}:{amt}")]
    ])
    
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"💸 Withdraw Request\n"
            f"👤 {users[uid]['name']}\n"
            f"🆔 {uid}\n"
            f"💰 ₹{amt}\n"
            f"📋 {method}\n"
            f"🔧 {context.user_data['detail']}",
            reply_markup=kb
        )
    except:
        # Refund if failed
        users[uid]["balance"] += amt
        save(USERS, users)
        await update.message.reply_text("❌ Error. Try again.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"✅ Request sent!\n\n"
        f"• Amount: ₹{amt}\n"
        f"• Method: {method}\n\n"
        f"Processing time: 24-48 hours",
        reply_markup=menu()
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def wd_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        return
    
    parts = query.data.split(':')
    action = parts[0]
    uid = parts[1]
    amount = float(parts[2])
    
    if action == "done":
        msg = f"✅ Withdrawal processed!\n💰 ₹{amount} sent."
        await query.edit_message_text(f"✅ Approved for {uid}")
    else:
        # Refund balance
        users = load(USERS, {})
        if uid in users:
            users[uid]["balance"] += amount
            save(USERS, users)
        msg = f"❌ Withdrawal rejected\n💰 ₹{amount} refunded."
        await query.edit_message_text(f"❌ Rejected for {uid}")
    
    try:
        await context.bot.send_message(int(uid), msg)
    except:
        pass

# ================= ADMIN COMMANDS =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    
    await update.message.reply_text("⚙ Admin Panel", reply_markup=admin_menu())

# ================= ADD BALANCE =================
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    await update.message.reply_text("Send user ID to add balance:")
    return ADD_BAL_USER

async def add_bal_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.text.strip()
    users = load(USERS, {})
    
    if uid not in users:
        await update.message.reply_text("❌ User not found")
        return ConversationHandler.END
    
    context.user_data["add_user"] = uid
    await update.message.reply_text(f"User: {users[uid].get('name', 'Unknown')}\n\nEnter amount to add:")
    return ADD_BAL_AMOUNT

async def add_bal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
    except:
        await update.message.reply_text("❌ Invalid amount")
        return ADD_BAL_AMOUNT
    
    uid = context.user_data["add_user"]
    users = load(USERS, {})
    
    if uid in users:
        users[uid]["balance"] += amount
        save(USERS, users)
        
        try:
            await update.get_bot().send_message(
                int(uid),
                f"💰 Balance updated!\n"
                f"✅ ₹{amount} added to your account.\n"
                f"New balance: ₹{users[uid]['balance']}"
            )
        except:
            pass
        
        await update.message.reply_text(
            f"✅ ₹{amount} added to {uid}\n"
            f"New balance: ₹{users[uid]['balance']}",
            reply_markup=admin_menu()
        )
    else:
        await update.message.reply_text("❌ User not found")
    
    context.user_data.clear()
    return ConversationHandler.END

# ================= REMOVE BALANCE =================
async def remove_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    await update.message.reply_text("Send user ID to remove balance:")
    return REM_BAL_USER

async def rem_bal_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.text.strip()
    users = load(USERS, {})
    
    if uid not in users:
        await update.message.reply_text("❌ User not found")
        return ConversationHandler.END
    
    context.user_data["rem_user"] = uid
    await update.message.reply_text(
        f"User: {users[uid].get('name', 'Unknown')}\n"
        f"Balance: ₹{users[uid]['balance']}\n\n"
        f"Enter amount to remove:"
    )
    return REM_BAL_AMOUNT

async def rem_bal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
    except:
        await update.message.reply_text("❌ Invalid amount")
        return REM_BAL_AMOUNT
    
    uid = context.user_data["rem_user"]
    users = load(USERS, {})
    
    if uid in users:
        if amount > users[uid]["balance"]:
            users[uid]["balance"] = 0
        else:
            users[uid]["balance"] -= amount
        
        save(USERS, users)
        
        try:
            await update.get_bot().send_message(
                int(uid),
                f"⚠️ Balance updated!\n"
                f"❌ ₹{amount} removed from your account.\n"
                f"New balance: ₹{users[uid]['balance']}"
            )
        except:
            pass
        
        await update.message.reply_text(
            f"✅ ₹{amount} removed from {uid}\n"
            f"New balance: ₹{users[uid]['balance']}",
            reply_markup=admin_menu()
        )
    else:
        await update.message.reply_text("❌ User not found")
    
    context.user_data.clear()
    return ConversationHandler.END

# ================= ADD VERIFIED IDs =================
async def add_verified_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    await update.message.reply_text(
        "📋 Send user IDs (one per line) in this format:\n\n"
        "6274638384 Got Invited By Your Url: +3 Rs\n"
        "1234567890 Got Invited By Your Url: +5 Rs\n"
        "9876543210 Got Invited By Your Url: +10 Rs\n\n"
        "I'll extract only the user IDs (6274638384, 1234567890, 9876543210)"
    )
    return ADD_VER_IDS

async def add_ver_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = text.split('\n')
    
    verified = load(VERIFIED, [])
    added_count = 0
    
    for line in lines:
        line = line.strip()
        # Extract only the user ID from the beginning of the line
        # Example: "6274638384 Got Invited By Your Url: +3 Rs" → "6274638384"
        
        # Take first word if it's all digits
        words = line.split()
        if words and words[0].isdigit():
            user_id = words[0]
            if user_id not in verified:
                verified.append(user_id)
                added_count += 1
    
    save(VERIFIED, verified)
    
    await update.message.reply_text(
        f"✅ {added_count} ID(s) added to verified list!\n"
        f"Total verified IDs: {len(verified)}",
        reply_markup=admin_menu()
    )
    return ConversationHandler.END

# ================= SET AUTO AMOUNT =================
async def set_auto_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    auto_amount = load(AUTO_AMOUNT, {"amount": 0})
    current = auto_amount["amount"]
    
    await update.message.reply_text(
        f"🤖 Set Auto Amount for Verified IDs\n\n"
        f"Current amount: ₹{current}\n"
        f"When users submit proof with verified IDs, they get this amount.\n\n"
        f"Enter amount (0 to disable):"
    )
    return AUTO_AMOUNT_INPUT

async def auto_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
    except:
        await update.message.reply_text("❌ Invalid amount")
        return AUTO_AMOUNT_INPUT
    
    auto_amount = {"amount": amount}
    save(AUTO_AMOUNT, auto_amount)
    
    if amount > 0:
        msg = f"✅ Auto amount set to ₹{amount}!\nAll verified proofs will get ₹{amount}."
    else:
        msg = "✅ Auto amount disabled!"
    
    await update.message.reply_text(msg, reply_markup=admin_menu())
    return ConversationHandler.END

# ================= TOTAL USERS =================
async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    users = load(USERS, {})
    verified = load(VERIFIED, [])
    auto_amount = load(AUTO_AMOUNT, {"amount": 0})
    
    total_balance = sum(user["balance"] for user in users.values())
    total_proofs = sum(user["proofs"] for user in users.values())
    
    await update.message.reply_text(
        f"📊 Statistics:\n\n"
        f"👥 Total Users: {len(users)}\n"
        f"💰 Total Balance: ₹{total_balance}\n"
        f"📥 Total Proofs: {total_proofs}\n"
        f"✅ Verified IDs: {len(verified)}\n"
        f"🤖 Auto Amount: ₹{auto_amount['amount']}"
    )

# ================= USER DETAILS =================
async def user_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    users = load(USERS, {})
    if not users:
        await update.message.reply_text("❌ No users found")
        return
    
    # Show last 5 users
    user_list = list(users.items())[-5:]
    msg = "📋 Recent Users:\n\n"
    
    for uid, data in user_list:
        msg += (
            f"👤 {data.get('name', 'Unknown')}\n"
            f"🆔 {uid}\n"
            f"💰 Balance: ₹{data['balance']}\n"
            f"📊 Proofs: {data['proofs']}\n"
            f"━━━━━━━━━━━━━━\n"
        )
    
    await update.message.reply_text(msg)

# ================= CANCEL =================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled", reply_markup=menu())
    if context.user_data:
        context.user_data.clear()
    return ConversationHandler.END

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Basic commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Callback queries
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(wd_action, pattern="^(done|rej):"))
    
    # User menu
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    
    # Admin menu
    app.add_handler(MessageHandler(filters.Regex("^👥 Total Users$"), total_users))
    app.add_handler(MessageHandler(filters.Regex("^📊 User Details$"), user_details))
    app.add_handler(MessageHandler(filters.Regex("^🏠 Main Menu$"), start))
    
    # Submit Proof Conversation
    proof_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={
            PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_link)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Withdraw Conversation
    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw)],
        states={
            WD_METHOD: [CallbackQueryHandler(wd_method)],
            WD_DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, wd_detail)],
            WD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wd_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add Balance Conversation
    add_bal_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Add Balance$"), add_balance)],
        states={
            ADD_BAL_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_bal_user)],
            ADD_BAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_bal_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Remove Balance Conversation
    rem_bal_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➖ Remove Balance$"), remove_balance)],
        states={
            REM_BAL_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, rem_bal_user)],
            REM_BAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rem_bal_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add Verified IDs Conversation
    ver_ids_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Add Verified IDs$"), add_verified_ids)],
        states={
            ADD_VER_IDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ver_ids)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Set Auto Amount Conversation
    auto_amount_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🤖 Set Auto Amount$"), set_auto_amount)],
        states={
            AUTO_AMOUNT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, auto_amount_input)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add all conversation handlers
    app.add_handler(proof_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(add_bal_conv)
    app.add_handler(rem_bal_conv)
    app.add_handler(ver_ids_conv)
    app.add_handler(auto_amount_conv)
    
    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
