from pyrogram import Client, filters
from pyrogram.types import Message
from flask import Flask
import os
import hashlib
from pymongo import MongoClient

# Environment variables
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
MONGO_URI = os.environ["MONGO_URI"]

# Flask app
web = Flask(__name__)

@web.route("/")
def home():
    return "Bot is running!"

# MongoDB setup
mongo = MongoClient(MONGO_URI)
db = mongo["redirector"]
videos = db["videos"]
config = db["config"]

# Bot
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Slug generator
def generate_slug(file_id):
    return hashlib.md5(file_id.encode()).hexdigest()[:6]

# Handle /index replies
@bot.on_message(filters.command("index") & filters.reply)
async def manual_index(client: Client, message: Message):
    print("📥 /index command received")
    reply = message.reply_to_message

    if not reply or not reply.video:
        await message.reply("❌ Please reply to a video to index it.")
        return

    file_id = reply.video.file_id
    caption = reply.caption or ""
    slug = generate_slug(file_id)

    if not videos.find_one({"slug": slug}):
        videos.insert_one({"slug": slug, "file_id": file_id, "caption": caption})

    base = config.find_one({}, sort=[("_id", -1)])
    link = f"{base['base_url']}/file/{slug}.html" if base and "base_url" in base else "Link unavailable"
    await message.reply(f"✅ Video indexed!\n\n🔗 {link}")
    print(f"✅ Indexed: {slug}")

# Start both Flask and bot
if __name__ == "__main__":
    import threading
    import asyncio

    def run_flask():
        web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

    def run_bot():
        asyncio.run(bot.start())
        print("✅ Bot started")
        asyncio.run(bot.idle())

    threading.Thread(target=run_bot).start()
    run_flask()
