#!/usr/bin/env python3
"""Consulta GA4 (statsfut.com e statsfutbrasil.blogspot.com) — read-only.
Uso: python3 ga_query.py [dias] [summary|pages|sources] [site|blog]
"""
import json, urllib.request, datetime, sys

sd = "/root/.openclaw/workspace/.secrets"
tokens = json.load(open(f"{sd}/gsc_tokens.json"))
AT = tokens["access_token"]

PROPS = {
    "blog": "properties/544305744",   # statsfutbrasil.blogspot.com
    "site": "properties/537252454",   # statsfut.com
}

def run_report(prop, body):
    req = urllib.request.Request(
        f"https://analyticsdata.googleapis.com/v1beta/{prop}:runReport",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {AT}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 28
    mode = sys.argv[2] if len(sys.argv) > 2 else "summary"
    target = sys.argv[3] if len(sys.argv) > 3 else "blog"
    prop = PROPS[target]
    end = datetime.date.today().isoformat()
    start = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    dr = {"dateRanges": [{"startDate": start, "endDate": end}]}

    if mode == "summary":
        r = run_report(prop, dict(dr, metrics=[{"name": "sessions"}, {"name": "totalUsers"}, {"name": "screenPageViews"}]))
        for row in r.get("rows", []):
            m = [x["value"] for x in row["metricValues"]]
            print(f"{target}: sessoes={m[0]} usuarios={m[1]} pageviews={m[2]}")
    elif mode == "pages":
        r = run_report(prop, dict(dr, dimensions=[{"name": "pagePath"}], metrics=[{"name": "screenPageViews"}],
            orderBys=[{"metric": {"metricName": "screenPageViews"}, "desc": True}], limit=10))
        for row in r.get("rows", []):
            print(f"{row['dimensionValues'][0]['value'][:65]:65s} {row['metricValues'][0]['value']}")
    elif mode == "sources":
        r = run_report(prop, dict(dr, dimensions=[{"name": "sessionDefaultChannelGroup"}], metrics=[{"name": "sessions"}],
            orderBys=[{"metric": {"metricName": "sessions"}, "desc": True}]))
        for row in r.get("rows", []):
            print(f"{row['dimensionValues'][0]['value']:25s} {row['metricValues'][0]['value']}")
