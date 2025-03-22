#    This file is part of the CompressorQueue distribution.
#    Copyright (c) 2021 Danish_00
#    Script Improved by Zylern
#    Modified as per progress bar design and queue fixes

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

# Global FFMPEG version (update as needed)
FFMPEG_VERSION = "ffmpeg 4.4"

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("VideoEncoder")


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
    """Generate a progress bar in the desired style:
    ┃ [■■■■▤□□□□□□□□] 32.09%
    """
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
        boot_time = dt.fromtimestamp(psutil.boot_time())
        uptime_delta = dt.now() - boot_time
        hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h{minutes}m{seconds}s"
    except Exception as e:
        logger.error(f"Error calculating uptime: {str(e)}")
        return "N/A"


def format_elapsed(seconds):
    """Format seconds as Xm, Ys"""
    minutes, sec = divmod(int(seconds), 60)
    return f"{minutes}m, {sec}s"

async def encode_video(dl, out, nn, wah, user_info):
    """Encode video with live progress updates using new progress layout.
    user_info is a tuple: (username, user_id)
    Limited to 350MB RAM
    """
    logger.info(f"Starting video encoding with RAM limit: {dl} -> {out}")
    
    # Add memory limit to ffmpeg command using -memory_size parameter (in bytes)
    # 350MB = 350 * 1024 * 1024 = 367001600 bytes
    memory_limit_bytes = 350 * 1024 * 1024
    
    cmd = f"""ffmpeg -i "{dl}" -memory_size {memory_limit_bytes} {ffmpegcode[0]} "{out}" -y -progress pipe:1 -nostats"""
    logger.debug(f"Running command: {cmd}")

    # Create subprocess with resource limits
    import resource
    
    # Function to set memory limits as preexec_fn for subprocess
    def limit_memory():
        # Set soft limit to 350MB
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
        
    process = await asyncio.create_subprocess_shell(
        cmd, 
        stdout=asyncio.subprocess.PIPE, 
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=limit_memory  # Apply resource limits before executing
    )

    total_duration = await get_video_duration(dl)
    logger.info(f"Total video duration: {total_duration} seconds")

    org_size = int(Path(dl).stat().st_size)
    org_size_str = hbs(org_size)
    logger.info(f"Original file size: {org_size_str}")

    encoded_time = 0
    start_time = time.time()
    update_interval = 3  # seconds
    last_update_time = start_time
    encoding_speeds = []

    logger.info("Starting encoding progress monitoring with 350MB RAM limit")
    while True:
        line = await process.stdout.readline()
        if not line:
            logger.debug("Reached end of ffmpeg output")
            break

        line = line.decode().strip()
        logger.debug(f"FFMPEG progress line: {line}")

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
            cur_size = int(Path(out).stat().st_size) if Path(out).exists() else 0

            compression_percent = 100 - ((cur_size / org_size) * 100) if org_size > 0 else 0
            compression_str = f"{compression_percent:.2f}%" if isinstance(compression_percent, float) else "N/A"

            avg_speed = encoded_time / elapsed_time if elapsed_time > 0 else 0
            remaining_seconds = (total_duration - encoded_time) / avg_speed if avg_speed > 0 else 0
            eta = str(timedelta(seconds=int(remaining_seconds)))
            est = str(timedelta(seconds=int(elapsed_time + remaining_seconds)))  # Total estimated time

            stats = get_system_stats()
            free_disk, free_disk_percent = get_disk_stats()
            uptime = get_uptime()
            tasks_count = len(WORKING) + len(QUEUE) if (WORKING or QUEUE) else 0

            status_message = (
                f"**⎘** __{Path(dl).name}__ | __{percentage:.2f}%__ **⟳**\n"
                f"{progress_bar}\n"
                f"**❖** 𝗢𝗚: __{org_size_str}__ **→** 𝗘𝗡𝗖: __{hbs(cur_size)}__ **__({compression_str})__**\n\n"
                f"**⚡** 𝗦𝗣𝗘𝗘𝗗: **__{encoding_speed:.2f}x__**  | ** ⧖** 𝗘𝗧𝗔: __{eta}__\n"
                f"** ⧗** 𝗘𝗟𝗧: __{timedelta(seconds=int(elapsed_time))}__  | **⌖** 𝗘𝗦𝗧: **__{est}__""\n\n"
                f"** ᚛᚜** 𝗧𝗔𝗦𝗞: __{tasks_count}__ | **⌬** 𝗖𝗣𝗨: __{stats['cpu']}%__ | ** 🜁** 𝗥𝗔𝗠: __{stats['ram_used']} ({stats['ram_percent']}%)__\n"
                f"**⌸** 𝗙 𝗦𝗧𝗢𝗥𝗔𝗚𝗘: __{free_disk}__ (__{free_disk_percent}__)"
            )

            try:
                await nn.edit(
                    status_message,
                    buttons=[
                        [Button.inline("📊 STATS", data=f"stats{wah}")],
                        [Button.inline("❌ CANCEL", data=f"skip{wah}")],
                    ],
                )
                logger.debug("Progress message updated")
                last_update_time = current_time
            except Exception as e:
                logger.error(f"Progress update error: {str(e)}")

    logger.info("Encoding process completed, waiting for final output")
    stdout, stderr = await process.communicate()
    error_output = stderr.decode()

    total_encoding_time = time.time() - start_time
    logger.info(f"Total encoding time: {ts(int(total_encoding_time * 1000))}")

    if error_output:
        logger.error(f"FFMPEG error output: {error_output}")
    else:
        logger.info("Encoding completed successfully")

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
            logger.error("File not found for stats request")
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
        await e.answer("Something went wrong while retrieving stats. Please try again.", cache_time=0, alert=True)


