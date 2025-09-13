import functools
import json

from addict import Dict as Addict

from api_auth import auth_flickr

flickr = auth_flickr()

ORDER_DESC = "DESC"
ORDER_ASC = "ASC"

start_album_id = "72157714081800731"
sort_by = "count_views"
sort_convert = int
sort_order = ORDER_DESC
show_attrs = ["title._content", "id", "count_views", "count_photos"]
except_album_ids = []

is_save_to_file = True
is_load_from_file = True
album_file = "albums.json"


def sub_attr(attr: str):
    if "." in attr:
        attr = attr.split(".")
    else:
        attr = [attr]

    def wrapper(album):
        sub_value = album
        for attr_part in attr:
            sub_value = sub_value[attr_part]
        return sub_value

    return wrapper


def convert_attr(attr):
    if sort_convert:
        return sort_convert(attr)
    return attr


def chain(*fs, reverse=True):
    def wrapper(arg):
        functions = reversed(fs) if reverse else fs
        return functools.reduce(lambda m, f: f(m), functions, arg)

    return wrapper


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


def extract_data(albums):
    albums_sub = []
    for i, album in enumerate(albums):
        if album.id == start_album_id:
            # start_album_id included
            albums_sub = albums[: i + 1]
            break
    else:
        print("Start album id not found !")
        albums_sub = albums

    key = chain(convert_attr, sub_attr(sort_by))

    reverse = sort_order == ORDER_DESC
    albums_sub = sorted(albums_sub, key=key, reverse=reverse)

    return albums_sub


def show_data(albums):
    show_attrs_f = [sub_attr(attr) for attr in show_attrs]
    for album in albums:
        album_str = []
        for attr_f in show_attrs_f:
            value = str(attr_f(album))
            album_str.append(value)
        print("\t".join(album_str))


if is_load_from_file and album_file:
    with open(album_file, encoding="utf-8") as f:
        albums = [Addict(album) for album in json.load(f)]
else:
    albums = list(get_albums())
    if is_save_to_file:
        if not album_file:
            print("'album_file' is empty !")
            exit(1)

        with open(album_file, "w", encoding="utf-8") as f:
            json.dump(albums, f)

albums = extract_data(albums)
show_data(albums)
