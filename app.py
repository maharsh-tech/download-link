from pyrogram import idle
import threading
import asyncio
from pyrogram import Client, filters
from flask import Flask, jsonify
from pymongo import MongoClient
import os
import asyncio
import hashlib
import threading

# === ENVIRONMENT VARIABLES ===
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
MONGO_URI = os.environ["MONGO_URI"]

# === MongoDB ===
mongo = MongoClient(MONGO_URI)
db = mongo["redirector"]
videos = db["videos"]
config = db["config"]
indexed = db["indexed_channels"]

# === Flask Web App ===
web = Flask(__name__)

@web.route("/")
def home():
    return "✅ Koyeb redirector + bot is running!"

@web.route("/config")
def get_config():
    current = config.find_one({}, sort=[("_id", -1)])
    return jsonify({"base_url": current["base_url"] if current else ""})

@web.route("/download/<slug>")
def serve(slug):
    video = videos.find_one({"slug": slug})
    if not video:
        return "Not found", 404
    return jsonify({"file_id": video["file_id"]})

# === Telegram Bot ===
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def generate_slug(file_id):
    return hashlib.md5(file_id.encode()).hexdigest()[:6]

# 🟩 Video Handler
@bot.on_message(filters.video & filters.channel)
async def handle_video(client, message):
    chat_id = message.chat.id

    # Check if channel is indexed
    if not indexed.find_one({"chat_id": chat_id}):
        return

    file_id = message.video.file_id
    caption = message.caption or ""
    slug = generate_slug(file_id)

    # Insert into DB if new
    if not videos.find_one({"slug": slug}):
        videos.insert_one({"slug": slug, "file_id": file_id, "caption": caption})

    # Get latest base_url from config
    cfg = config.find_one({}, sort=[("_id", -1)])
    base_url = cfg["base_url"] if cfg else "https://yourname.pages.dev"

    redirect_link = f"{base_url}/file/{slug}.html"
    new_caption = f"{caption}\n\n📥 Download: {redirect_link}"

    # Forward file back with updated caption
    await client.send_video(chat_id=chat_id, video=file_id, caption=new_caption)

# 🟦 Index Command
@bot.on_message(filters.command("index") & filters.channel)
async def index_channel(client, message):
    chat_id = message.chat.id

    if not indexed.find_one({"chat_id": chat_id}):
        indexed.insert_one({"chat_id": chat_id})
        await message.reply("✅ Channel has been indexed for video monitoring.")
    else:
        await message.reply("ℹ️ This channel is already being monitored.")

try:
    if not indexed.find_one({"chat_id": chat_id}):
        indexed.insert_one({"chat_id": chat_id})
        await message.reply("✅ Channel has been indexed for video monitoring.")
    else:
        await message.reply("ℹ️ This channel is already being monitored.")
except Exception as e:
    print(f"MongoDB error: {e}")
    await message.reply("❌ Failed to index this channel.")


def start_bot():
    bot.start()                 # ✅ No await needed
    print("✅ Bot started")
    asyncio.run(idle())        # ✅ idle is still a coroutine

if __name__ == "__main__":
    threading.Thread(target=start_bot).start()
    web.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
