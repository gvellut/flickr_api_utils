from datetime import datetime
from functools import partial
import logging
from multiprocessing import Pool
from operator import attrgetter
import os
from time import sleep

from addict import Dict as Addict
from attrs import define
import click
import flickrapi
import piexif
from requests import ReadTimeout
from tqdm import tqdm

from api_auth import auth_flickr
from flickr_utils import get_photos
from xmp_utils import (
    NoXMPPacketFound,
    extract_xmp,
    get_document_id,
    get_label,
    get_tags,
    get_title,
    parse_xmp,
)

API_RETRIES = 6
API_RETRY_DELAY = 5

UPLOAD_CONCURRENCY = 4
QUICK_CONCURRENCY = 1

NCOLS = 80

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# too chatty
flickrapi.set_log_level(logging.CRITICAL)
# log outputs HTML error page for 500 errors + 504
logging.getLogger("flickrapi.auth.OAuthTokenHTTPServer").disabled = True
logging.getLogger("flickrapi.auth.OAuthFlickrInterface").disabled = True

PRINT_API_ERROR = False


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
            print("Aborted by user")
            exit(1)

    # so close approximate value of date taken start from the POV of Flickr
    now_ts = datetime.now().timestamp()

    files_to_upload = order_by_date(files_to_upload)

    photo_uploaded_ids = _upload_photos(
        flickr, upload_options, files_to_upload, parallel
    )
    _set_date_posted(flickr, now_ts, photo_uploaded_ids, QUICK_CONCURRENCY)
    _add_to_album(flickr, upload_options, photo_uploaded_ids, QUICK_CONCURRENCY)


def _upload_photos(flickr, upload_options, files_to_upload, parallel):
    photos_uploaded = []

    progress_bar = tqdm(desc="Uploading...", total=len(files_to_upload), ncols=NCOLS)

    def _result_callback(result):
        photos_uploaded.append(result)
        progress_bar.update(1)

    def _error_callback(ex):
        msg = "Error during 'Uploading photos': " + str(ex.args[0])
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

    # print the photos with a readtimeout error : may be duplicated on Flickr =>
    # uploaded successfully but error returned from the API
    # display path so is visible which ones so can delete manually (no photo ID
    # available so has to be done manually)
    timeout_photos = [os.path.basename(x[2]) for x in photos_uploaded if x[3]]
    if timeout_photos:
        print(f"{len(timeout_photos)} photo timeouts : {','.join(timeout_photos)}")

    # parallel upload may have changed the order : the first item of the tuple is
    # the rank in the original order
    photos_uploaded = sorted(photos_uploaded, key=lambda x: x[0])
    photo_ids_uploaded = [x[1] for x in photos_uploaded]

    return photo_ids_uploaded


def _print_album_options(upload_options):
    if upload_options.is_create_album:
        print(f"Will create album {upload_options.album_name}")
    elif upload_options.album_id:
        print(f"Will add to album {upload_options.album_id}")
    else:
        print("Not adding to album")


def _set_date_posted(flickr, now_ts, photos_uploaded, parallel):
    # so the photos appear in order in the photostream
    print("Resetting upload dates...")

    progress_bar = tqdm(
        desc="Resetting dates...", total=len(photos_uploaded), ncols=NCOLS
    )

    def _result_callback(result):
        progress_bar.update(1)

    def _error_callback(ex):
        msg = "Error during 'Resetting upload dates': " + str(ex.args[0])
        progress_bar.write(msg)

    now_ts = generate_timestamps(now_ts, len(photos_uploaded))
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
        primary_photo_id = photo_uploaded_ids[0]
        print(f"Creating album with primary photo {primary_photo_id} ...")
        album_id = create_album(flickr, upload_options, primary_photo_id)
        print(f"Album created with id {album_id}")

    if album_id:
        print(f"Adding photos to album {album_id}...")

        to_add_photo_ids = list(
            filter(lambda x: x != primary_photo_id, photo_uploaded_ids)
        )
        progress_bar = tqdm(
            desc="Adding to album...", total=len(to_add_photo_ids), ncols=NCOLS
        )

        def _result_callback(result):
            progress_bar.update(1)

        def _error_callback(ex):
            msg = "Error during 'Adding to album': " + str(ex.args[0])
            progress_bar.write(msg)

        with Pool(parallel) as pool:
            # already added in create_album
            for photo_id in to_add_photo_ids:
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
        album_photos = retry(API_RETRIES, partial(get_photos, flickr, album_id))
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
    progress_bar = tqdm(images, desc="Getting exif + DocumentID...", ncols=NCOLS)
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
            print("Aborted by user")
            exit(1)

    files_to_upload = [file_index_by_did[did] for did in dids_to_upload]
    files_to_upload = order_by_date(files_to_upload)

    progress_bar = tqdm(files_to_upload, desc="Uploading...", ncols=NCOLS)
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


