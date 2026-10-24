"""Recompute dashboard metrics from an exported audit JSON, verifying the chain."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import calculate

if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as f:
        export = json.load(f)
    previous = '0' * 64
    for e in export['events']:
        body = json.dumps({k: e[k] for k in ['timestamp', 'kind', 'detail']}, sort_keys=True)
        digest = hashlib.sha256((previous + e['asset'] + body).encode()).hexdigest()
        if e['previous'] != previous or e['digest'] != digest:
            raise SystemExit('Audit chain verification failed; metrics suppressed')
        previous = digest
    print(json.dumps(calculate(export['events']), indent=2))
