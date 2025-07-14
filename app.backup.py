from flask import Flask, request, send_file, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import tempfile
import time
import os

app = Flask(__name__)

# Hardcoded API key (you can move this to env vars later)
API_KEY = "my-secret-key"

def take_screenshot(url: str, width=1920, height=1080) -> str:
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument(f"--window-size={width},{height}")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        time.sleep(2)  # Wait for page load

        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        driver.save_screenshot(tmp_file.name)
        return tmp_file.name
    finally:
        driver.quit()

@app.route("/screenshot", methods=["POST"])
def screenshot():
    # Check API key
    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    # Parse JSON body
    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' field"}), 400

    url = data["url"]

    try:
        screenshot_path = take_screenshot(url)
        return send_file(screenshot_path, mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'screenshot_path' in locals() and os.path.exists(screenshot_path):
            os.remove(screenshot_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

