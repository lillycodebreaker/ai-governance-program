"""Metrics derived exclusively from the exported event stream (no asset snapshots)."""
from datetime import datetime
from statistics import mean

def calculate(events):
    groups = {}
    for e in events:
        groups.setdefault(e['asset'], []).append(e)
    gates = [e for e in events if e['kind'] == 'ci_gate']
    releases = [e for e in events if e['kind'] == 'deployment']
    cohorts, durations, reviewed, audited, compliant = [], [], [], [], []
    for es in groups.values():
        registrations = [e for e in es if e['kind'] == 'registration']
        cycles = []
        for e in es:
            if e['kind'] in ['registration', 'material_change']:
                cycles.append([])
            if cycles:
                cycles[-1].append(e)
        for cycle in cycles:
            gs = [e for e in cycle if e['kind'] == 'ci_gate']
            if gs:
                cohorts.append(gs[0]['detail']['decision'] == 'review_required')
                risk = next((e['detail'].get('risk') for e in registrations), None)
                if risk == 'low':
                    reviewed.append(any(e['kind'] == 'demo_human_approval' or (e['kind'] == 'ci_gate' and e['detail']['decision'] == 'review_required') for e in cycle))
        asset_audits = []
        asset_releases = [e for e in es if e['kind'] == 'deployment']
        for release in asset_releases:
            prior = [e for e in es if e['seq'] < release['seq']]
            approval = next((e for e in reversed(prior) if e['kind'] == 'demo_human_approval'), None)
            gate = next((e for e in reversed(prior) if e['kind'] == 'ci_gate'), None)
            valid = bool(gate and gate['detail']['decision'] == 'review_required' and all(r['passed'] for r in gate['detail']['results']) and gate['detail']['policy'] == release['detail']['policy'] and gate['detail']['baseline'] == release['detail']['baseline'])
            compliant.append(valid)
            asset_audits.append(bool(valid and approval and registrations and gate['detail'].get('build') and release['detail'].get('release_id') and approval['detail'].get('reviewer') and approval['detail'].get('baseline') == release['detail']['baseline'] and approval['detail'].get('policy') == release['detail']['policy']))
        if asset_releases:
            last_release = asset_releases[-1]
            if not any(e['seq'] > last_release['seq'] and e['kind'] in ['material_change', 'ci_gate'] for e in es):
                audited.append(asset_audits[-1])
        if registrations:
            first_release = next((e for e in es if e['kind'] in ['demo_human_approval', 'deployment']), None)
            if first_release:
                durations.append((datetime.fromisoformat(first_release['timestamp']) - datetime.fromisoformat(registrations[0]['timestamp'])).total_seconds())
    controls = [r for g in gates for r in g['detail']['results']]
    latest_team = {}
    for e in events:
        if e['kind'] == 'team_adoption': latest_team[e['detail']['team']] = e['detail']['adopted']
    incidents = [e for e in events if e['kind'] == 'incident_detected']
    resolved = []
    for issue in incidents:
        d = issue['detail']
        resolution = next((e for e in events if e['kind'] == 'incident_resolved' and e['detail']['incident_id'] == d['incident_id']), None)
        if resolution:
            resolved.append((datetime.fromisoformat(resolution['timestamp']) - datetime.fromisoformat(issue['timestamp'])).total_seconds())
    def pct(values): return round(100 * sum(values) / len(values), 1) if values else None
    def avg(values): return round(mean(values), 2) if values else None
    def metric(name, value, unit, direction, formula, n):
        return dict(name=name, value=value, unit=unit, direction=direction, formula=formula, denominator=n)
    definitions = [
        ('Governance cycle time', 'time from registration to approval/deployment', avg(durations), 'seconds', '↓', 'Mean registration → first approval or deployment for completed assets', len(durations)),
        ('First-pass success rate', '% of submissions passing without repeated remediation', pct(cohorts), '%', '↑', 'Submissions passing their first CI gate / evaluated submissions; registration or material change starts a submission', len(cohorts)),
        ('Automated control coverage', '% of required RAI controls/tests executed automatically in CI/CD', pct([r.get('execution') == 'ci_automated' for r in controls]), '%', '↑', 'Automatically executed required control instances / all required control instances in CI runs; fixtures excluded', len(controls)),
        ('Manual review rate', '% of cases needing human review for routine/low-risk cases', pct(reviewed), '%', '↓', 'Low-risk submissions requiring human review / evaluated low-risk submissions; review requirement counts before approval completion', len(reviewed)),
        ('Developer adoption', '% of AI teams using the standard SDK/pipeline', pct(list(latest_team.values())), '%', '↑', 'Teams declaring standard SDK and pipeline use / inventoried AI teams; latest declaration per team', len(latest_team)),
        ('Policy compliance', '% of releases meeting required controls before production', pct(compliant), '%', '↑', 'Releases with prior passing CI evidence matching release policy and baseline / all production-representing demo releases', len(releases)),
        ('Exception rate', 'number of waivers/bypasses', sum(e['kind'] == 'exception' for e in events), 'waivers/bypasses', '↓', 'Count of recorded waivers/bypasses in the audit trail; records do not bypass controls', None),
        ('Production risk', 'PHI leakage, unsafe outputs, policy violations, fairness issues, agent incidents', len(incidents) if releases or incidents else None, 'incidents', '↓', 'Confirmed incidents across the five risk categories; blocked attempts excluded', None),
        ('Mean time to detect/remediate', 'time from RAI issue detection to resolution', avg(resolved), 'seconds', '↓', 'Mean detection → resolution for resolved RAI issues; unresolved issues excluded', len(resolved)),
        ('Auditability', '% of deployed AI assets with complete evidence, versioning, approvals, and traceability', pct(audited), '%', '↑', 'Currently deployed unique assets whose latest release has registration, passing versioned CI evidence, approval, build and release traceability / currently deployed unique assets', len(audited)),
    ]
    result = []
    for name, definition, value, unit, direction, formula, n in definitions:
        item = metric(name, value, unit, direction, formula, n)
        item['definition'] = definition
        if name == 'Production risk':
            item['breakdown'] = {category: sum(e['detail']['category'] == category for e in incidents) for category in ['phi_leakage', 'unsafe_output', 'policy_violation', 'fairness_issue', 'agent_incident']}
        if name == 'Mean time to detect/remediate':
            item['unresolved_issues'] = len(incidents) - len(resolved)
        result.append(item)
    return result
