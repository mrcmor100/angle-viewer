import os
import re
from collections import OrderedDict
import pygame

FPS_LIMIT = 30
CACHE_SIZE = 3


# -----------------------------
# Tiny image cache (prev/cur/next)
# -----------------------------
class SurfaceCache:
    def __init__(self, max_items=CACHE_SIZE):
        self.max_items = max_items
        self.cache = OrderedDict()

    def get(self, key, loader):
        if key in self.cache:
            surf = self.cache.pop(key)
            self.cache[key] = surf
            return surf
        surf = loader(key)
        self.cache[key] = surf
        if len(self.cache) > self.max_items:
            self.cache.popitem(last=False)
        return surf


# -----------------------------
# Text input overlay
# -----------------------------
def text_input_overlay(screen, base_surface, prompt, initial=""):
    font = pygame.font.Font(None, 36)
    text = initial
    entering = True
    clock = pygame.time.Clock()

    while entering:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return text
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    entering = False
                elif event.key == pygame.K_ESCAPE:
                    return ""
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    if event.unicode:
                        text += event.unicode

        screen.blit(base_surface, (0, 0))

        line = font.render(f"{prompt}{text}", True, (255, 255, 255))
        pad = 10
        box_w, box_h = line.get_width() + 2 * pad, line.get_height() + 2 * pad
        box = pygame.Surface((box_w, box_h))
        box.set_alpha(220)
        box.fill((30, 30, 30))

        screen_w, screen_h = screen.get_size()
        x = (screen_w - box_w) // 2
        y = int(screen_h * 0.9 - box_h)

        screen.blit(box, (x, y))
        screen.blit(line, (x + pad, y + pad))

        pygame.display.flip()
        clock.tick(60)

    return text


# -----------------------------
# Helpers
# -----------------------------
def discover_images(pattern, directory):
    files = []
    for f in os.listdir(directory):
        m = re.match(pattern, f)
        if m:
            files.append((int(m.group(1)), os.path.join(directory, f)))
    files.sort(key=lambda x: x[0])
    return files


def find_missing_ranges(sorted_numbers):
    missing = []
    if not sorted_numbers:
        return missing
    for prev, curr in zip(sorted_numbers, sorted_numbers[1:]):
        if curr > prev + 1:
            if curr == prev + 2:
                missing.append(f"{prev+1}")
            else:
                missing.append(f"{prev+1} … {curr-1}")
    return missing


# -----------------------------
# Main viewer
# -----------------------------
def run_viewer(arm: str, start_index: int = 0):
    """
    Run the HMS/SHMS angle viewer.

    Parameters
    ----------
    arm : str
        "HMS" or "SHMS"
    start_index : int, optional
        Index of image to start on (default = 0).
    """

    img_dir = arm
    img_pattern = rf"{arm}_angle_(\d+)\.jpg"
    window_title = f"{arm} Angle Viewer"

    files = discover_images(img_pattern, img_dir)
    if not files:
        print(f"No matching images found in {img_dir}/ with pattern {arm}_angle_<number>.jpg")
        return

    numbers = [n for n, _ in files]
    missing = find_missing_ranges(numbers)

    print(f"Starting with run - {numbers[0]}")
    for mr in missing:
        print(f"No images for run(s) {mr}")

    pygame.init()
    pygame.display.set_caption(window_title)
    clock = pygame.time.Clock()

    # Safe loader with error placeholder
    def load_surface_by_index(idx):
        _, fname = files[idx]
        try:
            return pygame.image.load(fname)
        except Exception as e:
            w, h = screen.get_size() if "screen" in locals() else (800, 600)
            surf = pygame.Surface((w, h))
            surf.fill((50, 0, 0))
            font = pygame.font.Font(None, 36)
            msg1 = font.render("Error loading file:", True, (255, 255, 255))
            msg2 = font.render(fname, True, (255, 200, 200))
            msg3 = font.render(str(e), True, (200, 200, 0))
            surf.blit(msg1, (20, 20))
            surf.blit(msg2, (20, 60))
            surf.blit(msg3, (20, 100))
            return surf

    # clamp start index
    if start_index < 0 or start_index >= len(files):
        start_index = 0

    current_idx = start_index
    first_surface = load_surface_by_index(current_idx)
    screen = pygame.display.set_mode(first_surface.get_size())
    first_surface = first_surface.convert()
    cache = SurfaceCache(CACHE_SIZE)

    labels = {}
    labels_outfile = "labels.txt"

    def draw_image(idx):
        num, fname = files[idx]
        surf = cache.get(idx, load_surface_by_index).convert()
        screen.blit(surf, (0, 0))

        overlay_font = pygame.font.Font(None, 28)
        info = f"Run {num} ({idx+1}/{len(files)})"
        if num in labels and labels[num] != "":
            info += f' | label: "{labels[num]}"'
        info_surface = overlay_font.render(info, True, (255, 255, 255))

        bg = pygame.Surface((info_surface.get_width() + 16, info_surface.get_height() + 10))
        bg.set_alpha(160)
        bg.fill((0, 0, 0))
        x, y = 10, screen.get_height() - info_surface.get_height() - 15
        screen.blit(bg, (x, y))
        screen.blit(info_surface, (x + 8, y + 5))

        pygame.display.set_caption(f"{window_title} — Run {num} [{idx+1}/{len(files)}]")
        pygame.display.flip()

        if idx - 1 >= 0:
            cache.get(idx - 1, load_surface_by_index)
        if idx + 1 < len(files):
            cache.get(idx + 1, load_surface_by_index)

    def save_log(outfile):
        with open(outfile, "w") as f:
            f.write(f"Starting with run - {numbers[0]}\n")
            for mr in missing:
                f.write(f"No images for run(s) {mr}\n")
            for num in sorted(labels.keys()):
                f.write(f'run {num} labeled "{labels[num]}"\n')
        print(f"Saved log to {outfile}")

    draw_image(current_idx)
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                base_surf = cache.get(current_idx, load_surface_by_index)
                name = text_input_overlay(screen, base_surf, "Save log as: ", initial=labels_outfile)
                if name.strip() != "":
                    labels_outfile = name.strip()
                save_log(labels_outfile)
                running = False

            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0 and current_idx > 0:
                    current_idx -= 1
                    draw_image(current_idx)
                elif event.y < 0 and current_idx < len(files) - 1:
                    current_idx += 1
                    draw_image(current_idx)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT and current_idx < len(files) - 1:
                    current_idx += 1
                    draw_image(current_idx)
                elif event.key == pygame.K_LEFT and current_idx > 0:
                    current_idx -= 1
                    draw_image(current_idx)
                elif event.key == pygame.K_RETURN:
                    num, _ = files[current_idx]
                    base_surf = cache.get(current_idx, load_surface_by_index)
                    entered = text_input_overlay(screen, base_surf, f'Label for run {num}: ',
                                                 initial=labels.get(num, ""))
                    labels[num] = entered
                    if entered != "":
                        print(f'run {num} labeled "{entered}"')
                    else:
                        print(f'run {num} label cleared')
                    draw_image(current_idx)
                elif event.key == pygame.K_q:
                    base_surf = cache.get(current_idx, load_surface_by_index)
                    name = text_input_overlay(screen, base_surf, "Save log as: ", initial=labels_outfile)
                    if name.strip() != "":
                        labels_outfile = name.strip()
                    save_log(labels_outfile)
                    running = False

        clock.tick(FPS_LIMIT)

    pygame.quit()
