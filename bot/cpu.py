import psutil
import platform
from pyrogram import Client, filters

@Client.on_message(filters.command("cpu"))
async def cpu_info(client, message):
    cpu_name = platform.processor()
    physical_cores = psutil.cpu_count(logical=False)
    logical_cores = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()

    response = f"""
🖥 **CPU Information**  
🔹 **Processor**: {cpu_name}  
🔹 **Physical Cores**: {physical_cores}  
🔹 **Logical Cores**: {logical_cores}  
🔹 **Max Frequency**: {cpu_freq.max:.2f} MHz  
🔹 **Current Frequency**: {cpu_freq.current:.2f} MHz  
🔹 **CPU Usage**: {psutil.cpu_percent(interval=1)}%
"""

    await message.reply(response)