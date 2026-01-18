import discord
from discord.ext import commands, tasks
from utils.database import db
from utils.ui import PremiumEmbed
import datetime
import time

class Features(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()
        self.update_info_channels.start()

    def cog_unload(self):
        self.update_info_channels.cancel()

    def get_uptime(self):
        delta = time.time() - self.start_time
        hours, remainder = divmod(int(delta), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        return f"{days}g {hours}s {minutes}d"

    @tasks.loop(minutes=2)
    async def update_info_channels(self):
        """Periodically updates the feature info message in designated channels."""
        for guild in self.bot.guilds:
            try:
                config = await db.get_guild_config(guild.id)
                f_config = config.get("feature_channel", {})
                
                if f_config.get("enabled") and f_config.get("channel_id"):
                    channel = guild.get_channel(int(f_config["channel_id"]))
                    if channel:
                        await self.send_feature_panel(channel, config)
            except Exception as e:
                print(f"Error updating feature channel for {guild.id}: {e}")

    async def send_feature_panel(self, channel, config):
        """Sunucunun özelliklerini gösteren profesyonel bir komuta merkezi gönderir."""
        # Görsel Şema Sabitleri
        AYIRICI = "═" * 32
        
        # Dinamik Renk Kayması (Zamana bağlı offset)
        # Her güncellemede renklerin bir adım kaymasını sağlar
        tick = int(time.time() / 60) % 6 
        colors = ["\u001b[1;31m", "\u001b[1;33m", "\u001b[1;32m", "\u001b[1;36m", "\u001b[1;34m", "\u001b[1;35m"]
        
        # Hareketli Üst Şerit
        rainbow_str = ""
        for i in range(30):
            color = colors[(i + tick) % len(colors)]
            rainbow_str += f"{color}━"
        
        embed = PremiumEmbed(
            title=f"〔 ✧ NO.PUNQ SİSTEM — KOMUTA MERKEZİ 〕",
            description=(
                f"```ansi\n{rainbow_str}\n"
                f"\u001b[1;34m[ SİSTEM ]\u001b[0m \u001b[1;32mAKTİF\u001b[0m   \u001b[1;34m[ GÜVENLİK ]\u001b[0m \u001b[1;32mKORUMALI\u001b[0m\n```\n"
                f"**No.punq SİSTEM**, sunucunuzu profesyonel yönetim ve güvenlik "
                f"standartlarıyla stabilize eden yapay zeka çekirdeğidir.\n\n"
                f"**{AYIRICI}**"
            ),
            color=0x7000ff
        )

        # 🛡️ GÜVENLİK KATMANI (Sabit Renkler)
        embed.add_field(
            name="🛡️ GÜVENLİK VE SAVUNMA ALTYAPISI",
            value=(
                f"```ansi\n\u001b[0;35m»\u001b[0m \u001b[0;37mGelişmiş Filtreleme Sistemi\u001b[0m\n\n"
                f"\u001b[0;35m»\u001b[0m \u001b[0;37mYetkili Hesabı Denetimi\u001b[0m\n\n"
                f"\u001b[0;35m»\u001b[0m \u001b[0;37m7/24 Kesintisiz Tehdit Takibi\u001b[0m\n```\n"
                f"Veri akışları gerçek zamanlı taranarak tehditler neutralize edilir.\n"
                "\u200b"
            ),
            inline=False
        )

        # ⚙️ OTOMASYON MERKEZİ (Sabit Renkler)
        embed.add_field(
            name="⚙️ OTOMASYON VE YÖNETİM MERKEZİ",
            value=(
                f"```ansi\n\u001b[0;34m»\u001b[0m \u001b[0;37mProfesyonel Karşılama Tasarımı\u001b[0m\n\n"
                f"\u001b[0;34m»\u001b[0m \u001b[0;37mDinamik Otomatik Rol Sistemi\u001b[0m\n\n"
                f"\u001b[0;34m»\u001b[0m \u001b[0;37mHedef Odaklı Üye Koordinasyonu\u001b[0m\n```\n"
                f"Süreçler otonom bir şekilde insan müdahalesi olmadan yönetilir.\n"
                "\u200b"
            ),
            inline=False
        )

        # 📡 SOSYAL RADAR (Belirginleştirilmiş)
        embed.add_field(
            name="📡 SOSYAL MEDYA RADAR TAKİBİ",
            value=(
                f"```ansi\n"
                f"\u001b[1;31m📺 YOUTUBE\u001b[0m   \u001b[1;30m•\u001b[0m \u001b[1;32m[ AKTİF ]\u001b[0m\n"
                f"\u001b[1;35m🎥 KICK\u001b[0m      \u001b[1;30m•\u001b[0m \u001b[1;32m[ AKTİF ]\u001b[0m\n"
                f"\u001b[1;34m📱 TIKTOK\u001b[0m    \u001b[1;30m•\u001b[0m \u001b[1;32m[ AKTİF ]\u001b[0m\n"
                f"```\n"
                f"Platformlardaki tüm yeni içerikler anında sunucuya aktarılır.\n"
                "\u200b"
            ),
            inline=False
        )

        # 📊 ANALİZ VE VERİ
        current = channel.guild.member_count
        target = config.get("welcome", {}).get('member_target', 100)
        percent = min(100, int((current / target) * 100)) if target > 0 else 0
        filled = int(percent / 5)
        
        # Dinamik (Kayan) RGB Progress Bar
        bar_ansi = ""
        for i in range(20):
            if i < filled:
                color = colors[(i + tick) % len(colors)]
                bar_ansi += f"{color}▰"
            else:
                bar_ansi += "\u001b[0;30m▱"
        bar_ansi += "\u001b[0m"

        embed.add_field(
            name="📈 SUNUCU ANALİZİ VE İSTATİSTİK",
            value=(
                f"**Doluluk Oranı:** `% {percent}`\n"
                f"```ansi\n{bar_ansi}\n```\n"
                f"> Mevcut Birim: `{current}` / `{target}`\n"
                f"**{AYIRICI}**"
            ),
            inline=False
        )

        # ⌬ BAŞ MİMAR
        embed.add_field(
            name="⌬ SİSTEM BAŞ MİMARI",
            value=(
                f"Bu dijital ekosistem, **Kyraelpm** tarafından en ileri teknolojik "
                f"standartlar ve özel yazılım mimarisiyle inşa edilmiştir."
            ),
            inline=False
        )

        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
        
        latency = round(self.bot.latency * 1000)
        embed.set_footer(
            text=f"NO.PUNQ • Yanıt: {latency}ms • Kyraelpm tarafından hazırlandı",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )

        # Mevcut paneli bulup güncelle
        try:
            async for message in channel.history(limit=10):
                if message.author == self.bot.user and message.embeds and "KOMUTA MERKEZİ" in (message.embeds[0].title or ""):
                    await message.edit(embed=embed)
                    return
        except discord.Forbidden:
            pass

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Automatically setup the system channel when the bot joins a new server."""
        try:
            # Create channel with specific permissions: 
            # Members can view but NOT send messages. Admins/Owner can send.
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, embed_links=True),
            }
            
            # Additional overwrites for users with Manage Channels or Admin to be able to talk if needed
            # But the request says just Owner and Admin, so we rely on their native permissions 
            # usually overriding the default_role's "send_messages=False".
            
            channel_name = "🛡️┃punq-sistem"
            
            channel = discord.utils.get(guild.text_channels, name=channel_name)
            
            if not channel:
                channel = await guild.create_text_channel(
                    channel_name,
                    overwrites=overwrites,
                    topic="No.punq OS Komuta Merkezi | Yüksek Seviye Güvenlik İstihbaratı.",
                    reason="Otomatik sistem başlangıcı"
                )
            else:
                # If channel exists, update its permissions to match the requirement
                await channel.edit(overwrites=overwrites)
            
            await db.update_guild_config(guild.id, "feature_channel", "enabled", True)
            await db.update_guild_config(guild.id, "feature_channel", "channel_id", channel.id)
            
            config = await db.get_guild_config(guild.id)
            await self.send_feature_panel(channel, config)
            
        except Exception as e:
            print(f"Failed to auto-setup feature channel for {guild.id}: {e}")

    @commands.Cog.listener()
    async def on_feature_channel_update(self, guild_id: int):
        """Triggered when the feature channel config is updated via the web panel."""
        guild = self.bot.get_guild(guild_id)
        if not guild: return
        
        config = await db.get_guild_config(guild_id)
        f_config = config.get("feature_channel", {})
        
        if f_config.get("enabled") and f_config.get("channel_id"):
            channel = guild.get_channel(int(f_config["channel_id"]))
            if channel:
                await self.send_feature_panel(channel, config)

    @commands.command(name="tr")
    @commands.has_permissions(administrator=True)
    async def trigger_feature(self, ctx):
        """Manually triggers the feature panel in the current channel for testing."""
        config = await db.get_guild_config(ctx.guild.id)
        # Update config to use THIS channel for future updates
        await db.update_guild_config(ctx.guild.id, "feature_channel", "enabled", True)
        await db.update_guild_config(ctx.guild.id, "feature_channel", "channel_id", ctx.channel.id)
        
        await self.send_feature_panel(ctx.channel, config)
        if ctx.interaction:
            await ctx.send("✅ Panel bu kanala kuruldu.", ephemeral=True)
        else:
            await ctx.message.delete()

    @commands.hybrid_command(name="ozellik_yenile", description="Bilgilendirme kanalındaki mesajı manuel olarak yeniler.")
    @commands.has_permissions(administrator=True)
    async def refresh_feature(self, ctx):
        config = await db.get_guild_config(ctx.guild.id)
        f_config = config.get("feature_channel", {})
        
        if not f_config.get("enabled") or not f_config.get("channel_id"):
            return await ctx.send("❌ Bilgilendirme kanalı bu sunucu için aktif edilmemiş.", ephemeral=True)
            
        channel = ctx.guild.get_channel(int(f_config["channel_id"]))
        if not channel:
            return await ctx.send("❌ Ayarlı olan kanal bulunamadı. Lütfen panelden ID'yi kontrol edin.", ephemeral=True)
            
        await ctx.defer(ephemeral=True)
        await self.send_feature_panel(channel, config)
        await ctx.send("✅ Bilgilendirme mesajı güncellendi.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Features(bot))
