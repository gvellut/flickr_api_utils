from addict import Dict as Addict

from api_auth import auth_flickr

flickr = auth_flickr()

search_result = Addict(
    flickr.photos.search(
        user_id="me",
        tags="andonnee",
        tag_mode="all",
        min_uploaded_date="2021-10-25 00:00:00",
        per_page=500,
        extras="tags,machine_tags",
    )
)

# TODO replace wiht walk https://stuvel.eu/flickrapi-doc/7-util.html
for photo in search_result.photos.photo:
    info = Addict(flickr.photos.getInfo(photo_id=photo.id))
    for tag in info.photo.tags.tag:
        if tag["raw"] == "andonnee":
            tag_id_to_remove = tag.id
            resp = flickr.photos.removeTag(tag_id=tag_id_to_remove)
            # flickr.photos.addTags(photo_id=photo.id, tags="randonnee")
            break
