import asyncio
import json
import logging
import os
import datetime
import discord
from discord.ext import commands
from fastapi import FastAPI
from uvicorn import Config, Server
from utils.database import db
from utils.ui import PremiumEmbed

# ---------------------------------------------------------------------------- #
#                                LOGGING SETUP                                 #
# ---------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("System")

# ---------------------------------------------------------------------------- #
#                                CONFIGURATION                                 #
# ---------------------------------------------------------------------------- #
CONFIG_PATH = "config.json"

def load_config():
    config = {}
    # 1. Try to load from file
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            
    # 2. Override/Fallback to Environment Variables (for Render/Cloud)
    if os.environ.get("TOKEN"): config["token"] = os.environ.get("TOKEN")
    if os.environ.get("CLIENT_ID"): config["client_id"] = os.environ.get("CLIENT_ID")
    if os.environ.get("CLIENT_SECRET"): config["client_secret"] = os.environ.get("CLIENT_SECRET")
    if os.environ.get("REDIRECT_URI"): config["redirect_uri"] = os.environ.get("REDIRECT_URI")
    if os.environ.get("OWNER_ID"): config["owner_id"] = os.environ.get("OWNER_ID")
    
    return config

config = load_config()

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import aiohttp

# ---------------------------------------------------------------------------- #
#                               FASTAPI (WEB)                                  #
# ---------------------------------------------------------------------------- #
app = FastAPI(
    title="No.punq Dashboard",
    description="Professional Discord Bot Control Panel",
    version="1.0.0"
)

# Secrets
SECRET_KEY = "super_secret_session_key_change_this"
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Mount Static Files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Setup Templates
templates = Jinja2Templates(directory="web/templates")
from utils.translations import TRANSLATIONS
templates.env.globals['t'] = TRANSLATIONS

API_ENDPOINT = "https://discord.com/api/v10"

@app.get("/")
async def index(request: Request):
    user = request.session.get("user")
    lang = request.session.get("lang", "tr")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "maintenance": config.get("maintenance", False),
        "user": user,
        "lang": lang
    })

@app.get("/set_lang/{lang}")
async def set_lang(request: Request, lang: str):
    if lang in ["tr", "en"]:
        request.session["lang"] = lang
    return RedirectResponse(request.headers.get("referer", "/"))

@app.get("/login")
async def login():
    return RedirectResponse(
        f"{API_ENDPOINT}/oauth2/authorize?client_id={config['client_id']}&redirect_uri={config['redirect_uri']}&response_type=code&scope=identify%20guilds"
    )

@app.get("/callback")
async def callback(request: Request, code: str = None):
    if not code:
        return RedirectResponse("/")
    data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": config["redirect_uri"]
    }
    
    async with aiohttp.ClientSession() as session:
        # Get Token
        async with session.post(f"{API_ENDPOINT}/oauth2/token", data=data) as resp:
            if resp.status != 200:
                return RedirectResponse("/?error=token_failed")
            token_data = await resp.json()
            access_token = token_data["access_token"]
        
        # Get User Info
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(f"{API_ENDPOINT}/users/@me", headers=headers) as resp:
            user_data = await resp.json()
        
        # Save to Session
        request.session["user"] = user_data
        request.session["token"] = access_token
        
    return RedirectResponse("/dashboard")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")

@app.get("/dashboard")
async def dashboard(request: Request):
    user = request.session.get("user")
    token = request.session.get("token")
    
    if not user or not token:
        return RedirectResponse("/login")
    
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_ENDPOINT}/users/@me/guilds", headers=headers) as resp:
            user_guilds = await resp.json()
            
    # Filter Admin Guilds & Check Bot Presence
    final_guilds = []
    bot_guilds = {g.id for g in bot.guilds}
    
    if isinstance(user_guilds, list):
        for g in user_guilds:
            # Check permissions (0x8 = Administrator, 0x20 = Manage Guild)
            perms = int(g["permissions"])
            if (perms & 0x8) == 0x8 or (perms & 0x20) == 0x20:
                g["bot_in"] = int(g["id"]) in bot_guilds
                final_guilds.append(g)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_data": user,
        "guilds": final_guilds,
        "client_id": config["client_id"],
        "lang": request.session.get("lang", "tr")
    })

