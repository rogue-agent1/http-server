#!/usr/bin/env python3
"""Minimal HTTP/1.1 server from scratch using raw sockets."""
import sys, socket, os, mimetypes, json, datetime, threading

MIME = {".html":"text/html",".css":"text/css",".js":"application/javascript",
    ".json":"application/json",".txt":"text/plain",".png":"image/png",
    ".jpg":"image/jpeg",".gif":"image/gif",".svg":"image/svg+xml"}

def parse_request(data):
    lines = data.split("\r\n"); method, path, version = lines[0].split(" ", 2)
    headers = {}
    for line in lines[1:]:
        if ": " in line: k, v = line.split(": ", 1); headers[k.lower()] = v
        elif not line: break
    body = data.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in data else ""
    if "?" in path: path, query = path.split("?", 1)
    else: query = ""
    return {"method": method, "path": path, "query": query, "headers": headers, "body": body, "version": version}

def response(status, body="", content_type="text/html", headers=None):
    h = headers or {}
    h["Content-Type"] = content_type; h["Content-Length"] = str(len(body.encode() if isinstance(body, str) else body))
    h["Connection"] = "close"; h["Date"] = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    h["Server"] = "MiniHTTP/1.0"
    header_str = "\r\n".join(f"{k}: {v}" for k, v in h.items())
    status_line = f"HTTP/1.1 {status}\r\n{header_str}\r\n\r\n"
    if isinstance(body, bytes): return status_line.encode() + body
    return (status_line + body).encode()

class Router:
    def __init__(self): self.routes = []
    def route(self, method, path):
        def decorator(fn): self.routes.append((method, path, fn)); return fn
        return decorator
    def match(self, method, path):
        for m, p, fn in self.routes:
            if m == method and p == path: return fn
        return None

def serve(host="127.0.0.1", port=8080, root="."):
    router = Router()

    @router.route("GET", "/api/time")
    def api_time(req): return response("200 OK", json.dumps({"time": str(datetime.datetime.now())}), "application/json")

    @router.route("GET", "/api/echo")
    def api_echo(req): return response("200 OK", json.dumps({"query": req["query"], "headers": req["headers"]}), "application/json")

    def handle(conn, addr):
        try:
            data = conn.recv(8192).decode("utf-8", errors="replace")
            if not data: return
            req = parse_request(data)
            print(f"{req['method']} {req['path']} - {addr[0]}")
            handler = router.match(req["method"], req["path"])
            if handler: conn.sendall(handler(req)); return
            filepath = os.path.join(root, req["path"].lstrip("/"))
            if os.path.isdir(filepath): filepath = os.path.join(filepath, "index.html")
            if os.path.isfile(filepath):
                ext = os.path.splitext(filepath)[1]
                ct = MIME.get(ext, "application/octet-stream")
                with open(filepath, "rb") as f: body = f.read()
                conn.sendall(response("200 OK", body, ct))
            else:
                conn.sendall(response("404 Not Found", "<h1>404 Not Found</h1>"))
        except Exception as e: conn.sendall(response("500 Internal Server Error", f"<h1>500</h1><p>{e}</p>"))
        finally: conn.close()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port)); sock.listen(5)
    print(f"Serving on http://{host}:{port} (root: {os.path.abspath(root)})")
    try:
        while True:
            conn, addr = sock.accept()
            threading.Thread(target=handle, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt: print("\nShutdown"); sock.close()

def main():
    import argparse
    p = argparse.ArgumentParser(description="Minimal HTTP server")
    p.add_argument("-p", "--port", type=int, default=8080)
    p.add_argument("-d", "--dir", default="."); p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args(); serve(args.host, args.port, args.dir)

if __name__ == "__main__": main()
