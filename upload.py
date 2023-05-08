import os

from tqdm import tqdm

from api_auth import auth_flickr
from xmp_utils import extract_xmp, get_label, get_tags, get_title, parse_xmp

folder = "E:/photos/20230503_brasses/___test"

album_id = "72177720308008185"
is_create_album = False
album_name = ""
album_description = ""

is_public = False

filter_label = "Accepted"

retries = 3


def is_filtered(xmp_root):
    label = get_label(xmp_root)
    return label == filter_label


def format_tags(tags):
    if tags:
        return '"' + '" "'.join(tags) + '"'
    return None


def main():
    flickr = auth_flickr()

    # TODO use TUI library see jncep
    print("Getting files to upload ...")
    files_to_upload = []
    for file_name in os.listdir(folder):
        if not file_name.upper().endswith(".JPG"):
            continue

        file_path = os.path.join(folder, file_name)
        xmp_bytes = extract_xmp(file_path)
        xmp_root = parse_xmp(xmp_bytes)
        if is_filtered(xmp_root):
            files_to_upload.append((file_path, xmp_root))

    print(f"{len(files_to_upload)} files to upload")
    progress_bar = tqdm(files_to_upload)
    for filepath, xmp_root in progress_bar:
        title = get_title(xmp_root)
        tags = get_tags(xmp_root)
        flickr_tags = format_tags(tags)

        # geotags should be picked up on the Flickr side
        progress_bar.set_description(
            f"Uploading file {filepath} : {title}, {len(tags)} tags ..."
        )

        def upload():
            # for some reason the default JSON format is not working, only XML
            # so ask for etree for parsing
            resp = flickr.upload(
                filename=filepath,
                title=title,
                tags=flickr_tags,
                is_public=is_public,
                format="etree",
            )
            return resp

        def retry_callback():
            progress_bar.set_description(
                f"Retrying file {filepath} : {title}, {len(tags)} tags ..."
            )

        try:
            resp = retry(retries, upload, retry_callback)
            photo_id = resp.find("photoid").text
            add_to_album(flickr, progress_bar, photo_id)
        except Exception as e:
            msg = f"Error uploading file {filepath}: {e}"
            progress_bar.write(msg)


def retry(num_retries, func, retry_callback):
    retry = num_retries
    while retry > 0:
        try:
            return func()
        except Exception:
            retry -= 1
            if retry > 0:
                retry_callback()
                continue
            raise


def add_to_album(flickr, progress_bar, photo_id):
    global album_id
    # do at the end : primary_photo_id is needed
    if is_create_album and not album_id:
        try:
            # create album using Flicker api
            resp = flickr.photosets.create(
                title=album_name,
                description=album_description,
                primary_photo_id=photo_id,
            )
            album_id = resp.photoset.id
        except Exception as e:
            msg = f"Error creating album {album_name}: {e}"
            progress_bar.write(msg)
            return

    # possible it was just created so no "else"
    if album_id:
        try:
            # append to existing album
            progress_bar.set_description(f"Appending to album {album_id} ...")

            # add photos to album
            def func():
                flickr.photosets.addPhoto(
                    photoset_id=album_id,
                    photo_id=photo_id,
                )

            def retry_callback():
                progress_bar.set_description(
                    f"Retrying appending to album {album_id} ..."
                )

            retry(retries, func, retry_callback)

        except Exception as e:
            msg = f"Error adding photo {photo_id} to album {album_id}: {e}"
            progress_bar.write(msg)


if __name__ == "__main__":
    main()
