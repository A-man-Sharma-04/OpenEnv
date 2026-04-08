import urllib.request
import urllib.error

try:
    resp = urllib.request.urlopen('http://127.0.0.1:8001/')
    print('status', resp.status)
    body = resp.read(1024)
    print(body.decode('utf-8', errors='replace'))
except urllib.error.HTTPError as e:
    print('HTTPError', e.code)
    print(e.read().decode('utf-8', errors='replace'))
except Exception as e:
    print('ERROR', type(e).__name__, e)
