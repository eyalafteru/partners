"""Test script for reading Chrome cookies - multiple methods"""
import shutil, tempfile, os, sqlite3, subprocess

src = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies")
dst = os.path.join(tempfile.gettempdir(), "fb_cookies_test.db")

def try_copy(src, dst):
    """Try multiple copy methods for locked Chrome cookie file"""
    # Method 1: shutil.copy2
    try:
        shutil.copy2(src, dst)
        return "shutil.copy2"
    except Exception as e:
        print(f"  Method 1 (copy2) failed: {e}")

    # Method 2: PowerShell Copy-Item -Force
    try:
        result = subprocess.run(
            ["powershell", "-Command", f'Copy-Item -Path "{src}" -Destination "{dst}" -Force'],
            capture_output=True, text=True, timeout=10
        )
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            return "powershell"
    except Exception as e:
        print(f"  Method 2 (powershell) failed: {e}")

    # Method 3: cmd /c copy
    try:
        result = subprocess.run(
            ["cmd", "/c", "copy", "/Y", src, dst],
            capture_output=True, text=True, timeout=10
        )
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            return "cmd_copy"
    except Exception as e:
        print(f"  Method 3 (cmd copy) failed: {e}")

    # Method 4: Read file in binary mode (works if SQLite WAL mode)
    try:
        with open(src, "rb") as f:
            data = f.read()
        with open(dst, "wb") as f:
            f.write(data)
        return "binary_read"
    except Exception as e:
        print(f"  Method 4 (binary read) failed: {e}")

    # Method 5: Open SQLite directly (immutable mode - read-only, no lock needed)
    try:
        uri = f"file:{src}?immutable=1"
        conn = sqlite3.connect(uri, uri=True)
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return "sqlite_immutable"
    except Exception as e:
        print(f"  Method 5 (sqlite immutable) failed: {e}")

    return None

print(f"Source: {src}")
print(f"Exists: {os.path.exists(src)}")
print(f"Size: {os.path.getsize(src)} bytes")
print()

method = try_copy(src, dst)

if method == "sqlite_immutable":
    print(f"Using SQLite immutable mode directly on source")
    uri = f"file:{src}?immutable=1"
    conn = sqlite3.connect(uri, uri=True)
elif method:
    print(f"Copy successful via: {method}")
    conn = sqlite3.connect(dst)
else:
    print("ALL methods failed!")
    exit(1)

query = "SELECT name, host_key, path, expires_utc, is_httponly, is_secure, samesite, encrypted_value FROM cookies WHERE host_key LIKE '%facebook.com'"
rows = conn.execute(query).fetchall()
print(f"\nFound {len(rows)} facebook cookies")
for r in rows:
    has_encrypted = len(r[7]) > 0 if r[7] else False
    print(f"  {r[0]:20s} host={r[1]:20s} expires={r[3]} httponly={r[4]} secure={r[5]} samesite={r[6]} encrypted={has_encrypted}")
conn.close()

if method != "sqlite_immutable" and os.path.exists(dst):
    os.unlink(dst)
