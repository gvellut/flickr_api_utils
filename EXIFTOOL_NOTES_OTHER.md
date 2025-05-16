# Exiftool

```sh
exiftool -m -XMP /Users/guilhem/Pictures/camera/20191108_fier/100MSDCF/DSC09670\ copy.JPG  -b
exiftool -m "-XMP-dc:title<XMP:City" /Users/guilhem/Pictures/camera/20210417_grottesveyrier/xt30/corr -overwrite_original

Purge city:
exiftool -m "-XMP:City=" /Users/guilhem/Pictures/camera/20191108_fier/100MSDCF/ -overwrite_original 

exiftool -m "-XMP-dc:title<XMP:TransmissionReference" _to_correct -overwrite_original

exiftool -m "-XMP-dc:title<IPTC:Country-PrimaryLocationCode" _to_correct -overwrite_original 

exiftool -lensmake=7Artisans -lensmodel="7Artisans 18mm F6.3 cap lens" -fnumber=”6.3” -aperturevalue=”6.3”  -focallength=18 -lens="18.0 mm" -lensinfo="18mm f/6.3" *  -overwrite_original

exiftool -lensmake=Meike -lensmodel="Meike 25mm F1.8"  -focallength=25 -lens="25.0 mm" *  -overwrite_original

exiftool -lensmake=Meike -lensmodel="Meike 35mm F1.7"  -focallength=35 -lens="35.0 mm" *  -overwrite_original

exiftool -lensmake=Samyang -lensmodel="Samyang 12mm f/2.0 NCS CS"  -focallength=12 -lens="12.0 mm" *  -overwrite_original 

exiftool -lensmake="TTArtisan" -lensmodel="TTArtisan APS-C 40mm F2.8 MACRO"  -focallength="40" -lens="40.0 mm" *  -overwrite_original

exiftool -lensmake="TTArtisan" -lensmodel="TTArtisan APS-C 23mm F1.4"  -focallength="23" -lens="23 mm" *  -overwrite_original
```

# List all tags

```sh
exiftool DSCF5838.JPG -a -G1 -s
```

# Exposure correction +0.4 (cf gegl_exposure.sh for replacement)

```sh
#!/bin/bash
for f in $@
do
  echo "processing $f..."
  outf="${f%%.*}_exp0d4.JPG"
  gegl -i "$f" -o "$outf" -- exposure exposure=0.4
  exiftool -tagsfromfile "$f" "$outf" -overwrite_original
  mv "$outf" "$f"
done
```

# Changement quality JPEG pour xt30 trop grand (avec brew install imagemagick)

```sh
mogrify -monitor -quality 95% DSCF*.JPG
```