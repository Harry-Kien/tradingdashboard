"""Keep MIT notices in the embedded bundle and record the built artifact hash."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
bundle = root / 'indicators.js'
body = bundle.read_text(encoding='utf-8')
marker = '/* HGR OSS 1.0.0 - MIT notices\n'
if not body.startswith(marker):
    licenses = '\n\n'.join((root / (name + '-LICENSE.txt')).read_text(encoding='utf-8')
                           for name in ('indicatorts', 'technicalindicators'))
    body = marker + licenses + '\n*/\n' + body
    bundle.write_text(body, encoding='utf-8', newline='\n')
path = root / 'PROVENANCE.json'
record = json.loads(path.read_text(encoding='utf-8'))
record['bundle_sha256'] = hashlib.sha256(bundle.read_bytes()).hexdigest()
record['bundle_bytes'] = bundle.stat().st_size
record['build_command'] = ('npx --yes --package=esbuild@0.28.1 esbuild build-entry.js --bundle --platform=browser '
                           '--format=iife --global-name=HGR_OSS --target=es2020 --minify --legal-comments=linked --outfile=indicators.js')
record['post_build'] = 'python finalize.py'
path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'bytes': record['bundle_bytes'], 'sha256': record['bundle_sha256']}))
