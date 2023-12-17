from collections import namedtuple
import re

from addict import Addict

from api_auth import auth_flickr
from flickr_utils import get_photostream_photos

FlickrAlbum = namedtuple("FlickrAlbum", "album_id url")

flickr = auth_flickr()


start_id = "53351502103"
end_id = "53351333836"

images = get_photostream_photos(flickr, start_id, end_id)

is_process = False
for image in images:
    if image.id == start_id:
        is_process = True

    if not is_process:
        continue

    title, n = re.subn("None", "Annecy", image.title)
    if n:
        print("Replacing...")
        flickr.photos.setMeta(photo_id=image.id, title=title)

    # info = Addict(flickr.photos.getInfo(photo_id=image.id))
    # for tag in info.photo.tags.tag:
    #     if tag["raw"] == "manigod":
    #         tag_id_to_remove = tag.id
    #         resp = flickr.photos.removeTag(tag_id=tag_id_to_remove)

    # flickr.photos.addTags(photo_id=image.id, tags='"bouchet-mont-charvin"')

    # incluide photo with end_id in processing
    if image.id == end_id:
        break
