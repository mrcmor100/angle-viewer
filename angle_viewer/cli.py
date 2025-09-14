import sys
from .viewer import run_viewer

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(
            "Usage:\n"
            "  angle-viewer HMS|SHMS [start_index]\n\n"
            "Arguments:\n"
            "  HMS|SHMS       Required. Which spectrometer's images to view.\n"
            "  start_index    Optional. Integer index to start viewing from (0-based).\n\n"
            "Examples:\n"
            "  angle-viewer HMS\n"
            "      Start browsing HMS images from the first file.\n\n"
            "  angle-viewer SHMS 1489\n"
            "      Start browsing SHMS images at index 1489.\n"
        )
        sys.exit(0)

    if sys.argv[1] not in ("HMS", "SHMS"):
        print("Error: First argument must be HMS or SHMS. Use -h for help.")
        sys.exit(1)

    arm = sys.argv[1]
    start_index = 0

    if len(sys.argv) >= 3:
        try:
            start_index = int(sys.argv[2])
        except ValueError:
            print(f"Invalid start index: {sys.argv[2]!r}, must be an integer")
            sys.exit(1)

    run_viewer(arm, start_index)
