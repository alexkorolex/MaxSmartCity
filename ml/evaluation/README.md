# Evaluation

`TODO[ml-evaluation]`: реализовать единый CLI после фиксации Gold.

Планируемые отчёты:

- classification Macro F1 и per-class precision/recall;
- retrieval Recall@K;
- reranking MRR/NDCG, false merge/split;
- ECE, Brier и risk-coverage;
- stress throughput, p50/p95 и queue drain time.

Test Gold не используется для выбора модели или threshold.
