# train.py
# Train a small CNN for color classification. Adjust IMG_SIZE, EPOCHS as needed.
import os, json
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import ModelCheckpoint

IMG_SIZE = (128,128)
BATCH = 32
EPOCHS = 12
DATA_DIR = "dataset"  # contains train/ and val/

if not os.path.exists(DATA_DIR):
    raise SystemExit("dataset/ not found. Run split_dataset.py after labeling and placing images.")

train_datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=15,
    width_shift_range=0.1,
    height_shift_range=0.1,
    zoom_range=0.15,
    horizontal_flip=True
)
val_datagen = ImageDataGenerator(rescale=1./255)

train_gen = train_datagen.flow_from_directory(
    os.path.join(DATA_DIR,"train"),
    target_size=IMG_SIZE,
    batch_size=BATCH,
    class_mode="categorical"
)
val_gen = val_datagen.flow_from_directory(
    os.path.join(DATA_DIR,"val"),
    target_size=IMG_SIZE,
    batch_size=BATCH,
    class_mode="categorical"
)

NUM_CLASSES = train_gen.num_classes

model = Sequential([
    Conv2D(32,(3,3),activation="relu",input_shape=(IMG_SIZE[0],IMG_SIZE[1],3)),
    BatchNormalization(), MaxPooling2D(2,2),
    Conv2D(64,(3,3),activation="relu"),
    BatchNormalization(), MaxPooling2D(2,2),
    Conv2D(128,(3,3),activation="relu"),
    BatchNormalization(), MaxPooling2D(2,2),
    Flatten(),
    Dense(256, activation="relu"),
    Dropout(0.4),
    Dense(NUM_CLASSES, activation="softmax")
])

model.compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])
model.summary()

os_model = "color_cnn.h5"
checkpoint = ModelCheckpoint(os_model, monitor='val_accuracy', save_best_only=True, verbose=1)

model.fit(
    train_gen,
    epochs=EPOCHS,
    validation_data=val_gen,
    callbacks=[checkpoint]
)

# Save class indices mapping for later use
mapping = train_gen.class_indices  # e.g. {'blue':0,'green':1,...}
with open("classes.json","w") as f:
    json.dump(mapping, f)
print("Saved model (color_cnn.h5) and classes.json")