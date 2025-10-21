import os
import shutil
from PIL import Image
import numpy as np
from tqdm import tqdm

# ----------------------------
# Config
# ----------------------------
INPUT_DIR = "images_all"        # Your original images
OUTPUT_DIR = "dataset_labeled"  # Auto-created folders for each color
MIN_WIDTH = 50                  # Minimum width to consider image valid
MIN_HEIGHT = 50                 # Minimum height

# Pre-defined color thresholds (you can tweak)
COLOR_RANGES = {
    "red":      {"R": (150, 255), "G": (0, 100), "B": (0, 100)},
    "pink":     {"R": (200, 255), "G": (100, 180), "B": (150, 220)},
    "white":    {"R": (200, 255), "G": (200, 255), "B": (200, 255)},
    "blue":     {"R": (0, 100), "G": (0, 100), "B": (150, 255)},
    "yellow":   {"R": (200, 255), "G": (200, 255), "B": (0, 100)},
    "green":    {"R": (0, 100), "G": (150, 255), "B": (0, 100)},
    "black":    {"R": (0, 80), "G": (0, 80), "B": (0, 80)},
}

# ----------------------------
# Helper function: detect color
# ----------------------------
def detect_color(image_path):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((50, 50))  # downscale for faster processing
    arr = np.array(img)
    
    # Calculate average RGB
    avg_color = arr.mean(axis=(0, 1))  # [R, G, B]
    R, G, B = avg_color
    # print(image_path, avg_color)
    
    for color, ranges in COLOR_RANGES.items():
        r_min, r_max = ranges["R"]
        g_min, g_max = ranges["G"]
        b_min, b_max = ranges["B"]
        if r_min <= R <= r_max and g_min <= G <= g_max and b_min <= B <= b_max:
            return color
    return "unknown"

# ----------------------------
# Create output folders
# ----------------------------
for color in COLOR_RANGES.keys():
    os.makedirs(os.path.join(OUTPUT_DIR, color), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "unknown"), exist_ok=True)

# ----------------------------
# Process all images
# ----------------------------
image_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith((".jpg", ".png", ".jpeg"))]

for img_file in tqdm(image_files, desc="Auto-labeling images"):
    img_path = os.path.join(INPUT_DIR, img_file)
    
    try:
        color = detect_color(img_path)
    except Exception as e:
        print(f"Error processing {img_file}: {e}")
        color = "unknown"

    # Move to folder
    dest_path = os.path.join(OUTPUT_DIR, color, img_file)
    shutil.copy(img_path, dest_path)

print("✅ Auto-labeling finished. Check folder 'dataset_labeled/' for colored folders.")
