"""Photo management commands."""
import os
import re
import shutil
import traceback
from datetime import datetime
from fnmatch import fnmatch

import click
import piexif
import requests
from addict import Dict as Addict

from .api_auth import auth_flickr
from .flickr_utils import get_photos, get_photostream_photos
from .url_utils import extract_album_id, extract_photo_id


@click.group()
def photo():
    """Photo management commands."""
    pass


@photo.command()
@click.option(
    "--album",
    required=True,
    help="Album ID or URL to download photos from",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(),
    help="Output folder path",
)
@click.option(
    "--start-id",
    help="Photo ID or URL to start processing from (inclusive)",
)
@click.option(
    "--end-id",
    help="Photo ID or URL to end processing at (inclusive)",
)
def download(album, output, start_id, end_id):
    """Download photos from a Flickr album.
    
    Photos are renamed with date taken and photo ID.
    """
    flickr = auth_flickr()
    
    album_id = extract_album_id(album)
    if start_id:
        start_id = extract_photo_id(start_id)
    if end_id:
        end_id = extract_photo_id(end_id)
    
    images = get_photos(flickr, album_id, privacy_filter=3)
    
    os.makedirs(output, exist_ok=True)
    
    is_process = False
    for image in images:
        if start_id is None or image.id == start_id:
            is_process = True
        
        if not is_process:
            continue
        
        try:
            datetaken = datetime.strptime(image.datetaken, "%Y-%m-%d %H:%M:%S")
            formatted_date = datetaken.strftime("%Y%m%d_%H%M%S")
            old_path = os.path.join(output, f"{image.id}.jpg")
            new_path = os.path.join(output, f"{formatted_date}_{image.id}.jpg")
            if os.path.exists(old_path):
                shutil.move(old_path, new_path)
            else:
                url = image.url_o
                click.echo(f"Downloading {url}...")
                resp = requests.get(url)
                resp.raise_for_status()
                with open(new_path, "wb") as f:
                    f.write(resp.content)
        except Exception:
            click.echo("An error occurred", err=True)
            traceback.print_exc()
            continue
        
        # Include photo with end_id in processing
        if end_id is not None and image.id == end_id:
            break


@photo.command()
@click.option(
    "--album",
    required=True,
    help="Album ID or URL containing photos to replace",
)
@click.option(
    "--folder",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Folder containing replacement photos",
)
@click.option(
    "--pattern",
    default="*.JPG",
    help="File pattern to match (e.g., 'DSCF*.JPG')",
)
def replace(album, folder, pattern):
    """Replace photos in an album with local files.
    
    Matches photos by EXIF date taken timestamp.
    """
    flickr = auth_flickr()
    user = Addict(flickr.auth.oauth.checkToken())
    
    album_id = extract_album_id(album)
    
    def make_flickr_photo_url(photo, user_id):
        if photo.pathalias:
            user_path = photo.pathalias
        else:
            user_path = user_id
        return f"https://www.flickr.com/photos/{user_path}/{photo.id}"
    
    photos = list(get_photos(flickr, album_id, extras="date_taken,url_o,path_alias"))
    
    flickr_time_index = {}
    for photo in photos:
        date_taken = photo.datetaken
        flickr_time_index[date_taken] = photo
    
    photo_time_index = {}
    for file_name in os.listdir(folder):
        if fnmatch(file_name, pattern):
            file_path = os.path.join(folder, file_name)
            try:
                exif_data = piexif.load(file_path)
                dt_original = exif_data["Exif"][piexif.ExifIFD.DateTimeOriginal]
                dt_original = dt_original.decode("ascii")
                dt_format_in = "%Y:%m:%d %H:%M:%S"
                dt_original = datetime.strptime(dt_original, dt_format_in)
                dt_format_out = "%Y-%m-%d %H:%M:%S"
                dt_original = datetime.strftime(dt_original, dt_format_out)
                photo_time_index[dt_original] = file_path
            except Exception:
                click.echo(f"Error reading EXIF from {file_path}", err=True)
                continue
    
    for date_taken, file_path in photo_time_index.items():
        if date_taken not in flickr_time_index:
            click.echo(
                f"Photo {file_path} with date {date_taken} not found on Flickr!"
            )
            continue
        flickr_photo = flickr_time_index[date_taken]
        click.echo(
            f"Replace {make_flickr_photo_url(flickr_photo, user.id)} with {file_path}..."
        )
        result = flickr.replace(file_path, flickr_photo.id, format="rest")
        # not parsed as JSON => bytes
        result = result.decode("utf-8", "ignore")
        if 'stat="ok"' not in result:
            click.echo(f"Error uploading: {result}", err=True)


