from collections import namedtuple
import ctypes
from ctypes.macholib.dyld import dyld_find
import ctypes.util
from datetime import datetime, timedelta
import fnmatch
import logging
import os
import re
import shlex
import shutil
import subprocess

import attr
import click
import piexif
from PIL import ExifTags, Image

from .base import CatchAllExceptionsCommand
from .upload import UPLOADED_DIR, ZOOM_DIR, ZOOM_PREFIX

logger = logging.getLogger(__name__)


@click.group("local")
def local():
    """Local file operations."""
    pass


@local.command("crop43", cls=CatchAllExceptionsCommand)
@click.argument(
    "input_folder", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.argument("output_folder", type=click.Path())
def crop43(input_folder, output_folder):
    """Crop vertical JPEG images to 4:3 aspect ratio.

    Processes all JPEG files in INPUT_FOLDER and saves cropped versions to
    OUTPUT_FOLDER.
    Preserves EXIF data.
    """

    os.makedirs(output_folder, exist_ok=True)
    count = 0

    if not click.confirm(f"Crop {input_folder} to {output_folder}. Confirm?"):
        logger.warning("Aborted by user")
        return

    for filename in sorted(list(os.listdir(input_folder))):
        if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
            logger.info(f"Processing file: {filename}")
            img_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            crop_image(img_path, output_path)
            count += 1


def crop_image(img_path, output_path):
    """Crop a single image to 4:3 aspect ratio."""
    with Image.open(img_path) as img:
        exif = {
            ExifTags.TAGS[k]: v
            for k, v in img.getexif().items()
            if k in ExifTags.TAGS and isinstance(v, (int, bytes))
        }

        orientation = exif.get("Orientation", 1)

        if orientation in [6, 8]:  # Vertical image
            if orientation == 6:  # Rotate 90 degrees to the right
                img_rot = img.rotate(-90, expand=True)
            elif orientation == 8:  # Rotate 90 degrees to the left
                img_rot = img.rotate(90, expand=True)

            new_height = int(img_rot.width * 4 / 3)
            img_cropped = img_rot.crop((0, 0, img_rot.width, new_height))
        else:  # Horizontal image
            new_width = int(img.height * 4 / 3)
            left = img.width - new_width
            img_cropped = img.crop((left, 0, img.width, img.height))

        if "exif" in img.info:
            # clear the orientation in exif since saved pixels already rotated
            exif_dict = piexif.load(img.info["exif"])
            exif_dict["0th"][piexif.ImageIFD.Orientation] = 1
            exif_bytes = piexif.dump(exif_dict)
            img_cropped.save(
                output_path, "JPEG", subsampling=0, quality=95, exif=exif_bytes
            )
        else:
            img_cropped.save(output_path, "JPEG", subsampling=0, quality=95)


@local.command("check-copied", cls=CatchAllExceptionsCommand)
@click.option(
    "--source",
    "source_folders",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=str),
    multiple=True,
)
@click.option(
    "--target",
    "target_folder",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=str),
)
@click.option(
    "--filter",
    "filter_pattern",
    help="Glob pattern of subfolder names to include",
)
@click.option(
    "--ignore",
    "ignore_pattern",
    help="Glob pattern of subfolder names to ignore",
)
@click.option(
    "--rsync",
    "generate_rsync",
    is_flag=True,
    help="Generate rsync commands for missing subfolders",
)
@click.option(
    "--all",
    "rsync_all",
    is_flag=True,
    help="Generate rsync commands for all subfolders, not just the missing",
)
def check_copied(
    source_folders,
    target_folder,
    filter_pattern,
    ignore_pattern,
    generate_rsync,
    rsync_all,
):
    """Ensure subfolders from SOURCE_FOLDER exist in TARGET_FOLDER."""
    source_children = set()
    source_children_origin = {}
    for source_folder in source_folders:
        for entry in os.scandir(source_folder):
            if not entry.is_dir():
                continue
            name = entry.name
            if filter_pattern and not fnmatch.fnmatch(name, filter_pattern):
                continue
            if ignore_pattern and fnmatch.fnmatch(name, ignore_pattern):
                continue
            source_children.add(name)
            source_children_origin[name] = source_folder

    target_children = {
        entry.name for entry in os.scandir(target_folder) if entry.is_dir()
    }

    missing = sorted(source_children - target_children)
    if not missing:
        logger.info("All subfolders from source exist in target.")
        # do not return : rsync can still be generated if all
    else:
        logger.info("Missing subfolders:")
        grouped = {}
        for name in missing:
            origin = source_children_origin.get(name, "<unknown>")
            grouped.setdefault(origin, []).append(name)

        for origin in sorted(grouped):
            logger.info(f"{origin}:")
            for n in sorted(grouped[origin]):
                logger.info(f"  {n}")

    rsync_folders = missing if not rsync_all else source_children
    if generate_rsync and rsync_folders:
        logger.info("Rsync commands:\n\n")
        for name in rsync_folders:
            source_folder = source_children_origin[name]
            source_path = os.path.join(source_folder, name)
            command = build_rsync_command(source_path, target_folder)
            logger.info(command)
        logger.info("\n\n")