def generate_timestamps(now_ts, num_photos):
    # well in the past so no overlap with actual upload time : bug in Flickr API will
    # duplicate some uploads => easier to remove manually after the fact if the case
    # in the past instead of in the future so no error from Flickr ie
    # 6: Invalid Date Taken
    # should be fine if no multiple uploads at the same time
    # photos take > 1 sec (unless parallel very high)
    now_ts -= 3 * num_photos
    timestamps = [now_ts + i for i in range(num_photos)]
    return timestamps


# timeout was set to 15 but sometimes recently since end of 2024
# Error calling Flickr API: HTTPSConnectionPool(host='up.flickr.com', port=443):
# Read timed out. (read timeout=15)
# Still photo is uploaded.
# No change with timeout set to 45 => To correct : check the last upload since no id ?
# how to search # if multiple threads
# try 30: but already tried, no change
def upload_to_flickr(flickr, upload_options, order, filepath, xmp_root, timeout=30):
    title = get_title(xmp_root)
    tags = get_tags(xmp_root)
    flickr_tags = format_tags(tags)

    # only count once even if multiple timeouts
    has_timeout = False

    def error_callback(ex):
        if isinstance(ex, ReadTimeout):
            nonlocal has_timeout
            has_timeout = True
        return False, False

    def upload():
        # for some reason the default JSON format is not working, only XML
        # so ask for etree for parsing
        resp = flickr.upload(
            filename=filepath,
            title=title,
            tags=flickr_tags,
            is_public=int(upload_options.is_public),
            format="etree",
            timeout=timeout,
        )
        return resp

    try:
        resp = retry(API_RETRIES, upload, error_callack=error_callback)
        photo_id = resp.find("photoid").text
        # return filepath since inputs can be missing from outputs if error so not
        # aligned
        return order, photo_id, filepath, has_timeout
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
            try:
                file_path = os.path.join(folder, file_name)
                xmp_bytes = extract_xmp(file_path)
                xmp_root = parse_xmp(xmp_bytes)
                if not is_filtered(xmp_root, filter_label):
                    continue
            except NoXMPPacketFound:
                logger.warning(f"No XMP data for {file_name}")
                continue

        files_to_upload.append((file_path, xmp_root))

    return files_to_upload


def index_by_did(files_set):
    file_index_by_id = {}
    for file_path, xmp_root in files_set:
        document_id = get_document_id(xmp_root)
        file_index_by_id[document_id] = file_path, xmp_root
    return file_index_by_id


def retry(num_retries, func, error_callack=None):
    retry = num_retries
    while retry > 0:
        try:
            return func()
        except Exception as ex:
            # put error : case of mulitple uploads : not sure if silent error in Flickr
            # API or case of an error is returned but the photo is still uploaded
            # check
            # TODO see if formatting problem with progress bar
            if PRINT_API_ERROR:
                logger.warning(f"Error calling Flickr API: {ex}\nRetry ...")
            if error_callack:
                return_now, raise_now = error_callack(ex)
                if return_now:
                    return None
                if raise_now:
                    raise
            retry -= 1
            if retry > 0:
                sleep(API_RETRY_DELAY)
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

        def error_callack(ex: Exception):
            # usually means a 500 error was received when adding a photo but the photo
            # was actually successfully added to album
            if len(ex.args) > 0 and "Error: 3: Photo already in set" in ex.args[0]:
                return True, False

            return False, False

        retry(API_RETRIES, func, error_callack)

    except Exception as e:
        msg = f"Error adding photo {photo_id} to album {album_id}: {e}"
        raise AddToAlbumError(msg)


if __name__ == "__main__":
    cli()
