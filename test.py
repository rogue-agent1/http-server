from http_server import Request, Response, Router
req = Request.parse("GET /api?key=val HTTP/1.1\r\nHost: localhost\r\n\r\n")
assert req.method == "GET"
assert req.path == "/api"
assert req.query["key"] == "val"
r = Response.json({"ok": True})
assert b"200 OK" in r.to_bytes()
assert b"application/json" in r.to_bytes()
router = Router()
@router.get("/test")
def test(req): return Response.text("hi")
resp = router.handle(Request("GET", "/test", {}))
assert b"hi" in resp.to_bytes()
assert router.handle(Request("GET", "/nope", {})).status == 404
print("HTTP server tests passed")