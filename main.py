"""Server entry point."""

import os

from app import create_app
from app.config import Config

app = create_app(Config)

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    threads = int(os.getenv("THREADS", "4"))

    if app.config.get("DEBUG"):
        app.run(host=host, port=port, debug=True, threaded=True)
    else:
        import waitress

        waitress.serve(app, host=host, port=port, threads=threads)
