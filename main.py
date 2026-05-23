# main.py

# LUCIFER DONGHUA AUTO DOWNLOADER BOT

import os
import re
import asyncio
import subprocess

from pyrogram import Client, filters
from playwright.async_api import async_playwright

# =========================================================
# CONFIG
# =========================================================

API_ID = 26826540
API_HASH = ""
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

        context = await browser.new_context(
            accept_downloads=True
        )

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
        # HANDLE GET VIDEO + DOWNLOAD
        # =====================================================

        for _ in range(30):

            try:

                current = redirect_page.url

                print(f"Current URL: {current}")

                await redirect_page.wait_for_timeout(3000)

                # ==============================================
                # CHECK MP4 DIRECTLY
                # ==============================================

                html = await redirect_page.content()

                mp4s = re.findall(
                    r'https?://[^\s"\']+\.mp4[^\s"\']*',
                    html
                )

                if mp4s:

                    print("FINAL MP4 FOUND")

                    await browser.close()

                    return title, mp4s[0]

                # ==============================================
                # FIND BUTTONS
                # ==============================================

                btns = await redirect_page.locator("button,a").all()

                clicked = False

                for b in btns:

                    try:

                        txt = (await b.inner_text()).strip().lower()

                        print("BUTTON:", txt)

                        # ======================================
                        # GET VIDEO
                        # ======================================

                        if "get video" in txt:

                            print("CLICK GET VIDEO")

                            old_url = redirect_page.url

                            await b.click(force=True)

                            await redirect_page.wait_for_timeout(8000)

                            # ==================================
                            # AD REDIRECT DETECT
                            # ==================================

                            if redirect_page.url != old_url:

                                print("AD REDIRECT DETECTED")

                                try:

                                    await redirect_page.go_back()

                                    await redirect_page.wait_for_timeout(5000)

                                except:
                                    pass

                            clicked = True
                            break

                        # ======================================
                        # WAIT STATE
                        # ======================================

                        elif "getting download link" in txt:

                            print("WAITING FOR DOWNLOAD")

                            await redirect_page.wait_for_timeout(10000)

                            clicked = True
                            break

                        # ======================================
                        # FINAL DOWNLOAD
                        # ======================================

                        elif txt == "download":

                            print("CLICK DOWNLOAD")

                            old_url = redirect_page.url

                            try:

                                async with redirect_page.expect_download(timeout=30000) as dl:

                                    await b.click(force=True)

                                download = await dl.value

                                save_path = f"{DOWNLOAD_DIR}/{title}_raw.mp4"

                                await download.save_as(save_path)

                                print("DOWNLOAD COMPLETED")

                                await browser.close()

                                return title, save_path

                            except Exception as e:

                                print(e)

                                # AD REDIRECT
                                if redirect_page.url != old_url:

                                    print("DOWNLOAD REDIRECT DETECTED")

                                    try:

                                        await redirect_page.go_back()

                                        await redirect_page.wait_for_timeout(5000)

                                    except:
                                        pass

                            clicked = True
                            break

                    except Exception as e:
                        print(e)

                if clicked:
                    continue

                print("WAITING...")

                await redirect_page.wait_for_timeout(5000)

            except Exception as e:

                print(e)

        await browser.close()

        raise Exception("Final video not found")

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

        title, raw_file = await extract_video(link)

        encoded_file = f"{DOWNLOAD_DIR}/{title}_480p.mp4"

        thumb = f"{DOWNLOAD_DIR}/{title}.jpg"

        await msg.edit("🎞 Encoding 480p under 150MB...")

        encode_480p(raw_file, encoded_file)

        await msg.edit("🖼 Creating thumbnail...")

        make_thumb(encoded_file, thumb)

        await msg.edit("📤 Uploading...")

        await app.send_video(
            chat_id=message.chat.id,
            video=encoded_file,
            caption=title,
            thumb=thumb,
            supports_streaming=True
        )

        await msg.delete()

        try:
            os.remove(raw_file)
            os.remove(encoded_file)
            os.remove(thumb)
        except:
            pass

    except Exception as e:

        print(e)

        await message.reply(f"❌ Error:\n{e}")

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

# =========================================================
# RUN
# =========================================================

print("BOT STARTED")

app.run()