async def dl_link(event):
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
    newFile = dl.replace("downloads/", "").replace("_", " ")
    rr = "encode"
    bb = kk.replace(f".{aa}", ".mkv")
    out = f"{rr}/{bb}"
    thum = "thumb.jpg"
    dtime = ts(int((es - s).seconds) * 1000)
    hehe = f"{out};{dl};{event.sender_id}"
    wah = code(hehe)
    # Pass user info: (username, user id)
    user_info = (getattr(event.sender, "username", None) or event.sender.first_name, event.sender_id)
    nn = await xxx.edit(
        "**🗜 Compressing...**",
        buttons=[
            [Button.inline("STATS", data=f"stats{wah}")],
            [Button.inline("CANCEL", data=f"skip{wah}")],
        ],
    )

    er = await encode_video(dl, out, nn, wah, user_info)

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
    per = f"{pe:.2f}%"
    eees = dt.now()
    x = dtime
    xx = ts(int((ees - es).seconds) * 1000)
    xxx_time = ts(int((eees - ees).seconds) * 1000)
    a1 = await info(dl, xxx)
    a2 = await info(out, xxx)
    dk = (f"<b>File Name:</b> {newFile}\n\n"
          f"<b>Original File Size:</b> {hbs(org)}\n"
          f"<b>Encoded File Size:</b> {hbs(com)}\n"
          f"<b>Encoded Percentage:</b> {per}\n\n"
          f"<b>Get Mediainfo Here:</b> <a href='{a1}'>Before</a>/<a href='{a2}'>After</a>\n\n"
          f"<i>Downloaded in {x}\nEncoded in {xx}\nUploaded in {xxx_time}</i>")
    ds = await event.client.send_file(
        event.chat_id, file=ok, force_document=True, caption=dk, link_preview=False, thumb=thum, parse_mode="html"
    )
    os.remove(dl)
    os.remove(out)
    WORKING.clear()


async def encod(event):
    try:
        if not event.is_private:
            return
        event.sender
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
                return await xxx.edit("**This File is Already Added in QUEUE**")
            name = event.file.name
            if not name:
                name = "video_" + dt.now().isoformat("_", "seconds") + ".mp4"
            QUEUE.update({doc.id: [name, doc]})
            return await xxx.edit("**Added This File in Queue**")
        WORKING.append(1)
        xxx = await event.reply("**📥 Downloading...**")
        s = dt.now()
        ttt = time.time()
        dir = "downloads/"
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
        rr = "encode"
        bb = kk.replace(f".{aa}", ".mkv")
        newFile = dl.replace("downloads/", "").replace("_", " ")
        out = f"{rr}/{bb}"
        thum = "thumb.jpg"
        dtime = ts(int((es - s).seconds) * 1000)
        e = xxx
        hehe = f"{out};{dl};{event.sender_id}"
        wah = code(hehe)
        # Pass user info: (username, user id)
        user_info = (getattr(event.sender, "username", None) or event.sender.first_name, event.sender_id)
        nn = await e.edit(
            "**🗜 Compressing...**",
            buttons=[
                [Button.inline("STATS", data=f"stats{wah}")],
                [Button.inline("CANCEL", data=f"skip{wah}")],
            ],
        )

        er = await encode_video(dl, out, nn, wah, user_info)

        try:
            if er:
                await e.edit(str(er) + "\n\n**ERROR**")
                WORKING.clear()
                os.remove(dl)
                return os.remove(out)
        except BaseException:
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
                    progress(d, t, nnn, ttt, f"**📤 Uploading**\n__{out.replace('encode/', '')}__")
                ),
            )
        await nnn.delete()
        org = int(Path(dl).stat().st_size)
        com = int(Path(out).stat().st_size)
        pe = 100 - ((com / org) * 100)
        per = f"{pe:.2f}%"
        eees = dt.now()
        x = dtime
        xx = ts(int((ees - es).seconds) * 1000)
        xxx_time = ts(int((eees - ees).seconds) * 1000)
        a1 = await info(dl, e)
        a2 = await info(out, e)
        dk = (f"<b>File Name:</b> {newFile}\n\n"
              f"<b>Original File Size:</b> {hbs(org)}\n"
              f"<b>Encoded File Size:</b> {hbs(com)}\n"
              f"<b>Encoded Percentage:</b> {per}\n\n"
              f"<b>Get Mediainfo Here:</b> <a href='{a1}'>Before</a>/<a href='{a2}'>After</a>\n\n"
              f"<i>Downloaded in {x}\nEncoded in {xx}\nUploaded in {xxx_time}</i>")
        ds = await event.client.send_file(
            event.chat_id, file=ok, force_document=True, caption=dk, link_preview=False, thumb=thum, parse_mode="html"
        )
        os.remove(dl)
        os.remove(out)
        WORKING.clear()
    except BaseException as er:
        LOGS.info(er)
        WORKING.clear()