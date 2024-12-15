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


def dirname_with_date(parent_folder, name, dates):
    if isinstance(dates[0], DateRange):
        # all the same anyway
        date_r = dates[0]
        if date_r.end:
            f_date = date_r.end
        elif date_r.start:
            f_date = date_r.start
        else:
            # today
            f_date = datetime.now().date()
    else:
        # can be different if L was used
        f_date = min(dates)
    date_s = f_date.strftime(OUTPUT_DATE_FMT)
    output_folder = os.path.join(parent_folder, f"{date_s}_{name}")

    return output_folder


def to_dates(date_s, volumes):
    if date_s == "TD":
        # same date for all volumes
        return [datetime.now().date()] * len(volumes)

    if date_s == "YD":
        return [datetime.now().date() - timedelta(days=1)] * len(volumes)

    if date_s == "YD2":
        return [datetime.now().date() - timedelta(days=2)] * len(volumes)

    if date_s == "YD3":
        return [datetime.now().date() - timedelta(days=3)] * len(volumes)

    if date_s == "L":
        # L for latest
        dates = [find_latest_date(v) for v in volumes]
        return dates

    if date_s == "L2":
        dates = [find_latest_date(v, rank=1) for v in volumes]
        return dates

    if date_s == "L3":
        dates = [find_latest_date(v, rank=2) for v in volumes]
        return dates

    if "-" in date_s:
        date_range = [parse_date_range(date_s)] * len(volumes)
        return date_range

    return [datetime.strptime(date_s, DATE_FMT).date()] * len(volumes)


def parse_date_range(date_range_str):
    dates = date_range_str.split("-")
    start_date = datetime.strptime(dates[0], DATE_FMT).date() if dates[0] else None
    end_date = (
        datetime.strptime(dates[1], DATE_FMT).date()
        if len(dates) > 1 and dates[1]
        else None
    )

    return DateRange(start_date, end_date)


def find_latest_date(volume, rank=0):
    volume_path = volume[1]
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
    return sorted(dates, reverse=True)[rank]


def get_volumes(media):
    volumes_path = "/Volumes"
    volumes = os.listdir(volumes_path)

    return [
        (volume, os.path.join(volumes_path, volume))
        for volume in volumes
        if volume in media
    ]


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


def copy_to_volumes(volumes, output_folder_base, dates):
    os.makedirs(output_folder_base, exist_ok=True)

    for i, (volume, volume_path) in enumerate(volumes):
        media_folder = MEDIA_FOLDER_MAPPING[volume]
        output_folder = os.path.join(output_folder_base, media_folder)
        os.makedirs(output_folder, exist_ok=True)

        counter = 0
        for root, _, filenames in os.walk(volume_path):
            for filename in filenames:
                if not filter_relevant_image(filename):
                    continue
                file_path = os.path.join(root, filename)
                last_modified_date = datetime.fromtimestamp(os.path.getmtime(file_path))

                if filter_by_date(last_modified_date.date(), dates[i]):
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
    volumes = get_volumes(MEDIA)

    if not volumes:
        print("No relevant SD card. Volume not renamed?")
        exit(1)

    dates = to_dates(date_spec, volumes)
    if not dates:
        # if used with L : need the SD card to be available
        # to_dates will be None if not the case
        print("No image found: Is the SD card inserted and mounted?")
        exit(1)
    output_folder_base = dirname_with_date(output_parent_folder, name, dates)

    volumes_s = ", ".join((v[0] for v in volumes))
    volume_mapping = [MEDIA_FOLDER_MAPPING[volume[0]] for volume in volumes]
    volume_mapping_s = ", ".join(volume_mapping)
    dates_s = ", ".join([date_to_str(d) for d in dates])
    if not click.confirm(
        f"The images will be copied from : {volumes_s} to {output_folder_base} "
        f"[folders {volume_mapping_s}] - (dates: {dates_s})\nConfirm?"
    ):
        print("Aborted by user")
        exit(1)

    copy_to_volumes(volumes, output_folder_base, dates)

    for volume in volumes:
        try:
            if is_eject:
                print(f"Ejecting {volume[1]} ...")
                eject_volume(volume[0])
        except Exception:
            print(f"Error ejecting {volume}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
