# RAG

## Minimal retrieval-augmented generation
1. Collect licensed, attributable documents.
2. Chunk text with stable source IDs and offsets.
3. Embed chunks; index vectors.
4. Retrieve top-k chunks for a query.
5. Ask LLM to answer *only from retrieved chunks* with citations.
6. Evaluate unsupported claims and abstention.

For a tiny corpus, keyword retrieval may outperform a rushed vector DB. Don't put private user data into third-party embedding services without authorization. See [[Embeddings]] and [[Evaluation]].
