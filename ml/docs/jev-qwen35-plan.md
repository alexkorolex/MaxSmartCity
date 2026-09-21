# Jev-like report-to-incident model on RTX 3060

## Decision

Use Bionic/LM Studio for local serving and smoke tests, not for training. Train a LoRA adapter with
Unsloth/Transformers, merge it, export to GGUF and then load the resulting model in LM Studio or a
compatible runtime.

The preferred experiment is `Qwen/Qwen3.5-4B`: Apache-2.0, multilingual and small enough for a
12 GB RTX 3060 when using bf16 LoRA. Published Unsloth guidance estimates about 10 GB VRAM for the
4B bf16 LoRA configuration. That leaves little headroom, so begin with sequence length 512–1024,
batch size 1, gradient accumulation and gradient checkpointing. Full fine-tuning is out of scope;
4-bit QLoRA is not the default because the Qwen3.5-specific guidance warns against it.

If 4B is unstable or too slow on the actual machine, the fallback is Qwen3.5-2B with the same data
and evaluation protocol. Windows users should prefer WSL2/Linux for the training environment.

## Training curriculum

1. Optional NLI warm-up: a small, stratified RuWANLI subset. It provides Russian entailment,
   contradiction and neutral examples, but it is auxiliary language-task data rather than city data.
2. Domain training: `ml/data/matching/dev-v1/pairs.jsonl`, rendered as report premise + incident
   hypothesis. `MATCH` maps to entailment; hard negatives become contradiction or neutral according
   to their reason.
3. Domain review set: 50–100 manually checked multi-report scenarios with positive, same-house wrong
   category, same-category wrong house, stale incident and new-incident cases.
4. Frozen holdout: time-based or incident-disjoint, because the synthetic smoke corpus is shared
   across query splits and cannot prove generalization to unseen incidents.
5. Calibration: choose merge/abstain thresholds on validation only. Keep the frozen test untouched.

Russian SuperGLUE RCB/TERRa may be used as a second auxiliary benchmark, but neither it nor RuWANLI
should be mixed into the domain test set.

## Metrics and acceptance gates

- Retrieval: Recall@K and MRR; prioritize Recall@10 because a missed candidate cannot be recovered by
  the reranker.
- Reranking: pairwise ROC-AUC/PR-AUC and MRR/NDCG on queries with a known incident.
- Decision: false-merge rate, false-split rate, `NEW_INCIDENT` recall and selective accuracy after
  abstention.
- Operational: p50/p95 latency and peak VRAM on the 3060.

The first comparison must include the structured rule baseline and a lightweight encoder
cross-encoder. A 4B generative NLI model is accepted only if it materially improves false-merge and
false-split behavior at tolerable latency; architecture size alone is not a quality argument.

## Responsibilities and TODOs

- ML owns synthetic pairs, NLI rendering, training, evaluation, calibration and artifact manifest.
- Backend owns the active candidate snapshot/query, stable IDs, persistence and async transport.
- Ingestion owns canonical addresses and any external-event snapshot.
- TODO on the RTX 3060 host: verify the exact VRAM size and installed CUDA driver first, then pin a
  compatible PyTorch/Unsloth environment. Add the GPU training script only after that smoke test;
  CUDA-specific dependencies are deliberately not mixed into the CPU application lockfile.
- No model weights belong in Git. Download the selected Qwen checkpoint and optional RuWANLI cache
  on the GPU host; keep both in the Hugging Face cache or another local data volume.
