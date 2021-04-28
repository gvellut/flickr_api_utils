from addict import Dict as Addict
import dateutil
from dateutil.relativedelta import relativedelta

from api_auth import auth_flickr

flickr = auth_flickr()

search_result = Addict(
    flickr.photos.search(
        user_id="me",
        tags="summer,ete,2020",
        tag_mode="all",
        min_taken_date="2019-01-16 00:00:00",
        max_taken_date="2019-01-17 00:00:00",
        extras="date_taken",
        per_page=500,
    )
)

for photo in search_result.photos.photo:
    taken = photo.datetaken
    print(f"Original: {taken}")
    taken_dt = dateutil.parser.isoparse(taken)
    delta = relativedelta(years=1, months=8, hours=-8)
    taken_dt_corrected = taken_dt + delta
    taken_corrected = taken_dt_corrected.strftime("%Y-%m-%d %H:%M:%S")
    print(f"Corrected: {taken_corrected}")
    resp = flickr.photos.setDates(photo_id=photo.id, date_taken=taken_corrected)
