import datetime as dt
import json
from pathlib import Path
import webbrowser

from addict import Dict as Addict
from dateutil.relativedelta import relativedelta
import flickrapi

with open("api_key.json") as f:
    flickr_key = Addict(json.load(f))

api_key = flickr_key.key
api_secret = flickr_key.secret


flickr = flickrapi.FlickrAPI(
    api_key,
    api_secret,
    format="parsed-json",
    token_cache_location=Path("./.flickr").resolve(),
)
if not flickr.token_valid(perms="write"):
    flickr.get_request_token(oauth_callback="oob")
    authorize_url = flickr.auth_url(perms="write")
    webbrowser.open_new_tab(authorize_url)
    verifier = input("Verifier code: ")
    flickr.get_access_token(verifier)

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
    taken_dt = dt.datetime.fromisoformat(taken)
    delta = relativedelta(years=1, months=8, hours=-8)
    taken_dt_corrected = taken_dt + delta
    taken_corrected = taken_dt_corrected.strftime("%Y-%m-%d %H:%M:%S")
    print(f"Corrected: {taken_corrected}")
    resp = flickr.photos.setDates(photo_id=photo.id, date_taken=taken_corrected)
