"""Example developer SDK backed by the local HTTP API."""
import json
from urllib.request import Request, urlopen

class GovernanceClient:
    def __init__(self, base_url='http://127.0.0.1:8000'):
        self.base_url = base_url

    def call(self, endpoint, **payload):
        request = Request(self.base_url + '/api/' + endpoint, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=10) as response:
            return json.load(response)

    def register(self, **metadata):
        return self.call('register', **metadata)

    def evaluate(self, asset_id, scenario='pass'):
        return self.call('evaluate', id=asset_id, scenario=scenario)

    def validate_policy(self, asset_id):
        result = self.evaluate(asset_id)
        if result['status'] != 'review_required':
            raise RuntimeError('Governance gate failed: deployment blocked')
        return result
