import os
import shutil

folder_path = (
    "/Users/guilhem/Pictures/camera/___uploaded/20210508_foretlanfon_ok/autocorrect2"
)
original_folder_path = (
    "/Users/guilhem/Pictures/camera/___uploaded/20210508_foretlanfon_ok/xt30"
)


for file_name in os.listdir(folder_path):
    if not file_name.endswith(".JPG"):
        continue
    original_file_path = os.path.join(original_folder_path, file_name)
    shutil.copy(original_file_path, folder_path)
