import logging
import os

import click
import piexif
from PIL import ExifTags, Image

logging.basicConfig(level=logging.INFO)


@click.command()
@click.argument("input_folder")
@click.argument("output_folder")
def main(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    count = 0
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
            logging.info(f"Processing file: {filename}")
            img_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            crop_image(img_path, output_path)

            count += 1
            # if count > 5:
            #     return


def crop_image(img_path, output_path):
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

            # base, ext = os.path.splitext(output_path)
            # output_path_intermediate = f"{base}-intermediate{ext}"
            # img.save(output_path_intermediate)

            new_height = int(img_rot.width * 4 / 3)
            img_cropped = img_rot.crop((0, 0, img_rot.width, new_height))
        else:  # Horizontal image
            new_width = int(img.height * 4 / 3)
            left = img.width - new_width
            img_cropped = img.crop((left, 0, img.width, img.height))

        if "exif" in img.info:
            exif_dict = piexif.load(img.info["exif"])
            exif_dict["0th"][piexif.ImageIFD.Orientation] = 1
            exif_bytes = piexif.dump(exif_dict)
            img_cropped.save(
                output_path, "JPEG", subsampling=0, quality=95, exif=exif_bytes
            )
        else:
            img_cropped.save(output_path, "JPEG", subsampling=0, quality=95)


if __name__ == "__main__":
    main()
