#!/usr/bin/env python3
import os
import re
import sys
from collections import OrderedDict

import pygame

# -----------------------------
# Config
# -----------------------------
IMG_GLOB_PATTERN = r"SHMS_angle_(\d+)\.jpg"  # pattern to match and extract run number
LABELS_OUTFILE   = "labels.txt"             # where we write the output
WINDOW_TITLE     = "SHMS Angle Viewer"
FPS_LIMIT        = 30                       # throttle main loop to reduce CPU
CACHE_SIZE       = 3                        # keep prev/current/next surfaces cached

# -----------------------------
# Helpers: file discovery / gaps
# -----------------------------
def discover_images():
    files = []
    for f in os.listdir("."):
        m = re.match(IMG_GLOB_PATTERN, f)
        if m:
            files.append((int(m.group(1)), f))
    files.sort(key=lambda x: x[0])
    return files

def find_missing_ranges(sorted_numbers):
    """Return a list of strings like '1005' or '1007 … 1012' for gaps."""
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
# Tiny image cache (prev/cur/next)
# -----------------------------
class SurfaceCache:
    def __init__(self, max_items=CACHE_SIZE):
        self.max_items = max_items
        self.cache = OrderedDict()

    def get(self, key, loader):
        if key in self.cache:
            surf = self.cache.pop(key)
            self.cache[key] = surf  # move to end (recent)
            return surf
        surf = loader(key)
        self.cache[key] = surf
        if len(self.cache) > self.max_items:
            self.cache.popitem(last=False)  # evict LRU
        return surf

# -----------------------------
# Text input overlay
# -----------------------------
def text_input_overlay(screen, base_surface, prompt, initial=""):
    """
    Simple in-window text box: shows prompt + typed text.
    ENTER to accept, ESC to cancel, BACKSPACE to delete.
    Returns the string (can be empty if ESC).
    """
    font = pygame.font.Font(None, 36)
    text = initial
    entering = True
    clock = pygame.time.Clock()

    # semi-transparent overlay
    overlay = pygame.Surface(base_surface.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))

    while entering:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return text  # accept what we have if window closes
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    entering = False
                elif event.key == pygame.K_ESCAPE:
                    return ""  # cancel
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                else:
                    # append unicode char (allow digits, dot, minus, but also leave free-form)
                    if event.unicode:
                        text += event.unicode

        # draw base image
        screen.blit(base_surface, (0, 0))
        # screen.blit(base_surface, (0, 0))
        # screen.blit(overlay, (0, 0))

        # draw prompt + text
        line = font.render(f"{prompt}{text}", True, (255, 255, 255))
        pad = 10
        box_w, box_h = line.get_width() + 2*pad, line.get_height() + 2*pad
        box = pygame.Surface((box_w, box_h))
        box.set_alpha(220)
        box.fill((30, 30, 30))

        # compute centered x and bottom-y (10% margin from bottom)
        screen_w, screen_h = screen.get_size()
        x = (screen_w - box_w) // 2
        y = int(screen_h * 0.95 - box_h)

        screen.blit(box, (x, y))
        screen.blit(line, (x + pad, y + pad))


        pygame.display.flip()
        clock.tick(60)

    return text

# -----------------------------
# Main
# -----------------------------
def main():
    files = discover_images()
    if not files:
        print("No matching images found for pattern SHMS_angle_<number>.jpg")
        sys.exit(1)

    numbers = [n for n, _ in files]

    # Print summary to terminal
    print(f"Starting with run - {numbers[0]}")
    missing = find_missing_ranges(numbers)
    for mr in missing:
        print(f"No images for run(s) {mr}")

    # Init pygame
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()

    # Loader for cache
    def load_surface_by_index(idx):
        _, fname = files[idx]
        # don't convert here until after display mode is set
        return pygame.image.load(fname)

    # load first image to get size
    current_idx = 0
    first_surface = load_surface_by_index(current_idx)
    screen = pygame.display.set_mode(first_surface.get_size())

    # now that a display exists, we can convert the first one
    first_surface = first_surface.convert()
    cache = SurfaceCache(CACHE_SIZE)

    # show first image, set fixed window size to image size
    current_idx = 0
    first_surface = load_surface_by_index(current_idx)
    screen = pygame.display.set_mode(first_surface.get_size())
    cache = SurfaceCache(CACHE_SIZE)

    labels = {}  # num -> string label

    def draw_image(idx):
        num, fname = files[idx]
        surf = cache.get(idx, load_surface_by_index).convert()
        screen.blit(surf, (0, 0))

        # Optional overlay: show run and existing label (if any)
        overlay_font = pygame.font.Font(None, 28)
        info = f"Run {num} ({idx+1}/{len(files)})"
        if num in labels and labels[num] != "":
            info += f' | label: "{labels[num]}"'
        info_surface = overlay_font.render(info, True, (255, 255, 255))
        # draw a dark bg behind text for readability
        bg = pygame.Surface((info_surface.get_width() + 16, info_surface.get_height() + 10))
        bg.set_alpha(160)
        bg.fill((0, 0, 0))
        x, y = 10, screen.get_height() - info_surface.get_height() - 15
        screen.blit(bg, (x, y))
        screen.blit(info_surface, (x + 8, y + 5))

        pygame.display.set_caption(f"{WINDOW_TITLE} — Run {num} [{idx+1}/{len(files)}]")
        pygame.display.flip()

        # Pre-warm neighbors in cache for instant flip
        if idx - 1 >= 0:
            cache.get(idx - 1, load_surface_by_index)
        if idx + 1 < len(files):
            cache.get(idx + 1, load_surface_by_index)

    draw_image(current_idx)

    running = True

    def save_log():
        with open(LABELS_OUTFILE, "w") as f:
            f.write(f"Starting with run - {numbers[0]}\n")
            for mr in missing:
                f.write(f"No images for run(s) {mr}\n")
            for num in sorted(labels.keys()):
                f.write(f'run {num} labeled "{labels[num]}"\n')
        print(f"Saved log to {LABELS_OUTFILE}")

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_log()
                running = False
            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0 and current_idx > 0:   # up → prev
                    current_idx -= 1
                    draw_image(current_idx)
                elif event.y < 0 and current_idx < len(files) - 1:  # down → next
                    current_idx += 1
                    draw_image(current_idx)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    if current_idx < len(files) - 1:
                        current_idx += 1
                        draw_image(current_idx)
                elif event.key == pygame.K_LEFT:
                    if current_idx > 0:
                        current_idx -= 1
                        draw_image(current_idx)
                elif event.key == pygame.K_RETURN:
                    num, _ = files[current_idx]
                    base_surf = cache.get(current_idx, load_surface_by_index)
                    prompt = f'Label for run {num}: '
                    entered = text_input_overlay(screen, base_surf, prompt, initial=labels.get(num, ""))

                    # Always update the label, even if blank (means clear it)
                    labels[num] = entered
                    if entered != "":
                        print(f'run {num} labeled "{entered}"')
                    else:
                        print(f'run {num} label cleared')
                    draw_image(current_idx)
                elif event.key == pygame.K_s:
                    save_log()
                elif event.key == pygame.K_q:
                    save_log()
                    running = False

        clock.tick(FPS_LIMIT)  # keep CPU cool

    pygame.quit()

if __name__ == "__main__":
    main()
