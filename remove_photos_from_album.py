from addict import Dict as Addict

from api_auth import auth_flickr

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

photoset_id = "72177720309365095"

album = Addict(
    flickr.photosets.getPhotos(
        photoset_id=photoset_id,
        per_page=500,
    )
)

start_id = "53010449188"
end_id = None  # "51730863735"

photo_ids = []

is_process = False
# TODO replace wiht walk https://stuvel.eu/flickrapi-doc/7-util.html
for photo in album.photoset.photo:
    if end_id and photo.id == end_id:
        break

    if start_id:
        if photo.id == start_id:
            is_process = True
    else:
        # from the start
        is_process = True

    if not is_process:
        continue

    photo_ids.append(photo.id)


flickr.photosets.removePhotos(photoset_id=photoset_id, photo_ids=",".join(photo_ids))
