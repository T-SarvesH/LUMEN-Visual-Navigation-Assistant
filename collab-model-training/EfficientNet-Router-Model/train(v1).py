import tensorflow as tf
import pandas as pd
import numpy as np
from tensorflow.keras import layers, models, callbacks
from tensorflow.keras.applications.efficientnet_v2 import EfficientNetV2B3
import os
import time
from random import randrange
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report

# ==============================
# GPU SETUP
# ==============================
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        tf.config.set_visible_devices(gpus[0], 'GPU')
        tf.config.experimental.set_memory_growth(gpus[0], True)
        print(f"✅ Using GPU: {gpus[0].name}")
    except RuntimeError as e:
        print("⚠️ GPU setup error:", e)
else:
    print("⚠️ No GPU found, running on CPU")

# ==============================
# CONSTANTS
# ==============================
IMG_SIZE = 300
BATCH_SIZE = 32
EPOCHS = 10

# ==============================
# DATA PATHS
# ==============================
TRAIN_DIR = './Dataset/train'
VALID_DIR = './Dataset/valid'
TEST_DIR = './Dataset/test'
TRAIN_CSV = os.path.join(TRAIN_DIR, '_classes.csv')
VALID_CSV = os.path.join(VALID_DIR, '_classes.csv')
TEST_CSV = os.path.join(TEST_DIR, '_classes.csv')

# ==============================
# DATA LOADING
# ==============================
def load_labels(csv_path):
    df = pd.read_csv(csv_path)
    if "Unlabeled" in df.columns:
        df = df.drop(columns=["Unlabeled"])
    labels = df.columns[1:].to_list()
    label_map = {
        row['filename']: row[labels].values.astype(np.float32)
        for _, row in df.iterrows()
    }
    return df['filename'].values.astype(str), label_map, len(labels), labels

def dataset_generator(file_names, label_map, data_dir):
    for name in file_names:
        img_path = os.path.join(data_dir, name)
        image = tf.io.read_file(img_path)
        image = tf.image.decode_jpeg(image, channels=3)
        image = tf.image.resize(image, [IMG_SIZE, IMG_SIZE])
        image = tf.cast(image, tf.float32) / 255.0
        labels = label_map[name]
        yield image, labels

def set_shapes(image, label, num_labels):
    image.set_shape([IMG_SIZE, IMG_SIZE, 3])
    label.set_shape([num_labels])
    return image, label

def create_dataset(csv_path, data_dir, repeat=False, shuffle=False):
    file_names, label_map, num_labels, labels = load_labels(csv_path)
    dataset = tf.data.Dataset.from_generator(
        lambda: dataset_generator(file_names, label_map, data_dir),
        output_signature=(
            tf.TensorSpec(shape=(IMG_SIZE, IMG_SIZE, 3), dtype=tf.float32),
            tf.TensorSpec(shape=(num_labels,), dtype=tf.float32)
        )
    )
    dataset = dataset.map(lambda img, lbl: set_shapes(img, lbl, num_labels))
    if shuffle:
        dataset = dataset.shuffle(buffer_size=256)
    if repeat:
        dataset = dataset.repeat()
    dataset = dataset.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    return dataset, num_labels, len(file_names), labels

# ==============================
# CREATE DATASETS
# ==============================
train_ds, num_classes, train_samples, label_columns = create_dataset(TRAIN_CSV, TRAIN_DIR, repeat=True, shuffle=True)
val_ds, _, val_samples, _ = create_dataset(VALID_CSV, VALID_DIR, repeat=True)
test_ds, _, test_samples, _ = create_dataset(TEST_CSV, TEST_DIR, repeat=False)

# ==============================
# MULTI-LABEL CLASS WEIGHTS FROM CSV
# ==============================
df_train = pd.read_csv(TRAIN_CSV)
if "Unlabeled" in df_train.columns:
    df_train = df_train.drop(columns=["Unlabeled"])
class_weights_array = []
for col in df_train.columns[1:]:
    y = df_train[col].values.astype(int)
    pos_weight = (len(y) - y.sum()) / y.sum() if y.sum() > 0 else 1.0
    class_weights_array.append(pos_weight)
class_weights_array = np.array(class_weights_array, dtype=np.float32)
print("✅ Per-class positive weights:", class_weights_array)

# ==============================
# CUSTOM LOSS WITH PER-CLASS WEIGHTS
# ==============================
def weighted_binary_crossentropy(y_true, y_pred):
    epsilon = 1e-7
    y_pred = tf.clip_by_value(y_pred, epsilon, 1.0 - epsilon)
    loss = -(y_true * tf.math.log(y_pred) * class_weights_array + (1 - y_true) * tf.math.log(1 - y_pred))
    return tf.reduce_mean(tf.reduce_sum(loss, axis=-1))

