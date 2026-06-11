import sys
import os

# Add root directory to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    print("Testing order schemas...")
    from order import schemas
    print("Order schemas imported successfully.")

    print("Testing order models...")
    from order import models
    print("Order models imported successfully.")

    print("Testing order crud...")
    from order import crud
    print("Order crud imported successfully.")

    print("Testing order router...")
    from order import router
    print("Order router imported successfully.")

    print("Testing ai router...")
    from ai import router as ai_router
    print("AI router imported successfully.")

    print("Testing ai agent...")
    from ai import agent
    print("AI agent imported successfully.")

    print("✅ All imports completed successfully! No syntax or import errors found.")

except Exception as e:
    print("❌ Import failed with error:")
    import traceback
    traceback.print_exc()
    sys.exit(1)
