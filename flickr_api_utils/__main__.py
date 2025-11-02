import click

from .album import album
from .local import local
from .photo import photo
from .upload import upload


@click.group(context_settings={"show_default": True})
@click.version_option()
def cli():
    pass


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
