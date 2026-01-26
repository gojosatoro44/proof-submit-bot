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

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
FORCE_JOIN_CHANNEL = "@TaskByZahid"

DATA = "data"
USERS = f"{DATA}/users.json"
VERIFIED = f"{DATA}/verified.json"
TRANSACTIONS = f"{DATA}/transactions.json"
os.makedirs(DATA, exist_ok=True)

# Thread lock for file operations to prevent corruption
file_lock = threading.Lock()

# ================= STATES =================
(
    PROOF_LINK,
    WD_METHOD, WD_DETAIL, WD_AMOUNT,
    ADMIN_ADD_BAL, ADMIN_REM_BAL, ADD_VER, ADMIN_CHECK_USER
) = range(8)

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
         ["📋 Add Verified IDs", "🔍 Check User"],
         ["👥 Total Users", "📊 Verified IDs"],
         ["🏠 User Menu"]],
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
        print(f"Error checking channel membership: {e}")
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

    # Show appropriate menu based on user role
    if is_admin(update.effective_user.id):
        await update.message.reply_text(
            f"👋 Welcome Admin, {update.effective_user.first_name}!\n\n"
            "You have access to both user and admin features.",
            reply_markup=admin_menu()
        )
    else:
        await update.message.reply_text(
            f"👋 Welcome to Task Bot, {update.effective_user.first_name}!\n\n"
            "✅ You can now submit proofs and withdraw earnings.",
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
    
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    
    if uid not in users:
        await update.message.reply_text("❌ User not found. Please use /start first")
        return
    
    bal = users[uid]["balance"]
    proofs = users[uid]["proofs"]
    await update.message.reply_text(
        f"💰 Your Balance: ₹{bal}\n"
        f"📊 Total Proofs Submitted: {proofs}"
    )

# ================= SUPPORT =================
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 Need help?\nContact owner: @DTXZAHID\n\n"
        "For technical issues or payment queries, please DM the owner."
    )

# ================= SUBMIT PROOF =================
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start proof submission process - ONLY ASKS FOR LINK"""
    # Check if user has joined channel
    if not await force_join(update, context):
        await update.message.reply_text("❌ Please join our channel first using /start")
        return ConversationHandler.END
    
    # Clear previous conversation data
    context.user_data.clear()
    
    await update.message.reply_text(
        "🔗 Please send your referral link/proof link:\n\n"
        "⚠️ Make sure to send the exact referral link you used for the task.\n"
        "Example: https://example.com/ref=your_id"
    )
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the referral link"""
    link = update.message.text.strip()
    uid = str(update.effective_user.id)
    
    # Basic URL validation
    if not link.startswith(('http://', 'https://')):
        await update.message.reply_text(
            "❌ Please send a valid URL starting with http:// or https://"
        )
        return PROOF_LINK
    
    # Load data
    verified = load(VERIFIED, {})
    users = load(USERS, {})
    
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
    verified_id = None
    
    # Check against verified IDs
    for vid, amt in verified.items():
        if vid.lower() in link.lower():
            status = "VERIFIED"
            verified_id = vid
            if amt > 0:
                users[uid]["balance"] += amt
                added = amt
            users[uid]["proofs"] += 1
            # Remove used verified ID
            del verified[vid]
            break
    
    # Save updated data
    save(USERS, users)
    save(VERIFIED, verified)
    
    # Send to admin
    user_name = users[uid].get("name", "Unknown")
    user_username = users[uid].get("username", "")
    
    try:
        await context.bot.send_message(
            ADMIN_ID,
            text=(
                f"📥 New Proof Submission\n\n"
                f"👤 User: {user_name}\n"
                f"@{user_username}\n"
                f"🆔 ID: {uid}\n"
                f"✅ Status: {status}\n"
                f"💰 Amount: ₹{added}\n"
                f"🔗 Link: {link}\n"
                f"{f'🎯 Verified ID: {verified_id}' if verified_id else ''}\n\n"
                f"User Balance: ₹{users[uid]['balance']}\n"
                f"Total Proofs: {users[uid]['proofs']}"
            )
        )
    except Exception as e:
        print(f"Error sending to admin: {e}")
    
    # Clear user data
    context.user_data.clear()
    
    # Respond to user
    if status == "VERIFIED":
        if added > 0:
            msg = f"✅ Proof verified!\n💰 ₹{added} has been added to your balance."
        else:
            msg = "✅ Proof verified!\n💰 Payment will be added within 5–10 minutes."
    else:
        msg = (
            "❌ Proof rejected!\n\n"
            "Possible reasons:\n"
            "• Invalid referral link\n"
            "• Link already used\n"
            "• Not a verified referral ID\n"
            "• Same device used multiple times\n\n"
            "Contact support if you believe this is an error."
        )
    
    await update.message.reply_text(msg, reply_markup=menu())
    return ConversationHandler.END

