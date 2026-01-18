import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
from utils.database import db
from utils.ui import PremiumEmbed
import re
from typing import Optional

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Simple spam cache: {user_id: [timestamp, timestamp, ...]}
        self.spam_cache = {} 
        self.SPAM_THRESHOLD = 5  # messages
        self.SPAM_WINDOW = 5     # seconds
        
        # Load Global Bad Words
        self.global_bad_words = []
        try:
            import json, os
            if os.path.exists("utils/bad_words.json"):
                with open("utils/bad_words.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for lang_list in data.values():
                        self.global_bad_words.extend(lang_list)
        except Exception as e:
            print(f"Failed to load global bad words: {e}")
            
        # Start cleanup task
        self.cleanup_spam_cache.start()
        
    def cog_unload(self):
        self.cleanup_spam_cache.cancel()

    @tasks.loop(minutes=5)
    async def cleanup_spam_cache(self):
        """Clears the spam cache periodically to prevent memory leaks."""
        self.spam_cache.clear()

    async def log_action(self, guild, action: str, user: discord.Member, moderator: discord.Member, reason: str = "Yok"):
        """Sends a moderation log embed."""
        config = await db.get_guild_config(guild.id)
        log_channel_id = config["moderation"].get("log_channel")
        if not log_channel_id:
            return

        channel = guild.get_channel(log_channel_id)
        if not channel:
            return

        embed = PremiumEmbed(title=f"🛡️ Moderasyon: {action}", color=discord.Color.red())
        embed.add_field(name="Kullanıcı", value=f"{user} ({user.id})", inline=True)
        embed.add_field(name="Yetkili", value=f"{moderator} ({moderator.id})", inline=True)
        embed.add_field(name="Sebep", value=reason, inline=False)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await channel.send(embed=embed)

    async def apply_punishment(self, message, reason):
        """Applies automated punishments based on warn count."""
        author = message.author
        guild = message.guild
        
        # Add Warn
        warn_count = await db.add_warn(guild.id, author.id, reason)
        
        # 1. Warn Message
        embed = PremiumEmbed(title="⚠️ Uyarı", description=f"{guild.name} sunucusunda uyarıldınız.", color=discord.Color.orange())
        embed.add_field(name="Sebep", value=reason)
        embed.add_field(name="Ceza Sırası", value=f"#{warn_count}")
        
        try:
            await author.send(embed=embed)
        except:
            pass # DM kapalı olabilir

        action_taken = "Uyarı Verildi"

        # 2. Timeout (15 mins) -> 2nd Offense
        if warn_count == 2:
            duration = datetime.timedelta(minutes=15)
            try:
                await author.timeout(duration, reason=reason)
                action_taken = "15 Dakika Susturma"
            except discord.Forbidden:
                action_taken = "Susturma (Yetki Yok)"

        # 3. Kick -> 3rd Offense
        elif warn_count >= 3:
            try:
                await author.kick(reason=f"Otomatik Ceza: {reason} (3+ Uyarı)")
                action_taken = "Sunucudan Atıldı"
            except discord.Forbidden:
                action_taken = "Atma (Yetki Yok)"

        # Log to Server
        await self.log_action(guild, action_taken, author, self.bot.user, reason)
        
        # Reply to user in channel
        await message.channel.send(embed=PremiumEmbed.warning("İşlem Uygulandı", f"{author.mention} işlem uygulandı: **{action_taken}**\nSebep: {reason}"), delete_after=10)


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.webhook_id or not message.guild:
            return

        config = await db.get_guild_config(message.guild.id)
        mod_config = config.get("moderation", {})
        
        if not mod_config.get("enabled", False):
            return

        # Essential Bypass: Server Owner & Bot Developers are ALWAYS immune
        if message.author.id == message.guild.owner_id or await self.bot.is_owner(message.author):
            return

        # Admin Checking Logic
        scan_admins = mod_config.get("scan_admins", False)
        if not scan_admins:
             if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_guild:
                 return

        content_lower = message.content.lower()
        content_stripped = "".join(content_lower.split()) # Remove spaces for bypass attempts like "k ü f ü r"

        # 0. Repetitive Character Check (Spam/Flood)
        if len(content_lower) > 10:
             # Check if more than 50% of the message is the same character repeated
             for char in set(content_stripped):
                 if content_stripped.count(char) > len(content_stripped) * 0.6 and len(content_stripped) > 5:
                     try:
                         await message.delete()
                         await self.apply_punishment(message, "Gereksiz Karakter Tekrarı (Spam)")
                         return
                     except:
                         pass

        # 1. Bad Words Filter
        custom_bad_words = mod_config.get("bad_words", [])
        all_bad_words = custom_bad_words + self.global_bad_words
        
        if any(word in content_lower for word in all_bad_words) or any(word in content_stripped for word in all_bad_words):
            try:
                await message.delete()
                await self.apply_punishment(message, "Yasaklı Kelime / Küfür")
            except:
                pass
            return

        # 2. Link & Ad Protection
        if mod_config.get("link_protection", False):
            # Regex for generic links
            url_pattern = re.compile(r'(https?://\S+|www\.\S+)')
            # Specific Regex for Discord Invites (Ads)
            invite_pattern = re.compile(r'(discord(?:app)?\.com/invite/|discord\.gg/)[a-zA-Z0-9]+')
            
            found_url = url_pattern.search(message.content)
            found_invite = invite_pattern.search(message.content)
            
            if found_url or found_invite:
                whitelist = mod_config.get("whitelist_links", [])
                
                # If it's an invite and no specific whitelist for it, block it as AD
                if found_invite:
                     # Check if it's the guild's own invite? (Optional, but safe to block all for now if strict)
                     await message.delete()
                     await self.apply_punishment(message, "Reklam (Discord Invite)")
                     return

                # Generic Link Check
                if not any(allowed in message.content for allowed in whitelist):
                    await message.delete()
                    await self.apply_punishment(message, "Reklam / Yasaklı Link")
                    return

        # 3. Spam Protection
        if mod_config.get("spam_protection", False):
            now = datetime.datetime.now().timestamp()
            user_id = message.author.id
            
            if user_id not in self.spam_cache:
                self.spam_cache[user_id] = []
            
            # Add current msg timestamp
            self.spam_cache[user_id].append(now)
            
            # Clean old timestamps
            self.spam_cache[user_id] = [t for t in self.spam_cache[user_id] if now - t < self.SPAM_WINDOW]
            
            if len(self.spam_cache[user_id]) > self.SPAM_THRESHOLD:
                # Spam detected
                await message.delete() # Delete latest
                # Ideally delete previous ones too but that requires history fetch
                await self.apply_punishment(message, "Spam / Flood")
                self.spam_cache[user_id] = [] # Reset to prevent loop kick
                return


    # ------------------------------------------------------------------------ #
    #                               COMMANDS                                   #
    # ------------------------------------------------------------------------ #

    @commands.hybrid_group(name="mod", description="Moderasyon ve güvenlik ayarları.")
    @commands.has_permissions(administrator=True)
    async def mod(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=PremiumEmbed.warning("Eksik Komut", "Lütfen bir alt komut kullanın: `setup`, `badword`, `link`, `spam`, `test`"), delete_after=10)

    @mod.command(name="test", description="Moderasyon sistemini test eder.")
    async def test_moderation(self, ctx):
        """Moderasyon sisteminin durumunu kontrol eder"""
        config = await db.get_guild_config(ctx.guild.id)
        mod_config = config.get("moderation", {})
        
        embed = PremiumEmbed(title="🛡️ Moderasyon Sistemi Test", color=0x9d4edd)
        
        embed.add_field(name="Durum", value="✅ Aktif" if mod_config.get("enabled", False) else "❌ Deaktif", inline=True)
        embed.add_field(name="Global Küfür Listesi", value=f"{len(self.global_bad_words)} kelime", inline=True)
        embed.add_field(name="Özel Küfür Listesi", value=f"{len(mod_config.get('bad_words', []))} kelime", inline=True)
        embed.add_field(name="Spam Koruması", value="✅ Aktif" if mod_config.get("spam_protection", False) else "❌ Deaktif", inline=True)
        embed.add_field(name="Link Koruması", value="✅ Aktif" if mod_config.get("link_protection", False) else "❌ Deaktif", inline=True)
        embed.add_field(name="Log Kanalı", value=f"<#{mod_config.get('log_channel')}>" if mod_config.get('log_channel') else "Ayarlanmamış", inline=True)
        
        if self.global_bad_words:
            sample_words = ", ".join(self.global_bad_words[:5])
            embed.add_field(name="Örnek Yasaklı Kelimeler", value=f"||{sample_words}||...", inline=False)
        
        embed.set_footer(text="⚠️ Yöneticiler moderasyondan muaf tutulur • No.punq Security")
        await ctx.send(embed=embed)

    @mod.command(name="setup", description="Log kanalını ve sistemi aktif eder.")
    @app_commands.describe(enabled="Modülü aç/kapat", channel="Logların gideceği kanal")
    async def setup(self, ctx, enabled: bool, channel: discord.TextChannel):
        await db.update_guild_config(ctx.guild.id, "moderation", "enabled", enabled)
        await db.update_guild_config(ctx.guild.id, "moderation", "log_channel", channel.id)
        
        status = "Aktif ✅" if enabled else "Deaktif ❌"
        await ctx.send(embed=PremiumEmbed.success("Kurulum Başarılı", f"Moderasyon sistemi **{status}**.\nLog kanalı: {channel.mention}"))

    @mod.command(name="badword", description="Yasaklı kelime ekle/kaldır.")
    @app_commands.describe(action="add (ekle) veya remove (kaldır)", word="Kelime")
    @app_commands.choices(action=[
        app_commands.Choice(name="Ekle", value="add"),
        app_commands.Choice(name="Kaldır", value="remove"),
        app_commands.Choice(name="Listele", value="list")
    ])
    async def badword(self, ctx, action: str, word: Optional[str] = None):
        config = await db.get_guild_config(ctx.guild.id)
        current_words = config["moderation"].get("bad_words", [])

        if action == "list":
            if not current_words:
                await ctx.send(embed=PremiumEmbed.warning("Liste Boş", "Hiç özel yasaklı kelime yok."))
            else:
                await ctx.send(embed=PremiumEmbed(title="🚫 Yasaklı Kelimeler", description=f"||{', '.join(current_words)}||"))
            return

        if not word:
            await ctx.send(embed=PremiumEmbed.error("Hata", "Lütfen bir kelime belirtin."))
            return

        word = word.lower()
        if action == "add":
            if word not in current_words:
                current_words.append(word)
                await ctx.send(embed=PremiumEmbed.success("Eklendi", f"Yasaklı kelime eklendi: ||{word}||"))
            else:
                await ctx.send(embed=PremiumEmbed.warning("Mevcut", "Bu kelime zaten listede."))
        
        elif action == "remove":
            if word in current_words:
                current_words.remove(word)
                await ctx.send(embed=PremiumEmbed.success("Kaldırıldı", f"Yasaklı kelime kaldırıldı: ||{word}||"))
            else:
                await ctx.send(embed=PremiumEmbed.error("Bulunamadı", "Bu kelime listede yok."))
        
        await db.update_guild_config(ctx.guild.id, "moderation", "bad_words", current_words)

    @mod.command(name="spam", description="Spam korumasını aç/kapat.")
    async def spam_toggle(self, ctx, enabled: bool):
        await db.update_guild_config(ctx.guild.id, "moderation", "spam_protection", enabled)
        state = "Açık" if enabled else "Kapalı"
        color = 0x2ecc71 if enabled else 0xe74c3c
        await ctx.send(embed=PremiumEmbed(title="Spam Koruması", description=f"Durum: **{state}**", color=color))

    @mod.command(name="links", description="Link engelleyici ve Whitelist.")
    @app_commands.describe(enabled="Aç/Kapat", whitelist="Virgülle ayrılmış izinli domainler (örn: youtube.com,google.com)")
    async def links_toggle(self, ctx, enabled: bool, whitelist: Optional[str] = None):
        await db.update_guild_config(ctx.guild.id, "moderation", "link_protection", enabled)
        
        msg = f"Link Koruması: **{'Açık' if enabled else 'Kapalı'}**"
        
        if whitelist:
            allowed_list = [d.strip() for d in whitelist.split(",")]
            await db.update_guild_config(ctx.guild.id, "moderation", "whitelist_links", allowed_list)
            msg += f"\nWhitelist Güncellendi: {', '.join(allowed_list)}"
            
        await ctx.send(embed=PremiumEmbed.success("Link Ayarı", msg))

    # ------------------------------------------------------------------------ #
    #                             MANUAL ACTIONS                               #
    # ------------------------------------------------------------------------ #
    
    # ------------------------------------------------------------------------ #
    #                             MANUAL ACTIONS                               #
    # ------------------------------------------------------------------------ #
    
    @commands.hybrid_command(name="kick", description="Kullanıcıyı sunucudan atar.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason: str = "Sebep belirtilmedi"):
        await user.kick(reason=reason)
        await self.log_action(ctx.guild, "Atıldı (Kick)", user, ctx.author, reason)
        await ctx.send(embed=PremiumEmbed.success("İşlem Başarılı", f"**{user}** sunucudan atıldı.\nSebep: {reason}"))

    @commands.hybrid_command(name="ban", description="Kullanıcıyı sunucudan yasaklar.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.User, *, reason: str = "Sebep belirtilmedi"):
        await ctx.guild.ban(user, reason=reason)
        await self.log_action(ctx.guild, "Yasaklandı (Ban)", user, ctx.author, reason)
        await ctx.send(embed=PremiumEmbed.success("İşlem Başarılı", f"**{user}** sunucudan yasaklandı.\nSebep: {reason}"))

    @commands.hybrid_command(name="unban", description="Kullanıcının yasaklamasını kaldırır.")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: str):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await self.log_action(ctx.guild, "Yasak Kaldırıldı", user, ctx.author)
            await ctx.send(embed=PremiumEmbed.success("İşlem Başarılı", f"**{user}** yasaklaması kaldırıldı."))
        except discord.NotFound:
             await ctx.send(embed=PremiumEmbed.error("Hata", "Kullanıcı bulunamadı."))
        except Exception as e:
             await ctx.send(embed=PremiumEmbed.error("Hata", f"İşlem sırasında bir hata oluştu: {e}"))

    @commands.hybrid_command(name="siciltemizle", description="Bir kullanıcının tüm sicilini (uyarılarını) temizler. (Sadece Sahip)")
    @app_commands.describe(member="Sicili temizlenecek kullanıcı")
    async def siciltemizle(self, ctx, member: discord.Member):
        """Kullanıcının tüm uyarı geçmişini siler - Sadece sunucu sahibi veya bot sahibi kullanabilir"""
        # Authorization check: Server Owner or Bot Owner
        is_server_owner = ctx.author.id == ctx.guild.owner_id
        is_bot_owner = await self.bot.is_owner(ctx.author)
        
        if not (is_server_owner or is_bot_owner):
            embed = PremiumEmbed(
                title="❌ Yetki Yetersiz",
                description="Bu komutu sadece **Sunucu Sahibi** kullanabilir!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return
            
        success = await db.clear_warns(ctx.guild.id, member.id)
        if success:
            await self.log_action(ctx.guild, "Sicil Temizlendi", member, ctx.author, "Geçmiş sıfırlandı.")
            embed = PremiumEmbed(
                title="✨ Sicil Temizlendi",
                description=f"**{member}** kullanıcısının tüm sicili başarıyla temizlendi.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = PremiumEmbed(
                title="ℹ️ Bilgi",
                description=f"**{member}** kullanıcısının zaten temiz bir sicili var.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)

    # ------------------------------------------------------------------------ #
    #                             CLEANUP ACTIONS                               #
    # ------------------------------------------------------------------------ #
    
    @commands.hybrid_command(name="clear", description="Belirtilen sayıda mesajı siler.")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        if amount < 1:
            await ctx.send(embed=PremiumEmbed.warning("Uyarı", "En az 1 mesaj silmelisiniz."))
            return
        
        deleted = await ctx.channel.purge(limit=amount)
        embed = PremiumEmbed(description=f"🗑️ **{len(deleted)}** mesaj silindi.", color=discord.Color.green())
        await ctx.send(embed=embed, delete_after=5)

    @commands.hybrid_command(name="nuke", description="Kanalı silip yeniden oluşturur.")
    @commands.has_permissions(administrator=True)
    async def nuke(self, ctx):
        channel = ctx.channel
        pos = channel.position
        
        # Clone
        new_channel = await channel.clone(reason="Nuke command used")
        await new_channel.edit(position=pos)
        
        # Delete old
        await channel.delete(reason="Nuke command used")
        
        # Send msg in new channel
        embed = PremiumEmbed(title="Nuke Başarılı ☢️", description="Bu kanal temizlendi.", color=discord.Color.red())
        embed.set_image(url="https://media.giphy.com/media/HhTXt43pk1I1W/giphy.gif")
        await new_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Error handler for moderation commands"""
        
        if hasattr(ctx.command, 'on_error'):
            return
        
        if isinstance(error, commands.MissingPermissions):
            embed = PremiumEmbed(
                title="🛡️ Moderasyon Yetki Hatası",
                description=(
                    f"{ctx.author.mention}, bu moderasyon komutunu kullanmak için yeterli yetkiniz yok!\n\n"
                    "**Gerekli Yetkiler:**\n"
                    f"• {', '.join(error.missing_permissions)}\n\n"
                    "Bu komut **yönetici** veya **sunucu sahibi** tarafından kullanılabilir."
                ),
                color=0xff5555
            )
            await ctx.send(embed=embed, delete_after=10)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
