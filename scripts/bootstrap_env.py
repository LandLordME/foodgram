import argparse
import secrets
from pathlib import Path

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--demo', action='store_true')
options = parser.parse_args()
destination = root / '.env'
if destination.exists():
    print('.env already exists; nothing changed.')
else:
    content = (root / '.env.example').read_text(encoding='utf-8')
    content = content.replace('replace-with-a-long-random-value',
                              secrets.token_urlsafe(64))
    content = content.replace('replace-with-a-random-database-password',
                              secrets.token_urlsafe(32))
    if options.demo:
        content = content.replace('SEED_DEMO=False', 'SEED_DEMO=True')
        content = content.replace('DEMO_PASSWORD=',
                                  'DEMO_PASSWORD=' + secrets.token_urlsafe(18))
    with destination.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
    print('Created .env with random local secrets.')