# ================= WITHDRAW =================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start withdrawal process - FIRST show methods"""
    # Check if user has joined channel
    if not await force_join(update, context):
        await update.message.reply_text("❌ Please join our channel first using /start")
        return ConversationHandler.END
    
    # Clear previous data
    context.user_data.clear()
    
    # Get user balance
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    
    if uid not in users:
        await update.message.reply_text("❌ User not found. Please use /start first")
        return ConversationHandler.END
    
    user_bal = users[uid]["balance"]
    
    # Create buttons - ALWAYS show all options
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("UPI", callback_data="upi"),
         InlineKeyboardButton("VSV", callback_data="vsv"),
         InlineKeyboardButton("FXL", callback_data="fxl")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
    
    await update.message.reply_text(
        f"💸 Choose withdrawal method\n\n"
        f"💰 Your Balance: ₹{user_bal}\n\n"
        f"Minimum withdrawal amounts:\n"
        f"• UPI: ₹5\n"
        f"• VSV/FXL: ₹2\n\n"
        f"Select your preferred method:",
        reply_markup=kb
    )
    return WD_METHOD

async def wd_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal method selection with balance check"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.message.reply_text("❌ Withdrawal cancelled", reply_markup=menu())
        return ConversationHandler.END
    
    method = query.data.upper()
    context.user_data["method"] = method
    
    # Get user balance
    users = load(USERS, {})
    uid = str(query.from_user.id)
    
    if uid not in users:
        await query.message.reply_text("❌ User not found")
        return ConversationHandler.END
    
    user_bal = users[uid]["balance"]
    
    # Check minimum balance based on method
    min_amount = 5 if method == "UPI" else 2
    
    if user_bal < min_amount:
        await query.message.edit_text(
            f"❌ Not enough balance for {method} withdrawal\n\n"
            f"Your balance: ₹{user_bal}\n"
            f"Minimum required for {method}: ₹{min_amount}\n\n"
            f"Please submit more proofs to earn ₹{min_amount - user_bal} more!"
        )
        return ConversationHandler.END
    
    # If balance is sufficient, proceed
    method_names = {
        "UPI": "UPI ID (e.g., yourname@upi)",
        "VSV": "VSV registered mobile number",
        "FXL": "FXL registered mobile number"
    }
    
    await query.message.edit_text(
        f"✅ Selected: {method}\n\n"
        f"💰 Your Balance: ₹{user_bal}\n"
        f"📝 Minimum withdrawal: ₹{min_amount}\n\n"
        f"Please send your {method_names.get(method, 'details')}:"
    )
    return WD_DETAIL

