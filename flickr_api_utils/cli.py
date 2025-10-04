"""Main CLI entry point for flickr-api-utils."""
import click

from .album_commands import album
from .blog_commands import blog
from .local_commands import local
from .photo_commands import photo
from .tag_commands import tag
from .upload import cli as upload_cli


@click.group()
@click.version_option()
def cli():
    """Flickr API utilities for managing photos, albums, tags and more.
    
    Requires a JSON file named 'api_key.json' with your Flickr API key and secret:
    
    \b
    {
        "key": "your_api_key",
        "secret": "your_api_secret"
    }
    """
    pass


# Register command groups
cli.add_command(photo)
cli.add_command(album)
cli.add_command(tag)
cli.add_command(local)
cli.add_command(blog)
# Add upload as a separate top-level group since it's already well-structured
cli.add_command(upload_cli, name="upload")


if __name__ == "__main__":
    cli()
