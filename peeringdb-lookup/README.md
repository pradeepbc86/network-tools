# PeeringDB Lookup Tool

Query PeeringDB API to find ASN information, IX locations, and peering opportunities.

## Features

- Look up ASN details (name, type, policy, traffic levels)
- List all IX locations where an ASN peers
- **Find common IX locations between two ASNs** (peering opportunities)
- Export results to JSON or formatted tables

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Look up single ASN
```bash
python peeringdb_tool.py --asn 13335
```

Output:
```
============================================================
Network: Cloudflare, Inc.
ASN: AS13335
============================================================
  Type: Content
  Traffic: 100+ Tbps
  Scope: Global
  Peering Policy: Open
  Website: https://www.cloudflare.com

  IX Locations (200+):
  +--------------+----------+----------+--------------+-------------+
  | IX Name      | City     | Country  | IPv4         | Speed (Mbps)|
  +--------------+----------+----------+--------------+-------------+
  | AMS-IX       | Amsterdam| NL       | 80.249.208.x | 400000      |
  | DE-CIX       | Frankfurt| DE       | 80.81.202.x  | 400000      |
  +--------------+----------+----------+--------------+-------------+
```

### Find common IX locations (peering opportunities)
```bash
python peeringdb_tool.py --compare 13335 15169
```

Output:
```
Found 42 common IX location(s)

============================================================
AS13335: Cloudflare, Inc.
AS15169: Google LLC
============================================================

  +--------------+----------+----------+--------------+--------------+
  | IX Name      | City     | Country  | AS13335 IP   | AS15169 IP   |
  +--------------+----------+----------+--------------+--------------+
  | AMS-IX       | Amsterdam| NL       | 80.249.208.x | 80.249.209.y |
  | LINX LON1    | London   | GB       | 195.66.224.x | 195.66.236.y |
  +--------------+----------+----------+--------------+--------------+

Peering Opportunity: You can establish BGP sessions at 42 IX location(s)
```

### Export to JSON
```bash
python peeringdb_tool.py --asn 13335 --output json > cloudflare.json
```

## Use Cases

1. **Peering Research**: Find where your competitors or potential peers are present
2. **IX Selection**: Identify which IXs to join based on peer presence
3. **Network Planning**: Map out global peering footprint
4. **Capacity Planning**: See connection speeds at different IXs

## API Notes

- Uses public PeeringDB API (no authentication required for basic queries)
- Rate limiting: Be respectful, avoid hammering the API
- Data freshness: PeeringDB is community-maintained, accuracy may vary

## Troubleshooting

**"ASN not found"**
- Verify ASN number (no "AS" prefix needed, just the number)
- Check if ASN is registered in PeeringDB at peeringdb.com

**"No IX locations found"**
- ASN may not peer at public IXs (private peering only)
- ASN may not have updated their PeeringDB record

**"PeeringDB API error"**
- Check internet connectivity
- PeeringDB may be temporarily unavailable (try again later)