@photo.command("list-by-date")
@click.option(
    "--date",
    required=True,
    help="Date to search for (YYYY-MM-DD)",
)
@click.option(
    "--limit",
    default=5,
    type=int,
    help="Maximum number of results",
)
def list_by_date(date, limit):
    """List photos taken on a specific date."""
    flickr = auth_flickr()
    
    search_result = Addict(
        flickr.photos.search(
            user_id="me",
            min_taken_date=f"{date} 00:00:00",
            max_taken_date=f"{date} 23:59:59",
            per_page=limit,
        )
    )
    
    click.echo(f"Searching {date}...")
    
    for photo in search_result.photos.photo:
        photo = Addict(flickr.photos.getInfo(photo_id=photo.id)).photo
        title = photo.title._content
        owner = photo.owner.nsid
        id_ = photo.id
        url = f"https://flickr.com/photos/{owner}/{id_}"
        click.echo(f"{url} {title}")


@photo.command("find-replace")
@click.option(
    "--album",
    help="Album ID or URL to process (if not provided, uses photostream)",
)
@click.option(
    "--start-id",
    help="Photo ID or URL to start processing from (inclusive)",
)
@click.option(
    "--end-id",
    help="Photo ID or URL to end processing at (inclusive)",
)
@click.option(
    "--find-title",
    help="Text pattern to find in photo titles (regex supported)",
)
@click.option(
    "--replace-title",
    help="Text to replace in photo titles",
)
@click.option(
    "--remove-tag",
    help="Tag to remove from photos",
)
@click.option(
    "--add-tags",
    help="Comma-separated tags to add to photos (e.g., 'tag1,tag2')",
)
@click.option(
    "--sort",
    default="date-posted-asc",
    help="Sort order for photostream (e.g., date-posted-asc, date-posted-desc, date-taken-asc, date-taken-desc). Ignored for albums.",
)
def find_replace_cmd(album, start_id, end_id, find_title, replace_title, remove_tag, add_tags, sort):
    """Find and replace text in photo titles and/or modify tags.
    
    Works on either an album (if --album provided) or photostream (if --album not provided).
    Can perform title replacements (--find-title and --replace-title) and/or
    tag operations (--remove-tag and/or --add-tags).
    
    At least one operation (title replacement or tag modification) must be specified.
    
    For photostream, photos are processed in the order specified by --sort.
    For albums, photos are processed in their album order (as they appear on Flickr).
    """
    flickr = auth_flickr()
    
    # Validate that at least one operation is specified
    if not find_title and not remove_tag and not add_tags:
        raise click.ClickException(
            "At least one operation must be specified: "
            "--find-title/--replace-title, --remove-tag, or --add-tags"
        )
    
    # Validate title replacement options
    if find_title and not replace_title:
        raise click.ClickException("--replace-title is required when --find-title is specified")
    if replace_title and not find_title:
        raise click.ClickException("--find-title is required when --replace-title is specified")
    
    # Extract IDs from URLs if needed
    if start_id:
        start_id = extract_photo_id(start_id)
    if end_id:
        end_id = extract_photo_id(end_id)
    
    # Get photos from album or photostream
    if album:
        # Album mode - use album order
        album_id = extract_album_id(album)
        images = get_photos(flickr, album_id)
        click.echo(f"Processing photos in album {album_id}...")
        
        is_process = False
        for image in images:
            if start_id is None or image.id == start_id:
                is_process = True
            
            if not is_process:
                continue
            
            _process_photo(flickr, image, find_title, replace_title, remove_tag, add_tags)
            
            # Include photo with end_id in processing
            if end_id is not None and image.id == end_id:
                break
    else:
        # Photostream mode - require start and end IDs
        if not start_id or not end_id:
            raise click.ClickException(
                "For photostream mode, both --start-id and --end-id are required"
            )
        
        click.echo(f"Processing photos in photostream (sort: {sort})...")
        images = get_photostream_photos(flickr, start_id, end_id, sort=sort)
        
        for image in images:
            _process_photo(flickr, image, find_title, replace_title, remove_tag, add_tags)


