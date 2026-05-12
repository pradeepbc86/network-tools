#!/usr/bin/env python3
"""
RPKI ROA Validator

Validates BGP route announcements against RPKI ROAs from multiple public validators.

Supports:
- Cloudflare RPKI validator
- RIPE NCC RPKI validator

Usage:
    python rpki_validator.py --prefixes prefixes.yaml
    python rpki_validator.py --prefix 192.0.2.0/24 --asn 65000
"""

import argparse
import sys
import logging
from typing import Dict, List, Optional
import yaml
import requests
from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RPKI_VALIDATORS = [
    {
        'name': 'Cloudflare',
        'url': 'https://rpki.cloudflare.com/rpki.json'
    },
    {
        'name': 'RIPE NCC',
        'url': 'https://rpki-validator.ripe.net/api/v1/validity'
    }
]


class RPKIValidator:
    """RPKI ROA validator using public validators."""

    def __init__(self):
        self.roas = None
        self.validator_name = None

    def fetch_roas(self) -> bool:
        """Fetch ROAs from available validators."""
        for validator in RPKI_VALIDATORS:
            try:
                logger.info(f"Fetching ROAs from {validator['name']}...")
                response = requests.get(validator['url'], timeout=30)
                response.raise_for_status()

                self.roas = response.json().get('roas', [])
                self.validator_name = validator['name']
                logger.info(f"Loaded {len(self.roas)} ROAs from {validator['name']}")
                return True

            except requests.RequestException as e:
                logger.warning(f"Failed to fetch from {validator['name']}: {e}")
                continue

        logger.error("All RPKI validators failed")
        return False

    def validate_prefix(self, prefix: str, origin_asn: int) -> Dict:
        """
        Validate a prefix/ASN combination against ROAs.

        Returns dict with keys: status (valid/invalid/not_found), details
        """
        if not self.roas:
            return {'status': 'error', 'details': 'ROAs not loaded'}

        try:
            _, prefix_len_str = prefix.split('/')
            prefix_len = int(prefix_len_str)
        except ValueError:
            return {'status': 'error', 'details': 'Invalid prefix format'}

        matching_roas = [roa for roa in self.roas if roa.get('prefix') == prefix]

        if not matching_roas:
            return {
                'status': 'not_found',
                'details': f'No ROA exists for {prefix}'
            }

        for roa in matching_roas:
            roa_asn = int(str(roa.get('asn', '')).replace('AS', ''))
            roa_max_length = roa.get('maxLength', prefix_len)

            if roa_asn == origin_asn and prefix_len <= roa_max_length:
                return {
                    'status': 'valid',
                    'details': f'Valid ROA: AS{roa_asn}, maxLength /{roa_max_length}',
                    'roa': roa
                }

        return {
            'status': 'invalid',
            'details': f'ROA exists but AS{origin_asn} not authorized',
            'matching_roas': matching_roas
        }


def load_prefixes(file_path: str) -> Dict:
    """Load prefix list from YAML file."""
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            if 'asn' not in data or 'prefixes' not in data:
                raise ValueError("YAML must contain 'asn' and 'prefixes' keys")
            return data
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML: {e}")
        sys.exit(1)


def display_results(results: List[Dict]):
    """Display validation results in a table."""
    table_data = []

    for result in results:
        prefix = result['prefix']
        asn = result['asn']
        status = result['status']
        details = result['details']

        if status == 'valid':
            status_display = 'VALID'
        elif status == 'invalid':
            status_display = 'INVALID'
        elif status == 'not_found':
            status_display = 'NOT FOUND'
        else:
            status_display = 'ERROR'

        table_data.append([
            prefix,
            f'AS{asn}',
            status_display,
            details
        ])

    headers = ['Prefix', 'Origin ASN', 'Status', 'Details']
    print(f"\n{tabulate(table_data, headers=headers, tablefmt='grid')}\n")

    valid_count = sum(1 for r in results if r['status'] == 'valid')
    invalid_count = sum(1 for r in results if r['status'] == 'invalid')
    not_found_count = sum(1 for r in results if r['status'] == 'not_found')

    print(f"Summary:")
    print(f"  Valid:        {valid_count}")
    print(f"  Invalid:      {invalid_count}")
    print(f"  ROA Missing:  {not_found_count}")
    print(f"  Total:        {len(results)}")


def main():
    parser = argparse.ArgumentParser(
        description='Validate BGP announcements against RPKI ROAs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate from YAML file
  python rpki_validator.py --prefixes prefixes.yaml

  # Validate single prefix
  python rpki_validator.py --prefix 192.0.2.0/24 --asn 65000

prefixes.yaml format:
  asn: 65000
  prefixes:
    - "192.0.2.0/24"
    - "198.51.100.0/24"
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prefixes', help='Path to YAML file with prefix list')
    group.add_argument('--prefix', help='Single prefix to validate (CIDR format)')

    parser.add_argument('--asn', type=int, help='Origin ASN (required with --prefix)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.prefix and not args.asn:
        parser.error("--asn is required when using --prefix")

    validator = RPKIValidator()
    if not validator.fetch_roas():
        sys.exit(1)

    print(f"\nUsing RPKI validator: {validator.validator_name}\n")

    if args.prefixes:
        data = load_prefixes(args.prefixes)
        asn = data['asn']
        prefixes = data['prefixes']
    else:
        asn = args.asn
        prefixes = [args.prefix]

    results = []
    for prefix in prefixes:
        logger.debug(f"Validating {prefix} AS{asn}")
        validation = validator.validate_prefix(prefix, asn)
        results.append({
            'prefix': prefix,
            'asn': asn,
            'status': validation['status'],
            'details': validation['details']
        })

    display_results(results)

    if any(r['status'] == 'invalid' for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
