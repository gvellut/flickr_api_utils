from datetime import datetime
from fnmatch import fnmatch
import logging
import os
import re
import shutil

from addict import Dict as Addict
import click
import piexif
import requests

from .api_auth import auth_flickr
from .base import CatchAllExceptionsCommand
from .flickr_utils import format_tags, get_photos, get_photostream_photos
from .url_utils import extract_album_id, extract_photo_id

logger = logging.getLogger(__name__)


@click.group("photo")
def photo():
    """Photo management commands."""
    pass


@photo.command(cls=CatchAllExceptionsCommand)
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
                logger.info(f"Downloading {url}...")
                resp = requests.get(url)
                resp.raise_for_status()
                with open(new_path, "wb") as f:
                    f.write(resp.content)
        except Exception:
            logger.exception("An error occurred")
            continue

        # Include photo with end_id in processing
        if end_id is not None and image.id == end_id:
            break


@photo.command(cls=CatchAllExceptionsCommand)
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
                logger.error(f"Error reading EXIF from {file_path}")
                continue

    for date_taken, file_path in photo_time_index.items():
        if date_taken not in flickr_time_index:
            logger.info(
                f"Photo {file_path} with date {date_taken} not found on Flickr!"
            )
            continue
        flickr_photo = flickr_time_index[date_taken]
        logger.info(
            f"Replace {make_flickr_photo_url(flickr_photo, user.id)} with "
            f"{file_path}..."
        )
        result = flickr.replace(file_path, flickr_photo.id, format="rest")
        # not parsed as JSON => bytes
        result = result.decode("utf-8", "ignore")
        if 'stat="ok"' not in result:
            raise click.ClickException(f"Error replacing photo: {result}")


@photo.command("list-by-date", cls=CatchAllExceptionsCommand)
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

    logger.info(f"Searching {date}...")

    for photo in search_result.photos.photo:
        photo = Addict(flickr.photos.getInfo(photo_id=photo.id)).photo
        title = photo.title._content
        owner = photo.owner.nsid
        id_ = photo.id
        url = f"https://flickr.com/photos/{owner}/{id_}"
        logger.info(f"{url} {title}")


SORT_PARAMS = [
    "date-posted-asc",
    "date-posted-desc",
    "date-taken-asc",
    "date-taken-desc",
]


