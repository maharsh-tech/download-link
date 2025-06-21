from flask import Flask, jsonify, redirect
from pymongo import MongoClient
import os

app = Flask(__name__)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["redirector_db"]
videos = db["videos"]
config = db["config"]

@app.route("/config")
def get_config():
    cfg = config.find_one({}, sort=[("_id", -1)])
    return jsonify({"base_url": cfg["base_url"]}) if cfg else ("Not set", 404)

@app.route("/download/<slug>")
def redirect_download(slug):
    video = videos.find_one({"slug": slug})
    cfg = config.find_one({}, sort=[("_id", -1)])
    if not video or not cfg:
        return "Not found", 404
    return redirect(f"{cfg['base_url']}/download/{video['file_hash']}", code=302)

@app.route("/")
def home():
    return "Koyeb redirector is running!"
