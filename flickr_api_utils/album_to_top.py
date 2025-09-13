from operator import attrgetter
import os.path

from addict import Dict as Addict

from .api_auth import auth_flickr

flickr = auth_flickr()

to_top_album_id = "72177720325191036"


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


albums = list(get_albums())
album_ids = list(map(attrgetter("id"), albums))

# to save
save_original = "original_set_to_top.txt"
if not os.path.exists(save_original):
    with open(save_original, "w") as f:
        f.write(repr(album_ids))

album_ids.pop(album_ids.index(to_top_album_id))
album_ids.insert(0, to_top_album_id)

q_album_ids = ",".join(album_ids)

flickr.photosets.orderSets(photoset_ids=q_album_ids)
