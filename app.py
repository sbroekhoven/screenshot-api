from flask import Flask, request, send_file, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import tempfile
import time
import os
import logging
import json
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv



app = Flask(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY", "my-secret-key")
DEFAULT_WIDTH = int(os.getenv("DEFAULT_WIDTH", 1920))
DEFAULT_HEIGHT = int(os.getenv("DEFAULT_HEIGHT", 1080))
DEFAULT_PROXY = os.getenv("DEFAULT_PROXY", None)
WAIT_TIME = int(os.getenv("PAGE_LOAD_WAIT", 2))

# Config
API_KEY = "my-secret-key"

# Metrics counters
metrics = {
    "total_requests": 0,
    "screenshots_taken": 0,
    "errors": 0
}

# Setup JSON logger
logger = logging.getLogger("screenshot-api")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Function to log events
def log_event(event_type, data=None):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "data": data or {}
    }
    logger.info(json.dumps(entry))

# Decorator for logging and metrics
def log_and_count(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        metrics["total_requests"] += 1
        try:
            return func(*args, **kwargs)
        except Exception as e:
            metrics["errors"] += 1
            log_event("error", {"exception": str(e)})
            raise
    return wrapper

# Function to take a screenshot
def take_screenshot(url: str, proxy: str = None, width=None, height=None) -> str:
    width = width or DEFAULT_WIDTH
    height = height or DEFAULT_HEIGHT
    proxy = proxy or DEFAULT_PROXY

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument(f"--window-size={width},{height}")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # Custom User-Agent, because I'm not a robot
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    if proxy:
        chrome_options.add_argument(f'--proxy-server={proxy}')

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        time.sleep(WAIT_TIME)
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        driver.save_screenshot(tmp_file.name)
        return tmp_file.name
    finally:
        driver.quit()

# Routes
@app.route("/screenshot", methods=["POST"])
@log_and_count
def screenshot():
    if request.headers.get("X-API-Key") != API_KEY:
        log_event("unauthorized_access", {"ip": request.remote_addr})
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' field"}), 400

    url = data["url"]
    width = data.get("width")
    height = data.get("height")
    proxy = data.get("proxy")

    try:
        screenshot_path = take_screenshot(url, proxy, width, height)
        metrics["screenshots_taken"] += 1
        log_event("screenshot_taken", {"url": url, "ip": request.remote_addr, "proxy": proxy})
        return send_file(screenshot_path, mimetype="image/png")
    except Exception as e:
        raise
    finally:
        if 'screenshot_path' in locals() and os.path.exists(screenshot_path):
            os.remove(screenshot_path)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/metrics", methods=["GET"])
def get_metrics():
    return jsonify(metrics)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
