#!/usr/bin/env python3
"""Minimal HTTP server framework. Zero dependencies."""
import socket, sys, os, json, mimetypes

class Request:
    def __init__(self, method, path, headers, body="", query=None):
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.query = query or {}

    @staticmethod
    def parse(raw):
        lines = raw.split("\r\n")
        method, path_q, _ = lines[0].split(" ", 2)
        query = {}
        if "?" in path_q:
            path, qs = path_q.split("?", 1)
            for pair in qs.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    query[k] = v
        else:
            path = path_q
        headers = {}
        i = 1
        while i < len(lines) and lines[i]:
            k, v = lines[i].split(": ", 1)
            headers[k.lower()] = v
            i += 1
        body = "\r\n".join(lines[i+1:]) if i+1 < len(lines) else ""
        return Request(method, path, headers, body, query)

class Response:
    STATUS = {200: "OK", 201: "Created", 204: "No Content", 301: "Moved",
              400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed", 500: "Internal Server Error"}

    def __init__(self, status=200, body="", content_type="text/html", headers=None):
        self.status = status
        self.body = body.encode() if isinstance(body, str) else body
        self.headers = headers or {}
        self.headers["Content-Type"] = content_type
        self.headers["Content-Length"] = str(len(self.body))

    def to_bytes(self):
        status_text = self.STATUS.get(self.status, "Unknown")
        lines = [f"HTTP/1.1 {self.status} {status_text}"]
        for k, v in self.headers.items():
            lines.append(f"{k}: {v}")
        return ("\r\n".join(lines) + "\r\n\r\n").encode() + self.body

    @staticmethod
    def json(data, status=200):
        return Response(status, json.dumps(data), "application/json")

    @staticmethod
    def text(text, status=200):
        return Response(status, text, "text/plain")

    @staticmethod
    def html(html, status=200):
        return Response(status, html, "text/html")

class Router:
    def __init__(self):
        self.routes = []

    def route(self, method, path):
        def decorator(fn):
            self.routes.append((method.upper(), path, fn))
            return fn
        return decorator

    def get(self, path): return self.route("GET", path)
    def post(self, path): return self.route("POST", path)

    def handle(self, request):
        for method, path, fn in self.routes:
            if request.method == method and request.path == path:
                return fn(request)
        return Response(404, "Not Found")

def serve(router, host="0.0.0.0", port=8080):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(5)
    print(f"Serving on {host}:{port}")
    while True:
        conn, addr = sock.accept()
        try:
            data = conn.recv(4096).decode()
            if data:
                req = Request.parse(data)
                resp = router.handle(req)
                conn.sendall(resp.to_bytes())
        finally:
            conn.close()

if __name__ == "__main__":
    r = Router()
    @r.get("/")
    def index(req): return Response.html("<h1>Hello!</h1>")
    @r.get("/api")
    def api(req): return Response.json({"status": "ok"})
    print("Router configured with / and /api")