# ==============================
# MODEL CREATION
# ==============================
with tf.device('/GPU:0'):
    base_model = EfficientNetV2B3(include_top=False, input_shape=(IMG_SIZE, IMG_SIZE, 3), weights="imagenet")
    base_model.trainable = False

    inputs = layers.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    x = base_model(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation='sigmoid')(x)
    model = models.Model(inputs, outputs)

    model.compile(
        optimizer='adam',
        loss=weighted_binary_crossentropy,
        metrics=[
            tf.keras.metrics.BinaryAccuracy(name='binary_accuracy'),
            tf.keras.metrics.AUC(name='auc'),
            tf.keras.metrics.Precision(name='precision'),
            tf.keras.metrics.Recall(name='recall')
        ]
    )

    early_stop = callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

    print("🚀 Phase 1: Training top classifier...")
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS,
        steps_per_epoch=train_samples // BATCH_SIZE,
        validation_steps=val_samples // BATCH_SIZE,
        callbacks=[early_stop]
    )

    # ==============================
    # PHASE 2: GRADUAL FINE-TUNING
    # ==============================
    total_layers = len(base_model.layers)
    unfreeze_step = 100
    fine_tune_epochs_per_step = 2
    learning_rate = 2e-4
    start = total_layers
    all_histories = [history]

    for i in range(0, total_layers, unfreeze_step):
        start -= unfreeze_step
        if start < 0:
            print("🛑 Reached start of model layers — stopping fine-tuning.")
            break

        for layer in base_model.layers[start:]:
            layer.trainable = True

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate),
            loss=weighted_binary_crossentropy,
            metrics=[
                tf.keras.metrics.BinaryAccuracy(name='binary_accuracy'),
                tf.keras.metrics.AUC(name='auc'),
                tf.keras.metrics.Precision(name='precision'),
                tf.keras.metrics.Recall(name='recall')
            ]
        )

        early_stop_fine = callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
        print(f"🔓 Fine-tuning layers {start} to {total_layers}...")
        history_fine = model.fit(
            train_ds,
            validation_data=val_ds,
            epochs=fine_tune_epochs_per_step,
            steps_per_epoch=train_samples // BATCH_SIZE,
            validation_steps=val_samples // BATCH_SIZE,
            callbacks=[early_stop_fine]
        )

        all_histories.append(history_fine)

        cooldown = randrange(90, 140)
        print(f"🕒 Cooling GPU for {cooldown} seconds...")
        time.sleep(cooldown)

# ==============================
# METRIC TRACKING AND PLOTS
# ==============================
def plot_metrics(history_list, output_dir="./training_metrics/v1"):
    os.makedirs(output_dir , exist_ok=True)
    combined = {k: [] for k in ['loss', 'val_loss', 'binary_accuracy', 'val_binary_accuracy',
                                'precision', 'val_precision', 'recall', 'val_recall', 'auc', 'val_auc']}
    for hist in history_list:
        for k in combined.keys():
            if k in hist.history:
                combined[k].extend(hist.history[k])

    for metric in ['loss', 'binary_accuracy', 'precision', 'recall', 'auc']:
        plt.figure(figsize=(8, 5))
        plt.plot(combined[metric], label=f"Train {metric}", linewidth=2)
        plt.plot(combined[f'val_{metric}'], label=f"Val {metric}", linestyle='--', linewidth=2)
        plt.title(f"{metric.replace('_', ' ').title()} Over Epochs", fontsize=14)
        plt.xlabel("Epoch", fontsize=12)
        plt.ylabel(metric.replace('_', ' ').title(), fontsize=12)
        plt.legend()
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{metric}.png"), dpi=300)
        plt.close()
        print(f"📊 Saved {metric} plot → {output_dir}/{metric}.png")

    # Save all metrics as CSV
    metrics_df = pd.DataFrame(combined)
    metrics_df.to_csv(os.path.join(output_dir, "metrics_history.csv"), index=False)
    print("✅ Metrics history saved to CSV and images.")

plot_metrics(all_histories)

# ==============================
# EVALUATION
# ==============================
print("🧪 Evaluating on test dataset...")
y_true, y_pred = [], []
for x_batch, y_batch in test_ds:

    #For now we are considering 0.5 as a threshold, ie if model prediction > 0.5, we consider it as positive class and present in image
    preds = model.predict(x_batch)
    y_true.append(y_batch.numpy())
    y_pred.append((preds > 0.5).astype(int))
y_true = np.vstack(y_true)
y_pred = np.vstack(y_pred)

print(classification_report(y_true, y_pred, target_names=label_columns))

# ==============================
# SAVE MODEL
# ==============================
os.makedirs('./trained_models', exist_ok=True)
save_path = './trained_models/efficientnetv2b3_finetuned_model(v1).h5'
model.save(save_path)
print(f"💾 Model saved to {save_path}")