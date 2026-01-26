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
os.makedirs(DATA, exist_ok=True)

# Thread lock for file operations to prevent corruption
file_lock = threading.Lock()

# ================= STATES =================
(
    PROOF_SCREEN, PROOF_LINK,
    WD_METHOD, WD_DETAIL, WD_AMOUNT,
    ADD_BAL, REM_BAL, ADD_VER, CHECK_USER
) = range(9)

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
        users[uid] = {"balance": 0, "proofs": 0, "name": update.effective_user.full_name}
    save(USERS, users)

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
    # Check if user has joined channel
    if not await force_join(update, context):
        await update.message.reply_text("❌ Please join our channel first using /start")
        return ConversationHandler.END
    
    # Clear previous conversation data
    context.user_data.clear()
    
    await update.message.reply_text(
        "📸 Please send the screenshot proof.\n\n"
        "⚠️ Make sure the screenshot clearly shows:\n"
        "• The task completion\n"
        "• Your referral/username\n"
        "• Date and time (if possible)"
    )
    return PROOF_SCREEN

async def proof_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(
            "❌ Please send a screenshot (photo only).\n"
            "If you sent a document, please send it as a photo."
        )
        return PROOF_SCREEN
    
    # Save the photo file_id
    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text(
        "✅ Screenshot received!\n\n"
        "🔗 Now send the referral link.\n"
        "This should be the link you used for the task."
    )
    return PROOF_LINK

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        users[uid] = {"balance": 0, "proofs": 0, "name": update.effective_user.full_name}
    
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
    
    # Build caption without nested f-strings
    caption_lines = [
        f"📥 New Proof Submission",
        f"👤 User: {user_name}",
        f"🆔 ID: {uid}",
        f"✅ Status: {status}",
        f"💰 Amount: ₹{added}",
        f"🔗 Link: {link[:100]}..."
    ]
    
    if verified_id:
        caption_lines.append(f"🎯 Verified ID: {verified_id}")
    
    caption = "\n".join(caption_lines)
    
    try:
        await context.bot.send_photo(
            ADMIN_ID,
            photo=context.user_data["photo"],
            caption=caption
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
            "• Fake screenshot\n"
            "• Same device used multiple times\n"
            "• Referral link mismatch\n"
            "• Invalid or already used link\n\n"
            "Contact support if you believe this is an error."
        )
    
    await update.message.reply_text(msg, reply_markup=menu())
    return ConversationHandler.END

