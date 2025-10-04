"""Local file operations commands."""
from collections import namedtuple
from datetime import datetime, timedelta
import ctypes
from ctypes.macholib.dyld import dyld_find
import ctypes.util
import fnmatch
import logging
import os
import re
import shutil
import subprocess
import traceback

import attr
import click
import piexif
from PIL import ExifTags, Image


@click.group()
def local():
    """Local file operations."""
    pass


@local.command("crop43")
@click.argument("input_folder", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument("output_folder", type=click.Path())
def crop43(input_folder, output_folder):
    """Crop vertical JPEG images to 4:3 aspect ratio.
    
    Processes all JPEG files in INPUT_FOLDER and saves cropped versions to OUTPUT_FOLDER.
    Preserves EXIF data.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    os.makedirs(output_folder, exist_ok=True)
    count = 0
    
    if not click.confirm(f"Crop to {output_folder}. Confirm?"):
        click.echo("Aborted by user")
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
            
            # Reset orientation
            try:
                exif_bytes = piexif.dump({"0th": {piexif.ImageIFD.Orientation: 1}})
                img_cropped.save(output_path, exif=exif_bytes, quality=95)
            except Exception:
                img_cropped.save(output_path, quality=95)
        else:
            # Horizontal: just copy
            img.save(output_path, quality=95)


@local.command("copy-zoom-to-std")
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
    
    click.echo(f"Source directory: {source_dir_path}")
    click.echo(f"Destination directory: {dest_dir_path}")
    
    if not os.path.isdir(source_dir_path):
        click.echo(f"Error: Source directory '{folder_zoom}' not found.")
        return
    if not os.path.isdir(dest_dir_path):
        click.echo(f"Error: Destination directory '{folder_std}' not found.")
        return
    
    if not click.confirm("Proceed with copying files?"):
        click.echo("Operation cancelled by user.")
        return
    
    copied_count = 0
    
    for item_name in os.listdir(source_dir_path):
        source_item_path = os.path.join(source_dir_path, item_name)
        dest_item_path = os.path.join(dest_dir_path, item_name)
        
        if os.path.isfile(source_item_path):
            try:
                shutil.copy2(source_item_path, dest_item_path)
                click.echo(f"Copied '{item_name}'")
                copied_count += 1
            except Exception as e:
                click.echo(f"Error copying '{item_name}': {e}")
        else:
            click.echo(f"Skipping '{item_name}', not a file.")
    
    click.echo(f"\nCopy complete. {copied_count} file(s) copied.")


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
            dirs = dirs_with_date(output_parent_folder, subfolder=folder_for_sd)
            if dirs:
                # replace with last folder in order
                date_s = dirs[0]
                print(f"last => {date_s}")
            else:
                # no folder (new camera maybe?)
                # dummy date far in the past
                date_s = "10000101"
                print("No existing folder: From the beginning")

        # only first 8 characters in case title copied
        date_s = date_s[:8]
        date_since = datetime.strptime(date_s, "%Y%m%d").date()
        filtered = filter_after(find_all_dates(volume.path), date_since)
        if not filtered:
            print("No photo since last date.")
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
                    print(f"Copy #{counter}: {file_path}")
                shutil.copy2(file_path, output_folder)


@local.command("copy-sd")
@click.option(
    "--name",
    required=True,
    help="Folder name for the copied photos",
)
@click.option(
    "--date",
    "date_spec",
    default="TD",
    show_default=True,
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
        click.echo("No relevant SD card. Volume not renamed?")
        return

    dates = to_dates(date_spec, volume)
    if not isinstance(dates, list):
        dates = [dates]
    if not dates:
        click.echo("No image found: Is the SD card inserted and mounted?")
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
        click.echo("Aborted by user")
        return

    for i, f_date in enumerate(dates):
        folder_base = output_folder_base[i]
        print(f"Copy to {folder_base} (date: {f_date}) ...")
        copy_to_folder(volume, folder_base, f_date)

    try:
        if is_eject:
            print(f"Ejecting {volume[0]} ...")
            eject_volume(volume[0])
    except Exception:
        print(f"Error ejecting {volume[0]}")
        traceback.print_exc()


@local.command("copy-all")
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
            click.echo(f"Copied: {file_name}")
    
    click.echo(f"\nTotal files copied: {copied}")


@local.command("list-not-uploaded")
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
            click.echo(entry)
    
    click.echo(f"\nTotal unmatched entries: {len(unmatched)}")


# XMP library setup for find-replace-local
def find_library(name):
    possible = [
        "/opt/homebrew/lib/lib%s.dylib" % name,
        "@executable_path/../lib/lib%s.dylib" % name,
        "lib%s.dylib" % name,
        "%s.dylib" % name,
        "%s.framework/%s" % (name, name),
    ]
    for name in possible:
        try:
            return dyld_find(name)
        except ValueError:
            continue
    return None


ctypes.util.find_library = find_library


@local.command("find-replace-local")
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
def find_replace_local(folder, start_name, end_name, find_title, replace_title, pattern):
    """Find and replace text in local image XMP metadata.
    
    Modifies XMP metadata in local image files (requires python-xmp-toolkit).
    Processes files in the folder sorted by EXIF date taken.
    """
    # Import here to make it optional
    try:
        from libxmp import consts, XMPFiles, XMPMeta
    except ImportError:
        raise click.ClickException(
            "python-xmp-toolkit is required for this command. "
            "Install it with: pip install python-xmp-toolkit"
        )
    
    # Validate options
    if find_title and not replace_title:
        raise click.ClickException("--replace-title is required when --find-title is specified")
    if replace_title and not find_title:
        raise click.ClickException("--find-title is required when --replace-title is specified")
    if not find_title:
        raise click.ClickException("At least --find-title/--replace-title must be specified")
    
    def date_taken(exif_data):
        dt_original = exif_data["Exif"][piexif.ExifIFD.DateTimeOriginal]
        return dt_original.decode("ascii")
    
    # Get and sort images by date taken
    file_paths = os.listdir(folder)
    images = []
    for file_path in file_paths:
        if not fnmatch.fnmatch(file_path, pattern):
            continue
        
        image_path = os.path.join(folder, file_path)
        if not os.path.isfile(image_path):
            continue
            
        try:
            exif_data = piexif.load(image_path)
            dt = date_taken(exif_data)
            images.append((image_path, dt, file_path))
        except Exception:
            click.echo(f"Warning: Could not read EXIF from {file_path}", err=True)
            continue
    
    ordered_images = sorted(images, key=lambda x: x[1])
    
    is_process = False
    processed = 0
    
    for image_path, _, file_name in ordered_images:
        if start_name is None or file_name == start_name:
            is_process = True
        
        if not is_process:
            continue
        
        click.echo(f"Processing: {file_name}")
        
        to_save = False
        
        try:
            xmpfile = XMPFiles(file_path=image_path, open_forupdate=True)
            xmp = xmpfile.get_xmp()
            ns = "http://purl.org/dc/elements/1.1/"
            title = xmp.get_property(ns, "dc:title[1]")
            
            if find_title and replace_title and title:
                new_title, n = re.subn(find_title, replace_title, title)
                if n:
                    to_save = True
                    xmp.set_array_item(ns, "dc:title", 1, new_title)
                    click.echo(f"  Updated title: {new_title}")
            
            if to_save:
                xmpfile.put_xmp(xmp)
                xmpfile.close_file(consts.XMP_CLOSE_SAFEUPDATE)
                processed += 1
        except Exception as e:
            click.echo(f"  Error processing: {e}", err=True)
        
        # Include file with end_name in processing
        if end_name is not None and file_name == end_name:
            break
    
    click.echo(f"\nTotal files processed: {processed}")
