# ACTION: User-Specific Aspects and Recommendations

This document lists all user-specific hardcoded values, paths, and configurations identified in the `flickr_api_utils` package. For each item, recommendations are provided for how to make them configurable.

---

## 1. API Authentication (`api_auth.py`)

### 1.1 API Key File Path

**Location:** `api_auth.py:17`

```python
with open("api_key.json") as f:
```

**Issue:** The API key file is expected to be named `api_key.json` and located in the current working directory.

**Recommendation:**
- Add a CLI option `--api-key-file` with an environment variable `FAU_API_KEY_FILE`.
- Default to `api_key.json` in the current directory if not specified.
- Add to the main CLI group in `__main__.py`:
  ```python
  @click.option(
      "--api-key-file",
      default="api_key.json",
      envvar="FAU_API_KEY_FILE",
      help="Path to the Flickr API key JSON file",
  )
  ```
- Pass the path to `auth_flickr()` function.

### 1.2 Token Cache Location

**Location:** `api_auth.py:27`

```python
token_cache_location=Path("./.flickr").resolve(),
```

**Issue:** The OAuth token cache is stored in `.flickr` folder relative to the current directory.

**Recommendation:**
- Add an environment variable `FAU_TOKEN_CACHE_DIR`.
- Default to `~/.flickr` (user home directory) or `$XDG_CACHE_HOME/flickr_api_utils`.
- Add CLI option `--token-cache-dir` with fallback to environment variable.

---

## 2. Upload Module (`upload.py`)

### 2.1 Base Photo Directory

**Location:** `upload.py:43`

```python
BASE_PHOTO_DIR = "/Volumes/CrucialX8/photos/"
```

**Issue:** This is a macOS-specific external drive path, hardcoded for the developer's personal setup.

**Recommendation:**
- Add environment variable `FAU_BASE_PHOTO_DIR`.
- Add CLI option `--base-photo-dir` to the `archive` and `standard` commands.
- Update `_copy_to_uploaded()` to accept the base directory as a parameter.

### 2.2 Uploaded Archive Directory Name

**Location:** `upload.py:44`

```python
UPLOADED_DIR = "____uploaded"
```

**Issue:** The archive subfolder name is hardcoded with a specific naming convention.

**Recommendation:**
- Add environment variable `FAU_UPLOADED_DIR`.
- Default to `____uploaded` if not specified.
- Used in `_copy_to_uploaded()` and `local.py` for archive operations.

### 2.3 Zoom Camera Directory and Prefix

**Location:** `upload.py:45-46`

```python
ZOOM_DIR = "tz95"
ZOOM_PREFIX = "P"
```

**Issue:** These are specific to the developer's camera naming conventions (Panasonic TZ95 zoom camera with "P" prefix for files).

**Recommendation:**
- Add environment variables:
  - `FAU_ZOOM_DIR` (default: `tz95`)
  - `FAU_ZOOM_PREFIX` (default: `P`)
- These are used in `move_zoom_photos()` and `local.py`.

### 2.4 Default Filter Label

**Location:** `upload.py:199`

```python
@click.option("--label", "filter_label", default="Accepted", help="Label to filter on")
```

**Issue:** The default XMP label filter "Accepted" is hardcoded.

**Recommendation:**
- Add environment variable `FAU_FILTER_LABEL`.
- Already has CLI option, just add envvar support:
  ```python
  @click.option("--label", "filter_label", default="Accepted", envvar="FAU_FILTER_LABEL", ...)
  ```

### 2.5 Upload Concurrency Settings

**Location:** `upload.py:38-39`

```python
UPLOAD_CONCURRENCY = 2
QUICK_CONCURRENCY = 1
```

**Issue:** Concurrency settings are hardcoded; users may want different values based on their network/machine.

**Recommendation:**
- `UPLOAD_CONCURRENCY` already has `--parallel` option.
- Add environment variable `FAU_UPLOAD_CONCURRENCY` as default for `--parallel`.
- Add environment variable `FAU_QUICK_CONCURRENCY` for API operations concurrency.

---

## 3. Local Operations (`local.py`)

### 3.1 Output Parent Folder for SD Card Copy

**Location:** `local.py:298`

```python
output_parent_folder = "/Volumes/CrucialX8/photos"
```

**Issue:** Hardcoded macOS external drive path for the destination of SD card copies.

**Recommendation:**
- Add environment variable `FAU_OUTPUT_PARENT_FOLDER`.
- Add CLI option `--output-folder` to `copy-sd` command.
- Default to the environment variable if not provided via CLI.

### 3.2 Camera/Media Folder Mapping

**Location:** `local.py:299-305`

```python
MEDIA_FOLDER_MAPPING = {
    "LUMIX": "tz95",
    "XS10": "xs10",
    "RX100M7": "rx100",
    "XS20": "xs20",
}
```

**Issue:** This mapping is specific to the developer's camera collection and naming conventions.

