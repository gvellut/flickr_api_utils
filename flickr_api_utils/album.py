from collections import defaultdict, namedtuple
from datetime import UTC, datetime
import json
import logging
from operator import attrgetter
import os.path

from addict import Dict as Addict
import click
import dateutil.parser

from .api_auth import auth_flickr
from .base import CatchAllExceptionsCommand
from .flickr_utils import get_photos
from .url_utils import extract_album_id, extract_photo_id

logger = logging.getLogger(__name__)


@click.group("album")
def album():
    """Album management commands."""
    pass


def all_pages(page_elem, iter_elem, func, *args, **kwargs):
    """Helper to iterate through all pages of a Flickr API result."""
    page = 1
    acc = []
    while True:
        paginated = Addict(func(*args, **kwargs, page=page))[page_elem]
        acc.extend(paginated[iter_elem])

        if int(paginated.page) >= int(paginated.pages):
            return acc

        page += 1


def get_albums():
    """Get all albums for the authenticated user."""
    flickr = auth_flickr()
    return all_pages(
        "photosets",
        "photoset",
        flickr.photosets.getList,
    )


@album.command("list", cls=CatchAllExceptionsCommand)
@click.option(
    "--sort-by",
    type=click.Choice(["date", "title"]),
    default="date",
    help="Sort albums by date or title",
)
def list_albums(sort_by):
    """List all albums ordered by creation date or title."""
    albums_with_cd = []
    for album_data in get_albums():
        date_create = int(album_data.date_create)
        dt_date_create = datetime.fromtimestamp(date_create, UTC)
        albums_with_cd.append(
            (album_data.title._content, dt_date_create, album_data.id)
        )

    if sort_by == "date":
        albums_with_cd.sort(key=lambda x: x[1], reverse=True)
    else:
        albums_with_cd.sort(key=lambda x: x[0])

    for title, date, album_id in albums_with_cd:
        logger.info(f"{date.strftime('%Y-%m-%d')} {album_id:20s} {title}")


@album.command("delete", cls=CatchAllExceptionsCommand)
@click.argument("album")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def delete_album(album, yes):
    """Delete an album.

    ALBUM can be an album ID or URL.
    """
    flickr = auth_flickr()
    album_id = extract_album_id(album)

    if not yes:
        if not click.confirm(f"Delete album {album_id}?"):
            logger.warning("Aborted")
            return

    flickr.photosets.delete(photoset_id=album_id)
    logger.info(f"Deleted album {album_id}")


@album.command("move-to-top", cls=CatchAllExceptionsCommand)
@click.argument("album")
@click.option(
    "--save-original",
    default="original_set_to_top.txt",
    help="File to save original order to",
)
def move_to_top(album, save_original):
    """Move an album to the top of your album list.

    ALBUM can be an album ID or URL.
    """
    flickr = auth_flickr()
    album_id = extract_album_id(album)

    albums = list(get_albums())
    album_ids = list(map(attrgetter("id"), albums))

    # Save original order
    if not os.path.exists(save_original):
        with open(save_original, "w") as f:
            f.write(repr(album_ids))

    album_ids.pop(album_ids.index(album_id))
    album_ids.insert(0, album_id)

    q_album_ids = ",".join(album_ids)

    flickr.photosets.orderSets(photoset_ids=q_album_ids)
    logger.info(f"Moved album {album_id} to top")


@album.command("reorder", cls=CatchAllExceptionsCommand)
@click.option(
    "--start-album",
    help="Album ID or URL to start reordering from (inclusive)",
)
@click.option(
    "--save-original",
    default="original_set_to_top.txt",
    help="File to save original order to",
)
def reorder_albums(start_album, save_original):
    """Reorder albums by the modal date of photos in each album.

    The most common date taken in an album is used to determine its position.
    """
    flickr = auth_flickr()

    if start_album:
        start_album_id = extract_album_id(start_album)
    else:
        start_album_id = None

    albums = list(get_albums())

    # Save original order
    if not os.path.exists(save_original):
        with open(save_original, "w") as f:
            f.write(repr(list(map(attrgetter("id"), albums))))

    as_is = []
    if start_album_id:
        until_index = list(map(attrgetter("id"), albums)).index(start_album_id) + 1
        until = albums[:until_index]
        as_is = albums[until_index:]
        albums = until

    DatePercent = namedtuple("DatePercent", "date percent")
    album_dates = {}

    for album_data in albums:
        logger.info(f"{album_data.title._content} {album_data.id}")
        album_id = album_data.id
        photos = all_pages(
            "photoset",
            "photo",
            flickr.photosets.getPhotos,
            photoset_id=album_id,
            extras="date_taken,url_o",
        )
        date_counts = defaultdict(lambda: 0)
        for photo in photos:
            date = dateutil.parser.isoparse(photo.datetaken).date()
            date_iso = date.isoformat()
            date_counts[date_iso] += 1

        date_mode = max(date_counts, key=lambda x: date_counts[x])
        date_mode_count = date_counts[date_mode]
        all_counts = len(photos)
        percent_mode = date_mode_count / all_counts

        album_dates[album_id] = DatePercent(date_mode, percent_mode)

    partial_ordered_album_ids = list(
        sorted(album_dates.keys(), key=lambda x: album_dates[x].date, reverse=True)
    )

    ordered_album_ids = partial_ordered_album_ids + list(map(attrgetter("id"), as_is))

    logger.info("Reordering albums...")
    q_album_ids = ",".join(ordered_album_ids)
    flickr.photosets.orderSets(photoset_ids=q_album_ids)
    logger.info("Albums reordered")


