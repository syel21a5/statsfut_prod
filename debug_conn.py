
import requests

url = "https://www.soccerstats.com/latest.asp?league=england"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    print(f"Connecting to {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Content Length: {len(response.content)}")
    if response.status_code == 200:
        print("Success! Head of content:")
        print(response.text[:200])
except Exception as e:
    print(f"Error: {e}")
