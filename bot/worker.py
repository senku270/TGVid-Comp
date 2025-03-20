#    This file is part of the CompressorQueue distribution.
#    Copyright (c) 2021 Danish_00
#    Script Improved by Zylern

import re
import time
import asyncio
import logging
import psutil
import os
from pathlib import Path
from datetime import datetime as dt, timedelta
from telethon import Button
from .FastTelethon import download_file, upload_file
from .funcn import *
from .config import *

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("VideoEncoder")

# Global variable for the separate Queue-Status message.
QUEUE_MESSAGE = None

async def get_video_duration(video_path):
    """Get video duration in seconds using ffprobe"""
    logger.info(f"Getting duration for video: {video_path}")
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"'
    logger.debug(f"Running command: {cmd}")

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
        logger.error(f"Exception: {str(e)}")
        LOGS.info(f"Error getting video duration: {error_msg}")
        return 1

def generate_progress_bar(percentage):
    """Generate a text-based progress bar"""
    bar_length = 20  # Length of the progress bar
    filled_length = int(bar_length * percentage / 100)
    bar = "█" * filled_length + "░" * (bar_length - filled_length)
    logger.debug(f"Generated progress bar at {percentage:.2f}%: {bar}")
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
            "ram_used": ram_used
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        return {
            "cpu": 0,
            "ram_percent": 0,
            "ram_used": "0 GB"
        }

async def encode_video(dl, out, nn, wah):
    """Encode video with live progress updates including file size information and elapsed time"""
    global QUEUE_MESSAGE
    logger.info(f"Starting video encoding: {dl} -> {out}")
    cmd = f"""ffmpeg -i "{dl}" {ffmpegcode[0]} "{out}" -y -progress pipe:1 -nostats"""
    logger.debug(f"Running command: {cmd}")

    process = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    total_duration = await get_video_duration(dl)  # Get video duration in seconds
    logger.info(f"Total video duration: {total_duration} seconds")

    # Get original file size
    org_size = int(Path(dl).stat().st_size)
    org_size_str = hbs(org_size)
    logger.info(f"Original file size: {org_size_str}")

    encoded_time = 0
    start_time = time.time()
    update_interval = 3  # Update the progress message every 3 seconds
    last_update_time = start_time
    encoding_speeds = []  # To track encoding speed over time

    # Get download time from metadata if available
    download_time_str = "N/A"
    try:
        if hasattr(nn, "download_time"):
            download_time_str = ts(nn.download_time)
        else:
            download_time_str = "N/A"
    except Exception as e:
        logger.error(f"Error getting download time: {str(e)}")
        download_time_str = "N/A"

    logger.info("Starting encoding progress monitoring")
    while True:
        line = await process.stdout.readline()
        if not line:
            logger.debug("Reached end of ffmpeg output")
            break

        line = line.decode().strip()
        logger.debug(f"FFMPEG progress line: {line}")

        if "out_time_ms=" in line:  # Extract the encoding progress
            match = re.search(r"out_time_ms=(\d+)", line)
            if match:
                encoded_time = int(match.group(1)) / 1_000_000  # Convert to seconds
                logger.debug(f"Encoded time: {encoded_time:.2f}s / {total_duration:.2f}s")

        current_time = time.time()
        if current_time - last_update_time >= update_interval:
            elapsed_time = current_time - start_time
            elapsed_time_str = ts(int(elapsed_time * 1000))
            
            percentage = min(100, (encoded_time / total_duration) * 100)
            logger.info(f"Encoding progress: {percentage:.2f}%")
            progress_bar = generate_progress_bar(percentage)

            if elapsed_time > 0:
                encoding_speed = encoded_time / elapsed_time
                encoding_speeds.append(encoding_speed)
                recent_speeds = encoding_speeds[-5:] if len(encoding_speeds) >= 5 else encoding_speeds
                avg_speed = sum(recent_speeds) / len(recent_speeds)
                remaining_seconds = (total_duration - encoded_time) / avg_speed if avg_speed > 0 else 0
                eta = str(timedelta(seconds=int(remaining_seconds)))
            else:
                avg_speed = 0
                eta = "N/A"

            # Get system stats
            stats = get_system_stats()

            try:
                if Path(out).exists():
                    cur_size = int(Path(out).stat().st_size)
                    cur_size_str = hbs(cur_size)
                    if org_size > 0:
                        compression_percent = 100 - ((cur_size / org_size) * 100)
                        compression_str = f"{compression_percent:.2f}%"
                    else:
                        compression_str = "N/A"
                else:
                    cur_size_str = "0 B"
                    compression_str = "N/A"
            except Exception as e:
                logger.error(f"Error getting current file size: {str(e)}")
                cur_size_str = "calculating..."
                compression_str = "calculating..."

            # Create status messages
            status_message = (
                f"**🗜 Compressing {Path(dl).name}...**\n"
                f"{progress_bar} {percentage:.2f}%\n\n"
                f"**📊 Original Size:** {org_size_str}\n"
                f"**📉 Current Size:** {cur_size_str}\n"
                f"**💯 Compression:** {compression_str}\n\n"
                f"**⏱️ ETA:** {eta}\n"
                f"**🚀 Speed:** {avg_speed:.2f}x\n"
                f"**⌛ Download Time:** {download_time_str}\n"
                f"**⏳ Encoding Time:** {elapsed_time_str}\n"
                f"**💻 CPU:** {stats['cpu']}%\n"
                f"**🧠 RAM:** {stats['ram_used']} ({stats['ram_percent']}%)"
            )

            # Update individual file progress message and the separate queue-status message
            try:
                # Update file progress message
                await nn.edit(status_message, buttons=[
                    [Button.inline("STATS", data=f"stats{wah}")],
                    [Button.inline("CANCEL", data=f"skip{wah}")],
                ])

                # Update the Queue-Status message (assumes QUEUE_MESSAGE has been set)
                queue_status = "**📋 Queue Status:**\n"
                for index, (file_id, file_data) in enumerate(QUEUE.items()):
                    file_name = file_data[0]
                    if file_name == Path(dl).name:
                        status = f"🔄 {generate_progress_bar(percentage)} {percentage:.2f}%"
                    elif index == 0:
                        status = "🔄 Processing..."
                    else:
                        status = "⏳ Waiting..."
                    queue_status += f"{status} {file_name}\n"
                if QUEUE_MESSAGE:
                    await QUEUE_MESSAGE.edit(queue_status)
                last_update_time = current_time
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Progress update error: {error_msg}")
                LOGS.info(f"Progress update error: {error_msg}")

    logger.info("Encoding process completed, waiting for final output")
    stdout, stderr = await process.communicate()
    error_output = stderr.decode()

    total_encoding_time = time.time() - start_time
    logger.info(f"Total encoding time: {ts(int(total_encoding_time * 1000))}")

    if error_output:
        logger.error(f"FFMPEG error output: {error_output}")
    else:
        logger.info("Encoding completed successfully")

    # Remove processed file from the queue and update Queue-Status message
    for key, file_data in list(QUEUE.items()):
        if file_data[0] == Path(dl).name:
            del QUEUE[key]
    queue_status = "**📋 Queue Status:**\n"
    for index, (file_id, file_data) in enumerate(QUEUE.items()):
        file_name = file_data[0]
        if index == 0:
            status = "🔄 Processing..."
        else:
            status = "⏳ Waiting..."
        queue_status += f"{status} {file_name}\n"
    if not QUEUE:
        queue_status += "✅ All tasks completed!"
    if QUEUE_MESSAGE:
        await QUEUE_MESSAGE.edit(queue_status)

    return error_output

