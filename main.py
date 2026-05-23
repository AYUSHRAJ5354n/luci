# main.py

# =========================================================
# FAST LUCIFER DONGHUA DOWNLOADER BOT
# QUEUE + CHANNEL UPLOAD + FLOODWAIT SAFE
# =========================================================

import os
import re
import math
import time
import signal
import asyncio
import subprocess

from collections import deque

from pyrogram import Client, filters
from pyrogram.errors import FloodWait

from playwright.async_api import async_playwright

# =========================================================
# CONFIG
# =========================================================

API_ID = 
API_HASH = "32d454f51fc7b3b3c7d51c4f80f628b5"
BOT_TOKEN = "YOUR_BOT_TOKEN"

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

# =========================================================
# GLOBALS
# =========================================================

USER_MODE = {}

QUEUE = deque()

PROCESSING = False

UPLOAD_CHANNEL = None

LAST_STATUS = {}

# =========================================================
# UTIL
# =========================================================

def clean_name(name):

    remove_words = [

        " - Lucifer Donghua.in - ChineseDonghua Anime Stream",
        "- Lucifer Donghua.in - ChineseDonghua Anime Stream",

        "Lucifer Donghua.in - ChineseDonghua Anime Stream",

        "ChineseDonghua Anime Stream",

        "Lucifer Donghua.in",

        "- ChineseDonghua Anime Stream",

        " - ChineseDonghua Anime Stream"
    ]

    for w in remove_words:

        name = name.replace(w, "")

    name = re.sub(r'[\\/:*?"<>|]', '', name)

    name = re.sub(r'\s+', ' ', name).strip()

    return name

def run(cmd):

    process = subprocess.Popen(
        cmd,
        shell=True,
        preexec_fn=os.setsid
    )

    try:

        process.wait(timeout=1800)

    except subprocess.TimeoutExpired:

        os.killpg(
            os.getpgid(process.pid),
            signal.SIGTERM
        )

        print("PROCESS KILLED")

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
# SAFE EDIT
# =========================================================

async def safe_edit(msg, text):

    try:

        old = LAST_STATUS.get(msg.id)

        if old == text:
            return

        LAST_STATUS[msg.id] = text

        await msg.edit(text)

        await asyncio.sleep(15)

    except FloodWait as e:

        await asyncio.sleep(e.value)

    except:
        pass

# =========================================================
# DOWNLOAD
# =========================================================

async def extract_video(post_url, msg):

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = await browser.new_context(
            viewport={
                "width": 1366,
                "height": 768
            },
            accept_downloads=True
        )

        page = await context.new_page()

        await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        """)

        await safe_edit(
            msg,
            "🌐 Opening page..."
        )

        await page.goto(post_url, timeout=0)

        await page.wait_for_timeout(8000)

        title = await page.title()

        title = clean_name(title)

        await safe_edit(
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

        await safe_edit(
            msg,
            "☁ Opening download page..."
        )

        async with context.expect_page() as page_info:

            await target_btn.click(force=True)

        redirect_page = await page_info.value

        await redirect_page.wait_for_load_state()

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

                    # =====================================
                    # GET VIDEO
                    # =====================================

                    if "get video" in txt:

                        await safe_edit(
                            msg,
                            "⚡ Generating download..."
                        )

                        await b.click(force=True)

                        await redirect_page.wait_for_timeout(
                            10000
                        )

                        break

                    # =====================================
                    # WAIT
                    # =====================================

                    elif "getting download link" in txt:

                        await safe_edit(
                            msg,
                            "⏳ Waiting for server..."
                        )

                        await redirect_page.wait_for_timeout(
                            12000
                        )

                        break

                    # =====================================
                    # DOWNLOAD
                    # =====================================

                    elif txt == "download":

                        await safe_edit(
                            msg,
                            "⬇ Downloading video..."
                        )

                        await b.click(force=True)

                        await redirect_page.wait_for_timeout(
                            8000
                        )

                        current_url = redirect_page.url

                        print(
                            "CURRENT URL:",
                            current_url
                        )

                        save_path = (
                            f"{DOWNLOAD_DIR}/"
                            f"{title}_raw.mp4"
                        )

                        # =================================
                        # DIRECT MP4 STREAM
                        # =================================

                        if ".mp4" in current_url:

                            cmd = f'''
wget -O "{save_path}" "{current_url}"
'''

                            run(cmd)

                            await browser.close()

                            return title, save_path

                        # =================================
                        # NORMAL DOWNLOAD
                        # =================================

                        async with redirect_page.expect_download(
                            timeout=30000
                        ) as dl2:

                            await b.click(force=True)

                        download = await dl2.value

                        await download.save_as(save_path)

                        await browser.close()

                        return title, save_path

                except:
                    pass

        await browser.close()

        raise Exception(
            "Final video not found"
        )

# =========================================================
# ENCODE
# =========================================================

async def encode_480p(
    input_file,
    output_file,
    msg
):

    await safe_edit(
        msg,
        "⚡ Encoding video..."
    )

    cmd = f'''
ffmpeg -y \
-ss 00:01:26 \
-i "{input_file}" \
-vf scale=-2:480 \
-c:v libx264 \
-crf 28 \
-preset veryfast \
-pix_fmt yuv420p \
-profile:v high \
-level 4.0 \
-c:a aac \
-b:a 96k \
-ar 44100 \
-ac 2 \
-movflags +faststart \
-map_metadata -1 \
"{output_file}"
'''

    process = await asyncio.create_subprocess_shell(
        cmd
    )

    while True:

        if process.returncode is not None:
            break

        await safe_edit(
            msg,
            "🎞 Encoding 480p..."
        )

        await asyncio.sleep(15)

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

async def progress(
    current,
    total,
    msg
):

    percent = current * 100 / total

    filled = math.floor(percent / 10)

    bar = (
        "█" * filled
        +
        "░" * (10 - filled)
    )

    uploaded = (
        current / 1024 / 1024
    )

    totalmb = (
        total / 1024 / 1024
    )

    text = f"""