def build_rsync_command(source_path, target_parent):
    source_abs = os.path.abspath(source_path)
    target_abs = os.path.abspath(target_parent)

    args = ["rsync", "-vaE"]

    args.append("--exclude=.DS_Store")

    filters = compute_zoom_filters(source_abs)
    args.extend(filters)

    args.extend([source_abs, target_abs])

    return " ".join(shlex.quote(arg) for arg in args)


def compute_zoom_filters(source_path):
    try:
        with os.scandir(source_path) as entries:
            entry_list = list(entries)
    except FileNotFoundError:
        return []

    # If there are no subdirectories at top level, copy normally (no special
    # rsync filters)
    if not any(entry.is_dir() for entry in entry_list):
        return []

    has_zoom_dir = any(
        entry.is_dir() and entry.name == ZOOM_DIR for entry in entry_list
    )

    stray_zoom_found = False
    for root, _, files in os.walk(source_path):
        rel_root = os.path.relpath(root, source_path)
        if rel_root in (".", ""):
            path_parts = ()
        else:
            path_parts = tuple(rel_root.split(os.sep))
        if ZOOM_DIR in path_parts:
            continue
        for filename in files:
            if filename.startswith(ZOOM_PREFIX):
                stray_zoom_found = True
                break
        if stray_zoom_found:
            break

    if not stray_zoom_found:
        return []

    filters = []
    if has_zoom_dir:
        # include zoom folder and its contents first so files inside it are preserved
        filters.append(f"--include={ZOOM_DIR}/")
        filters.append(f"--include={ZOOM_DIR}/**")
    # exclude stray zoom files elsewhere
    filters.append(f"--exclude={ZOOM_PREFIX}*")
    return filters


@local.command("copy-zoom-to-std", cls=CatchAllExceptionsCommand)
@click.argument("folder_path")
def copy_zoom_to_std(folder_path):
    """Copy photos from zoom camera folder to standard camera folder.

    Copies files from {folder}/tz95 to {folder}/xs20.
    """
    BASE_DIR = "/Volumes/CrucialX8/photos"
    folder_std = "xs20"
    folder_zoom = "tz95"

    if not os.path.isabs(folder_path):
        # make abs
        folder_path = os.path.join(BASE_DIR, folder_path)

    source_dir_path = os.path.join(folder_path, folder_zoom)
    dest_dir_path = os.path.join(folder_path, folder_std)

    logger.info(f"Source directory: {source_dir_path}")
    logger.info(f"Destination directory: {dest_dir_path}")

    if not os.path.isdir(source_dir_path):
        logger.error(f"Source directory '{folder_zoom}' not found.")
        return
    if not os.path.isdir(dest_dir_path):
        logger.error(f"Destination directory '{folder_std}' not found.")
        return

    if not click.confirm("Proceed with copying files?"):
        logger.warning("Operation cancelled by user.")
        return

    copied_count = 0

    for item_name in sorted(os.listdir(source_dir_path)):
        source_item_path = os.path.join(source_dir_path, item_name)
        dest_item_path = os.path.join(dest_dir_path, item_name)

        if os.path.isfile(source_item_path):
            try:
                shutil.copy2(source_item_path, dest_item_path)
                if copied_count % 20 == 0:
                    logger.info(f"Copy #{copied_count + 1}: '{item_name}'")
                copied_count += 1
            except Exception as e:
                logger.error(f"Error copying '{item_name}': {e}")
        else:
            logger.warning(f"Skipping '{item_name}', not a file.")

    logger.info(f"Copy complete. {copied_count} file(s) copied.")


