# main.py

# =========================================================
# FAST LUCIFER DONGHUA DOWNLOADER BOT
# =========================================================

import os
import re
import math
import time
import asyncio
import subprocess

from pyrogram import Client, filters
from playwright.async_api import async_playwright

# =========================================================
# CONFIG
# =========================================================

API_ID = 
API_HASH = "32d454f51fc7b3b3c7d51c4f80f628b5"
BOT_TOKEN = ""

OWNER_ID = [1685470205]

DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# =========================================================
# BOT
# =========================================================

app = Client(
    "lucifer_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=50
)

USER_MODE = {}

# =========================================================
# UTIL
# =========================================================

def clean_name(name):

    remove_words = [
        " - Lucifer Donghua.in - ChineseDonghua Anime Stream",
        "Lucifer Donghua.in",
        "ChineseDonghua Anime Stream"
    ]

    for w in remove_words:
        name = name.replace(w, "")

    name = re.sub(r'[\\/:*?"<>|]', '', name)

    name = re.sub(r'\s+', ' ', name).strip()

    return name

def run(cmd):

    subprocess.run(cmd, shell=True)

def get_duration(file):

    cmd = f'''
ffprobe -v error \
-show_entries format=duration \
-of default=noprint_wrappers=1:nokey=1 \
"{file}"
'''

    out = subprocess.check_output(
        cmd,
        shell=True
    ).decode().strip()

    return float(out)

# =========================================================
# TG STATUS
# =========================================================

async def update_status(msg, text):

    try:
        await msg.edit(text)
    except:
        pass

# =========================================================
# EXTRACT VIDEO
# =========================================================

async def extract_video(post_url, msg):

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--start-maximized"
            ]
        )

        context = await browser.new_context(
            viewport={
                "width": 1366,
                "height": 768
            },
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            accept_downloads=True
        )

        page = await context.new_page()

        # =====================================================
        # STEALTH
        # =====================================================

        await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        window.chrome = {
            runtime: {}
        };

        Object.defineProperty(navigator, 'plugins', {
            get: () => [1,2,3,4,5]
        });

        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        """)

        await update_status(
            msg,
            "🌐 Opening Lucifer Donghua page..."
        )

        await page.goto(post_url, timeout=0)

        await page.wait_for_timeout(7000)

        title = await page.title()

        title = clean_name(title)

        # =====================================================
        # FIND DOWNLOAD BUTTON
        # =====================================================

        await update_status(
            msg,
            "🔍 Finding download button..."
        )

        buttons = await page.locator("a").all()

        target_btn = None

        for btn in buttons:

            try:

                txt = (
                    await btn.inner_text()
                ).strip().lower()

                if "download" in txt:

                    target_btn = btn

            except:
                pass

        if not target_btn:

            raise Exception(
                "Download button not found"
            )

        await update_status(
            msg,
            "☁ Opening download page..."
        )

        async with context.expect_page() as page_info:

            await target_btn.click(force=True)

        redirect_page = await page_info.value

        await redirect_page.wait_for_load_state()

        # =====================================================
        # LOOP
        # =====================================================

        for _ in range(60):

            await redirect_page.wait_for_timeout(4000)

            btns = await redirect_page.locator(
                "button,a"
            ).all()

            for b in btns:

                try:

                    txt = (
                        await b.inner_text()
                    ).strip().lower()

                    # =============================================
                    # GET VIDEO
                    # =============================================

                    if "get video" in txt:

                        await update_status(
                            msg,
                            "⚡ Generating download link..."
                        )

                        await b.click(force=True)

                        await redirect_page.wait_for_timeout(
                            10000
                        )

                        break

                    # =============================================
                    # WAIT
                    # =============================================

                    elif "getting download link" in txt:

                        await update_status(
                            msg,
                            "⏳ Waiting for server..."
                        )

                        await redirect_page.wait_for_timeout(
                            12000
                        )

                        break

                    # =============================================
                    # DOWNLOAD
                    # =============================================

                    elif txt == "download":

                        await update_status(
                            msg,
                            "⬇ Starting download..."
                        )

                        async with redirect_page.expect_download(
                            timeout=120000
                        ) as dl:

                            await b.click(force=True)

                        download = await dl.value

                        save_path = f"{DOWNLOAD_DIR}/{title}_raw.mp4"

                        await download.save_as(save_path)

                        await browser.close()

                        return title, save_path

                except:
                    pass

        await browser.close()

        raise Exception("Final video not found")

# =========================================================
# FAST ENCODE
# =========================================================

async def encode_480p(
    input_file,
    output_file,
    msg
):

    await update_status(
        msg,
        "⚡ Fast encoding started..."
    )

    cmd = f'''
ffmpeg -y \
-ss 00:01:26 \
-i "{input_file}" \
-vf scale=-2:480 \
-c:v libx264 \
-crf 32 \
-preset ultrafast \
-pix_fmt yuv420p \
-profile:v baseline \
-level 3.0 \
-c:a aac \
-b:a 64k \
-ar 44100 \
-ac 2 \
-movflags +faststart \
-map_metadata -1 \
"{output_file}"
'''

    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    while True:

        if process.returncode is not None:
            break

        await update_status(
            msg,
            "🎞 Encoding video to 480p..."
        )

        await asyncio.sleep(5)

        if process.returncode is not None:
            break

    await process.communicate()

# =========================================================
# THUMBNAIL
# =========================================================

def make_thumb(video, thumb):

    cmd = f'''
ffmpeg -y \
-i "{video}" \
-ss 00:00:30 \
-vframes 1 \
"{thumb}"
'''

    run(cmd)

# =========================================================
# UPLOAD PROGRESS
# =========================================================

async def progress(current, total, msg):

    percent = current * 100 / total

    filled = math.floor(percent / 10)

    bar = "█" * filled + "░" * (10 - filled)

    speed = current / 1024 / 1024

    text = f"""
