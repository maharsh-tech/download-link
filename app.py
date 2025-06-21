from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask, jsonify
from pymongo import MongoClient
import os
import hashlib
import threading
import asyncio

# ENV variables
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
MONGO_URI = os.environ["MONGO_URI"]
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 0))  # ✅ Your target channel ID

# Telegram bot
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Flask app
web = Flask(__name__)

# MongoDB setup
mongo = MongoClient(MONGO_URI)
db = mongo["redirector"]
videos = db["videos"]
config = db["config"]
indexed = db["indexed_channels"]

# Routes
@web.route("/")
def home():
    return "Koyeb redirector + bot is running!"

@web.route("/config")
def get_config():
    current = config.find_one({}, sort=[("_id", -1)])
    if current:
        return jsonify({"base_url": current["base_url"]})
    return jsonify({"base_url": ""})

@web.route("/download/<slug>")
def serve(slug):
    video = videos.find_one({"slug": slug})
    if not video:
        return "Not found", 404
    return jsonify({"file_id": video["file_id"]})

# Helper function
def generate_slug(file_id):
    return hashlib.md5(file_id.encode()).hexdigest()[:6]

# ✅ Handle new video in channel
@bot.on_message(filters.video & filters.channel)
async def handle_video(client: Client, message: Message):
    chat_id = message.chat.id
    if not indexed.find_one({"chat_id": chat_id}):
        print(f"❌ Ignoring video from unmonitored channel {chat_id}")
        return

    file_id = message.video.file_id
    caption = message.caption or ""
    slug = generate_slug(file_id)

    if not videos.find_one({"slug": slug}):
        videos.insert_one({"slug": slug, "file_id": file_id, "caption": caption})

    base_url = config.find_one({}, sort=[("_id", -1)])
    if not base_url or "base_url" not in base_url:
        print("❌ Base URL not found in config")
        return

    redirect_link = f"{base_url['base_url']}/file/{slug}.html"
    new_caption = f"{caption}\n\n📥 Download: {redirect_link}"

    await client.send_video(chat_id=chat_id, video=file_id, caption=new_caption)
    print(f"✅ Video processed and posted with link: {redirect_link}")

# ✅ Bot start + send connection message
async def run_bot():
    await bot.start()
    print("✅ Bot started")

    # ✅ Send startup message
    try:
        await bot.send_message(CHANNEL_ID, "🤖 Bot has connected and is ready!")
        print(f"✅ Connected message sent to {CHANNEL_ID}")
    except Exception as e:
        print(f"❌ Failed to send startup message: {e}")

    await bot.idle()

# ✅ Start bot in background thread
def start_bot():
    asyncio.run(run_bot())

# ✅ Launch
if __name__ == "__main__":
    print("🚀 Starting bot...")
    threading.Thread(target=start_bot).start()
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
