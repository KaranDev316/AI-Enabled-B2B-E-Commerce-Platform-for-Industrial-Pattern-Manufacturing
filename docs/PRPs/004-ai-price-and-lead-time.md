# PRP-004 — Advisory price and lead-time estimation

Version 1.0 · 2026-11-15 · Requirements specification

Read [CONTEXT.md](../CONTEXT.md) and [PRP.md](../PRP.md). This file owns REQ-11–REQ-13. All requirements are **Must**. Acceptance remains **NOT VERIFIED**.

## Goal and users

Admin can consult an explainable academic estimate while preparing an official quotation. The project can demonstrate how the model was trained and evaluated without presenting synthetic results as proven manufacturing accuracy.

## Requirements

### REQ-11 — Project provides a reproducible offline model and evaluation

- **Actor** — Project team preparing the demonstration.
- **Trigger** — Prepares or evaluates a model artifact outside the running API.
- **Success** — A fixed, clearly labeled synthetic dataset supports price and lead-time linear regression using material, dimensions, quantity, and complexity. A reproducible held-out evaluation reports MAE separately in INR and days. The saved artifact includes preprocessing and a training-time model-version string.
- **Failure** — Invalid data or an unsuccessful training/evaluation run cannot be presented as a validated artifact. Missing evidence is reported explicitly.
- **Constraints** — Fit preprocessing and estimators on training data only. Use `backend/ml/`, `data/demo/`, and `MODEL_PATH` as established. No minimum accuracy claim is invented. Training never runs through an API request.
- **Source** — CONTEXT §§4, 7–9 and the user's linear-regression/model-version decisions.

### REQ-12 — Admin can obtain and retain an advisory estimate

- **Actor** — Admin.
- **Trigger** — Requests an estimate for an RFQ using its structured manufacturing inputs.
- **Success** — Valid supported inputs yield a price and lead-time estimate. A saved estimate retains the inputs, predictions, model version from the loaded artifact, and creation time. The UI clearly labels the synthetic-data demonstration and advisory nature.
- **Failure** — Missing/invalid inputs produce field feedback. Unsupported inputs or unusable predictions produce an unavailable result instead of a fabricated value.
- **Constraints** — Load a trusted artifact once at startup. Model inputs are structured form values, not features extracted from CAD. No confidence percentage, chat, or product recommendation is added. Admin controls the final quote.
- **Source** — CONTEXT §§6–7, 10–11.

### REQ-13 — Manual quotation remains available when estimation is unavailable

- **Actor** — Admin.
- **Trigger** — The model is missing/corrupt, input is unsupported, prediction is unusable, or Admin chooses manual pricing.
- **Success** — Admin can complete an official price and lead time manually. A manual quote stores a null estimate reference and an explicit manual pricing source. AI-assisted entry references the saved estimate and records its source.
- **Failure** — Estimation failure does not silently become zero price/lead time, a fake estimate row, or a successful AI-assisted label.
- **Constraints** — Missing model functionality must not prevent the rest of the application from operating. Saved provenance remains attached to the quotation version even when a newer model is deployed.
- **Source** — CONTEXT §7 and user fix for estimation unavailability.

## Journeys

Admin opens an RFQ, requests an estimate, reviews the advisory values, and sets the official quotation. If the artifact cannot load, Admin sees that estimation is unavailable and completes the same quotation manually. An examiner can inspect the synthetic dataset, held-out metrics, and saved model version behind an estimate.

## Acceptance scenarios

| ID | Requirement | Expected observation |
| --- | --- | --- |
| AC-04-01 | REQ-11 | Fixed data, reproducible split, training-only preprocessing, and two held-out MAEs are evidenced |
| AC-04-02 | REQ-11 | Artifact contains preprocessing, estimators, and model-version metadata |
| AC-04-03 | REQ-12 | Saved inputs, predictions, and version match the model used for the estimate |
| AC-04-04 | REQ-12 | Invalid/unsupported inputs do not yield a fabricated successful estimate |
| AC-04-05 | REQ-12 | API startup loads the artifact; user requests never train it |
| AC-04-06 | REQ-13 | Missing/corrupt artifact permits manual quotation with null estimate reference |
| AC-04-07 | REQ-13 | Manual and AI-assisted quotations retain accurate, distinguishable provenance |

## Dependencies, risks, and exclusions

PRP-003 supplies RFQ inputs. PRP-005 owns official quotations. PRP-010 consumes saved pricing provenance where relevant. Synthetic data cannot establish real production accuracy. No external AI service, automatic price approval, model settings page, or model-training UI is required.

## UI references

The provided Quotation Review & Decision design illustrates advisory versus official price. Remove confidence percentages and retain a clear distinction between the estimate and Admin's official amount. An unavailable estimate must leave the official quotation understandable.
