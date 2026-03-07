import sys, os
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from testing.session_logger import SessionLogger
from api.models import UserState
# Try importing module used in test_main
try:
    from models_pipeline.inference import InferenceManager
    print("✅ InferenceManager imported successfully.")
except ImportError as e:
    print(f"❌ InferenceManager Import FAILED: {e}")

def verify():
    print("--- Verifying SessionLogger with Video ---")
    try:
        # Simulate the call from test_main.py with video=True
        logger = SessionLogger(session_name="VERIFY_VIDEO", record_video=True)
        print("✅ SessionLogger (Video) initialized successfully.")
        print(f"Log Dir: {logger.log_dir}")
        logger.close()
    except Exception as e:
        print(f"❌ SessionLogger (Video) Initialization FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
