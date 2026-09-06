#!/usr/bin/env python3
"""Measure real Gemma 4 loss for one immutable live-learning dataset."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--maximum-sequence-length", type=int, required=True)
    parser.add_argument("--assistant-id", type=int, required=True)
    args = parser.parse_args()

    import mlx.core as mx
    from datasets import load_dataset
    from mlx_vlm.trainer.datasets import VisionDataset
    from mlx_vlm.trainer.sft_trainer import evaluate
    from mlx_vlm.trainer.utils import apply_lora_layers
    from mlx_vlm.utils import load

    model, processor = load(args.model, processor_config={"trust_remote_code": True})
    if args.adapter:
        adapter = args.adapter.resolve()
        load_path = adapter.parent if adapter.is_file() else adapter
        model = apply_lora_layers(model, str(load_path))
    raw = load_dataset(str(args.dataset.resolve()), split="train")
    dataset = VisionDataset(raw, model.config.__dict__, processor)
    loss = float(
        evaluate(
            model=model,
            dataset=dataset,
            batch_size=1,
            num_batches=-1,
            max_seq_length=args.maximum_sequence_length,
            train_on_completions=True,
            assistant_id=args.assistant_id,
        )
    )
    mx.eval(mx.array(loss))
    if not math.isfinite(loss):
        raise RuntimeError("non-finite evaluation loss")
    print("ERNOS_LIVE_LEARNING_LOSS=" + json.dumps({"loss": loss, "examples": len(dataset)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
