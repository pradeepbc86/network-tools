"""Config generator — render vendor-specific configs from YAML inventory."""

import sys
import logging
from pathlib import Path
from typing import Dict, List
import click
import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)

VENDOR_TEMPLATES = {
    'juniper': 'juniper_junos.j2',
    'cisco_ios': 'cisco_ios.j2',
    'cisco_iosxr': 'cisco_iosxr.j2',
    'arista': 'arista_eos.j2',
}


def load_inventory(inventory_file: str) -> Dict:
    try:
        with open(inventory_file, 'r') as f:
            inventory = yaml.safe_load(f)
            if 'devices' not in inventory:
                raise ValueError("Inventory must contain 'devices' key")
            return inventory
    except FileNotFoundError:
        click.echo(f"Error: Inventory file not found: {inventory_file}", err=True)
        sys.exit(1)
    except yaml.YAMLError as e:
        click.echo(f"Error: Invalid YAML: {e}", err=True)
        sys.exit(1)


def render_config(device: Dict, template_dir: str) -> str:
    vendor = device.get('vendor', '').lower()
    if vendor not in VENDOR_TEMPLATES:
        raise ValueError(f"Unsupported vendor: {vendor}")

    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = env.get_template(VENDOR_TEMPLATES[vendor])
    return template.render(device=device)


@click.group()
def config():
    """Generate vendor-specific device configurations."""
    pass


@config.command()
@click.option('--inventory', '-i', required=True, help='Path to inventory YAML file')
@click.option('--templates', '-t', default='templates', help='Templates directory (default: templates/)')
@click.option('--output', '-o', default='generated', help='Output directory (default: generated/)')
@click.option('--vendor', type=click.Choice(list(VENDOR_TEMPLATES.keys())), help='Filter by vendor')
@click.option('--device', help='Filter by device name')
@click.option('--debug', is_flag=True, help='Enable debug logging')
def generate(inventory, templates, output, vendor, device, debug):
    """Generate configs from a YAML inventory file.

    \b
    Examples:
      netcli config generate --inventory inventory.yaml
      netcli config generate --inventory inventory.yaml --vendor juniper
      netcli config generate --inventory inventory.yaml --device edge-router-01
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    data = load_inventory(inventory)
    devices = data['devices']

    if vendor:
        devices = [d for d in devices if d.get('vendor', '').lower() == vendor]
    if device:
        devices = [d for d in devices if d.get('name') == device]

    if not devices:
        click.echo("Error: No devices match the specified filters", err=True)
        sys.exit(1)

    output_dir = Path(output)
    output_dir.mkdir(exist_ok=True)

    success = 0
    for dev in devices:
        name = dev.get('name', 'unknown')
        try:
            rendered = render_config(dev, templates)
            out_file = output_dir / f"{name}.conf"
            out_file.write_text(rendered)
            click.echo(f"  {name} -> {out_file}")
            success += 1
        except (TemplateNotFound, ValueError) as e:
            click.echo(f"  {name}: FAILED — {e}", err=True)

    click.echo(f"\n{success}/{len(devices)} configs generated")
    if success < len(devices):
        sys.exit(1)
