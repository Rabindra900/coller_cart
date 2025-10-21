import os
import shutil
import random

SOURCE_DIR = "dataset_labeled"
TARGET_DIR = "dataset"
TRAIN_RATIO = 0.8

def safe_mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def split_dataset():
    if os.path.exists(TARGET_DIR):
        shutil.rmtree(TARGET_DIR)
    os.makedirs(TARGET_DIR)

    train_dir = os.path.join(TARGET_DIR, "train")
    val_dir = os.path.join(TARGET_DIR, "val")
    os.makedirs(train_dir)
    os.makedirs(val_dir)

    classes = [c for c in os.listdir(SOURCE_DIR) if os.path.isdir(os.path.join(SOURCE_DIR, c))]
    print(f"Detected {len(classes)} classes: {classes}")

    for c in classes:
        imgs = os.listdir(os.path.join(SOURCE_DIR, c))
        if len(imgs) < 2:
            print(f"⚠️ Skipping class '{c}' (too few images)")
            continue

        random.shuffle(imgs)
        split_point = int(len(imgs) * TRAIN_RATIO)

        train_imgs = imgs[:split_point]
        val_imgs = imgs[split_point:]

        # ensure at least 1 file in both train & val
        if len(val_imgs) == 0:
            val_imgs = train_imgs[-1:]
            train_imgs = train_imgs[:-1]

        train_class_dir = os.path.join(train_dir, c)
        val_class_dir = os.path.join(val_dir, c)
        safe_mkdir(train_class_dir)
        safe_mkdir(val_class_dir)

        for img in train_imgs:
            shutil.copy(os.path.join(SOURCE_DIR, c, img), os.path.join(train_class_dir, img))
        for img in val_imgs:
            shutil.copy(os.path.join(SOURCE_DIR, c, img), os.path.join(val_class_dir, img))

    print("✅ Done: train and val sets have identical class folders.")

if __name__ == "__main__":
    split_dataset()