# Copy SD card functionality
output_parent_folder = "/Volumes/CrucialX8/photos"
MEDIA_FOLDER_MAPPING = {
    "LUMIX": "tz95",
    "XS10": "xs10",
    "RX100M7": "rx100",
    "XS20": "xs20",
}
MEDIA = list(MEDIA_FOLDER_MAPPING.keys())

DATE_FMT = "%Y%m%d"
OUTPUT_DATE_FMT = DATE_FMT

PhotoVolume = namedtuple("PhotoVolume", "name path")

# TODO remove the multiple volumes and date array: makes code more complex and is not
# actually used


@attr.s
class DateRange:
    start = attr.ib()
    end = attr.ib()


def date_to_str(d):
    if isinstance(d, DateRange):
        s = []
        if d.start:
            s.append(d.start.isoformat() + " ")
        s.append("-")
        if d.end:
            s.append(" " + d.end.isoformat())
        return "".join(s)
    return d.isoformat()


def dirname_with_date(parent_folder, name, f_date):
    if isinstance(f_date, DateRange):
        # all the same anyway
        date_r = f_date
        if date_r.end:
            f_date = date_r.end
        elif date_r.start:
            f_date = date_r.start
        else:
            # today
            f_date = datetime.now().date()

    date_s = f_date.strftime(OUTPUT_DATE_FMT)
    output_folder = os.path.join(parent_folder, f"{date_s}_{name}")

    return output_folder


def dirs_with_date(folder, subfolder=None):
    date_pattern = re.compile(r"^\d{8}_")
    items = os.listdir(folder)
    date_folders = [
        item
        for item in items
        if os.path.isdir(os.path.join(folder, item)) and date_pattern.match(item)
    ]

    if subfolder:
        # only keep the dates with a folder for the SD card inside
        date_folders = [
            date_folder
            for date_folder in date_folders
            if os.path.isdir(os.path.join(folder, date_folder, subfolder))
        ]

    return sorted(date_folders, reverse=True)


PREFIX_SINCE = "since:"


def is_since(date_s):
    return date_s.startswith(PREFIX_SINCE)


def to_dates(date_s, volume: PhotoVolume):
    if date_s == "TD":
        return datetime.now().date()

    if date_s == "YD":
        return datetime.now().date() - timedelta(days=1)

    if date_s == "YD2":
        return datetime.now().date() - timedelta(days=2)

    if date_s == "YD3":
        return datetime.now().date() - timedelta(days=3)

    if date_s == "L":
        # L for latest
        return find_latest_date(volume.path)

    if date_s == "L2":
        return find_latest_date(volume.path, rank=1)

    if date_s == "L3":
        return find_latest_date(volume.path, rank=2)

    if "-" in date_s:
        return parse_date_range(date_s)

    # may return multiple dates
    if is_since(date_s):
        date_s = date_s[len(PREFIX_SINCE) :]
        if date_s == "last":
            folder_for_sd = MEDIA_FOLDER_MAPPING[volume.name]
            dirs_workspace = dirs_with_date(
                output_parent_folder, subfolder=folder_for_sd
            )
            dirs_uploaded = dirs_with_date(
                os.path.join(output_parent_folder, UPLOADED_DIR),
                subfolder=folder_for_sd,
            )
            dirs = sorted(dirs_workspace + dirs_uploaded, reverse=True)
            if dirs:
                # replace with last folder in order
                date_s = dirs[0]
                logger.info(f"last => {date_s}")
            else:
                # no folder (new camera maybe?)
                # dummy date far in the past
                date_s = "10000101"
                logger.info("No existing folder: From the beginning")

        # only first 8 characters in case title copied
        date_s = date_s[:8]
        date_since = datetime.strptime(date_s, "%Y%m%d").date()
        filtered = filter_after(find_all_dates(volume.path), date_since)
        if not filtered:
            logger.warning("No photo since last date.")
        return filtered

    return datetime.strptime(date_s, DATE_FMT).date()


