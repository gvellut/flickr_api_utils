# Flickr API Utils - Usage Examples

This document provides detailed examples of using the flickr-api-utils CLI.

## Getting Started

```bash
# Show all available commands
python -m flickr_api_utils --help

# Show help for a specific command group
python -m flickr_api_utils photo --help

# Show help for a specific command
python -m flickr_api_utils photo download --help
```

## Photo Management

### Download Photos from an Album

```bash
# Using album URL
python -m flickr_api_utils photo download \
  --album https://www.flickr.com/photos/o_0/albums/72177720318026202 \
  --output ./my_downloads

# Using album ID only
python -m flickr_api_utils photo download \
  --album 72177720318026202 \
  --output ./my_downloads

# Download with start and end photo IDs
python -m flickr_api_utils photo download \
  --album 72177720318026202 \
  --output ./my_downloads \
  --start-id 54828191514 \
  --end-id 54828191520
```

### Replace Photos in an Album

Match photos by EXIF date taken and replace them with local files:

```bash
python -m flickr_api_utils photo replace \
  --album 72157719125798869 \
  --folder /path/to/replacement/photos \
  --pattern "DSCF*.JPG"
```

### List Photos by Date

```bash
python -m flickr_api_utils photo list-by-date \
  --date 2024-03-15 \
  --limit 10
```

### Find and Replace in Photo Titles

```bash
# In an album
python -m flickr_api_utils photo find-replace \
  --album 72177720329191084 \
  --start-id 54802861875 \
  --end-id 54802862180 \
  --find "Varzeron" \
  --replace-with "Varzéron"

# In your photostream
python -m flickr_api_utils photo find-replace-photostream \
  --start-id 54801998889 \
  --end-id 54802009228 \
  --find "Pac" \
  --replace-with "Parc"
```

### Correct Date Taken

Fix bad "date taken" for photos beyond the 24-hour shift limit in Flickr Organizr:

```bash
python -m flickr_api_utils photo correct-date \
  --start-id 30540419 \
  --end-id 55899593 \
  --min-date "2005-03-30 14:05" \
  --margin-minutes 231
```

## Album Management

### List All Albums

```bash
# Sort by date (default)
python -m flickr_api_utils album list

# Sort by title
python -m flickr_api_utils album list --sort-by title
```

### Delete an Album

```bash
python -m flickr_api_utils album delete 72157713509133748 --yes
```

### Move Album to Top

```bash
python -m flickr_api_utils album move-to-top \
  https://www.flickr.com/photos/o_0/albums/72177720325191036
```

### Reorder Albums

Reorder albums by the most common photo date in each album:

```bash
python -m flickr_api_utils album reorder \
  --start-album 72177720324434515
```

### Reorder Photos in Album

Sort photos by date taken:

```bash
python -m flickr_api_utils album reorder-photos 72177720308609341
```

### Remove Photos from Album

```bash
python -m flickr_api_utils album remove-photos \
  72177720317654892 \
  --start-id 53812610982 \
  --yes
```

### Album Info

Display album information sorted by various attributes:

```bash
python -m flickr_api_utils album info \
  --start-album 72157714081800731 \
  --sort-by count_views \
  --order desc \
  --show-attrs "title._content,id,count_views,count_photos"
```

## Tag Management

### Remove Tags

Remove a specific tag from photos in an album:

```bash
python -m flickr_api_utils tag remove \
  --album 72157720209505213 \
  --tag "old-tag" \
  --start-id 51730055105 \
  --end-id 51730863735
```

## Upload Photos

### Complete Upload Workflow

Upload photos with metadata from XMP sidecar files:

```bash
python -m flickr_api_utils upload complete \
  --folder /path/to/photos \
  --label Accepted \
  --public \
  --album 72157720209505213 \
  --create-album \
  --album-name "My New Album" \
  --album-description "Photos from my trip" \
  --parallel 4 \
  --yes \
  --archive
```

### Finish Started Uploads

Process recently uploaded photos (add to album, set visibility):

```bash
python -m flickr_api_utils upload finish_started \
  --folder /path/to/photos \
  --last 10 \
  --album 72157720209505213 \
  --public \
  --parallel 4 \
  --yes
```

### Upload Missing Photos

Find and upload photos that are in local folder but not in Flickr album:

```bash
python -m flickr_api_utils upload diff \
  --folder /path/to/photos \
  --label Uploaded \
  --album 72157720209505213 \
  --yes
```

## Local File Operations

### Crop Images to 4:3

Crop vertical images to 4:3 aspect ratio:

```bash
python -m flickr_api_utils local crop43 \
  /path/to/input \
  /path/to/output
```

### Copy from SD Card

Automatically detect SD card and copy photos:

```bash
# Copy today's photos
python -m flickr_api_utils local copy-sd \
  --name my_photos \
  --date TD

# Copy specific date
python -m flickr_api_utils local copy-sd \
  --name vacation \
  --date 20240315

# Don't eject SD card after copying
python -m flickr_api_utils local copy-sd \
  --name my_photos \
  --date TD \
  --no-eject
```

### Copy Zoom to Standard

Copy photos from zoom camera folder to standard folder:

```bash
python -m flickr_api_utils local copy-zoom-to-std 20240425_feracheval
```

## Blog Utilities

### Generate Markdown for Hugo

Generate markdown image links from Flickr URLs:

```bash
python -m flickr_api_utils blog to-markdown \
  --posts-dir /path/to/hugo/content/post \
  --urls-file /path/to/flickr_urls.txt
```

The urls file should contain one Flickr photo URL per line:
```
https://www.flickr.com/photos/o_0/54828191514/in/dateposted/
https://www.flickr.com/photos/o_0/54828191515/in/dateposted/
```

## Using Flickr URLs vs IDs

Most commands accept both Flickr URLs and IDs:

```bash
# These are equivalent:
python -m flickr_api_utils album delete 72157720209505213
python -m flickr_api_utils album delete https://www.flickr.com/photos/o_0/albums/72157720209505213

# Photo URLs also work (with or without path suffix):
python -m flickr_api_utils photo download \
  --album 72157720209505213 \
  --start-id https://www.flickr.com/photos/o_0/54828191514/in/dateposted/
```

## Tips

1. Use `--help` on any command to see all available options
2. Use `--yes` flag to skip confirmation prompts in scripts
3. Most commands support `--start-id` and `--end-id` for batch operations
4. The `--parallel` option in upload commands controls concurrency
5. Launch configurations in `launch.sample.json` provide ready-to-use examples
