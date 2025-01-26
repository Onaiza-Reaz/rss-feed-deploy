from flask import Flask, request, jsonify
from flask_cors import CORS
import feedparser
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
import bcrypt
from dateutil import parser
import html
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
CORS(app)

# MongoDB setup
client = MongoClient("mongodb+srv://reaz4401477:8Gv6MH8VZUUu%21ju@cluster0.zgn4s.mongodb.net/rss_user_db?retryWrites=true&w=majority")
db = client["rss_user_db"]
users_collection = db["users"]

# Specific RSS Feed URLs
specific_feed_urls = [
    "https://hollywoodlife.com/feed/",
    "https://www.etonline.com/style/lifestyle/rss",
    "http://rss.cnn.com/rss/edition_entertainment.rss",
    "https://feeds.feedburner.com/GeoEntertainment-GeoTvNetwork",
    "https://www.dailymail.co.uk/tvshowbiz/index.rss",
    "https://eol-feeds.eonline.com/rssfeed/us/top_stories",
    "https://www.usmagazine.com/category/entertainment/feed/",
    "https://www.mirror.co.uk/lifestyle/?service=rss",
    "https://feeds.feedburner.com/variety/headlines",
    "https://feeds.feedburner.com/com/Yeor"
]

# Sports RSS Feed URLs
sports_feed_urls = [
    "https://feeds.feedburner.com/com/Yeor",
    "https://www.bolnews.com/sports/feed/",
    "http://feeds.feedburner.com/GeoSport-GeoTvNetwork",
    "https://arynews.tv/category/sports/feed/"
]

shared_articles = []
shared_sports_articles = []

# Function to fetch RSS feed data
def fetch_rss_feed_data(feed_urls):
    articles = []
    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
            channel_name = feed.feed.get('title', 'Unknown Channel')

            for entry in feed.entries:
                try:
                    title = html.unescape(entry.get('title', 'No Title'))
                    link = entry.get('link', 'No Link')
                    pub_date_str = entry.get('published', entry.get('updated', None))
                    pub_date = parser.parse(pub_date_str) if pub_date_str else None

                    if pub_date:
                        time_diff = datetime.now(timezone.utc) - pub_date
                        if time_diff > timedelta(hours=24):
                            continue

                    formatted_pub_date = pub_date.strftime('%Y-%m-%d %H:%M') if pub_date else 'Unknown Date'

                    articles.append({
                        'title': title,
                        'link': link,
                        'pubDate': formatted_pub_date,
                        'channel': channel_name
                    })
                except Exception as e:
                    print(f"Error processing article from {channel_name}. Error: {e}")
        except Exception as e:
            print(f"Error parsing feed from URL: {url}. Error: {e}")

    return articles

# Functions to update shared articles
def update_specific_articles():
    global shared_articles
    print("Fetching updated specific RSS feed data...")
    shared_articles = fetch_rss_feed_data(specific_feed_urls)

def update_sports_articles():
    global shared_sports_articles
    print("Fetching updated sports RSS feed data...")
    shared_sports_articles = fetch_rss_feed_data(sports_feed_urls)

# API endpoints
@app.route('/api/articles', methods=['GET'])
def get_specific_articles():
    try:
        return jsonify({'status': 'success', 'data': shared_articles}), 200
    except Exception as e:
        print(f"Error fetching specific RSS feed data: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to fetch RSS feed data.'}), 500

@app.route('/api/sports', methods=['GET'])
def get_sports_articles():
    try:
        return jsonify({'status': 'success', 'data': shared_sports_articles}), 200
    except Exception as e:
        print(f"Error fetching sports RSS feed data: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to fetch sports RSS feed data.'}), 500

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    if not username:
        return jsonify({"error": "Username is required"}), 400
    if not password:
        return jsonify({"error": "Password is required"}), 400
    if not email:
        return jsonify({"error": "Email is required"}), 400

    if users_collection.find_one({"username": username}):
        return jsonify({"error": "User already exists"}), 409
    if users_collection.find_one({"email": email}):
        return jsonify({"error": "Email already exists"}), 409

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    users_collection.insert_one({
        "username": username,
        "email": email,
        "password": hashed_password.decode('utf-8')
    })
    return jsonify({"message": "Signup successful"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(force=True)
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    if not username:
        return jsonify({"error": "Username is required"}), 400
    if not password:
        return jsonify({"error": "Password is required"}), 400
    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = users_collection.find_one({"username": username, "email": email})
    if not user:
        return jsonify({"error": "Invalid username, email, or password"}), 401

    if not bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
        return jsonify({"error": "Invalid username or password"}), 401

    return jsonify({"message": "Login successful"}), 200

if __name__ == "__main__":
    # Scheduler setup
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_specific_articles, 'interval', minutes=3)
    scheduler.add_job(update_sports_articles, 'interval', minutes=3)
    scheduler.start()

    app.run(debug=True, port=5000)
