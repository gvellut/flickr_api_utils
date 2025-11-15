import logging
import os
import sys

import click
import coloredlogs

from .album import album
from .local import local
from .photo import photo
from .upload import upload


def setup_logging(logger):
    if os.getenv("DEBUG") == "1":
        level = logging.DEBUG
    else:
        level = logging.INFO

    coloredlogs.install(
        level=level,
        logger=logger,
        isatty=True,
        fmt="%(asctime)s %(levelname)-8s %(message)s",
        stream=sys.stdout,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@click.group(context_settings={"show_default": True})
@click.version_option()
def cli():
    logger = logging.getLogger(__package__)
    setup_logging(logger)


cli.add_command(photo)
cli.add_command(album)
cli.add_command(local)
cli.add_command(upload)

if __name__ == "__main__":
    try:
        cli()
    except click.exceptions.Abort:
        # Click raises this on Ctrl+C, and it prints "Aborted!".
        # We can pass to let the script exit cleanly.
        pass
