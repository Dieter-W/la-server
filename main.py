"""LA-Server entry point."""

import os

from app import create_app
from app.config import Config

app = create_app(Config)

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    threads = int(os.getenv("THREADS", "4"))
    debug = bool(app.config.get("DEBUG"))

    if debug:
        if threads == 0:
            # codeql[py/flask-debug]
            app.run(port=port, debug=True, threaded=False)
        else:
            # codeql[py/flask-debug]
            app.run(port=port, debug=True, threaded=True)
    else:
        import socket

        hostname = socket.gethostname()
        ip_addr = socket.gethostbyname(hostname)

        app.logger.info("Running LA-Server in Production Mode")
        app.logger.info(" * Running on all addresses %s", host)
        app.logger.info(" * Running on http://127.0.0.1:%s", port)
        app.logger.info(" * Running on http://%s:%s", ip_addr, port)
        app.logger.info("Press CTRL+C to quit")

        import waitress

        waitress.serve(app, host=host, port=port, threads=threads)