async def wd_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get withdrawal details"""
    detail = update.message.text.strip()
    
    # Basic validation
    if len(detail) < 3:
        await update.message.reply_text("❌ Please provide valid details")
        return WD_DETAIL
    
    context.user_data["detail"] = detail
    
    # Get user balance
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    user_bal = users.get(uid, {}).get("balance", 0)
    
    method = context.user_data["method"]
    min_amount = 5 if method == "UPI" else 2
    
    await update.message.reply_text(
        f"✅ Details saved!\n\n"
        f"Method: {method}\n"
        f"Detail: {detail}\n\n"
        f"💰 Your Balance: ₹{user_bal}\n"
        f"📝 Minimum withdrawal: ₹{min_amount}\n\n"
        f"Enter withdrawal amount (₹{min_amount} - ₹{user_bal}):"
    )
    return WD_AMOUNT

async def wd_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process withdrawal amount"""
    amt_text = update.message.text.strip()
    
    # Validate amount
    if not amt_text.replace('.', '', 1).isdigit():
        await update.message.reply_text("❌ Please enter a valid number")
        return WD_AMOUNT
    
    amt = float(amt_text)
    method = context.user_data["method"]
    min_amt = 5.0 if method == "UPI" else 2.0
    
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    
    # Check balance
    user_bal = users.get(uid, {}).get("balance", 0)
    
    if amt < min_amt:
        await update.message.reply_text(f"❌ Minimum withdrawal is ₹{min_amt} for {method}")
        return WD_AMOUNT
    
    if amt > user_bal:
        await update.message.reply_text(
            f"❌ Insufficient balance!\n"
            f"You requested: ₹{amt}\n"
            f"Your balance: ₹{user_bal}\n"
            f"You need ₹{amt - user_bal} more."
        )
        return WD_AMOUNT
    
    # Deduct balance
    users[uid]["balance"] -= amt
    save(USERS, users)
    
    # Record transaction
    transactions = load(TRANSACTIONS, [])
    transactions.append({
        "user_id": uid,
        "type": "withdrawal",
        "amount": amt,
        "method": method,
        "detail": context.user_data["detail"],
        "status": "pending",
        "timestamp": update.message.date.isoformat()
    })
    save(TRANSACTIONS, transactions)
    
    # Send withdrawal request to admin
    user_info = users.get(uid, {})
    user_name = user_info.get("name", "Unknown")
    user_username = user_info.get("username", "")
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"done:{uid}:{amt}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"rej:{uid}:{amt}")]
    ])
    
    try:
        await update.get_bot().send_message(
            ADMIN_ID,
            f"💸 New Withdrawal Request\n\n"
            f"👤 User: {user_name}\n"
            f"@{user_username}\n"
            f"🆔 ID: {uid}\n"
            f"💰 Amount: ₹{amt}\n"
            f"📋 Method: {method}\n"
            f"🔧 Details: {context.user_data['detail']}\n"
            f"⏰ Time: {update.message.date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"User Balance: ₹{user_bal - amt}",
            reply_markup=kb
        )
    except Exception as e:
        print(f"Error sending to admin: {e}")
        # Refund if failed to notify admin
        users[uid]["balance"] += amt
        save(USERS, users)
        await update.message.reply_text("❌ Error processing request. Please try again.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"✅ Withdrawal request sent!\n\n"
        f"• Amount: ₹{amt}\n"
        f"• Method: {method}\n"
        f"• Details: {context.user_data['detail']}\n\n"
        f"⏳ Processing time: 24-48 hours\n"
        f"📩 You'll be notified when processed.",
        reply_markup=menu()
    )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def wd_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin withdrawal actions"""
    query = update.callback_query
    await query.answer()
    
    # Check if admin
    if not is_admin(query.from_user.id):
        await query.message.reply_text("❌ Admin only")
        return
    
    data_parts = query.data.split(':')
    action = data_parts[0]
    uid = data_parts[1]
    amount = float(data_parts[2]) if len(data_parts) > 2 else 0
    
    if action == "done":
        # Withdrawal approved
        await context.bot.send_message(
            int(uid),
            f"✅ Withdrawal Approved!\n\n"
            f"💰 ₹{amount} has been processed.\n"
            f"Thank you for using our service!"
        )
        await query.edit_message_text(f"✅ Withdrawal approved for user {uid}")
        
        # Update transaction status
        transactions = load(TRANSACTIONS, [])
        for tx in transactions:
            if tx.get("user_id") == uid and tx.get("status") == "pending" and tx.get("amount") == amount:
                tx["status"] = "approved"
                tx["approved_at"] = query.id
                break
        save(TRANSACTIONS, transactions)
        
    elif action == "rej":
        # Withdrawal rejected - refund balance
        users = load(USERS, {})
        if uid in users:
            users[uid]["balance"] += amount
            save(USERS, users)
        
        await context.bot.send_message(
            int(uid),
            f"❌ Withdrawal Rejected\n\n"
            f"💰 ₹{amount} has been refunded to your balance.\n"
            f"Reason: Invalid details or system issue\n\n"
            f"Contact support if you need help."
        )
        await query.edit_message_text(f"❌ Withdrawal rejected for user {uid}")
        
        # Update transaction status
        transactions = load(TRANSACTIONS, [])
        for tx in transactions:
            if tx.get("user_id") == uid and tx.get("status") == "pending" and tx.get("amount") == amount:
                tx["status"] = "rejected"
                tx["rejected_at"] = query.id
                break
        save(TRANSACTIONS, transactions)

# ================= ADMIN COMMANDS =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    
    await update.message.reply_text(
        "⚙ Admin Panel\n\n"
        "Select an option below:",
        reply_markup=admin_menu()
    )

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add balance to user"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "➕ Add Balance\n\n"
        "Send user ID and amount to add:\n"
        "Format: user_id amount\n\n"
        "Example: 123456789 100\n"
        "(This will add ₹100 to user 123456789)"
    )
    return ADMIN_ADD_BAL

async def admin_add_balance_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return ConversationHandler.END
    
    text = update.message.text.strip().split()
    if len(text) != 2:
        await update.message.reply_text("❌ Invalid format. Use: user_id amount")
        return ADMIN_ADD_BAL
    
    user_id, amount_str = text
    if not amount_str.replace('.', '', 1).isdigit():
        await update.message.reply_text("❌ Invalid amount. Use numbers only")
        return ADMIN_ADD_BAL
    
    amount = float(amount_str)
    
    users = load(USERS, {})
    if user_id not in users:
        await update.message.reply_text(f"❌ User {user_id} not found")
        return ConversationHandler.END
    
    users[user_id]["balance"] += amount
    save(USERS, users)
    
    # Record transaction
    transactions = load(TRANSACTIONS, [])
    transactions.append({
        "user_id": user_id,
        "type": "admin_add",
        "amount": amount,
        "admin": update.effective_user.id,
        "timestamp": update.message.date.isoformat()
    })
    save(TRANSACTIONS, transactions)
    
    await update.message.reply_text(
        f"✅ Added ₹{amount} to user {user_id}\n"
        f"New balance: ₹{users[user_id]['balance']}"
    )
    
    # Notify user
    try:
        await context.bot.send_message(
            int(user_id),
            f"💰 Balance Updated!\n\n"
            f"Admin added ₹{amount} to your account.\n"
            f"New balance: ₹{users[user_id]['balance']}"
        )
    except:
        pass
    
    return ConversationHandler.END

async def admin_remove_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove balance from user"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "➖ Remove Balance\n\n"
        "Send user ID and amount to remove:\n"
        "Format: user_id amount\n\n"
        "Example: 123456789 50\n"
        "(This will remove ₹50 from user 123456789)"
    )
    return ADMIN_REM_BAL

async def admin_remove_balance_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return ConversationHandler.END
    
    text = update.message.text.strip().split()
    if len(text) != 2:
        await update.message.reply_text("❌ Invalid format. Use: user_id amount")
        return ADMIN_REM_BAL
    
    user_id, amount_str = text
    if not amount_str.replace('.', '', 1).isdigit():
        await update.message.reply_text("❌ Invalid amount. Use numbers only")
        return ADMIN_REM_BAL
    
    amount = float(amount_str)
    
    users = load(USERS, {})
    if user_id not in users:
        await update.message.reply_text(f"❌ User {user_id} not found")
        return ConversationHandler.END
    
    if users[user_id]["balance"] < amount:
        await update.message.reply_text(
            f"❌ User has only ₹{users[user_id]['balance']}, cannot remove ₹{amount}"
        )
        return ConversationHandler.END
    
    users[user_id]["balance"] -= amount
    save(USERS, users)
    
    # Record transaction
    transactions = load(TRANSACTIONS, [])
    transactions.append({
        "user_id": user_id,
        "type": "admin_remove",
        "amount": amount,
        "admin": update.effective_user.id,
        "timestamp": update.message.date.isoformat()
    })
    save(TRANSACTIONS, transactions)
    
    await update.message.reply_text(
        f"✅ Removed ₹{amount} from user {user_id}\n"
        f"New balance: ₹{users[user_id]['balance']}"
    )
    
    # Notify user
    try:
        await context.bot.send_message(
            int(user_id),
            f"💰 Balance Updated!\n\n"
            f"Admin removed ₹{amount} from your account.\n"
            f"New balance: ₹{users[user_id]['balance']}"
        )
    except:
        pass
    
    return ConversationHandler.END

async def add_ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add verified IDs - MULTIPLE IDs AT ONCE"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📋 Add Verified IDs\n\n"
        "Send multiple verified IDs with amounts:\n\n"
        "📝 Format 1 (One per line):\n"
        "ID1 amount1\n"
        "ID2 amount2\n"
        "ID3 amount3\n\n"
        "📝 Format 2 (Comma separated):\n"
        "ID1 amount1, ID2 amount2, ID3 amount3\n\n"
        "📝 Format 3 (IDs only, amount 0):\n"
        "ID1, ID2, ID3\n\n"
        "📝 Format 4 (Single ID):\n"
        "ID1 amount\n\n"
        "📌 Examples:\n"
        "• REF123 50\n"
        "• ABC123 100, XYZ789 200, TEST456 0\n"
        "• ID1, ID2, ID3, ID4\n"
        "• SINGLE123 75\n\n"
        "Send your IDs now:"
    )
    return ADD_VER

async def add_ver_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return ConversationHandler.END
    
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ Please send some IDs")
        return ADD_VER
    
    v = load(VERIFIED, {})
    added_count = 0
    updated_count = 0
    
    # Try to parse different formats
    lines = text.split('\n')
    if len(lines) > 1:
        # Format 1: One per line
        for line in lines:
            parts = line.strip().split()
            if parts:
                vid = parts[0]
                amt = float(parts[1]) if len(parts) > 1 else 0
                if vid not in v:
                    added_count += 1
                else:
                    updated_count += 1
                v[vid] = amt
    else:
        # Try comma separated format
        entries = text.split(',')
        for entry in entries:
            entry = entry.strip()
            if entry:
                parts = entry.split()
                if parts:
                    vid = parts[0]
                    amt = float(parts[1]) if len(parts) > 1 else 0
                    if vid not in v:
                        added_count += 1
                    else:
                        updated_count += 1
                    v[vid] = amt
    
    save(VERIFIED, v)
    
    # Show summary
    total_with_amount = len([amt for amt in v.values() if amt > 0])
    
    await update.message.reply_text(
        f"✅ Verified IDs Updated!\n\n"
        f"📊 Statistics:\n"
        f"• New IDs added: {added_count}\n"
        f"• IDs updated: {updated_count}\n"
        f"• Total IDs now: {len(v)}\n"
        f"• IDs with amount (>0): {total_with_amount}\n\n"
        f"🎯 Recent additions (last 5):\n" +
        '\n'.join([f"• {list(v.keys())[-i-1]}: ₹{list(v.values())[-i-1]}" 
                  for i in range(min(5, len(v)))])
    )
    return ConversationHandler.END

async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check user details"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔍 Check User Details\n\n"
        "Send user ID to check details:\n\n"
        "Example: 123456789\n\n"
        "Or send 'all' to see all users\n"
        "Or send 'top' to see top 10 users by balance"
    )
    return ADMIN_CHECK_USER

async def check_user_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return ConversationHandler.END
    
    user_input = update.message.text.strip().lower()
    users = load(USERS, {})
    
    if user_input == "all":
        # Show all users summary
        total_users = len(users)
        total_balance = sum(user.get("balance", 0) for user in users.values())
        total_proofs = sum(user.get("proofs", 0) for user in users.values())
        
        message = (
            f"👥 All Users Summary\n\n"
            f"Total Users: {total_users}\n"
            f"Total Balance: ₹{total_balance}\n"
            f"Total Proofs: {total_proofs}\n\n"
        )
        
        if total_users > 0:
            # Calculate average
            avg_balance = total_balance / total_users
            avg_proofs = total_proofs / total_users
            message += f"📊 Averages:\n"
            message += f"• Balance per user: ₹{avg_balance:.2f}\n"
            message += f"• Proofs per user: {avg_proofs:.1f}\n\n"
        
        await update.message.reply_text(message[:4000])  # Telegram limit
        
    elif user_input == "top":
        # Show top 10 users by balance
        sorted_users = sorted(
            users.items(),
            key=lambda x: x[1].get("balance", 0),
            reverse=True
        )[:10]
        
        if not sorted_users:
            await update.message.reply_text("❌ No users found")
            return ConversationHandler.END
        
        message = "🏆 Top 10 Users by Balance:\n\n"
        for i, (uid, user_data) in enumerate(sorted_users, 1):
            name = user_data.get("name", "Unknown")[:15]
            username = f"@{user_data.get('username', '')}" if user_data.get('username') else "No username"
            balance = user_data.get("balance", 0)
            proofs = user_data.get("proofs", 0)
            message += f"{i}. {name} ({username})\n"
            message += f"   ID: {uid}\n"
            message += f"   Balance: ₹{balance} | Proofs: {proofs}\n\n"
        
        await update.message.reply_text(message[:4000])
        
    else:
        # Check specific user
        if user_input not in users:
            await update.message.reply_text(f"❌ User {user_input} not found")
            return ConversationHandler.END
        
        user_data = users[user_input]
        message = (
            f"👤 User Details\n\n"
            f"🆔 ID: {user_input}\n"
            f"📛 Name: {user_data.get('name', 'Unknown')}\n"
            f"👤 Username: @{user_data.get('username', 'N/A')}\n"
            f"💰 Balance: ₹{user_data.get('balance', 0)}\n"
            f"📊 Proofs: {user_data.get('proofs', 0)}\n"
            f"📅 Account age: Calculating...\n"
        )
        await update.message.reply_text(message)
    
    return ConversationHandler.END

async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show total users statistics"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    
    users = load(USERS, {})
    verified = load(VERIFIED, {})
    total_balance = sum(user.get("balance", 0) for user in users.values())
    total_proofs = sum(user.get("proofs", 0) for user in users.values())
    
    # Calculate active users (submitted at least 1 proof)
    active_users = len([u for u in users.values() if u.get("proofs", 0) > 0])
    
    await update.message.reply_text(
        f"📊 Statistics:\n\n"
        f"👥 Total Users: {len(users)}\n"
        f"✅ Active Users: {active_users}\n"
        f"💰 Total Balance: ₹{total_balance}\n"
        f"📥 Total Proofs: {total_proofs}\n"
        f"🎯 Verified IDs: {len(verified)}\n"
        f"💰 IDs with amount: {len([v for v in verified.values() if v > 0])}\n"
        f"🎫 IDs without amount: {len([v for v in verified.values() if v == 0])}"
    )

async def show_verified_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all verified IDs"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    
    verified = load(VERIFIED, {})
    if not verified:
        await update.message.reply_text("❌ No verified IDs found")
        return
    
    # Separate IDs with and without amount
    with_amount = {k: v for k, v in verified.items() if v > 0}
    without_amount = {k: v for k, v in verified.items() if v == 0}
    
    total_amount = sum(with_amount.values())
    
    message = "📋 Verified IDs Summary\n\n"
    
    if with_amount:
        message += f"💰 IDs WITH Amount ({len(with_amount)}):\n"
        for idx, (vid, amount) in enumerate(list(with_amount.items())[:20], 1):  # Limit to 20
            message += f"{idx}. {vid} - ₹{amount}\n"
        if len(with_amount) > 20:
            message += f"... and {len(with_amount) - 20} more\n"
        message += f"\n💰 Total amount value: ₹{total_amount}\n\n"
    
    if without_amount:
        message += f"🎫 IDs WITHOUT Amount ({len(without_amount)}):\n"
        for idx, vid in enumerate(list(without_amount.keys())[:20], 1):  # Limit to 20
            message += f"{idx}. {vid}\n"
        if len(without_amount) > 20:
            message += f"... and {len(without_amount) - 20} more\n"
    
    message += f"\n📊 Total: {len(verified)} IDs"
    await update.message.reply_text(message[:4000])

async def switch_to_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch from admin menu to user menu"""
    await update.message.reply_text(
        "🏠 Switching to User Menu",
        reply_markup=menu()
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any conversation"""
    # Clear user data
    if context.user_data:
        context.user_data.clear()
    
    # Show appropriate menu based on user role
    if is_admin(update.effective_user.id):
        await update.message.reply_text(
            "Operation cancelled.",
            reply_markup=admin_menu()
        )
    else:
        await update.message.reply_text(
            "Operation cancelled.",
            reply_markup=menu()
        )
    return ConversationHandler.END

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Callback query handlers
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(wd_action, pattern="^(done|rej):"))
    
    # User menu handlers
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    
    # Admin menu handlers
    app.add_handler(MessageHandler(filters.Regex("^👥 Total Users$"), total_users))
    app.add_handler(MessageHandler(filters.Regex("^📊 Verified IDs$"), show_verified_ids))
    app.add_handler(MessageHandler(filters.Regex("^🏠 User Menu$"), switch_to_user_menu))
    
    # Submit Proof Conversation (SIMPLIFIED - ONLY LINK)
    proof_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={
            PROOF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, proof_link)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    
    # Withdraw Conversation
    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💸 Withdraw$"), withdraw)],
        states={
            WD_METHOD: [CallbackQueryHandler(wd_method)],
            WD_DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, wd_detail)],
            WD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wd_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    
    # Admin: Add Balance Conversation
    add_bal_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Add Balance$"), admin_add_balance)],
        states={
            ADMIN_ADD_BAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_balance_do)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Admin: Remove Balance Conversation
    rem_bal_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➖ Remove Balance$"), admin_remove_balance)],
        states={
            ADMIN_REM_BAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_remove_balance_do)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Admin: Add Verified IDs Conversation (MULTIPLE)
    add_ver_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Add Verified IDs$"), add_ver)],
        states={
            ADD_VER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ver_do)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Admin: Check User Conversation
    check_user_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔍 Check User$"), check_user)],
        states={
            ADMIN_CHECK_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_user_do)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add all conversation handlers
    app.add_handler(proof_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(add_bal_conv)
    app.add_handler(rem_bal_conv)
    app.add_handler(add_ver_conv)
    app.add_handler(check_user_conv)
    
    # Start polling
    print("🤖 Bot is running...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"📢 Force Join Channel: {FORCE_JOIN_CHANNEL}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
