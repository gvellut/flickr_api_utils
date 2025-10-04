"""Tag management commands."""
import click
from addict import Dict as Addict

from .api_auth import auth_flickr
from .flickr_utils import get_photos
from .url_utils import extract_album_id, extract_photo_id


@click.group()
def tag():
    """Tag management commands."""
    pass


@tag.command("remove")
@click.option(
    "--album",
    required=True,
    help="Album ID or URL to process",
)
@click.option(
    "--tag",
    "tag_to_remove",
    required=True,
    help="Tag to remove from photos",
)
@click.option(
    "--start-id",
    help="Photo ID or URL to start from (inclusive)",
)
@click.option(
    "--end-id",
    help="Photo ID or URL to end at (inclusive)",
)
def remove(album, tag_to_remove, start_id, end_id):
    """Remove a tag from photos in an album.
    
    This is useful when there's a bug in the Flickr UI where you cannot
    batch delete tags within the camera roll.
    """
    flickr = auth_flickr()
    
    album_id = extract_album_id(album)
    if start_id:
        start_id = extract_photo_id(start_id)
    if end_id:
        end_id = extract_photo_id(end_id)
    
    photos = get_photos(flickr, album_id)
    
    is_process = False
    for photo in photos:
        if photo.id == end_id:
            break
        
        if photo.id == start_id:
            is_process = True
        
        if not is_process:
            continue
        
        info = Addict(flickr.photos.getInfo(photo_id=photo.id))
        for tag in info.photo.tags.tag:
            if tag["raw"] == tag_to_remove:
                tag_id_to_remove = tag.id
                resp = flickr.photos.removeTag(tag_id=tag_id_to_remove)
                click.echo(f"Removed tag '{tag_to_remove}' from photo {photo.id}")
                break
