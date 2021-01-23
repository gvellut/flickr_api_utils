import json
from pathlib import Path
import webbrowser

from addict import Dict as Addict
import flickrapi

with open("api_key.json") as f:
    flickr_key = Addict(json.load(f))

api_key = flickr_key.key
api_secret = flickr_key.secret


def auth_flickr():
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

    return flickr
