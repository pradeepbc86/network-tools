# Network Tools

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Production-ready Python tools for network engineers: config generation, PeeringDB lookups, RPKI validation, device inventory, and console access.

## Tools

| Tool | Description |
|------|-------------|
| [config-generator](config-generator/) | Generate vendor-specific configs from YAML inventory using Jinja2 |
| [peeringdb-lookup](peeringdb-lookup/) | Query PeeringDB API for ASN info and IX peering opportunities |
| [rpki-validator](rpki-validator/) | Validate BGP announcements against RPKI ROAs |
| [device-inventory](device-inventory/) | SSH-based device inventory collection via Netmiko |
| [console-connector](console-connector/) | Connect to device consoles via NetBox + SSH jump host |

## Quick Start

```bash
# Install all dependencies
pip install -r requirements.txt

# Or install per-tool
cd config-generator && pip install -r requirements.txt
```

## Requirements

- Python 3.9+
- See each tool's `requirements.txt` for specific dependencies

## License

MIT License — see [LICENSE](LICENSE)
