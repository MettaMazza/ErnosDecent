#!/usr/bin/env python3
import os
import sys
import json
import shlex
import signal
import subprocess
import time

CONFIG_PATH = 'config/platforms.json'
BRIDGE_SCRIPT = 'decent_net/discord_bridge.py'
LOG_PATH = 'decent_net/discord_bridge.log'

def load_config():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Discord Manager] Error loading config: {e}", flush=True)
        return None
    return {}

def save_config(config):
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
        print("[Discord Manager] Config saved successfully.", flush=True)
    except Exception as e:
        print(f"[Discord Manager] Error saving config: {e}", flush=True)

def find_existing_bridge_pids():
    """Return only Python processes whose script argument is this bridge."""
    result = subprocess.run(
        ['ps', '-axo', 'pid=,command='], capture_output=True, text=True,
        check=False,
    )
    bridge_pids = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        pid_text, separator, command = line.partition(' ')
        if not separator or not pid_text.isdigit():
            continue
        try:
            args = shlex.split(command)
        except ValueError:
            continue
        if len(args) < 2:
            continue
        executable = os.path.basename(args[0]).lower()
        if executable not in ('python', 'python3'):
            continue
        script_args = [arg for arg in args[1:] if not arg.startswith('-')]
        if not script_args:
            continue
        script = script_args[0]
        if script != BRIDGE_SCRIPT and os.path.abspath(script) != os.path.abspath(BRIDGE_SCRIPT):
            continue
        pid = int(pid_text)
        if pid != os.getpid():
            bridge_pids.append(pid)
    return bridge_pids


def kill_existing_bridge():
    print("[Discord Manager] Terminating any existing Discord bridge process...", flush=True)
    # Do not use `pkill -f BRIDGE_SCRIPT`: it also matches an unrelated shell,
    # health probe, or editor command whose argument text happens to mention the
    # filename.
    try:
        bridge_pids = find_existing_bridge_pids()

        for pid in bridge_pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 2.0
        while bridge_pids and time.monotonic() < deadline:
            remaining = []
            for pid in bridge_pids:
                try:
                    os.kill(pid, 0)
                    remaining.append(pid)
                except ProcessLookupError:
                    pass
            bridge_pids = remaining
            if bridge_pids:
                time.sleep(0.05)
        for pid in bridge_pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        return True
    except Exception as e:
        print(f"[Discord Manager] Error stopping bridge: {e}", flush=True)
        return False

def wait_for_bridge_ready(process, timeout_seconds=15.0):
    """Require both a live child and the bridge's durable ONLINE acknowledgement."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        config = load_config()
        if config is not None:
            status = config.get('discord', {}).get('status', 'OFFLINE')
            if status == 'ONLINE':
                return True
        time.sleep(0.05)
    return False


def _parse_ipc_port(argv):
    args = list(argv or [])
    if '--ipc-port' not in args:
        return ''
    index = args.index('--ipc-port')
    if index + 1 >= len(args):
        return ''
    value = args[index + 1].strip()
    return value if value.isdigit() else ''


def main(argv=None):
    config = load_config()
    if config is None:
        return 1
    discord_cfg = config.get('discord', {})
    enabled = discord_cfg.get('enabled', False)
    token = discord_cfg.get('token', '')
    channel = discord_cfg.get('channel', '')

    # Ensure status field exists
    if 'status' not in discord_cfg:
        discord_cfg['status'] = 'OFFLINE'

    if enabled and token and channel:
        preserve = os.environ.get('ERNOS_PRESERVE_DISCORD_BRIDGE') == '1'
        existing_pids = find_existing_bridge_pids() if preserve else []
        if len(existing_pids) == 1:
            # A factory reset restarts only the node. The existing bridge owns the
            # retained reset workflow and must survive long enough to observe the
            # replacement node and deliver the completion acknowledgement.
            print(
                f"[Discord Manager] Preserving live bridge PID {existing_pids[0]} "
                "across controlled node restart.",
                flush=True,
            )
            return 0

        print("[Discord Manager] Discord bot is ENABLED. Starting bridge...", flush=True)
        # Initial/manual launches replace stale configuration. A preserve request with
        # zero or multiple bridges repairs the state by launching exactly one.
        discord_cfg['status'] = 'OFFLINE'
        save_config(config)
        if not kill_existing_bridge():
            return 1
        
        # Start bridge in a new session so it detaches from the current process
        try:
            child_env = os.environ.copy()
            ipc_port = _parse_ipc_port(argv)
            if ipc_port:
                child_env['ERNOS_IPC_PORT'] = ipc_port
            with open(LOG_PATH, 'a') as log_file:
                log_file.write(f"\n--- Starting Discord Bridge at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                log_file.flush()
                # Popen duplicates the descriptor for the child; the manager closes
                # its copy immediately after spawn instead of leaking it until exit.
                process = subprocess.Popen(
                    ['python3', BRIDGE_SCRIPT],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=child_env,
                )
            if not wait_for_bridge_ready(process):
                print("[Discord Manager] Bridge failed to acknowledge ONLINE readiness.", flush=True)
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
                discord_cfg['status'] = 'OFFLINE'
                save_config(config)
                return 1
            print("[Discord Manager] Discord bridge launched and acknowledged ONLINE.", flush=True)
            return 0
        except Exception as e:
            print(f"[Discord Manager] Failed to start Discord bridge: {e}", flush=True)
            discord_cfg['status'] = 'OFFLINE'
            save_config(config)
            return 1
    else:
        print("[Discord Manager] Discord bot is DISABLED (or config is incomplete). Stopping bridge...", flush=True)
        kill_existing_bridge()
        
        # Explicitly set status to OFFLINE if disabled or configuration is incomplete
        if discord_cfg.get('status') != 'OFFLINE':
            discord_cfg['status'] = 'OFFLINE'
            save_config(config)
        return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