@album.command("reorder-photos", cls=CatchAllExceptionsCommand)
@click.argument("album")
def reorder_photos(album):
    """Reorder photos in an album by date taken.

    ALBUM can be an album ID or URL.
    """
    flickr = auth_flickr()
    album_id = extract_album_id(album)

    photos = get_photos(flickr, album_id)
    photos = sorted(photos, key=attrgetter("datetaken"))
    photo_ids = list(map(attrgetter("id"), photos))

    q_photo_ids = ",".join(photo_ids)
    flickr.photosets.reorderPhotos(photoset_id=album_id, photo_ids=q_photo_ids)
    logger.info(f"Reordered photos in album {album_id}")


@album.command("remove-photos", cls=CatchAllExceptionsCommand)
@click.argument("album")
@click.option(
    "--start-id",
    help="Photo ID or URL to start removing from (inclusive)",
)
@click.option(
    "--end-id",
    help="Photo ID or URL to end removing at (inclusive)",
)
@click.option("--yes", is_flag=True, help="Skip confirmation")
def remove_photos(album, start_id, end_id, yes):
    """Remove photos from an album.

    ALBUM can be an album ID or URL.
    """
    flickr = auth_flickr()
    album_id = extract_album_id(album)

    if start_id:
        start_id = extract_photo_id(start_id)
    if end_id:
        end_id = extract_photo_id(end_id)

    images = get_photos(flickr, album_id)

    photo_ids = []

    is_process = False
    for photo in images:
        if end_id and photo.id == end_id:
            break

        if start_id:
            if photo.id == start_id:
                is_process = True
        else:
            # from the start
            is_process = True

        if not is_process:
            continue

        photo_ids.append(photo.id)

    if not photo_ids:
        logger.warning("No photos to remove")
        return

    if not yes:
        if not click.confirm(f"Remove {len(photo_ids)} photos from album {album_id}?"):
            logger.warning("Aborted")
            return

    flickr.photosets.removePhotos(photoset_id=album_id, photo_ids=",".join(photo_ids))
    logger.info(f"Removed {len(photo_ids)} photos from album {album_id}")


@album.command("info", cls=CatchAllExceptionsCommand)
@click.option(
    "--start-album",
    help="Album ID or URL to start from (inclusive)",
)
@click.option(
    "--sort-by",
    default="count_views",
    help="Attribute to sort by (e.g., 'count_views', 'count_photos')",
)
@click.option(
    "--order",
    type=click.Choice(["asc", "desc"]),
    default="desc",
    help="Sort order",
)
@click.option(
    "--save-file",
    default="albums.json",
    help="File to cache album data",
)
@click.option(
    "--load-from-file",
    is_flag=True,
    help="Load album data from cache file instead of API",
)
@click.option(
    "--show-attrs",
    default="title._content,id,count_views,count_photos",
    help="Comma-separated list of attributes to display",
)
def info(start_album, sort_by, order, save_file, load_from_file, show_attrs):
    """Display album information sorted by various attributes."""
    import functools

    if start_album:
        start_album_id = extract_album_id(start_album)
    else:
        start_album_id = None

    show_attrs = show_attrs.split(",")

    def sub_attr(attr: str):
        if "." in attr:
            attr = attr.split(".")
        else:
            attr = [attr]

        def wrapper(album_data):
            sub_value = album_data
            for attr_part in attr:
                sub_value = sub_value[attr_part]
            return sub_value

        return wrapper

    def convert_attr(attr):
        try:
            return int(attr)
        except (ValueError, TypeError):
            return attr

    def chain(*fs, reverse=True):
        def wrapper(arg):
            functions = reversed(fs) if reverse else fs
            return functools.reduce(lambda m, f: f(m), functions, arg)

        return wrapper

    if load_from_file and os.path.exists(save_file):
        with open(save_file, encoding="utf-8") as f:
            albums = [Addict(album_data) for album_data in json.load(f)]
    else:
        albums = list(get_albums())
        if save_file:
            with open(save_file, "w", encoding="utf-8") as f:
                json.dump(albums, f)

    albums_sub = []
    for i, album_data in enumerate(albums):
        if start_album_id and album_data.id == start_album_id:
            # start_album_id included
            albums_sub = albums[: i + 1]
            break
    else:
        albums_sub = albums

    key = chain(convert_attr, sub_attr(sort_by))

    reverse = order == "desc"
    albums_sub = sorted(albums_sub, key=key, reverse=reverse)

    show_attrs_f = [sub_attr(attr) for attr in show_attrs]
    for album_data in albums_sub:
        album_str = []
        for attr_f in show_attrs_f:
            value = str(attr_f(album_data))
            album_str.append(value)
        logger.info("\t".join(album_str))
