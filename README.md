# Flickr API Utilities

Command-line utilities for managing photos and albums on Flickr.

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
uv sync
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

When the Flickr authorization opens in the browser and you accept, the page will communicate with the script to transmit the token. It will be cached for later in the `.flickr` folder in the project (listed in `.gitignore`). That folder can be deleted to clear the cache and force a relogin.

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
- **upload**: Upload photos to Flickr (complete workflow, resume, diff)
- **local**: Local file operations (crop images, copy from SD card)


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

## Launch Upload with VSCode

Added to launch config:

```json
"envFile": "${workspaceFolder}/upload_params/plate_sixtfac.env"
```

In `<params>.env`:

```sh
FAU_FOLDER="/Volumes/CrucialX8/photos/20250807_plate_sixtfac/xs20"
FAU_CREATE_ALBUM=1
FAU_ALBUM_NAME="Randonnée des Grandes Platières à Sixt par les Gorges de Sales"
# FAU_ALBUM_ID="https://www.flickr.com/photos/o_0/albums/72177720329227813"
FAU_ARCHIVE=1
```

Switch as needed.

## Other Resources

Find NSID by URL: https://www.flickr.com/services/api/flickr.urls.lookupUser.html