📤 Uploading Video

[{bar}]

⚡ {round(percent,2)}%

📦 {round(uploaded,2)} / {round(totalmb,2)} MB
"""

    await safe_edit(
        msg,
        text
    )

# =========================================================
# PROCESS
# =========================================================

async def process_link(message, link):

    global UPLOAD_CHANNEL

    msg = await message.reply(
        "🔍 Starting..."
    )

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

    await encode_480p(
        raw_file,
        encoded_file,
        msg
    )

    await safe_edit(
        msg,
        "🖼 Creating thumbnail..."
    )

    make_thumb(
        encoded_file,
        thumb
    )

    size = (
        os.path.getsize(encoded_file)
        / 1024 / 1024
    )

    await safe_edit(
        msg,
        f"📦 Final Size: {round(size,2)} MB"
    )

    duration = int(
        get_duration(encoded_file)
    )

    caption_text = f"{title}"

    # =====================================================
    # SEND USER
    # =====================================================

    await app.send_video(

        chat_id=message.chat.id,

        video=encoded_file,

        caption=caption_text,

        thumb=thumb,

        duration=duration,

        width=854,

        height=480,

        supports_streaming=True,

        progress=progress,

        progress_args=(msg,)
    )

    # =====================================================
    # SEND CHANNEL
    # =====================================================

    if UPLOAD_CHANNEL:

        try:

            await app.send_video(

                chat_id=UPLOAD_CHANNEL,

                video=encoded_file,

                caption=caption_text,

                thumb=thumb,

                duration=duration,

                width=854,

                height=480,

                supports_streaming=True
            )

        except Exception as e:

            print(e)

    await safe_edit(
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

# =========================================================
# QUEUE
# =========================================================

async def process_queue():

    global PROCESSING

    if PROCESSING:
        return

    PROCESSING = True

    while QUEUE:

        data = QUEUE.popleft()

        message = data["message"]

        link = data["link"]

        try:

            await process_link(
                message,
                link
            )

        except Exception as e:

            print(e)

    PROCESSING = False

async def add_to_queue(message, link):

    if len(QUEUE) >= 10:

        return await message.reply(
            "❌ Queue Full (10 Max)"
        )

    QUEUE.append({

        "message": message,
        "link": link

    })

    pos = len(QUEUE)

    await message.reply(
        f"✅ Added To Queue\n"
        f"📦 Position: {pos}"
    )

    asyncio.create_task(
        process_queue()
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
        "/chklink LINK\n"
        "/setchannel CHANNEL_ID"
    )

@app.on_message(filters.command("help"))
async def help_cmd(_, message):

    await message.reply(
        "manual:\n"
        "Use /chklink LINK\n\n"

        "automatic:\n"
        "Send link directly"
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

@app.on_message(filters.command("setchannel"))
async def setchannel(_, message):

    global UPLOAD_CHANNEL

    try:

        cid = int(
            message.text.split(" ")[1]
        )

        UPLOAD_CHANNEL = cid

        await message.reply(
            f"✅ Upload Channel Set\n{cid}"
        )

    except:

        await message.reply(
            "/setchannel -100xxxxxxxx"
        )

@app.on_message(filters.command("chklink"))
async def chk(_, message):

    try:

        link = message.text.split(
            " ",
            1
        )[1]

        await add_to_queue(
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

        await add_to_queue(
            message,
            text
        )

# =========================================================
# RUN
# =========================================================

print("BOT STARTED")

app.run()
