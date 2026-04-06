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
            app.run(host=host, port=port, debug=True, threaded=False)
        else:
            app.run(host=host, port=port, debug=True, threaded=True)
    else:
        import socket

        hostname = socket.gethostname()
        ip_addr = socket.gethostbyname(hostname)

        print("Running LA-Server in Production Mode")
        print(f" * Running on all addresses {host}")
        print(f" * Running on http://127.0.0.1:{port}")
        print(f" * Running on http://{ip_addr}:{port}")
        print("Press CTRL+C to quit")

        import waitress

        waitress.serve(app, host=host, port=port, threads=threads)
