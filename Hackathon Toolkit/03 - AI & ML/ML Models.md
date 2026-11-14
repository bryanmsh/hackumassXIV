# ML Models

## Practical model selection
- Classification: logistic regression / tree ensemble as baseline.
- Forecasting: naive last-value/seasonal baseline before complex model.
- Optimization: deterministic solver/rules before LLM.
- Language: LLM + retrieval for grounded explanation.

Split train/test before preprocessing; avoid leakage. Record metric, dataset, runtime and caveats. If data is sparse, a transparent rules-based MVP can be stronger than unvalidated ML. See [[Evaluation]].
