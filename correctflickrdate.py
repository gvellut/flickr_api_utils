from datetime import datetime, timedelta

from addict import Dict as Addict
import dateutil.parser
from dateutil.relativedelta import relativedelta

from api_auth import auth_flickr
from flickr_utils import get_photostream_photos

flickr = auth_flickr()

# search_result = Addict(
#     flickr.photos.search(
#         user_id="me",
#         tags="summer,ete,2020",
#         tag_mode="all",
#         min_taken_date="2019-01-16 00:00:00",
#         max_taken_date="2019-01-17 00:00:00",
#         extras="date_taken",
#         per_page=500,
#     )
# )

photos_uploaded = []
for photos in get_photostream_photos(
    flickr,
    start_photo_id=30540419,
    end_photo_id=55899593,
    # limit=25,
    sort="date-posted-asc",
    extras="date_taken",
):
    p = Addict(photos)
    p.datetaken = dateutil.parser.isoparse(p.datetaken)
    photos_uploaded.append(p)


min_dt = datetime(2005, 3, 30, 14, 5) + timedelta(minutes=231)
margin_dt = min_dt + timedelta(minutes=231)
fake_date = min_dt
sorted_photos = list(sorted(photos_uploaded, key=lambda x: x.datetaken))
for photo in sorted_photos:
    taken = photo.datetaken

    if taken > margin_dt:
        date_posted = taken
    else:
        date_posted = fake_date

    # unixtime
    ts = int(date_posted.timestamp())
    resp = flickr.photos.setDates(photo_id=photo.id, date_posted=ts)
    print(f"posted {photo.id} {date_posted}")

    fake_date += timedelta(minutes=1)
