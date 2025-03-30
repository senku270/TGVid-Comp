from config import *
import os
import sys
import asyncio
import logging
from telethon import events

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ADMIN_USER_ID = Config.OWNER  # Ensure this exists in config

# Flag to indicate if the bot is restarting
is_restarting = False

async def restart_bot(event):
    global is_restarting
    if str(event.sender_id) not in ADMIN_USER_ID:
        return await event.reply("**🚫 You're not an authorized user!**")

    if not is_restarting:
        is_restarting = True
        await event.reply("**🔄 Restarting bot...**")
        logger.info("Restarting bot requested by %s", event.sender_id)

        # Gracefully disconnect the bot
        await bot.disconnect()

        # Non-blocking sleep before restart
        await asyncio.sleep(2)  

        # Restart the bot process
        os.execl(sys.executable, sys.executable, *sys.argv)