# AI Governance Engineering Lab — User Manual

Version: October 24, 2026

## 1. Purpose and audience

This application demonstrates an AI governance workflow from registration through testing, approval, simulated deployment, runtime controls, and reassessment. Developers can practice submitting an AI asset, reviewers can inspect release evidence, and governance teams can explore audit-derived success metrics.

This is a local engineering demonstration using synthetic data. It is independent of CVS enterprise systems and policies. “Deployment” changes the asset's local workflow state; it does not deploy a model to infrastructure. Approval uses a demo reviewer identity rather than authenticated role-based signoff.

## 2. Start and stop the application

Prerequisite: Python 3.10 or later. Default demo mode requires no additional packages, model credentials, or external services.

Open PowerShell and run:

```powershell
Set-Location 'C:\Users\lilyq\Documents\ChatGPT\AI Review Governance'
python app.py
```

Open [the dashboard](http://127.0.0.1:8000/). Keep the terminal running. To stop the server, press Ctrl+C in that terminal. To restart it, run `python app.py` again.

If the application is already running, open the dashboard without starting another copy. Refresh the browser after application updates. Asset and audit records persist in `governance.db` in the project folder; closing the browser does not clear them.

## 3. Dashboard orientation

| Area | What you do |
| --- | --- |
| Governance success metrics | Read definitions, expand calculation and scope, inspect denominators, and export results |
| Record operational evidence | Record team adoption, exceptions, and incident detection/resolution |
| 1. Register an AI asset | Enter use-case metadata and risk signals |
| Workflow coverage | See the 16 governance steps represented by the framework |
| 2. Select asset | Choose the asset used by testing, approval, runtime, and operational actions |
| 3. Evaluate → gate → approve | Select testing mode/scenario, run checks, approve passing evidence, or change the prompt |
| 4. Runtime guardrails | Try synthetic requests and tool authorization decisions |
| 5. Evidence & observability | Expand timestamped audit events and inspect trace details |

Metrics cover the entire recorded history across assets. The selected asset controls the workflow panels and asset-specific operational records, not the metric reporting window. There is no date-range filter. Team adoption is organization-wide.

## 4. Quick-start walkthrough

1. Leave the registration example populated and click **Register asset**. Note the asset ID, risk classification, and reviewer routing.
2. Keep **Simulated tool fixtures** selected. Choose **Privacy failure → blocked release**, then click **Run CI/CD evaluations**. The asset becomes `blocked`; approval is unavailable.
3. Select **Passing synthetic fixture** and rerun. The asset becomes `review_required`.
4. Click **Simulate human approval & deployment**. The asset becomes `deployed`; approval and deployment events are recorded.
5. In runtime guardrails, use the normal benefits question with the `search` tool. Click **Run guarded request**. Expect `allowed` with a synthetic answer.
6. Try `claims_write`. Expect `denied_tool`. No claims system is contacted.
7. Click **Change prompt → reassess**. The prompt version advances and the deployment becomes invalid. Rerun evaluations and approve again to restore the deployed workflow state.
8. Inspect the evidence panel and download the audit JSON and metrics CSV.

The initial failed submission remains a first-pass failure even after successful remediation. Changing the prompt begins a new submission cycle.

## 5. Register an asset

Required fields are asset name, owner, purpose, model, data source, and population. Blank required fields prevent registration. Use descriptive synthetic values so exported evidence is understandable.

| Field or option | Meaning |
| --- | --- |
| System type: GenAI / RAG | Adds groundedness, retrieval, language-quality, LangFair, and UQLM checks |
| System type: Traditional ML | Adds F1 and subgroup fairness-gap fixture checks |
| Potential PHI | Indicates a use case that could handle protected health information; do not enter actual PHI |
| Member-facing | Indicates external users |
| Agent tools enabled | Indicates autonomous capabilities and adds tool-scope/approval-gate checks |
| Human escalation available | Represents an escalation control; unchecking it causes that fixture control to fail |

Risk routing is deterministic: potential PHI **or** agent autonomy produces high risk; otherwise member-facing assets are medium risk; remaining assets are low risk. Reviewer labels come from `policy.json`. The application displays routing but does not contact reviewers or enforce multiple reviewer identities.

## 6. Test and approve an asset

### Demo testing mode

Use **Simulated tool fixtures** for the fully local walkthrough. Scores are predetermined examples, not measurements of an actual model. The source column identifies fixtures explicitly.

| Scenario | Expected result |
| --- | --- |
| Passing synthetic fixture | All fixture checks pass if human escalation is enabled |
| Privacy failure | Privacy score fails and blocks approval |
| Quality failure | Groundedness fails for RAG; F1 fails for ML |

The gate requires every returned control to pass. Most controls use minimum thresholds; fairness gap and LangFair toxic fraction use maximum thresholds. The comparison symbol appears beside each threshold.

### LangFair and UQLM

For RAG assets, the framework includes two additional gates:

| Tool | Implemented gate | Illustrative threshold |
| --- | --- | --- |
| LangFair | Toxic fraction | At most 0.05 |
| UQLM | Mean exact-match consistency confidence across generated responses | At least 0.80 |

The LangFair gate does not establish comprehensive fairness. UQLM consistency supports uncertainty assessment; consistent answers can still be incorrect. Thresholds are demo choices, not validated healthcare acceptance criteria.

In real-library mode these adapters invoke installed libraries and a configured model. Other existing controls remain fixtures. Real-mode setup is described in section 12; it is not required for normal demo use.

### Approval and workflow states

| State | Meaning and next action |
| --- | --- |
| `registered` | Intake is complete; run evaluations |
| `blocked` | One or more checks failed; inspect failed rows and rerun after remediation or select another demo scenario |
| `review_required` | The latest gate passed; simulate reviewer approval |
| `deployed` | Approval and local deployment recorded; runtime controls are available |
| `reassessment_required` | Prompt change invalidated deployment; evaluate and approve again |

Approval requires current passing results with the same policy version and asset baseline. If the policy changes, reevaluate before approval. Running evaluations again on a deployed asset moves it back through the gate and approval workflow.

## 7. Exercise runtime guardrails

Runtime requires an approved, currently deployed asset whose policy and baseline still match. Every completed runtime call creates a trace with a trace ID, decision, model/prompt versions, requested tool, and latency. Raw prompts are excluded from runtime telemetry.

| Test | Expected decision |
| --- | --- |
| Normal synthetic question using `search` | `allowed` |
| Synthetic email such as `demo@example.com`, using `search` | `redacted_escalated` |
| Synthetic SSN-shaped input such as `000-00-0000`, using `search` | `redacted_escalated` |
| `ignore previous instructions`, using `search` | `blocked_injection`; opens the circuit breaker |
| `member_db` or `claims_write` tool | `denied_tool` |
| `action_api` with agent tools enabled | `human_approval_required` |
| `action_api` without agent tools enabled | `denied_tool` |
| Any request after the circuit breaker opens | `circuit_open` |

Run these examples independently: the circuit breaker takes priority once open, and injection/tool decisions can take priority over privacy detection. Search is the only allowed tool. Requests never execute external tools, send approval requests, or change enterprise data.

The circuit breaker persists for that asset and has no reset button. Register a new synthetic asset for a fresh runtime demonstration. Reevaluation and approval do not reset an open breaker. Privacy detection is limited to email and SSN patterns and is not an enterprise DLP system.

## 8. Record operational evidence

Expand **Record operational evidence** above the asset workflow. These records provide inputs that cannot be inferred from test results alone.

### Team adoption

Enter a team name, check whether the team uses **both** the standard SDK and pipeline, and click **Record team status**. Register nonadopting teams too; otherwise the adoption denominator is incomplete. Use consistent names: each distinct name represents a team. A team's most recent declaration replaces its previous status for metric calculation while retaining the audit history.

### Exceptions

Select an asset, enter a reason, and click **Record exception for selected asset**. Each record increases the waiver/bypass count. Recording an exception does not authorize a bypass, change test results, or unlock deployment.

### Incident detection and resolution

1. Select a deployed asset.
2. Choose `phi_leakage`, `unsafe_output`, `policy_violation`, `fairness_issue`, or `agent_incident`.
3. Enter the occurrence time as an ISO 8601 timestamp with a timezone, for example `2026-10-24T10:00:00-05:00`. It must not be in the future.
4. Click **Detect incident**. The server records the detection timestamp and assigns an incident ID.
5. Select the incident in **Unresolved incidents** and click **Resolve incident** when the synthetic issue is resolved.

An incident can be resolved only once. The production-risk count includes resolved incidents because it counts incidents over the full history. Resolution contributes a duration to the detection-to-resolution metric. Runtime blocks do not automatically create confirmed incident records. Resolving an incident does not reset the circuit breaker.

## 9. Metric definitions and scope

Arrows indicate desired direction, not a measured trend. `N/A` means no eligible evidence; it is different from zero. Percentages show their denominator, duration metrics use seconds, and counts cover all recorded history. Expand **Calculation & scope** on any card for the implemented formula.

| Metric | Definition and direction | Implemented reporting scope |
| --- | --- | --- |
| Governance cycle time | Time from registration to approval/deployment ↓ | Mean registration-to-first-approval-or-deployment duration for completed assets; pending assets excluded |
| First-pass success rate | % of submissions passing without repeated remediation ↑ | First gate passes divided by evaluated submissions; registration or material change starts a submission |
| Automated control coverage | % of required RAI controls/tests executed automatically in CI/CD ↑ | Required control instances marked `ci_automated` divided by required control instances across CI runs; all fixtures excluded |
| Manual review rate | % of cases needing human review ↓ for routine/low-risk cases | Low-risk evaluated submissions requiring human review divided by low-risk evaluated submissions; awaiting approval counts as needing review |
| Developer adoption | % of AI teams using the standard SDK/pipeline ↑ | Latest team declarations using both SDK and pipeline divided by all inventoried teams |
| Policy compliance | % of releases meeting required controls before production ↑ | Demo release events with prior passing CI evidence matching release policy and baseline divided by all demo release events |
| Exception rate | Number of waivers/bypasses ↓ | Count of exception records, without a release-rate denominator |
| Production risk | PHI leakage, unsafe outputs, policy violations, fairness issues, agent incidents ↓ | Confirmed synthetic incident count, with category breakdown; blocked attempts excluded |
| Mean time to detect/remediate | Time from RAI issue detection to resolution ↓ | Mean detection-to-resolution duration for resolved issues; unresolved count shown separately |
| Auditability | % of deployed AI assets with complete evidence, versioning, approvals, and traceability ↑ | Unique currently deployed assets whose latest release has complete linked evidence divided by unique currently deployed assets |

For auditability, a later material change or evaluation removes an asset from the deployed cohort until redeployment. Repeated releases of one asset do not inflate the asset denominator. Compliance remains release-based and includes historical releases.

The current demo requires human approval after a passing gate, even for low-risk assets; it does not implement automatic low-risk approval. Therefore the manual review metric can remain high. Automated coverage is zero in fixture-only mode even though the demo harness itself runs automatically: it does not count simulated checks as executed model evaluations.

If the audit hash chain fails verification, metric cards are suppressed. Local demo metrics are not proof of real-world model safety, regulatory compliance, enterprise adoption, or production incident absence.

## 10. Export and inspect audit evidence

Click **Export audit trail JSON** to download the currently loaded dashboard snapshot, including events, hash links, asset state, policy, and metrics. Click **Export metrics CSV** to download metric names, definitions, values, units, desired direction, formulas, and denominators. Refresh the page before export when another tab or client has changed data.

In **Evidence & observability**, expand an event to see its details. **Open evidence JSON** opens the full API response. Dashboard events are filtered to the selected asset; the audit download includes all assets and organization-level records. Keep that broader scope in mind when sharing an export.

To verify the exported event chain and independently recompute metrics, run:

```powershell
python recompute_metrics.py 'C:\path\to\governance-audit.json'
```

The script prints the recalculated metrics or reports a verification failure. A hash chain detects some alterations but does not provide immutable storage or prove that an export contains every source event. A privileged database operator can rewrite the chain.

## 11. Developer SDK and API

The Python client in `sdk.py` provides `register`, `evaluate`, `validate_policy`, and generic `call` methods. `validate_policy` reruns the passing fixture scenario and raises when the resulting gate is blocked; it does not approve or deploy an asset and is not a production CI attestation mechanism.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/state` | Full dashboard state and metrics |
| `GET /api/evidence` | Full evidence/state snapshot |
| `GET /api/metrics` | Currently returns the same full snapshot, including the metrics array |
| `POST /api/register` | Register asset metadata |
| `POST /api/evaluate` | Evaluate asset ID with `scenario` and optional `tool_mode` (`fixture` or `real`) |
| `POST /api/approve` | Record demo approval and deployment |
| `POST /api/change` | Advance prompt version and invalidate deployment |
| `POST /api/runtime` | Evaluate a synthetic prompt and requested tool |
| `POST /api/operations` | Record team adoption, exception, incident detection, or resolution |

See `README.md` for request examples and `CONNECTIONS.md` for pseudocode covering enterprise identity, policy services, CI provenance, monitoring, and immutable evidence storage.

## 12. Optional real-library setup — operator task

Real LangFair/UQLM execution has not been validated against installed libraries in this workspace. Default fixture mode remains the verified local demonstration.

1. Use a standard Python installation to create a dedicated virtual environment.
2. Install `requirements-tools.txt` and the LangChain provider needed for your model. Validate and pin compatible versions in your environment.
3. Create an importable Python module containing a no-argument factory that returns a configured LangChain chat model. Supply provider credentials through your approved environment/secret mechanism.
4. Create a UTF-8 JSON dataset containing a nonempty `prompts` array of strings. The model and dataset must match the asset under evaluation; the application does not enforce that association.
5. In the same PowerShell session used to start the server, set the configuration:

```powershell
$env:GOVERNANCE_LLM_FACTORY = 'my_model_factory:create_model'
$env:GOVERNANCE_EVAL_DATASET = 'C:\path\to\synthetic-prompts.json'
python app.py
```

6. Register/select a RAG asset, select **Real libraries**, and run evaluations. ML assets do not invoke these RAG adapters.

Real mode may download classifier models and make multiple paid model calls. LangFair calls `AutoEval.evaluate`; UQLM calls `BlackBoxUQ.generate_and_score` with five responses and the `exact_match` scorer. Library versions are attached to returned tool control rows. Missing configuration or incompatible result schemas fail evaluation without substituting fixture results. Other test controls still use fixtures.

The fixture scenario selector still applies to the existing synthetic controls in real mode. Real-tool thresholds currently reside in `app.py`; other thresholds and reviewer routing reside in `policy.json`. Changes to real-tool thresholds need normal engineering versioning and reassessment; they are not automatically represented by the policy JSON version.

## 13. Troubleshooting

| Symptom | Action |
| --- | --- |
| Dashboard will not open | Start `python app.py`; check the terminal; use `http://127.0.0.1:8000/` on the same computer |
| Port 8000 is already in use | Open the existing server, or stop its terminal with Ctrl+C before restarting |
| Old definitions or metrics remain visible | Refresh the page; confirm the updated server was restarted after Python changes |
| Approval button is disabled | Select an asset and run evaluations; all required controls must pass |
| Passing scenario still fails | Enable human escalation for a new registration or inspect the failed control; real-tool results can fail independently of fixtures |
| Runtime is unavailable | Complete current evaluation and approval; changes or policy mismatches require reevaluation |
| Every runtime call says `circuit_open` | Register a new synthetic asset; there is no circuit reset shortcut |
| Metric says `N/A` | Add eligible evidence: a completed approval/deployment, evaluated low-risk submission, team inventory, or resolved incident, depending on the metric |
| Adoption looks too high | Inventory nonadopting teams as well as adopting teams |
| Automated coverage is zero | Fixtures are excluded; only actual adapter results marked `ci_automated` count |
| Incident detection is rejected | Select a deployed asset and use a past ISO timestamp with a timezone |
| No unresolved incident appears | Select the incident's asset; resolved incidents are removed from this selector |
| Real tools fail or appear slow | Check operator configuration, compatible packages, provider access, terminal errors, and model/classifier execution time |
| Audit verification fails | Preserve the export/database for investigation; do not treat suppressed metrics as valid evidence |

## 14. Data handling and maintenance

Use synthetic information in every field, including owner names, registration descriptions, exception reasons, and prompts. Registration metadata and exception reasons are retained in records; runtime prompt exclusion is not a universal data-redaction guarantee.

There are no user accounts, deletion screens, production permissions, or authenticated reviewer controls. Keep the server local. Before backing up the application data, stop the server and copy `governance.db` to your approved backup location. Preserve the code and policy version with the backup. No database deletion is required for normal use.

For a code health check, run `python -m unittest -v` from the project directory. Automated tests use temporary databases and do not clear your working audit history.
