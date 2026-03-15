import sys
import os

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools'))

# Import the Flask app from tools/server.py
from server import app

# Vercel expects the Flask app to be exported as 'app'
# No handler function needed - Vercel's Python runtime handles Flask apps directly
