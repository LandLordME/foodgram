"""Create a copy that checks ingredient prefixes without case sensitivity."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
source = root / 'postman_collection' / 'foodgram.postman_collection.json'
destination = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    root / 'verification-output' / 'foodgram.postman_collection.json'
)
collection = json.loads(source.read_text(encoding='utf-8'))
old = 'elem.name.startsWith(expectedingredientNameStart)'
new = ('elem.name.toLowerCase().startsWith('
       'expectedingredientNameStart.toLowerCase())')
replacements = 0


def visit(items):
    global replacements
    for item in items:
        if 'item' in item:
            visit(item['item'])
        for event in item.get('event', []):
            lines = event.get('script', {}).get('exec', [])
            for index, line in enumerate(lines):
                if old in line:
                    lines[index] = line.replace(old, new)
                    replacements += 1


visit(collection['item'])
if replacements != 1:
    raise RuntimeError('The upstream collection changed; review the patch.')
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(collection, ensure_ascii=False, indent=2),
                       encoding='utf-8')
print(f'Prepared {destination}; original collection unchanged.')
