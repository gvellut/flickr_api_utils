# Migration Guide: Old Scripts → New CLI

This guide helps you transition from the old standalone scripts to the new unified CLI.

## Quick Migration Table

| Old Script | New Command |
|------------|-------------|
| `python flickr_api_utils/list_albums.py` | `python -m flickr_api_utils album list` |
| `python flickr_api_utils/delete_album.py` | `python -m flickr_api_utils album delete ALBUM_ID` |
| `python flickr_api_utils/album_to_top.py` | `python -m flickr_api_utils album move-to-top ALBUM_ID` |
| `python flickr_api_utils/reorder_albums.py` | `python -m flickr_api_utils album reorder` |
| `python flickr_api_utils/reorder_photos_in_album.py` | `python -m flickr_api_utils album reorder-photos ALBUM_ID` |
| `python flickr_api_utils/remove_photos_from_album.py` | `python -m flickr_api_utils album remove-photos ALBUM_ID` |
| `python flickr_api_utils/info_albums.py` | `python -m flickr_api_utils album info` |
| `python flickr_api_utils/download.py` | `python -m flickr_api_utils photo download` |
| `python flickr_api_utils/replace_photos.py` | `python -m flickr_api_utils photo replace` |
| `python flickr_api_utils/list_photos_taken_at.py` | `python -m flickr_api_utils photo list-by-date` |
| `python flickr_api_utils/find_replace.py` | `python -m flickr_api_utils photo find-replace` |
| `python flickr_api_utils/find_replace_photostream.py` | `python -m flickr_api_utils photo find-replace-photostream` |
| `python flickr_api_utils/correctflickrdate.py` | `python -m flickr_api_utils photo correct-date` |
| `python flickr_api_utils/removetag.py` | `python -m flickr_api_utils tag remove` |
| `python flickr_api_utils/crop43.py` | `python -m flickr_api_utils local crop43` |
| `python flickr_api_utils/copy_sd.py` | `python -m flickr_api_utils local copy-sd` |
| `python flickr_api_utils/copy_zoom_to_std.py` | `python -m flickr_api_utils local copy-zoom-to-std` |
| `python flickr_api_utils/blog_utils/to_markdown.py` | `python -m flickr_api_utils blog to-markdown` |
| `python flickr_api_utils/upload.py` | `python -m flickr_api_utils upload` |

## Key Changes

### 1. No More Hardcoded Variables

**Old Way:**
```python
# Edit the script file
album = "72177720318026202"
output_folder = "laetitia"
```

**New Way:**
```bash
# Pass as command-line options
python -m flickr_api_utils photo download \
  --album 72177720318026202 \
  --output laetitia
```

### 2. Flickr URLs Supported

**Old Way:**
```python
# Only IDs worked
album_id = "72177720318026202"
```

**New Way:**
```bash
# Both URLs and IDs work
python -m flickr_api_utils album delete 72177720318026202
# OR
python -m flickr_api_utils album delete https://www.flickr.com/photos/o_0/albums/72177720318026202
```

### 3. Consistent Option Names

All commands use consistent names:
- `--album` for album ID/URL
- `--start-id` for starting photo
- `--end-id` for ending photo
- `--yes` to skip confirmations

### 4. Help is Built-In

**Old Way:**
```bash
# Read the script source code to understand options
```

**New Way:**
```bash
# Get help for any command
python -m flickr_api_utils photo download --help
```

## Detailed Migration Examples

### Example 1: List Albums

**Old:**
```python
# flickr_api_utils/list_albums.py
from .api_auth import auth_flickr
flickr = auth_flickr()
# ... hardcoded logic ...
```

**New:**
```bash
python -m flickr_api_utils album list
# or with options
python -m flickr_api_utils album list --sort-by title
```

### Example 2: Download Photos

**Old:**
```python
# Edit download.py
album = "72177720318026202"
output_folder = "laetitia"
start_id = None
end_id = None
# Then run: python flickr_api_utils/download.py
```

**New:**
```bash
python -m flickr_api_utils photo download \
  --album 72177720318026202 \
  --output laetitia \
  --start-id 54828191514 \
  --end-id 54828191520
```

### Example 3: Remove Tag

**Old:**
```python
# Edit removetag.py
album = "72157720209505213"
start_id = "51730055105"
end_id = "51730863735"
tag_to_remove = "naves-parmelan"
# Then run: python flickr_api_utils/removetag.py
```

**New:**
```bash
python -m flickr_api_utils tag remove \
  --album 72157720209505213 \
  --tag naves-parmelan \
  --start-id 51730055105 \
  --end-id 51730863735
```

### Example 4: Upload Photos

**Old:**
```bash
python flickr_api_utils/upload.py complete --folder /path --album 123
```

**New:**
```bash
python -m flickr_api_utils upload complete --folder /path --album 123
```

(Upload commands mostly unchanged except for URL support)

## Benefits of the New CLI

1. **No Code Editing**: All parameters via command line
2. **Better Documentation**: Built-in help for all commands
3. **URL Support**: Accept Flickr URLs anywhere
4. **Consistent Interface**: Same patterns across all commands
5. **Easier Debugging**: VS Code launch configurations included
6. **Grouped Commands**: Logical organization by function

## Need More Help?

- Run `python -m flickr_api_utils --help` to see all commands
- Run `python -m flickr_api_utils COMMAND --help` for command-specific help
- See [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) for detailed examples
- Check [launch.sample.json](launch.sample.json) for VS Code configurations
