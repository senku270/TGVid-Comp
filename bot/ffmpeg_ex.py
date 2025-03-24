import re
import os
import time
import asyncio
import logging
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from telethon import Button

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("FFmpegExecutor")

# Global variables to manage state
WORKING = []
QUEUE = {}

def generate_progress_bar(percentage):
    """Generate a progress bar in the desired style"""
    bar_length = 14
    if percentage >= 100:
        bar = "■" * bar_length
    else:
        filled = int(percentage / 100 * bar_length)
        if filled < bar_length:
            bar = "■" * filled + "▤" + "□" * (bar_length - filled - 1)
        else:
            bar = "■" * bar_length
    return f"[{bar}]"

def get_system_stats():
    """Get current system stats (CPU, RAM)"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        ram_percent = ram.percent
        ram_used = f"{ram.used / (1024 ** 3):.2f} GB"
        return {
            "cpu": cpu_percent,
            "ram_percent": ram_percent,
            "ram_used": ram_used,
            "total_ram": f"{ram.total/(1024**2):.0f}Mb"
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        return {
            "cpu": 0,
            "ram_percent": 0,
            "ram_used": "0 GB",
            "total_ram": "0Mb"
        }

def get_disk_stats():
    """Get free disk space and its percentage"""
    try:
        disk = psutil.disk_usage('.')
        free = hbs(disk.free)
        free_percent = f"{(disk.free/disk.total)*100:.1f}%"
        return free, free_percent
    except Exception as e:
        logger.error(f"Error getting disk stats: {str(e)}")
        return "N/A", "N/A"

def get_uptime():
    """Return system uptime as formatted string"""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_delta = datetime.now() - boot_time
        hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h{minutes}m{seconds}s"
    except Exception as e:
        logger.error(f"Error calculating uptime: {str(e)}")
        return "N/A"

def hbs(size):
    """Convert bytes to human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f}{unit}"
        size /= 1024.0
    return f"{size:.2f}PB"

