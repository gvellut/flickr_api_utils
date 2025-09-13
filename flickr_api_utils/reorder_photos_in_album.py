from operator import attrgetter

from .api_auth import auth_flickr
from .flickr_utils import get_photos

flickr = auth_flickr()

album_id = "72177720308609341"

photos = get_photos(flickr, album_id)
photos = sorted(photos, key=attrgetter("datetaken"))
photo_ids = list(map(attrgetter("id"), photos))

q_photo_ids = ",".join(photo_ids)
flickr.photosets.reorderPhotos(photoset_id=album_id, photo_ids=q_photo_ids)
