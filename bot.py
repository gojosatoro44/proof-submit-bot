import os, json
import threading
from telegram import (
    Update, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from datetime import datetime
import logging

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
FORCE_JOIN_CHANNEL = "@TaskByZahid"

# ✅ Use persistent volume on Railway
PERSISTENT_DATA_DIR = "/data" if os.path.exists("/data") else "data"
os.makedirs(PERSISTENT_DATA_DIR, exist_ok=True)

# JSON files in persistent storage
USERS_FILE = os.path.join(PERSISTENT_DATA_DIR, "users.json")
VERIFIED_FILE = os.path.join(PERSISTENT_DATA_DIR, "verified.json")
WITHDRAWALS_FILE = os.path.join(PERSISTENT_DATA_DIR, "withdrawals.json")

# Thread lock for file operations
file_lock = threading.Lock()

# ================= STATES =================
SUBMIT_PROOF, WITHDRAW_METHOD, WITHDRAW_DETAIL, WITHDRAW_AMOUNT = range(4)

# ================= LOGGING =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= FILE OPERATIONS =================
def load_json(file_path, default={}):
    """Load JSON file safely"""
    with file_lock:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
        
        # Return default and save it
        with open(file_path, 'w') as f:
            json.dump(default, f, indent=2)
        return default

def save_json(file_path, data):
    """Save JSON file safely"""
    with file_lock:
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
            return False

# ================= UTILS =================
def menu():
    return ReplyKeyboardMarkup(
        [["📤 Submit Proof"],
         ["💰 Balance", "💸 Withdraw"],
         ["🆘 Support"]],
        resize_keyboard=True
    )

async def force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if user has joined the channel"""
    try:
        chat_member = await context.bot.get_chat_member(
            FORCE_JOIN_CHANNEL, 
            update.effective_user.id
        )
        return chat_member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        return False

def is_admin(user_id):
    """Check if user is admin"""
    return user_id == ADMIN_ID

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clear any existing conversation data
    if context.user_data:
        context.user_data.clear()
    
    if not await force_join(update, context):
        btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton(
                "✅ Join Channel", 
                url=f"https://t.me/{FORCE_JOIN_CHANNEL[1:]}"
            )],
             [InlineKeyboardButton(
                "✅ I've Joined", 
                callback_data="check_join"
             )]]
        )
        await update.message.reply_text(
            "🚫 You must join our channel to use this bot.\n\n"
            "1. Click '✅ Join Channel' below\n"
            "2. After joining, click '✅ I've Joined'\n"
            "3. Then use /start again",
            reply_markup=btn
        )
        return

    users = load_json(USERS_FILE, {})
    uid = str(update.effective_user.id)
    
    if uid not in users:
        users[uid] = {
            "balance": 0.0,
            "proofs": 0,
            "name": update.effective_user.full_name,
            "username": update.effective_user.username,
            "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        users[uid]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    save_json(USERS_FILE, users)
    
    await update.message.reply_text(
        f"👋 Welcome to Task Bot, {update.effective_user.first_name}!\n\n"
        "📤 Submit your referral link to earn money!\n"
        "💰 Withdraw when you reach ₹5 balance.",
        reply_markup=menu()
    )

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback for join verification button"""
    query = update.callback_query
    await query.answer()
    
    if not await force_join(update, context):
        await query.edit_message_text(
            "❌ I still can't see you in the channel. "
            "Please make sure you've joined and try again."
        )
        return
    
    await query.edit_message_text(
        "✅ Great! You've joined the channel. Now use /start to begin."
    )

# ================= BALANCE =================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user has joined channel
    if not await force_join(update, context):
        await update.message.reply_text("❌ Please join our channel first using /start")
        return
    
    users = load_json(USERS_FILE, {})
    uid = str(update.effective_user.id)
    
    if uid not in users:
        await update.message.reply_text("❌ User not found. Please use /start first")
        return
    
    user = users[uid]
    await update.message.reply_text(
        f"💰 Your Balance: ₹{user['balance']:.2f}\n"
        f"📊 Proofs Submitted: {user['proofs']}\n"
        f"📅 Last Active: {user.get('last_active', 'N/A')}"
    )

# ================= SUPPORT =================
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 Need help?\nContact owner: @DTXZAHID"
    )

