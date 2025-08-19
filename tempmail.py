# Author (C) @patelmilan07
# Channel : https://t.me/mpx7ai
# Full script: debugged & hardened

import re
import time
import random
import string
import hashlib
import sqlite3
import asyncio
import requests
import logging
from bs4 import BeautifulSoup
from pyrogram.enums import ParseMode, ChatType, ChatMemberStatus
from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup
from pyrogram import StopPropagation

# ===== CONFIGURATION =====
API_ID = "24082016"
API_HASH = "81af1b2969f06110e0901aa41bfb932d"
BOT_TOKEN = "8310630920:AAFa9w_D-1_iOeFbpbYShNO3vAWKxaL69kI"  # Replace with your actual BOT_TOKEN
DATABASE_NAME = "bot_database.db"
OWNER_ID = 5524867269  # REPLACE WITH YOUR TELEGRAM USER ID
REQUIRED_CHANNEL = "mpx7ai"  # channel username without @
# ========================

# ===== LOGGING =====
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("temp_mail_bot")

# ===== BOT CLIENT =====
bot = Client(
    "bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=100,
    parse_mode=ParseMode.MARKDOWN
)

# ===== GLOBALS =====
token_map = {}
user_tokens = {}
user_last_messages = {}
MAX_MESSAGE_LENGTH = 4000
BASE_URL = "https://api.mail.tm"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

