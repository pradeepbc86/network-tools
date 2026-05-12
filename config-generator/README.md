# Config Generator

Generate vendor-specific network device configurations from YAML inventory using Jinja2 templates.

## Supported Vendors

- **Juniper JunOS** (PTX, QFX, MX series)
- **Cisco IOS** (2900, 3900, Catalyst switches)
- **Cisco IOS-XR** (ASR9k, NCS series)
- **Arista EOS** (7000 series)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Generate configs for all devices:
```bash
python generator.py --inventory inventory.yaml
```

Generate for specific vendor only:
```bash
python generator.py --inventory inventory.yaml --vendor juniper
```

Generate for single device:
```bash
python generator.py --inventory inventory.yaml --device edge-router-sea01
```

Custom output directory:
```bash
python generator.py --inventory inventory.yaml --output /tmp/configs/
```

Enable debug logging:
```bash
python generator.py --inventory inventory.yaml --debug
```

## Inventory Format

See `inventory.yaml` for complete examples. Basic structure:

```yaml
devices:
  - name: "device-hostname"
    vendor: "juniper"  # or cisco_ios, cisco_iosxr, arista
    model: "PTX10003"
    mgmt_ip: "10.0.0.1"
    loopback_ip: "192.0.2.1/32"
    bgp_asn: 65000
    bgp_router_id: "192.0.2.1"
    interfaces:
      - name: "ge-0/0/0"
        description: "Description"
        ip: "198.51.100.1/31"
        bgp_peer_ip: "198.51.100.0"
        bgp_peer_asn: 65001
```

## Adding Custom Templates

1. Create a new Jinja2 template in `templates/`
2. Add vendor mapping in `generator.py` VENDOR_TEMPLATES dict
3. Use Jinja2 syntax with `device` context variable

## Output

Configurations are saved to `generated/` directory (or custom path via `--output`):
```
generated/
├── edge-router-sea01.conf
├── core-router-lax01.conf
├── access-switch-nyc01.conf
└── spine-switch-dfw01.conf
```

## Troubleshooting

**"Template not found"**
- Verify template exists in `templates/` directory
- Check vendor name matches VENDOR_TEMPLATES mapping in `generator.py`

**"Invalid YAML"**
- Validate YAML syntax (use yamllint or an online validator)
- Check indentation (YAML is whitespace-sensitive)

**"No devices match the specified filters"**
- Check vendor/device name spelling (case-sensitive)
- Verify the device exists in your inventory.yaml
