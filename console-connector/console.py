#!/usr/bin/env python3
"""
NetBox Console Connector

Connects to network device consoles via NetBox API + SSH jump host + telnet.
Supports any NetBox instance and jump host configuration.

Usage:
    python console.py <device-name>
    python console.py --config myconfig.yaml core-switch-02
    python console.py --debug spine-switch-01

Configuration:
    Copy config.yaml.example to config.yaml and customize.
    Or set environment variables: NETBOX_URL, NETBOX_TOKEN, JUMP_HOST
"""

import argparse
import sys
import os
import logging
import subprocess
from typing import Dict, List, Optional
import yaml
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('console-connector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Config:
    """Load configuration from file or environment variables."""

    def __init__(self, config_file: str = 'config.yaml'):
        self.netbox_url = None
        self.netbox_token = None
        self.jump_host = None
        self.ssh_username = None

        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                self.netbox_url = config.get('netbox', {}).get('url')
                self.netbox_token = config.get('netbox', {}).get('api_token')
                self.jump_host = config.get('ssh', {}).get('jump_host')
                self.ssh_username = config.get('ssh', {}).get('username')

        self.netbox_url = os.getenv('NETBOX_URL', self.netbox_url)
        self.netbox_token = os.getenv('NETBOX_TOKEN', self.netbox_token)
        self.jump_host = os.getenv('JUMP_HOST', self.jump_host)
        self.ssh_username = os.getenv('SSH_USERNAME', self.ssh_username)

        if not all([self.netbox_url, self.netbox_token, self.jump_host]):
            raise ValueError(
                "Missing required configuration. Provide via config.yaml or environment variables:\n"
                "  NETBOX_URL, NETBOX_TOKEN, JUMP_HOST"
            )


class NetBoxClient:
    """Client for NetBox API interactions."""

    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.headers = {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }

    def get_device_id(self, device_name: str) -> Optional[int]:
        """Get device ID from NetBox by name."""
        endpoint = f"{self.url}/dcim/devices/?name={device_name}"
        try:
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()
            results = response.json().get('results', [])
            if not results:
                logger.error(f"Device '{device_name}' not found in NetBox")
                return None
            return results[0]['id']
        except requests.RequestException as e:
            logger.error(f"NetBox API error: {e}")
            return None

    def get_console_ports(self, device_id: int) -> List[Dict]:
        """Get console port details for a device."""
        endpoint = f"{self.url}/dcim/console-ports/?device_id={device_id}"
        try:
            response = requests.get(endpoint, headers=self.headers, timeout=10)
            response.raise_for_status()
            ports = []
            for port in response.json().get('results', []):
                if port.get('connected_endpoints'):
                    for ep in port['connected_endpoints']:
                        ports.append({
                            'name': port['display'],
                            'console_server': ep['device']['display'],
                            'port_name': ep['display']
                        })
            return ports
        except requests.RequestException as e:
            logger.error(f"NetBox API error: {e}")
            return []


def parse_console_port(port_name: str) -> Optional[int]:
    """Extract port number from console port name (e.g., 'Line 2023' -> 2023)."""
    try:
        parts = port_name.replace(')', '').split()
        for part in parts:
            if part.isdigit():
                return int(part)
        return None
    except (ValueError, AttributeError) as e:
        logger.error(f"Failed to parse port number from '{port_name}': {e}")
        return None


def connect_via_ssh(console_server: str, port: int, jump_host: str, username: str):
    """
    Connect to console server via SSH ProxyJump.

    Uses SSH ProxyJump to tunnel through the jump host, then telnet to the console port.
    """
    logger.info(f"Connecting to {console_server}:{port} via {jump_host}")

    ssh_cmd = [
        'ssh',
        '-J', f'{username}@{jump_host}',
        '-t',
        f'{username}@{console_server}',
        f'telnet localhost {port}'
    ]

    try:
        subprocess.run(ssh_cmd, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"SSH connection failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Connection interrupted by user")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='Connect to device console via NetBox + SSH jump host',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python console.py edge-router-01
  python console.py --config myconfig.yaml core-switch-02
  python console.py --debug spine-switch-01
        """
    )
    parser.add_argument('device', help='Device name as it appears in NetBox')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    try:
        config = Config(args.config)
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    username = config.ssh_username or input("SSH Username: ")

    netbox = NetBoxClient(config.netbox_url, config.netbox_token)

    device_id = netbox.get_device_id(args.device)
    if not device_id:
        sys.exit(1)

    console_ports = netbox.get_console_ports(device_id)
    if not console_ports:
        logger.error(f"No console ports found for device '{args.device}'")
        sys.exit(1)

    if len(console_ports) == 1:
        selected_port = console_ports[0]
        logger.info(f"Using console port: {selected_port['name']}")
    else:
        print("\nAvailable console ports:")
        for i, port in enumerate(console_ports, 1):
            print(f"  {i}. {port['name']} on {port['console_server']}")

        while True:
            try:
                choice = int(input(f"\nSelect port (1-{len(console_ports)}): "))
                if 1 <= choice <= len(console_ports):
                    selected_port = console_ports[choice - 1]
                    break
                print(f"Please enter a number between 1 and {len(console_ports)}")
            except ValueError:
                print("Invalid input. Please enter a number.")

    port_number = parse_console_port(selected_port['port_name'])
    if not port_number:
        logger.error(f"Could not parse port number from '{selected_port['port_name']}'")
        sys.exit(1)

    console_server = selected_port['console_server']
    connect_via_ssh(console_server, port_number, config.jump_host, username)


if __name__ == '__main__':
    main()
