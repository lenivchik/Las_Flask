import http.server
import socketserver
import os

# Create a 2MB test file
with open("test_2mb.bin", "wb") as f:
    f.write(os.urandom(2 * 1024 * 1024))

PORT = 8888
Handler = http.server.SimpleHTTPRequestHandler

print(f"Starting test server on port {PORT}")
print("From client machine, run:")
print(f"  wget http://10.2.22.200:{PORT}/test_2mb.bin")
print(f"  or")
print(f"  curl -O http://10.2.22.200:{PORT}/test_2mb.bin")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()