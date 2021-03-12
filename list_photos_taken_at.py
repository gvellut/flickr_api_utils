from addict import Dict as Addict

from api_auth import auth_flickr

flickr = auth_flickr()

taken_date = "2020-12-23"

search_result = Addict(
    flickr.photos.search(
        user_id="me",
        min_taken_date=f"{taken_date} 00:00:00",
        max_taken_date=f"{taken_date} 23:59:59",
        per_page=5,
    )
)

print(f"Searching {taken_date}...")

# TODO replace wiht walk https://stuvel.eu/flickrapi-doc/7-util.html
for photo in search_result.photos.photo:
    photo = Addict(flickr.photos.getInfo(photo_id=photo.id)).photo
    title = photo.title._content
    owner = photo.owner.nsid
    id_ = photo.id
    url = f"https://flickr.com/photos/{owner}/{id_}"
    print(f"{url} {title}")
