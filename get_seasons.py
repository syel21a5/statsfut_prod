from curl_cffi import requests

url = 'https://api.sofascore.com/api/v1/unique-tournament/480/seasons'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Origin': 'https://www.sofascore.com',
    'Referer': 'https://www.sofascore.com/'
}
response = requests.get(url, headers=headers, impersonate="chrome110")
if response.status_code == 200:
    for s in response.json().get('seasons', []):
        print(f"Year: {s.get('year')}, ID: {s.get('id')}")
else:
    print('Error:', response.status_code)
