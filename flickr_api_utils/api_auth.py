import json
from pathlib import Path
import random
import string

from addict import Dict as Addict
import flickrapi


def generate_random_string(length):
    letters = string.ascii_letters + string.digits
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str


def auth_flickr() -> flickrapi.FlickrAPI:
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

    v = generate_random_string(5)
    flickr.flickr_oauth.session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit"
            f"/537.36 (KHTML, like Gecko) Chrome/120.0.0.0v{v} Safari/537.3"
        }
    )

    if not flickr.token_valid(perms="write"):
        flickr.authenticate_via_browser(perms="write")

    return flickr
