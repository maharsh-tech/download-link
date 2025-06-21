from pyrogram import Client, filters
from flask import Flask, jsonify
from pymongo import MongoClient
import os
import asyncio
import hashlib

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

@bot.on_message(filters.video & filters.channel)
async def handle_video(client, message):
    file_id = message.video.file_id
    caption = message.caption or ""
    slug = generate_slug(file_id)

    if not videos.find_one({"slug": slug}):
        videos.insert_one({"slug": slug, "file_id": file_id, "caption": caption})

    redirect_link = f"https://yourname.pages.dev/file/{slug}.html"
    new_caption = f"{caption}\n\n📥 Download: {redirect_link}"

    await client.send_video(chat_id=message.chat.id, video=file_id, caption=new_caption)

# Main runner
async def main():
    await bot.start()
    print("✅ Bot started")
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

if __name__ == "__main__":
    asyncio.run(main())
