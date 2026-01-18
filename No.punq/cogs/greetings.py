import discord
from discord.ext import commands, tasks
from utils.database import db
from utils.ui import PremiumEmbed
import datetime

class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_time.start()

    def cog_unload(self):
        self.check_time.cancel()

    @tasks.loop(minutes=1)
    async def check_time(self):
        # Turkey Time (UTC+3)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        now = now_utc + datetime.timedelta(hours=3)
        print(f"[DEBUG] Turkey Time Check: {now.strftime('%H:%M:%S')}")
        
        # Iterate over all guilds to check their custom times
        for guild in self.bot.guilds:
            try:
                config = await db.get_guild_config(guild.id)
                greeting_config = config.get("greeting", {})
                
                if not greeting_config.get("enabled", False):
                    continue
                
                channel_id = greeting_config.get("channel_id")
                if not channel_id:
                    continue
                
                # Get custom times or use defaults (10:00 and 22:00)
                morning_hour = greeting_config.get("morning_hour", 10)
                morning_minute = greeting_config.get("morning_minute", 0)
                evening_hour = greeting_config.get("evening_hour", 22)
                evening_minute = greeting_config.get("evening_minute", 0)
                
                # Check for morning time
                if now.hour == morning_hour and now.minute == morning_minute:
                    print(f"[INFO] Sending morning greeting to {guild.name}")
                    await self.send_greeting_to_guild(guild, "morning")
                
                # Check for evening time
                elif now.hour == evening_hour and now.minute == evening_minute:
                    print(f"[INFO] Sending evening greeting to {guild.name}")
                    await self.send_greeting_to_guild(guild, "evening")
            except Exception as e:
                print(f"[ERROR] Greeting loop error in {guild.name}: {e}")

    async def send_greeting_to_guild(self, guild, type: str):
        """Send greeting to a specific guild"""
        config = await db.get_guild_config(guild.id)
        greeting_config = config.get("greeting", {})
        
        channel_id = greeting_config.get("channel_id")
        if not channel_id:
            return
            
        channel = guild.get_channel(channel_id)
        if not channel:
            try:
                channel = await guild.fetch_channel(channel_id)
            except:
                return
            
        morning_msg = greeting_config.get("morning_msg", "Günaydın! ☀️")
        evening_msg = greeting_config.get("evening_msg", "İyi Akşamlar! 🌙")

        if type == "morning":
            # Cool Sunshine Neon Style
            embed = PremiumEmbed(
                title="Sistem: Günaydın ✨",
                description=f"**{morning_msg}**\n\n> Yeni bir güne, yeni bir enerjiyle! ☀️",
                color=0xFFD60A # Bright Gold Neon
            )
            # High-end Neon Sun GIF
            embed.set_image(url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExMjRreGJ6Z2Z6YXpqeWJ6Z2Z6YXpqeWJ6Z2Z6YXpqeWJ6JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/6ozwFj8zAbK1S/giphy.gif")
        else:
            # Cool Moon Neon Style
            embed = PremiumEmbed(
                title="Sistem: İyi Akşamlar 🌙",
                description=f"**{evening_msg}**\n\n> Günün yorgunluğunu geride bırakma vakti! ✨",
                color=0x7209B7 # Deep Purple Neon
            )
            embed.set_image(url="https://media.giphy.com/media/3o6fJ5LANL0x31R1Ic/giphy.gif")
        
        try:
            # Force @everyone mention as a separate part of the content string
            # and send the embed along with it
            await channel.send(content="@everyone", embed=embed)
            print(f"[SUCCESS] Greeting ({type}) sent with @everyone to {guild.name}")
        except Exception as e:
            print(f"[ERROR] Failed to send greeting to {guild.name}: {e}")

    async def send_greeting(self, type: str):
        """Legacy method - kept for compatibility"""
        for guild in self.bot.guilds:
            await self.send_greeting_to_guild(guild, type)

    @commands.hybrid_command(name="selamayarla", description="Otomatik selamlama saatlerini ayarla")
    @commands.is_owner()
    async def set_greeting_time(self, ctx, tip: str, saat: int, dakika: int = 0):
        """
        Otomatik selamlama saatlerini ayarla
        
        Kullanım:
        !selamayarla sabah 12 0  -> Sabah selamını 12:00'ye ayarlar
        !selamayarla akşam 21 30 -> Akşam selamını 21:30'a ayarlar
        """
        # Validate input
        if tip.lower() not in ["sabah", "akşam", "morning", "evening"]:
            embed = PremiumEmbed(
                title="❌ Hatalı Tip",
                description="Lütfen `sabah` veya `akşam` yazın.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        if not (0 <= saat <= 23):
            embed = PremiumEmbed(
                title="❌ Hatalı Saat",
                description="Saat 0-23 arasında olmalıdır.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        if not (0 <= dakika <= 59):
            embed = PremiumEmbed(
                title="❌ Hatalı Dakika",
                description="Dakika 0-59 arasında olmalıdır.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Get current config
        config = await db.get_guild_config(ctx.guild.id)
        if "greeting" not in config:
            config["greeting"] = {}
        
        # Update the appropriate time
        if tip.lower() in ["sabah", "morning"]:
            config["greeting"]["morning_hour"] = saat
            config["greeting"]["morning_minute"] = dakika
            time_type = "Sabah"
            emoji = "☀️"
        else:
            config["greeting"]["evening_hour"] = saat
            config["greeting"]["evening_minute"] = dakika
            time_type = "Akşam"
            emoji = "🌙"
        
        # Save to database
        full_config = await db.get_guild_config(ctx.guild.id)
        full_config["greeting"] = config["greeting"]
        await db.set(str(ctx.guild.id), full_config)
        
        # Send confirmation
        embed = PremiumEmbed(
            title=f"{emoji} {time_type} Selamı Ayarlandı",
            description=f"{time_type} selamı **{saat:02d}:{dakika:02d}** olarak ayarlandı.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="💡 Bilgi",
            value="Selamlar her gün bu saatte otomatik olarak gönderilecektir.",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="selamzaman", description="Mevcut selamlama saatlerini göster")
    @commands.is_owner()
    async def show_greeting_times(self, ctx):
        """Mevcut selamlama saatlerini gösterir"""
        config = await db.get_guild_config(ctx.guild.id)
        greeting_config = config.get("greeting", {})
        
        morning_hour = greeting_config.get("morning_hour", 10)
        morning_minute = greeting_config.get("morning_minute", 0)
        evening_hour = greeting_config.get("evening_hour", 22)
        evening_minute = greeting_config.get("evening_minute", 0)
        
        enabled = greeting_config.get("enabled", False)
        status = "✅ Aktif" if enabled else "❌ Kapalı"
        
        embed = PremiumEmbed(
            title="🕐 Selamlama Zamanları",
            description=f"Otomatik selamlama sistemi: {status}",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="☀️ Sabah Selamı",
            value=f"**{morning_hour:02d}:{morning_minute:02d}**",
            inline=True
        )
        embed.add_field(
            name="🌙 Akşam Selamı",
            value=f"**{evening_hour:02d}:{evening_minute:02d}**",
            inline=True
        )
        embed.add_field(
            name="💡 Değiştirmek için",
            value="`!selamayarla <sabah/akşam> <saat> <dakika>`",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @check_time.before_loop
    async def before_check_time(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="selamtest", description="Selamlama mesajını test eder.")
    @commands.is_owner()
    async def selam_test(self, ctx, tip: str):
        """Test the greeting manually: !selamtest <sabah/akşam>"""
        if tip.lower() not in ["sabah", "akşam"]:
            return await ctx.send("❌ Geçersiz tip! `sabah` veya `akşam` yazmalısınız.")
        
        greeting_type = "morning" if tip.lower() == "sabah" else "evening"
        await self.send_greeting_to_guild(ctx.guild, greeting_type)
        await ctx.send(f"✅ {tip.capitalize()} selamlaması test edildi!", ephemeral=True)

    @commands.command(name="loopdurum")
    @commands.is_owner()
    async def loop_status(self, ctx):
        is_running = self.check_time.is_running()
        await ctx.send(f"📊 Zamanlayıcı durumu: {'✅ Çalışıyor' if is_running else '❌ Durmuş'}")
        if not is_running:
            self.check_time.start()
            await ctx.send("🔄 Zamanlayıcı tekrar başlatıldı!")

async def setup(bot):
    await bot.add_cog(Greetings(bot))
