import psutil
import platform
import logging
from telethon import events

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
LOGS = logging.getLogger("CPU_Info")

@bot.on(events.NewMessage(pattern='/cpu'))
async def cpu_info(event):
    LOGS.info(f"Received /cpu command from user: {event.sender_id}")

    try:
        LOGS.info("Fetching CPU details...")

        cpu_name = platform.processor()
        physical_cores = psutil.cpu_count(logical=False)
        logical_cores = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_usage = psutil.cpu_percent(interval=1)

        LOGS.info(f"Processor: {cpu_name}")
        LOGS.info(f"Physical Cores: {physical_cores}")
        LOGS.info(f"Logical Cores: {logical_cores}")
        LOGS.info(f"Max Frequency: {cpu_freq.max:.2f} MHz")
        LOGS.info(f"Current Frequency: {cpu_freq.current:.2f} MHz")
        LOGS.info(f"CPU Usage: {cpu_usage}%")

        response = (
            "🖥 **CPU Information**\n"
            f"🔹 **Processor**: {cpu_name}\n"
            f"🔹 **Physical Cores**: {physical_cores}\n"
            f"🔹 **Logical Cores**: {logical_cores}\n"
            f"🔹 **Max Frequency**: {cpu_freq.max:.2f} MHz\n"
            f"🔹 **Current Frequency**: {cpu_freq.current:.2f} MHz\n"
            f"🔹 **CPU Usage**: {cpu_usage}%"
        )

        LOGS.info("Sending response to user...")
        await event.reply(response)
        LOGS.info("Response sent successfully.")

    except Exception as e:
        LOGS.error(f"Error in CPU command: {e}")
        await event.reply("❌ An error occurred while fetching CPU info.")