def _process_photo(flickr, image, find_title, replace_title, remove_tag, add_tags):
    """Process a single photo with title replacement and/or tag operations."""
    click.echo(f"Processing {image.id} [{image.title}] ...")
    
    # Title replacement
    if find_title and replace_title:
        title, n = re.subn(find_title, replace_title, image.title)
        if n:
            flickr.photos.setMeta(photo_id=image.id, title=title)
            click.echo(f"  Updated title: {title}")
    
    # Tag operations (need to get full photo info for tags)
    if remove_tag or add_tags:
        info = Addict(flickr.photos.getInfo(photo_id=image.id))
        
        # Remove tag
        if remove_tag:
            for tag in info.photo.tags.tag:
                if tag["raw"] == remove_tag:
                    tag_id_to_remove = tag.id
                    flickr.photos.removeTag(tag_id=tag_id_to_remove)
                    click.echo(f"  Removed tag: {remove_tag}")
                    break
        
        # Add tags
        if add_tags:
            # Format tags with quotes for multi-word tags
            tag_list = [f'"{tag.strip()}"' for tag in add_tags.split(',')]
            tags_str = ' '.join(tag_list)
            flickr.photos.addTags(photo_id=image.id, tags=tags_str)
            click.echo(f"  Added tags: {add_tags}")


@photo.command("correct-date")
@click.option(
    "--start-id",
    required=True,
    help="Photo ID or URL to start from",
)
@click.option(
    "--end-id",
    required=True,
    help="Photo ID or URL to end at",
)
@click.option(
    "--min-date",
    required=True,
    help="Minimum date taken (YYYY-MM-DD HH:MM)",
)
@click.option(
    "--margin-minutes",
    type=int,
    required=True,
    help="Margin in minutes from min date",
)
def correct_date(start_id, end_id, min_date, margin_minutes):
    """Correct date taken for a range of photos.
    
    Used to fix bad "date taken" for photos beyond the max 24 hour shift
    in the Flickr Organizr. Photos before the margin are backdated in
    1-minute increments.
    """
    import dateutil.parser
    from datetime import timedelta
    
    flickr = auth_flickr()
    
    start_photo_id = extract_photo_id(start_id)
    end_photo_id = extract_photo_id(end_id)
    
    photos_uploaded = []
    for photos in get_photostream_photos(
        flickr,
        start_photo_id=start_photo_id,
        end_photo_id=end_photo_id,
        sort="date-posted-asc",
        extras="date_taken",
    ):
        p = Addict(photos)
        p.datetaken = dateutil.parser.isoparse(p.datetaken)
        photos_uploaded.append(p)
    
    min_dt = dateutil.parser.parse(min_date)
    margin_dt = min_dt + timedelta(minutes=margin_minutes)
    fake_date = min_dt
    sorted_photos = list(sorted(photos_uploaded, key=lambda x: x.datetaken))
    
    for photo in sorted_photos:
        taken = photo.datetaken
        
        if taken > margin_dt:
            date_posted = taken
        else:
            date_posted = fake_date
        
        # unixtime
        ts = int(date_posted.timestamp())
        resp = flickr.photos.setDates(photo_id=photo.id, date_posted=ts)
        click.echo(f"Posted {photo.id} {date_posted}")
        
        fake_date += timedelta(minutes=1)
