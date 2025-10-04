import re


def extract_photo_id(value: str) -> str:
    """Extract photo ID from a Flickr URL or return the ID directly.

    Supports URLs like:
    - https://www.flickr.com/photos/o_0/54828191514/
    - https://www.flickr.com/photos/o_0/54828191514/in/dateposted/
    - 54828191514

    Args:
        value: Flickr URL or photo ID

    Returns:
        Photo ID as a string

    Raises:
        ValueError: If the value is not a valid Flickr URL or photo ID
    """
    # If it's just a numeric ID, return it
    if value.isdigit():
        return value

    # Try to extract from URL
    # Pattern matches: /photos/{user}/{photo_id}/ with optional path after
    regex = r"flickr\.com/photos/[^/]+/(\d+)"
    m = re.search(regex, value)
    if m:
        return m.group(1)

    raise ValueError(f"Not a valid Flickr photo URL or ID: {value}")


def extract_album_id(value: str) -> str:
    """Extract album/photoset ID from a Flickr URL or return the ID directly.

    Supports URLs like:
    - https://www.flickr.com/photos/o_0/albums/72177720318026202
    - https://www.flickr.com/photos/o_0/sets/72177720318026202
    - 72177720318026202

    Args:
        value: Flickr album URL or album ID

    Returns:
        Album ID as a string

    Raises:
        ValueError: If the value is not a valid Flickr album URL or ID
    """
    # If it's just a numeric ID, return it
    if value.isdigit():
        return value

    # Try to extract from URL
    regex = r"flickr\.com/photos/[^/]+/(?:albums|sets)/(\d+)"
    m = re.search(regex, value)
    if m:
        return m.group(1)

    raise ValueError(f"Not a valid Flickr album URL or ID: {value}")
