from flask import Flask, request, send_file, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import tempfile
import time
import os

app = Flask(__name__)

API_KEY = "my-secret-key"

def take_screenshot(url: str, proxy: str = None, width=1920, height=1080) -> str:
    """
    Take a screenshot of a webpage.

    Parameters:
        url (str): URL of the webpage to take a screenshot of
        proxy (str, optional): Proxy server to use for the request
        width (int, optional): Width of the screenshot (default: 1920)
        height (int, optional): Height of the screenshot (default: 1080)

    Returns:
        str: Path to the screenshot file
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument(f"--window-size={width},{height}")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    if proxy:
        chrome_options.add_argument(f'--proxy-server={proxy}')

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        time.sleep(2)  # Adjust for slow-loading pages
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        driver.save_screenshot(tmp_file.name)
        return tmp_file.name
    finally:
        driver.quit()

@app.route("/screenshot", methods=["POST"])
def screenshot():
    # Auth check
    """
    Endpoint to generate a screenshot of a webpage.

    Request Body:
        {
            "url": str,  # URL of the webpage to take a screenshot of
            "proxy": str,  # Optional proxy server to use for the request
        }

    Response:
        {
            "error": str,  # Error message if the request was invalid
        }

    Returns:
        A PNG image of the webpage.
    """
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' field"}), 400

    url = data["url"]
    proxy = data.get("proxy")

    try:
        screenshot_path = take_screenshot(url, proxy)
        return send_file(screenshot_path, mimetype="image/png")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'screenshot_path' in locals() and os.path.exists(screenshot_path):
            os.remove(screenshot_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
