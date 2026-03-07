#!/usr/bin/env python3
"""Open the interactive 3D gamut viewer in your browser.

No dependencies required — just Python and a browser.
"""

import http.server
import os
import socket
import threading
import webbrowser

PORT = 8000

# Serve from project root so viewer/index.html can reach data/*.csv
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

handler = http.server.SimpleHTTPRequestHandler
http.server.HTTPServer.allow_reuse_address = True
server = http.server.HTTPServer(("", PORT), handler)

URL = f"http://localhost:{PORT}/viewer/"
print(f"Gamut viewer at {URL}")
print("Press Ctrl+C to stop.\n")
threading.Timer(0.5, lambda: webbrowser.open(URL)).start()
server.serve_forever()
