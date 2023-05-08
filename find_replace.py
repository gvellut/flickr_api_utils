from collections import namedtuple
import re

from api_auth import auth_flickr
from flickr_utils import get_photos

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


album = parse_album_url("https://www.flickr.com/photos/o_0/albums/72157719930382185")
images = get_photos(flickr, album.album_id)

for image in images:
    title, n = re.subn("Grotte de Banges", "Grotte de Bange", image.title)
    if n:
        flickr.photos.setMeta(photo_id=image.id, title=title)
