
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from models_pipeline import config
    print("✅ Successfully imported config")
except ImportError as e:
    print(f"❌ Failed to import config: {e}")
    sys.exit(1)

def check_path(name, path):
    if os.path.exists(path):
        print(f"✅ {name}: Found at {path}")
        return True
    else:
        print(f"❌ {name}: NOT FOUND at {path}")
        return False

print(f"\nVerifying Model Paths...")
print(f"Base Dir: {config.BASE_MODELS_DIR}")

all_good = True

if not check_path("Router Model", config.ROUTER_MODEL_PATH):
    all_good = False

for name, path in config.YOLO_MODELS.items():
    if not check_path(f"YOLO {name}", path):
        all_good = False

print("\n")
if all_good:
    print("🚀 All configuration paths are valid.")
    sys.exit(0)
else:
    print("⚠️ Some model files are missing. Backend will likely fail.")
    sys.exit(1)