def ts(milliseconds):
    """Convert milliseconds to human-readable time"""
    total_seconds = int(milliseconds / 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

async def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe"""
    logger.info(f"Getting duration for video: {video_path}")
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
    
    process = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    try:
        duration = float(stdout.decode().strip())
        logger.info(f"Video duration: {duration} seconds")
        return duration
    except Exception as e:
        error_msg = stderr.decode()
        logger.error(f"Error getting video duration: {error_msg}")
        return 1

async def execute_ffmpeg(event, input_path, output_path, ffmpeg_cmd):
    """Execute FFmpeg command with progress tracking"""
    logger.info(f"Starting FFmpeg execution: {input_path} -> {output_path}")
    
    full_cmd = f"""ffmpeg -i "{input_path}" {ffmpeg_cmd} "{output_path}" -y -progress pipe:1 -nostats"""
    logger.debug(f"Running command: {full_cmd}")

    process = await asyncio.create_subprocess_shell(
        full_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    total_duration = await get_video_duration(input_path)
    logger.info(f"Total video duration: {total_duration} seconds")

    org_size = int(Path(input_path).stat().st_size)
    org_size_str = hbs(org_size)
    logger.info(f"Original file size: {org_size_str}")

    encoded_time = 0
    start_time = time.time()
    update_interval = 3  # seconds
    last_update_time = start_time

    logger.info("Starting FFmpeg progress monitoring")
    while True:
        line = await process.stdout.readline()
        if not line:
            logger.debug("Reached end of FFmpeg output")
            break

        line = line.decode().strip()
        logger.debug(f"FFmpeg progress line: {line}")

        if "out_time_ms=" in line:
            match = re.search(r"out_time_ms=(\d+)", line)
            if match:
                encoded_time = int(match.group(1)) / 1_000_000  # seconds

        current_time = time.time()
        if current_time - last_update_time >= update_interval:
            elapsed_time = current_time - start_time
            percentage = min(100, (encoded_time / total_duration) * 100)
            progress_bar = generate_progress_bar(percentage)

            encoding_speed = (encoded_time / elapsed_time) if elapsed_time > 0 else 0
            cur_size = int(Path(output_path).stat().st_size) if Path(output_path).exists() else 0

            compression_percent = 100 - ((cur_size / org_size) * 100) if org_size > 0 else 0
            compression_str = f"{compression_percent:.2f}%" if isinstance(compression_percent, float) else "N/A"

            avg_speed = encoded_time / elapsed_time if elapsed_time > 0 else 0
            remaining_seconds = (total_duration - encoded_time) / avg_speed if avg_speed > 0 else 0
            eta = str(timedelta(seconds=int(remaining_seconds)))
            est = str(timedelta(seconds=int(elapsed_time + remaining_seconds)))

            stats = get_system_stats()
            free_disk, free_disk_percent = get_disk_stats()
            uptime = get_uptime()
            tasks_count = len(WORKING) + len(QUEUE) if (WORKING or QUEUE) else 0

            status_message = (
                f"**⎘** __{Path(input_path).name}__ | __{percentage:.2f}%__ **⟳**\n"
                f"{progress_bar}\n"
                f"**❖** 𝗢𝗚: __{org_size_str}__ **→** 𝗢𝗨𝗧: __{hbs(cur_size)}__ **__({compression_str})__**\n\n"
                f"**⚡** 𝗦𝗣𝗘𝗘𝗗: **__{encoding_speed:.2f}x__**  | ** ⧖** 𝗘𝗧𝗔: __{eta}__\n"
                f"** ⧗** 𝗘𝗟𝗧: __{timedelta(seconds=int(elapsed_time))}__  | **⌖** 𝗘𝗦𝗧: **__{est}__""\n\n"
                f"** ᚛᚜** 𝗧𝗔𝗦𝗞: __{tasks_count}__ | **⌬** 𝗖𝗣𝗨: __{stats['cpu']}%__ | ** 🜁** 𝗥𝗔𝗠: __{stats['ram_used']} ({stats['ram_percent']}%)__\n"
                f"**⌸** 𝗙 𝗦𝗧𝗢𝗥𝗔𝗚𝗘: __{free_disk}__ (__{free_disk_percent}__)"
            )

            try:
                await event.edit(
                    status_message,
                    buttons=[
                        [Button.inline("📊 STATS", data=f"stats{output_path}")],
                        [Button.inline("❌ CANCEL", data=f"skip{output_path}")],
                    ],
                )
                logger.debug("Progress message updated")
                last_update_time = current_time
            except Exception as e:
                logger.error(f"Progress update error: {str(e)}")

    stdout, stderr = await process.communicate()
    error_output = stderr.decode()

    if error_output:
        logger.error(f"FFmpeg error output: {error_output}")
        return None, error_output

    return output_path, None

async def ffmpeg_executor(event):
    """Main function to handle FFmpeg execution command"""
    if not event.is_private:
        return

    # Check authorization (replace with your actual authorization logic)
    if str(event.sender_id) not in OWNER and event.sender_id != DEV:
        return await event.reply("**Sorry, you're not an authorized user!**")

    # Parse command
    try:
        parts = event.text.split(maxsplit=1)[1].split()
    except IndexError:
        return await event.reply("**Usage: /ex ffmpeg -i input_path [ffmpeg_options] output_path**")

    # Validate input and output
    if '-i' not in parts:
        return await event.reply("**Error: -i (input) is mandatory**")

    try:
        input_index = parts.index('-i')
        input_path = parts[input_index + 1]
        output_path = parts[-1]  # Last argument is output

        if not os.path.exists(input_path):
            return await event.reply(f"**Error: Input file {input_path} does not exist**")

        # Reconstruct FFmpeg command without input and output paths
        ffmpeg_cmd = ' '.join(parts[1:input_index] + parts[input_index+2:-1])

    except Exception as e:
        return await event.reply(f"**Error parsing command: {str(e)}**")

    # Start processing
    WORKING.append(1)
    start_time = time.time()
    xxx = await event.reply("**🔧 Executing FFmpeg Command...**")

    try:
        output, error = await execute_ffmpeg(xxx, input_path, output_path, ffmpeg_cmd)
        
        if error:
            await xxx.edit(f"**FFmpeg Error:**\n`{error}`")
            WORKING.clear()
            return

        # Prepare result message
        org_size = int(Path(input_path).stat().st_size)
        out_size = int(Path(output_path).stat().st_size)
        pe = 100 - ((out_size / org_size) * 100)
        per = f"{pe:.2f}%"
        total_time = time.time() - start_time

        result_msg = (
            f"**FFmpeg Execution Complete**\n\n"
            f"**📁 Input File:** {os.path.basename(input_path)}\n"
            f"**📤 Output File:** {os.path.basename(output_path)}\n\n"
            f"**📊 Original Size:** {hbs(org_size)}\n"
            f"**📉 Output Size:** {hbs(out_size)}\n"
            f"**💯 Size Reduction:** {per}\n\n"
            f"**⏱️ Total Execution Time:** {ts(int(total_time * 1000))}"
        )

        await xxx.edit(result_msg)
        WORKING.clear()

    except Exception as e:
        logger.error(f"FFmpeg execution error: {e}")
        await xxx.edit(f"**Error during FFmpeg execution:** `{str(e)}`")
        WORKING.clear()

# Add this to your event handlers
# client.add_event_handler(ffmpeg_executor, events.NewMessage(pattern='/ex ffmpeg'))