"""RPKI validator — validate BGP announcements against ROAs."""

import sys
import logging
from typing import Dict, List, Optional
import click
import yaml
import requests
from tabulate import tabulate

logger = logging.getLogger(__name__)

RPKI_VALIDATORS = [
    {'name': 'Cloudflare', 'url': 'https://rpki.cloudflare.com/rpki.json'},
    {'name': 'RIPE NCC',   'url': 'https://rpki-validator.ripe.net/api/v1/validity'},
]


class RPKIValidator:
    def __init__(self):
        self.roas: Optional[List] = None
        self.validator_name: Optional[str] = None

    def fetch_roas(self) -> bool:
        for v in RPKI_VALIDATORS:
            try:
                click.echo(f"Fetching ROAs from {v['name']}...")
                r = requests.get(v['url'], timeout=30)
                r.raise_for_status()
                self.roas = r.json().get('roas', [])
                self.validator_name = v['name']
                click.echo(f"Loaded {len(self.roas)} ROAs from {v['name']}")
                return True
            except requests.RequestException as e:
                click.echo(f"Warning: {v['name']} unavailable: {e}", err=True)
        click.echo("Error: All RPKI validators failed", err=True)
        return False

    def validate(self, prefix: str, origin_asn: int) -> Dict:
        if not self.roas:
            return {'status': 'error', 'details': 'ROAs not loaded'}
        try:
            _, prefix_len = prefix.split('/')
            prefix_len = int(prefix_len)
        except ValueError:
            return {'status': 'error', 'details': 'Invalid prefix format (use CIDR)'}

        matching = [r for r in self.roas if r.get('prefix') == prefix]
        if not matching:
            return {'status': 'not_found', 'details': f'No ROA exists for {prefix}'}

        for roa in matching:
            roa_asn = int(str(roa.get('asn', '')).replace('AS', ''))
            max_len = roa.get('maxLength', prefix_len)
            if roa_asn == origin_asn and prefix_len <= max_len:
                return {'status': 'valid', 'details': f'Valid ROA: AS{roa_asn}, maxLength /{max_len}'}

        return {'status': 'invalid', 'details': f'ROA exists but AS{origin_asn} not authorized'}


@click.group()
def rpki():
    """Validate BGP announcements against RPKI ROAs."""
    pass


@rpki.command()
@click.option('--prefixes', 'prefixes_file', help='YAML file with ASN and prefix list')
@click.option('--prefix', help='Single prefix to validate (CIDR format)')
@click.option('--asn', type=int, help='Origin ASN (required with --prefix)')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def validate(prefixes_file, prefix, asn, debug):
    """Validate prefixes against RPKI ROAs.

    \b
    Examples:
      netcli rpki validate --prefixes prefixes.yaml
      netcli rpki validate --prefix 192.0.2.0/24 --asn 65000
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    if not prefixes_file and not prefix:
        click.echo("Error: Provide --prefixes or --prefix", err=True)
        sys.exit(2)
    if prefix and not asn:
        click.echo("Error: --asn is required with --prefix", err=True)
        sys.exit(2)

    validator = RPKIValidator()
    if not validator.fetch_roas():
        sys.exit(1)

    click.echo(f"\nUsing validator: {validator.validator_name}\n")

    if prefixes_file:
        try:
            with open(prefixes_file) as f:
                data = yaml.safe_load(f)
            asn = data['asn']
            prefixes = data['prefixes']
        except (FileNotFoundError, KeyError) as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    else:
        prefixes = [prefix]

    results = []
    for p in prefixes:
        result = validator.validate(p, asn)
        results.append({'prefix': p, 'asn': asn, **result})

    table = []
    for r in results:
        status_map = {'valid': 'VALID', 'invalid': 'INVALID', 'not_found': 'NOT FOUND', 'error': 'ERROR'}
        table.append([r['prefix'], f"AS{r['asn']}", status_map.get(r['status'], r['status']), r['details']])

    click.echo(tabulate(table, headers=['Prefix', 'Origin ASN', 'Status', 'Details'], tablefmt='grid'))

    valid = sum(1 for r in results if r['status'] == 'valid')
    invalid = sum(1 for r in results if r['status'] == 'invalid')
    missing = sum(1 for r in results if r['status'] == 'not_found')

    click.echo(f"\nSummary:")
    click.echo(f"  Valid:       {valid}")
    click.echo(f"  Invalid:     {invalid}")
    click.echo(f"  ROA Missing: {missing}")
    click.echo(f"  Total:       {len(results)}")

    if invalid:
        sys.exit(1)
