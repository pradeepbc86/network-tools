# Console Connector

Connect to network device consoles via NetBox API, SSH jump host, and console server telnet.

## Features

- Queries NetBox for device console port information
- Supports SSH ProxyJump for jump host tunneling
- Handles multiple console ports (prompts for selection)
- Secure credential handling (config file + environment variables)
- Comprehensive logging to file and console

## Prerequisites

- Python 3.9+
- SSH access to jump host and console servers
- NetBox API token with read access to DCIM
- Device console ports configured in NetBox

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy `config.yaml.example` to `config.yaml`:
```bash
cp config.yaml.example config.yaml
```

2. Edit `config.yaml` with your NetBox URL, API token, and jump host.

**OR** use environment variables:
```bash
export NETBOX_URL="https://netbox.example.com/api"
export NETBOX_TOKEN="your-token-here"
export JUMP_HOST="jumphost.example.com"
export SSH_USERNAME="your-username"
```

## Usage

```bash
# Connect to device
python console.py edge-router-01

# With custom config file
python console.py --config myconfig.yaml core-switch-02

# Enable debug logging
python console.py --debug spine-switch-01
```

## How It Works

1. Queries NetBox API for device by name
2. Retrieves connected console port information
3. If multiple ports, prompts user to select
4. Uses SSH ProxyJump to tunnel through jump host
5. Executes `telnet localhost <port>` on the console server
6. Drops into interactive console session

## Security Notes

- Never commit `config.yaml` with real credentials
- Use environment variables in production
- Consider SSH agent forwarding (`ssh-add`) for jump host auth
- Rotate NetBox API tokens regularly

## Troubleshooting

**"Device not found in NetBox"**
- Verify device name spelling (case-sensitive, must match NetBox exactly)
- Check NetBox API token has permission to read DCIM devices

**"No console ports found"**
- Ensure device has console ports configured in NetBox
- Verify console port has a connected endpoint (console server)

**"SSH connection failed"**
- Verify jump host SSH access: `ssh user@jumphost`
- Check console server reachability from jump host
- Confirm telnet port number is correct in NetBox

**"SSH ProxyJump not supported"**
- Requires OpenSSH 7.3+ on your local machine
- Alternative: configure ProxyCommand in `~/.ssh/config`
