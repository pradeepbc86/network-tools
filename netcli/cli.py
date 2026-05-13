"""netcli — main CLI entry point."""

import click
from netcli import __version__


@click.group()
@click.version_option(__version__, prog_name="netcli")
def cli():
    """netcli — CLI toolkit for network reliability engineers.

    \b
    Commands:
      config     Generate vendor-specific device configurations
      peering    Query PeeringDB for ASN and IX information
      rpki       Validate BGP announcements against RPKI ROAs
      inventory  Collect device inventory via SSH
      console    Connect to device console via NetBox + jump host
    """
    pass


from netcli.config.generator import config
from netcli.peering.peeringdb import peering
from netcli.rpki.validator import rpki
from netcli.inventory.collector import inventory
from netcli.console.connector import console

cli.add_command(config)
cli.add_command(peering)
cli.add_command(rpki)
cli.add_command(inventory)
cli.add_command(console)
