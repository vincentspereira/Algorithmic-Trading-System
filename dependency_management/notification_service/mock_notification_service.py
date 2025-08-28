
from http.server import BaseHTTPRequestHandler, HTTPServer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockNotificationHandler(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        logger.info(f"Received notification: {post_data.decode('utf-8')}")
        self._set_response()
        self.wfile.write("Notification received".encode('utf-8'))

def run(server_class=HTTPServer, handler_class=MockNotificationHandler, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    logger.info(f"Starting mock notification service on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