# ---------------------------------------------------------------------------- #
#                                MANAGE GUILD                                  #
# ---------------------------------------------------------------------------- #

@app.get("/dashboard/{guild_id}")
async def manage_guild(request: Request, guild_id: str):
    user = request.session.get("user")
    token = request.session.get("token")
    
    if not user or not token:
        return RedirectResponse("/login")
        
    # Verify User Permission for this Guild
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_ENDPOINT}/users/@me/guilds", headers=headers) as resp:
            if resp.status != 200:
                return RedirectResponse("/dashboard")
            user_guilds = await resp.json()
            
    target_guild = None
    if isinstance(user_guilds, list):
        for g in user_guilds:
            if g["id"] == guild_id:
                perms = int(g["permissions"])
                if (perms & 0x8) == 0x8 or (perms & 0x20) == 0x20:
                    target_guild = g
                break
            
    if not target_guild:
        return RedirectResponse("/dashboard?error=unauthorized")
        
    # Get Config from DB
    guild_config = await db.get_guild_config(int(guild_id))
    
    return templates.TemplateResponse("manage.html", {
        "request": request,
        "guild": target_guild,
        "config": guild_config,
        "user_data": user,
        "lang": request.session.get("lang", "tr")
    })

@app.post("/dashboard/{guild_id}/moderation")
async def update_moderation(request: Request, guild_id: str):
    user = request.session.get("user")
    if not user: return RedirectResponse("/login")
    
    form = await request.form()
    
    enabled = form.get("enabled") == "on"
    log_channel = form.get("log_channel")
    bad_words_str = form.get("bad_words", "")
    link_protection = form.get("link_protection") == "on"
    spam_protection = form.get("spam_protection") == "on"
    scan_admins = form.get("scan_admins") == "on"
    
    # Process inputs
    try:
        log_channel_id = int(log_channel) if log_channel and log_channel.strip() else None
    except ValueError:
        log_channel_id = None
        
    bad_words = [w.strip() for w in bad_words_str.split(",") if w.strip()]
    
    await db.update_guild_config(int(guild_id), "moderation", "enabled", enabled)
    await db.update_guild_config(int(guild_id), "moderation", "log_channel", log_channel_id)
    await db.update_guild_config(int(guild_id), "moderation", "bad_words", bad_words)
    await db.update_guild_config(int(guild_id), "moderation", "link_protection", link_protection)
    await db.update_guild_config(int(guild_id), "moderation", "spam_protection", spam_protection)
    await db.update_guild_config(int(guild_id), "moderation", "scan_admins", scan_admins)
    
    return RedirectResponse(f"/dashboard/{guild_id}", status_code=303)

@app.post("/dashboard/{guild_id}/welcome")
async def update_welcome(request: Request, guild_id: str):
    user = request.session.get("user")
    if not user: return RedirectResponse("/login")
    
    form = await request.form()
    
    enabled = form.get("enabled") == "on"
    leave_enabled = form.get("leave_enabled") == "on"
    channel_id_str = form.get("channel_id")
    rules_channel_id_str = form.get("rules_channel_id")
    message = form.get("message")
    leave_message = form.get("leave_message")
    member_target_str = form.get("member_target")
    
    channel_id = None
    if channel_id_str and channel_id_str.strip():
        try: channel_id = int(channel_id_str.strip())
        except ValueError: pass

    rules_channel_id = None
    if rules_channel_id_str and rules_channel_id_str.strip():
        try: rules_channel_id = int(rules_channel_id_str.strip())
        except ValueError: pass

    member_target = 100
    if member_target_str and member_target_str.strip():
        try: member_target = int(member_target_str)
        except ValueError: pass
            
    await db.update_guild_config(int(guild_id), "welcome", "enabled", enabled)
    await db.update_guild_config(int(guild_id), "welcome", "leave_enabled", leave_enabled)
    await db.update_guild_config(int(guild_id), "welcome", "channel_id", channel_id)
    await db.update_guild_config(int(guild_id), "welcome", "rules_channel_id", rules_channel_id)
    await db.update_guild_config(int(guild_id), "welcome", "member_target", member_target)
    if message:
        await db.update_guild_config(int(guild_id), "welcome", "message", message)
    if leave_message:
        await db.update_guild_config(int(guild_id), "welcome", "leave_message", leave_message)
    
    return RedirectResponse(f"/dashboard/{guild_id}", status_code=303)

