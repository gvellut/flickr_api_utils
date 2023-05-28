from collections import namedtuple
import re

from addict import Addict

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


album = parse_album_url("https://www.flickr.com/photos/o_0/albums/72177720308482555")
images = get_photos(flickr, album.album_id)

start_id = "52922582680"
end_id = "52922199281"

is_process = False
for image in images:
    if image.id == start_id:
        is_process = True

    if not is_process:
        continue

    title, n = re.subn("Lathuile", "Doussard", image.title)
    if n:
        flickr.photos.setMeta(photo_id=image.id, title=title)

        info = Addict(flickr.photos.getInfo(photo_id=image.id))
        for tag in info.photo.tags.tag:
            if tag["raw"] == "lathuile":
                tag_id_to_remove = tag.id
                resp = flickr.photos.removeTag(tag_id=tag_id_to_remove)

        flickr.photos.addTags(photo_id=image.id, tags='"doussard"')

    # incluide photo with end_id in processing
    if image.id == end_id:
        break