def parse_date_range(date_range_str):
    dates = date_range_str.split("-")
    start_date = datetime.strptime(dates[0], DATE_FMT).date() if dates[0] else None
    end_date = (
        datetime.strptime(dates[1], DATE_FMT).date()
        if len(dates) > 1 and dates[1]
        else None
    )

    return DateRange(start_date, end_date)


def find_latest_date(volume_path, rank=0):
    dates = find_all_dates(volume_path)
    if not dates:
        return None
    return dates[rank]


def find_all_dates(volume_path):
    dates = []
    for root, _, filenames in os.walk(volume_path):
        for filename in filenames:
            if not filter_relevant_image(filename):
                continue
            file_path = os.path.join(root, filename)
            last_modified_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            dates.append(last_modified_date.date())
    if not dates:
        return None
    dates = list(set(dates))
    return sorted(dates, reverse=True)


def filter_after(dates, date_after):
    return [d for d in dates if d > date_after]


def get_volume(media):
    volumes_path = "/Volumes"
    volumes = os.listdir(volumes_path)

    for volume in volumes:
        if volume in media:
            return PhotoVolume(volume, os.path.join(volumes_path, volume))

    return None


def eject_volume(volume_name):
    subprocess.run(["diskutil", "eject", f"/Volumes/{volume_name}"])


def filter_relevant_image(filename):
    return filename.lower().endswith((".jpg", ".jpeg", ".raf", ".raw", ".m4a", ".avi"))


def filter_by_date(image_date, date_):
    if isinstance(date_, DateRange):
        if date_.start and image_date < date_.start:
            return False
        if date_.end and image_date > date_.end:
            return False
        return True
    return image_date == date_


def copy_to_folder(volume: PhotoVolume, folder_base, f_date):
    os.makedirs(folder_base, exist_ok=True)

    media_folder = MEDIA_FOLDER_MAPPING[volume.name]
    output_folder = os.path.join(folder_base, media_folder)
    os.makedirs(output_folder, exist_ok=True)

    counter = 0
    for root, _, filenames in os.walk(volume.path):
        for filename in filenames:
            if not filter_relevant_image(filename):
                continue
            file_path = os.path.join(root, filename)
            last_modified_date = datetime.fromtimestamp(os.path.getmtime(file_path))

            if filter_by_date(last_modified_date.date(), f_date):
                counter += 1
                if counter % 20 == 0:
                    logger.info(f"Copy #{counter}: {file_path}")
                shutil.copy2(file_path, output_folder)


@local.command("copy-sd", cls=CatchAllExceptionsCommand)
@click.option(
    "--name",
    required=True,
    help="Folder name for the copied photos",
)
@click.option(
    "--date",
    "date_spec",
    default="TD",
    help="Date spec (TD=today, YD=yesterday, YYYYMMDD, or YYYYMMDD-YYYYMMDD for range)",
)
@click.option(
    "--no-eject",
    "is_eject",
    default=True,
    is_flag=True,
    help="Do not eject SD card after copying",
)
def copy_sd(name, date_spec, is_eject):
    """Copy photos from SD card to local folder.

    Automatically detects SD card (LUMIX, XS10, RX100M7, XS20) and copies
    photos based on date specification.
    """
    volume = get_volume(MEDIA)

    if not volume:
        logger.error("No relevant SD card. Volume not renamed?")
        return

    dates = to_dates(date_spec, volume)
    if not isinstance(dates, list):
        dates = [dates]
    if not dates:
        logger.info("No image found: Is the SD card inserted and mounted?")
        return

    dates = sorted(dates)
    output_folder_base = [
        dirname_with_date(output_parent_folder, name, f_date) for f_date in dates
    ]

    volume_mapping = MEDIA_FOLDER_MAPPING[volume.name]
    text_folder = ", ".join(output_folder_base)
    text_date = ", ".join([date_to_str(d) for d in dates])

    if not click.confirm(
        f"The images will be copied from : {volume_mapping} to {text_folder} "
        f"(dates: {text_date})\nConfirm?"
    ):
        logger.warning("Aborted by user")
        return

    for i, f_date in enumerate(dates):
        folder_base = output_folder_base[i]
        logger.info(f"Copy to {folder_base} (date: {f_date}) ...")
        copy_to_folder(volume, folder_base, f_date)

    try:
        if is_eject:
            logger.info(f"Ejecting {volume[0]} ...")
            eject_volume(volume[0])
    except Exception:
        logger.exception(f"Error ejecting {volume[0]}")


