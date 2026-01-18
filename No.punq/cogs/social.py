import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.database import db
import aiohttp
import xml.etree.ElementTree as ET
import logging
from typing import Optional
import json

class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_updates.start()
        self.logger = logging.getLogger("Social")
        self.session = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession(headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    async def cog_unload(self):
        self.check_updates.cancel()
        if self.session:
            await self.session.close()

    async def check_youtube(self, channel_id):
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                data = await response.text()
                root = ET.fromstring(data)
                ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
                entry = root.find('atom:entry', ns)
                if entry is not None:
                    video_id = entry.find('yt:videoId', ns).text
                    link = entry.find('atom:link', ns).attrib['href']
                    title = entry.find('atom:title', ns).text
                    return {"id": video_id, "link": link, "title": title, "type": "video"}
        except Exception as e:
            self.logger.error(f"Error fetching YT {channel_id}: {e}")
        return None

    async def check_kick(self, channel_slug):
        url = f"https://kick.com/api/v1/channels/{channel_slug}"
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                livestream = data.get("livestream")
                if livestream:
                    return {
                        "id": str(livestream["id"]),
                        "title": livestream["session_title"],
                        "link": f"https://kick.com/{channel_slug}",
                        "thumbnail": livestream["thumbnail"]["url"],
                        "type": "live"
                    }
        except Exception as e:
            self.logger.error(f"Error fetching Kick {channel_slug}: {e}")
        return None

    async def check_tiktok(self, username):
        # Best effort scraping for TikTok Live
        url = f"https://www.tiktok.com/@{username}/live"
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                # Check for indicators of live stream
                # Verify specific meta tags or room_id presence which usually indicates live session
                if '"status":2' in html or "room_id" in html and '"status":4' not in html: # Simplified guess
                    # TikTok structure changes often, this is fragile.
                    # Alternative: checking for og:title containing "LIVE"
                    # For now, let's assume if we can fetch the live page and it has certain data, they might be live.
                    # A robust way needs a headless browser or heavy reversing.
                    # We will use a simple heuristic: if "room_id" is present and we are redirected to /live, good chance.
                    
                    if "room_id" in html:
                         return {
                            "id": "live", # Dynamic ID is hard to extract reliably without regex
                            "link": f"https://www.tiktok.com/@{username}/live",
                            "title": f"{username} TikTok'ta Canlı Yayında!",
                            "type": "live"
                        }
        except Exception as e:
            self.logger.error(f"Error fetching TikTok {username}: {e}")
        return None

    @tasks.loop(minutes=5)
    async def check_updates(self):
        await self.bot.wait_until_ready()
        
        try:
            all_data = await db.get_all()
            for guild_id_str, config in all_data.items():
                if "social" not in config:
                    continue
                
                social_config = config["social"]
                notify_channel_id = social_config.get("notification_channel")
                if not notify_channel_id:
                    continue

                guild = self.bot.get_guild(int(guild_id_str))
                if not guild: continue
                channel = guild.get_channel(notify_channel_id)
                if not channel: continue

                # Check YouTube
                for yt in social_config.get("youtube", []):
                    latest = await self.check_youtube(yt["id"])
                    if latest and latest["id"] != yt.get("last_video"):
                        await channel.send(f"@everyone 📢 **Yeni YouTube Videosu!**\n**{yt['name']}** yeni bir video yükledi:\n{latest['link']}")
                        yt["last_video"] = latest["id"]
                        await db.update_guild_config(int(guild_id_str), "social", "youtube", social_config["youtube"])

                # Check Kick
                for kick in social_config.get("kick", []):
                    latest = await self.check_kick(kick["id"]) # id is slug here
                    if latest:
                        # Check if we already notified for this stream
                        if latest["id"] != kick.get("last_stream"):
                            await channel.send(f"@everyone 🔴 **KICK CANLI YAYIN!**\n**{kick['name']}** yayında!\n{latest['title']}\n{latest['link']}")
                            kick["last_stream"] = latest["id"]
                            await db.update_guild_config(int(guild_id_str), "social", "kick", social_config["kick"])

                # Check TikTok
                for tiktok in social_config.get("tiktok", []):
                    latest = await self.check_tiktok(tiktok["id"])
                    # Simple state tracking for generic "live" status to avoid spam
                    # Since we don't get a unique stream ID easily from regex, we toggle a boolean or ignore 'id' logic if it is always 'live'
                    # We will just use 'live' as ID and check if we have already notified 'live' recently?
                    # Better: If latest found (Online) and last_stream != "online", notify.
                    # If not found (Offline), set last_stream = "offline".
                    
                    is_live = latest is not None
                    last_status = tiktok.get("last_stream", "offline")
                    
                    if is_live and last_status != "online":
                        await channel.send(f"@everyone 🔴 **TIKTOK CANLI YAYIN!**\n**{tiktok['name']}** yayında!\n{latest['link']}")
                        tiktok["last_stream"] = "online"
                        await db.update_guild_config(int(guild_id_str), "social", "tiktok", social_config["tiktok"])
                    elif not is_live and last_status == "online":
                        tiktok["last_stream"] = "offline"
                        await db.update_guild_config(int(guild_id_str), "social", "tiktok", social_config["tiktok"])

        except Exception as e:
            self.logger.error(f"Error in social update loop: {e}")

    @commands.hybrid_group(name="social", description="Sosyal medya takip sistemi.")
    @commands.has_permissions(administrator=True)
    async def social(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Lütfen paneli kullanın: `/dashboard`")

    @social.command(name="setup", description="Bildirim kanalını hızlıca ayarlar.")
    async def setup(self, ctx, channel: discord.TextChannel):
        await db.update_guild_config(ctx.guild.id, "social", "notification_channel", channel.id)
        await ctx.send(f"📢 Bildirim kanalı {channel.mention} olarak ayarlandı.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Error handler for social commands"""
        
        if hasattr(ctx.command, 'on_error'):
            return
        
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="📢 Sosyal Medya Yetki Hatası",
                description=(
                    f"{ctx.author.mention}, sosyal medya komutlarını kullanmak için yeterli yetkiniz yok!\n\n"
                    "**Gerekli Yetkiler:**\n"
                    f"• {', '.join(error.missing_permissions)}\n\n"
                    "Bu komut **yönetici** tarafından kullanılabilir."
                ),
                color=0xff5555
            )
            embed.set_footer(text="Yönetici komutları için !yardım yazın.")
            await ctx.send(embed=embed, delete_after=10)

async def setup(bot):
    await bot.add_cog(Social(bot))
