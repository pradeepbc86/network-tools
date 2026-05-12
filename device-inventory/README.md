# Device Inventory Collector

Automated network device inventory collection using SSH (Netmiko).

## Features

- Connects to devices via SSH and collects:
  - Hostname
  - Model/Platform
  - OS Version
  - Serial Number
- Multi-vendor support (Juniper, Cisco IOS/IOS-XR, Arista)
- Export to CSV or JSON
- Secure credential handling (no passwords in config files)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

1. Copy `devices.yaml.example` to `devices.yaml`:
```bash
cp devices.yaml.example devices.yaml
```

2. Edit `devices.yaml` and add your devices (DO NOT add passwords)

3. Set password via environment variable:
```bash
export DEVICE_PASSWORD=your_password
```

Or you'll be prompted when running the script.

## Usage

### Display inventory in table format
```bash
python inventory_collector.py --devices devices.yaml
```

### Export to CSV
```bash
python inventory_collector.py --devices devices.yaml --output csv
```

### Export to JSON
```bash
python inventory_collector.py --devices devices.yaml --output json --file inventory.json
```

### Enable debug logging
```bash
python inventory_collector.py --devices devices.yaml --debug
```

## Output

```
+------------------+--------------+-------------+-------------+--------------+----------------+
| IP Address       | Hostname     | Model       | OS Version  | Serial       | Status         |
+------------------+--------------+-------------+-------------+--------------+----------------+
| 192.168.1.1      | edge-rtr-01  | PTX10003    | 22.2R1.9    | AB1234567890 | OK (success)   |
| 192.168.1.2      | core-rtr-01  | ASR9001     | 7.3.2       | CD9876543210 | OK (success)   |
| 192.168.1.3      | N/A          | N/A         | N/A         | N/A          | FAIL (timeout) |
+------------------+--------------+-------------+-------------+--------------+----------------+

Summary: 2/3 devices collected successfully
```

## Supported Vendors

| Vendor         | device_type values                |
|----------------|-----------------------------------|
| Juniper JunOS  | `juniper_junos`                   |
| Cisco IOS      | `cisco_ios`, `cisco_xe`           |
| Cisco IOS-XR   | `cisco_xr`                        |
| Cisco NX-OS    | `cisco_nxos`                      |
| Arista EOS     | `arista_eos`                      |

## Security Best Practices

- **Never commit `devices.yaml` with real IPs or passwords**
- Use environment variables for passwords (`DEVICE_PASSWORD`)
- Consider SSH keys instead of passwords
- Use separate read-only accounts for inventory collection
- Rotate credentials regularly

## Troubleshooting

**"Connection timeout"**
- Verify device IP is reachable (`ping <ip>`)
- Check SSH is enabled on device
- Verify firewall allows SSH (port 22)

**"Authentication failed"**
- Check username in `devices.yaml`
- Verify the password is correct
- Some devices need `enable` mode — the tool passes `secret` automatically

**"Command not recognized"**
- Verify `device_type` is correct for your platform
- Cisco IOS and IOS-XE use different types (`cisco_ios` vs `cisco_xe`)
