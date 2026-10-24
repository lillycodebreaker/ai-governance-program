"""Optional real adapters; no external models are called in fixture mode."""
import asyncio
import importlib
import json
import os
from importlib.metadata import version

def run_real():
    # This factory is configured by the server operator, never from request input.
    factory = os.environ.get('GOVERNANCE_LLM_FACTORY', '')
    dataset = os.environ.get('GOVERNANCE_EVAL_DATASET', '')
    if ':' not in factory or not dataset:
        raise ValueError('Real mode requires GOVERNANCE_LLM_FACTORY=module:function and GOVERNANCE_EVAL_DATASET JSON path; no fixture fallback')
    try:
        from langfair.auto import AutoEval
        from uqlm import BlackBoxUQ
        module, function = factory.split(':', 1)
        llm = getattr(importlib.import_module(module), function)()
        with open(dataset, encoding='utf-8') as f:
            prompts = json.load(f)['prompts']
        if not prompts or not all(isinstance(p, str) and p for p in prompts):
            raise ValueError('Nonempty evaluation prompts required')
        async def execute():
            fairness = await AutoEval(prompts=prompts, langchain_llm=llm).evaluate(return_data=False)
            uq = await BlackBoxUQ(llm=llm, scorers=['exact_match']).generate_and_score(prompts=prompts, num_responses=5)
            return fairness, uq.to_df()
        fairness, uq = asyncio.run(execute())
        # Metric names are explicit. Unknown result schemas fail closed.
        toxicity = float(fairness['metrics']['Toxicity']['Toxic Fraction'])
        confidence = float(uq['exact_match'].mean())
        return toxicity, confidence, {'langfair': version('langfair'), 'uqlm': version('uqlm')}
    except (ImportError, KeyError, AttributeError, TypeError) as exc:
        raise ValueError('Real tool setup/schema unavailable; check installed versions and adapter mapping: ' + str(exc)) from exc