# ===== DB INIT =====
def init_database():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                admin_id INTEGER PRIMARY KEY
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                banned INTEGER DEFAULT 0
            )
        ''')
        # ensure owner is admin
        cursor.execute("INSERT OR IGNORE INTO admins (admin_id) VALUES (?)", (OWNER_ID,))
        conn.commit()
        logger.info("Database initialized OK")
    except Exception as e:
        logger.exception(f"init_database error: {e}")
    finally:
        try:
            conn.close()
        except:
            pass

# ===== DB HELPERS =====
def is_admin(user_id:int)->bool:
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM admins WHERE admin_id = ?", (user_id,))
        return cur.fetchone() is not None
    except Exception as e:
        logger.exception(f"is_admin error: {e}")
        return False
    finally:
        try: conn.close()
        except: pass

def add_admin(admin_id:int)->bool:
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO admins (admin_id) VALUES (?)", (admin_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.exception(f"add_admin error: {e}")
        return False
    finally:
        try: conn.close()
        except: pass

def remove_admin(admin_id:int)->bool:
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM admins WHERE admin_id = ?", (admin_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.exception(f"remove_admin error: {e}")
        return False
    finally:
        try: conn.close()
        except: pass

def add_user(user_id:int)->bool:
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.exception(f"add_user error: {e}")
        return False
    finally:
        try: conn.close()
        except: pass

def get_all_users():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        return [r[0] for r in cur.fetchall()]
    except Exception as e:
        logger.exception(f"get_all_users error: {e}")
        return []
    finally:
        try: conn.close()
        except: pass

def get_all_admins():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("SELECT admin_id FROM admins")
        return [r[0] for r in cur.fetchall()]
    except Exception as e:
        logger.exception(f"get_all_admins error: {e}")
        return []
    finally:
        try: conn.close()
        except: pass

def get_user_count()->int:
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0]
    except Exception as e:
        logger.exception(f"get_user_count error: {e}")
        return 0
    finally:
        try: conn.close()
        except: pass

def get_admin_count()->int:
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM admins")
        return cur.fetchone()[0]
    except Exception as e:
        logger.exception(f"get_admin_count error: {e}")
        return 0
    finally:
        try: conn.close()
        except: pass

def is_banned(user_id:int)->bool:
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("SELECT banned FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return bool(row and row[0] == 1)
    except Exception as e:
        logger.exception(f"is_banned error: {e}")
        return False
    finally:
        try: conn.close()
        except: pass

def ban_user(user_id:int)->bool:
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.exception(f"ban_user error: {e}")
        return False
    finally:
        try: conn.close()
        except: pass

def unban_user(user_id:int)->bool:
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        logger.exception(f"unban_user error: {e}")
        return False
    finally:
        try: conn.close()
        except: pass

def get_banned_count()->int:
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
        return cur.fetchone()[0]
    except Exception as e:
        logger.exception(f"get_banned_count error: {e}")
        return 0
    finally:
        try: conn.close()
        except: pass

# ===== FILTERS =====
def admin_filter(_, __, message):
    try:
        return is_admin(message.from_user.id)
    except Exception as e:
        logger.exception(f"admin_filter error: {e}")
        return False

admin_only = filters.create(admin_filter)

def ban_filter(_, __, message):
    try:
        return not is_banned(message.from_user.id)
    except Exception as e:
        logger.exception(f"ban_filter error: {e}")
        return False

active_user = filters.create(ban_filter)

# ===== FORCE CHANNEL JOIN =====
async def has_joined_channel(user_id:int)->bool:
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        logger.debug(f"Channel member status for {user_id}: {member.status}")
        return member.status not in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]
    except Exception as e:
        logger.error(f"Error checking channel membership for {user_id}: {e}")
        # On error, allow (or you can return False to enforce)
        return True

def get_join_message():
    return (
        "📢 **Channel Join Required**\n\n"
        f"To use this bot, you must join our official channel:\n➡️ @{REQUIRED_CHANNEL}\n\n"
        "Join karne ke baad **/start** dabao."
    )

@bot.on_message(filters.private & ~filters.bot, group=-1)
async def force_join_check(client, message):
    try:
        user_id = message.from_user.id
        if is_admin(user_id):
            return
        if not await has_joined_channel(user_id):
            await message.reply(get_join_message(), disable_web_page_preview=True)
            raise StopPropagation
    except StopPropagation:
        raise
    except Exception as e:
        logger.exception(f"force_join_check error: {e}")

# ===== HELPERS =====
def short_id_generator(email):
    unique_string = email + str(time.time())
    return hashlib.md5(unique_string.encode()).hexdigest()[:10]

def generate_random_username(length=8):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_domain():
    try:
        response = requests.get(f"{BASE_URL}/domains", headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        domain = None
        if isinstance(data, list) and data:
            domain = data[0].get('domain')
        elif isinstance(data, dict) and data.get('hydra:member'):
            domain = data['hydra:member'][0].get('domain')
        logger.debug(f"Selected domain: {domain}")
        return domain
    except Exception as e:
        logger.exception(f"get_domain error: {e}")
        return None

def create_account(email, password):
    data = {"address": email, "password": password}
    try:
        response = requests.post(f"{BASE_URL}/accounts", headers=HEADERS, json=data, timeout=20)
        logger.debug(f"create_account status: {response.status_code} body: {response.text[:300]}")
        if response.status_code in [200, 201]:
            return response.json()
        return None
    except Exception as e:
        logger.exception(f"create_account error: {e}")
        return None

def get_token(email, password):
    data = {"address": email, "password": password}
    try:
        response = requests.post(f"{BASE_URL}/token", headers=HEADERS, json=data, timeout=20)
        logger.debug(f"get_token status: {response.status_code} body: {response.text[:300]}")
        if response.status_code == 200:
            return response.json().get('token')
        return None
    except Exception as e:
        logger.exception(f"get_token error: {e}")
        return None

def get_text_from_html(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            url = a_tag['href']
            a_tag.replace_with(f"{a_tag.text} [{url}]")
        for img_tag in soup.find_all('img'):
            if img_tag.get('src'):
                img_tag.replace_with(f"[Image: {img_tag.get('src')}]")
        text = soup.get_text()
        cleaned = re.sub(r'\s+', ' ', text).strip()
        return cleaned
    except Exception as e:
        logger.exception(f"get_text_from_html error: {e}")
        return html_content if isinstance(html_content, str) else "No content"

def list_messages(token):
    headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/messages", headers=headers, timeout=20)
        logger.debug(f"list_messages status: {response.status_code} body: {response.text[:300]}")
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and data.get('hydra:member'):
            return data['hydra:member']
        return []
    except Exception as e:
        logger.exception(f"list_messages error: {e}")
        return []

# ===== KEYBOARDS =====
def get_user_panel():
    return ReplyKeyboardMarkup(
        [["Generate Temp Mail"], ["Check My Inbox"], ["Help / Support"]],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_admin_panel():
    return ReplyKeyboardMarkup(
        [
            ["Generate Temp Mail", "Check My Inbox"],
            ["Admin Panel", "Bot Stats"],
            ["Help / Support"]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_admin_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["Add Admin", "Remove Admin"],
            ["Ban User", "Unban User"],
            ["Broadcast", "Stats"],
            ["Admin List", "Main Menu"]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

# ===== BASIC CMDS =====
@bot.on_message(filters.command(['id']) & active_user)
async def cmd_id(client, message):
    await message.reply(f"🆔 Your ID: `{message.from_user.id}`")

@bot.on_message(filters.command(['ping']) & active_user)
async def cmd_ping(client, message):
    t1 = time.time()
    m = await message.reply("🏓 Pinging...")
    dt = (time.time() - t1) * 1000
    await m.edit(f"🏓 Pong! `{int(dt)}ms`")

@bot.on_message(filters.command(['debug']) & admin_only & active_user)
async def cmd_debug(client, message):
    try:
        me = await bot.get_me()
        text = (
            "**🔧 Debug Info**\n"
            f"• Bot: `{me.username}`\n"
            f"• Bot ID: `{me.id}`\n"
            f"• Channel: `@{REQUIRED_CHANNEL}`\n"
            f"• Users: `{get_user_count()}` | Admins: `{get_admin_count()}` | Banned: `{get_banned_count()}`\n"
        )
        await message.reply(text)
    except Exception as e:
        logger.exception(f"/debug error: {e}")
        await message.reply(f"Error: `{e}`")

# ===== ADMIN COMMANDS =====
@bot.on_message(filters.command("admin") & admin_only & active_user)
async def admin_panel(client, message):
    try:
        admin_count = get_admin_count()
        user_count = get_user_count()
        admin_menu = (
            "**👑 Admin Control Panel**\n\n"
            f"**Current Admins:** `{admin_count}`\n"
            f"**Total Users:** `{user_count}`\n"
            f"**Banned Users:** `{get_banned_count()}`"
        )
        await message.reply(admin_menu, reply_markup=get_admin_menu_keyboard())
    except Exception as e:
        logger.exception(f"/admin error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.regex("^Add Admin$") & admin_only & active_user)
async def add_admin_prompt(client, message):
    await message.reply("**👑 Add Admin**\n\nSend: `/addadmin 123456789`")

@bot.on_message(filters.regex("^Remove Admin$") & admin_only & active_user)
async def remove_admin_prompt(client, message):
    await message.reply("**👑 Remove Admin**\n\nSend: `/removeadmin 123456789`")

@bot.on_message(filters.regex("^Ban User$") & admin_only & active_user)
async def ban_user_prompt(client, message):
    await message.reply("**🔨 Ban User**\n\nSend: `/ban 123456789`")

@bot.on_message(filters.regex("^Unban User$") & admin_only & active_user)
async def unban_user_prompt(client, message):
    await message.reply("**🔓 Unban User**\n\nSend: `/unban 123456789`")

@bot.on_message(filters.regex("^Broadcast$") & admin_only & active_user)
async def broadcast_prompt(client, message):
    await message.reply("**📢 Broadcast**\n\nSend: `/broadcast Your message here`")

@bot.on_message(filters.regex("^Stats$") & admin_only & active_user)
async def stats_button(client, message):
    await show_stats(client, message)

@bot.on_message(filters.regex("^Admin List$") & admin_only & active_user)
async def list_admins_callback(client, message):
    await list_admins(client, message)

@bot.on_message(filters.regex("^Main Menu$") & active_user)
async def back_to_main(client, message):
    await start(client, message)

@bot.on_message(filters.command("addadmin") & admin_only & active_user)
async def add_admin_command(client, message):
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply("**Usage:** `/addadmin [user_id]`")
            return
        new_admin = int(args[1])
        if new_admin == message.from_user.id:
            await message.reply("⚠️ You cannot add yourself!")
            return
        if is_admin(new_admin):
            await message.reply("⚠️ User is already an admin!")
            return
        if add_admin(new_admin):
            await message.reply(f"✅ Added `{new_admin}` as admin")
        else:
            await message.reply("⚠️ Failed to add admin")
    except Exception as e:
        logger.exception(f"add_admin_command error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.command("removeadmin") & admin_only & active_user)
async def remove_admin_command(client, message):
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply("**Usage:** `/removeadmin [user_id]`")
            return
        admin_id = int(args[1])
        if admin_id == OWNER_ID:
            await message.reply("⚠️ You cannot remove the owner!")
            return
        if admin_id == message.from_user.id:
            await message.reply("⚠️ You cannot remove yourself!")
            return
        if not is_admin(admin_id):
            await message.reply("⚠️ User is not an admin!")
            return
        if remove_admin(admin_id):
            await message.reply(f"✅ Removed `{admin_id}` from admins")
        else:
            await message.reply("⚠️ Failed to remove admin")
    except Exception as e:
        logger.exception(f"remove_admin_command error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.command("ban") & admin_only & active_user)
async def ban_user_command(client, message):
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply("**Usage:** `/ban [user_id]`")
            return
        user_id = int(args[1])
        if user_id == OWNER_ID:
            await message.reply("⚠️ You cannot ban the owner!")
            return
        if is_admin(user_id):
            await message.reply("⚠️ You cannot ban an admin!")
            return
        if ban_user(user_id):
            await message.reply(f"✅ Banned `{user_id}`")
        else:
            await message.reply("⚠️ User not found or already banned")
    except Exception as e:
        logger.exception(f"ban_user_command error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.command("unban") & admin_only & active_user)
async def unban_user_command(client, message):
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply("**Usage:** `/unban [user_id]`")
            return
        user_id = int(args[1])
        if unban_user(user_id):
            await message.reply(f"✅ Unbanned `{user_id}`")
        else:
            await message.reply("⚠️ User not found or not banned")
    except Exception as e:
        logger.exception(f"unban_user_command error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.command("broadcast") & admin_only & active_user)
async def broadcast_message(client, message):
    try:
        if len(message.text.split()) < 2:
            await message.reply("**Usage:** `/broadcast [your message]`")
            return
        broadcast_text = message.text.split(maxsplit=1)[1]
        users = get_all_users()
        total = len(users)
        if total == 0:
            await message.reply("❌ No users to broadcast to!")
            return
        progress = await message.reply(f"📢 **Broadcast started...**\n0/{total} users")
        success = 0
        failed = 0
        for user_id in users:
            if is_banned(user_id):
                failed += 1
                continue
            try:
                await bot.send_message(user_id, broadcast_text)
                success += 1
            except Exception as e:
                logger.error(f"Broadcast to {user_id} failed: {e}")
                failed += 1
            if (success + failed) % 10 == 0:
                await progress.edit(f"📢 **Broadcasting...**\n{success + failed}/{total} users\n✅ {success} | ❌ {failed}")
            await asyncio.sleep(0.08)
        await progress.edit(f"📢 **Broadcast Completed!**\n\n• ✅ Success: `{success}`\n• ❌ Failed: `{failed}`\n• 📊 Total: `{total}`")
    except Exception as e:
        logger.exception(f"broadcast_message error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.command("stats") & admin_only & active_user)
async def show_stats(client, message):
    try:
        user_count = get_user_count()
        admin_count = get_admin_count()
        banned_count = get_banned_count()
        active_sessions = len(token_map)
        stats_msg = (
            "📊 **Bot Statistics**\n\n"
            f"• 👥 Total Users: `{user_count}`\n"
            f"• 👑 Admins: `{admin_count}`\n"
            f"• 🔨 Banned Users: `{banned_count}`\n"
            f"• 📧 Active Sessions: `{active_sessions}`"
        )
        await message.reply(stats_msg)
    except Exception as e:
        logger.exception(f"show_stats error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.command("listadmins") & admin_only & active_user)
async def list_admins(client, message):
    try:
        admins = get_all_admins()
        if not admins:
            await message.reply("❌ No admins found!")
            return
        admin_list = "\n".join([f"• `{admin_id}`" for admin_id in admins])
        await message.reply(f"👑 **Admin List:**\n\n{admin_list}")
    except Exception as e:
        logger.exception(f"list_admins error: {e}")
        await message.reply(f"Error: `{e}`")

# ===== USER COMMANDS =====
@bot.on_message(filters.command('start') & active_user)
async def start(client, message):
    try:
        if message.chat.type != ChatType.PRIVATE:
            await message.reply("**🔒 Please use me in private chats only!**")
            return
        user_id = message.from_user.id
        add_user(user_id)
        welcome = (
            "**🌟 Welcome to Smart Temp Mail Bot!**\n\n"
            "Create temporary email addresses instantly with these options:"
        )
        if is_admin(user_id):
            await message.reply(welcome, reply_markup=get_admin_panel())
        else:
            await message.reply(welcome, reply_markup=get_user_panel())
    except Exception as e:
        logger.exception(f"/start error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.regex("^Generate Temp Mail$") & active_user)
async def generate_mail_button(client, message):
    await generate_mail(client, message)

@bot.on_message(filters.regex("^Check My Inbox$") & active_user)
async def check_mail_button(client, message):
    await message.reply("🔑 **Check Inbox**\n\nSend: `/cmail YOUR_TOKEN`")

@bot.on_message(filters.regex("^Help / Support$") & active_user)
async def help_button(client, message):
    await help_command(client, message)

@bot.on_message(filters.regex("^Admin Panel$") & admin_only & active_user)
async def admin_panel_button(client, message):
    await admin_panel(client, message)

@bot.on_message(filters.regex("^Bot Stats$") & admin_only & active_user)
async def stats_button2(client, message):
    await show_stats(client, message)

@bot.on_message(filters.command('help') & active_user)
async def help_command(client, message):
    try:
        help_text = (
            "**❓ Help Guide**\n\n"
            "**For All Users:**\n"
            "• /tmail - Create new temporary email\n"
            "• /cmail [TOKEN] - Check your inbox\n"
            "• /help - Show this help message\n"
            "• /id - Show your Telegram ID\n"
            "• /ping - Ping\n\n"
            "**For Admins:**\n"
            "• /admin - Admin control panel\n"
            "• /addadmin [ID] - Add new admin\n"
            "• /removeadmin [ID] - Remove admin\n"
            "• /ban [ID] - Ban user\n"
            "• /unban [ID] - Unban user\n"
            "• /broadcast [MSG] - Broadcast message\n"
            "• /stats - Bot statistics\n"
            "• /debug - Debug info\n\n"
            "**Note:** Private chat only."
        )
        await message.reply(help_text)
    except Exception as e:
        logger.exception(f"/help error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.command('tmail') & active_user)
async def generate_mail(client, message):
    try:
        if message.chat.type != ChatType.PRIVATE:
            await message.reply("**🔒 Please use me in private chats only!**")
            return
        loading = await message.reply("**🔄 Creating your temporary email...**")
        args = message.text.split()
        if len(args) > 1 and ':' in args[1]:
            username, password = args[1].split(':', 1)
        else:
            username = generate_random_username()
            password = generate_random_password()

        domain = get_domain()
        if not domain:
            await loading.edit("**❌ Failed to get domain. Try again later.**")
            return

        email = f"{username}@{domain}"
        account = create_account(email, password)
        if not account:
            await loading.edit("**⚠️ Username already taken or API error. Try again.**")
            return

        token = get_token(email, password)
        if not token:
            await loading.edit("**❌ Failed to create account token. Try again.**")
            return

        short_id = short_id_generator(email)
        token_map[short_id] = token

        msg = (
            "**📬 Smart Email Created Successfully!**\n\n"
            f"**📧 Email:** `{email}`\n"
            f"**🔑 Password:** `{password}`\n"
            f"**🔒 Token:** `{token}`\n\n"
            "⚠️ **Note**: Use token with `/cmail` to check your inbox."
        )
        await loading.delete()
        await message.reply(msg)
    except Exception as e:
        logger.exception(f"/tmail error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.command('cmail') & active_user)
async def check_mail_cmd(client, message):
    try:
        if message.chat.type != ChatType.PRIVATE:
            await message.reply("**🔒 Please use me in private chats only!**")
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("**❌ Please provide your token!**\nExample: `/cmail YOUR_TOKEN`")
            return
        token = args[1].strip()
        user_tokens[message.from_user.id] = token
        messages = list_messages(token)
        if not messages:
            await message.reply("**📭 No emails found!**")
            return
        user_last_messages[message.from_user.id] = messages
        text = "**📥 Your Recent Emails:**\n\n"
        for idx, msg in enumerate(messages[:10], 1):
            frm = (msg.get('from') or {}).get('address') or "Unknown"
            subj = msg.get('subject') or "(no subject)"
            text += f"{idx}. **From:** `{frm}`\n   **Subject:** {subj}\n\n"
        text += "\nTo read an email, send:\n`/read EMAIL_NUMBER`\nExample: `/read 1`"
        await message.reply(text)
    except Exception as e:
        logger.exception(f"/cmail error: {e}")
        await message.reply(f"Error: `{e}`")

@bot.on_message(filters.command('read') & active_user)
async def read_email_command(client, message):
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.reply("**❌ Please provide an email number!**\nExample: `/read 1`")
            return
        index = int(args[1])
        messages = user_last_messages.get(message.from_user.id)
        if not messages:
            await message.reply("❌ No inbox data available. Please check your inbox first.")
            return
        if index < 1 or index > len(messages):
            await message.reply(f"❌ Invalid email number. Choose between 1-{len(messages)}")
            return
        msg = messages[index-1]
        token = user_tokens.get(message.from_user.id)
        if not token:
            await message.reply("❌ Token missing! Please check your inbox again.")
            return
        headers = {**HEADERS, "Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/messages/{msg.get('id')}", headers=headers, timeout=20)
        logger.debug(f"read_email status: {resp.status_code} body: {resp.text[:300]}")
        if resp.status_code != 200:
            await message.reply("❌ Failed to fetch email content")
            return
        email = resp.json()
        content = email.get('html', []) or email.get('text', '')
        if isinstance(content, list):
            content = ''.join(content)
        text_content = get_text_from_html(content) if content else "No content available"
        if len(text_content) > MAX_MESSAGE_LENGTH:
            text_content = text_content[:MAX_MESSAGE_LENGTH] + "... [truncated]"
        frm = ((email.get('from') or {}).get('address')) or "Unknown"
        subj = email.get('subject') or "(no subject)"
        created = email.get('createdAt') or "Unknown"
        msg_text = (
            f"**✉️ From:** `{frm}`\n"
            f"**📌 Subject:** `{subj}`\n"
            f"**📅 Date:** `{created}`\n\n"
            f"{text_content}"
        )
        await message.reply(msg_text)
    except ValueError:
        await message.reply("❌ Please enter a valid number")
    except Exception as e:
        logger.exception(f"/read error: {e}")
        await message.reply(f"❌ **Error:** `{e}`")

# ===== BANNED USER HANDLER =====
@bot.on_message(filters.private & ~active_user)
async def banned_user_handler(client, message):
    try:
        await message.reply("⛔ **Account Suspended**\n\nIf this is a mistake, contact admin.")
    except Exception as e:
        logger.exception(f"banned_user_handler error: {e}")

# ===== STARTUP HEALTH CHECKS =====
def telegram_get_me_check():
    try:
        r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=15)
        logger.info(f"Telegram getMe: {r.status_code} {r.text[:200]}")
    except Exception as e:
        logger.exception(f"telegram_get_me_check error: {e}")

def channel_access_check():
    try:
        # Fire and forget during runtime as we need bot loop
        logger.info(f"Channel required: @{REQUIRED_CHANNEL} (ensure bot is admin there)")
    except Exception as e:
        logger.exception(f"channel_access_check error: {e}")

# ===== MAIN =====
if __name__ == "__main__":
    init_database()
    if not is_admin(OWNER_ID):
        add_admin(OWNER_ID)

    logger.info("🚀 Bot starting...")
    logger.info(f"Owner ID: {OWNER_ID}")
    logger.info(f"Database: {DATABASE_NAME}")
    logger.info(f"Force Join Channel: @{REQUIRED_CHANNEL}")

    telegram_get_me_check()
    channel_access_check()

    bot.run()