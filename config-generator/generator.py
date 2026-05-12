#!/usr/bin/env python3
"""
Multi-Vendor Network Config Generator

Generates vendor-specific configurations from YAML inventory using Jinja2 templates.

Supported Vendors:
- Juniper JunOS (PTX, QFX, MX)
- Cisco IOS (2900, 3900, Catalyst)
- Cisco IOS-XR (ASR9k, NCS)
- Arista EOS

Usage:
    python generator.py --inventory inventory.yaml
    python generator.py --inventory inventory.yaml --vendor juniper
    python generator.py --inventory inventory.yaml --device edge-router-01
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Dict, List
import yaml
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

VENDOR_TEMPLATES = {
    'juniper': 'juniper_junos.j2',
    'cisco_ios': 'cisco_ios.j2',
    'cisco_iosxr': 'cisco_iosxr.j2',
    'arista': 'arista_eos.j2'
}


def load_inventory(inventory_file: str) -> Dict:
    """Load device inventory from YAML file."""
    try:
        with open(inventory_file, 'r') as f:
            inventory = yaml.safe_load(f)
            if 'devices' not in inventory:
                raise ValueError("Inventory must contain 'devices' key")
            return inventory
    except FileNotFoundError:
        logger.error(f"Inventory file not found: {inventory_file}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in inventory file: {e}")
        sys.exit(1)


def generate_config(device: Dict, template_dir: str, output_dir: str) -> bool:
    """Generate configuration for a single device."""
    vendor = device.get('vendor', '').lower()
    device_name = device.get('name', 'unknown')

    if vendor not in VENDOR_TEMPLATES:
        logger.error(f"Unsupported vendor '{vendor}' for device '{device_name}'")
        return False

    template_file = VENDOR_TEMPLATES[vendor]

    try:
        env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        template = env.get_template(template_file)
        config = template.render(device=device)

        output_file = Path(output_dir) / f"{device_name}.conf"
        with open(output_file, 'w') as f:
            f.write(config)

        logger.info(f"Generated config for {device_name} ({vendor}) -> {output_file}")
        return True

    except TemplateNotFound:
        logger.error(f"Template not found: {template_file}")
        return False
    except Exception as e:
        logger.error(f"Error generating config for {device_name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Generate network device configs from YAML inventory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generator.py --inventory inventory.yaml
  python generator.py --inventory inventory.yaml --vendor juniper
  python generator.py --inventory inventory.yaml --device edge-router-sea01
  python generator.py --inventory inventory.yaml --output /tmp/configs/
        """
    )
    parser.add_argument(
        '--inventory', '-i',
        required=True,
        help='Path to inventory YAML file'
    )
    parser.add_argument(
        '--templates', '-t',
        default='templates',
        help='Templates directory (default: templates/)'
    )
    parser.add_argument(
        '--output', '-o',
        default='generated',
        help='Output directory (default: generated/)'
    )
    parser.add_argument(
        '--vendor',
        choices=list(VENDOR_TEMPLATES.keys()),
        help='Generate configs for specific vendor only'
    )
    parser.add_argument(
        '--device',
        help='Generate config for specific device only'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    inventory = load_inventory(args.inventory)
    devices = inventory['devices']

    if args.vendor:
        devices = [d for d in devices if d.get('vendor', '').lower() == args.vendor]
    if args.device:
        devices = [d for d in devices if d.get('name') == args.device]

    if not devices:
        logger.error("No devices match the specified filters")
        sys.exit(1)

    logger.info(f"Generating configs for {len(devices)} device(s)...")
    success_count = 0

    for device in devices:
        if generate_config(device, args.templates, args.output):
            success_count += 1

    logger.info(f"Summary: {success_count}/{len(devices)} configs generated successfully")
    if success_count < len(devices):
        sys.exit(1)


if __name__ == '__main__':
    main()
