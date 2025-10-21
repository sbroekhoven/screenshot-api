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
from PIL import Image, ImageDraw, ImageFont
import os
import requests
from urllib.parse import urlparse
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

# Load environment variables
load_dotenv()
API_KEY = os.getenv("API_KEY", "my-secret-key")
DEFAULT_WIDTH = int(os.getenv("DEFAULT_WIDTH", 1920))
DEFAULT_HEIGHT = int(os.getenv("DEFAULT_HEIGHT", 1080))
DEFAULT_PROXY = os.getenv("DEFAULT_PROXY", None)
WAIT_TIME = int(os.getenv("PAGE_LOAD_WAIT", 2))

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
        screenshot_path = tmp_file.name

        driver.save_screenshot(screenshot_path)
        add_watermark(screenshot_path, url)

        return screenshot_path
    finally:
        driver.quit()

def add_watermark(image_path, url, font_size=20):
    # Load timezone from env
    tz_name = os.getenv("WATERMARK_TIMEZONE", "UTC")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")  # Fallback if invalid timezone

    now = datetime.now(tz)
    timestamp = now.strftime("%Y-%m-%d %H:%M %Z")  # Example: 2025-07-15 15:43 CEST

    text = f"{timestamp}\n{url}"
    with Image.open(image_path).convert("RGBA") as base:
        watermark = Image.new("RGBA", base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark)

        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, font_size)

        # Build watermark text
        # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        # text = f"{timestamp}\n{url}"

        # Get bounding box for multiline text
        bbox = draw.multiline_textbbox((0, 0), text, font=font)
        textwidth = bbox[2] - bbox[0]
        textheight = bbox[3] - bbox[1]

        # Position: bottom-left corner with padding
        padding = 16
        x = padding
        y = base.height - textheight - padding

        # Background box
        draw.rectangle(
            [(x - padding, y - padding), (x + textwidth + padding, y + textheight + padding)],
            fill=(200, 200, 200, 180)  # light gray, semi-transparent
        )

        # Text
        draw.multiline_text((x, y), text, font=font, fill=(0, 0, 0, 255))

        # Save result
        combined = Image.alpha_composite(base, watermark).convert("RGB")
        combined.save(image_path, "PNG")


# Function to validate URL
def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and parsed.netloc
    except:
        return False

# Routes
@app.route("/screenshot", methods=["POST"])
@log_and_count
def screenshot():
    if request.headers.get("X-API-Key") != API_KEY:
        log_event("unauthorized_access", {"ip": request.remote_addr})
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    # Check is URL is set.
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' field"}), 400

    url = data["url"]
    # Check if URL is valid.
    if not is_valid_url(url):
        return jsonify({"error": "Invalid URL"}), 400



    width = int(data.get("width", DEFAULT_WIDTH) or DEFAULT_WIDTH)
    height = int(data.get("height", DEFAULT_HEIGHT) or DEFAULT_HEIGHT)
    # Check if dimensions are not too big
    if width > 1920 or height > 1080:
        return jsonify({"error": "Screenshot dimensions too large"}), 400

    proxy = data.get("proxy")
    # If the URL is .ontion, check if a proxy is provided.
    if ".onion" in url and not proxy:
        return jsonify({"error": "Tor proxy required for .onion domains"}), 403

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

# Start FORM option.
@app.route("/form", methods=["GET", "POST"])
def form():
    if request.method == "POST":
        url = request.form.get("url")
        api_key = request.form.get("api_key")
        proxy = request.form.get("proxy")
        width = request.form.get("width")
        height = request.form.get("height")

        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        payload = {
            "url": url,
            "proxy": proxy or None,
            "width": int(width) if width else None,
            "height": int(height) if height else None
        }

        try:
            r = requests.post(
                f"{request.host_url}screenshot",
                headers=headers,
                json=payload,
                stream=True
            )

            if r.status_code == 200:
                unique_name = f"preview-{uuid.uuid4().hex}.png"
                preview_path = os.path.join(tempfile.gettempdir(), unique_name)
                with open(preview_path, "wb") as f:
                    f.write(r.content)

                return f"""
                <h2>Screenshot Success</h2>
                <img src="/preview/{unique_name}" style="max-width:100%;" />
                <p><a href="/form">Back</a></p>
                """
            else:
                return f"<p>Error {r.status_code}: {r.text}</p><a href='/form'>Back</a>"
        except Exception as e:
            return f"<p>Request failed: {e}</p><a href='/form'>Back</a>"

    return '''
    <h2>Screenshot Form</h2>
    <form method="post">
        URL: <input name="url" size="60"><br><br>
        API Key: <input name="api_key" size="30"><br><br>
        Proxy (optional): <input name="proxy" size="30"><br><br>
        Width (optional): <input name="width" size="6"> Height: <input name="height" size="6"><br><br>
        <input type="submit" value="Take Screenshot">
    </form>
    '''

@app.route("/preview/<filename>")
def preview(filename):
    preview_path = os.path.join(tempfile.gettempdir(), filename)

    if os.path.exists(preview_path):
        response = send_file(preview_path, mimetype="image/png")
        os.remove(preview_path)
        return response

    return "Screenshot not found", 404

# End FORM option

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/metrics", methods=["GET"])
def get_metrics():
    return jsonify(metrics)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
