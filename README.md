# Angle Viewer

Interactive Python tool for browsing and labeling **HMS** and **SHMS** angle plots.

## Features

- Browse images in order (`HMS_angle_<n>.jpg` or `SHMS_angle_<n>.jpg`)
- Supports both **HMS/** and **SHMS/** directories
- Navigate with:
  - `←` / `→` keys
  - Mouse scroll wheel
- Labels:
  - Press **Enter** to open a text box at the bottom of the screen
  - Type a floating-point label (e.g. `23.115`) and hit Enter
  - Labels are saved and displayed in overlay
- Missing runs are detected and reported at startup
- Quit:
  - Press **Q** or close window
  - A save dialog appears: enter a filename for your labels (default `labels.txt`)
- Handles corrupted/malformed images gracefully — shows an error placeholder instead of crashing

## Installation

Clone the repo and install in editable mode:

```bash
git clone https://github.com/mrcmor100/angle-viewer.git
cd angle-viewer
python -m venv .env
source .env/bin/activate
pip install -e .
