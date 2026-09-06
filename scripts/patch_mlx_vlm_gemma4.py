#!/usr/bin/env python3
"""Apply the forward-identical MoE routing gradient barrier to MLX-VLM 0.5.0.

MLX-VLM's Gemma 4 router currently leaves discrete argpartition indices on the
autodiff path. MLX correctly rejects a VJP for integer gather indices. The same
one-line stop-gradient remedy is already merged upstream for MLX-LM's Qwen3 MoE
(ml-explore/mlx-lm#1787). This patch is hash-pinned and refuses unknown bytes.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path


BEFORE_SHA256 = "73575838295d89c2fa637ebf4162a464b0b2222dcb68276b471adf5e46cf9a59"
AFTER_SHA256 = "3a11cabc074da8cabaa70665ff017ea35ba453293fea3924fda8c2a47906f738"
OLD = b"        top_k_indices = top_k_indices[..., -self.config.top_k_experts :]\n\n        top_k_weights = mx.take_along_axis(expert_scores, top_k_indices, axis=-1)"
NEW = b"        top_k_indices = top_k_indices[..., -self.config.top_k_experts :]\n        top_k_indices = mx.stop_gradient(top_k_indices)\n\n        top_k_weights = mx.take_along_axis(expert_scores, top_k_indices, axis=-1)"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_mlx_vlm_gemma4.py <venv>")
    runtime = Path(sys.argv[1]).expanduser().resolve()
    candidates = list(runtime.glob("lib/python*/site-packages/mlx_vlm/models/gemma4/language.py"))
    if len(candidates) != 1:
        raise SystemExit(f"expected one pinned MLX-VLM Gemma 4 source, found {len(candidates)}")
    path = candidates[0]
    before = path.read_bytes()
    before_hash = digest(before)
    if before_hash == AFTER_SHA256:
        print(f"[live-learning] Gemma 4 MoE gradient barrier already verified: {AFTER_SHA256}")
        return 0
    if before_hash != BEFORE_SHA256 or before.count(OLD) != 1:
        raise SystemExit(f"refusing unknown MLX-VLM source bytes: {before_hash}")
    after = before.replace(OLD, NEW)
    if digest(after) != AFTER_SHA256:
        raise SystemExit("patched MLX-VLM source did not match the pinned result")
    temp = path.with_name(f".{path.name}.tmp.{os.getpid()}.{time.time_ns()}")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(after)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()
    print(f"[live-learning] applied and verified Gemma 4 MoE gradient barrier: {AFTER_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