async def stats(e):
    """Handle stats button press with enhanced information"""
    try:
        wah = e.pattern_match.group(1).decode("UTF-8")
        logger.info(f"Stats button pressed with data: {wah}")

        wh = decode(wah)
        logger.debug(f"Decoded data: {wh}")

        if ";" not in wh:
            logger.error(f"Invalid data format: {wh}")
            return await e.answer("Invalid data format. Please try again.", cache_time=0, alert=True)

        parts = wh.split(";")
        if len(parts) != 3:
            logger.error(f"Expected 3 parts in data, got {len(parts)}: {parts}")
            return await e.answer("Data format error. Please try again.", cache_time=0, alert=True)

        out, dl, id = parts

        if not Path(out).exists() or not Path(dl).exists():
            logger.error(f"File not found. Output: {Path(out).exists()}, Download: {Path(dl).exists()}")
            return await e.answer("Files no longer exist. Process may have completed.", cache_time=0, alert=True)

        try:
            ot = hbs(int(Path(out).stat().st_size))
            ov = hbs(int(Path(dl).stat().st_size))
        except Exception as size_err:
            logger.error(f"Error getting file sizes: {size_err}")
            return await e.answer("Error reading file sizes. Please try again.", cache_time=0, alert=True)

        try:
            org = int(Path(dl).stat().st_size)
            com = int(Path(out).stat().st_size)
            pe = 100 - ((com / org) * 100)
            per = f"{pe:.2f}%"
        except Exception as calc_err:
            logger.error(f"Error calculating percentage: {calc_err}")
            per = "calculating..."

        sys_stats = get_system_stats()
        
        try:
            total_duration = await get_video_duration(dl)
            if Path(out).exists():
                progress_ratio = Path(out).stat().st_size / Path(dl).stat().st_size
                estimated_encoded_seconds = total_duration * progress_ratio
                encoding_rate = f"{estimated_encoded_seconds / total_duration:.2f}x"
            else:
                encoding_rate = "calculating..."
        except Exception as speed_err:
            logger.error(f"Error calculating encoding speed: {speed_err}")
            encoding_rate = "calculating..."

        processing_file_name = Path(dl).name.replace("_", " ")

        ans = (
            f"📁 File: {processing_file_name}\n\n"
            f"📊 Original Size: {ov}\n"
            f"📉 Current Size: {ot}\n"
            f"💯 Compression: {per}\n\n"
            f"🚀 Speed: {encoding_rate}\n"
            f"💻 CPU: {sys_stats['cpu']}%\n"
            f"🧠 RAM: {sys_stats['ram_used']} ({sys_stats['ram_percent']}%)"
        )

        logger.info(f"Sending stats answer: {ans}")
        await e.answer(ans, cache_time=0, alert=True)

    except Exception as er:
        logger.error(f"Stats error: {er}", exc_info=True)
        LOGS.info(f"Stats error: {er}")
        await e.answer(
            "Something went wrong while retrieving stats. Please try again.", 
            cache_time=0, 
            alert=True
        )

