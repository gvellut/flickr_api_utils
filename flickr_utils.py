from addict import Dict as Addict


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
def get_photostream_photos(flickr, start_photo_id, end_photo_id, limit=1000, **kwargs):
    info_s = Addict(flickr.photos.getInfo(photo_id=start_photo_id))
    # UNIX timestamp
    date_s = int(info_s.photo.dates.posted)
    info_e = Addict(flickr.photos.getInfo(photo_id=end_photo_id))
    date_e = int(info_e.photo.dates.posted)

    if date_e < date_s:
        raise ValueError(
            f"Date of start {start_photo_id} is after date of end {end_photo_id}"
        )

    counter = 0
    for photos in all_pages_generator(
        "photos",
        "photo",
        flickr.photos.search,
        user_id="me",
        min_upload_date=date_s,
        max_upload_date=date_e,
        sort="date-posted-asc",
        **kwargs,
    ):
        for photo in photos:
            yield photo

            counter += 1
            if limit and counter >= limit:
                print(f"Limit {limit} reached. Stopping")
                return
