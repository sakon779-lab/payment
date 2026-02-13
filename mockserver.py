from http.server import BaseHTTPRequestHandler, HTTPServer

class MockServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Mock Server Response')

def run(server_class=HTTPServer, handler_class=MockServer, port=5000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Starting mock server on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()