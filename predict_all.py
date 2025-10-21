import os
import pandas as pd
from PIL import Image
import numpy as np
from tqdm import tqdm
from sklearn.cluster import KMeans
import colorsys
import random

# ----------------------------
# Config
# ----------------------------
IMAGE_DIR = "images_all"      # Folder with all shirt images
CSV_FILE = "image_colors.csv" # Output CSV file
NUM_CLUSTERS = 3              # KMeans clusters

# Predefined colors in HSV (Hue 0–360, Sat 0–1, Val 0–1)
COLOR_HSV_MAP = {
    "red": ((0, 15), (0.5, 1.0), (0.2, 1.0)),
    "pink": ((320, 345), (0.3, 1.0), (0.5, 1.0)),
    "yellow": ((25, 45), (0.4, 1.0), (0.5, 1.0)),
    "green": ((60, 160), (0.3, 1.0), (0.2, 1.0)),
    "blue": ((180, 250), (0.3, 1.0), (0.2, 1.0)),
    "black": ((0, 360), (0, 0.3), (0, 0.25)),
    "white": ((0, 360), (0, 0.2), (0.8, 1.0)),
    "gray": ((0, 360), (0, 0.25), (0.25, 0.8)),
    "brown": ((20, 35), (0.4, 1.0), (0.2, 0.6))
}

# Some random materials to assign
MATERIALS = ["Cotton", "Polyester", "Silk", "Linen", "Denim", "Wool"]

# ----------------------------
# Helper Functions
# ----------------------------
def map_hsv_to_color(h, s, v):
    """Map HSV values to predefined color names"""
    for color, ((h_min, h_max), (s_min, s_max), (v_min, v_max)) in COLOR_HSV_MAP.items():
        if h_min <= h <= h_max and s_min <= s <= s_max and v_min <= v <= v_max:
            return color
    return "unknown"

def detect_color_kmeans(image_path):
    """Detect dominant shirt color while ignoring white background"""
    img = Image.open(image_path).convert("RGB")
    img = img.resize((50, 50))
    arr = np.array(img) / 255.0
    pixels = arr.reshape(-1, 3)

    # Convert RGB → HSV
    hsv_pixels = np.array([colorsys.rgb_to_hsv(*p) for p in pixels])
    hsv_pixels[:, 0] *= 360  # Hue in degrees

    # Mask to ignore white/bright background
    mask = ~((hsv_pixels[:, 1] < 0.15) & (hsv_pixels[:, 2] > 0.9))
    filtered_pixels = pixels[mask]
    if len(filtered_pixels) == 0:
        filtered_pixels = pixels  # fallback if all removed

    # Run KMeans
    kmeans = KMeans(n_clusters=min(NUM_CLUSTERS, len(filtered_pixels)), random_state=42)
    kmeans.fit(filtered_pixels)
    counts = np.bincount(kmeans.labels_)
    dominant_idx = np.argmax(counts)
    dominant_rgb = kmeans.cluster_centers_[dominant_idx]

    # Convert dominant color to HSV
    h, s, v = colorsys.rgb_to_hsv(*dominant_rgb)
    h *= 360
    color_name = map_hsv_to_color(h, s, v)
    probability = counts[dominant_idx] / len(filtered_pixels)
    return color_name, probability

# ----------------------------
# Process All Images
# ----------------------------
image_files = [f for f in os.listdir(IMAGE_DIR)
               if f.lower().endswith((".jpg", ".jpeg", ".png"))]

results = []

for img_file in tqdm(image_files, desc="Detecting colors"):
    img_path = os.path.join(IMAGE_DIR, img_file)
    try:
        color, prob = detect_color_kmeans(img_path)
    except Exception as e:
        print(f"Error processing {img_file}: {e}")
        color, prob = "unknown", 0.0

    # Generate product info
    name = f"{color.capitalize()} Shirt" if color != "unknown" else "Stylish Shirt"
    price = random.randint(1500, 3000)
    mrp = price + random.randint(300, 800)
    material = random.choice(MATERIALS)

    results.append({
        "image": img_file,
        "predicted_color": color,
        "aquarius": f"{prob * 100:.0f}%",
        "name": name,
        "price": price,
        "mrp": mrp,
        "material": material
    })

# ----------------------------
# Save Results
# ----------------------------
df = pd.DataFrame(results)
df.to_csv(CSV_FILE, index=False)
print(f"\n✅ Color detection & product info saved to: {CSV_FILE}")
