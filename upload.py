import os

from addict import Dict as Addict
from attrs import define
import click
import piexif
from tqdm import tqdm

from api_auth import auth_flickr
from flickr_utils import get_photos
from xmp_utils import (
    extract_xmp,
    get_document_id,
    get_label,
    get_tags,
    get_title,
    parse_xmp,
)

retries = 3


class ConfirmationAbortedException(Exception):
    pass


@define
class UploadOptions:
    is_public: bool = False
    album_id: str = None
    is_create_album: bool = False
    album_name: str = None
    album_description: str = None


def is_filtered(xmp_root, filter_label):
    label = get_label(xmp_root)
    return label == filter_label


def format_tags(tags):
    if tags:
        return '"' + '" "'.join(tags) + '"'
    return None


folder_option = click.option(
    "--folder",
    "folder",
    required=True,
    help="Folder to upload",
)

album_option = click.option(
    "--album",
    "album_id",
    help="Album ID to upload to",
)

create_album_option = click.option(
    "--create-album",
    "is_create_album",
    is_flag=True,
    help="Create album",
)

album_name_option = click.option(
    "--album-name",
    "album_name",
    help="Album name to create",
)

album_description_option = click.option(
    "--album-description",
    "album_description",
    help="Album description to create",
)

public_option = click.option(
    "--public",
    "is_public",
    is_flag=True,
    help="Make photos public",
)


yes_option = click.option(
    "--yes",
    "is_yes",
    is_flag=True,
    help="Do not ask for confirmation",
)


@click.group()
def cli():
    pass


@cli.command("complete")
@folder_option
@click.option("--label", "filter_label", default="Accepted", help="Label to filter on")
@public_option
@album_option
@create_album_option
@album_name_option
@album_description_option
@yes_option
def complete(folder, filter_label, is_yes, **kwargs):
    flickr = auth_flickr()

    upload_options = UploadOptions(**kwargs)

    # TODO use TUI library see jncep : rich or textual
    print("Getting files to upload ...")
    files_to_upload = filtered(folder, filter_label)

    print(f"{len(files_to_upload)} files to upload")

    if not is_yes:
        if not click.confirm("The images will be uploaded. Confirm?"):
            raise ConfirmationAbortedException()

    files_to_upload = order_by_date(files_to_upload)

    # FIXME parallel uploads
    progress_bar = tqdm(files_to_upload)
    for filepath, xmp_root in progress_bar:
        upload_to_flickr(flickr, progress_bar, upload_options, filepath, xmp_root)


# to upload photos that are missing
# for now : only album
@cli.command("diff")
@folder_option
@click.option("--label", "filter_label", default="Uploaded", help="Label to filter on")
@click.option(
    "--album",
    "album_id",
    required=True,
    help="Album ID to upload to",
)
@public_option
@yes_option
def diff(folder, filter_label, is_yes, **kwargs):
    flickr = auth_flickr()

    upload_options = UploadOptions(**kwargs)

    print("Getting local set of photos ...")
    files_set = filtered(folder, filter_label)
    file_index_by_did = index_by_did(files_set)

    # for now : only album
    print(f"Get flickr images in {upload_options.album_id} ...")
    images = get_photos(flickr, upload_options.album_id)

    flickr_index_by_did = {}
    progress_bar = tqdm(images)
    for image in progress_bar:
        # get exif info from flick
        progress_bar.set_description(f"Getting exif for {image.id}")

        resp = Addict(flickr.photos.getExif(photo_id=image.id))
        for exif in resp.photo.exif:
            if exif.tag == "DocumentID":
                document_id = exif.raw._content
                flickr_index_by_did[document_id] = image
                break

    local_did_set = set(file_index_by_did.keys())
    flickr_did_set = set(flickr_index_by_did.keys())
    files_to_upload = list(local_did_set - flickr_did_set)
    if not files_to_upload:
        print("Nothing to upload")
        return

    print(f"{len(files_to_upload)} files to upload")

    if not is_yes:
        if not click.confirm("The images will be uploaded. Confirm?"):
            raise ConfirmationAbortedException()

    files_to_upload = order_by_date(files_to_upload)

    progress_bar = tqdm(files_to_upload)
    for did in progress_bar:
        filepath, xmp_root = file_index_by_did[did]

        upload_to_flickr(flickr, progress_bar, upload_options, filepath, xmp_root)


def order_by_date(files_to_upload):
    return sorted(files_to_upload, key=date_taken_key)


def date_taken_key(x):
    filepath, _ = x
    exif_data = piexif.load(filepath)
    dt_original = exif_data["Exif"][piexif.ExifIFD.DateTimeOriginal]
    # should be string orderable
    return dt_original.decode("ascii")


def upload_to_flickr(flickr, progress_bar, upload_options, filepath, xmp_root):
    title = get_title(xmp_root)
    tags = get_tags(xmp_root)
    flickr_tags = format_tags(tags)

    # geotags should be picked up on the Flickr side
    progress_bar.set_description(
        f"Uploading file {filepath} : {title}, {len(tags)} tags"
    )

    def upload():
        # for some reason the default JSON format is not working, only XML
        # so ask for etree for parsing
        resp = flickr.upload(
            filename=filepath,
            title=title,
            tags=flickr_tags,
            is_public=int(upload_options.is_public),
            format="etree",
        )
        return resp

    def retry_callback():
        progress_bar.set_description(
            f"Retrying file {filepath} : {title}, {len(tags)} tags"
        )

    try:
        resp = retry(retries, upload, retry_callback)
        photo_id = resp.find("photoid").text
        add_to_album(flickr, progress_bar, upload_options, photo_id)
        progress_bar.set_description("Done")
    except Exception as e:
        msg = f"Error uploading file {filepath}: {e}"
        progress_bar.write(msg)


def filtered(folder, filter_label):
    files_to_upload = []
    for file_name in os.listdir(folder):
        if not file_name.upper().endswith(".JPG"):
            continue

        file_path = os.path.join(folder, file_name)
        xmp_bytes = extract_xmp(file_path)
        xmp_root = parse_xmp(xmp_bytes)
        if is_filtered(xmp_root, filter_label):
            files_to_upload.append((file_path, xmp_root))
    return files_to_upload


def index_by_did(files_set):
    file_index_by_id = {}
    for file_path, xmp_root in files_set:
        document_id = get_document_id(xmp_root)
        file_index_by_id[document_id] = file_path, xmp_root
    return file_index_by_id


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


def add_to_album(flickr, progress_bar, upload_options, photo_id):
    # do at the end : primary_photo_id is needed
    album_id = upload_options.album_id
    if upload_options.is_create_album and not album_id:
        try:
            # create album using Flicker api
            resp = flickr.photosets.create(
                title=upload_options.album_name,
                description=upload_options.album_description,
                primary_photo_id=photo_id,
            )
            album_id = resp.photoset.id
        except Exception as e:
            msg = f"Error creating album {upload_options.album_name}: {e}"
            progress_bar.write(msg)
            return

    # possible it was just created so no "else"
    if album_id:
        try:
            # append to existing album
            progress_bar.set_description(f"Appending to album {album_id}")

            # add photos to album
            def func():
                flickr.photosets.addPhoto(
                    photoset_id=album_id,
                    photo_id=photo_id,
                )

            def retry_callback():
                progress_bar.set_description(f"Retrying appending to album {album_id}")

            retry(retries, func, retry_callback)

        except Exception as e:
            msg = f"Error adding photo {photo_id} to album {album_id}: {e}"
            progress_bar.write(msg)


if __name__ == "__main__":
    cli()
