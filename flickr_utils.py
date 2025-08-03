from datetime import datetime
import logging
from time import sleep

from addict import Dict as Addict

logger = logging.getLogger()


def all_pages(page_elem, iter_elem, func, *args, **kwargs):
    page = 1
    acc = []
    while True:
        paginated = Addict(func(*args, **kwargs, page=page))[page_elem]
        acc.extend(paginated[iter_elem])

        if int(paginated.page) >= int(paginated.pages):
            return acc

        page += 1


def get_albums(flickr):
    return all_pages(
        "photosets",
        "photoset",
        flickr.photosets.getList,
    )


def get_photos(flickr, album_id, extras="date_taken,url_o", **kwargs):
    return all_pages(
        "photoset",
        "photo",
        flickr.photosets.getPhotos,
        photoset_id=album_id,
        extras=extras,
        **kwargs,
    )


def all_pages_generator(page_elem, iter_elem, func, *args, **kwargs):
    page = 1
    while True:
        paginated = Addict(func(*args, **kwargs, page=page))[page_elem]
        yield paginated[iter_elem]

        if int(paginated.page) >= int(paginated.pages):
            return

        page += 1


# TODO more options for stream
def get_photostream_photos(
    flickr, start_photo_id=None, end_photo_id=None, limit=1000, **kwargs
):
    date_s = None
    if start_photo_id:
        info_s = Addict(flickr.photos.getInfo(photo_id=start_photo_id))
        # UNIX timestamp
        date_s = int(info_s.photo.dates.posted)

        dt_s = datetime.fromtimestamp(date_s)
        logger.info(f"Start: {dt_s}")

    date_e = None
    if end_photo_id:
        info_e = Addict(flickr.photos.getInfo(photo_id=end_photo_id))
        date_e = int(info_e.photo.dates.posted)

        dt_e = datetime.fromtimestamp(date_e)
        logger.info(f"End: {dt_e} ")

    if date_e and date_s:
        if date_e < date_s:
            raise ValueError(
                f"Date of start {start_photo_id} is after date of end {end_photo_id}"
            )

    if not date_s:
        # most likely a mistake : too many photos from the beginning
        if not limit:
            raise ValueError("Date of start empty and no limit")

        if "sort" in kwargs and kwargs["stop"] in ("date-posted-asc", "date-taken-asc"):
            raise ValueError(
                "Date of start empty and sort is from the very start (2005)"
            )
    else:
        kwargs.update(min_upload_date=date_s)

    if not date_e:
        # could be a problem depending on the start date
        logger.warning("No end date! Wait 2s. Abort if error.")
        sleep(2)
    else:
        kwargs.update(max_upload_date=date_e)

    counter = 0
    for photos in all_pages_generator(
        "photos",
        "photo",
        flickr.photos.search,
        user_id="me",
        **kwargs,
    ):
        for photo in photos:
            yield photo

            counter += 1
            if limit and counter >= limit:
                logger.info(f"Limit {limit} reached. Stopping")
                return
