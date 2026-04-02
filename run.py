import os
import sys

from app import create_app

app = create_app()

if __name__ == '__main__':
    # When running directly (e.g., via run.py instead of gunicorn/flask run)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
