from collections import namedtuple
from datetime import datetime
import os
import shutil
import traceback

import requests

from api_auth import auth_flickr
from flickr_utils import get_photos

FlickrAlbum = namedtuple("FlickrAlbum", "album_id url")

flickr = auth_flickr()


album = "72177720318026202"
images = get_photos(flickr, album, privacy_filter=3)

output_folder = "laetitia"
os.makedirs(output_folder, exist_ok=True)

start_id = None
end_id = None

is_process = False
for image in images:
    if start_id is None or image.id == start_id:
        is_process = True

    if not is_process:
        continue

    try:
        datetaken = datetime.strptime(image.datetaken, "%Y-%m-%d %H:%M:%S")
        formatted_date = datetaken.strftime("%Y%m%d_%H%M%S")
        old_path = os.path.join(output_folder, f"{image.id}.jpg")
        new_path = os.path.join(output_folder, f"{formatted_date}_{image.id}.jpg")
        if os.path.exists(os.path.join(output_folder, f"{image.id}.jpg")):
            shutil.move(old_path, new_path)
        else:
            url = image.url_o
            print(f"Donwloading  {url}...")
            resp = requests.get(url)
            resp.raise_for_status()
            with open(
                os.path.join(output_folder, f"{formatted_date}_{image.id}.jpg"), "wb"
            ) as f:
                f.write(resp.content)
    except Exception:
        print("An error occured")
        traceback.print_exc()
        continue

    # incluide photo with end_id in processing
    if end_id is not None and image.id == end_id:
        break
