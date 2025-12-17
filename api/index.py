import os
import sys
import traceback

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app import app
except Exception as e:
    # Capture import errors (e.g. missing dependencies, syntax errors in app.py)
    app = None
    import_error = traceback.format_exc()

def handler(request, context):
    # Verify if app loaded correctly
    if not app:
        return [f"CRITICAL: Application failed to start.\n\n{import_error}".encode('utf-8')]

    try:
        # User defined signature: handler(request, context)
        # Attempt to run Flask app using the request's environment
        if hasattr(request, 'environ'):
            return app(request.environ, lambda status, headers: None)
        else:
            return [f"Error: Response object has no 'environ'. Type: {type(request)}".encode('utf-8')]
            
    except Exception as e:
        return [f"CRITICAL: Traceback during handling:\n{traceback.format_exc()}".encode('utf-8')]
