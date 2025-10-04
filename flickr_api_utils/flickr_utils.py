from datetime import datetime
import logging
from time import sleep

from addict import Dict as Addict

logger = logging.getLogger(__name__)


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


# start, end : depend on sort order which is later : desc : e < s; asc: s < e
# in argument
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

    if not date_e and not date_s and not limit:
        raise ValueError("No dates and no limit: All photos would be returned.")

    # avoid going to 2005 in both sort order (most likely a mistake)
    if "sort" in kwargs and kwargs["sort"].endswith("-asc"):
        if not date_s:
            # in this case, you should input the first photo
            raise ValueError("Start date empty: would start from 2005 (sort=asc)")
    else:
        # desc
        if not date_e and not limit:
            raise ValueError(
                "End date empty and would go to 2005. Probably a mistake (sort=desc)"
            )
        # for flickr API parameters : it should be ordered
        date_e, date_s = date_s, date_e

    if date_s:
        kwargs.update(min_upload_date=date_s)

    if date_e:
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
            # limit is applied in code
            if limit and counter >= limit:
                logger.info(f"Limit {limit} reached. Stopping")
                return