async def dl_link(event):
    global QUEUE_MESSAGE
    if not event.is_private:
        return
    if str(event.sender_id) not in OWNER and event.sender_id != DEV:
        return
    link, name = "", ""
    try:
        link = event.text.split()[1]
        name = event.text.split()[2]
    except BaseException:
        pass
    if not link:
        return
    if WORKING or QUEUE:
        QUEUE.update({link: name})
        return await event.reply(f"**✅ Added {link} in QUEUE**")
    WORKING.append(1)
    s = dt.now()
    xxx = await event.reply("**📥 Downloading...**")
    try:
        dl = await fast_download(xxx, link, name)
    except Exception as er:
        WORKING.clear()
        LOGS.info(er)
        return
    es = dt.now()
    kk = dl.split("/")[-1]
    aa = kk.split(".")[-1]
    newFile = dl.replace(f"downloads/", "").replace(f"_", " ")
    rr = "encode"
    bb = kk.replace(f".{aa}", ".mkv")
    out = f"{rr}/{bb}"
    thum = "thumb.jpg"
    dtime = ts(int((es - s).seconds) * 1000)
    hehe = f"{out};{dl};0"
    wah = code(hehe)
    # Create a separate Queue-Status message if not already present.
    if QUEUE_MESSAGE is None:
        QUEUE_MESSAGE = await xxx.client.send_message(xxx.chat_id, "**📋 Queue Status:**\n🔄 Updating...")
    nn = await xxx.edit(
        "**🗜 Compressing...**",
        buttons=[
            [Button.inline("STATS", data=f"stats{wah}")],
            [Button.inline("CANCEL", data=f"skip{wah}")],
        ],
    )

    er = await encode_video(dl, out, nn, wah)

    try:
        if er:
            await xxx.edit(str(er) + "\n\n**ERROR**")
            WORKING.clear()
            os.remove(dl)
            return os.remove(out)
    except BaseException:
        pass

    ees = dt.now()
    ttt = time.time()
    await nn.delete()
    nnn = await xxx.client.send_message(xxx.chat_id, "**📤 Uploading...**")
    with open(out, "rb") as f:
        ok = await upload_file(
            client=xxx.client,
            file=f,
            name=out,
            progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                progress(d, t, nnn, ttt, "**📤 Uploading...**")
            ),
        )
    await nnn.delete()
    org = int(Path(dl).stat().st_size)
    com = int(Path(out).stat().st_size)
    pe = 100 - ((com / org) * 100)
    per = str(f"{pe:.2f}") + "%"
    eees = dt.now()
    x = dtime
    xx = ts(int((ees - es).seconds) * 1000)
    xxxx = ts(int((eees - ees).seconds) * 1000)
    a1 = await info(dl, xxx)
    a2 = await info(out, xxx)
    dk = f"<b>File Name:</b> {newFile}\n\n<b>Original File Size:</b> {hbs(org)}\n<b>Encoded File Size:</b> {hbs(com)}\n<b>Encoded Percentage:</b> {per}\n\n<b>Get Mediainfo Here:</b> <a href='{a1}'>Before</a>/<a href='{a2}'>After</a>\n\n<i>Downloaded in {x}\nEncoded in {xx}\nUploaded in {xxxx}</i>"
    ds = await event.client.send_file(
        event.chat_id, file=ok, caption=dk, force_document=True, link_preview=False, thumb=thum, parse_mode="html"
    )
    os.remove(dl)
    os.remove(out)
    WORKING.clear()

