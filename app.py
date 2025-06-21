from pyrogram import Client, filters
from pyrogram.types import Message
import os
import hashlib

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

bot = Client("debug_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Generate a dummy slug
def generate_slug(file_id):
    return hashlib.md5(file_id.encode()).hexdigest()[:6]

@bot.on_message(filters.command("index") & filters.reply)
async def handle_index(client: Client, message: Message):
    print("📥 Received /index")
    reply = message.reply_to_message

    if not reply or not reply.video:
        await message.reply("❌ Please reply to a video message.")
        return

    slug = generate_slug(reply.video.file_id)
    await message.reply(f"✅ Video indexed as `{slug}`")

@bot.on_message(filters.command("ping"))
async def test(client: Client, message: Message):
    await message.reply("🏓 Pong!")

bot.run()
