import ctypes
from ctypes.macholib.dyld import dyld_find
import ctypes.util
import os
import re


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

from libxmp import consts, XMPFiles, XMPMeta  # noqa
import piexif  # noqa


def date_taken(exif_data):
    dt_original = exif_data["Exif"][piexif.ExifIFD.DateTimeOriginal]
    # should be string orderable
    return dt_original.decode("ascii")


dir_path = "/Volumes/CrucialX8/photos/20240425_feracheval/xs10/TEST"
start_name = None  # "DSCF0603.JPG"
end_name = None  # "53391702206"

file_paths = os.listdir(dir_path)

images = []
for file_path in file_paths:
    if not file_path.upper().endswith(".JPG"):
        continue

    image_path = os.path.join(dir_path, file_path)
    exif_data = piexif.load(image_path)
    dt = date_taken(exif_data)
    images.append((image_path, dt))

ordered_images = sorted(images, key=lambda x: x[1])
for image in ordered_images:
    image_path, _ = image
    if start_name is None or os.path.basename(file_path) == start_name:
        is_process = True

    if not is_process:
        continue

    to_save = False

    xmpfile = XMPFiles(file_path=image_path, open_forupdate=True)
    xmp = xmpfile.get_xmp()
    ns = "http://purl.org/dc/elements/1.1/"
    title = xmp.get_property(ns, "dc:title[1]")

    title, n = re.subn(
        "@ Six$",
        "@ Sixt",
        title,
    )

    if n:
        to_save = True
        xmp.set_array_item(ns, "dc:title", 1, title)

    # TODO tags

    if to_save:
        xmpfile.put_xmp(xmp)
        xmpfile.close_file(consts.XMP_CLOSE_SAFEUPDATE)

    # incluide photo with end_name in processing
    if end_name is not None and os.path.basename(file_path) == end_name:
        break
