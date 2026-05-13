"""Device inventory collector — SSH into devices and collect inventory."""

import sys
import os
import csv
import json
import logging
from getpass import getpass
from typing import Dict, List
import click
import yaml
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from tabulate import tabulate

logger = logging.getLogger(__name__)


def load_devices(file_path: str) -> List[Dict]:
    try:
        with open(file_path) as f:
            data = yaml.safe_load(f)
            if 'devices' not in data:
                raise ValueError("YAML must contain 'devices' key")
            return data['devices']
    except FileNotFoundError:
        click.echo(f"Error: File not found: {file_path}", err=True)
        sys.exit(1)
    except yaml.YAMLError as e:
        click.echo(f"Error: Invalid YAML: {e}", err=True)
        sys.exit(1)


def _parse(output: str, keyword: str, split_on: str = ':') -> str:
    for line in output.splitlines():
        if keyword in line:
            parts = line.split(split_on, 1)
            return parts[1].strip() if len(parts) > 1 else 'Unknown'
    return 'Unknown'


def collect_device_info(device_params: Dict, password: str) -> Dict:
    ip = device_params.get('ip')
    params = {**device_params, 'password': password, 'secret': password}

    try:
        conn = ConnectHandler(**params)
        hostname = conn.find_prompt().replace('>', '').replace('#', '').strip()
        output = conn.send_command('show version')
        conn.disconnect()

        dtype = params.get('device_type', '')
        if 'juniper' in dtype:
            model   = _parse(output, 'Model:')
            version = next((p for line in output.splitlines() if 'JUNOS' in line for p in line.split() if p[0].isdigit()), 'Unknown')
            serial  = _parse(output, 'Serial number:')
        elif 'cisco_ios' in dtype or 'cisco_xe' in dtype:
            model   = next((p for line in output.splitlines() if 'cisco' in line.lower() and 'processor' in line for p in line.split() if p.upper().startswith(('C', 'WS-', 'ASR', 'ISR'))), 'Unknown')
            version = next((line.split('Version')[1].split(',')[0].strip() for line in output.splitlines() if 'Version' in line and 'IOS' in line), 'Unknown')
            serial  = _parse(output, 'Processor board ID', ' ')
        elif 'arista' in dtype:
            model   = _parse(output, 'Model:')
            version = _parse(output, 'Software image version:')
            serial  = _parse(output, 'Serial number:')
        else:
            model = version = serial = 'Unknown'

        return {'ip': ip, 'hostname': hostname, 'model': model, 'version': version, 'serial': serial, 'status': 'success', 'error': None}

    except NetmikoTimeoutException:
        return {'ip': ip, 'hostname': 'N/A', 'model': 'N/A', 'version': 'N/A', 'serial': 'N/A', 'status': 'timeout', 'error': 'Connection timeout'}
    except NetmikoAuthenticationException:
        return {'ip': ip, 'hostname': 'N/A', 'model': 'N/A', 'version': 'N/A', 'serial': 'N/A', 'status': 'auth_failed', 'error': 'Authentication failed'}
    except Exception as e:
        return {'ip': ip, 'hostname': 'N/A', 'model': 'N/A', 'version': 'N/A', 'serial': 'N/A', 'status': 'error', 'error': str(e)}


@click.group()
def inventory():
    """Collect device inventory via SSH."""
    pass


@inventory.command()
@click.option('--devices', '-d', required=True, help='Path to devices YAML file')
@click.option('--output', '-o', type=click.Choice(['table', 'csv', 'json']), default='table', help='Output format')
@click.option('--file', '-f', 'out_file', default='inventory.csv', help='Output file (for csv/json)')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def collect(devices, output, out_file, debug):
    """Collect inventory from network devices.

    \b
    Examples:
      netcli inventory collect --devices devices.yaml
      netcli inventory collect --devices devices.yaml --output csv
      netcli inventory collect --devices devices.yaml --output json --file inv.json
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    device_list = load_devices(devices)
    click.echo(f"Loaded {len(device_list)} device(s)")

    password = os.getenv('DEVICE_PASSWORD') or getpass("Device password: ")

    results = []
    for device in device_list:
        click.echo(f"  Connecting to {device.get('ip')}...")
        results.append(collect_device_info(device, password))

    table = [[r['ip'], r['hostname'], r['model'], r['version'], r['serial'],
              'OK' if r['status'] == 'success' else f"FAIL ({r['status']})"] for r in results]
    click.echo(f"\n{tabulate(table, headers=['IP', 'Hostname', 'Model', 'OS Version', 'Serial', 'Status'], tablefmt='grid')}")

    success = sum(1 for r in results if r['status'] == 'success')
    click.echo(f"\nSummary: {success}/{len(results)} devices collected successfully")

    if output == 'csv':
        with open(out_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ip', 'hostname', 'model', 'version', 'serial', 'status', 'error'])
            writer.writeheader()
            writer.writerows(results)
        click.echo(f"Saved to {out_file}")
    elif output == 'json':
        out_file = out_file if out_file.endswith('.json') else out_file.replace('.csv', '.json')
        with open(out_file, 'w') as f:
            json.dump(results, f, indent=2)
        click.echo(f"Saved to {out_file}")

    if any(r['status'] != 'success' for r in results):
        sys.exit(1)
