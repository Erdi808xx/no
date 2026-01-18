import discord
from discord.ext import commands
import json
import os
import datetime
from utils.ui import PremiumEmbed

class Owner(commands.Cog):
    """Bot sahibi için özel komutlar - Yardım menüsünde görünmez"""
    
    def __init__(self, bot):
        self.bot = bot
        self.config_path = "config.json"
    
    def load_config(self):
        """Config dosyasını yükle"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Config yükleme hatası: {e}")
            return {}
    
    def save_config(self, config):
        """Config dosyasını kaydet"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Config kaydetme hatası: {e}")
            return False
    
    @commands.command(name="bakım", hidden=True)
    @commands.is_owner()
    async def maintenance_on(self, ctx):
        """Bakım modunu aktif eder ve tüm sunuculara bildirim gönderir"""
        
        config = self.load_config()
        config["maintenance"] = True
        
        if not self.save_config(config):
            await ctx.send("❌ Config dosyası kaydedilemedi!")
            return
        
        # Bot durumunu güncelle
        await self.bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name="Bakımda 🛠️"
            )
        )
        
        # Bildirim embed'i
        embed = discord.Embed(
            title="🛠️ Bakım Modu Aktif",
            description=(
                "**No.punq** şu anda bakım moduna alındı.\n\n"
                "Bot geçici olarak kullanılamayacak. Bakım işlemleri tamamlandığında "
                "tekrar bilgilendirileceksiniz.\n\n"
                "**Tahmini Süre:** Bilinmiyor\n"
                "**Sebep:** Sistem güncellemeleri ve iyileştirmeler"
            ),
            color=0xff9800
        )
        embed.set_footer(text="No.punq System | Anlayışınız için teşekkürler")
        embed.timestamp = discord.utils.utcnow()
        
        # Tüm sunuculara bildirim gönder
        sent_count = 0
        failed_count = 0
        
        for guild in self.bot.guilds:
            try:
                # Sistem mesajları kanalını bul
                channel = guild.system_channel or guild.text_channels[0] if guild.text_channels else None
                
                if channel:
                    await channel.send(embed=embed)
                    sent_count += 1
            except:
                failed_count += 1
                continue
        
        # Onay mesajı
        confirm_embed = discord.Embed(
            title="✅ Bakım Modu Aktif Edildi",
            description=(
                f"**Bildirim Gönderildi:** {sent_count} sunucu\n"
                f"**Başarısız:** {failed_count} sunucu\n\n"
                "Bot artık bakım modunda. Komutlar sadece bot sahibi tarafından kullanılabilir."
            ),
            color=0x4caf50
        )
        await ctx.send(embed=confirm_embed)
    
    @commands.command(name="bakımbitti", hidden=True)
    @commands.is_owner()
    async def maintenance_off(self, ctx):
        """Bakım modunu kapatır ve tüm sunuculara bildirim gönderir"""
        
        config = self.load_config()
        config["maintenance"] = False
        
        if not self.save_config(config):
            await ctx.send("❌ Config dosyası kaydedilemedi!")
            return
        
        # Bot durumunu güncelle
        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="/help | No.punq"
            )
        )
        
        # Bildirim embed'i
        embed = discord.Embed(
            title="✅ Bakım Tamamlandı!",
            description=(
                "**No.punq** tekrar aktif!\n\n"
                "Bakım işlemleri başarıyla tamamlandı. Bot artık tam kapasiteyle "
                "hizmetinizde.\n\n"
                "**Yenilikler:**\n"
                "• Performans iyileştirmeleri\n"
                "• Hata düzeltmeleri\n"
                "• Sistem güncellemeleri\n\n"
                "İyi kullanımlar! 🚀"
            ),
            color=0x4caf50
        )
        embed.set_footer(text="No.punq System | Sabırınız için teşekkürler")
        embed.timestamp = discord.utils.utcnow()
        
        # Tüm sunuculara bildirim gönder
        sent_count = 0
        failed_count = 0
        
        for guild in self.bot.guilds:
            try:
                channel = guild.system_channel or guild.text_channels[0] if guild.text_channels else None
                
                if channel:
                    await channel.send(embed=embed)
                    sent_count += 1
            except:
                failed_count += 1
                continue
        
        # Onay mesajı
        confirm_embed = discord.Embed(
            title="✅ Bakım Modu Kapatıldı",
            description=(
                f"**Bildirim Gönderildi:** {sent_count} sunucu\n"
                f"**Başarısız:** {failed_count} sunucu\n\n"
                "Bot artık normal modda çalışıyor."
            ),
            color=0x4caf50
        )
        await ctx.send(embed=confirm_embed)
    
    @commands.command(name="np")
    async def owner_help(self, ctx):
        """Sadece bot sahibi için özel yardım menüsü"""
        embed = PremiumEmbed(
            title="🛠️ No.punq Geliştirici Paneli",
            description="Bot yapımcısına özel sistem ve yönetim komutları aşağıdadır.",
            color=0x9d4edd # Brand Purple
        )
        
        # Sistem Yönetimi
        embed.add_field(
            name="⚙️ Sistem Yönetimi",
            value=(
                "`!reload` - Tüm sistemleri ve cogs'ları yeniler.\n"
                "`!bakım` - Botu bakım moduna alır.\n"
                "`!bakımbitti` - Bakım modundan çıkarır.\n"
                "`!loopdurum` - Zamanlayıcıların durumunu kontrol eder."
            ),
            inline=False
        )
        
        # Selamlama Yönetimi
        embed.add_field(
            name="☀️ Selamlama Sistemi",
            value=(
                "`!selamayarla <sabah/akşam> <saat> <dakiha>` - Saatleri ayarlar.\n"
                "`!selamzaman` - Mevcut ayarlı saatleri gösterir.\n"
                "`!selamtest <sabah/akşam>` - Selamlamayı anlık test eder."
            ),
            inline=False
        )
        
        # Bilgi
        embed.add_field(
            name="💡 Bilgi",
            value="Bu menüdeki komutlar sadece bot yapımcısı tarafından tetiklenebilir.",
            inline=False
        )
        
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        await ctx.send(embed=embed)

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cogs(self, ctx):
        """Tüm sistemleri ve modülleri (cogs) yeniler"""
        success = []
        failed = []
        cogs_folder = "./cogs"
        
        # Iterating over copy of list
        for filename in list(os.listdir(cogs_folder)):
            if filename.endswith(".py") and not filename.startswith("__"):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.bot.reload_extension(cog_name)
                    success.append(filename)
                except commands.ExtensionNotLoaded:
                    try:
                        await self.bot.load_extension(cog_name)
                        success.append(f"{filename} (Yeni)")
                    except Exception as e:
                        failed.append(f"{filename} ({e})")
                except Exception as e:
                    failed.append(f"{filename} ({e})")
        
        # Sync Hybrid Commands (Slash Commands)
        sync_status = "N/A"
        try:
            synced = await self.bot.tree.sync()
            sync_status = f"✅ {len(synced)} komut senkronize edildi."
        except Exception as e:
            sync_status = f"❌ Senkronizasyon hatası: {e}"

        embed = PremiumEmbed(
            title="🔄 Sistem Yenilendi",
            description=(
                f"**Başarılı:** {', '.join(success) if success else 'Yok'}\n"
                f"**Hatalı:** {', '.join(failed) if failed else 'Yok'}\n\n"
                f"**Durum:** {sync_status}"
            ),
            color=0x9d4edd # Purple
        )
        embed.set_footer(text=f"Yenileme saati: {datetime.datetime.now().strftime('%H:%M:%S')} | No.punq Security")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Owner(bot))
