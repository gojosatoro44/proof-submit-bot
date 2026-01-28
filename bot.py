
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
VERIFIED = f"{DATA}/verified.json"  # Now stores as {"user_id": amount}
os.makedirs(DATA, exist_ok=True)

# Thread lock for file operations
file_lock = threading.Lock()

# ================= STATES =================
(
    PROOF_LINK,
    WD_METHOD, WD_DETAIL, WD_AMOUNT,
    ADD_BAL_USER, ADD_BAL_AMOUNT,
    REM_BAL_USER, REM_BAL_AMOUNT,
    ADD_VER_IDS, VER_AMOUNT
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
         ["📋 Add Verified IDs"],
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
    
    # Create inline keyboard with cancel button
    cancel_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_proof")]
    ])
    
    await update.message.reply_text(
        "Bro Send Your Refer Link/Bhai Apna Refer Link Bhejo!\n"
        "\n"
        "[Example:-https://t.me/Abc?start=123456789]",
        reply_markup=cancel_kb
    )
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    uid = str(update.effective_user.id)
    
    # Validate the link
    if not is_valid_url(link):
        cancel_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_proof")]
        ])
        await update.message.reply_text(
            "❌ Invalid link format!\n\n"
            "Please send a valid referral link.\n"
            "Example: https://t.me/Abc?start=123456789",
            reply_markup=cancel_kb
        )
        return PROOF_LINK
    
    # Load all data
    verified = load(VERIFIED, {})  # Now dictionary: {user_id: amount}
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
    used_verified_id = None
    
    # Check if link contains any verified ID
    for vid, amount in verified.items():
        if str(vid) in link:
            status = "VERIFIED"
            used_verified_id = vid
            added = amount
            
            # Add to user's balance
            users[uid]["balance"] += added
            users[uid]["proofs"] += 1
            
            # Remove used verified ID from dictionary
            if vid in verified:
                del verified[vid]
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
            msg = "✅ Proof verified! Amount was 0."
    else:
        msg = "❌ Proof rejected! (Invalid/Fake/Used link)"
    
    await update.message.reply_text(msg, reply_markup=menu())
    return ConversationHandler.END

async def cancel_proof_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle proof submission cancellation via inline button"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "❌ Proof submission cancelled.",
        reply_markup=menu()
    )
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
        [InlineKeyboardButton("UPI", callback_data="upi"),
         InlineKeyboardButton("VSV (Wallet)", callback_data="vsv")],
        [InlineKeyboardButton("FXL", callback_data="fxl"),
         InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
    
    await update.message.reply_text(
        f"💸 Choose Withdrawal Method\n\n"
        f"💰 Your Balance: ₹{users[uid]['balance']}\n\n"
        f"📋 Minimum Amount:\n"
        f"• UPI: ₹5\n"
        f"• VSV (Wallet): ₹2\n"
        f"• FXL: ₹5",
        reply_markup=kb
    )
    return WD_METHOD

async def wd_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.message.reply_text("❌ Withdrawal cancelled", reply_markup=menu())
        return ConversationHandler.END
    
    context.user_data["method"] = query.data.upper()
    
    method_names = {
        "UPI": "UPI ID",
        "VSV": "VSV (Wallet) number",
        "FXL": "FXL details"
    }
    
    await query.message.edit_text(f"📝 Send your {method_names[query.data.upper()]}:")
    return WD_DETAIL

async def wd_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    detail = update.message.text.strip()
    
    # Validate UPI ID format if method is UPI
    if context.user_data["method"] == "UPI":
        # Basic UPI validation (contains @ or .)
        if '@' not in detail and '.' not in detail:
            await update.message.reply_text(
                "❌ Invalid UPI ID format!\n"
                "Valid UPI ID should contain '@' or '.', e.g., username@upi or username.bankname"
            )
            return WD_DETAIL
    
    context.user_data["detail"] = detail
    
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    bal = users[uid]["balance"]
    
    method = context.user_data["method"]
    min_amt = 5.0 if method == "UPI" else (2.0 if method == "VSV" else 5.0)
    
    await update.message.reply_text(
        f"💵 Enter withdrawal amount\n\n"
        f"💰 Available Balance: ₹{bal}\n"
        f"📋 Minimum Amount: ₹{min_amt}\n"
        f"💳 Method: {method}"
    )
    return WD_AMOUNT

async def wd_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text)
    except:
        await update.message.reply_text("❌ Please enter a valid amount (numbers only)")
        return WD_AMOUNT
    
    method = context.user_data["method"]
    min_amt = 5.0 if method == "UPI" else (2.0 if method == "VSV" else 5.0)
    
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    
    if uid not in users:
        await update.message.reply_text("❌ User not found")
        return ConversationHandler.END
    
    if amt < min_amt:
        await update.message.reply_text(f"❌ Minimum withdrawal for {method} is ₹{min_amt}")
        return ConversationHandler.END
    
    if amt > users[uid]["balance"]:
        await update.message.reply_text(f"❌ Insufficient balance. You have ₹{users[uid]['balance']}")
        return ConversationHandler.END
    
    # Check for decimal places
    if '.' in update.message.text:
        decimal_places = len(update.message.text.split('.')[1])
        if decimal_places > 2:
            await update.message.reply_text("❌ Maximum 2 decimal places allowed")
            return WD_AMOUNT
    
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
            f"💸 WITHDRAWAL REQUEST\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 User: {users[uid]['name']}\n"
            f"🆔 ID: {uid}\n"
            f"💰 Amount: ₹{amt}\n"
            f"📋 Method: {method}\n"
            f"🔧 Details: {context.user_data['detail']}\n"
            f"━━━━━━━━━━━━━━━━━━",
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
        f"✅ Withdrawal Request Sent!\n\n"
        f"• Amount: ₹{amt}\n"
        f"• Method: {method}\n"
        f"• Details: {context.user_data['detail']}\n\n"
        f"⏳ Processing time: 24-48 hours\n"
        f"📬 You'll be notified when processed.",
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
        msg = (
            f"✅ WITHDRAWAL APPROVED!\n\n"
            f"💰 Amount: ₹{amount}\n"
            f"✅ Status: Completed\n\n"
            f"Thank you for using our service!"
        )
        await query.edit_message_text(f"✅ Withdrawal approved for user {uid}")
    else:
        # Refund balance
        users = load(USERS, {})
        if uid in users:
            users[uid]["balance"] += amount
            save(USERS, users)
        msg = (
            f"❌ WITHDRAWAL REJECTED\n\n"
            f"💰 Amount: ₹{amount}\n"
            f"❌ Status: Rejected\n"
            f"💸 Refunded to your balance\n\n"
            f"Contact support if you have questions."
        )
        await query.edit_message_text(f"❌ Withdrawal rejected for user {uid}")
    
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
    
    await update.message.reply_text("📝 Send user ID to add balance:")
    return ADD_BAL_USER

