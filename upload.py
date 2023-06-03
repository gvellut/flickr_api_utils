from datetime import datetime
from functools import partial
import logging
from multiprocessing import Pool
from operator import attrgetter
import os

from addict import Dict as Addict
from attrs import define
import click
import flickrapi
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

API_RETRIES = 3

UPLOAD_CONCURRENCY = 4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# too chatty
flickrapi.set_log_level(logging.CRITICAL)
# log outputs HTML error page for 500 errors + 504
logging.getLogger("flickrapi.auth.OAuthTokenHTTPServer").disabled = True
logging.getLogger("flickrapi.auth.OAuthFlickrInterface").disabled = True


class ConfirmationAbortedException(Exception):
    pass


class ValidationError(Exception):
    pass


class UploadError(Exception):
    pass


class AlbumCreationError(Exception):
    pass


class AddToAlbumError(Exception):
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

parallel_option = click.option(
    "--parallel",
    default=UPLOAD_CONCURRENCY,
    help="Set number of parallel uploads + Flickr API calls",
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
@parallel_option
@yes_option
def complete(folder, filter_label, is_yes, parallel, **kwargs):
    flickr = auth_flickr()

    upload_options = UploadOptions(**kwargs)

    if upload_options.is_create_album and not upload_options.album_name:
        raise ValidationError("Album name is required for creation")

    print("Getting files to upload ...")
    files_to_upload = filtered(folder, filter_label)

    print(f"{len(files_to_upload)} files to upload")

    _print_album_options(upload_options)
    if upload_options.is_public:
        print("Will make photos public")
    else:
        print("Will keep photos private")

    if not is_yes:
        if not click.confirm("The images will be uploaded. Confirm?"):
            raise ConfirmationAbortedException()

    files_to_upload = order_by_date(files_to_upload)

    photo_uploaded_ids = _upload_photos(
        flickr, upload_options, files_to_upload, parallel
    )
    _set_date_posted(flickr, photo_uploaded_ids, parallel)
    _add_to_album(flickr, upload_options, photo_uploaded_ids, parallel)


def _upload_photos(flickr, upload_options, files_to_upload, parallel):
    photos_uploaded = []

    progress_bar = tqdm(desc="Uploading...", total=len(files_to_upload))

    def _result_callback(result):
        photos_uploaded.append(result)
        progress_bar.update(1)

    def _error_callback(ex):
        msg = ex.args[0]
        progress_bar.write(msg)

    with Pool(parallel) as pool:
        for index, (filepath, xmp_root) in enumerate(files_to_upload):
            pool.apply_async(
                upload_to_flickr,
                (flickr, upload_options, index, filepath, xmp_root),
                callback=_result_callback,
                error_callback=_error_callback,
            )
        pool.close()
        pool.join()

    progress_bar.close()

    if photos_uploaded:
        print(f"{len(photos_uploaded)} files uploaded")

    # parallel upload may have changed the order : the first item of the tuple is
    # the rank in the original order
    photos_uploaded = sorted(photos_uploaded, key=lambda x: x[0])
    photos_uploaded = [x[1] for x in photos_uploaded]

    return photos_uploaded


def _print_album_options(upload_options):
    if upload_options.is_create_album:
        print(f"Will create album {upload_options.album_name}")
    elif upload_options.album_id:
        print(f"Will add to album {upload_options.album_id}")
    else:
        print("Not adding to album")


def _set_date_posted(flickr, photos_uploaded, parallel):
    # so the photos appear in order in the photostream
    print("Resetting upload dates...")

    progress_bar = tqdm(desc="Resetting dates...", total=len(photos_uploaded))

    def _result_callback(result):
        progress_bar.update(1)

    def _error_callback(ex):
        msg = ex.args[0]
        progress_bar.write(msg)

    now_ts = generate_timestamps(len(photos_uploaded))
    with Pool(parallel) as pool:
        for photo_id, timestamp in zip(photos_uploaded, now_ts):
            pool.apply_async(
                partial(
                    retry,
                    API_RETRIES,
                    partial(
                        flickr.photos.setDates,
                        photo_id=photo_id,
                        date_posted=timestamp,
                    ),
                ),
                callback=_result_callback,
                error_callback=_error_callback,
            )
        pool.close()
        pool.join()

    progress_bar.close()


def _add_to_album(flickr, upload_options, photo_uploaded_ids, parallel):
    album_id = upload_options.album_id
    primary_photo_id = None
    if upload_options.is_create_album and not album_id:
        print("Creating album...")
        primary_photo_id = photo_uploaded_ids[0]
        album_id = create_album(flickr, upload_options, primary_photo_id)
        print(f"Album created with id {album_id}")

    if album_id:
        print(f"Adding photos to album {album_id}...")

        progress_bar = tqdm(desc="Adding to album...", total=len(photo_uploaded_ids))

        def _result_callback(result):
            progress_bar.update(1)

        def _error_callback(ex):
            msg = ex.args[0]
            progress_bar.write(msg)

        with Pool(parallel) as pool:
            for photo_id in photo_uploaded_ids:
                if primary_photo_id == photo_id:
                    # already added in create_album
                    continue
                pool.apply_async(
                    add_to_album,
                    (flickr, album_id, photo_id),
                    callback=_result_callback,
                    error_callback=_error_callback,
                )
            pool.close()
            pool.join()

        progress_bar.close()

        print("Reordering album...")
        # get everything in the album and reorder it: tried with only passing the new
        # uploads but weird result
        album_photos = get_photos(flickr, album_id)
        photos = sorted(album_photos, key=attrgetter("datetaken"))
        photo_ids = list(map(attrgetter("id"), photos))

        q_photo_ids = ",".join(photo_ids)
        flickr.photosets.reorderPhotos(photoset_id=album_id, photo_ids=q_photo_ids)


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
    progress_bar = tqdm(images, desc="Getting exif + DocumentID...")
    for image in progress_bar:
        # get exif info from flick
        try:
            resp = Addict(
                retry(API_RETRIES, partial(flickr.photos.getExif, photo_id=image.id))
            )
            for exif in resp.photo.exif:
                if exif.tag == "DocumentID":
                    document_id = exif.raw._content
                    flickr_index_by_did[document_id] = image
                    break
            else:
                progress_bar.write(f"No DocumentID found for {image.id}")

        except Exception as e:
            msg = f"Error getting DocumentID for {image.id}: {e}"
            progress_bar.write(msg)

    local_did_set = set(file_index_by_did.keys())
    flickr_did_set = set(flickr_index_by_did.keys())
    dids_to_upload = local_did_set - flickr_did_set
    if not dids_to_upload:
        print("Nothing to upload")
        return

    print(f"{len(dids_to_upload)} files to upload")

    if not is_yes:
        if not click.confirm("The images will be uploaded. Confirm?"):
            raise ConfirmationAbortedException()

    files_to_upload = [file_index_by_did[did] for did in dids_to_upload]
    files_to_upload = order_by_date(files_to_upload)

    progress_bar = tqdm(files_to_upload, desc="Uploading...")
    for index, filepath, xmp_root in enumerate(progress_bar):
        try:
            upload_to_flickr(flickr, upload_options, index, filepath, xmp_root)
        except Exception as ex:
            msg = ex.args[0]
            progress_bar.write(msg)
    progress_bar.close()


def order_by_date(files_to_upload):
    return sorted(files_to_upload, key=date_taken_key)


def date_taken_key(x):
    filepath, _ = x
    exif_data = piexif.load(filepath)
    dt_original = exif_data["Exif"][piexif.ExifIFD.DateTimeOriginal]
    # should be string orderable
    return dt_original.decode("ascii")


def generate_timestamps(num_photos):
    # should be fine if no multiple uploads at the same time
    # photos take > 1 sec (unless parallel very high)
    now_ts = int(datetime.now().timestamp()) - num_photos
    timestamps = [now_ts + i for i in range(num_photos)]
    return timestamps


def upload_to_flickr(flickr, upload_options, order, filepath, xmp_root):
    title = get_title(xmp_root)
    tags = get_tags(xmp_root)
    flickr_tags = format_tags(tags)

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

    try:
        resp = retry(API_RETRIES, upload)
        photo_id = resp.find("photoid").text
        return order, photo_id
    except Exception as e:
        msg = f"Error uploading file {filepath}: {e}"
        raise UploadError(msg)


def filtered(folder, filter_label):
    files_to_upload = []
    for file_name in os.listdir(folder):
        if not (
            file_name.upper().endswith(".JPG") or file_name.upper().endswith(".PNG")
        ):
            continue

        if filter_label:
            file_path = os.path.join(folder, file_name)
            xmp_bytes = extract_xmp(file_path)
            xmp_root = parse_xmp(xmp_bytes)
            if not is_filtered(xmp_root, filter_label):
                continue

        files_to_upload.append((file_path, xmp_root))

    return files_to_upload


def index_by_did(files_set):
    file_index_by_id = {}
    for file_path, xmp_root in files_set:
        document_id = get_document_id(xmp_root)
        file_index_by_id[document_id] = file_path, xmp_root
    return file_index_by_id


def retry(num_retries, func, retry_callback=None):
    retry = num_retries
    while retry > 0:
        try:
            return func()
        except Exception:
            retry -= 1
            if retry > 0:
                if retry_callback:
                    retry_callback()
                continue
            raise


def create_album(flickr, upload_options, primary_photo_id):
    try:
        # create album using Flicker api
        def func():
            return flickr.photosets.create(
                title=upload_options.album_name,
                description=upload_options.album_description,
                primary_photo_id=primary_photo_id,
            )

        resp = Addict(retry(API_RETRIES, func))
        album_id = resp.photoset.id
        return album_id
    except Exception as e:
        msg = f"Error creating album {upload_options.album_name}: {e}"
        raise AlbumCreationError(msg)


def add_to_album(flickr, album_id, photo_id):
    try:
        # append to existing album
        # add photos to album
        def func():
            flickr.photosets.addPhoto(
                photoset_id=album_id,
                photo_id=photo_id,
            )

        retry(API_RETRIES, func)

    except Exception as e:
        msg = f"Error adding photo {photo_id} to album {album_id}: {e}"
        raise AddToAlbumError(msg)


if __name__ == "__main__":
    cli()
