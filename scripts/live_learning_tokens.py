#!/usr/bin/env python3
"""Count a Gemma 4 MLX-VLM chat prompt with the provider's exact processor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(args.model.resolve()), trust_remote_code=True, use_fast=True)
    messages = json.loads(args.input.read_text(encoding="utf-8"))
    rendered = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
    if isinstance(rendered, dict):
        rendered = rendered["input_ids"]
    if hasattr(rendered, "shape"):
        count = int(rendered.shape[-1])
    else:
        count = len(rendered)
    print(f"ERNOS_MLX_PROMPT_TOKENS={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
