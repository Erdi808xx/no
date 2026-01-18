
import sys
try:
    import discord
    print("discord imported")
    import aiohttp
    print("aiohttp imported")
    import aiohappyeyeballs
    print("aiohappyeyeballs imported")
    from aiohappyeyeballs import HappyEyeballs
    print("HappyEyeballs imported")
except Exception as e:
    print(f"Error: {e}")
except SystemExit as e:
    print(f"SystemExit: {e}")
