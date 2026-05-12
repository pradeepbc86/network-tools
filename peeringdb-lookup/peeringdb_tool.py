#!/usr/bin/env python3
"""
PeeringDB Lookup Tool

Query PeeringDB API for ASN information, IX locations, and peering opportunities.

Features:
- Look up single ASN details
- Find common IX locations between two ASNs
- Export results to JSON or formatted table

Usage:
    python peeringdb_tool.py --asn 13335
    python peeringdb_tool.py --compare 13335 15169
    python peeringdb_tool.py --asn 13335 --output json
"""

import argparse
import sys
import json
import logging
from typing import Dict, List, Optional
import requests
from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PEERINGDB_API = "https://www.peeringdb.com/api"


class PeeringDBClient:
    """Client for PeeringDB API."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'PeeringDB-Lookup-Tool/1.0'})

    def get_network(self, asn: int) -> Optional[Dict]:
        """Get network information for an ASN."""
        url = f"{PEERINGDB_API}/net?asn={asn}"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data.get('data'):
                logger.error(f"ASN {asn} not found in PeeringDB")
                return None

            return data['data'][0]
        except requests.RequestException as e:
            logger.error(f"PeeringDB API error: {e}")
            return None

    def get_ix_locations(self, net_id: int) -> List[Dict]:
        """Get IX locations where a network is present."""
        url = f"{PEERINGDB_API}/netixlan?net_id={net_id}"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json().get('data', [])
        except requests.RequestException as e:
            logger.error(f"PeeringDB API error: {e}")
            return []

    def get_ix_details(self, ix_id: int) -> Dict:
        """Get IX details by ID."""
        url = f"{PEERINGDB_API}/ix/{ix_id}"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json().get('data', [])
            return data[0] if data else {}
        except requests.RequestException as e:
            logger.error(f"PeeringDB API error: {e}")
            return {}


def display_network_info(network: Dict):
    """Display network information."""
    print(f"\n{'='*60}")
    print(f"Network: {network.get('name')}")
    print(f"ASN: AS{network.get('asn')}")
    print(f"{'='*60}")
    print(f"  Type: {network.get('info_type', 'N/A')}")
    print(f"  Traffic: {network.get('info_traffic', 'N/A')}")
    print(f"  Scope: {network.get('info_scope', 'N/A')}")
    print(f"  Peering Policy: {network.get('policy_general', 'N/A')}")
    print(f"  Website: {network.get('website', 'N/A')}")
    print(f"  Looking Glass: {network.get('looking_glass', 'N/A')}")
    print(f"  Route Server: {network.get('route_server', 'N/A')}")


def display_ix_locations(ix_locations: List[Dict], client: PeeringDBClient):
    """Display IX locations in a table."""
    if not ix_locations:
        print("\n  No IX locations found")
        return

    print(f"\n  IX Locations ({len(ix_locations)}):")

    table_data = []
    for ix_lan in ix_locations:
        ix_id = ix_lan.get('ix_id')
        ix_details = client.get_ix_details(ix_id)

        table_data.append([
            ix_details.get('name', 'N/A'),
            ix_details.get('city', 'N/A'),
            ix_details.get('country', 'N/A'),
            ix_lan.get('ipaddr4', 'N/A'),
            ix_lan.get('speed', 'N/A')
        ])

    headers = ['IX Name', 'City', 'Country', 'IPv4', 'Speed (Mbps)']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))


def find_common_ixs(asn1: int, asn2: int, client: PeeringDBClient):
    """Find common IX locations between two ASNs."""
    print(f"\nFinding common IX locations between AS{asn1} and AS{asn2}...")

    net1 = client.get_network(asn1)
    net2 = client.get_network(asn2)

    if not net1 or not net2:
        sys.exit(1)

    ix1 = client.get_ix_locations(net1['id'])
    ix2 = client.get_ix_locations(net2['id'])

    ix1_ids = {ix['ix_id'] for ix in ix1}
    ix2_ids = {ix['ix_id'] for ix in ix2}
    common_ix_ids = ix1_ids & ix2_ids

    if not common_ix_ids:
        print(f"\nNo common IX locations found")
        print(f"\n  AS{asn1} ({net1['name']}) is at {len(ix1)} IXs")
        print(f"  AS{asn2} ({net2['name']}) is at {len(ix2)} IXs")
        return

    print(f"\nFound {len(common_ix_ids)} common IX location(s)")
    print(f"\n{'='*60}")
    print(f"AS{asn1}: {net1['name']}")
    print(f"AS{asn2}: {net2['name']}")
    print(f"{'='*60}")

    table_data = []
    for ix_id in common_ix_ids:
        ix_details = client.get_ix_details(ix_id)

        asn1_ip = next((ix['ipaddr4'] for ix in ix1 if ix['ix_id'] == ix_id), 'N/A')
        asn2_ip = next((ix['ipaddr4'] for ix in ix2 if ix['ix_id'] == ix_id), 'N/A')

        table_data.append([
            ix_details.get('name', 'N/A'),
            ix_details.get('city', 'N/A'),
            ix_details.get('country', 'N/A'),
            asn1_ip,
            asn2_ip
        ])

    headers = ['IX Name', 'City', 'Country', f'AS{asn1} IP', f'AS{asn2} IP']
    print(tabulate(table_data, headers=headers, tablefmt='grid'))

    print(f"\nPeering Opportunity: You can establish BGP sessions at {len(common_ix_ids)} IX location(s)")


def main():
    parser = argparse.ArgumentParser(
        description='Query PeeringDB for ASN and IX information',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Look up single ASN
  python peeringdb_tool.py --asn 13335

  # Find common IXs between two ASNs
  python peeringdb_tool.py --compare 13335 15169

  # Export to JSON
  python peeringdb_tool.py --asn 13335 --output json > output.json
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--asn', type=int, help='Look up single ASN')
    group.add_argument(
        '--compare',
        nargs=2,
        type=int,
        metavar=('ASN1', 'ASN2'),
        help='Find common IXs between two ASNs'
    )

    parser.add_argument(
        '--output',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table)'
    )
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    client = PeeringDBClient()

    if args.asn:
        network = client.get_network(args.asn)
        if not network:
            sys.exit(1)

        ix_locations = client.get_ix_locations(network['id'])

        if args.output == 'json':
            output = {
                'network': network,
                'ix_locations': ix_locations
            }
            print(json.dumps(output, indent=2))
        else:
            display_network_info(network)
            display_ix_locations(ix_locations, client)

    elif args.compare:
        find_common_ixs(args.compare[0], args.compare[1], client)


if __name__ == '__main__':
    main()
