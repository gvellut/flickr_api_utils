from addict import Dict as Addict

from .api_auth import auth_flickr

flickr = auth_flickr()

# search_result = Addict(
#     flickr.photos.search(
#         user_id="me",
#         tags="andonnee",
#         tag_mode="all",
#         min_uploaded_date="2021-10-25 00:00:00",
#         per_page=500,
#         extras="tags,machine_tags",
#     )
# )

album = Addict(
    flickr.photosets.getPhotos(
        photoset_id="72157720209505213",
        per_page=500,
    )
)

start_id = "51730055105"
end_id = "51730863735"

is_process = False
# TODO replace wiht walk https://stuvel.eu/flickrapi-doc/7-util.html
for photo in album.photoset.photo:
    if photo.id == end_id:
        break

    if photo.id == start_id:
        is_process = True

    if not is_process:
        continue

    info = Addict(flickr.photos.getInfo(photo_id=photo.id))
    for tag in info.photo.tags.tag:
        if tag["raw"] == "naves-parmelan":
            tag_id_to_remove = tag.id
            resp = flickr.photos.removeTag(tag_id=tag_id_to_remove)
            # flickr.photos.addTags(photo_id=photo.id, tags="randonnee")
            break
