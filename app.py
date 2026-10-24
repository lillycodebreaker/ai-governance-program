"""Local governance engineering demonstrator. Python 3.10+, no dependencies."""
import hashlib
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
# Support the desktop's isolated bundled Python runtime as well as standard Python.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import calculate
from testing_tools import run_real

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'governance.db'
STEPS = ['AI registration / inventory', 'Intake completeness', 'Risk classification / routing', 'Policy-as-code', 'Developer SDK', 'Traditional ML evaluation', 'GenAI / RAG evaluation', 'Security / adversarial testing', 'Agentic AI controls', 'CI/CD governance gates', 'Data protection', 'Runtime guardrails', 'Observability', 'Continuous governance', 'Evidence / audit trail', 'Developer self-service']

@contextmanager
def connect():
    db = sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS assets (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, asset TEXT, body TEXT, previous TEXT, digest TEXT)')
    try:
        with db:
            yield db
    finally:
        db.close()

def policy():
    return json.loads((ROOT / 'policy.json').read_text())

def evidence(db, asset, kind, detail):
    previous = db.execute('SELECT digest FROM events ORDER BY seq DESC LIMIT 1').fetchone()
    previous = previous[0] if previous else '0' * 64
    body = json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'kind': kind, 'detail': detail}, sort_keys=True)
    digest = hashlib.sha256((previous + asset + body).encode()).hexdigest()
    db.execute('INSERT INTO events(asset,body,previous,digest) VALUES(?,?,?,?)', (asset, body, previous, digest))

def save(db, asset):
    db.execute('INSERT OR REPLACE INTO assets VALUES (?,?)', (asset['id'], json.dumps(asset)))

def load(db, asset_id):
    row = db.execute('SELECT body FROM assets WHERE id=?', (asset_id,)).fetchone()
    if not row:
        raise ValueError('Asset not found')
    return json.loads(row[0])

def baseline(asset):
    return {key: asset.get(key) for key in ['model', 'prompt_version', 'tools', 'data_source', 'population', 'phi', 'external', 'autonomous', 'kind', 'human_escalation']}

def classify(asset):
    return 'high' if asset['phi'] or asset['autonomous'] else 'medium' if asset['external'] else 'low'

def redact(text):
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED SSN]', text)
    return re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[REDACTED EMAIL]', text)

def evaluate(asset, scenario, tool_mode='fixture'):
    # These deterministic fixtures exercise orchestration, not real model quality.
    p = policy()
    required = ['privacy', 'injection', 'safety', 'monitoring', 'human_escalation']
    required += ['f1', 'fairness_gap'] if asset['kind'] == 'ml' else ['groundedness', 'retrieval_recall', 'language_quality']
    if asset['autonomous']:
        required += ['tool_scope', 'approval_gate']
    values = {'privacy': 1, 'injection': 1, 'safety': 1, 'monitoring': 1, 'human_escalation': int(asset['human_escalation']), 'f1': .91, 'fairness_gap': .04, 'groundedness': .94, 'retrieval_recall': .92, 'language_quality': .91, 'tool_scope': 1, 'approval_gate': 1}
    if scenario == 'privacy_failure':
        values['privacy'] = 0
    if scenario == 'quality_failure':
        values['f1' if asset['kind'] == 'ml' else 'groundedness'] = .5
    results = [{'control': c, 'value': values[c], 'threshold': p['thresholds'][c], 'passed': values[c] <= p['thresholds'][c] if c == 'fairness_gap' else values[c] >= p['thresholds'][c], 'source': 'synthetic fixture', 'execution': 'fixture'} for c in required]
    if asset['kind'] == 'rag':
        toxicity, confidence, versions = .02, .94, {}
        if tool_mode == 'real':
            toxicity, confidence, versions = run_real()
        for control, value, threshold, passed, tool in [
            ('langfair_toxic_fraction', toxicity, .05, toxicity <= .05, 'LangFair'),
            ('uqlm_consistency_confidence', confidence, .8, confidence >= .8, 'UQLM')]:
            results.append(dict(control=control, value=value, threshold=threshold, passed=passed, source=tool + (' real adapter' if tool_mode == 'real' else ' simulated fixture — library not executed'), execution='ci_automated' if tool_mode == 'real' else 'fixture', versions=versions))
    return results

