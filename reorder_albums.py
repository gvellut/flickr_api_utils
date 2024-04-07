from collections import defaultdict, namedtuple
from operator import attrgetter
import os.path

from addict import Dict as Addict
import dateutil.parser

from api_auth import auth_flickr

flickr = auth_flickr()

start_album_id = "72177720313267710"


def all_pages(page_elem, iter_elem, func, *args, **kwargs):
    page = 1
    acc = []
    while True:
        paginated = Addict(func(*args, **kwargs, page=page))[page_elem]
        acc.extend(paginated[iter_elem])

        if int(paginated.page) >= int(paginated.pages):
            return acc

        page += 1


def get_albums():
    return all_pages(
        "photosets",
        "photoset",
        flickr.photosets.getList,
    )


def get_photos(album_id, extras="date_taken,url_o"):
    return all_pages(
        "photoset",
        "photo",
        flickr.photosets.getPhotos,
        photoset_id=album_id,
        extras=extras,
    )


albums = list(get_albums())

# to save
save_original = "reorder_sets_original_sort.txt"
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
for album in albums:
    print(f"{album.title._content} {album.id}")
    album_id = album.id
    photos = get_photos(album_id)
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

q_album_ids = ",".join(ordered_album_ids)
flickr.photosets.orderSets(photoset_ids=q_album_ids)