@app.post("/dashboard/{guild_id}/autorole")
async def update_autorole(request: Request, guild_id: str):
    user = request.session.get("user")
    if not user: return RedirectResponse("/login")
    
    form = await request.form()
    enabled = form.get("enabled") == "on"
    role_id_str = form.get("role_id")
    
    role_id = None
    if role_id_str and role_id_str.strip():
        try: role_id = int(role_id_str.strip())
        except ValueError: pass
            
    await db.update_guild_config(int(guild_id), "auto_role", "enabled", enabled)
    await db.update_guild_config(int(guild_id), "auto_role", "role_id", role_id)
    
    return RedirectResponse(f"/dashboard/{guild_id}", status_code=303)

@app.post("/dashboard/{guild_id}/feature")
async def update_feature(request: Request, guild_id: str):
    user = request.session.get("user")
    if not user: return RedirectResponse("/login")
    
    form = await request.form()
    enabled = form.get("enabled") == "on"
    channel_id_str = form.get("channel_id")
    
    channel_id = None
    if channel_id_str and channel_id_str.strip():
        try: channel_id = int(channel_id_str.strip())
        except ValueError: pass
            
    await db.update_guild_config(int(guild_id), "feature_channel", "enabled", enabled)
    await db.update_guild_config(int(guild_id), "feature_channel", "channel_id", channel_id)
    
    # Trigger message update in bot
    bot.dispatch("feature_channel_update", int(guild_id))
    
    return RedirectResponse(f"/dashboard/{guild_id}", status_code=303)

@app.post("/dashboard/{guild_id}/greeting")
async def update_greeting(request: Request, guild_id: str):
    user = request.session.get("user")
    if not user: return RedirectResponse("/login")
    
    form = await request.form()
    guild_id_int = int(guild_id)
    
    # Get current config to preserve existing times if not provided
    current_config = await db.get_guild_config(guild_id_int)
    greeting = current_config.get("greeting", {})
    
    # Update fields
    greeting["enabled"] = form.get("enabled") == "on"
    
    channel_id_str = form.get("channel_id")
    if channel_id_str and channel_id_str.strip():
        try: greeting["channel_id"] = int(channel_id_str.strip())
        except ValueError: pass
    else:
        greeting["channel_id"] = None
        
    morning_msg = form.get("morning_msg")
    if morning_msg: greeting["morning_msg"] = morning_msg
    
    evening_msg = form.get("evening_msg")
    if evening_msg: greeting["evening_msg"] = evening_msg
    
    # Handle Times robustly
    try:
        m_hour = form.get("morning_hour")
        if m_hour is not None and m_hour.strip() != "":
            greeting["morning_hour"] = int(m_hour)
            
        m_min = form.get("morning_minute")
        if m_min is not None and m_min.strip() != "":
            greeting["morning_minute"] = int(m_min)
            
        e_hour = form.get("evening_hour")
        if e_hour is not None and e_hour.strip() != "":
            greeting["evening_hour"] = int(e_hour)
            
        e_min = form.get("evening_minute")
        if e_min is not None and e_min.strip() != "":
            greeting["evening_minute"] = int(e_min)
    except (ValueError, TypeError):
        pass
    
    # Save the entire greeting dict at once
    full_config = await db.get_guild_config(guild_id_int)
    full_config["greeting"] = greeting
    await db.set(str(guild_id_int), full_config)
    
    return RedirectResponse(f"/dashboard/{guild_id}", status_code=303)

