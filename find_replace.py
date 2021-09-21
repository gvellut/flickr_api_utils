from collections import namedtuple
import re

from addict import Dict as Addict

from api_auth import auth_flickr

FlickrAlbum = namedtuple("FlickrAlbum", "album_id url")

flickr = auth_flickr()


def parse_album_url(value):
    if value is not None:
        regex = r"flickr\.com/photos/[^/]+/(?:albums|sets)/(\d+)"
        m = re.search(regex, value)
        if m:
            return FlickrAlbum(m.group(1), value)
        else:
            raise ValueError("Not a Flickr album URL")
    return None


def _get_page_of_images_in_album(flickr, album_id, page, acc, output=False):
    album_info = Addict(
        flickr.photosets.getPhotos(
            photoset_id=album_id, page=page, extras="url_m,date_taken,geo"
        )
    ).photoset

    if output:
        print(
            f"Processing album '{album_info.title}' with {album_info.total} "
            "photos..."
        )

    acc.extend(album_info.photo)

    # return album for data about it
    return album_info


def get_images_in_album(flickr, album):
    flickr_images = []
    page = 1
    while True:
        album_info = _get_page_of_images_in_album(
            flickr,
            album.album_id,
            page,
            flickr_images,
            output=(page == 1),
        )

        if page >= album_info.pages:
            break
        page += 1

    return flickr_images


album = parse_album_url("https://www.flickr.com/photos/o_0/albums/72157719930382185")
images = get_images_in_album(flickr, album)

for image in images:
    title, n = re.subn("Grotte de Banges", "Grotte de Bange", image.title)
    if n:
        flickr.photos.setMeta(photo_id=image.id, title=title)
