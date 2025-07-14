# Flask based Screenshot API

A simple Flask-based API that captures website screenshots using Selenium and Chrome (headless).  
Built for lightweight automation, Docker deployment, and optional proxy routing.

## 🚀 Features

- Capture full-page screenshots via API
- Simple API key authentication (do not use for prod)
- Proxy support (HTTP/SOCKS, think about TOR pages or geoblocked content)
- Configurable via `.env` (resolution, proxy, API key)
- Some `/health` and `/metrics` endpoints
- Structured JSON logging to stdout
- Docker-ready



## Configuration via `.env`

Create a `.env` file in the root of the project:

```dotenv
# Authentication
API_KEY=my-secret-key

# Screenshot defaults
DEFAULT_WIDTH=1920
DEFAULT_HEIGHT=1080
DEFAULT_PROXY=  # example: socks5://127.0.0.1:9050
```

> You can override these per-request via the API.


## Docker Deployment

### Build & Run

```bash
docker build -t screenshot-api .
docker run --env-file .env -p 5000:5000 --rm screenshot-api
```


## API Usage

### Endpoint

```
POST /screenshot
```

### Headers

```http
X-API-Key: your-api-key
Content-Type: application/json
```

### JSON Body

```json
{
  "url": "https://example.com",
  "width": 1366,
  "height": 768,
  "proxy": "socks5://127.0.0.1:9050"
}
```

### Response

- `200 OK`: PNG screenshot (binary)
- `401 Unauthorized`: Invalid API key
- `400 Bad Request`: Missing or invalid fields
- `500 Internal Server Error`: Selenium or capture error

### Example `curl`

```bash
curl -X POST http://localhost:5000/screenshot \
  -H "X-API-Key: my-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}' --output screenshot.png
```

---

## Health & Metrics

Nothing fancy, not database backed or something.

- `GET /health` → `{"status": "ok"}`
- `GET /metrics` → JSON counters

```json
{
  "total_requests": 10,
  "screenshots_taken": 9,
  "errors": 1
}
```

---

## Logging

All actions and errors are logged to stdout as structured JSON:

```json
{"timestamp":"2025-07-14T15:21:33.412Z","event":"screenshot_taken","data":{"url":"https://example.com","ip":"172.17.0.1"}}
```

