#!/usr/bin/env python3
"""Consulta o Google Search Console do statsfut.com via API (read-only)."""
import json, urllib.parse, urllib.request, urllib.error, datetime, sys

SD = "/root/.openclaw/workspace/.secrets"
SITE = urllib.parse.quote("sc-domain:statsfut.com", safe="")

def _load():
    return json.load(open(f"{SD}/gsc_tokens.json")), json.load(open(f"{SD}/gsc_client.json"))

tokens, client = _load()

def refresh():
    global tokens
    data = urllib.parse.urlencode({
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    new = json.load(urllib.request.urlopen(
        urllib.request.Request("https://oauth2.googleapis.com/token", data=data)))
    tokens.update(new)
    json.dump(tokens, open(f"{SD}/gsc_tokens.json", "w"), indent=2)

def api(path, payload=None):
    req = urllib.request.Request(
        "https://www.googleapis.com/webmasters/v3" + path,
        data=json.dumps(payload).encode() if payload else None,
        headers={"Authorization": f"Bearer {tokens['access_token']}",
                 "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            refresh()
            return api(path, payload)
        print("HTTP", e.code, e.read().decode()[:300], file=sys.stderr)
        raise

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "summary"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 28
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    base = {"startDate": start.isoformat(), "endDate": end.isoformat()}

    if mode == "summary":
        r = api("/sites/" + SITE + "/searchAnalytics/query", base)
        for row in r.get("rows", []):
            print(f"cliques={row['clicks']} impressoes={row['impressions']} "
                  f"ctr={row['ctr']:.3f} pos={row['position']:.1f}")
    elif mode == "queries":
        p = dict(base, dimensions=["query"], rowLimit=int(sys.argv[3]) if len(sys.argv) > 3 else 15)
        for row in api("/sites/" + SITE + "/searchAnalytics/query", p).get("rows", []):
            print(f"{row['keys'][0][:55]:55s} cl={row['clicks']:5d} imp={row['impressions']:6d} pos={row['position']:5.1f}")
    elif mode == "pages":
        p = dict(base, dimensions=["page"], rowLimit=int(sys.argv[3]) if len(sys.argv) > 3 else 15)
        for row in api("/sites/" + SITE + "/searchAnalytics/query", p).get("rows", []):
            print(f"{row['keys'][0][:70]:70s} cl={row['clicks']:5d} imp={row['impressions']:6d}")
    elif mode == "countries":
        p = dict(base, dimensions=["country"], rowLimit=10)
        for row in api("/sites/" + SITE + "/searchAnalytics/query", p).get("rows", []):
            print(f"{row['keys'][0]}: cl={row['clicks']:5d} imp={row['impressions']:6d}")
    elif mode == "sitemaps":
        for sm in api("/sites/" + SITE + "/sitemaps").get("sitemap", []):
            print(f"{sm['path']} | {sm.get('type')} | erros={sm.get('errors')} | "
                  f"enviadas={sm.get('contents', [{}])[0].get('submitted', '?')} "
                  f"descobertas={sm.get('contents', [{}])[0].get('discovered', '?')}")
    else:
        print("uso: gsc_query.py [summary|queries|pages|countries|sitemaps] [dias] [limite]")
