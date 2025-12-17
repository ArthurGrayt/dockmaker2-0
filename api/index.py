import os
import sys

# Add the parent directory to sys.path so 'app.py' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

def handler(request, context):
    return app(request.environ, lambda status, headers: None)
