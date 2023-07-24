from api_auth import auth_flickr

flickr = auth_flickr()

to_delete_album_id = "72177720307400878"

flickr.photosets.delete(photoset_id=to_delete_album_id)
