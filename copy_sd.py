from datetime import datetime, timedelta
import os
import shutil
import sys

import click

NAME = sys.argv[1]
if len(sys.argv) >= 2:
    DATE = sys.argv[2]
else:
    DATE = None


MEDIA = ["LUMIX", "XS10"]
output_parent_folder = "/Volumes/CrucialX8/photos"
MEDIA_FOLDER_MAPPING = {"LUMIX": "tz95", "XS10": "xs10"}


def create_folder_with_date(parent_folder, name, date):
    date_s = date.strftime("%Y%m%d")
    output_folder = os.path.join(parent_folder, f"{date_s}_{name}")
    os.makedirs(output_folder, exist_ok=True)
    return output_folder


def to_date(date_s):
    if not date_s or date_s == "TD":
        return datetime.now().date()
    if date_s == "YD":
        return datetime.now().date() - timedelta(days=1)
    return datetime.strptime(date_s, "%Y%m%d").date()


def get_volumes(media):
    volumes_path = "/Volumes"
    volumes = os.listdir(volumes_path)

    return [
        (volume, os.path.join(volumes_path, volume))
        for volume in volumes
        if volume in media
    ]


def check_volumes(volumes, output_folder_base, date):
    for volume, volume_path in volumes:
        media_folder = MEDIA_FOLDER_MAPPING[volume]
        output_folder = os.path.join(output_folder_base, media_folder)
        os.makedirs(output_folder, exist_ok=True)

        counter = 0
        for root, _, filenames in os.walk(volume_path):
            for filename in filenames:
                if not filename.lower().endswith(
                    (".jpg", ".jpeg", ".raf", ".raw", ".m4a")
                ):
                    continue
                file_path = os.path.join(root, filename)
                last_modified_date = datetime.fromtimestamp(os.path.getmtime(file_path))

                if last_modified_date.date() == date:
                    counter += 1
                    if counter % 20 == 0:
                        print(f"Copy #{counter}: {file_path}")
                    shutil.copy2(file_path, output_folder)


date = to_date(DATE)
output_folder_base = create_folder_with_date(output_parent_folder, NAME, date)
volumes = get_volumes(MEDIA)

volumes_s = ", ".join((v[0] for v in volumes))
if not click.confirm(
    f"The images will be copied from : {volumes_s} to {output_folder_base} "
    + f"(date: {date}) Confirm?"
):
    raise ValueError("No")
check_volumes(volumes, output_folder_base, date)