📤 Uploading to Telegram...

[{bar}] {round(percent,2)}%

📦 Uploaded: {round(speed,2)} MB
"""

    try:
        await msg.edit(text)
    except:
        pass

# =========================================================
# PROCESS
# =========================================================

async def process_link(message, link):

    user_id = message.from_user.id

    if user_id not in OWNER_ID:

        return await message.reply(
            "❌ Not allowed"
        )

    try:

        msg = await message.reply(
            "🔍 Starting process..."
        )

        # =====================================================
        # DOWNLOAD
        # =====================================================

        title, raw_file = await extract_video(
            link,
            msg
        )

        encoded_file = (
            f"{DOWNLOAD_DIR}/{title}_480p.mp4"
        )

        thumb = (
            f"{DOWNLOAD_DIR}/{title}.jpg"
        )

        # =====================================================
        # ENCODE
        # =====================================================

        await encode_480p(
            raw_file,
            encoded_file,
            msg
        )

        # =====================================================
        # THUMB
        # =====================================================

        await update_status(
            msg,
            "🖼 Creating thumbnail..."
        )

        make_thumb(
            encoded_file,
            thumb
        )

        # =====================================================
        # FILE SIZE
        # =====================================================

        size = (
            os.path.getsize(encoded_file)
            / 1024 / 1024
        )

        await update_status(
            msg,
            f"📦 Final Size: {round(size,2)} MB"
        )

        # =====================================================
        # UPLOAD
        # =====================================================

        await asyncio.sleep(2)

        duration = int(
            get_duration(encoded_file)
        )

        await app.send_video(
            chat_id=message.chat.id,
            video=encoded_file,
            caption=f"{title}",
            thumb=thumb,
            duration=duration,
            width=854,
            height=480,
            supports_streaming=True,
            progress=progress,
            progress_args=(msg,)
        )

        await update_status(
            msg,
            "✅ Upload completed!"
        )

        # =====================================================
        # CLEANUP
        # =====================================================

        try:
            os.remove(raw_file)
            os.remove(encoded_file)
            os.remove(thumb)
        except:
            pass

    except Exception as e:

        print(e)

        await message.reply(
            f"❌ Error:\n{e}"
        )

# =========================================================
# COMMANDS
# =========================================================

@app.on_message(filters.command("start"))
async def start(_, message):

    await message.reply(
        "🔥 Lucifer Donghua Downloader Bot\n\n"
        "/help\n"
        "/mode manual\n"
        "/mode automatic\n"
        "/chklink LINK"
    )

@app.on_message(filters.command("help"))
async def help_cmd(_, message):

    await message.reply(
        "manual:\nUse /chklink LINK\n\n"
        "automatic:\nSend link directly"
    )

@app.on_message(filters.command("mode"))
async def mode(_, message):

    try:

        mode = (
            message.text.split(" ")[1]
            .lower()
        )

        if mode not in [
            "manual",
            "automatic"
        ]:

            return await message.reply(
                "Use manual or automatic"
            )

        USER_MODE[
            message.from_user.id
        ] = mode

        await message.reply(
            f"✅ Mode set to {mode}"
        )

    except:

        await message.reply(
            "/mode manual"
        )

@app.on_message(filters.command("chklink"))
async def chk(_, message):

    try:

        link = message.text.split(
            " ",
            1
        )[1]

        await process_link(
            message,
            link
        )

    except:

        await message.reply(
            "❌ Invalid link"
        )

@app.on_message(filters.text)
async def auto(_, message):

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
# RUN
# =========================================================

print("BOT STARTED")

app.run()
