import json
from pathlib import Path
import webbrowser

from addict import Dict as Addict
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
        tags="aire-la-ville,satigny",
        tag_mode="all",
        min_uploaded_date="2020-12-19 00:00:00",
        per_page=100,
        extras="tags,machine_tags",
    )
)

# TODO replace wiht walk https://stuvel.eu/flickrapi-doc/7-util.html
for photo in search_result.photos.photo:
    if "pont" not in photo.tags:
        info = Addict(flickr.photos.getInfo(photo_id=photo.id))
        for tag in info.photo.tags.tag:
            if tag["raw"] == "aire-la-ville":
                tag_id_to_remove = tag.id
                resp = flickr.photos.removeTag(tag_id=tag_id_to_remove)
                break
