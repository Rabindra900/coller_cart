# gan_generator.py
"""
GAN Simulator for ColorKart
---------------------------
Simulates shirt generation using PIL and AI-powered color rendering.
"""

from PIL import Image, ImageDraw
import numpy as np

# Define base shirt shape (silhouette simulation)
def _create_shirt_shape(size=(512, 512), color=(255, 255, 255)):
    img = Image.new("RGB", size, (240, 240, 240))
    draw = ImageDraw.Draw(img)

    # Basic shirt outline
    w, h = size
    shirt_color = color

    # Shirt body
    draw.rectangle([w * 0.25, h * 0.25, w * 0.75, h * 0.85], fill=shirt_color, outline=(80, 80, 80))

    # Sleeves
    draw.polygon([(w * 0.25, h * 0.25), (w * 0.05, h * 0.4), (w * 0.25, h * 0.45)], fill=shirt_color, outline=(80, 80, 80))
    draw.polygon([(w * 0.75, h * 0.25), (w * 0.95, h * 0.4), (w * 0.75, h * 0.45)], fill=shirt_color, outline=(80, 80, 80))

    # Neck area
    draw.ellipse([w * 0.4, h * 0.15, w * 0.6, h * 0.3], fill=(220, 220, 220), outline=(50, 50, 50))
    return img


# Define color presets
COLOR_MAP = {
    "red": (220, 20, 60),
    "blue": (30, 144, 255),
    "white": (245, 245, 245),
    "black": (20, 20, 20),
    "green": (50, 205, 50),
    "yellow": (255, 215, 0),
    "pink": (255, 105, 180),
    "purple": (138, 43, 226),
    "orange": (255, 140, 0),
    "gray": (128, 128, 128),
}


def generate_realistic_shirt(color_name: str):
    """
    Generate a realistic shirt image for the given color.
    """
    color_name = color_name.lower().strip()
    base_color = COLOR_MAP.get(color_name, (200, 200, 200))
    shirt_img = _create_shirt_shape(color=base_color)
    return shirt_img
