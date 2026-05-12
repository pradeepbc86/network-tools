# RPKI Validator

Validate BGP route announcements against RPKI ROAs from multiple public validators.

## What is RPKI?

RPKI (Resource Public Key Infrastructure) helps prevent BGP hijacks by cryptographically binding IP prefixes to authorized origin ASNs.

**ROA (Route Origin Authorization)** = Certificate that says "AS X is authorized to originate prefix Y"

## Features

- Validates prefix/ASN combinations against RPKI ROAs
- Checks maxLength validation rules
- Falls back between multiple RPKI validators (Cloudflare, RIPE NCC)
- Batch validation from YAML file
- Clear validation status: Valid, Invalid, or ROA Not Found

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Validate from YAML file
```bash
cp prefixes.yaml.example prefixes.yaml
# Edit prefixes.yaml with your prefixes and ASN
python rpki_validator.py --prefixes prefixes.yaml
```

### Validate single prefix
```bash
python rpki_validator.py --prefix 192.0.2.0/24 --asn 65000
```

### Enable debug logging
```bash
python rpki_validator.py --prefixes prefixes.yaml --debug
```

## Output

```
Using RPKI validator: Cloudflare

+--------------------+-------------+-----------+----------------------------------+
| Prefix             | Origin ASN  | Status    | Details                          |
+--------------------+-------------+-----------+----------------------------------+
| 192.0.2.0/24       | AS65000     | VALID     | Valid ROA: AS65000, maxLength /24|
| 198.51.100.0/24    | AS65000     | NOT FOUND | No ROA exists for this prefix    |
| 203.0.113.0/24     | AS65000     | INVALID   | ROA exists but AS65000 not auth  |
+--------------------+-------------+-----------+----------------------------------+

Summary:
  Valid:        1
  Invalid:      1
  ROA Missing:  1
  Total:        3
```

## Validation Logic

1. **VALID**: ROA exists, ASN matches, prefix length <= maxLength
2. **INVALID**: ROA exists but ASN doesn't match or prefix is more specific than maxLength
3. **NOT FOUND**: No ROA exists for this exact prefix

## Best Practices

- Create ROAs for all your announced prefixes
- Set maxLength to the most specific prefix you'll ever announce
- Validate before announcing new prefixes to the internet
- Monitor regularly for INVALID status (indicates potential hijack or misconfiguration)

## RPKI Resources

- [ARIN RPKI](https://www.arin.net/resources/manage/rpki/)
- [RIPE NCC RPKI](https://www.ripe.net/manage-ips-and-asns/resource-management/rpki)
- [Cloudflare RPKI Toolkit](https://rpki.cloudflare.com/)
- [RPKI.is overview](https://rpki.is/)

## Troubleshooting

**"All RPKI validators failed"**
- Check internet connectivity
- Validators may be temporarily down — try again later

**"Invalid prefix format"**
- Use CIDR notation: `192.0.2.0/24`
- Include the prefix length (the /XX part)

**"YAML must contain 'asn' and 'prefixes' keys"**
- Verify your prefixes.yaml matches the format in `prefixes.yaml.example`
