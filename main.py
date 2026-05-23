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

API_ID = 123456
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"

OWNER_ID = [123456789]

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =========================================================
# BOT
# =========================================================

app = Client(
    "lucifer_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

USER_MODE = {}

# =========================================================
# UTIL
# =========================================================

def clean_name(name):

    return re.sub(r'[\\/:*?"<>|]', '', name)


def run(cmd):

    subprocess.run(cmd, shell=True)


def get_duration(file):

    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file}"'

    out = subprocess.check_output(cmd, shell=True).decode().strip()

    return float(out)


# =========================================================
# EXTRACT VIDEO
# =========================================================

async def extract_video(post_url):

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = await browser.new_context()

        page = await context.new_page()

        print("Opening post page...")

        await page.goto(post_url, timeout=0)

        await page.wait_for_timeout(8000)

        title = await page.title()

        title = clean_name(title)

        print("Finding red cloud button...")

        buttons = await page.locator("a").all()

        target_btn = None

        for btn in buttons:

            try:

                txt = await btn.inner_text()

                if "Download" in txt:

                    href = await btn.get_attribute("href")

                    if href:

                        target_btn = btn

            except:
                pass

        if not target_btn:

            raise Exception("Download button not found")

        print("Clicking red cloud button...")

        async with context.expect_page() as page_info:

            await target_btn.click(force=True)

        redirect_page = await page_info.value

        await redirect_page.wait_for_load_state()

        print("Redirect page opened")

        # =====================================================
        # HANDLE REDIRECTS
        # =====================================================

        for _ in range(20):

            try:

                current = redirect_page.url

                print(f"Current URL: {current}")

                html = await redirect_page.content()

                # =================================================
                # FIND MP4
                # =================================================

                mp4s = re.findall(
                    r'https?://[^\s"\']+\.mp4[^\s"\']*',
                    html
                )

                if mp4s:

                    print("FINAL MP4 FOUND")

                    await browser.close()

                    return title, mp4s[0]

                # =================================================
                # FIND BUTTONS
                # =================================================

                btns = await redirect_page.locator("button,a").all()

                clicked = False

                for b in btns:

                    try:

                        txt = (await b.inner_text()).lower()

                        # GET VIDEO
                        if "get video" in txt:

                            print("CLICK GET VIDEO")

                            await b.click(force=True)

                            await redirect_page.wait_for_timeout(6000)

                            clicked = True
                            break

                        # DOWNLOAD
                        elif "download" in txt:

                            print("CLICK DOWNLOAD")

                            await b.click(force=True)

                            await redirect_page.wait_for_timeout(6000)

                            clicked = True
                            break

                    except:
                        pass

                if clicked:
                    continue

                # =================================================
                # REDIRECT FIX
                # =================================================

                print("GOING BACK")

                try:

                    await redirect_page.go_back(timeout=10000)

                except:
                    pass

                await redirect_page.wait_for_timeout(4000)

            except Exception as e:

                print(e)

        await browser.close()

        raise Exception("Final video URL not found")

# =========================================================
# DOWNLOAD VIDEO
# =========================================================

def download_video(url, output):

    print("Downloading final mp4...")

    r = requests.get(url, stream=True)

    total = 0

    with open(output, "wb") as f:

        for chunk in r.iter_content(chunk_size=1024 * 1024):

            if chunk:

                total += len(chunk)

                f.write(chunk)

                mb = total / 1024 / 1024

                print(f"Downloaded {mb:.2f} MB")

# =========================================================
# ENCODE
# =========================================================

def encode_480p(input_file, output_file):

    duration = get_duration(input_file)

    duration = duration - 86

    target_size = 150 * 1024 * 1024

    audio_bitrate = 64000

    video_bitrate = int((target_size * 8 / duration) - audio_bitrate)

    if video_bitrate < 250000:
        video_bitrate = 250000

    print("Encoding started...")

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

    print("Encoding completed")

# =========================================================
# THUMBNAIL
# =========================================================

def make_thumb(video, thumb):

    cmd = f'''
ffmpeg -y -i "{video}" -ss 00:00:30 -vframes 1 "{thumb}"
'''

    run(cmd)

# =========================================================
# PROCESS
# =========================================================

async def process_link(message, link):

    user_id = message.from_user.id

    if user_id not in OWNER_ID:

        return await message.reply("Not allowed")

    try:

        msg = await message.reply("🔍 Extracting video...")

        title, video_url = await extract_video(link)

        raw_file = f"{DOWNLOAD_DIR}/{title}.mp4"

        encoded_file = f"{DOWNLOAD_DIR}/{title}_480p.mp4"

        thumb = f"{DOWNLOAD_DIR}/{title}.jpg"

        await msg.edit("⬇ Downloading video...")

        download_video(video_url, raw_file)

        await msg.edit("🎞 Encoding video...")

        encode_480p(raw_file, encoded_file)

        await msg.edit("🖼 Creating thumbnail...")

        make_thumb(encoded_file, thumb)

        await msg.edit("📤 Uploading to Telegram...")

        await app.send_video(
            chat_id=message.chat.id,
            video=encoded_file,
            caption=title,
            thumb=thumb,
            supports_streaming=True
        )

        await msg.delete()

        # CLEANUP
        os.remove(raw_file)
        os.remove(encoded_file)
        os.remove(thumb)

    except Exception as e:

        print(e)

        await message.reply(f"❌ Error:\n{e}")

# =========================================================
# START
# =========================================================

@app.on_message(filters.command("start"))
async def start(_, message):

    txt = """
🔥 Lucifer Donghua Downloader Bot

Commands:

/help
/mode manual
/mode automatic
/chklink LINK
"""

    await message.reply(txt)

# =========================================================
# HELP
# =========================================================

@app.on_message(filters.command("help"))
async def help_cmd(_, message):

    txt = """
manual:
Use /chklink LINK

automatic:
Just send link directly
"""

    await message.reply(txt)

# =========================================================
# MODE
# =========================================================

@app.on_message(filters.command("mode"))
async def mode(_, message):

    try:

        mode = message.text.split(" ")[1].lower()

        if mode not in ["manual", "automatic"]:

            return await message.reply("Use manual or automatic")

        USER_MODE[message.from_user.id] = mode

        await message.reply(f"✅ Mode changed to {mode}")

    except:

        await message.reply("/mode manual")

# =========================================================
# MANUAL
# =========================================================

@app.on_message(filters.command("chklink"))
async def chk(_, message):

    try:

        link = message.text.split(" ", 1)[1]

        await process_link(message, link)

    except:

        await message.reply("❌ Invalid link")

# =========================================================
# AUTOMATIC
# =========================================================

@app.on_message(filters.text)
async def auto(_, message):

    user_id = message.from_user.id

    mode = USER_MODE.get(user_id, "manual")

    if mode != "automatic":
        return

    text = message.text.strip()

    if "luciferdonghua.in" in text:

        await process_link(message, text)

# =========================================================
# RUN
# =========================================================

print("BOT STARTED")

app.run()
