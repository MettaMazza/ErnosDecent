#!/usr/bin/env python3
"""Run real text and image inference against one candidate MLX-VLM adapter."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def post_json(url: str, payload: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
    value = json.loads(body)
    if not isinstance(value, dict):
        raise RuntimeError("candidate server returned a non-object response")
    return value


def response_text(value: dict) -> str:
    choices = value.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content", "") if isinstance(message, dict) else ""
    return content if isinstance(content, str) else ""


def wait_ready(port: int, process: subprocess.Popen | None, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = "no HTTP response"
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"candidate server exited before readiness with {process.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.5)
    raise RuntimeError(f"candidate server did not become ready; last probe: {last_error}")


def create_probe_image(path: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (256, 128), "red")
    draw = ImageDraw.Draw(image)
    draw.rectangle((128, 0, 255, 127), fill="blue")
    image.save(path, format="PNG")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--port", type=int, default=11437)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--startup-timeout", type=float, default=300)
    parser.add_argument("--existing-server", action="store_true")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.server_log.parent.mkdir(parents=True, exist_ok=True)
    adapter_weights = args.adapter.resolve()
    adapter_load_path = adapter_weights.parent if adapter_weights.is_file() else adapter_weights
    adapter_config = adapter_load_path / "adapter_config.json"
    if not adapter_weights.is_file() or not adapter_config.is_file():
        raise RuntimeError("candidate adapter package is incomplete")
    image_path = args.output.parent / "multimodal-probe.png"
    create_probe_image(image_path)
    command = [
        sys.executable,
        "-m",
        "mlx_vlm.server",
        "--host",
        "127.0.0.1",
        "--port",
        str(args.port),
        "--model",
        args.model,
        "--adapter-path",
        str(adapter_load_path),
        "--max-kv-size",
        "8192",
    ]
    started = time.time()
    with args.server_log.open("ab" if args.existing_server else "wb") as server_log:
        process = None
        if not args.existing_server:
            process = subprocess.Popen(
                command,
                stdout=server_log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        try:
            wait_ready(args.port, process, args.startup_timeout)
            endpoint = f"http://127.0.0.1:{args.port}/v1/chat/completions"
            common = {"model": args.model, "stream": False, "temperature": 0, "max_tokens": 80}
            text_value = post_json(
                endpoint,
                {
                    **common,
                    "messages": [
                        {
                            "role": "user",
                            "content": "Return exactly the text LEARNING_PROBE_OK and nothing else.",
                        }
                    ],
                },
                timeout=300,
            )
            text = response_text(text_value).strip()
            image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
            image_value = post_json(
                endpoint,
                {
                    **common,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Name both colours visible in this image. Be concise."},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": "data:image/png;base64," + image_data},
                                },
                            ],
                        }
                    ],
                },
                timeout=300,
            )
            image_text = response_text(image_value).strip()
            lower_image = image_text.lower()
            text_passed = text == "LEARNING_PROBE_OK"
            image_passed = "red" in lower_image and "blue" in lower_image
            receipt = {
                "schema": "ernosdecent-live-learning-probe-v1",
                "model": args.model,
                "adapter_path": str(adapter_weights),
                "adapter_load_path": str(adapter_load_path),
                "adapter_hash": hashlib.sha256(adapter_weights.read_bytes()).hexdigest(),
                "adapter_config_hash": hashlib.sha256(adapter_config.read_bytes()).hexdigest(),
                "server_command": command,
                "started_at": int(started),
                "completed_at": int(time.time()),
                "text_response": text,
                "text_response_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "text_passed": text_passed,
                "image_response": image_text,
                "image_response_hash": hashlib.sha256(image_text.encode("utf-8")).hexdigest(),
                "image_passed": image_passed,
                "passed": bool(text_passed and image_passed),
            }
            args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print("ERNOS_LIVE_LEARNING_PROBE=" + json.dumps(receipt, ensure_ascii=False, separators=(",", ":")))
            return 0 if receipt["passed"] else 2
        finally:
            if process is not None and process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=15)


if __name__ == "__main__":
    raise SystemExit(main())
