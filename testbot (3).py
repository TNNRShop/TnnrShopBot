import telebot
import random
import os
import re  
from telebot import types

# 1. BOT SETUP & CONFIGURATION
BOT_TOKEN = "8644664816:AAH9yTil0KsFETrguw7WX2gYrMv-0VBUTUs"
bot = telebot.TeleBot(BOT_TOKEN)

OWNER_ID = 6531314640
EXTRA_ADMIN = 8650959684
ADMINS = [OWNER_ID, EXTRA_ADMIN]

LOG_GROUP_ID = -5406849696
INVENTORY_FILE = "inventory.txt"

giveaway_data = {
    "active": False,
    "prize_name": "",
    "ticket_price": 0,
    "prize_amount": 1,     
    "group_chat_id": None, 
    "tickets": {},        
    "usernames": {},      
    "is_admin_ticket": {} 
}

def safe_log(text):
    try:
        bot.send_message(LOG_GROUP_ID, text, parse_mode="Markdown")
    except Exception:
        pass  

def get_multiple_rewards(amount):
    if not os.path.exists(INVENTORY_FILE):
        return []
    
    with open(INVENTORY_FILE, "r") as f:
        lines = f.readlines()
        
    if not lines or len(lines) < amount:
        return [] 
    
    rewards = [line.strip() for line in lines[:amount]]
    
    with open(INVENTORY_FILE, "w") as f:
        f.writelines(lines[amount:])
        
    return rewards

# 2. ADMIN COMMAND: START GIVEAWAY
@bot.message_handler(commands=['startgiveaway'])
def start_giveaway(message):
    if message.chat.type == "private":
        return bot.reply_to(message, "❌ This command must be executed inside your Telegram Group Chat.")

    if message.from_user.id not in ADMINS:
        return bot.reply_to(message, "❌ Access Denied. Admins only.")
    
    text_content = message.text.strip()
    if ' ' in text_content:
        args = text_content.split(' ', 1)[1].strip()
    else:
        return bot.reply_to(message, "❌ Invalid format. Use: `/startgiveaway Prize Name | Price | Amount accounts`")

    if args.count('|') < 2:
        return bot.reply_to(message, "❌ Invalid format. Example: `/startgiveaway 18k Coin Account | 15 | 2 accounts`")
    
    try:
        prize_part, price_part, amount_part = args.split('|', 2)
        prize = prize_part.strip()
        price = int(price_part.strip())
        
        amount_digits = re.findall(r'\d+', amount_part)
        if not amount_digits:
            return bot.reply_to(message, "❌ Quantity not found. Example: `2 accounts`")
        
        amount = int(amount_digits[0])
        
        if amount <= 0:
            return bot.reply_to(message, "❌ Quantity must be greater than 0.")
            
        giveaway_data["active"] = True
        giveaway_data["prize_name"] = prize
        giveaway_data["ticket_price"] = price
        giveaway_data["prize_amount"] = amount
        giveaway_data["group_chat_id"] = message.chat.id 
        giveaway_data["tickets"] = {}
        giveaway_data["usernames"] = {}
        giveaway_data["is_admin_ticket"] = {}
        
        bot_username = bot.get_me().username
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎫 BUY TICKET VIA PM", url=f"t.me/{bot_username}?start=buy"))

        success_msg = (
            f"🎉 **NEW LUCKY DRAW STARTED!** 🎉\n\n"
            f"🎁 **Prize:** {prize}\n"
            f"📦 **Quantity:** {amount} Accounts\n"
            f"💰 **Ticket Price:** {price} Stars\n\n"
            f"👇 Click the button below to purchase tickets privately via DM to avoid group spam!"
        )
        bot.send_message(message.chat.id, success_msg, parse_mode="Markdown", reply_markup=markup)
        
        safe_log(f"📢 [LOG] Giveaway started by Admin. Prize: {prize} ({amount}x)")
    except ValueError:
        bot.reply_to(message, "❌ Invalid input. Please ensure Price and Quantity are valid numbers.")
    except Exception as e:
        bot.reply_to(message, f"❌ System Error: {str(e)}")

