# Healthcare & Biotech

Official illustrative themes: wearable data, health coverage, access and coordination, biotechnology innovation, clinical research. Source: https://hackachusetts2026.vercel.app/

## Candidate MVP: clinic appointment transit-access optimizer
Input: synthetic appointments, public GTFS schedules, clinic location, travel constraints. Output: reachable slots and a suggested reschedule. Baseline: reachable appointments before vs after. Tech: [[FastAPI]], [[React + TypeScript]], deterministic routing; optionally [[LLM APIs]] for source-grounded explanations.

## Other ideas
- Trial matching using public ClinicalTrials.gov data (informational, not eligibility determination).
- Coverage navigator linking to official program pages (not legal/medical advice).

## Data
- https://clinicaltrials.gov/data-api/api
- https://www.transit.land/ (check terms/access)
- https://www.mass.gov/ (official public services)

## Risk
Do not collect PHI; use synthetic patient profiles. Never claim clinical accuracy or give diagnoses.

See [[Datasets & APIs]], [[Idea Scoring Matrix]], [[MVP Scope]].