# ================= SUBMIT PROOF (ONLY REFERRAL LINK) =================
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user has joined channel
    if not await force_join(update, context):
        await update.message.reply_text("❌ Please join our channel first using /start")
        return ConversationHandler.END
    
    # Clear previous conversation data
    context.user_data.clear()
    
    await update.message.reply_text(
        "🔗 **Send your referral link:**\n\n"
        "• Must be the exact link from the task\n"
        "• Should contain your referral ID\n"
        "• Must start with http:// or https://\n\n"
        "Example: https://example.com/ref=YOUR_ID\n\n"
        "❌ **Reasons for rejection:**\n"
        "• Invalid or fake link\n"
        "• Already used link\n"
        "• Link doesn't contain valid referral ID"
    )
    return SUBMIT_PROOF

async def process_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process referral link only (no screenshot)"""
    link = update.message.text.strip()
    user_id = str(update.effective_user.id)
    
    # Basic URL validation
    if not link.startswith(('http://', 'https://')):
        await update.message.reply_text(
            "❌ Please send a valid URL starting with http:// or https://"
        )
        return SUBMIT_PROOF
    
    # Load data
    users = load_json(USERS_FILE, {})
    verified = load_json(VERIFIED_FILE, {})
    
    # Initialize user if not exists
    if user_id not in users:
        users[user_id] = {
            "balance": 0.0,
            "proofs": 0,
            "name": update.effective_user.full_name,
            "username": update.effective_user.username,
            "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    status = "REJECTED"
    amount = 0
    verified_id = None
    
    # Check against verified IDs
    for vid, amt in verified.items():
        if vid.lower() in link.lower():
            status = "VERIFIED"
            verified_id = vid
            amount = float(amt)
            
            # Add to user balance if amount > 0
            if amount > 0:
                users[user_id]["balance"] += amount
            
            users[user_id]["proofs"] += 1
            users[user_id]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Remove used verified ID
            del verified[vid]
            break
    
    # Save updated data
    save_json(USERS_FILE, users)
    save_json(VERIFIED_FILE, verified)
    
    # Send notification to admin
    user_name = users[user_id].get("name", "Unknown")
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"📥 New Proof Submission\n\n"
            f"👤 User: {user_name}\n"
            f"🆔 ID: {user_id}\n"
            f"✅ Status: {status}\n"
            f"💰 Amount: ₹{amount:.2f}\n"
            f"🔗 Link: {link[:100]}...\n"
            f"{f'🎯 Verified ID: {verified_id}' if verified_id else ''}\n"
            f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    except Exception as e:
        logger.error(f"Error sending to admin: {e}")
    
    # Respond to user
    if status == "VERIFIED":
        if amount > 0:
            msg = f"✅ Proof verified!\n💰 ₹{amount:.2f} added to your balance.\n📊 New Balance: ₹{users[user_id]['balance']:.2f}"
        else:
            msg = "✅ Proof verified!\n💰 Payment will be added within 5-10 minutes."
    else:
        msg = "❌ Proof rejected!\nPossible reasons: Invalid link, already used, or no matching referral ID."
    
    await update.message.reply_text(msg, reply_markup=menu())
    return ConversationHandler.END

# ================= WITHDRAW =================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user has joined channel
    if not await force_join(update, context):
        await update.message.reply_text("❌ Please join our channel first using /start")
        return ConversationHandler.END
    
    # Check user balance
    users = load_json(USERS_FILE, {})
    uid = str(update.effective_user.id)
    
    if uid not in users or users[uid]["balance"] <= 0:
        await update.message.reply_text("❌ Insufficient balance to withdraw")
        return ConversationHandler.END
    
    # Clear previous data
    context.user_data.clear()
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("UPI (Min ₹5)", callback_data="upi"),
         InlineKeyboardButton("VSV (Min ₹2)", callback_data="vsv")],
        [InlineKeyboardButton("FXL (Min ₹2)", callback_data="fxl")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
    
    await update.message.reply_text(
        f"💸 Choose withdrawal method\n\n"
        f"Your balance: ₹{users[uid]['balance']:.2f}\n"
        f"Minimum withdrawal:\n"
        f"• UPI: ₹5\n"
        f"• VSV/FXL: ₹2",
        reply_markup=kb
    )
    return WITHDRAW_METHOD

async def withdraw_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.message.reply_text("❌ Withdrawal cancelled", reply_markup=menu())
        return ConversationHandler.END
    
    context.user_data["method"] = query.data.upper()
    
    if query.data == "upi":
        await query.message.edit_text("Send your UPI ID (e.g., username@upi):")
    else:
        await query.message.edit_text(f"Send your {context.user_data['method']} registered number:")
    
    return WITHDRAW_DETAIL

async def withdraw_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    detail = update.message.text.strip()
    
    if len(detail) < 3:
        await update.message.reply_text("❌ Please provide valid details")
        return WITHDRAW_DETAIL
    
    if context.user_data["method"] == "UPI" and '@' not in detail:
        await update.message.reply_text("❌ Invalid UPI ID. Format: username@upi")
        return WITHDRAW_DETAIL
    
    context.user_data["detail"] = detail
    
    min_amt = 5 if context.user_data["method"] == "UPI" else 2
    users = load_json(USERS_FILE, {})
    uid = str(update.effective_user.id)
    
    await update.message.reply_text(
        f"Enter amount (Minimum ₹{min_amt})\n"
        f"Your current balance: ₹{users.get(uid, {}).get('balance', 0):.2f}"
    )
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amt_text = update.message.text.strip()
    
    # Validate amount
    try:
        amount = float(amt_text)
        if amount <= 0:
            raise ValueError
    except:
        await update.message.reply_text("❌ Please enter a valid positive number")
        return WITHDRAW_AMOUNT
    
    method = context.user_data["method"]
    min_amt = 5.0 if method == "UPI" else 2.0
    
    users = load_json(USERS_FILE, {})
    uid = str(update.effective_user.id)
    
    # Check balance
    user_bal = users.get(uid, {}).get("balance", 0)
    
    if amount < min_amt:
        await update.message.reply_text(f"❌ Minimum withdrawal is ₹{min_amt:.2f}")
        return ConversationHandler.END
    
    if amount > user_bal:
        await update.message.reply_text(f"❌ Insufficient balance. You have ₹{user_bal:.2f}")
        return ConversationHandler.END
    
    # Deduct balance
    users[uid]["balance"] -= amount
    save_json(USERS_FILE, users)
    
    # Load withdrawals
    withdrawals = load_json(WITHDRAWALS_FILE, [])
    
    # Create withdrawal record
    withdrawal_id = len(withdrawals) + 1
    withdrawal_record = {
        "id": withdrawal_id,
        "user_id": uid,
        "amount": amount,
        "method": method,
        "details": context.user_data["detail"],
        "status": "pending",
        "request_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_name": users[uid].get("name", "Unknown")
    }
    
    withdrawals.append(withdrawal_record)
    save_json(WITHDRAWALS_FILE, withdrawals)
    
    # Send to admin
    user_info = users[uid]
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"done:{withdrawal_id}:{uid}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"rej:{withdrawal_id}:{uid}")]
    ])
    
    try:
        await context.bot.send_message(
            ADMIN_ID,
            f"💸 New Withdrawal Request\n\n"
            f"🆔 Request ID: {withdrawal_id}\n"
            f"👤 User: {user_info.get('name', 'Unknown')}\n"
            f"🆔 User ID: {uid}\n"
            f"💰 Amount: ₹{amount:.2f}\n"
            f"📋 Method: {method}\n"
            f"🔧 Details: {context.user_data['detail']}\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=kb
        )
    except Exception as e:
        logger.error(f"Error sending to admin: {e}")
        # Refund if failed to notify admin
        users[uid]["balance"] += amount
        save_json(USERS_FILE, users)
        await update.message.reply_text("❌ Error processing request. Please try again.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"✅ Withdrawal request sent!\n\n"
        f"• Amount: ₹{amount:.2f}\n"
        f"• Method: {method}\n"
        f"• To: {context.user_data['detail']}\n"
        f"• Request ID: {withdrawal_id}\n\n"
        f"Processing time: 24-48 hours\n"
        f"You'll be notified when processed.",
        reply_markup=menu()
    )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def withdraw_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin withdrawal actions"""
    query = update.callback_query
    await query.answer()
    
    # Check if admin
    if not is_admin(query.from_user.id):
        await query.message.reply_text("❌ Admin only")
        return
    
    data_parts = query.data.split(':')
    action = data_parts[0]
    withdrawal_id = int(data_parts[1])
    user_id = data_parts[2]
    
    # Load withdrawals and users
    withdrawals = load_json(WITHDRAWALS_FILE, [])
    users = load_json(USERS_FILE, {})
    
    # Find withdrawal
    withdrawal = None
    for w in withdrawals:
        if w["id"] == withdrawal_id:
            withdrawal = w
            break
    
    if not withdrawal:
        await query.edit_message_text("❌ Withdrawal not found")
        return
    
    amount = withdrawal["amount"]
    
    if action == "done":
        # Withdrawal approved - update status
        for w in withdrawals:
            if w["id"] == withdrawal_id:
                w["status"] = "approved"
                w["processed_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        
        save_json(WITHDRAWALS_FILE, withdrawals)
        
        await context.bot.send_message(
            int(user_id),
            f"✅ Withdrawal Approved!\n\n"
            f"💰 Amount: ₹{amount:.2f}\n"
            f"🆔 Request ID: {withdrawal_id}\n"
            f"✅ Status: Approved\n\n"
            f"💸 Funds will be transferred within 24 hours."
        )
        await query.edit_message_text(f"✅ Withdrawal #{withdrawal_id} approved")
        
    elif action == "rej":
        # Withdrawal rejected - refund balance
        for w in withdrawals:
            if w["id"] == withdrawal_id:
                w["status"] = "rejected"
                w["processed_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        
        save_json(WITHDRAWALS_FILE, withdrawals)
        
        # Refund balance
        if user_id in users:
            users[user_id]["balance"] += amount
            save_json(USERS_FILE, users)
        
        await context.bot.send_message(
            int(user_id),
            f"❌ Withdrawal Rejected\n\n"
            f"💰 Amount: ₹{amount:.2f} (Refunded)\n"
            f"🆔 Request ID: {withdrawal_id}\n"
            f"❌ Status: Rejected\n\n"
            f"⚠️ Possible reasons:\n"
            f"• Invalid payment details\n"
            f"• System verification failed\n\n"
            f"🆘 Contact @DTXZAHID for assistance"
        )
        await query.edit_message_text(f"❌ Withdrawal #{withdrawal_id} rejected")

# ================= ADMIN COMMANDS =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    
    users = load_json(USERS_FILE, {})
    verified = load_json(VERIFIED_FILE, {})
    withdrawals = load_json(WITHDRAWALS_FILE, [])
    
    total_balance = sum(user.get("balance", 0) for user in users.values())
    pending_withdrawals = sum(1 for w in withdrawals if w.get("status") == "pending")
    
    kb = ReplyKeyboardMarkup(
        [["➕ Add Balance", "➖ Remove Balance"],
         ["📋 Add Verified ID", "👥 Total Users"],
         ["📊 Stats", "🏠 Main Menu"]],
        resize_keyboard=True
    )
    
    stats_msg = (
        f"⚙ Admin Panel\n\n"
        f"📊 Statistics:\n"
        f"• 👥 Total Users: {len(users)}\n"
        f"• 💰 Total Balance: ₹{total_balance:.2f}\n"
        f"• 💸 Pending Withdrawals: {pending_withdrawals}\n"
        f"• ✅ Verified IDs: {len(verified)}"
    )
    
    await update.message.reply_text(stats_msg, reply_markup=kb)

async def add_verified(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add verified ID"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    
    await update.message.reply_text(
        "Send Verified ID and Amount:\n"
        "Format: verified_id amount\n"
        "Example: REF123 10.50"
    )
    # This would be part of a conversation handler if you want it

async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    
    users = load_json(USERS_FILE, {})
    active_users = sum(1 for u in users.values() 
                      if datetime.now().timestamp() - datetime.strptime(
                          u.get("last_active", "2000-01-01"), 
                          "%Y-%m-%d %H:%M:%S"
                      ).timestamp() < 7*24*3600)  # Active in last 7 days
    
    await update.message.reply_text(
        f"👥 Total Users: {len(users)}\n"
        f"📈 Active Users (7 days): {active_users}"
    )

# ================= CANCEL =================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any conversation"""
    await update.message.reply_text(
        "Operation cancelled.",
        reply_markup=menu()
    )
    if context.user_data:
        context.user_data.clear()
    return ConversationHandler.END

# ================= MAIN =================
def main():
    # Create persistent directory
    if not os.path.exists(PERSISTENT_DATA_DIR):
        os.makedirs(PERSISTENT_DATA_DIR, exist_ok=True)
        logger.info(f"Created persistent directory: {PERSISTENT_DATA_DIR}")
    
    # Initialize JSON files
    load_json(USERS_FILE, {})
    load_json(VERIFIED_FILE, {})
    load_json(WITHDRAWALS_FILE, [])
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Callback query handlers
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(withdraw_action, pattern="^(done|rej):"))
    
    # Menu handlers
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(MessageHandler(filters.Regex("^👥 Total Users$"), total_users))
    app.add_handler(MessageHandler(filters.Regex("^📊 Stats$"), admin))
    app.add_handler(MessageHandler(filters.Regex("^🏠 Main Menu$"), start))
    
    # Submit Proof Conversation (ONLY REFERRAL LINK)
    proof_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={
            SUBMIT_PROOF: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_proof)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Withdraw Conversation
    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw)],
        states={
            WITHDRAW_METHOD: [CallbackQueryHandler(withdraw_method)],
            WITHDRAW_DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_detail)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(proof_conv)
    app.add_handler(withdraw_conv)
    
    # Start polling
    logger.info("🤖 Bot is running with PERSISTENT JSON STORAGE...")
    logger.info(f"Persistent data directory: {PERSISTENT_DATA_DIR}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
