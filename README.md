# AI Governance Engineering Lab

For dashboard instructions, metrics, exports, setup and troubleshooting, see [the User Manual](USER_MANUAL.md).

## LangFair, UQLM and governance success metrics

The dashboard now includes LangFair toxic-fraction and UQLM exact-match consistency-confidence gates for RAG assets, labeled by execution source. Default mode uses clearly marked fixtures. Real mode calls `langfair.auto.AutoEval.evaluate` and `uqlm.BlackBoxUQ.generate_and_score`. Consistency is supporting evidence, not a correctness guarantee. The other controls remain fixtures even in real-tool mode.

To enable real tools, create a virtual environment, install `requirements-tools.txt` and your LangChain model provider, and define a Python `module:function` factory returning a configured LangChain chat model. Set `GOVERNANCE_LLM_FACTORY` to that factory and `GOVERNANCE_EVAL_DATASET` to a JSON file with a nonempty `prompts` array before starting the server. The dataset and model must correspond to the asset being evaluated. Real execution can download classifier models and make multiple paid provider calls; no such calls occur by default. Adapter/schema failures block evaluation rather than falling back to fixtures. Real integrations have not been executed in this workspace; validate and pin package versions in your environment.

Sources: [LangFair AutoEval](https://cvs-health.github.io/langfair/latest/notebooks/examples/evaluations/text_generation/auto_eval_demo.html), [UQLM BlackBoxUQ](https://github.com/cvs-health/uqlm).

All requested success measures appear in the dashboard with formulas, units, desired direction and sample denominators. Detection-to-resolution is one combined Mean time to detect/remediate metric. Metrics use the all-time exported event stream, not current asset state. No evidence means N/A; arrows indicate goals, not actual trends. Export JSON includes hash-chain links and CSV includes metric formulas. Recompute a downloaded audit export with `python recompute_metrics.py path/to/governance-audit.json`.

Use “Record operational evidence” to inventory teams (including nonadopters), record exceptions without bypassing controls, and record/resolve synthetic incidents. The ten metric definitions follow the requested scope exactly. Exception rate is a count of waivers/bypasses. Production risk includes a breakdown of PHI leakage, unsafe outputs, policy violations, fairness issues and agent incidents; blocked attempts are excluded. Mean time to detect/remediate measures detection to resolution, with unresolved counts displayed separately. First-pass rate uses each submission's first gate (registration/material change starts a submission). Manual review measures low-risk cases needing review, including those awaiting approval. Automated coverage excludes fixtures. Cycle time measures registration to first approval or deployment. Auditability counts currently deployed unique assets, using each asset's latest release; a later change or evaluation removes it from that cohort until redeployment. Metrics describe demo activity, not validated enterprise outcomes. A hash chain cannot prove export completeness or prevent privileged rewriting.

A runnable, dependency-free Python reference application modeling all 16 steps in the supplied AI governance workflow. This is an independent interview/architecture demo, not a CVS system or representation of its internal policies.

## Run on Windows

```powershell
python app.py
```

Open http://127.0.0.1:8000 in your browser. Python 3.10+ is required. Stop with Ctrl+C. Data persists in `governance.db` beside the application. The server binds only to your local computer. Use synthetic data only.

## Walkthrough

1. Register the prefilled member benefits assistant. Required fields are validated; PHI or autonomy routes to high risk.
2. Choose the privacy failure fixture and run evaluations. The CI gate blocks deployment and records the failure.
3. Choose the passing fixture and rerun. The asset moves to review required.
4. Simulate reviewer approval to deploy. This button represents a human workflow, without authenticated identity enforcement.
5. Run a normal runtime question, then a synthetic email/SSN, a disallowed tool, or an injection attempt. Observe allowed, escalated, denied and circuit-breaker decisions. `action_api` requires human approval for an autonomous asset; no action is executed.
6. Change the prompt. The approval becomes invalid, runtime is blocked, and new evaluations plus approval are required.
7. Inspect evidence JSON and trace details. Create another asset for a fresh circuit breaker; the demo intentionally has no reset shortcut.

## Framework coverage

| Steps | Implementation |
| --- | --- |
| 1–4 | SQLite inventory, required-field validation, deterministic risk routing, versioned `policy.json` thresholds and reviewer routing |
| 5 | `sdk.py` HTTP client for registration, evaluation and CI validation |
| 6–8 | Synthetic ML/F1/fairness, RAG/retrieval/language, privacy/injection/safety evaluator fixtures |
| 9 | Search allowlist; other tools denied or escalated; no external actions executed |
| 10 | Server-side CI gate blocks failures and requires current evaluations before approval |
| 11–12 | Limited SSN/email detection, injection blocking, approval-bound runtime, persistent circuit breaker |
| 13 | Trace IDs, model/prompt versions, tool, latency and decisions; raw prompts excluded |
| 14 | Prompt change invalidates deployment; baseline and policy version checked at runtime |
| 15 | Timestamped, hash-linked evidence in SQLite with verification endpoint |
| 16 | Dashboard, remediation states, API and SDK |

The evaluations are labeled fixtures, not measurements of a real model. Reviewer routing is displayed; multi-role signoff is an enterprise connection point. Evidence is tamper-evident locally, not immutable: a database administrator can rewrite the entire chain. Regex matching does not detect all PHI. No external LLM, healthcare system, identity provider or monitoring service is connected. See `CONNECTIONS.md` for pseudocode at every integration boundary.

## API

`GET /api/state` and `GET /api/evidence` return dashboard state and evidence. POST endpoints accept JSON:

```text
/api/register  {name, owner, purpose, model, data_source, population,
                kind: "rag"|"ml", phi: true|false, external: true|false,
                autonomous: true|false, human_escalation: true|false}
/api/evaluate  {id, scenario: "pass"|"privacy_failure"|"quality_failure"}
/api/approve   {id}
/api/change    {id}
/api/runtime   {id, prompt, tool}
```

`sdk.GovernanceClient().validate_policy(asset_id)` raises on a blocked gate, for use in CI scripts. It runs the synthetic fixture harness in this demo. Production CI must execute and verify actual evaluators before using any release decision.

## Validation

```powershell
python -m unittest -v
```

Tests isolate persistence in a temporary database and check blocked releases, approval ordering, material change invalidation, runtime controls, and audit tamper detection.
