import requests

urls = [
    "https://34-45-106-67.sslip.io",
    "https://34.45.106.67.sslip.io",
    "https://34-45-106-67.sslip.io:5000",
    "http://34-45-106-67.sslip.io",
    "https://34-45-106-67.sslip.io/api/models",
]

print("=== HTTPS & Redirect Verification ===")
for url in urls:
    try:
        r = requests.get(url, allow_redirects=False, timeout=5)
        loc = r.headers.get("Location", "")
        print(f"[{r.status_code}] {url} -> {loc if loc else 'OK (Served)'}")
    except Exception as e:
        print(f"[ERR] {url} -> {e}")