@app.post("/dashboard/{guild_id}/social")
async def update_social(request: Request, guild_id: str):
    user = request.session.get("user")
    if not user: return RedirectResponse("/login")
    
    form = await request.form()
    notification_channel = form.get("notification_channel")
    
    try:
        notif_channel_id = int(notification_channel) if notification_channel and notification_channel.strip() else None
    except ValueError:
        notif_channel_id = None
        
    await db.update_guild_config(int(guild_id), "social", "notification_channel", notif_channel_id)
    
    return RedirectResponse(f"/dashboard/{guild_id}", status_code=303)

@app.post("/dashboard/{guild_id}/social/add")
async def add_social_account(request: Request, guild_id: str):
    user = request.session.get("user")
    if not user: return RedirectResponse("/login")

    form = await request.form()
    platform = form.get("platform")
    identifier = form.get("identifier") # URL or Username/ID
    
    if not platform or not identifier:
        return RedirectResponse(f"/dashboard/{guild_id}", status_code=303)

    # Simple validation/extraction logic
    # ideally we would move this to a utility, but for now here is fine
    entry = {"id": identifier, "name": identifier, "last_video": None, "last_stream": None}

    if platform == "youtube":
        # Extract Channel ID if full URL, else assume ID
        # Basic check, detailed handling in bot logic or improved later
        if "youtube.com/channel/" in identifier:
            entry["id"] = identifier.split("youtube.com/channel/")[-1].split("/")[0]
        entry["name"] = entry["id"] # Placeholder until fetched
        
    elif platform == "kick":
        if "kick.com/" in identifier:
            entry["id"] = identifier.split("kick.com/")[-1].split("/")[0]
        else:
            entry["id"] = identifier
        entry["name"] = entry["id"]

    elif platform == "tiktok":
        if "tiktok.com/@" in identifier:
            entry["id"] = identifier.split("tiktok.com/@")[-1].split("?")[0].split("/")[0]
        elif "tiktok.com/" in identifier: # handle mobile links or other formats best effort
             entry["id"] = identifier.split("tiktok.com/")[-1].replace("@", "").split("/")[0]
        else:
             entry["id"] = identifier.replace("@", "")
        entry["name"] = entry["id"]

    # Load current config
    config = await db.get_guild_config(int(guild_id))
    social_config = config.get("social", {})
    current_list = social_config.get(platform, [])
    
    # Check duplicate
    if not any(c["id"] == entry["id"] for c in current_list):
        current_list.append(entry)
        await db.update_guild_config(int(guild_id), "social", platform, current_list)

    return RedirectResponse(f"/dashboard/{guild_id}", status_code=303)

@app.post("/dashboard/{guild_id}/social/remove")
async def remove_social_account(request: Request, guild_id: str):
    user = request.session.get("user")
    if not user: return RedirectResponse("/login")

    form = await request.form()
    platform = form.get("platform")
    account_id = form.get("account_id")

    if platform and account_id:
        config = await db.get_guild_config(int(guild_id))
        social_config = config.get("social", {})
        current_list = social_config.get(platform, [])

        new_list = [c for c in current_list if c["id"] != account_id]
        
        await db.update_guild_config(int(guild_id), "social", platform, new_list)

    return RedirectResponse(f"/dashboard/{guild_id}", status_code=303)

