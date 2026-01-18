import discord

class PremiumEmbed(discord.Embed):
    def __init__(self, **kwargs):
        color = kwargs.pop("color", 0x9d4edd) # Default brand color
        super().__init__(color=color, **kwargs)
        self.set_footer(text="No.punq Premium Security")
        self.timestamp = discord.utils.utcnow()

    @classmethod
    def success(cls, title: str, description: str):
        return cls(title=f"✅ {title}", description=description, color=0x2ecc71)

    @classmethod
    def error(cls, title: str, description: str):
        return cls(title=f"❌ {title}", description=description, color=0xe74c3c)
        
    @classmethod
    def warning(cls, title: str, description: str):
        return cls(title=f"⚠️ {title}", description=description, color=0xf1c40f)
