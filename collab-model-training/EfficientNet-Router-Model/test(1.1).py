import tensorflow as tf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from sklearn.metrics import classification_report, roc_curve, auc, multilabel_confusion_matrix, f1_score

# ==============================
# CONFIG
# ==============================
IMG_SIZE = 300
BATCH_SIZE = 32
TEST_DIR = './Dataset/test'
TEST_CSV = os.path.join(TEST_DIR, '_classes.csv')
MODEL_PATH = './trained_models/efficientnetv2b3_finetuned_model(v1).h5'

# ==============================
# LOAD LABELS
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

# ==============================
# DATA PIPELINE
# ==============================
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

def create_dataset(csv_path, data_dir):
    file_names, label_map, num_labels, labels = load_labels(csv_path)
    dataset = tf.data.Dataset.from_generator(
        lambda: dataset_generator(file_names, label_map, data_dir),
        output_signature=(
            tf.TensorSpec(shape=(IMG_SIZE, IMG_SIZE, 3), dtype=tf.float32),
            tf.TensorSpec(shape=(num_labels,), dtype=tf.float32)
        )
    )
    dataset = dataset.map(lambda img, lbl: set_shapes(img, lbl, num_labels))
    dataset = dataset.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    return dataset, num_labels, file_names, labels

# ==============================
# LOAD MODEL & DATA
# ==============================
print("🧩 Loading model...")
model = tf.keras.models.load_model(MODEL_PATH, compile=False)
print("✅ Model loaded successfully")

test_ds, num_classes, file_names, label_columns = create_dataset(TEST_CSV, TEST_DIR)

# ==============================
# PREDICTION
# ==============================
print("🚀 Generating predictions...")
y_true, y_pred_probs = [], []
for x_batch, y_batch in test_ds:
    preds = model.predict(x_batch)
    y_true.append(y_batch.numpy())
    y_pred_probs.append(preds)

y_true = np.vstack(y_true)
y_pred_probs = np.vstack(y_pred_probs)
y_pred = (y_pred_probs > 0.5).astype(int)

# ==============================
# CLASSIFICATION METRICS
# ==============================
print("\n📊 Classification Report:")
print(classification_report(y_true, y_pred, target_names=label_columns, zero_division=0))

f1_macro = f1_score(y_true, y_pred, average='macro', zero_division=0)
print(f"\n🔹 Macro F1 Score: {f1_macro:.4f}")

# ==============================
# CONFUSION MATRIX
# ==============================
mcm = multilabel_confusion_matrix(y_true, y_pred)
os.makedirs("test_results", exist_ok=True)

for idx, label in enumerate(label_columns):
    tn, fp, fn, tp = mcm[idx].ravel()
    plt.figure(figsize=(4, 4))
    sns.heatmap([[tp, fp], [fn, tn]], annot=True, fmt='d', cmap='Blues',
                xticklabels=['Predicted 1', 'Predicted 0'],
                yticklabels=['Actual 1', 'Actual 0'])
    plt.title(f'Confusion Matrix - {label}')
    plt.tight_layout()
    plt.savefig(f"test_results/confmat_{label}.png")
    plt.close()

print("✅ Confusion matrices saved to test_results/")

# ==============================
# ROC CURVE
# ==============================
for i, label in enumerate(label_columns):
    fpr, tpr, _ = roc_curve(y_true[:, i], y_pred_probs[:, i])
    roc_auc = auc(fpr, tpr)
    plt.plot(fpr, tpr, label=f'{label} (AUC={roc_auc:.2f})')

plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curves (Multi-label)')
plt.legend()
plt.tight_layout()
plt.savefig("test_results/roc_curves.png")
plt.close()

print("✅ ROC curves saved to test_results/")

# ==============================
# PREDICTED LABEL PROBABILITIES
# ==============================
print("\n🔍 Showing sample predictions with probabilities:")

pred_df = pd.DataFrame(y_pred_probs, columns=[f"Prob_{lbl}" for lbl in label_columns])
true_df = pd.DataFrame(y_true, columns=[f"True_{lbl}" for lbl in label_columns])
pred_binary_df = pd.DataFrame(y_pred, columns=[f"Pred_{lbl}" for lbl in label_columns])

result_df = pd.concat([pd.DataFrame({"Filename": file_names}), true_df, pred_df, pred_binary_df], axis=1)
pd.set_option('display.max_columns', None)
print(result_df.head(10))

# Save predictions
os.makedirs("test_results/v1", exist_ok=True)
result_path = "test_results/v1/prediction_results.csv"
result_df.to_csv(result_path, index=False)
print(f"💾 Detailed predictions saved to {result_path}")

print("\n🏁 Testing complete.")