async def encod(event):
    global QUEUE_MESSAGE
    try:
        if not event.is_private:
            return
        if str(event.sender_id) not in OWNER and event.sender_id != DEV:
            return await event.reply("**Sorry You're not An Authorised User!**")
        if not event.media:
            return
        if hasattr(event.media, "document"):
            if not event.media.document.mime_type.startswith(("video", "application/octet-stream")):
                return
        else:
            return
        if WORKING or QUEUE:
            time.sleep(2)
            xxx = await event.reply("**Adding To Queue...**")
            doc = event.media.document
            if doc.id in list(QUEUE.keys()):
                return await xxx.edit("**This File is Already Added in Queue**")
            name = event.file.name
            if not name:
                name = "video_" + dt.now().isoformat("_", "seconds") + ".mp4"
            QUEUE.update({doc.id: [name, doc]})
            return await xxx.edit("**Added This File in Queue**")
        WORKING.append(1)
        xxx = await event.reply("**📥 Downloading...**")
        s = dt.now()
        ttt = time.time()
        dir = f"downloads/"
        try:
            if hasattr(event.media, "document"):
                file = event.media.document
                filename = event.file.name
                if not filename:
                    filename = "video_" + dt.now().isoformat("_", "seconds") + ".mp4"
                dl = dir + filename
                with open(dl, "wb") as f:
                    ok = await download_file(
                        client=event.client,
                        location=file,
                        out=f,
                        progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                            progress(d, t, xxx, ttt, f"**📥 Downloading**\n__{filename}__")
                        ),
                    )
            else:
                dl = await event.client.download_media(
                    event.media,
                    dir,
                    progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                        progress(d, t, xxx, ttt, f"**📥 Downloading**\n__{filename}__")
                    ),
                )
        except Exception as er:
            WORKING.clear()
            LOGS.info(er)
            return os.remove(dl)
        es = dt.now()
        kk = dl.split("/")[-1]
        aa = kk.split(".")[-1]
        rr = f"encode"
        bb = kk.replace(f".{aa}", ".mkv")
        newFile = dl.replace(f"downloads/", "").replace(f"_", " ")
        out = f"{rr}/{bb}"
        thum = "thumb.jpg"
        dtime = ts(int((es - s).seconds) * 1000)
        e = xxx
        hehe = f"{out};{dl};0"
        wah = code(hehe)
        if QUEUE_MESSAGE is None:
            QUEUE_MESSAGE = await event.client.send_message(event.chat_id, "**📋 Queue Status:**\n🔄 Updating...")
        nn = await e.edit(
            "**🗜 Compressing...**",
            buttons=[
                [Button.inline("STATS", data=f"stats{wah}")],
                [Button.inline("CANCEL", data=f"skip{wah}")],
            ],
        )

        er = await encode_video(dl, out, nn, wah)

        try:
            if er:
                await e.edit(str(er) + "\n\n**ERROR**")
                WORKING.clear()
                os.remove(dl)
                return os.remove(out)
        except BaseException as er:
            pass

        ees = dt.now()
        ttt = time.time()
        await nn.delete()
        nnn = await e.client.send_message(e.chat_id, "**📤 Uploading...**")
        with open(out, "rb") as f:
            ok = await upload_file(
                client=e.client,
                file=f,
                name=out,
                progress_callback=lambda d, t: asyncio.get_event_loop().create_task(
                    progress(d, t, nnn, ttt, f"**📤 Uploading**\n__{out.replace(f'encode/', '')}__")
                ),
            )
        await nnn.delete()
        org = int(Path(dl).stat().st_size)
        com = int(Path(out).stat().st_size)
        pe = 100 - ((com / org) * 100)
        per = str(f"{pe:.2f}") + "%"
        eees = dt.now()
        x = dtime
        xx = ts(int((ees - es).seconds) * 1000)
        xxx_time = ts(int((eees - ees).seconds) * 1000)
        a1 = await info(dl, e)
        a2 = await info(out, e)
        dk = f"<b>File Name:</b> {newFile}\n\n<b>Original File Size:</b> {hbs(org)}\n<b>Encoded File Size:</b> {hbs(com)}\n<b>Encoded Percentage:</b> {per}\n\n<b>Get Mediainfo Here:</b> <a href='{a1}'>Before</a>/<a href='{a2}'>After</a>\n\n<i>Downloaded in {x}\nEncoded in {xx}\nUploaded in {xxx_time}</i>"
        ds = await event.client.send_file(
            e.chat_id, file=ok, force_document=True, caption=dk, link_preview=False, thumb=thum, parse_mode="html"
        )
        os.remove(dl)
        os.remove(out)
        WORKING.clear()
    except BaseException as er:
        LOGS.info(er)
        WORKING.clear()