async def add_bal_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.text.strip()
    users = load(USERS, {})
    
    if uid not in users:
        await update.message.reply_text("❌ User not found")
        return ConversationHandler.END
    
    context.user_data["add_user"] = uid
    await update.message.reply_text(
        f"👤 User: {users[uid].get('name', 'Unknown')}\n"
        f"💰 Current Balance: ₹{users[uid]['balance']}\n\n"
        f"Enter amount to add:"
    )
    return ADD_BAL_AMOUNT

async def add_bal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive")
            return ADD_BAL_AMOUNT
    except:
        await update.message.reply_text("❌ Invalid amount. Enter a number")
        return ADD_BAL_AMOUNT
    
    uid = context.user_data["add_user"]
    users = load(USERS, {})
    
    if uid in users:
        users[uid]["balance"] += amount
        save(USERS, users)
        
        try:
            await update.get_bot().send_message(
                int(uid),
                f"💰 BALANCE UPDATED!\n\n"
                f"✅ ₹{amount} added to your account\n"
                f"💵 New Balance: ₹{users[uid]['balance']}\n\n"
                f"Thank you!"
            )
        except:
            pass
        
        await update.message.reply_text(
            f"✅ Balance added successfully!\n\n"
            f"👤 User: {uid}\n"
            f"💰 Added: ₹{amount}\n"
            f"💵 New Balance: ₹{users[uid]['balance']}",
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
    
    await update.message.reply_text("📝 Send user ID to remove balance:")
    return REM_BAL_USER

async def rem_bal_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.text.strip()
    users = load(USERS, {})
    
    if uid not in users:
        await update.message.reply_text("❌ User not found")
        return ConversationHandler.END
    
    context.user_data["rem_user"] = uid
    await update.message.reply_text(
        f"👤 User: {users[uid].get('name', 'Unknown')}\n"
        f"💰 Current Balance: ₹{users[uid]['balance']}\n\n"
        f"Enter amount to remove:"
    )
    return REM_BAL_AMOUNT

async def rem_bal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive")
            return REM_BAL_AMOUNT
    except:
        await update.message.reply_text("❌ Invalid amount. Enter a number")
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
                f"⚠️ BALANCE UPDATED!\n\n"
                f"❌ ₹{amount} removed from your account\n"
                f"💵 New Balance: ₹{users[uid]['balance']}\n\n"
                f"Contact support if this is an error."
            )
        except:
            pass
        
        await update.message.reply_text(
            f"✅ Balance removed successfully!\n\n"
            f"👤 User: {uid}\n"
            f"💰 Removed: ₹{amount}\n"
            f"💵 New Balance: ₹{users[uid]['balance']}",
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
        "📋 Send Verified User IDs (one per line):\n\n"
        "Example:\n"
        "6274638384\n"
        "1234567890\n"
        "9876543210\n\n"
        "I'll extract the user IDs and then ask for the amount."
    )
    return ADD_VER_IDS

