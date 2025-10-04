# Flickr API Utilities

Command-line utilities for managing photos, albums, and tags on Flickr.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Install dependencies
uv sync

# Or install the package
uv pip install -e .
```

## API Key

You need a JSON file named `api_key.json` in your working directory with your Flickr API key and secret:

```json
{
    "key": "your_api_key_here",
    "secret": "your_api_secret_here"
}
```

To get API credentials, visit: https://www.flickr.com/services/api/misc.api_keys.html

## Usage

The utilities are organized into command groups:

```bash
# Run as a module
python -m flickr_api_utils --help

# Or if installed
flickr-api-utils --help
```

### Command Groups

- **photo**: Photo management (download, replace, search, correct dates)
- **album**: Album management (list, create, delete, reorder)
- **tag**: Tag management (remove tags from photos)
- **upload**: Upload photos to Flickr (complete workflow, resume, diff)
- **local**: Local file operations (crop images, copy from SD card)
- **blog**: Blog utilities (generate markdown from Flickr photos)

### Examples

```bash
# List all albums
python -m flickr_api_utils album list

# Download photos from an album
python -m flickr_api_utils photo download \
  --album https://www.flickr.com/photos/user/albums/72177720318026202 \
  --output ./downloads

# Upload photos
python -m flickr_api_utils upload complete \
  --folder ./photos \
  --album 72157720209505213 \
  --public

# Remove a tag from photos in an album
python -m flickr_api_utils tag remove \
  --album 72157720209505213 \
  --tag "old-tag"

# Crop images to 4:3 aspect ratio
python -m flickr_api_utils local crop43 ./input ./output
```

### Accepting Flickr URLs

Most commands that accept album or photo IDs also accept Flickr URLs. For example:

```bash
# These are equivalent:
python -m flickr_api_utils album delete 72157720209505213
python -m flickr_api_utils photo download --album https://www.flickr.com/photos/o_0/albums/72157720209505213

# Photo URLs work too (with or without the /in/... suffix):
python -m flickr_api_utils photo download --start-id https://www.flickr.com/photos/o_0/54828191514/in/dateposted/
python -m flickr_api_utils photo download --start-id 54828191514
```

### Launch Configurations

See `launch.sample.json` for VS Code launch configurations with example parameters for all commands.

## Development

```bash
# Run linter
uv run ruff check flickr_api_utils/

# Run formatter
uv run ruff format flickr_api_utils/
```

## Utility Scripts

The following scripts in `flickr_api_utils/` are one-off utilities with hardcoded paths for specific use cases:

- `copy_all.py` - Copy files between folders
- `find_replace_local.py` - Find/replace in local file XMP metadata
- `list_not_uploaded.py` - List folders not matching a pattern
- `upload_async_test.py` - Test script for async uploads

These are not part of the main CLI and should be edited directly for your specific use case.

## Other Resources

Find NSID by URL: https://www.flickr.com/services/api/flickr.urls.lookupUser.html

## Python Version

Requires Python 3.13 or later.
