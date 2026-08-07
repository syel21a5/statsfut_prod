#!/bin/bash
# Quick test: fetch round 1 of Bundesliga (Germany) via Tor and check if events come back
echo "=== Testing SofaScore API via Tor ==="
echo ""

# Test 1: Check Tor IP
echo "1. Checking Tor IP..."
TOR_IP=$(curl --socks5 127.0.0.1:9050 -s https://check.torproject.org/api/ip)
echo "   Tor IP response: $TOR_IP"
echo ""

# Test 2: Fetch rounds info
echo "2. Fetching rounds for Bundesliga (Germany)..."
ROUNDS=$(curl --socks5 127.0.0.1:9050 -s "https://api.sofascore.com/api/v1/unique-tournament/35/season/77333/rounds")
echo "   Rounds response length: $(echo $ROUNDS | wc -c) bytes"
echo ""

# Test 3: Fetch events for round 1
echo "3. Fetching events for round 1..."
EVENTS=$(curl --socks5 127.0.0.1:9050 -s "https://api.sofascore.com/api/v1/unique-tournament/35/season/77333/events/round/1")
echo "   Events response length: $(echo $EVENTS | wc -c) bytes"
echo "   First 200 chars: $(echo $EVENTS | head -c 200)"
echo ""

# Test 4: Use python to parse
echo "4. Parsing with Python..."
echo "$EVENTS" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    events = d.get('events', [])
    print(f'   Events count: {len(events)}')
    if events:
        ev = events[0]
        home = ev.get('homeTeam',{}).get('name','?')
        away = ev.get('awayTeam',{}).get('name','?')
        print(f'   First event: {home} vs {away}')
    else:
        print(f'   Response keys: {list(d.keys())}')
except Exception as e:
    print(f'   Error parsing: {e}')
    print(f'   Raw: {sys.stdin.read()[:200]}')
"

# Test 5: Test with curl_cffi (same as master_fetcher.py uses)
echo ""
echo "5. Testing with curl_cffi (same lib as master_fetcher)..."
python -c "
from curl_cffi import requests
import json

session = requests.Session(impersonate='chrome120')
proxies = {'http': 'socks5://127.0.0.1:9050', 'https': 'socks5://127.0.0.1:9050'}

try:
    r = session.get('https://api.sofascore.com/api/v1/unique-tournament/35/season/77333/rounds', proxies=proxies, timeout=15)
    print(f'   Rounds HTTP status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        rounds = data.get('rounds', [])
        current = data.get('currentRound', {})
        print(f'   Total rounds: {len(rounds)}, Current round: {current}')
    else:
        print(f'   Response: {r.text[:200]}')
except Exception as e:
    print(f'   Error: {e}')

try:
    r2 = session.get('https://api.sofascore.com/api/v1/unique-tournament/35/season/77333/events/round/1', proxies=proxies, timeout=15)
    print(f'   Events round 1 HTTP status: {r2.status_code}')
    if r2.status_code == 200:
        data2 = r2.json()
        events = data2.get('events', [])
        print(f'   Events count: {len(events)}')
    else:
        print(f'   Response: {r2.text[:200]}')
except Exception as e:
    print(f'   Error: {e}')
"

echo ""
echo "=== Test Complete ==="
