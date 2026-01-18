import discord
from discord.ext import commands
from discord import app_commands
import os

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="panel", aliases=["pn"], description="Web panel bağlantısını gönderir.")
    @commands.has_permissions(administrator=True)
    async def panel_command(self, ctx):
        dashboard_url = "http://localhost:8000"
        
        embed = discord.Embed(
            title="🎛️ No.punq Kontrol Paneli",
            description=(
                f"Merhaba **{ctx.author.name}**! 👋\n\n"
                "Sunucu ayarlarını yönetmek, istatistikleri görmek ve botu yapılandırmak için "
                "aşağıdaki bağlantıyı kullanabilirsin. Gelişmiş panelimiz ile tam kontrol sende!\n\n"
                f"🔗 **[Panele Gitmek İçin Tıkla]({dashboard_url})**"
            ),
            color=0x9d4edd
        )
        embed.set_footer(text="No.punq - Profesyonel Bot Yönetimi")
        
        files = []
        if os.path.exists("assets/logo.jpg"):
            files.append(discord.File("assets/logo.jpg", filename="logo.jpg"))
            embed.set_thumbnail(url="attachment://logo.jpg")
            
        if os.path.exists("assets/banner.jpg"):
            files.append(discord.File("assets/banner.jpg", filename="banner.jpg"))
            embed.set_image(url="attachment://banner.jpg")

        await ctx.send(embed=embed, files=files, ephemeral=True)

    @commands.hybrid_command(name="avatar", description="Kullanıcının profil fotoğrafını gösterir.")
    async def avatar(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        embed = discord.Embed(title=f"{user.name} Avatarı", color=0x9d4edd)
        embed.set_image(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="user", description="Kullanıcı hakkında bilgi verir.")
    async def user_info(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        embed = discord.Embed(title="Kullanıcı Bilgisi", color=0x9d4edd)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Ad", value=user.name, inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Katılma Tarihi", value=user.joined_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="Hesap Oluşturma", value=user.created_at.strftime("%d/%m/%Y"), inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="server", description="Sunucu hakkında bilgi verir.")
    async def server_info(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title=f"{guild.name} Bilgisi", color=0x9d4edd)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Sahip", value=guild.owner.mention, inline=True)
        embed.add_field(name="Üye Sayısı", value=guild.member_count, inline=True)
        embed.add_field(name="Oluşturulma", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping", description="Botun gecikme süresini gösterir.")
    async def ping(self, ctx):
        await ctx.send(f"🏓 Pong! **{round(self.bot.latency * 1000)}ms**")

    @commands.hybrid_command(name="afk", description="AFK modunu açar.")
    async def afk(self, ctx, *, reason: str = "AFK"):
        embed = discord.Embed(
            title="💤 AFK Modu Aktif",
            description=f"{ctx.author.mention} artık AFK!\n**Sebep:** {reason}",
            color=0x9d4edd
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="invite", description="Botun davet linkini gönderir.")
    async def invite(self, ctx):
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={self.bot.user.id}&permissions=8&scope=bot%20applications.commands"
        embed = discord.Embed(
            title="🔗 Botu Sunucuna Ekle",
            description=f"Aşağıdaki linke tıklayarak botu kendi sunucuna ekleyebilirsin!\n\n[Botu Davet Et]({invite_url})",
            color=0x9d4edd
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="stats", description="Bot istatistiklerini gösterir.")
    async def stats(self, ctx):
        embed = discord.Embed(title="📊 Bot İstatistikleri", color=0x9d4edd)
        embed.add_field(name="Sunucu Sayısı", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Kullanıcı Sayısı", value=sum(g.member_count for g in self.bot.guilds), inline=True)
        embed.add_field(name="Gecikme", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ds", aliases=["destek"], description="Destek talebi oluşturur.")
    @commands.has_permissions(administrator=True)
    async def support(self, ctx, *, mesaj: str):
        """Destek ekibine sorun bildirir - Sadece yöneticiler ve sunucu sahipleri kullanabilir"""
        
        # Immediate "thinking" indicator if this takes time
        # Send initial message to user to fulfill "millisecond" requirement
        # But for hybrid commands, we can just respond directly.
        
        try:
            # Move config loading out of the command for better performance if triggered often
            # For now, let's keep it but clean it up.
            import json
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            
            support_channel_id = config.get("support_channel_id", 0)
            
            if not support_channel_id or support_channel_id == 0:
                await ctx.send("❌ Destek kanalı ayarlanmamış! Bot sahibiyle iletişime geçin.", ephemeral=True)
                return
            
            # Use get_channel first, then fetch_channel
            support_channel = self.bot.get_channel(support_channel_id)
            if not support_channel:
                try:
                    support_channel = await self.bot.fetch_channel(support_channel_id)
                except:
                    pass
            
            if not support_channel:
                await ctx.send("❌ Destek kanalı bulunamadı veya botun erişimi yok!", ephemeral=True)
                return
            
            # Create a simple embed for faster processing
            support_embed = discord.Embed(
                title="🆘 Yeni Destek Talebi",
                description=mesaj,
                color=0xff5555,
                timestamp=discord.utils.utcnow()
            )
            
            support_embed.add_field(
                name="📍 Sunucu",
                value=f"**{ctx.guild.name}** ({ctx.guild.id})",
                inline=False
            )
            
            support_embed.add_field(
                name="👤 Gönderen",
                value=f"{ctx.author.mention} ({ctx.author.id})",
                inline=False
            )
            
            # Simple invite logic - try to get existing one or create one quickly
            invite_link = "Oluşturulamadı"
            try:
                invites = await ctx.guild.invites()
                if invites:
                    invite_link = invites[0].url
                else:
                    invite = await ctx.channel.create_invite(max_age=3600, max_uses=1)
                    invite_link = invite.url
            except:
                pass
            
            support_embed.add_field(name="🔗 Davet", value=invite_link)
            
            if ctx.guild.icon:
                support_embed.set_thumbnail(url=ctx.guild.icon.url)
            
            # Send to support
            await support_channel.send(content="🔔 **Yeni Destek Talebi!** @everyone", embed=support_embed)
            
            # Success response
            await ctx.send("✅ Talebiniz başarıyla iletildi! Destek ekibi en kısa sürede ilgilenecek.", ephemeral=True)
            
        except Exception as e:
            await ctx.send(f"❌ Hata: {str(e)}", ephemeral=True)


    @commands.hybrid_command(name="yardım", aliases=["help"], description="Mevcut komutları ve özelliklerini gösterir.")
    async def yardim_command(self, ctx):
        embed = discord.Embed(
            title="🌌 No.punq Sistem Rehberi",
            description=(
                "No.punq botunu en verimli şekilde kullanmak için tüm komutlar aşağıda listelenmiştir. "
                "Web panel üzerinden daha detaylı ayarlar yapabilirsiniz."
            ),
            color=0x9d4edd
        )
        
        embed.set_author(name="No.punq Assistant", icon_url=self.bot.user.display_avatar.url)
        
        # Categories
        embed.add_field(
            name="🟢 Üye Komutları",
            value=(
                "`!avatar` - Profil fotoğrafı\n"
                "`!user` - Kullanıcı bilgisi\n"
                "`!server` - Sunucu bilgisi\n"
                "`!ping` - Gecikme süresi\n"
                "`!afk` - AFK modu\n"
                "`!invite` - Bot davet linki\n"
                "`!stats` - Bot istatistikleri"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🟡 Yönetici Komutları",
            value=(
                "`!ds <mesaj>` - Destek talebi\n"
                "`!clear <sayı>` - Mesaj temizleme\n"
                "`!mod badword` - Küfür filtresi\n"
                "`!mod spam` - Spam koruması\n"
                "`!mod links` - Link koruması\n"
                "`!social setup` - Bildirim kanalı"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔴 Sunucu Sahibi Komutları",
            value=(
                "`!panel` - Web yönetim paneli\n"
                "`!mod setup` - Koruma sistemi kurulumu\n"
                "`!nuke` - Kanal sıfırlama\n"
                "`!bakım` - Bakım modu (Geliştirici)"
            ),
            inline=False
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Talep eden: {ctx.author.name} • No.punq v1.0", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Global error handler for permission errors"""
        
        # Ignore if command has its own error handler
        if hasattr(ctx.command, 'on_error'):
            return
        
        # Handle MissingPermissions error
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Yetki Hatası",
                description=(
                    f"{ctx.author.mention}, bu komutu kullanmak için yeterli yetkiniz yok!\n\n"
                    "**Gerekli Yetkiler:**\n"
                    f"• {', '.join(error.missing_permissions)}"
                ),
                color=0xff5555
            )
            embed.set_footer(text="Yardım için !yardım komutunu kullanabilirsiniz.")
            await ctx.send(embed=embed, delete_after=10)
        
        # Handle MissingRole error
        elif isinstance(error, commands.MissingRole):
            embed = discord.Embed(
                title="❌ Rol Hatası",
                description=f"{ctx.author.mention}, bu komutu kullanmak için gerekli role sahip değilsiniz!",
                color=0xff5555
            )
            await ctx.send(embed=embed, delete_after=10)
        
        # Handle NotOwner error
        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                title="🔒 Geliştirici Komutu",
                description=(
                    f"{ctx.author.mention}, bu komut sadece **Bot Geliştiricisi** (Yapımcısı) tarafından kullanılabilir!\n\n"
                    "Bu komuta erişiminiz bulunmamaktadır."
                ),
                color=0xff5555
            )
            await ctx.send(embed=embed, delete_after=10)
        
        # Handle CheckFailure (for custom checks)
        elif isinstance(error, commands.CheckFailure):
            embed = discord.Embed(
                title="⚠️ Erişim Engellendi",
                description=f"{ctx.author.mention}, bu komutu kullanma yetkiniz bulunmuyor!",
                color=0xffaa00
            )
            await ctx.send(embed=embed, delete_after=10)

async def setup(bot):
    if bot.get_command("help"):
        bot.remove_command("help") # Varsayılan help komutunu kaldır
    await bot.add_cog(General(bot))
