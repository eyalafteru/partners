#!/usr/bin/env python3
import smtplib
import socket
import os

host = os.environ.get("SMTP_HOST", "loan-israel.co.il")
port = int(os.environ.get("SMTP_PORT", 465))
user = os.environ.get("SMTP_USER", "eyal@loan-israel.co.il")
password = os.environ.get("SMTP_PASSWORD", "")

print(f"Testing SMTP connection to {host}:{port}")
print(f"User: {user}")

# Test DNS
try:
    ip = socket.gethostbyname(host)
    print(f"✅ DNS OK: {host} -> {ip}")
except Exception as e:
    print(f"❌ DNS FAILED: {e}")
    exit(1)

# Test socket connection
try:
    socket.setdefaulttimeout(10)
    s = socket.create_connection((host, port))
    print(f"✅ Socket connection OK to port {port}")
    s.close()
except Exception as e:
    print(f"❌ Socket FAILED: {e}")
    exit(1)

# Test SMTP SSL
try:
    server = smtplib.SMTP_SSL(host, port, timeout=30)
    print("✅ SMTP_SSL connection OK!")
    server.login(user, password)
    print("✅ Login OK!")
    server.quit()
    print("✅ All tests passed!")
except Exception as e:
    print(f"❌ SMTP FAILED: {e}")
    exit(1)
