#!/usr/bin/env python3
import os
import sys
import json
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
    return {}

def save_config(config):
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f)
        print("[Discord Manager] Config saved successfully.", flush=True)
    except Exception as e:
        print(f"[Discord Manager] Error saving config: {e}", flush=True)

def kill_existing_bridge():
    print("[Discord Manager] Terminating any existing Discord bridge process...", flush=True)
    # Using pkill with full path match to target only the bridge script
    try:
        subprocess.run(['pkill', '-f', BRIDGE_SCRIPT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Give a small window for the process to terminate and clean up
        time.sleep(0.5)
    except Exception as e:
        print(f"[Discord Manager] Error running pkill: {e}", flush=True)

def main():
    config = load_config()
    discord_cfg = config.get('discord', {})
    enabled = discord_cfg.get('enabled', False)
    token = discord_cfg.get('token', '')
    channel = discord_cfg.get('channel', '')

    # Ensure status field exists
    if 'status' not in discord_cfg:
        discord_cfg['status'] = 'OFFLINE'

    if enabled and token and channel:
        print("[Discord Manager] Discord bot is ENABLED. Starting bridge...", flush=True)
        # Always terminate first to apply updated token/channel configurations
        kill_existing_bridge()
        
        # Start bridge in a new session so it detaches from the current process
        try:
            log_file = open(LOG_PATH, 'a')
            log_file.write(f"\n--- Starting Discord Bridge at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            log_file.flush()
            
            # Start the bridge process
            subprocess.Popen(
                ['python3', BRIDGE_SCRIPT],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
            print("[Discord Manager] Discord bridge launched successfully in the background.", flush=True)
        except Exception as e:
            print(f"[Discord Manager] Failed to start Discord bridge: {e}", flush=True)
            discord_cfg['status'] = 'OFFLINE'
            save_config(config)
    else:
        print("[Discord Manager] Discord bot is DISABLED (or config is incomplete). Stopping bridge...", flush=True)
        kill_existing_bridge()
        
        # Explicitly set status to OFFLINE if disabled or configuration is incomplete
        if discord_cfg.get('status') != 'OFFLINE':
            discord_cfg['status'] = 'OFFLINE'
            save_config(config)

if __name__ == '__main__':
    main()