**Recommendation:**
- Create a configuration file `cameras.toml` or `cameras.json`.
- Add environment variable `FAU_CAMERAS_CONFIG` pointing to the config file.
- Add CLI option `--cameras-config` to override.
- Default config location: `~/.config/flickr_api_utils/cameras.toml`.
- Example `cameras.toml`:
  ```toml
  [cameras]
  LUMIX = "tz95"
  XS10 = "xs10"
  RX100M7 = "rx100"
  XS20 = "xs20"
  ```
- Add a command `local config-cameras` to manage the mapping.

### 3.3 Copy Zoom to Std Command Paths

**Location:** `local.py:253-255`

```python
BASE_DIR = "/Volumes/CrucialX8/photos"
folder_std = "xs20"
folder_zoom = "tz95"
```

**Issue:** Hardcoded paths and folder names for camera-specific operations.

**Recommendation:**
- Use `FAU_BASE_PHOTO_DIR` environment variable (same as upload module).
- Add CLI options `--std-folder` and `--zoom-folder` to override defaults.
- Read defaults from camera configuration file.

### 3.4 Uploaded Directory Reference

**Location:** `local.py:20`

```python
from .upload import UPLOADED_DIR, ZOOM_DIR, ZOOM_PREFIX
```

**Issue:** These values are imported from upload.py, creating coupling. Making upload.py configurable requires making local.py configurable too.

**Recommendation:**
- Create a shared configuration module `config.py` that reads from environment variables and/or config file.
- Both `upload.py` and `local.py` import from `config.py`.

---

## 4. Scripts (`scripts/gegl_exposure.sh`)

### 4.1 Hardcoded Paths

**Location:** `scripts/gegl_exposure.sh:6-7`

```bash
INPUT_DIR="/Volumes/CrucialX8/photos/20241225_geneve/gegl"
OUTPUT_DIR="/Volumes/CrucialX8/photos/20241225_geneve/gegl_exp"
```

**Issue:** Script has hardcoded absolute paths.

**Recommendation:**
- Convert to command-line arguments or environment variables.
- Suggested usage: `gegl_exposure.sh <input_dir> <output_dir>`.
- Or read from environment: `INPUT_DIR=${1:-$GEGL_INPUT_DIR}`.

### 4.2 Processing Parameters

**Location:** `scripts/gegl_exposure.sh:8-10`

```bash
EXPOSURE_VAL="0.80"
BLACK_LEVEL_VAL="0.02"
JPG_QUALITY="90"
```

**Issue:** Image processing parameters are hardcoded.

**Recommendation:**
- Add command-line options for these values.
- Or read from environment variables with defaults:
  ```bash
  EXPOSURE_VAL="${GEGL_EXPOSURE:-0.80}"
  BLACK_LEVEL_VAL="${GEGL_BLACK_LEVEL:-0.02}"
  JPG_QUALITY="${GEGL_JPG_QUALITY:-90}"
  ```

---

## 5. Upload Parameters Template (`upload_params/__template.env`)

### 5.1 Template Enhancement

**Location:** `upload_params/__template.env`

**Issue:** The template is minimal and doesn't include all available environment variables.

**Recommendation:**
- Expand the template to include all new environment variables:
  ```bash
  # Required
  FAU_FOLDER=""
  
  # Album options
  FAU_CREATE_ALBUM=0
  FAU_ALBUM_NAME=""
  FAU_ALBUM_ID=""
  FAU_ALBUM_DESCRIPTION=""
  
  # Upload behavior
  FAU_ARCHIVE=0
  FAU_FILTER_LABEL="Accepted"
  FAU_UPLOAD_CONCURRENCY=2
  
  # Paths (optional overrides)
  FAU_BASE_PHOTO_DIR=""
  FAU_UPLOADED_DIR=""
  FAU_API_KEY_FILE=""
  FAU_TOKEN_CACHE_DIR=""
  
  # Camera settings (optional)
  FAU_ZOOM_DIR=""
  FAU_ZOOM_PREFIX=""
  FAU_CAMERAS_CONFIG=""
  FAU_OUTPUT_PARENT_FOLDER=""
  ```

---

## 6. Default Album Description

**Location:** `upload_params/__template.env:3`

```bash
FAU_ALBUM_NAME="Randonnée au "
```

**Issue:** French hiking description is a user preference.

**Recommendation:**
- Remove default text from template.
- Document that users should customize this.

---

## 7. Recommended Configuration System

### 7.1 Create a Central Configuration Module

Create `flickr_api_utils/config.py`:

