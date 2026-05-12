#!/usr/bin/env python3
"""
Device Inventory Collector

Connects to network devices via SSH and collects inventory information
(hostname, model, OS version, serial number).

Usage:
    python inventory_collector.py --devices devices.yaml
    python inventory_collector.py --devices devices.yaml --output csv
    python inventory_collector.py --devices devices.yaml --output json --file inventory.json
"""

import argparse
import sys
import os
import csv
import json
import logging
from getpass import getpass
from typing import Dict, List, Optional
import yaml
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from tabulate import tabulate

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_devices(file_path: str) -> List[Dict]:
    """Load device list from YAML file."""
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
            if 'devices' not in data:
                raise ValueError("YAML must contain 'devices' key")
            return data['devices']
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML: {e}")
        sys.exit(1)


def parse_juniper_model(output: str) -> str:
    """Parse Juniper model from show version output."""
    for line in output.split('\n'):
        if 'Model:' in line:
            return line.split('Model:')[1].strip()
    return 'Unknown'


def parse_juniper_version(output: str) -> str:
    """Parse Juniper OS version."""
    for line in output.split('\n'):
        if 'JUNOS' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if 'JUNOS' in part and i + 1 < len(parts):
                    return parts[i + 1]
    return 'Unknown'


def parse_juniper_serial(output: str) -> str:
    """Parse Juniper serial number."""
    for line in output.split('\n'):
        if 'Serial number:' in line:
            return line.split('Serial number:')[1].strip()
    return 'Unknown'


def parse_cisco_ios_model(output: str) -> str:
    """Parse Cisco IOS model."""
    for line in output.split('\n'):
        if 'cisco' in line.lower() and ('bytes of memory' in line or 'processor' in line):
            parts = line.split()
            for part in parts:
                if part.upper().startswith(('C', 'WS-', 'ASR', 'ISR')):
                    return part
    return 'Unknown'


def parse_cisco_ios_version(output: str) -> str:
    """Parse Cisco IOS version."""
    for line in output.split('\n'):
        if 'Version' in line and ('IOS' in line or 'Software' in line):
            version_part = line.split('Version')[1].split(',')[0].strip()
            return version_part
    return 'Unknown'


def parse_cisco_ios_serial(output: str) -> str:
    """Parse Cisco IOS serial number."""
    for line in output.split('\n'):
        if 'Processor board ID' in line:
            return line.split('Processor board ID')[1].strip()
    return 'Unknown'


def parse_arista_model(output: str) -> str:
    """Parse Arista model."""
    for line in output.split('\n'):
        if 'Hardware version:' in line or 'Model:' in line:
            return line.split(':')[1].strip()
    return 'Unknown'


def parse_arista_version(output: str) -> str:
    """Parse Arista EOS version."""
    for line in output.split('\n'):
        if 'Software image version:' in line:
            return line.split(':')[1].strip()
    return 'Unknown'


def parse_arista_serial(output: str) -> str:
    """Parse Arista serial."""
    for line in output.split('\n'):
        if 'Serial number:' in line or 'System MAC address:' in line:
            return line.split(':')[1].strip()
    return 'Unknown'


