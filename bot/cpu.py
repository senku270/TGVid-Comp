import psutil
import platform
from telethon import events

@bot.on(events.NewMessage(pattern='/cpu'))
async def cpu_info(event):
    cpu_name = platform.processor()
    physical_cores = psutil.cpu_count(logical=False)
    logical_cores = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    cpu_usage = psutil.cpu_percent(interval=1)

    response = (
        "🖥 **CPU Information**\n"
        f"🔹 **Processor**: {cpu_name}\n"
        f"🔹 **Physical Cores**: {physical_cores}\n"
        f"🔹 **Logical Cores**: {logical_cores}\n"
        f"🔹 **Max Frequency**: {cpu_freq.max:.2f} MHz\n"
        f"🔹 **Current Frequency**: {cpu_freq.current:.2f} MHz\n"
        f"🔹 **CPU Usage**: {cpu_usage}%"
    )

    await event.reply(response)