@photo.command("find-replace", cls=CatchAllExceptionsCommand)
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
    help=(
        "Text to replace in photo titles. Use with find-title: Regexp re.subn "
        "will be used (so \\1 can be used)"
    ),
)
@click.option(
    "--remove-tag",
    "remove_tags",
    help="Tags to remove from photos",
    multiple=True,
)
@click.option(
    "--replace-tag",
    "replace_tags",
    help="Tags to replace from photos (new tags only added photos with those tags)",
    multiple=True,
)
@click.option(
    "--add-tag",
    "add_tags",
    help="Tags to add to photos",
    multiple=True,
)
@click.option(
    "--limit",
    type=int,
    help="Max number of photos to retrieve.",
)
@click.option(
    "--sort",
    type=click.Choice(SORT_PARAMS),
    default="date-posted-desc",
    help=(
        f"Sort order for photostream ({', '.join(SORT_PARAMS)}). Ignored for albums."
    ),
)
def find_replace(
    album,
    start_id,
    end_id,
    find_title,
    replace_title,
    remove_tags,
    add_tags,
    replace_tags,
    sort,
    limit,
):
    """Find and replace text in photo titles and/or modify tags.

    Works on either an album (if --album provided) or photostream (if --album not
    provided).
    Can perform title replacements (--find-title and --replace-title) and/or
    tag operations (--remove-tag and/or --add-tags).

    At least one operation (title replacement or tag modification) must be specified.

    For photostream, photos are processed in the order specified by --sort.
    For albums, photos are processed in their album order (as they appear on Flickr).
    """
    flickr = auth_flickr()

    # Validate that at least one operation is specified
    if not find_title and not remove_tags and not add_tags:
        raise click.ClickException(
            "At least one operation must be specified: "
            "--find-title/--replace-title, --remove-tag, or --add-tags"
        )

    # Validate title replacement options
    if find_title and not replace_title:
        raise click.ClickException(
            "--replace-title is required when --find-title is specified"
        )
    if replace_title and not find_title:
        raise click.ClickException(
            "--find-title is required when --replace-title is specified"
        )

    is_replace = False
    if replace_tags:
        is_replace = True
        remove_tags = replace_tags

    if remove_tags:
        # Flickr does not allow space at start or end of tag : so remove ie probably
        # user error
        remove_tags = set(tag.strip() for tag in remove_tags)

    if add_tags:
        add_tags = format_tags(add_tags)

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
        logger.info(f"Processing photos in album {album_id}...")

        processed_count = 0
        is_process = False
        for image in images:
            if start_id is None or image.id == start_id:
                is_process = True

            if not is_process:
                continue

            if limit and processed_count >= limit:
                break

            _process_photo(
                flickr,
                image,
                find_title,
                replace_title,
                remove_tags,
                is_replace,
                add_tags,
            )
            processed_count += 1

            # Include photo with end_id in processing
            # TODO if bad order : will continue until the last photo in album
            if end_id is not None and image.id == end_id:
                break
    else:
        # Photostream mode - require start and end IDs
        if not start_id or not end_id:
            raise click.ClickException(
                "For photostream mode, both --start-id and --end-id are required"
            )

        logger.info(f"Processing photos in photostream (sort: {sort})...")
        images = get_photostream_photos(
            flickr, start_id, end_id, sort=sort, limit=limit
        )

        for image in images:
            _process_photo(
                flickr,
                image,
                find_title,
                replace_title,
                remove_tags,
                is_replace,
                add_tags,
            )


def _process_photo(
    flickr, image, find_title, replace_title, remove_tags, is_replace, add_tags
):
    """Process a single photo with title replacement and/or tag operations."""
    logger.info(f"Processing {image.id} [{image.title}] ...")

    # Title replacement
    if find_title and re.search(find_title, image.title):
        if replace_title:
            title, n = re.subn(find_title, replace_title, image.title)
            if n:
                flickr.photos.setMeta(photo_id=image.id, title=title)
                logger.info(f"  Updated title: {title}")

        # if title given : only add/remove tag related to the photos that match
        _add_remove_tags(flickr, image.id, remove_tags, is_replace, add_tags)
    else:
        # add/remove tag of all the photos
        _add_remove_tags(flickr, image.id, remove_tags, is_replace, add_tags)


def _add_remove_tags(flickr, photo_id, remove_tags, is_replace, add_tags):
    if remove_tags or add_tags:
        info = Addict(flickr.photos.getInfo(photo_id=photo_id))

        has_removed = False
        # Remove tag
        if remove_tags:
            for tag in info.photo.tags.tag:
                if tag["raw"] in remove_tags:
                    tag_id_to_remove = tag.id
                    flickr.photos.removeTag(tag_id=tag_id_to_remove)
                    logger.info(f"  Removed tag: {tag['raw']}")
                    has_removed = True

        # Add tags
        if add_tags and (not is_replace or has_removed):
            # not is_replace => always add
            # if is_replace => need has_removed
            # add_tags already transformed into correct arg shape for API
            flickr.photos.addTags(photo_id=photo_id, tags=add_tags)
            logger.info(f"  Added tags: {add_tags}")


@photo.command("correct-date", cls=CatchAllExceptionsCommand)
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
    from datetime import timedelta

    import dateutil.parser

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
        flickr.photos.setDates(photo_id=photo.id, date_posted=ts)
        logger.info(f"Posted {photo.id} {date_posted}")

        fake_date += timedelta(minutes=1)
