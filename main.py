# main.py

# =========================================================
# LUCIFER DONGHUA AUTO DOWNLOADER BOT
# FAST STABLE FINAL VERSION
# =========================================================

import os
import re
import math
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

API_ID = 123456
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"

OWNER_ID = [123456789]

DOWNLOAD_DIR = "downloads"

FFMPEG_THREADS = os.cpu_count()

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

    except FloodWait as e:

        await asyncio.sleep(e.value)

    except:
        pass

# =========================================================
# EXTRACT VIDEO
# =========================================================

async def extract_video(post_url, msg):

    async with async_playwright() as p:

        browser = await p.chromium.launch(

            headless=False,

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
        # OPEN POST PAGE
        # =====================================================

        await safe_edit(
            msg,
            "🌐 Opening page..."
        )

        await page.goto(
            post_url,
            timeout=0
        )

        await page.wait_for_timeout(6000)

        title = clean_name(
            await page.title()
        )

        # =====================================================
        # FIND RED DOWNLOAD BUTTON
        # =====================================================

        await safe_edit(
            msg,
            "🔍 Finding download button..."
        )

        target_btn = None

        btns = await page.locator("a").all()

        for b in btns:

            try:

                txt = (
                    await b.inner_text()
                ).strip().lower()

                if "download" in txt:

                    target_btn = b
                    break

            except:
                pass

        if not target_btn:

            await browser.close()

            raise Exception(
                "Download button not found"
            )

        # =====================================================
        # OPEN DOWNLOAD PAGE
        # =====================================================

        await safe_edit(
            msg,
            "☁ Opening download page..."
        )

        async with context.expect_page() as pinfo:

            await target_btn.click(force=True)

        redirect_page = await pinfo.value

        await redirect_page.wait_for_load_state()

        # =====================================================
        # MAIN LOOP
        # =====================================================

        while True:

            btns = await redirect_page.locator(
                "button,a"
            ).all()

            found_download = False

            for b in btns:

                try:

                    txt = (
                        await b.inner_text()
                    ).strip().lower()

                    # =================================================
                    # GET VIDEO
                    # =================================================

                    if "get video" in txt:

                        await safe_edit(
                            msg,
                            "⚡ Generating download..."
                        )

                        await b.click(force=True)

                        await redirect_page.wait_for_timeout(
                            3000
                        )

                        # =============================================
                        # CLOSE AD TAB
                        # =============================================

                        pages = context.pages

                        if len(pages) > 2:

                            try:

                                ad_page = pages[-1]

                                if ad_page != redirect_page:

                                    await ad_page.close()

                            except:
                                pass

                        await redirect_page.wait_for_timeout(
                            5000
                        )

                        break

                    # =================================================
                    # DOWNLOAD BUTTON
                    # =================================================

                    elif txt == "download":

                        found_download = True

                        await safe_edit(
                            msg,
                            "⬇ Starting download..."
                        )

                        before = set(
                            os.listdir(DOWNLOAD_DIR)
                        )

                        await b.click(force=True)

                        # =============================================
                        # WAIT DOWNLOAD START
                        # =============================================

                        while True:

                            now = set(
                                os.listdir(DOWNLOAD_DIR)
                            )

                            new = now - before

                            mp4s = [

                                x for x in new

                                if (
                                    x.endswith(".mp4")
                                    or
                                    x.endswith(".crdownload")
                                )
                            ]

                            if mp4s:
                                break

                            await asyncio.sleep(1)

                        # =============================================
                        # WAIT DOWNLOAD COMPLETE
                        # =============================================

                        while True:

                            files = os.listdir(
                                DOWNLOAD_DIR
                            )

                            downloading = [

                                x for x in files

                                if x.endswith(
                                    ".crdownload"
                                )
                            ]

                            if not downloading:
                                break

                            await asyncio.sleep(2)

                        files = os.listdir(
                            DOWNLOAD_DIR
                        )

                        mp4_files = [

                            x for x in files
                            if x.endswith(".mp4")
                        ]

                        latest = max(
                            mp4_files,
                            key=lambda x: os.path.getctime(
                                os.path.join(
                                    DOWNLOAD_DIR,
                                    x
                                )
                            )
                        )

                        save_path = os.path.join(
                            DOWNLOAD_DIR,
                            latest
                        )

                        await browser.close()

                        return title, save_path

                except:
                    pass

            if found_download:
                break

            await redirect_page.wait_for_timeout(
                2000
            )

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
-threads {FFMPEG_THREADS} \
-ss 00:01:26 \
-i "{input_file}" \
-vf scale=-2:480 \
-c:v libx264 \
-crf 29 \
-preset ultrafast \
-pix_fmt yuv420p \
-c:a aac \
-b:a 96k \
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
# THUMB
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

    uploaded = current / 1024 / 1024

    totalmb = total / 1024 / 1024

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
# PROCESS LINK
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

    await safe_edit(
        msg,
        "🖼 Creating thumbnail..."
    )

    make_thumb(
        encoded_file,
        thumb
    )

    duration = int(
        get_duration(encoded_file)
    )

    size = (
        os.path.getsize(encoded_file)
        / 1024 / 1024
    )

    await safe_edit(
        msg,
        f"📦 Final Size: {round(size,2)} MB"
    )

    caption = title

    # =====================================================
    # SEND USER
    # =====================================================

    await app.send_video(

        chat_id=message.chat.id,

        video=encoded_file,

        caption=caption,

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

                caption=caption,

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

            try:

                await message.reply(
                    f"❌ Failed:\n{e}\n\n"
                    f"⏭ Skipping next item..."
                )

            except:
                pass

    PROCESSING = False

async def add_to_queue(message, link):

    if len(QUEUE) >= 10:

        return await message.reply(
            "❌ Queue Full"
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
            f"✅ Channel Set\n{cid}"
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
