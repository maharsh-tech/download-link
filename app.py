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

# Helper
def generate_slug(file_id):
    return hashlib.md5(file_id.encode()).hexdigest()[:6]

# ✅ Manual indexing via reply
@bot.on_message(filters.command("index") & filters.reply)
async def manual_index(client: Client, message: Message):
    replied = message.reply_to_message

    if not replied or not replied.video:
        await message.reply("❌ Please reply to a video to index it.")
        return

    file_id = replied.video.file_id
    caption = replied.caption or ""
    slug = generate_slug(file_id)

    if videos.find_one({"slug": slug}):
        await message.reply("ℹ️ This video is already indexed.")
        return

    videos.insert_one({"slug": slug, "file_id": file_id, "caption": caption})
    base = config.find_one({}, sort=[("_id", -1)])
    if base and "base_url" in base:
        link = f"{base['base_url']}/file/{slug}.html"
        await message.reply(f"✅ Video indexed!\n\n🔗 Link: {link}")
    else:
        await message.reply("✅ Video indexed but base_url is not set.")

# ✅ Start bot thread
def start_bot():
    async def run_bot():
        await bot.start()
        print("✅ Bot started")
        await asyncio.Event().wait()  # Keeps bot running

    asyncio.run(run_bot())

# ✅ Start everything
if __name__ == "__main__":
    print("🚀 Starting bot...")
    threading.Thread(target=start_bot).start()
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
