import os
import shutil

import click

BASE_DIR = "/Volumes/CrucialX8/photos"

folder_std = "xs20"
folder_zoom = "tz95"


@click.command()
@click.argument("folder_path")
def copy_zoom_to_std(folder_path):
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


if __name__ == "__main__":
    copy_zoom_to_std()
