import sys
import os

# Ensure app is in path
sys.path.append("/app")

from app.main import app

print("Registered Routes:")
for route in app.routes:
    methods = getattr(route, "methods", None)
    print(f"Path: {route.path} Methods: {methods}")