@local.command("copy-all", cls=CatchAllExceptionsCommand)
@click.option(
    "--source",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Source folder path",
)
@click.option(
    "--dest",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Destination folder path",
)
@click.option(
    "--pattern",
    default="*.JPG",
    help="File pattern to copy (e.g., '*.JPG', 'DSCF*.jpg')",
)
def copy_all(source, dest, pattern):
    """Copy files matching a pattern from source to destination folder.

    Useful for copying specific files between folders.
    """
    copied = 0
    for file_name in os.listdir(source):
        if fnmatch.fnmatch(file_name, pattern):
            source_path = os.path.join(source, file_name)
            dest_path = os.path.join(dest, file_name)
            shutil.copy(source_path, dest_path)
            copied += 1
            logger.info(f"Copied: {file_name}")

    logger.info(f"Total files copied: {copied}")


@local.command("list-not-uploaded", cls=CatchAllExceptionsCommand)
@click.option(
    "--folder",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Folder to scan",
)
@click.option(
    "--pattern",
    default="*_ok",
    help="Pattern to match (files NOT matching are listed)",
)
def list_not_uploaded(folder, pattern):
    """List files in a folder that do NOT match a pattern.

    Useful for finding folders that haven't been processed yet.
    """
    list_of_files = sorted(os.listdir(folder))
    unmatched = []
    for entry in list_of_files:
        if not fnmatch.fnmatch(entry, pattern):
            unmatched.append(entry)
            logger.info(entry)

    logger.info(f"Total unmatched entries: {len(unmatched)}")


# XMP library setup for find-replace-local
def find_library(name):
    possible = [
        f"/opt/homebrew/lib/lib{name}.dylib",
        f"@executable_path/../lib/lib{name}.dylib",
        f"lib{name}.dylib",
        f"{name}.dylib",
        f"{name}.framework/{name}",
    ]
    for name in possible:
        try:
            return dyld_find(name)
        except ValueError:
            continue
    return None


ctypes.util.find_library = find_library


@local.command("find-replace-local", cls=CatchAllExceptionsCommand)
@click.option(
    "--folder",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Folder containing images to process",
)
@click.option(
    "--start-name",
    help="File name to start processing from (inclusive)",
)
@click.option(
    "--end-name",
    help="File name to end processing at (inclusive)",
)
@click.option(
    "--find-title",
    help="Text pattern to find in image titles (regex supported)",
)
@click.option(
    "--replace-title",
    help="Text to replace in image titles",
)
@click.option(
    "--pattern",
    default="*.JPG",
    help="File pattern to match (e.g., '*.JPG', '*.jpg')",
)
def find_replace_local(
    folder, start_name, end_name, find_title, replace_title, pattern
):
    """Find and replace text in local image XMP metadata.

    Modifies XMP metadata in local image files (requires python-xmp-toolkit).
    Processes files in the folder sorted by EXIF date taken.
    """
    # Import here to make it optional
    try:
        from libxmp import XMPFiles, consts

        _ = (XMPFiles, consts)
    except ImportError as ex:
        raise click.ClickException(
            "python-xmp-toolkit is required for this command. "
            "Install it with: pip install python-xmp-toolkit"
        ) from ex

    # Validate options
    if find_title and not replace_title:
        raise click.ClickException(
            "--replace-title is required when --find-title is specified"
        )
    if replace_title and not find_title:
        raise click.ClickException(
            "--find-title is required when --replace-title is specified"
        )
    if not find_title:
        raise click.ClickException(
            "At least --find-title/--replace-title must be specified"
        )

    def date_taken(exif_data):
        dt_original = exif_data["Exif"][piexif.ExifIFD.DateTimeOriginal]
        return dt_original.decode("ascii")

    # Get and sorted