def action(route, data):
    with connect() as db:
        if route == '/api/operations':
            kind = data.get('kind')
            detail = {}
            asset_id = data.get('id', 'organization')
            if kind == 'team_adoption':
                team = str(data.get('team', '')).strip()
                if not team: raise ValueError('Team name required')
                detail = {'team': team, 'adopted': data.get('adopted') is True}
                asset_id = 'organization'
            elif kind == 'exception':
                load(db, asset_id)
                detail = {'reason': str(data.get('reason', 'Demo waiver record'))[:500]}
            elif kind == 'incident_detected':
                a = load(db, asset_id)
                if a['status'] != 'deployed': raise ValueError('Deploy an asset before recording a production incident')
                category = data.get('category')
                if category not in ['phi_leakage', 'unsafe_output', 'policy_violation', 'fairness_issue', 'agent_incident']: raise ValueError('Invalid incident category')
                occurred = datetime.fromisoformat(data.get('occurred_at', ''))
                if occurred.tzinfo is None or occurred > datetime.now(timezone.utc): raise ValueError('Occurrence requires a past timestamp with timezone')
                detail = {'incident_id': uuid.uuid4().hex[:12], 'category': category, 'occurred_at': occurred.isoformat()}
            elif kind == 'incident_resolved':
                incident_id = data.get('incident_id')
                rows = [json.loads(r[0]) for r in db.execute('SELECT body FROM events WHERE asset=?', (asset_id,))]
                if not any(e['kind'] == 'incident_detected' and e['detail']['incident_id'] == incident_id for e in rows): raise ValueError('Incident not found')
                if any(e['kind'] == kind and e['detail']['incident_id'] == incident_id for e in rows): raise ValueError('Incident already resolved')
                detail = {'incident_id': incident_id}
            else: raise ValueError('Unknown operational event')
            evidence(db, asset_id, kind, detail)
            return detail
        if route == '/api/register':
            missing = [k for k in ['name', 'owner', 'purpose', 'model', 'data_source', 'population'] if not str(data.get(k, '')).strip()]
            if missing:
                raise ValueError('Required intake fields: ' + ', '.join(missing))
            asset = {k: data[k] for k in ['name', 'owner', 'purpose', 'model', 'data_source', 'population']}
            asset.update(id='AI-' + uuid.uuid4().hex[:8], kind=data.get('kind', 'rag'), phi=bool(data.get('phi')), external=bool(data.get('external')), autonomous=bool(data.get('autonomous')), human_escalation=bool(data.get('human_escalation')), prompt_version='v1', tools=['search'], status='registered', results=[], approved_baseline=None, circuit_open=False)
            if asset['kind'] not in ['rag', 'ml']:
                raise ValueError('kind must be rag or ml')
            asset['risk'] = classify(asset)
            evidence(db, asset['id'], 'registration', {'intake': 'complete', 'risk': asset['risk'], 'policy': policy()['version']})
        else:
            asset = load(db, data.get('id'))
            if route == '/api/evaluate':
                scenario = data.get('scenario', 'pass')
                if scenario not in ['pass', 'privacy_failure', 'quality_failure']:
                    raise ValueError('Unknown test scenario')
                tool_mode = data.get('tool_mode', 'fixture')
                if tool_mode not in ['fixture', 'real']: raise ValueError('Invalid tool mode')
                asset['results'] = evaluate(asset, scenario, tool_mode)
                asset['policy_version'] = policy()['version']
                asset['evaluated_baseline'] = baseline(asset)
                asset['status'] = 'review_required' if all(r['passed'] for r in asset['results']) else 'blocked'
                evidence(db, asset['id'], 'ci_gate', {'build': uuid.uuid4().hex[:8], 'policy': asset['policy_version'], 'baseline': baseline(asset), 'results': asset['results'], 'decision': asset['status']})
            elif route == '/api/approve':
                if asset['status'] != 'review_required' or asset.get('policy_version') != policy()['version'] or asset.get('evaluated_baseline') != baseline(asset):
                    raise ValueError('Current passing evaluations are required before approval')
                asset['status'] = 'deployed'
                asset['approved_baseline'] = baseline(asset)
                evidence(db, asset['id'], 'demo_human_approval', {'reviewer': 'local-demo-reviewer', 'policy': asset['policy_version'], 'baseline': baseline(asset)})
                evidence(db, asset['id'], 'deployment', {'release_id': uuid.uuid4().hex, 'policy': asset['policy_version'], 'baseline': baseline(asset), 'environment': 'synthetic-local'})
            elif route == '/api/change':
                asset['prompt_version'] = 'v' + str(int(asset['prompt_version'][1:]) + 1)
                asset['status'] = 'reassessment_required'
                asset['results'] = []
                evidence(db, asset['id'], 'material_change', {'field': 'prompt_version', 'current': asset['prompt_version'], 'approved_baseline': asset['approved_baseline'], 'decision': 'deployment invalidated'})
            elif route == '/api/runtime':
                if asset['status'] != 'deployed' or asset.get('policy_version') != policy()['version'] or baseline(asset) != asset['approved_baseline']:
                    raise ValueError('Runtime blocked: current policy and approved deployment required')
                started = time.perf_counter()
                prompt = str(data.get('prompt', ''))[:4000]
                tool = str(data.get('tool', 'search'))
                injection = any(s in prompt.lower() for s in ['ignore previous', 'reveal secrets', 'system prompt'])
                decision = 'allowed'
                if asset['circuit_open']:
                    decision = 'circuit_open'
                elif injection:
                    decision = 'blocked_injection'
                elif tool not in asset['tools']:
                    decision = 'human_approval_required' if tool == 'action_api' and asset['autonomous'] else 'denied_tool'
                elif redact(prompt) != prompt:
                    decision = 'redacted_escalated'
                if decision.startswith('blocked'):
                    asset['circuit_open'] = True
                result = {'trace_id': uuid.uuid4().hex, 'decision': decision, 'output': 'Synthetic benefit reference: contact the benefits team for member-specific guidance.' if decision == 'allowed' else 'Request stopped or routed to a human.', 'latency_ms': round((time.perf_counter() - started) * 1000, 2), 'model': asset['model'], 'prompt_version': asset['prompt_version'], 'tool': tool}
                # Raw prompts and outputs are deliberately excluded from telemetry.
                evidence(db, asset['id'], 'runtime_trace', result)
                save(db, asset)
                return result
            else:
                raise ValueError('Unknown endpoint')
        save(db, asset)
        return asset

