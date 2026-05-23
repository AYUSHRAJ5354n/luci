# main.py
# FULL LUCIFER DONGHUA DOWNLOADER BOT

import os
import re
import math
import shutil
import asyncio
import subprocess
import requests

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from playwright.async_api import async_playwright

# =========================================================
# CONFIG
# =========================================================

API_ID = 
API_HASH = ""
BOT_TOKEN = ""

OWNER_IDS = [1685470205]

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =========================================================
# BOT
# =========================================================

bot = Client(
    "LuciferDownloaderBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# =========================================================
# USER MODES
# =========================================================

USER_MODE = {}

# =========================================================
# UTILS
# =========================================================

def clean_filename(name):

    name = re.sub(r'[\\/:*?"<>|]', "", name)
    return name.strip()

def run(cmd):

    subprocess.run(
        cmd,
        shell=True
    )

def get_duration(file):

    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file}"'

    out = subprocess.check_output(
        cmd,
        shell=True
    ).decode().strip()

    return float(out)

def get_size_mb(path):

    return os.path.getsize(path) / (1024 * 1024)

# =========================================================
# EXTRACT VIDEO
# =========================================================

async def extract_video(post_url):

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )

        page = await browser.new_page(
            viewport={
                "width": 430,
                "height": 932
            },
            user_agent="Mozilla/5.0 (Linux; Android 13; Mobile)"
        )

        print("Opening post page...")

        await page.goto(
            post_url,
            timeout=0
        )

        await page.wait_for_timeout(10000)

        title = await page.title()

        title = title.replace(" - Lucifer Donghua", "")

        title = clean_filename(title)

        print("Finding red cloud button...")

        clicked = False

        buttons = await page.locator("a").all()

        for btn in buttons:

            try:

                html = await btn.inner_html()

                if (
                    "download" in html.lower()
                    or "fa-download" in html.lower()
                    or "cloud" in html.lower()
                ):

                    try:

                        await btn.click()

                        clicked = True

                        print("Clicked red cloud button")

                        break

                    except:
                        pass

            except:
                pass

        if not clicked:
            raise Exception("Red cloud button not found")

        await page.wait_for_timeout(10000)

        print("Handling redirects...")

        for i in range(10):

            try:

                await page.wait_for_load_state("networkidle")

            except:
                pass

            await page.wait_for_timeout(3000)

            # GET VIDEO

            try:

                btn = page.locator("text=Get Video")

                if await btn.count() > 0:

                    await btn.click()

                    print("Clicked GET VIDEO")

                    await page.wait_for_timeout(6000)

            except:
                pass

            # DOWNLOAD

            try:

                btn2 = page.locator("text=Download")

                if await btn2.count() > 0:

                    await btn2.click()

                    print("Clicked DOWNLOAD")

                    await page.wait_for_timeout(6000)

            except:
                pass

            html = await page.content()

            urls = re.findall(
                r'https?://[^\s"\']+\.mp4[^\s"\']*',
                html
            )

            if urls:

                final_url = urls[0]

                print("FOUND MP4")

                await browser.close()

                return title, final_url

        raise Exception("Final mp4 not found")

# =========================================================
# DOWNLOAD VIDEO
# =========================================================

def download_video(url, output):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(
        url,
        headers=headers,
        stream=True
    )

    total = int(r.headers.get("content-length", 0))

    downloaded = 0

    with open(output, "wb") as f:

        for chunk in r.iter_content(chunk_size=1024 * 1024):

            if chunk:

                f.write(chunk)

                downloaded += len(chunk)

                if total > 0:

                    percent = downloaded * 100 / total

                    print(f"{percent:.2f}%")

# =========================================================
# ENCODE 480P UNDER 150MB
# =========================================================

