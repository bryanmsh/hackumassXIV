# Embeddings

Embeddings map text into vectors for semantic similarity. Compare with cosine similarity; normalize vectors or use a library that handles it.
```python
import numpy as np

def cosine(a,b):
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    den=np.linalg.norm(a)*np.linalg.norm(b)
    return float(a@b/den) if den else 0.0
```
Use embeddings for semantic search, deduplication, and matching; don't confuse similarity with correctness. Benchmark against simple keyword search. See [[RAG]].