# ---------------------------------------------------------------------------- #
#                                DISCORD BOT                                   #
# ---------------------------------------------------------------------------- #
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class PunqBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    async def setup_hook(self):
        # Initialize Database
        await db.initialize()
        
        # Load Cogs
        cogs_folder = "./cogs"
        if os.path.exists(cogs_folder):
            for filename in os.listdir(cogs_folder):
                if filename.endswith(".py") and not filename.startswith("__"):
                    try:
                        await self.load_extension(f"cogs.{filename[:-3]}")
                        logger.info(f"Loaded extension: {filename}")
                    except Exception as e:
                        logger.error(f"Failed to load extension {filename}: {e}")
        
        # Sync Hybrid Commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} commands.")
        except Exception as e:
            logger.error(f"Command sync failed: {e}")
            
        # Ensure owner is fetched
        if config.get("owner_id"):
            try:
                self.owner_id = int(config["owner_id"])
                logger.info(f"Using Owner ID from config: {self.owner_id}")
            except (ValueError, TypeError):
                logger.warning("Invalid owner_id in config.json")
        
        if not self.owner_id and not self.owner_ids:
            try:
                app_info = await self.application_info()
                self.owner_id = app_info.owner.id
                logger.info(f"Fetched Bot Owner from API: {app_info.owner}")
            except Exception as e:
                logger.error(f"Failed to fetch app info: {e}")


    # Bot Owner Check specifically for ID from config
    async def is_owner(self, user: discord.User):
        if config.get("owner_id") and user.id == int(config["owner_id"]):
            return True
        return await super().is_owner(user)

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info("--------------------------------------------------")
        await self.update_status()

    async def update_status(self):
        # Reload config to ensure fresh state
        cfg = load_config()
        maintenance = cfg.get("maintenance", False)
        
        if maintenance:
            await self.change_presence(
                status=discord.Status.dnd,
                activity=discord.Activity(
                    type=discord.ActivityType.playing,
                    name="Bakımda 🛠️"
                )
            )
            logger.info("Status updated: Maintenance Mode")
        else:
            await self.change_presence(
                status=discord.Status.online,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="/help | No.punq"
                )
            )
            logger.info("Status updated: Online")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=PremiumEmbed.error("Yetki Hatası", "Bu komutu kullanmak için `Yönetici` yetkiniz olmalı."))
            return
        
        if isinstance(error, commands.NotOwner):
            await ctx.send(embed=PremiumEmbed.error("Yetki Hatası", "Bu komut sadece **Bot Sahibi** tarafından kullanılabilir."))
            return
        
        logger.error(f"Command Error: {error}")
        await ctx.send(embed=PremiumEmbed.error("Hata", f"Bir hata oluştu: `{error}`"))


bot = PunqBot()

# ---------------------------------------------------------------------------- #
#                             MAINTENANCE CHECK                                #
# ---------------------------------------------------------------------------- #
@bot.check
async def maintenance_check(ctx):
    # Owners bypass maintenance
    if await bot.is_owner(ctx.author):
        return True
    
    # Reload config for real-time check
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            current_config = json.load(f)
    except Exception:
        current_config = {}

    if current_config.get("maintenance", False):
        embed = PremiumEmbed(
            title="Bakımdayız 🛠️",
            description="Bot şu anda bakım modundadır.\nGeliştiricilerimiz sistemi güncelliyor. Lütfen daha sonra tekrar deneyiniz.",
            color=0x9d4edd
        )
        await ctx.send(embed=embed)
        return False
    
    return True

# ---------------------------------------------------------------------------- #
#                                 LAUNCHER                                     #
# ---------------------------------------------------------------------------- #
async def main():
    token = config.get("token")
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        logger.critical("Bot token is missing or default in config.json! Please update config.json.")
        return

    # Check and Kill Port 8000 if occupied (Windows Only)
    if os.name == 'nt':
        import subprocess
        try:
            # Check if port 8000 is in use
            result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if ":8000" in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    logger.warning(f"Port 8000 is occupied by PID {pid}. Attempting to kill...")
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                    await asyncio.sleep(2) # Wait for release
                    logger.info("Port freed.")
                    break
        except Exception as e:
            logger.error(f"Failed to clear port 8000: {e}")

    # Configure Uvicorn
    # Cloud platforms (Render, Heroku) provide PORT via env var
    port = int(os.environ.get("PORT", 8000))
    
    u_config = Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        loop="asyncio"
    )
    server = Server(u_config)
    
    logger.info("Starting No.punq System...")
    
    async with bot:
         await asyncio.gather(
            bot.start(token),
            server.serve()
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
