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

# ✅ Handles videos from monitored channels
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

# ✅ Handle /index command
@bot.on_message(filters.command("index") & filters.channel)
async def index_channel(client: Client, message: Message):
    chat_id = message.chat.id
    print(f"📥 Received /index in channel: {chat_id}")

    if not indexed.find_one({"chat_id": chat_id}):
        indexed.insert_one({"chat_id": chat_id})
        await client.send_message(chat_id, "✅ Channel has been indexed for video monitoring.")
        print(f"✅ Channel {chat_id} indexed")
    else:
        await client.send_message(chat_id, "ℹ️ This channel is already being monitored.")
        print(f"ℹ️ Channel {chat_id} already indexed")

# ✅ Run bot in background
def start_bot():
    asyncio.run(bot.start())
    print("✅ Bot started")
    asyncio.run(bot.idle())

# ✅ Start everything
if __name__ == "__main__":
    print("✅ Bot starting...")
    threading.Thread(target=start_bot).start()
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
