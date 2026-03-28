#!/usr/bin/env python3
"""Resolve environment variables into nanobot config and launch gateway."""

import json
import os
import sys
from pathlib import Path

def main():
    # Paths
    nanobot_dir = Path(__file__).parent.resolve()
    config_path = nanobot_dir / "config.json"
    resolved_path = nanobot_dir / "config.resolved.json"
    workspace_dir = nanobot_dir.parent  # /workspace
    venv_dir = workspace_dir / ".venv"
    venv_bin = venv_dir / "bin"
    
    # Load base config
    with open(config_path) as f:
        config = json.load(f)
    
    # Resolve LLM provider from env vars (docker-compose.yml uses LLM_API_KEY, LLM_API_BASE_URL)
    if "LLM_API_KEY" in os.environ:
        config["providers"]["custom"]["apiKey"] = os.environ["LLM_API_KEY"]
    
    if "LLM_API_BASE_URL" in os.environ:
        config["providers"]["custom"]["apiBase"] = os.environ["LLM_API_BASE_URL"]
    
    if "LLM_API_MODEL" in os.environ:
        config["agents"]["defaults"]["model"] = os.environ["LLM_API_MODEL"]
    
    # Resolve gateway host/port
    if "NANOBOT_GATEWAY_CONTAINER_ADDRESS" in os.environ:
        config.setdefault("gateway", {})["host"] = os.environ["NANOBOT_GATEWAY_CONTAINER_ADDRESS"]
    if "NANOBOT_GATEWAY_CONTAINER_PORT" in os.environ:
        config.setdefault("gateway", {})["port"] = int(os.environ["NANOBOT_GATEWAY_CONTAINER_PORT"])
    
    # Resolve webchat port
    if "NANOBOT_WEBCHAT_CONTAINER_PORT" in os.environ:
        config.setdefault("gateway", {})["webchat_port"] = int(os.environ["NANOBOT_WEBCHAT_CONTAINER_PORT"])
    
    # Resolve MCP server env vars
    if "mcpServers" in config.get("tools", {}):
        for server_name, server_config in config["tools"]["mcpServers"].items():
            if "env" in server_config:
                for env_key in list(server_config["env"].keys()):
                    # Map NANOBOT_LMS_BACKEND_URL -> NANOBOT_MCP_LMS_NANOBOT_LMS_BACKEND_URL
                    env_var_name = f"NANOBOT_{env_key}"
                    if env_var_name in os.environ:
                        server_config["env"][env_key] = os.environ[env_var_name]
    
    # Write resolved config
    with open(resolved_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"[entrypoint] Resolved config written to {resolved_path}", file=sys.stderr)
    
    # Add venv bin to PATH
    os.environ["PATH"] = str(venv_bin) + os.pathsep + os.environ.get("PATH", "")
    
    # Launch nanobot gateway using the venv python
    nanobot_script = venv_bin / "nanobot"
    os.execvp(str(nanobot_script), [
        str(nanobot_script), 
        "gateway", 
        "--config", str(resolved_path), 
        "--workspace", str(workspace_dir / "nanobot" / "workspace")
    ])

if __name__ == "__main__":
    main()
