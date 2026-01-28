import os, json
import threading
import re
import time
import warnings
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
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found in environment variables!")
    print("💡 Please set BOT_TOKEN environment variable")
    exit(1)

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
FORCE_JOIN_CHANNEL = "@TaskByZahid"

DATA = "data"
USERS = f"{DATA}/users.json"
VERIFIED = f"{DATA}/verified.json"
SUBMISSION_HISTORY = f"{DATA}/submission_history.json"
BACKUP_DIR = f"{DATA}/backups"
os.makedirs(DATA, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

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

# ================= ENHANCED UTILS =================
def backup_data():
    """Create backup of all data files"""
    timestamp = int(time.time())
    for file in [USERS, VERIFIED, SUBMISSION_HISTORY]:
        if os.path.exists(file):
            filename = os.path.basename(file)
            backup_path = os.path.join(BACKUP_DIR, f"{filename}.backup_{timestamp}")
            with file_lock:
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                    with open(backup_path, 'w') as f:
                        json.dump(data, f, indent=2)
                except Exception as e:
                    print(f"⚠️ Backup failed for {file}: {e}")

def load(p, d):
    """Enhanced load with auto-backup"""
    with file_lock:
        if not os.path.exists(p):
            print(f"📄 Creating new file: {p}")
            with open(p, "w") as f: 
                json.dump(d, f)
            return d.copy()
        
        try:
            with open(p, 'r') as f: 
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON decode error in {p}: {e}")
            # Create new file if corrupted
            with open(p, "w") as f: 
                json.dump(d, f)
            return d.copy()
        except Exception as e:
            print(f"⚠️ Error loading {p}: {e}")
            return d.copy()

def save(p, d):
    """Enhanced save with auto-backup"""
    with file_lock:
        # Create backup before saving
        if os.path.exists(p):
            backup_data()
        
        try:
            with open(p, "w") as f: 
                json.dump(d, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error saving {p}: {e}")
            return False

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
         ["📜 Proof History", "🔧 View Verified IDs"],
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
    except Exception as e:
        print(f"⚠️ Force join check error: {e}")
        return True  # Return True to avoid blocking users if check fails

def is_admin(user_id):
    return user_id == ADMIN_ID

def is_valid_url(url):
    """
    Check if the input is a valid URL.
    Supports http, https, and common app referral links.
    """
    if not url:
        return False
    
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
    
    # Check if it contains common domain words
    domain_words = ['.com', '.in', '.org', '.net', '.co', '.io', '.me', '.app', '.xyz']
    for word in domain_words:
        if word in url.lower():
            return True
    
    # Check if it looks like a Telegram invite link
    if 't.me' in url.lower() or 'telegram.me' in url.lower():
        return True
    
    return False

def log_submission(user_id, link, status, amount, used_ids):
    """Log submission history"""
    try:
        history = load(SUBMISSION_HISTORY, {})
        
        if user_id not in history:
            history[user_id] = []
        
        history[user_id].append({
            "timestamp": int(time.time()),
            "link": link,
            "status": status,
            "amount": amount,
            "used_ids": used_ids
        })
        
        # Keep only last 100 submissions per user
        if len(history[user_id]) > 100:
            history[user_id] = history[user_id][-100:]
        
        save(SUBMISSION_HISTORY, history)
    except Exception as e:
        print(f"⚠️ Error logging submission: {e}")

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print(f"🚀 Start command from user: {update.effective_user.id}")
        
        # Check force join
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
                "username": update.effective_user.username,
                "joined_at": int(time.time()),
                "last_active": int(time.time())
            }
            print(f"✅ New user registered: {uid}")
        else:
            # Update last active time
            users[uid]["last_active"] = int(time.time())
            if "joined_at" not in users[uid]:
                users[uid]["joined_at"] = int(time.time())
            print(f"✅ Existing user returned: {uid}")
        
        save(USERS, users)

        await update.message.reply_text(
            f"👋 Welcome {update.effective_user.first_name}!\n"
            "✅ You can now submit proofs and withdraw earnings.",
            reply_markup=menu()
        )
        print(f"✅ Start command completed for user: {uid}")
        
    except Exception as e:
        print(f"❌ Error in start command: {e}")
        try:
            await update.message.reply_text(
                "❌ An error occurred. Please try again."
            )
        except:
            pass

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        if not await force_join(update, context):
            await query.edit_message_text("❌ Still not in channel. Join and try /start")
            return
        
        await query.edit_message_text("✅ Join verified! Use /start to begin.")
    except Exception as e:
        print(f"❌ Error in check_join_callback: {e}")

# ================= BALANCE =================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await force_join(update, context):
            await update.message.reply_text("❌ Join channel first using /start")
            return
        
        users = load(USERS, {})
        uid = str(update.effective_user.id)
        
        if uid not in users:
            await update.message.reply_text("❌ User not found. Use /start")
            return
        
        # Update last active time
        users[uid]["last_active"] = int(time.time())
        save(USERS, users)
        
        bal = users[uid]["balance"]
        proofs = users[uid]["proofs"]
        await update.message.reply_text(
            f"💰 Balance: ₹{bal}\n"
            f"📊 Proofs Submitted: {proofs}"
        )
    except Exception as e:
        print(f"❌ Error in balance command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

# ================= SUPPORT =================
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🆘 Support: @DTXZAHID")
    except Exception as e:
        print(f"❌ Error in support command: {e}")

# ================= SUBMIT PROOF =================
async def submit_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        print(f"❌ Error in submit_proof: {e}")
        return ConversationHandler.END

async def proof_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
        verified = load(VERIFIED, {})
        users = load(USERS, {})
        
        # Initialize user if not exists
        if uid not in users:
            users[uid] = {
                "balance": 0, 
                "proofs": 0, 
                "name": update.effective_user.full_name,
                "username": update.effective_user.username,
                "joined_at": int(time.time()),
                "last_active": int(time.time())
            }
        
        status = "REJECTED"
        added = 0
        used_verified_ids = []
        
        # Check if link contains any verified ID
        for vid, data in verified.items():
            # Convert to dict if it's still old format (just a number)
            if isinstance(data, (int, float)):
                verified[vid] = {"amount": data, "used": False, "added_at": int(time.time())}
                data = verified[vid]
            
            # Check if this ID is in the link AND hasn't been used yet
            if str(vid) in link and not data.get("used", False):
                status = "VERIFIED"
                used_verified_ids.append(vid)
                added = data["amount"]
                
                # Mark this verified ID as used
                verified[vid]["used"] = True
                verified[vid]["used_by"] = uid
                verified[vid]["used_at"] = int(time.time())
                verified[vid]["link"] = link[:100]
                
                break  # Stop after first match (one verified ID per submission)
        
        if status == "VERIFIED" and added > 0:
            # Add to user's balance
            users[uid]["balance"] += added
            users[uid]["proofs"] += 1
            
            # Update user's last active time
            users[uid]["last_active"] = int(time.time())
            
            # Log the submission
            log_submission(uid, link, status, added, used_verified_ids)
        
        save(USERS, users)
        save(VERIFIED, verified)
        
        # Send to admin
        if ADMIN_ID:
            try:
                await context.bot.send_message(
                    ADMIN_ID,
                    f"📥 New Proof\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"👤 {users[uid]['name']}\n"
                    f"🆔 {uid}\n"
                    f"✅ {status}\n"
                    f"💰 +₹{added}\n"
                    f"🔗 {link[:100]}{'...' if len(link) > 100 else ''}\n"
                    f"🏷️ Used IDs: {', '.join(used_verified_ids) if used_verified_ids else 'None'}"
                )
            except Exception as e:
                print(f"⚠️ Failed to notify admin: {e}")
        
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
    except Exception as e:
        print(f"❌ Error in proof_link: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.", reply_markup=menu())
        return ConversationHandler.END

async def cancel_proof_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle proof submission cancellation via inline button"""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text(
            "❌ Proof submission cancelled.",
            reply_markup=menu()
        )
        return ConversationHandler.END
    except Exception as e:
        print(f"❌ Error in cancel_proof_callback: {e}")
        return ConversationHandler.END

# ================= WITHDRAW =================
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        print(f"❌ Error in withdraw: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.", reply_markup=menu())
        return ConversationHandler.END

async def wd_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
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
    except Exception as e:
        print(f"❌ Error in wd_method: {e}")
        return ConversationHandler.END

async def wd_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        print(f"❌ Error in wd_detail: {e}")
        return ConversationHandler.END

async def wd_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
        
        if ADMIN_ID:
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
    except Exception as e:
        print(f"❌ Error in wd_amount: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.", reply_markup=menu())
        return ConversationHandler.END

async def wd_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        if not is_admin(query.from_user.id):
            return
        
        parts = query.data.split(':')
        if len(parts) < 3:
            return
        
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
    except Exception as e:
        print(f"❌ Error in wd_action: {e}")

# ================= ADMIN COMMANDS =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("❌ Admin only")
            return
        
        await update.message.reply_text("⚙ Admin Panel", reply_markup=admin_menu())
    except Exception as e:
        print(f"❌ Error in admin command: {e}")

# ================= ADD BALANCE =================
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return
        
        await update.message.reply_text("📝 Send user ID to add balance:")
        return ADD_BAL_USER
    except Exception as e:
        print(f"❌ Error in add_balance: {e}")
        return ConversationHandler.END

async def add_bal_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        print(f"❌ Error in add_bal_user: {e}")
        return ConversationHandler.END

async def add_bal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        print(f"❌ Error in add_bal_amount: {e}")
        return ConversationHandler.END

# ================= REMOVE BALANCE =================
async def remove_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return
        
        await update.message.reply_text("📝 Send user ID to remove balance:")
        return REM_BAL_USER
    except Exception as e:
        print(f"❌ Error in remove_balance: {e}")
        return ConversationHandler.END

async def rem_bal_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        print(f"❌ Error in rem_bal_user: {e}")
        return ConversationHandler.END

async def rem_bal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        print(f"❌ Error in rem_bal_amount: {e}")
        return ConversationHandler.END

# ================= ADD VERIFIED IDs =================
async def add_verified_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e:
        print(f"❌ Error in add_verified_ids: {e}")
        return ConversationHandler.END

async def add_ver_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text.strip()
        lines = text.split('\n')
        
        extracted_ids = []
        
        for line in lines:
            line = line.strip()
            # Extract numbers from the line (for IDs)
            numbers = re.findall(r'\d+', line)
            for num in numbers:
                if len(num) >= 5:  # Reduced from 8 to 5 to accept shorter IDs
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
    except Exception as e:
        print(f"❌ Error in add_ver_ids: {e}")
        return ConversationHandler.END

async def ver_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
        updated_count = 0
        
        for uid in extracted_ids:
            if uid not in verified:
                # Add new verified ID
                verified[uid] = {
                    "amount": amount,
                    "used": False,
                    "added_at": int(time.time())
                }
                added_count += 1
            else:
                # Update existing ID - keep old data but update amount if different
                if isinstance(verified[uid], dict):
                    if verified[uid].get("amount", 0) != amount:
                        verified[uid]["amount"] = amount
                        verified[uid]["updated_at"] = int(time.time())
                        updated_count += 1
                else:
                    # Convert old format to new format
                    old_amount = verified[uid]
                    verified[uid] = {
                        "amount": amount,
                        "used": False,
                        "added_at": int(time.time()),
                        "old_amount": old_amount
                    }
                    updated_count += 1
        
        save(VERIFIED, verified)
        
        response_text = f"✅ Successfully processed {len(extracted_ids)} ID(s)!\n\n"
        if added_count > 0:
            response_text += f"➕ Newly added: {added_count} ID(s)\n"
        if updated_count > 0:
            response_text += f"✏️ Updated: {updated_count} ID(s)\n"
        
        response_text += f"💰 Amount set: ₹{amount} for each ID\n"
        response_text += f"📊 Total verified IDs now: {len(verified)}\n"
        
        # Count unused IDs
        unused_count = 0
        for data in verified.values():
            if isinstance(data, dict):
                if not data.get("used", False):
                    unused_count += 1
            else:
                unused_count += 1
        
        response_text += f"✅ Unused IDs: {unused_count}"
        
        await update.message.reply_text(
            response_text,
            reply_markup=admin_menu()
        )
        
        # Clear context
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        print(f"❌ Error in ver_amount: {e}")
        return ConversationHandler.END

# ================= VIEW VERIFIED IDs =================
async def view_verified_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return
        
        verified = load(VERIFIED, {})
        
        if not verified:
            await update.message.reply_text("📭 No verified IDs found.")
            return
        
        # Count statistics
        total_ids = len(verified)
        used_ids = 0
        unused_ids = 0
        total_amount = 0
        used_amount = 0
        unused_amount = 0
        
        for vid, data in verified.items():
            if isinstance(data, dict):
                amount = data.get("amount", 0)
                used = data.get("used", False)
            else:
                amount = data
                used = False
            
            total_amount += amount
            if used:
                used_ids += 1
                used_amount += amount
            else:
                unused_ids += 1
                unused_amount += amount
        
        # Show last 10 verified IDs
        msg = f"📋 VERIFIED IDs STATISTICS\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 Total IDs: {total_ids}\n"
        msg += f"✅ Unused: {unused_ids} (₹{unused_amount})\n"
        msg += f"❌ Used: {used_ids} (₹{used_amount})\n"
        msg += f"💰 Total Amount: ₹{total_amount}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"📜 Recent IDs (Last 10):\n"
        
        # Show last 10 IDs
        recent_ids = list(verified.items())[-10:]
        for i, (vid, data) in enumerate(recent_ids[-10:], 1):
            if isinstance(data, dict):
                amount = data.get("amount", 0)
                used = "✅" if not data.get("used", False) else "❌"
                status = f"{used} ₹{amount}"
            else:
                status = f"₹{data}"
            
            msg += f"{i}. {vid}: {status}\n"
        
        if len(verified) > 10:
            msg += f"\n... and {len(verified) - 10} more IDs"
        
        await update.message.reply_text(msg)
    except Exception as e:
        print(f"❌ Error in view_verified_ids: {e}")
        await update.message.reply_text("❌ An error occurred.")

# ================= PROOF HISTORY =================
async def proof_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return
        
        history = load(SUBMISSION_HISTORY, {})
        
        if not history:
            await update.message.reply_text("📭 No submission history found.")
            return
        
        # Get today's submissions
        today_timestamp = int(time.time()) - 86400  # Last 24 hours
        today_count = 0
        today_amount = 0
        
        # Get recent submissions (last 20)
        recent_subs = []
        for user_id, submissions in history.items():
            for sub in submissions[-5:]:  # Last 5 per user
                if sub["timestamp"] >= today_timestamp:
                    today_count += 1
                    today_amount += sub.get("amount", 0)
                recent_subs.append((user_id, sub))
        
        # Sort by timestamp (newest first)
        recent_subs.sort(key=lambda x: x[1]["timestamp"], reverse=True)
        
        msg = f"📜 PROOF SUBMISSION HISTORY\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 Today's Stats (24h):\n"
        msg += f"   • Submissions: {today_count}\n"
        msg += f"   • Amount: ₹{today_amount}\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"🕒 Recent Submissions:\n"
        
        for user_id, sub in recent_subs[:10]:  # Show last 10
            timestamp = time.strftime('%Y-%m-%d %H:%M', time.localtime(sub["timestamp"]))
            status = "✅" if sub["status"] == "VERIFIED" else "❌"
            amount = f"+₹{sub['amount']}" if sub["amount"] > 0 else "₹0"
            
            msg += f"\n⏰ {timestamp}\n"
            msg += f"👤 User: {user_id}\n"
            msg += f"📊 Status: {status} {amount}\n"
            msg += f"🔗 Link: {sub['link'][:50]}...\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if len(recent_subs) > 10:
            msg += f"\n\n... and {len(recent_subs) - 10} more submissions"
        
        await update.message.reply_text(msg)
    except Exception as e:
        print(f"❌ Error in proof_history: {e}")
        await update.message.reply_text("❌ An error occurred.")

# ================= TOTAL USERS =================
async def total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return
        
        users = load(USERS, {})
        verified = load(VERIFIED, {})
        history = load(SUBMISSION_HISTORY, {})
        
        # Calculate statistics
        total_balance = sum(user.get("balance", 0) for user in users.values())
        total_proofs = sum(user.get("proofs", 0) for user in users.values())
        
        # Calculate verified IDs statistics
        unused_amount = 0
        used_amount = 0
        for data in verified.values():
            if isinstance(data, dict):
                amount = data.get("amount", 0)
                if data.get("used", False):
                    used_amount += amount
                else:
                    unused_amount += amount
            else:
                unused_amount += data
        
        # Active users (last 7 days)
        week_ago = int(time.time()) - 604800
        active_users = sum(1 for user in users.values() 
                          if user.get("last_active", 0) >= week_ago)
        
        # Today's submissions
        today_timestamp = int(time.time()) - 86400
        today_subs = 0
        for submissions in history.values():
            for sub in submissions:
                if sub.get("timestamp", 0) >= today_timestamp:
                    today_subs += 1
        
        await update.message.reply_text(
            f"📊 BOT STATISTICS\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 Total Users: {len(users)}\n"
            f"📈 Active (7d): {active_users}\n"
            f"💰 Total Balance: ₹{total_balance}\n"
            f"📥 Total Proofs: {total_proofs}\n"
            f"📊 Today's Submissions: {today_subs}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ VERIFIED IDs:\n"
            f"• Total: {len(verified)}\n"
            f"• Unused Amount: ₹{unused_amount}\n"
            f"• Used Amount: ₹{used_amount}\n"
            f"• Total Amount: ₹{unused_amount + used_amount}"
        )
    except Exception as e:
        print(f"❌ Error in total_users: {e}")
        await update.message.reply_text("❌ An error occurred.")

# ================= USER DETAILS =================
async def user_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            return
        
        users = load(USERS, {})
        if not users:
            await update.message.reply_text("❌ No users found")
            return
        
        # Show last 5 users with detailed info
        user_list = list(users.items())[-5:]
        msg = "📋 RECENT USERS DETAILS\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for uid, data in user_list:
            username = f"@{data['username']}" if data.get('username') else "No username"
            
            # Format join date
            join_date = time.strftime('%Y-%m-%d', time.localtime(data.get('joined_at', 0)))
            
            # Format last active
            last_active = data.get('last_active', 0)
            if last_active:
                days_ago = (int(time.time()) - last_active) // 86400
                if days_ago == 0:
                    last_seen = "Today"
                else:
                    last_seen = f"{days_ago} day(s) ago"
            else:
                last_seen = "Never"
            
            msg += (
                f"👤 Name: {data.get('name', 'Unknown')}\n"
                f"📱 Username: {username}\n"
                f"🆔 ID: {uid}\n"
                f"💰 Balance: ₹{data.get('balance', 0)}\n"
                f"📊 Proofs: {data.get('proofs', 0)}\n"
                f"📅 Joined: {join_date}\n"
                f"⏰ Last Active: {last_seen}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )
        
        await update.message.reply_text(msg)
    except Exception as e:
        print(f"❌ Error in user_details: {e}")
        await update.message.reply_text("❌ An error occurred.")

# ================= CANCEL =================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("❌ Operation cancelled", reply_markup=menu())
        if context.user_data:
            context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        print(f"❌ Error in cancel: {e}")
        return ConversationHandler.END

# ================= MAIN =================
def main():
    print("=" * 50)
    print("🤖 Telegram Bot Starting...")
    print("=" * 50)
    
    # Check if BOT_TOKEN is set
    if not BOT_TOKEN:
        print("❌ FATAL ERROR: BOT_TOKEN environment variable is not set!")
        print("💡 Please set the BOT_TOKEN environment variable")
        print("   On Railway: Add it in the Variables section")
        print("   Locally: export BOT_TOKEN='your_token_here'")
        exit(1)
    
    print(f"✅ BOT_TOKEN: {'*' * (len(BOT_TOKEN) - 10)}{BOT_TOKEN[-10:] if len(BOT_TOKEN) > 10 else ''}")
    print(f"✅ ADMIN_ID: {ADMIN_ID}")
    print(f"✅ Force Join Channel: {FORCE_JOIN_CHANNEL}")
    
    # Create initial backup
    try:
        print("💾 Creating initial backup...")
        backup_data()
        print("✅ Backup created successfully!")
    except Exception as e:
        print(f"⚠️ Warning: Initial backup failed: {e}")
    
    try:
        # Suppress the warning
        warnings.filterwarnings("ignore", category=UserWarning)
        
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        print("✅ Application built successfully!")
    except Exception as e:
        print(f"❌ Failed to build application: {e}")
        exit(1)
    
    # Basic commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Callback queries
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(wd_action, pattern="^(done|rej):"))
    
    # User menu handlers
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^💰 Balance$'), balance))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^🆘 Support$'), support))
    
    # Submit Proof Conversation
    proof_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'^📤 Submit Proof$'), submit_proof)],
        states={
            PROOF_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, proof_link),
                CallbackQueryHandler(cancel_proof_callback, pattern="^cancel_proof$")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        per_message=False
    )
    
    # Withdraw Conversation
    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'^💸 Withdraw$'), withdraw)],
        states={
            WD_METHOD: [CallbackQueryHandler(wd_method, pattern="^(upi|vsv|fxl|cancel)$")],
            WD_DETAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, wd_detail)],
            WD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, wd_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        per_message=False
    )
    
    # Add Balance Conversation
    add_bal_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'^➕ Add Balance$'), add_balance)],
        states={
            ADD_BAL_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_bal_user)],
            ADD_BAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_bal_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        per_message=False
    )
    
    # Remove Balance Conversation
    rem_bal_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'^➖ Remove Balance$'), remove_balance)],
        states={
            REM_BAL_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, rem_bal_user)],
            REM_BAL_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rem_bal_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        per_message=False
    )
    
    # Add Verified IDs Conversation
    ver_ids_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex(r'^📋 Add Verified IDs$'), add_verified_ids)],
        states={
            ADD_VER_IDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_ver_ids)],
            VER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ver_amount)]
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        per_message=False
    )
    
    # Add all conversation handlers
    app.add_handler(proof_conv)
    app.add_handler(withdraw_conv)
    app.add_handler(add_bal_conv)
    app.add_handler(rem_bal_conv)
    app.add_handler(ver_ids_conv)
    
    # Admin menu handlers
    admin_handlers = [
        ("👥 Total Users", total_users),
        ("📊 User Details", user_details),
        ("📜 Proof History", proof_history),
        ("🔧 View Verified IDs", view_verified_ids),
        ("🏠 Main Menu", start)
    ]
    
    for text, handler in admin_handlers:
        app.add_handler(MessageHandler(filters.TEXT & filters.Regex(f'^{text}$'), handler))
    
    print("✅ All handlers registered successfully!")
    print("=" * 50)
    print("🏃 Bot is running...")
    print("=" * 50)
    print("📝 Commands available:")
    print("   • /start - Start the bot")
    print("   • /admin - Admin panel")
    print("   • /cancel - Cancel current operation")
    print("=" * 50)
    
    try:
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot crashed with error: {e}")
        import traceback
        traceback.print_exc()
        print("🔄 Restarting in 5 seconds...")
        time.sleep(5)
        main()

if __name__ == "__main__":
    main()