# 3. USER COMMAND: BUY TICKET (WITH STARS INVOICE GENERATOR)
@bot.message_handler(commands=['buyticket'])
def buy_ticket(message):
    if message.chat.type != "private":
        try:
            bot.delete_message(message.chat.id, message.message_id) 
        except:
            pass
        return bot.send_message(message.from_user.id, "❌ Do not send commands in the group chat. Send `/buyticket` directly here in my DMs.")

    if not giveaway_data["active"]:
        return bot.reply_to(message, "❌ There is no active lucky draw running at the moment.")
    
    try:
        text_content = message.text.strip()
        parts = text_content.split()
        count = int(parts[1]) if len(parts) > 1 else 1
        if count <= 0: raise ValueError
    except:
        return bot.reply_to(message, "❌ Invalid format. Example: `/buyticket 2` to purchase multiple tickets.")
    
    user_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else message.from_user.first_name
    
    # FOR ADMINS: Instantly entered for free (Admin Perks)
    if user_id in ADMINS:
        giveaway_data["tickets"][user_id] = giveaway_data["tickets"].get(user_id, 0) + count
        giveaway_data["usernames"][user_id] = username
        giveaway_data["is_admin_ticket"][user_id] = True
        
        bot.reply_to(message, f"✅ [ADMIN PERK] Successfully credited {count} free ticket(s) to your balance!")
        safe_log(f"👑 [ADMIN ENTRY] @{username} registered {count} free ticket(s).")
        return

    # FOR REGULAR USES: Generate Official Telegram Stars Invoice
    total_cost = count * giveaway_data["ticket_price"]
    
    prices = [types.LabeledPrice(label=f"{count} Ticket(s)", amount=total_cost)]
    
    try:
        bot.send_invoice(
            chat_id=user_id,
            title="🎟️ Lucky Draw Ticket Purchase",
            description=f"Purchase {count} ticket(s) for the {giveaway_data['prize_name']} draw.",
            invoice_payload=f"buy_tickets_{count}_{user_id}", # Saves ticket count and user info inside payload
            provider_token="", # Must remain empty ('') for Telegram Stars payments
            currency="XTR",    # XTR stands for Telegram Stars
            prices=prices,
            start_parameter="lucky-draw"
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Failed to generate checkout invoice: {str(e)}")

# 4. STARS PAYMENT CHECKOUT HANDLERS (ANTI-CHEAT)
@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    # Auto-approve the payment window when verification data matches
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def payment_success_catch(message):
    # Tickets are credited only after a fully verified and successful payment
    payload = message.successful_payment.invoice_payload
    
    if payload.startswith("buy_tickets_"):
        parts = payload.split("_")
        count = int(parts[2])
        user_id = int(parts[3])
        username = message.from_user.username if message.from_user.username else message.from_user.first_name
        
        giveaway_data["tickets"][user_id] = giveaway_data["tickets"].get(user_id, 0) + count
        giveaway_data["usernames"][user_id] = username
        giveaway_data["is_admin_ticket"][user_id] = False
        
        success_txt = (
            f"🌟 **PAYMENT CONFIRMED!** 🌟\n\n"
            f"✅ Successfully credited {count} ticket(s) to your balance!\n"
            f"🎁 Current Pool: {giveaway_data['prize_name']}\n\n"
            f"Type `/stats` to view your updated winning probability."
        )
        bot.send_message(user_id, success_txt, parse_mode="Markdown")
        
        safe_log(
            f"💰 **[SUCCESSFUL PAYMENT RECEIVED]**\n"
            f"👤 User: @{username} (`{user_id}`)\n"
            f"🎟️ Tickets Paid: {count}\n"
            f"💎 Total Stars Sent: {message.successful_payment.total_amount} Stars"
        )

# 5. STATS VIEW COMMAND
@bot.message_handler(commands=['stats'])
def show_stats(message):
    if not giveaway_data["active"]:
        return bot.reply_to(message, "❌ There is no active lucky draw running right now.")
    
    total_tickets = sum(giveaway_data["tickets"].values())
    unique_users = len(giveaway_data["tickets"])
    
    total_stars = sum(
        count * giveaway_data["ticket_price"] 
        for uid, count in giveaway_data["tickets"].items() 
        if not giveaway_data["is_admin_ticket"].get(uid, False)
    )
    
    text = f"📊 **Current Lucky Draw Status** – {giveaway_data['prize_name']} ({giveaway_data['prize_amount']}x)\n\n"
    text += f"🎟️ **Total Tickets Issued:** {total_tickets}\n"
    text += f"👥 **Unique Entrants:** {unique_users}\n"
    text += f"⭐ **Total Stars Collected:** {total_stars}\n\n"
    text += "🏅 **Top Contenders:**\n"
    
    sorted_users = sorted(giveaway_data["tickets"].items(), key=lambda x: x[1], reverse=True)
    
    for user_id, ticket_count in sorted_users[:5]:
        uname = giveaway_data["usernames"].get(user_id, "Unknown")
        percentage = (ticket_count / total_tickets) * 100 if total_tickets > 0 else 0
        text += f"• @{uname}: {ticket_count} ticket(s) ({percentage:.1f}% chance)\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# 6. ADMIN COMMAND: DRAW WINNER
@bot.message_handler(commands=['draw'])
def draw_winner(message):
    if message.from_user.id not in ADMINS:
        return
        
    if not giveaway_data["active"]:
        return bot.reply_to(message, "❌ There is no active pool available to draw from.")
        
    total_tickets = sum(giveaway_data["tickets"].values())
    if total_tickets == 0:
        return bot.reply_to(message, "❌ Cannot execute draw. No valid paid entries found.")
        
    needed_accounts = giveaway_data["prize_amount"]
    
    reward_list = get_multiple_rewards(needed_accounts)
    if not reward_list:
        return bot.reply_to(
            message, 
            f"🚨 [ERROR] Insufficient stock in `inventory.txt`!\n"
            f"Required: {needed_accounts} accounts, but inventory list is short."
        )

    ticket_pool = []
    for user_id, count in giveaway_data["tickets"].items():
        ticket_pool.extend([user_id] * count)
        
    winners_announcement = f"🏁 **THE LUCKY DRAW POOL HAS OFFICIALLY ENDED!** 🏁\n\n📢 **Official Winners:**\n"
    
    for i in range(needed_accounts):
        winner_id = random.choice(ticket_pool)
        winner_username = giveaway_data["usernames"].get(winner_id, "Unknown")
        current_account = reward_list[i]
        
        winners_announcement += f"🏆 **Winner {i+1}:** @{winner_username} → ({giveaway_data['prize_name']})\n"
        
        try:
            dm_text = (
                f"🎁 **Congratulations! You have won the Lucky Draw!** 🎁\n\n"
                f"📌 **Prize:** {giveaway_data['prize_name']}\n\n"
                f"🔐 **Account Credentials:**\n`{current_account}`\n\n"
                f"*Thank you for your entry and support!*"
            )
            bot.send_message(winner_id, dm_text, parse_mode="Markdown")
            dm_status = "✅ Dispatched"
        except Exception:
            dm_status = "❌ DM Blocked"
            safe_log(f"⚠️ [MANUAL DISPATCH REQUIRED] Failed to DM @{winner_username}. Credentials: `{current_account}`")

        safe_log(f"🏅 Draw Result {i+1}/{needed_accounts}: @{winner_username} -> {dm_status}")

    winners_announcement += "\n📬 All prizes have been automatically dispatched to the winners' Direct Messages. Please verify your inboxes!"
    
    bot.send_message(giveaway_data["group_chat_id"], winners_announcement, parse_mode="Markdown")
    giveaway_data["active"] = False

bot.infinity_polling()
