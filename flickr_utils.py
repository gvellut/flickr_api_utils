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


def get_photos(flickr, album_id, extras="date_taken,url_o"):
    return all_pages(
        "photoset",
        "photo",
        flickr.photosets.getPhotos,
        photoset_id=album_id,
        extras=extras,
    )