def collect_device_info(device_params: Dict, password: str) -> Dict:
    """
    Connect to device and collect inventory information.

    Returns dict with: ip, hostname, model, version, serial, status, error
    """
    ip = device_params.get('ip')
    logger.info(f"Connecting to {ip}...")

    device_params = device_params.copy()
    device_params['password'] = password
    device_params['secret'] = password

    try:
        connection = ConnectHandler(**device_params)
        hostname = connection.find_prompt().replace('>', '').replace('#', '').strip()

        device_type = device_params.get('device_type', '')
        output = connection.send_command('show version')

        if 'juniper' in device_type:
            model = parse_juniper_model(output)
            version = parse_juniper_version(output)
            serial = parse_juniper_serial(output)
        elif 'cisco_ios' in device_type or 'cisco_xe' in device_type:
            model = parse_cisco_ios_model(output)
            version = parse_cisco_ios_version(output)
            serial = parse_cisco_ios_serial(output)
        elif 'arista' in device_type:
            model = parse_arista_model(output)
            version = parse_arista_version(output)
            serial = parse_arista_serial(output)
        else:
            model = version = serial = 'Unknown'

        connection.disconnect()

        return {
            'ip': ip,
            'hostname': hostname,
            'model': model,
            'version': version,
            'serial': serial,
            'status': 'success',
            'error': None
        }

    except NetmikoTimeoutException:
        logger.error(f"{ip}: Connection timeout")
        return {
            'ip': ip, 'hostname': 'N/A', 'model': 'N/A',
            'version': 'N/A', 'serial': 'N/A',
            'status': 'timeout', 'error': 'Connection timeout'
        }

    except NetmikoAuthenticationException:
        logger.error(f"{ip}: Authentication failed")
        return {
            'ip': ip, 'hostname': 'N/A', 'model': 'N/A',
            'version': 'N/A', 'serial': 'N/A',
            'status': 'auth_failed', 'error': 'Authentication failed'
        }

    except Exception as e:
        logger.error(f"{ip}: Error - {str(e)}")
        return {
            'ip': ip, 'hostname': 'N/A', 'model': 'N/A',
            'version': 'N/A', 'serial': 'N/A',
            'status': 'error', 'error': str(e)
        }


def save_results(results: List[Dict], output_format: str, output_file: str):
    """Save results to file."""
    if output_format == 'csv':
        with open(output_file, 'w', newline='') as f:
            fieldnames = ['ip', 'hostname', 'model', 'version', 'serial', 'status', 'error']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        logger.info(f"Results saved to {output_file}")

    elif output_format == 'json':
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")


def display_results(results: List[Dict]):
    """Display results in a table."""
    table_data = []
    for result in results:
        status_icon = 'OK' if result['status'] == 'success' else 'FAIL'
        table_data.append([
            result['ip'],
            result['hostname'],
            result['model'],
            result['version'],
            result['serial'],
            f"{status_icon} ({result['status']})"
        ])

    headers = ['IP Address', 'Hostname', 'Model', 'OS Version', 'Serial', 'Status']
    print(f"\n{tabulate(table_data, headers=headers, tablefmt='grid')}\n")

    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"Summary: {success_count}/{len(results)} devices collected successfully")


def main():
    parser = argparse.ArgumentParser(
        description='Collect inventory from network devices via SSH',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Display inventory in table format
  python inventory_collector.py --devices devices.yaml

  # Export to CSV
  python inventory_collector.py --devices devices.yaml --output csv

  # Export to JSON
  python inventory_collector.py --devices devices.yaml --output json --file inventory.json

  # Enable debug logging
  python inventory_collector.py --devices devices.yaml --debug
        """
    )
    parser.add_argument(
        '--devices', '-d',
        required=True,
        help='Path to devices YAML file'
    )
    parser.add_argument(
        '--output', '-o',
        choices=['table', 'csv', 'json'],
        default='table',
        help='Output format (default: table)'
    )
    parser.add_argument(
        '--file', '-f',
        default='inventory.csv',
        help='Output file name (default: inventory.csv)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    devices = load_devices(args.devices)
    logger.info(f"Loaded {len(devices)} device(s)")

    password = os.getenv('DEVICE_PASSWORD') or getpass("Device password: ")

    results = []
    for device in devices:
        result = collect_device_info(device, password)
        results.append(result)

    display_results(results)

    if args.output != 'table':
        output_file = args.file
        if args.output == 'json' and not args.file.endswith('.json'):
            output_file = args.file.replace('.csv', '') + '.json'
        save_results(results, args.output, output_file)

    if any(r['status'] != 'success' for r in results):
        sys.exit(1)


if __name__ == '__main__':
    main()
