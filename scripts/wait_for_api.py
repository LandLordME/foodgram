import sys
import time
import urllib.error
import urllib.request

url = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8000/api/tags/'
for attempt in range(60):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            if response.status == 200:
                print('API is ready.')
                break
    except (OSError, urllib.error.URLError):
        time.sleep(1)
else:
    raise SystemExit('API did not become ready.')