```python
import os
from pathlib import Path
import toml

# Default configuration values
DEFAULTS = {
    "api_key_file": "api_key.json",
    "token_cache_dir": str(Path.home() / ".flickr"),
    "base_photo_dir": "",
    "uploaded_dir": "____uploaded",
    "zoom_dir": "tz95",
    "zoom_prefix": "P",
    "filter_label": "Accepted",
    "upload_concurrency": 2,
    "quick_concurrency": 1,
    "output_parent_folder": "",
    "cameras": {
        "LUMIX": "tz95",
        "XS10": "xs10",
        "RX100M7": "rx100",
        "XS20": "xs20",
    },
}

def load_config():
    """Load configuration from environment variables and optional config file."""
    config = DEFAULTS.copy()
    
    # Check for config file
    config_file = os.getenv("FAU_CONFIG_FILE", str(Path.home() / ".config/flickr_api_utils/config.toml"))
    if Path(config_file).exists():
        with open(config_file) as f:
            file_config = toml.load(f)
            config.update(file_config)
    
    # Environment variables override
    env_mappings = {
        "FAU_API_KEY_FILE": "api_key_file",
        "FAU_TOKEN_CACHE_DIR": "token_cache_dir",
        "FAU_BASE_PHOTO_DIR": "base_photo_dir",
        "FAU_UPLOADED_DIR": "uploaded_dir",
        "FAU_ZOOM_DIR": "zoom_dir",
        "FAU_ZOOM_PREFIX": "zoom_prefix",
        "FAU_FILTER_LABEL": "filter_label",
        "FAU_UPLOAD_CONCURRENCY": "upload_concurrency",
        "FAU_QUICK_CONCURRENCY": "quick_concurrency",
        "FAU_OUTPUT_PARENT_FOLDER": "output_parent_folder",
        "FAU_CAMERAS_CONFIG": "cameras_config",
    }
    
    for env_var, config_key in env_mappings.items():
        value = os.getenv(env_var)
        if value is not None:
            config[config_key] = value
    
    return config
```

### 7.2 Add Configuration File Support

Create default config file location: `~/.config/flickr_api_utils/config.toml`

Example config file:

```toml
# Flickr API Utils Configuration

[paths]
api_key_file = "~/.flickr/api_key.json"
token_cache_dir = "~/.flickr"
base_photo_dir = "/path/to/your/photos"
uploaded_dir = "____uploaded"
output_parent_folder = "/path/to/your/photos"

[cameras]
LUMIX = "tz95"
XS10 = "xs10"
RX100M7 = "rx100"
XS20 = "xs20"
# Add your own cameras:
# SONY = "sony"

[upload]
filter_label = "Accepted"
upload_concurrency = 2
zoom_dir = "tz95"
zoom_prefix = "P"
```

### 7.3 Add a Config Management Command

Add a new command group `config` to manage configuration:

```python
@click.group("config")
def config():
    """Configuration management."""
    pass

@config.command("show")
def show_config():
    """Display current configuration."""
    pass

@config.command("init")
def init_config():
    """Create a default configuration file."""
    pass

@config.command("set")
@click.argument("key")
@click.argument("value")
def set_config(key, value):
    """Set a configuration value."""
    pass
```

---

## 8. Summary of Environment Variables to Add

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `FAU_CONFIG_FILE` | `~/.config/flickr_api_utils/config.toml` | Path to configuration file |
| `FAU_API_KEY_FILE` | `api_key.json` | Path to Flickr API key JSON file |
| `FAU_TOKEN_CACHE_DIR` | `~/.flickr` | Directory for OAuth token cache |
| `FAU_BASE_PHOTO_DIR` | (none) | Base directory for photos |
| `FAU_UPLOADED_DIR` | `____uploaded` | Subdirectory name for archived uploads |
| `FAU_ZOOM_DIR` | `tz95` | Subdirectory for zoom camera photos |
| `FAU_ZOOM_PREFIX` | `P` | File prefix for zoom camera photos |
| `FAU_FILTER_LABEL` | `Accepted` | Default XMP label filter |
| `FAU_UPLOAD_CONCURRENCY` | `2` | Number of parallel uploads |
| `FAU_QUICK_CONCURRENCY` | `1` | Concurrency for quick API operations |
| `FAU_OUTPUT_PARENT_FOLDER` | (none) | Parent folder for SD card copy output |
| `FAU_CAMERAS_CONFIG` | (none) | Path to cameras configuration file |

---

## 9. Implementation Priority

### High Priority (Breaking for other users)
1. `BASE_PHOTO_DIR` - Required for archive functionality
2. `output_parent_folder` - Required for SD card copy
3. `MEDIA_FOLDER_MAPPING` - Required for SD card copy
4. `api_key.json` path - Users may want different locations

### Medium Priority (Convenience)
5. Token cache location
6. Default filter label
7. Upload concurrency defaults
8. Configuration file support

### Low Priority (Edge cases)
9. `ZOOM_DIR` and `ZOOM_PREFIX` - Only affects users with similar camera setups
10. `UPLOADED_DIR` name - Cosmetic preference
11. GEGL script parameters

---

## 10. Additional Recommendations

### 10.1 README Documentation Update

Update `README.md` to document:
- All available environment variables
- Configuration file location and format
- Example configuration for different setups

### 10.2 Example Configurations

Create `examples/` directory with sample configurations:
- `examples/config.toml.example`
- `examples/cameras.toml.example`
- `examples/upload_params.env.example`

### 10.3 Validation and Error Messages

Add helpful error messages when required paths are not configured:
```python
if not config.base_photo_dir:
    raise click.ClickException(
        "FAU_BASE_PHOTO_DIR not configured. "
        "Set it in your config file or via environment variable."
    )
```
