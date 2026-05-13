"""PeeringDB lookup — query ASN info and find IX peering opportunities."""

import sys
import json
import logging
from typing import Dict, List, Optional
import click
import requests
from tabulate import tabulate

logger = logging.getLogger(__name__)

PEERINGDB_API = "https://www.peeringdb.com/api"


class PeeringDBClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'netcli/0.1.0'})

    def get_network(self, asn: int) -> Optional[Dict]:
        try:
            r = self.session.get(f"{PEERINGDB_API}/net?asn={asn}", timeout=10)
            r.raise_for_status()
            data = r.json().get('data', [])
            if not data:
                click.echo(f"Error: ASN {asn} not found in PeeringDB", err=True)
                return None
            return data[0]
        except requests.RequestException as e:
            click.echo(f"Error: PeeringDB API error: {e}", err=True)
            return None

    def get_ix_locations(self, net_id: int) -> List[Dict]:
        try:
            r = self.session.get(f"{PEERINGDB_API}/netixlan?net_id={net_id}", timeout=10)
            r.raise_for_status()
            return r.json().get('data', [])
        except requests.RequestException:
            return []

    def get_ix_details(self, ix_id: int) -> Dict:
        try:
            r = self.session.get(f"{PEERINGDB_API}/ix/{ix_id}", timeout=10)
            r.raise_for_status()
            data = r.json().get('data', [])
            return data[0] if data else {}
        except requests.RequestException:
            return {}


@click.group()
def peering():
    """Query PeeringDB for ASN and IX information."""
    pass


@peering.command()
@click.option('--asn', required=True, type=int, help='ASN to look up')
@click.option('--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def lookup(asn, output):
    """Look up a single ASN in PeeringDB.

    \b
    Examples:
      netcli peering lookup --asn 13335
      netcli peering lookup --asn 13335 --output json
    """
    client = PeeringDBClient()
    network = client.get_network(asn)
    if not network:
        sys.exit(1)

    ix_locations = client.get_ix_locations(network['id'])

    if output == 'json':
        click.echo(json.dumps({'network': network, 'ix_locations': ix_locations}, indent=2))
        return

    click.echo(f"\n{'='*60}")
    click.echo(f"Network: {network.get('name')}")
    click.echo(f"ASN: AS{network.get('asn')}")
    click.echo(f"{'='*60}")
    click.echo(f"  Type:           {network.get('info_type', 'N/A')}")
    click.echo(f"  Traffic:        {network.get('info_traffic', 'N/A')}")
    click.echo(f"  Scope:          {network.get('info_scope', 'N/A')}")
    click.echo(f"  Peering Policy: {network.get('policy_general', 'N/A')}")
    click.echo(f"  Website:        {network.get('website', 'N/A')}")

    if not ix_locations:
        click.echo("\n  No IX locations found")
        return

    click.echo(f"\n  IX Locations ({len(ix_locations)}):")
    table = []
    for ix in ix_locations:
        details = client.get_ix_details(ix.get('ix_id'))
        table.append([
            details.get('name', 'N/A'),
            details.get('city', 'N/A'),
            details.get('country', 'N/A'),
            ix.get('ipaddr4', 'N/A'),
            ix.get('speed', 'N/A'),
        ])
    click.echo(tabulate(table, headers=['IX Name', 'City', 'Country', 'IPv4', 'Speed (Mbps)'], tablefmt='grid'))


@peering.command()
@click.argument('asn1', type=int)
@click.argument('asn2', type=int)
def compare(asn1, asn2):
    """Find common IX locations between two ASNs.

    \b
    Examples:
      netcli peering compare 13335 15169
    """
    client = PeeringDBClient()

    net1 = client.get_network(asn1)
    net2 = client.get_network(asn2)
    if not net1 or not net2:
        sys.exit(1)

    ix1 = client.get_ix_locations(net1['id'])
    ix2 = client.get_ix_locations(net2['id'])

    common = {ix['ix_id'] for ix in ix1} & {ix['ix_id'] for ix in ix2}

    if not common:
        click.echo(f"\nNo common IX locations between AS{asn1} and AS{asn2}")
        click.echo(f"  AS{asn1} ({net1['name']}) is at {len(ix1)} IXs")
        click.echo(f"  AS{asn2} ({net2['name']}) is at {len(ix2)} IXs")
        return

    click.echo(f"\nFound {len(common)} common IX location(s)")
    click.echo(f"\n{'='*60}")
    click.echo(f"AS{asn1}: {net1['name']}")
    click.echo(f"AS{asn2}: {net2['name']}")
    click.echo(f"{'='*60}")

    table = []
    for ix_id in common:
        details = client.get_ix_details(ix_id)
        ip1 = next((ix['ipaddr4'] for ix in ix1 if ix['ix_id'] == ix_id), 'N/A')
        ip2 = next((ix['ipaddr4'] for ix in ix2 if ix['ix_id'] == ix_id), 'N/A')
        table.append([details.get('name', 'N/A'), details.get('city', 'N/A'), details.get('country', 'N/A'), ip1, ip2])

    click.echo(tabulate(table, headers=['IX Name', 'City', 'Country', f'AS{asn1} IP', f'AS{asn2} IP'], tablefmt='grid'))
    click.echo(f"\nPeering opportunity: {len(common)} shared IX location(s)")
