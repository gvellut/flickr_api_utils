import fnmatch
import os

listOfFiles = sorted(
    os.listdir("/Volumes/Samsung T5 B2/backup/photos/travel/2017 - 2020 Annecy")
)
pattern = "*_ok"
for entry in listOfFiles:
    if not fnmatch.fnmatch(entry, pattern):
        print(entry)
