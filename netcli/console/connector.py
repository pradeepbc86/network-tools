"""Console connector — connect to device consoles via NetBox + SSH jump host."""

import sys
import os
import subprocess
import logging
from typing import Dict, List, Optional
import click
import yaml
import requests

logger = logging.getLogger(__name__)


class Config:
    def __init__(self, config_file: str = 'config.yaml'):
        self.netbox_url = self.netbox_token = self.jump_host = self.ssh_username = None

        if os.path.exists(config_file):
            with open(config_file) as f:
                cfg = yaml.safe_load(f)
                self.netbox_url   = cfg.get('netbox', {}).get('url')
                self.netbox_token = cfg.get('netbox', {}).get('api_token')
                self.jump_host    = cfg.get('ssh', {}).get('jump_host')
                self.ssh_username = cfg.get('ssh', {}).get('username')

        self.netbox_url   = os.getenv('NETBOX_URL',   self.netbox_url)
        self.netbox_token = os.getenv('NETBOX_TOKEN', self.netbox_token)
        self.jump_host    = os.getenv('JUMP_HOST',    self.jump_host)
        self.ssh_username = os.getenv('SSH_USERNAME', self.ssh_username)

        if not all([self.netbox_url, self.netbox_token, self.jump_host]):
            raise ValueError("Missing required config: NETBOX_URL, NETBOX_TOKEN, JUMP_HOST")


class NetBoxClient:
    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.headers = {'Authorization': f'Token {token}', 'Content-Type': 'application/json'}

    def get_device_id(self, device_name: str) -> Optional[int]:
        try:
            r = requests.get(f"{self.url}/dcim/devices/?name={device_name}", headers=self.headers, timeout=10)
            r.raise_for_status()
            results = r.json().get('results', [])
            if not results:
                click.echo(f"Error: Device '{device_name}' not found in NetBox", err=True)
                return None
            return results[0]['id']
        except requests.RequestException as e:
            click.echo(f"Error: NetBox API error: {e}", err=True)
            return None

    def get_console_ports(self, device_id: int) -> List[Dict]:
        try:
            r = requests.get(f"{self.url}/dcim/console-ports/?device_id={device_id}", headers=self.headers, timeout=10)
            r.raise_for_status()
            ports = []
            for port in r.json().get('results', []):
                for ep in port.get('connected_endpoints', []):
                    ports.append({'name': port['display'], 'console_server': ep['device']['display'], 'port_name': ep['display']})
            return ports
        except requests.RequestException as e:
            click.echo(f"Error: NetBox API error: {e}", err=True)
            return []


def parse_port_number(port_name: str) -> Optional[int]:
    for part in port_name.replace(')', '').split():
        if part.isdigit():
            return int(part)
    return None


@click.group()
def console():
    """Connect to device console via NetBox + SSH jump host."""
    pass


@console.command()
@click.argument('device')
@click.option('--config', 'config_file', default='config.yaml', help='Config file path')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def connect(device, config_file, debug):
    """Connect to a device console.

    \b
    Examples:
      netcli console connect edge-router-01
      netcli console connect --config myconfig.yaml core-switch-02
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    try:
        cfg = Config(config_file)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    username = cfg.ssh_username or click.prompt("SSH Username")

    netbox = NetBoxClient(cfg.netbox_url, cfg.netbox_token)
    device_id = netbox.get_device_id(device)
    if not device_id:
        sys.exit(1)

    ports = netbox.get_console_ports(device_id)
    if not ports:
        click.echo(f"Error: No console ports found for '{device}'", err=True)
        sys.exit(1)

    if len(ports) == 1:
        selected = ports[0]
    else:
        click.echo("\nAvailable console ports:")
        for i, p in enumerate(ports, 1):
            click.echo(f"  {i}. {p['name']} on {p['console_server']}")
        choice = click.prompt("Select port", type=click.IntRange(1, len(ports)))
        selected = ports[choice - 1]

    port_number = parse_port_number(selected['port_name'])
    if not port_number:
        click.echo(f"Error: Could not parse port number from '{selected['port_name']}'", err=True)
        sys.exit(1)

    click.echo(f"Connecting to {selected['console_server']}:{port_number} via {cfg.jump_host}...")
    try:
        subprocess.run([
            'ssh', '-J', f"{username}@{cfg.jump_host}", '-t',
            f"{username}@{selected['console_server']}", f"telnet localhost {port_number}"
        ], check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: SSH connection failed: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\nConnection closed")