# ================= WITHDRAW =================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user has joined channel
    if not await force_join(update, context):
        await update.message.reply_text("❌ Please join our channel first using /start")
        return ConversationHandler.END
    
    # Check user balance
    users = load(USERS, {})
    uid = str(update.effective_user.id)
    
    if uid not in users or users[uid]["balance"] <= 0:
        await update.message.reply_text("❌ Insufficient balance to withdraw")
        return ConversationHandler.END
    
    # Clear previous data
    context.user_data.clear()
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("UPI", callback_data="upi"),
         InlineKeyboardButton("VSV", callback_data="vsv"),
         InlineKeyboardButton("FXL", callback_data="fxl")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
    
    await update.message.reply_text(
        f"💸 Choose withdrawal method\n\n"
        f"Your balance: ₹{users[uid]['balance']}\n"
        f"Minimum withdrawal:\n"
        f"• UPI: ₹5\n"
        f"• VSV/FXL: ₹2",
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
    method_name = {"UPI": "UPI ID", "VSV": "VSV number", "FXL": "FXL number"}
    
    await query.message.edit_text(
        f"Please send your {method_name.get(context.user_data['method'], 'details')}"
    )
    return WD_DETAIL

async def wd_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    detail = update.message.text.strip()
    
    # Basic validation
    if len(detail) < 3:
        await update.message.reply_text("❌ Please provide valid details")
        return WD_DETAIL
    
    context.user_data["detail"] = detail
    
    min_amt = 5 if context.user_data["method"] == "UPI" else 2
    await update.message.reply_text(
        f"Enter withdrawal amount (Minimum ₹{min_amt})\n"
        f"Your current balance: ₹{load(USERS, {}).get(str(update.effective_user.id), {}).get('balance', 0)}"
    )
    return WD_AMOUNT

async def wd_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text(f"❌ Minimum withdrawal is ₹{min_amt}")
        return ConversationHandler.END
    
    if amt > user_bal:
        await update.message.reply_text(f"❌ Insufficient balance. You have ₹{user_bal}")
        return ConversationHandler.END
    
    # Deduct balance
    users[uid]["balance"] -= amt
    save(USERS, users)
    
    # Send withdrawal request to admin
    user_info = users.get(uid, {})
    user_name = user_info.get("name", "Unknown")
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"done:{uid}:{amt}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"rej:{uid}:{amt}")]
    ])
    
    # Build message without complex f-strings
    message_text = (
        f"💸 New Withdrawal Request\n"
        f"👤 User: {user_name}\n"
        f"🆔 ID: {uid}\n"
        f"💰 Amount: ₹{amt}\n"
        f"📋 Method: {method}\n"
        f"🔧 Details: {context.user_data['detail']}\n"
        f"⏰ Time: {update.message.date}"
    )
    
    try:
        await update.get_bot().send_message(
            ADMIN_ID,
            message_text,
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
        f"Processing time: 24-48 hours\n"
        f"You'll be notified when processed.",
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
        message_to_user = (
            f"✅ Withdrawal Approved!\n"
            f"💰 ₹{amount} has been processed.\n"
            f"Thank you for using our service!"
        )
        await context.bot.send_message(int(uid), message_to_user)
        await query.edit_message_text(f"✅ Withdrawal approved for user {uid}")
        
    elif action == "rej":
        # Withdrawal rejected - refund balance
        users = load(USERS, {})
        if uid in users:
            users[uid]["balance"] += amount
            save(USERS, users)
        
        message_to_user = (
            f"❌ Withdrawal Rejected\n"
            f"💰 ₹{amount} has been refunded to your balance.\n"
            f"Reason: Invalid details or system issue\n"
            f"Contact support if you need help."
        )
        await context.bot.send_message(int(uid), message_to_user)
        await query.edit_message_text(f"❌ Withdrawal rejected for user {uid}")

# ================= ADMIN COMMANDS =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    
    kb = ReplyKeyboardMarkup(
        [["➕ Add Balance", "➖ Remove Balance"],
         ["📋 Add Verified ID", "👥 Total Users"],
         ["📊 User Details", "🏠 Main Menu"]],
        resize_keyboard=True
    )
    await update.message.reply_text("⚙ Admin Panel", reply_markup=kb)

async def add_ver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add verified ID"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Send Verified ID and Amount (optional):\n\n"
        "Format:\n"
        "• verified_id amount (e.g., ref123 10)\n"
        "• or just verified_id (amount will be 0)"
    )
    return ADD_VER

async def add_ver_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return ConversationHandler.END
    
    parts = update.message.text.strip().split()
    if not parts:
        await update.message.reply_text("❌ Invalid format")
        return ADD_VER
    
    verified_id = parts[0]
    amount = float(parts[1]) if len(parts) > 1 else 0
    
    v = load(VERIFIED, {})
    v[verified_id] = amount
    save(VERIFIED, v)
    
    await update.message.reply_text(
        f"✅ Verified ID added:\n"
        f"ID: {verified_id}\n"
        f"Amount: ₹{amount}"
    )
    return ConversationHandler.END

async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    
    users = load(USERS, {})
    total_balance = sum(user.get("balance", 0) for user in users.values())
    total_proofs = sum(user.get("proofs", 0) for user in users.values())
    
    message_text = (
        f"📊 Statistics:\n\n"
        f"👥 Total Users: {len(users)}\n"
        f"💰 Total Balance: ₹{total_balance}\n"
        f"📥 Total Proofs: {total_proofs}\n"
        f"✅ Verified IDs: {len(load(VERIFIED, {}))}"
    )
    
    await update.message.reply_text(message_text)

async def user_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get details of a specific user"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin only")
        return
    
    await update.message.reply_text(
        "Send user ID to check details (or send 'all' for all users):"
    )
    # You can extend this to another conversation handler if needed

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any conversation"""
    await update.message.reply_text(
        "Operation cancelled.",
        reply_markup=menu()
    )
    # Clear user data
    if context.user_data:
        context.user_data.clear()
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
    
    # Menu handlers
    app.add_handler(MessageHandler(filters.Regex("^💰 Balance$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(MessageHandler(filters.Regex("^👥 Total Users$"), total_users))
    app.add_handler(MessageHandler(filters.Regex("^📊 User Details$"), user_details))
    app.add_handler(MessageHandler(filters.Regex("^🏠 Main Menu$"), start))
    
    # Submit Proof Conversation
    proof_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📤 Submit Proof$"), submit_proof)],
        states={
            PROOF_SCREEN: [
                MessageHandler(filters.PHOTO, proof_screen),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u,c: None)  # Ignore text
            ],
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
    
    # Add Verified ID Conversation (Admin)
    add_ver_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📋 Add Verified ID$"), add_ver)],
        states={
            ADD_VER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ver_do)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(proof_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(add_ver_conv)
    
    # Start polling
    print("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
