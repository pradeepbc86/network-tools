# netcli

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

network toolkit. Config generation, PeeringDB lookups, RPKI validation, device inventory, and console access — all under one command.

## Install

```bash
git clone https://github.com/pradeepbc86/network-tools.git
cd network-tools
pip install -e .
```

## Usage

```bash
# Generate vendor-specific device configs from YAML inventory
netcli config generate --inventory inventory.yaml
netcli config generate --inventory inventory.yaml --vendor juniper

# Look up ASN in PeeringDB
netcli peering lookup --asn 13335
netcli peering lookup --asn 13335 --output json

# Find common IX locations between two ASNs
netcli peering compare 13335 15169

# Validate prefixes against RPKI ROAs
netcli rpki validate --prefixes prefixes.yaml
netcli rpki validate --prefix 192.0.2.0/24 --asn 65000

# Collect device inventory via SSH
netcli inventory collect --devices devices.yaml
netcli inventory collect --devices devices.yaml --output csv

# Connect to device console via NetBox + jump host
netcli console connect edge-router-01
netcli console connect --config myconfig.yaml core-switch-02
```

## Supported Vendors

Config generation supports: Juniper JunOS · Cisco IOS · Cisco IOS-XR · Arista EOS

## Configuration

Tools that need credentials read from a config file or environment variables — no credentials in code.

```bash
# Console connector
export NETBOX_URL="https://netbox.example.com/api"
export NETBOX_TOKEN="your-token"
export JUMP_HOST="jumphost.example.com"

# Device inventory
export DEVICE_PASSWORD="your-password"
```

See `*.example` files in each module directory for full config reference.

## Development

```bash
make install   # install in editable mode
make test      # run tests
make lint      # syntax check
make clean     # remove build artifacts
```

## License

MIT
