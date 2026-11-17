"""Check HTML, JS, CSS, API and admin assets through the public gateway."""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

base = (sys.argv[1] if len(sys.argv) > 1
        else 'http://localhost:8080').rstrip('/')


def fetch(path, content_type=None):
    url = urllib.parse.urljoin(base + '/', path)
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            body = response.read()
            mime = response.headers.get_content_type()
            if content_type and mime not in content_type:
                raise RuntimeError(f'{url}: unexpected content type {mime}')
            if not body:
                raise RuntimeError(f'{url}: empty response')
            print(f'OK {response.status} {path} ({mime})')
            return body
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'{url}: HTTP {error.code}') from error


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.styles = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'script' and values.get('src'):
            self.scripts.append(values['src'])
        if tag == 'link' and values.get('rel') == 'stylesheet':
            self.styles.append(values['href'])


parser = AssetParser()
parser.feed(fetch('/', ('text/html',)).decode('utf-8'))
if not parser.scripts:
    raise RuntimeError('No frontend JavaScript found in index.html')
for path in parser.scripts:
    fetch(path, ('application/javascript', 'text/javascript'))
for path in parser.styles:
    fetch(path, ('text/css',))
for path in ('/api/tags/', '/api/recipes/'):
    json.loads(fetch(path, ('application/json',)))
fetch('/api/docs/', ('text/html',))
fetch('/backend_static/admin/css/base.css', ('text/css',))
print('Website smoke checks passed.')
