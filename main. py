# main.py
# Telegram Lucifer Donghua Downloader Bot
# Features:
# - Auto/manual mode
# - Bypass redirect pages
# - Download final mp4
# - Remove first 1m26s
# - Encode 480p under 150MB
# - Upload as Telegram media video with thumbnail
# - Commands: /start /help /mode /chklink

import os
import re
import json
import time
import asyncio
import requests
import subprocess
from bs4 import BeautifulSoup
from pyrogram import Client, filters
from pyrogram.types import Message
from playwright.async_api import async_playwright

API_ID = 123456
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"

OWNER_ID = [123456789]

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

app = Client(
    "lucifer_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

USER_MODE = {}

# ===========================================
# UTIL
# ===========================================

def clean_name(name):
    return re.sub(r'[\\/:*?"<>|]', '', name)

def run(cmd):
    subprocess.run(cmd, shell=True)

def get_duration(file):
    cmd = f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file}"'
    out = subprocess.check_output(cmd, shell=True).decode().strip()
    return float(out)

# ===========================================
# SCRAPER
# ===========================================

async def extract_video(post_url):

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Opening post page...")
        await page.goto(post_url, timeout=0)

        await page.wait_for_timeout(7000)

        html = await page.content()

        soup = BeautifulSoup(html, "html.parser")

        title = soup.title.text.strip()
        title = clean_name(title)

        print("Searching second red button...")

        buttons = await page.locator("a").all()

        target = None

        for btn in buttons:
            try:
                text = await btn.inner_text()
                if "Download" in text:
                    href = await btn.get_attribute("href")
                    target = href
            except:
                pass

        if not target:
            raise Exception("Download button not found")

        print("Opening redirect page...")
        await page.goto(target, timeout=0)

        await page.wait_for_timeout(8000)

        # click GET VIDEO
        try:
            await page.locator("text=Get Video").click()
        except:
            pass

        await page.wait_for_timeout(5000)

        # click DOWNLOAD
        try:
            await page.locator("text=Download").click()
        except:
            pass

        video_url = None

        for _ in range(20):

            content = await page.content()

            urls = re.findall(r'https?://[^\s"\']+\.mp4[^\s"\']*', content)

            if urls:
                video_url = urls[0]
                break

            await page.wait_for_timeout(2000)

        if not video_url:
            raise Exception("Final video URL not found")

        await browser.close()

        return title, video_url

# ===========================================
# DOWNLOAD
# ===========================================

def download_video(url, output):

    r = requests.get(url, stream=True)

    with open(output, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

# ===========================================
# ENCODE
# ===========================================

def encode_480p(input_file, output_file):

    duration = get_duration(input_file) - 86

    target_size = 150 * 1024 * 1024

    audio_bitrate = 64000

    video_bitrate = int((target_size * 8 / duration) - audio_bitrate)

    if video_bitrate < 250000:
        video_bitrate = 250000

    cmd = f'''
ffmpeg -y -ss 00:01:26 -i "{input_file}" \
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

# ===========================================
# THUMBNAIL
# ===========================================

def make_thumb(video, thumb):

    cmd = f'ffmpeg -y -i "{video}" -ss 00:00:30 -vframes 1 "{thumb}"'
    run(cmd)

# ===========================================
# PROCESS
# ===========================================

async def process_link(message: Message, link):

    user_id = message.from_user.id

    if user_id not in OWNER_ID:
        return

    try:

        msg = await message.reply("🔍 Extracting video...")

        title, video_url = await extract_video(link)

        raw_file = f"{DOWNLOAD_DIR}/{title}.mp4"
        enc_file = f"{DOWNLOAD_DIR}/{title}_480p.mp4"
        thumb = f"{DOWNLOAD_DIR}/{title}.jpg"

        await msg.edit("⬇ Downloading video...")

        download_video(video_url, raw_file)

        await msg.edit("🎞 Encoding 480p under 150MB...")

        encode_480p(raw_file, enc_file)

        await msg.edit("🖼 Creating thumbnail...")

        make_thumb(enc_file, thumb)

        await msg.edit("📤 Uploading...")

        await app.send_video(
            chat_id=message.chat.id,
            video=enc_file,
            caption=title,
            thumb=thumb,
            supports_streaming=True
        )

        await msg.delete()

        os.remove(raw_file)
        os.remove(enc_file)
        os.remove(thumb)

    except Exception as e:
        await message.reply(f"❌ Error:\n{e}")

# ===========================================
# COMMANDS
# ===========================================

@app.on_message(filters.command("start"))
async def start(_, message):

    await message.reply(
        "🔥 Lucifer Donghua Downloader Bot\n\n"
        "/help\n"
        "/mode automatic\n"
        "/mode manual\n"
        "/chklink LINK"
    )

@app.on_message(filters.command("help"))
async def help_cmd(_, message):

    await message.reply(
        "Modes:\n\n"
        "automatic = send link directly\n"
        "manual = use /chklink link"
    )

@app.on_message(filters.command("mode"))
async def mode(_, message):

    try:
        mode = message.text.split(" ")[1].lower()

        if mode not in ["manual", "automatic"]:
            return await message.reply("Use manual or automatic")

        USER_MODE[message.from_user.id] = mode

        await message.reply(f"✅ Mode set to {mode}")

    except:
        await message.reply("/mode manual")

@app.on_message(filters.command("chklink"))
async def chk(_, message):

    try:

        link = message.text.split(" ", 1)[1]

        await process_link(message, link)

    except:
        await message.reply("❌ Invalid link")

@app.on_message(filters.text)
async def auto(_, message):

    user_id = message.from_user.id

    mode = USER_MODE.get(user_id, "manual")

    if mode != "automatic":
        return

    text = message.text.strip()

    if "luciferdonghua.in" in text:

        await process_link(message, text)

# ===========================================
# START
# ===========================================

print("BOT STARTED")
app.run()
