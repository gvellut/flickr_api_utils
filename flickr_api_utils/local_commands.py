"""Local file operations commands."""
import logging
import os

import click
import piexif
from PIL import ExifTags, Image

from .copy_sd import copy_sd_main


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
    import shutil
    
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
    # Import the main function from the existing module
    copy_sd_main(name, date_spec, is_eject)
