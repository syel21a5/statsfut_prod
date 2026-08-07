#!/usr/bin/env python3
"""Checa a caixa support@statsfut.com (IMAP) + fila do postfix."""
import json, imaplib, email
from email.header import decode_header
import subprocess

c = json.load(open("/root/.openclaw/workspace/.secrets/support_mail.json"))

def dec(s):
    if not s: return ""
    parts = decode_header(s)
    out = []
    for txt, enc in parts:
        if isinstance(txt, bytes):
            out.append(txt.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(txt)
    return "".join(out)

m = imaplib.IMAP4_SSL(c["imap_host"], c["imap_port"], timeout=20)
m.login(c["email"], c["password"])
m.select("INBOX")
status, data = m.search(None, "UNSEEN")
unseen_ids = data[0].split() if data and data[0] else []
print(f"INBOX: {len(unseen_ids)} não lidas")
for i in unseen_ids[-8:]:
    status, msg_data = m.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
    if msg_data and msg_data[0]:
        msg = email.message_from_bytes(msg_data[0][1])
        print(f"  - {dec(msg.get('Date',''))[:16]} | {dec(msg.get('From',''))[:40]} | {dec(msg.get('Subject',''))[:60]}")
m.logout()

try:
    q = subprocess.run(["mailq"], capture_output=True, text=True, timeout=15).stdout
    import re
    ids = re.findall(r"^[A-F0-9]{10,}\s", q, re.M)
    print(f"FILA POSTFIX: {len(ids)} mensagens aguardando (retry)")
except Exception:
    pass