async def add_ver_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = text.split('\n')
    
    extracted_ids = []
    
    for line in lines:
        line = line.strip()
        # Extract numbers from the line (for IDs)
        numbers = re.findall(r'\d+', line)
        for num in numbers:
            if len(num) >= 8:  # Assuming user IDs are at least 8 digits
                extracted_ids.append(num)
    
    if not extracted_ids:
        await update.message.reply_text("❌ No valid user IDs found. Try again.")
        return ADD_VER_IDS
    
    # Store extracted IDs in context
    context.user_data["ver_ids"] = extracted_ids
    
    # Show extracted IDs
    ids_preview = "\n".join(extracted_ids[:10])  # Show first 10
    if len(extracted_ids) > 10:
        ids_preview += f"\n... and {len(extracted_ids) - 10} more"
    
    await update.message.reply_text(
        f"✅ Found {len(extracted_ids)} user ID(s):\n\n"
        f"{ids_preview}\n\n"
        f"Now enter the amount to give for ALL these IDs:"
    )
    return VER_AMOUNT

async def ver_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if amount < 0:
            await update.message.reply_text("❌ Amount cannot be negative")
            return VER_AMOUNT
    except:
        await update.message.reply_text("❌ Invalid amount. Enter a number")
        return VER_AMOUNT
    
    if "ver_ids" not in context.user_data:
        await update.message.reply_text("❌ No IDs found. Start over.")
        return ConversationHandler.END
    
    extracted_ids = context.user_data["ver_ids"]
    verified = load(VERIFIED, {})
    
    added_count = 0
    for uid in extracted_ids:
        if uid not in verified:
            verified[uid] = amount
            added_count += 1
        else:
            # Update existing ID with new amount
            verified[uid] = amount
    
    save(VERIFIED, verified)
    
    await update.message.reply_text(
        f"✅ Successfully added/updated {added_count} ID(s)!\n\n"
        f"💰 Amount set: ₹{amount} for each ID\n"
        f"📊 Total verified IDs now: {len(verified)}",
        reply_markup=admin_menu()
    )
    
    # Clear context
    context.user_data.clear()
    return ConversationHandler.END

# ================= TOTAL USERS =================
async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    users = load(USERS, {})
    verified = load(VERIFIED, {})
    
    total_balance = sum(user["balance"] for user in users.values())
    total_proofs = sum(user["proofs"] for user in users.values())
    
    # Calculate total amount in verified IDs
    total_verified_amount = sum(verified.values())
    
    await update.message.reply_text(
        f"📊 BOT STATISTICS\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: {len(users)}\n"
        f"💰 Total Balance: ₹{total_balance}\n"
        f"📥 Total Proofs: {total_proofs}\n"
        f"✅ Verified IDs: {len(verified)}\n"
        f"💵 Total Verified Amount: ₹{total_verified_amount}"
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
    msg = "📋 RECENT USERS\n━━━━━━━━━━━━━━\n\n"
    
    for uid, data in user_list:
        username = f"@{data['username']}" if data.get('username') else "No username"
        msg += (
            f"👤 Name: {data.get('name', 'Unknown')}\n"
            f"📱 Username: {username}\n"
            f"🆔 ID: {uid}\n"
            f"💰 Balance: ₹{data['balance']}\n"
            f"📊 Proofs: {data['proofs']}\n"
            f"━━━━━━━━━━━━━━\n"
        )
    
    await update.message.reply_text(msg)

# ================= CANCEL =================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled", reply_markup=menu())
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
    app.add_handler(CallbackQueryHandler(cancel_proof_callback, pattern="^cancel_proof$"))
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
            PROOF_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, proof_link),
                CallbackQueryHandler(cancel_proof_callback, pattern="^cancel_proof$")
            ]
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
            ADD_VER_IDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ver_ids)],
            VER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ver_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Add all conversation handlers
    app.add_handler(proof_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(add_bal_conv)
    app.add_handler(rem_bal_conv)
    app.add_handler(ver_ids_conv)
    
    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