def encode_video(input_file, output_file):

    duration = get_duration(input_file)

    duration = duration - 86

    target_size = 150 * 1024 * 1024

    audio_bitrate = 64000

    video_bitrate = int(
        ((target_size * 8) / duration) - audio_bitrate
    )

    if video_bitrate < 250000:
        video_bitrate = 250000

    cmd = f'''
ffmpeg -y \
-ss 00:01:26 \
-i "{input_file}" \
-vf scale=-2:480 \
-c:v libx264 \
-b:v {video_bitrate} \
-preset veryfast \
-c:a aac \
-b:a 64k \
-movflags +faststart \
"{output_file}"
'''

    run(cmd)

# =========================================================
# THUMBNAIL
# =========================================================

def create_thumbnail(video, thumb):

    cmd = f'''
ffmpeg -y \
-i "{video}" \
-ss 00:00:20 \
-vframes 1 \
"{thumb}"
'''

    run(cmd)

# =========================================================
# PROCESS
# =========================================================

async def process_link(message, link):

    user_id = message.from_user.id

    if user_id not in OWNER_IDS:

        return await message.reply(
            "Unauthorized"
        )

    status = await message.reply(
        "🔍 Extracting video..."
    )

    try:

        title, video_url = await extract_video(link)

        raw_path = f"{DOWNLOAD_DIR}/{title}.mp4"

        encoded_path = f"{DOWNLOAD_DIR}/{title}_480p.mp4"

        thumb_path = f"{DOWNLOAD_DIR}/{title}.jpg"

        await status.edit(
            "⬇ Downloading..."
        )

        download_video(video_url, raw_path)

        await status.edit(
            "🎞 Encoding 480p..."
        )

        encode_video(
            raw_path,
            encoded_path
        )

        size = get_size_mb(encoded_path)

        print(f"FINAL SIZE: {size:.2f} MB")

        await status.edit(
            "🖼 Creating thumbnail..."
        )

        create_thumbnail(
            encoded_path,
            thumb_path
        )

        await status.edit(
            "📤 Uploading..."
        )

        await bot.send_video(
            chat_id=message.chat.id,
            video=encoded_path,
            caption=title,
            thumb=thumb_path,
            supports_streaming=True
        )

        await status.delete()

        try:
            os.remove(raw_path)
        except:
            pass

        try:
            os.remove(encoded_path)
        except:
            pass

        try:
            os.remove(thumb_path)
        except:
            pass

    except Exception as e:

        await status.edit(
            f"❌ Error:\n{e}"
        )

# =========================================================
# COMMANDS
# =========================================================

@bot.on_message(filters.command("start"))
async def start(_, message):

    text = """
🔥 Lucifer Donghua Downloader Bot

Commands:

/help
/mode manual
/mode automatic
/chklink LINK

Modes:

manual:
Use /chklink link

automatic:
Send link directly
"""

    await message.reply(text)

# =========================================================

@bot.on_message(filters.command("help"))
async def help_cmd(_, message):

    await message.reply(
        "Use Lucifer Donghua post link only."
    )

# =========================================================

@bot.on_message(filters.command("mode"))
async def mode_cmd(_, message):

    try:

        mode = message.text.split(" ")[1].lower()

        if mode not in ["manual", "automatic"]:

            return await message.reply(
                "Use manual or automatic"
            )

        USER_MODE[message.from_user.id] = mode

        await message.reply(
            f"✅ Mode changed to {mode}"
        )

    except:

        await message.reply(
            "/mode manual"
        )

# =========================================================

@bot.on_message(filters.command("chklink"))
async def chklink(_, message):

    try:

        link = message.text.split(" ", 1)[1]

        if "luciferdonghua.in" not in link:

            return await message.reply(
                "Invalid link"
            )

        await process_link(
            message,
            link
        )

    except:

        await message.reply(
            "Usage:\n/chklink LINK"
        )

# =========================================================

@bot.on_message(filters.text)
async def auto_mode(_, message):

    user_id = message.from_user.id

    mode = USER_MODE.get(
        user_id,
        "manual"
    )

    if mode != "automatic":
        return

    text = message.text.strip()

    if "luciferdonghua.in" in text:

        await process_link(
            message,
            text
        )

# =========================================================
# START BOT
# =========================================================

print("BOT STARTED")

bot.run()
