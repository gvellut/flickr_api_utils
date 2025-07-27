from collections import namedtuple
import datetime
import re

from addict import Addict

from api_auth import auth_flickr
from flickr_utils import get_photostream_photos

FlickrAlbum = namedtuple("FlickrAlbum", "album_id url")


def local_tz_fixed():
    now_local_aware = datetime.datetime.now(datetime.UTC).astimezone()
    local_offset_timedelta = now_local_aware.utcoffset()
    local_tz = datetime.timezone(local_offset_timedelta)
    return local_tz


flickr = auth_flickr()


start_id = "54619969949"
# here the end id is mandatory
end_id = "54620138645"

images = get_photostream_photos(flickr, start_id, end_id)

for image in images:
    # photos are ordered by date posted ASC
    # and include all photos between start_id and end_id
    # so not need to check if processing

    print(f"Processing {image.id} [{image.title}] ...")

    title, n = re.subn("Montagne d'Àge", "Montagne d'Âge", image.title)
    if n:
        print("Replacing...")
        flickr.photos.setMeta(photo_id=image.id, title=title)

    # info = Addict(flickr.photos.getInfo(photo_id=image.id))
    # iso_date_string = datetime.datetime.fromtimestamp(
    #     int(info.photo.dates.posted), tz=local_tz_fixed()
    # ).isoformat()
    # print(f"Processing {image.id} posted={iso_date_string}...")
    # for tag in info.photo.tags.tag:
    #     if tag["raw"] == "may":
    #         tag_id_to_remove = tag.id
    #         resp = flickr.photos.removeTag(tag_id=tag_id_to_remove)

    # flickr.photos.addTags(photo_id=image.id, tags='"april","fujinon","xf 70 300"')
