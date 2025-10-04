"""Allow running the package as a module: python -m flickr_api_utils"""
from .cli import cli

if __name__ == "__main__":
    cli()
