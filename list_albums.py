from datetime import datetime, timezone

from addict import Dict as Addict

from api_auth import auth_flickr

flickr = auth_flickr()


def get_albums():
    return _get_album_page(1, [])


def _get_album_page(page, acc):
    search_result = Addict(flickr.photosets.getList(page=page))
    albums = search_result.photosets

    for album in albums.photoset:
        date_create = int(album.date_create)
        dt_date_create = datetime.fromtimestamp(date_create, timezone.utc)
        acc.append((album.title._content, dt_date_create))

    if albums.page < albums.pages:
        return _get_album_page(page + 1, acc)
    else:
        return acc


albums_with_cd = get_albums()
albums_with_cd.sort(key=lambda x: x[1], reverse=True)

for (title, date) in albums_with_cd:
    print(f"{date.strftime('%Y-%m-%d')} => {title}")
