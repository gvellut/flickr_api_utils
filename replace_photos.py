from datetime import datetime
from fnmatch import fnmatch
import os

from addict import Dict as Addict
import piexif

from api_auth import auth_flickr
from flickr_utils import get_photos


def make_flickr_photo_url(photo, user_id):
    if photo.pathalias:
        user_path = photo.pathalias
    else:
        user_path = user_id
    return f"https://www.flickr.com/photos/{user_path}/{photo.id}"


flickr = auth_flickr()

user = Addict(flickr.auth.oauth.checkToken())

album_id = "72157719125798869"
folder_path = (
    "/Users/guilhem/Pictures/camera/___uploaded/20210508_foretlanfon_ok/autocorrect2"
)
file_pattern = "DSCF*.JPG"

photos = list(get_photos(flickr, album_id, extras="date_taken,url_o,path_alias"))

flickr_time_index = {}
for photo in photos:
    date_taken = photo.datetaken
    flickr_time_index[date_taken] = photo

photo_time_index = {}
for file_name in os.listdir(folder_path):
    if not file_name.endswith(".JPG"):
        continue
    if not file_pattern or fnmatch(file_name, file_pattern):
        file_path = os.path.join(folder_path, file_name)
        exif_data = piexif.load(file_path)
        dt_original = exif_data["Exif"][piexif.ExifIFD.DateTimeOriginal]
        dt_original = dt_original.decode("ascii")
        dt_format_in = "%Y:%m:%d %H:%M:%S"
        dt_original = datetime.strptime(dt_original, dt_format_in)
        dt_format_out = "%Y-%m-%d %H:%M:%S"
        dt_original = datetime.strftime(dt_original, dt_format_out)
        # TODO process timezone ? since flickr stores in local timezone (using Offset)
        # but I don't use it so fine
        photo_time_index[dt_original] = file_path

for date_taken, file_path in photo_time_index.items():
    if date_taken not in flickr_time_index:
        # should not happen unless there is some time shifting shenanigan
        # or changed manually with Organizr
        print(f"Photo {file_path} with date {date_taken} not found on Flickr!")
        continue
    flickr_photo = flickr_time_index[date_taken]
    print(f"Replace {make_flickr_photo_url(flickr_photo, user.id)} with {file_path}...")
    result = flickr.replace(file_path, flickr_photo.id, format="rest")
    result = result.decode("utf-8", "ignore")
    if 'stat="ok"' not in result:
        # TODO or XML parse
        print(f"Error uploading: {result}")
