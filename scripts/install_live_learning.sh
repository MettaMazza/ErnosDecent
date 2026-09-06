#!/bin/bash
# Install the private Apple-silicon live-learning runtime and the exact Gemma 4
# 26B A4B checkpoint. This never starts, stops, or changes the running node.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$REPO_ROOT"

RUNTIME="${HOME}/.ernosdecent/live-learning/runtime"
MODEL="${HOME}/.ernosdecent/live-learning/models/gemma4-26b-a4b-it-4bit"
UV_BIN=$(command -v uv || true)

if [ -z "$UV_BIN" ]; then
  echo "[live-learning] uv is required (https://docs.astral.sh/uv/)." >&2
  exit 1
fi

mkdir -p "$(dirname "$RUNTIME")" "$(dirname "$MODEL")"
if [ ! -x "$RUNTIME/bin/python" ]; then
  "$UV_BIN" venv --python 3.12 "$RUNTIME"
fi

"$UV_BIN" pip install --python "$RUNTIME/bin/python" \
  'mlx-lm==0.31.3' 'mlx-vlm==0.5.0' \
  'torch==2.8.0' 'torchvision==0.23.0'

"$RUNTIME/bin/python" scripts/patch_mlx_vlm_gemma4.py "$RUNTIME"

"$RUNTIME/bin/python" - "$MODEL" <<'PY'
import sys
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="mlx-community/gemma-4-26b-a4b-it-4bit",
    local_dir=sys.argv[1],
)
print(f"[live-learning] exact checkpoint ready at {sys.argv[1]}")
PY

"$RUNTIME/bin/python" - "$MODEL" <<'PY'
import sys
from pathlib import Path
from transformers import AutoProcessor

model = Path(sys.argv[1]).resolve()
required = [model / "config.json", model / "model.safetensors.index.json", *sorted(model.glob("model-*.safetensors"))]
if len(required) < 5 or any(not path.is_file() or path.stat().st_size == 0 for path in required):
    raise SystemExit("[live-learning] checkpoint verification failed")
processor = AutoProcessor.from_pretrained(str(model), trust_remote_code=True)
print(f"[live-learning] processor={type(processor).__name__}; runtime and checkpoint verified")
PY
