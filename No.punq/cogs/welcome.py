import discord
from discord.ext import commands
from utils.database import db

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        config = await db.get_guild_config(member.guild.id)
        welcome_cfg = config.get("welcome", {})
        
        if not welcome_cfg.get("enabled", False):
            return
            
        channel_id = welcome_cfg.get("channel_id")
        if not channel_id:
            return
            
        channel = member.guild.get_channel(int(channel_id))
        if not channel:
            return
            
        rules_channel_id = welcome_cfg.get("rules_channel_id")
        rules_mention = f"<#{rules_channel_id}>" if rules_channel_id else "kurallar"
        
        count = member.guild.member_count
        target = welcome_cfg.get("member_target", 100)
        
        # Kullanıcının tam istediği yalın format (Progress bar ve ek alanlar çıkartıldı)
        message_template = welcome_cfg.get("message")
        if not message_template:
            message_template = "Hoş geldin {user}! Seninle birlikte {count} kişiyiz. Hedefimiz {target} üye! ✨ {rules_channel}"
            
        final_message = message_template.replace("{user}", member.mention)\
                                       .replace("{rules_channel}", rules_mention)\
                                       .replace("{count}", str(count))\
                                       .replace("{target}", str(target))
        
        embed = discord.Embed(
            title="Yeni Bir Üye Katıldı! ✨",
            description=final_message,
            color=0x9d4edd
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id} | No.punq System")
        
        try:
            await channel.send(content=member.mention, embed=embed)
        except Exception as e:
            print(f"Welcome message failed: {e}")

        # --- AUTO ROLE LOGIC ---
        autorole_cfg = config.get("auto_role", {})
        if autorole_cfg.get("enabled", False):
            role_id = autorole_cfg.get("role_id")
            if role_id:
                role = member.guild.get_role(int(role_id))
                if role:
                    try:
                        await member.add_roles(role)
                    except: pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        config = await db.get_guild_config(member.guild.id)
        welcome_cfg = config.get("welcome", {})
        
        if not welcome_cfg.get("leave_enabled", False):
            return
            
        channel_id = welcome_cfg.get("channel_id")
        if not channel_id:
            return
            
        channel = member.guild.get_channel(int(channel_id))
        if not channel:
            return
            
        count = member.guild.member_count
        target = welcome_cfg.get("member_target", 100)
        
        message_template = welcome_cfg.get("leave_message")
        if not message_template:
            message_template = "Güle güle **{user}**! Senden sonra {count} kişi kaldık. 😢"
        
        final_message = message_template.replace("{user}", member.name)\
                                       .replace("{count}", str(count))\
                                       .replace("{target}", str(target))
        
        embed = discord.Embed(
            title="Bir Üye Aramızdan Ayrıldı! 👋",
            description=final_message,
            color=0xe74c3c
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id} | No.punq System")
        
        try:
            await channel.send(embed=embed)
        except: pass

async def setup(bot):
    await bot.add_cog(Welcome(bot))
