from collections import namedtuple
from datetime import datetime, timedelta
import os
import shutil
import subprocess
import traceback

import attr
import click

MEDIA = ["LUMIX", "XS10", "RX100M7", "XS20"]
output_parent_folder = "/Volumes/CrucialX8/photos"
MEDIA_FOLDER_MAPPING = {
    "LUMIX": "tz95",
    "XS10": "xs10",
    "RX100M7": "rx100",
    "XS20": "xs20",
}

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
    prefix = "since:"
    if date_s.startswith(prefix):
        date_s = date_s[len(prefix) :]
        date_since = datetime.strptime(date_s, "%Y%m%d").date()
        return filter_after(find_all_dates(volume.path), date_since)

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


@click.command()
@click.option(
    "--name",
    "name",
    required=True,
    help="Folder name",
)
@click.option(
    "--date",
    "date_spec",
    default="TD",
    help="Date spec",
    show_default=True,
)
@click.option(
    "--no-eject",
    "is_eject",
    default=True,
    help="Eject SD",
    is_flag=True,
)
def main(name, date_spec, is_eject):
    volume = get_volume(MEDIA)

    if not volume:
        print("No relevant SD card. Volume not renamed?")
        exit(1)

    dates = to_dates(date_spec, volume)
    if not isinstance(dates, list):
        dates = [dates]
    if not dates:
        print("No image found: Is the SD card inserted and mounted?")
        exit(1)

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
        print("Aborted by user")
        exit(1)

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


if __name__ == "__main__":
    main()
