from datetime import datetime, timedelta
import os
import shutil
import subprocess
import sys
import traceback

import click

NAME = sys.argv[1]
if len(sys.argv) >= 2:
    DATE = sys.argv[2]
else:
    DATE = None


MEDIA = ["LUMIX", "XS10", "RX100M7"]
output_parent_folder = "/Volumes/CrucialX8/photos"
MEDIA_FOLDER_MAPPING = {"LUMIX": "tz95", "XS10": "xs10", "RX100M7": "rx100"}


def dirname_with_date(parent_folder, name, date):
    date_s = date.strftime("%Y%m%d")
    output_folder = os.path.join(parent_folder, f"{date_s}_{name}")

    return output_folder


def to_dates(date_s, volumes):
    if not date_s or date_s == "TD":
        # same date for all volumes
        return [datetime.now().date()] * len(volumes)

    if date_s == "YD":
        return [datetime.now().date() - timedelta(days=1)] * len(volumes)

    if date_s == "L":
        # L for latest
        dates = [find_latest_date(v) for v in volumes]
        return dates

    return [datetime.strptime(date_s, "%Y%m%d").date()] * len(volumes)


def find_latest_date(volume):
    volume_path = volume[1]
    dates = []
    for root, _, filenames in os.walk(volume_path):
        for filename in filenames:
            if not filter_relevant_image(filename):
                continue
            file_path = os.path.join(root, filename)
            last_modified_date = datetime.fromtimestamp(os.path.getmtime(file_path))
            dates.append(last_modified_date.date())
    return max(dates)


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

                if last_modified_date.date() == dates[i]:
                    counter += 1
                    if counter % 20 == 0:
                        print(f"Copy #{counter}: {file_path}")
                    shutil.copy2(file_path, output_folder)


volumes = get_volumes(MEDIA)

if not volumes:
    print("No relevant SD card. Volume not renamed?")
    exit(1)


dates = to_dates(DATE, volumes)
# arbitrarily take the first date
f_date = min(dates)
output_folder_base = dirname_with_date(output_parent_folder, NAME, f_date)

volumes_s = ", ".join((v[0] for v in volumes))
volume_mapping = [MEDIA_FOLDER_MAPPING[volume[0]] for volume in volumes]
volume_mapping_s = ", ".join(volume_mapping)
dates_s = ", ".join([d.isoformat() for d in dates])
if not click.confirm(
    f"The images will be copied from : {volumes_s} to {output_folder_base} "
    f"[folders {volume_mapping_s}] - (dates: {dates_s})\nConfirm?"
):
    print("Aborted by user")
    exit(1)


copy_to_volumes(volumes, output_folder_base, dates)

for volume in volumes:
    try:
        print(f"Ejecting {volume[1]} ...")
        eject_volume(volume[0])
    except Exception:
        print(f"Error ejecting {volume}")
        traceback.print_exc()
