#!/bin/bash

# install exiftool + gegl with Homebrew

# --- Configuration ---
INPUT_DIR="/Volumes/CrucialX8/photos/20241225_geneve/gegl"
OUTPUT_DIR="/Volumes/CrucialX8/photos/20241225_geneve/gegl_exp"
EXPOSURE_VAL="0.80"
BLACK_LEVEL_VAL="0.02"
JPG_QUALITY="90"
IMAGE_PATTERNS=("*.jpg" "*.jpeg") 
# --- End Configuration ---

# --- Check for dependencies ---
if ! command -v gegl &> /dev/null; then
    echo "Error: 'gegl' command not found. Please install it."
    exit 1
fi
if ! command -v exiftool &> /dev/null; then
    echo "Error: 'exiftool' command not found. Please install it."
    echo "(e.g., sudo apt install libimage-exiftool-perl or brew install exiftool)"
    exit 1
fi
# --- End Check ---


mkdir -p "$OUTPUT_DIR"

if [ ! -d "$INPUT_DIR" ]; then
  echo "Error: Input directory '$INPUT_DIR' not found."
  exit 1
fi

echo "Starting batch exposure adjustment + EXIF copy..."
echo "Input directory: $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo "Exposure value: $EXPOSURE_VAL"
echo "JPEG Quality: $JPG_QUALITY"
echo "Processing patterns: ${IMAGE_PATTERNS[*]}"
echo "---"


shopt -s nullglob
shopt -s nocaseglob # Match file patterns case-insensitively (e.g., *.jpg matches *.JPG)

for pattern in "${IMAGE_PATTERNS[@]}"; do
  # Note: nocaseglob handles case-insensitivity, so looping through patterns might be redundant
  # if they only differ by case. Consider simplifying IMAGE_PATTERNS if only JPG/JPEG is needed.
  # For now, keeping the loop as it was.
  for infile in "$INPUT_DIR"/$pattern; do
    if [[ -f "$infile" ]]; then
      filename=$(basename "$infile")
      base_filename="${filename%.*}"
      # Construct output filename with lowercase .jpg extension
      outfile="$OUTPUT_DIR/${base_filename}_exp.jpg"

      echo "Processing '$filename' -> '$outfile'"

      # STEP 1: Process image with GEGL
      gegl_success=true
      
      # test with black_level="$BLACK_LEVEL_VAL"
      
      gegl -i "$infile"  -o "$outfile" -- exposure exposure="$EXPOSURE_VAL" || gegl_success=false

      # Check if GEGL step was successful before attempting EXIF copy
      if [[ "$gegl_success" = true ]]; then
          # STEP 2: Copy EXIF data using exiftool
          echo "  Copying EXIF from '$infile' to '$outfile'..."
          # Add -m to ignore minor errors, which can sometimes happen with format conversions
          exiftool -m -tagsFromFile "$infile" -all:all -overwrite_original "$outfile"
          if [[ $? -ne 0 ]]; then
             echo "  Warning: exiftool encountered an error for '$filename' (output: '$outfile')."
             # Decide if you want to keep the file without EXIF or delete it
             # Example: rm "$outfile"
          fi
      else
         echo "  Skipping EXIF copy for '$filename' due to GEGL processing error or unsupported format."
         # Clean up potentially partially created/empty output file if GEGL failed
         # (This check assumes GEGL might leave an empty file on error)
         if [[ -f "$outfile" ]]; then
            # Be cautious with rm - check file size or content if needed
             echo "  Cleaning up potentially incomplete '$outfile'."
             rm "$outfile"
         fi
      fi

    fi # end check if -f infile
  done # end loop through files in pattern
done # end loop through patterns

shopt -u nullglob
shopt -u nocaseglob # Unset case-insensitive matching

echo "---"
echo "Batch processing complete."