def snapshot():
    with connect() as db:
        assets = [json.loads(r[0]) for r in db.execute('SELECT body FROM assets')]
        events, previous, valid = [], '0' * 64, True
        for seq, asset, body, prev, digest in db.execute('SELECT * FROM events ORDER BY seq'):
            valid &= prev == previous and digest == hashlib.sha256((prev + asset + body).encode()).hexdigest()
            previous = digest
            events.append(dict(seq=seq, asset=asset, **json.loads(body), previous=prev, digest=digest))
        return {'assets': assets, 'events': events, 'chain_valid': bool(valid), 'policy': policy(), 'steps': STEPS, 'metrics': calculate(events) if valid else [], 'metrics_note': 'Synthetic local activity; all-time window. Invalid chain suppresses metrics. Legacy approvals without deployment events are excluded.'}

class Handler(BaseHTTPRequestHandler):
    def reply(self, value, status=200):
        raw = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == '/':
            raw = (ROOT / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(raw)
        elif self.path in ['/api/state', '/api/evidence', '/api/metrics']:
            self.reply(snapshot())
        else:
            self.reply({'error': 'Not found'}, 404)

    def do_POST(self):
        # Local demo has no identity provider; reject cross-origin browser writes.
        if self.headers.get('Origin') not in [None, 'http://127.0.0.1:8000', 'http://localhost:8000']:
            return self.reply({'error': 'Origin rejected'}, 403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length > 16000:
                raise ValueError('Request too large')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('JSON object required')
            self.reply(action(self.path, data))
        except (ValueError, TypeError, KeyError) as exc:
            self.reply({'error': str(exc)}, 400)

if __name__ == '__main__':
    print('AI Governance Engineering Lab: http://127.0.0.1:8000', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8000), Handler).serve_forever()
