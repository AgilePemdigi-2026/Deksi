"""A small real Chrome/CDP adapter using existing websocket-client, no downloads."""
import base64
import json

from pathlib import Path
import socket
import subprocess
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

import websocket


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_http(url, process, seconds=25):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Owned server exited before readiness")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("Owned frontend was not ready")


class Chrome:
    def __init__(self, profile, artifacts, allowed_origin):
        self.ws = None
        self.process = None
        self.sequence = 0
        self.blocked = []
        self.errors = []
        self.requests = []
        self.allowed_origin = allowed_origin
        self.profile = Path(profile)
        self.artifacts = Path(artifacts)
        self.log = (self.artifacts / "chrome.log").open("w", encoding="utf-8")
        chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
        if not chrome.exists():
            raise FileNotFoundError("Existing Chrome is required; no automatic installation")
        self.process = subprocess.Popen([
            str(chrome), "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", "--disable-background-networking",
            "--disable-component-update", "--disable-sync", "--disable-default-apps",
            "--disable-domain-reliability", "--metrics-recording-only",
            "--disable-features=OptimizationHints,MediaRouter,AutofillServerCommunication",
            "--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1",
            "--remote-debugging-port=0", f"--user-data-dir={self.profile}", "about:blank",
        ], stdout=self.log, stderr=self.log)
        self.debug_port = None

    def connect(self):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            active = self.profile / "DevToolsActivePort"
            if active.exists():
                self.debug_port = int(active.read_text().splitlines()[0])
                break
            if self.process.poll() is not None:
                raise RuntimeError("Owned isolated Chrome exited")
            time.sleep(0.1)
        if self.debug_port is None:
            raise TimeoutError("Isolated Chrome did not provide a debug port")
        with urlopen(f"http://127.0.0.1:{self.debug_port}/json/list", timeout=5) as response:
            target = next(t for t in json.load(response) if t["type"] == "page")
        self.ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=15, suppress_origin=True)
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Network.enable")
        self.call("Emulation.setDeviceMetricsOverride", {
            "width": 1280, "height": 900, "deviceScaleFactor": 1, "mobile": False,
        })
        self.call("Fetch.enable", {"patterns": [{"urlPattern": "*", "requestStage": "Request"}]})

    def _send(self, method, params):
        self.sequence += 1
        self.ws.send(json.dumps({"id": self.sequence, "method": method, "params": params}))
        return self.sequence

    def event(self, message):
        params = message.get("params", {})
        if message.get("method") == "Fetch.requestPaused":
            url = params["request"]["url"]
            parsed = urlsplit(url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            denied_path = parsed.path in ("/api/status/", "/api/system/bps-status/")
            if (origin == self.allowed_origin and not denied_path) or parsed.scheme in ("data", "blob", "about"):
                self.requests.append({"url": url, "method": params["request"]["method"]})
                self._send("Fetch.continueRequest", {"requestId": params["requestId"]})
            else:
                self.blocked.append({"url": url, "reason": "outside task origin or provider-probe path"})
                self._send("Fetch.failRequest", {"requestId": params["requestId"], "errorReason": "BlockedByClient"})
        elif message.get("method") == "Runtime.exceptionThrown":
            self.errors.append(params.get("exceptionDetails", {}).get("text", "runtime exception"))

    def call(self, method, params=None):
        current = self._send(method, params or {})
        while True:
            data = json.loads(self.ws.recv())
            if data.get("id") == current:
                if "error" in data:
                    raise RuntimeError(f"CDP {method}: {data['error']}")
                return data.get("result", {})
            self.event(data)

    def js(self, expression):
        response = self.call("Runtime.evaluate", {
            "expression": expression, "returnByValue": True, "awaitPromise": True,
        })
        if response.get("exceptionDetails"):
            raise RuntimeError("Browser JS exception: " + response["exceptionDetails"].get("text", "unknown"))
        return response.get("result", {}).get("value")

    def wait(self, expression, seconds=20):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self.js(expression):
                return
            time.sleep(0.08)
        raise AssertionError("Browser condition timed out: " + expression)

    def screenshot(self, name):
        png = self.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        (self.artifacts / name).write_bytes(base64.b64decode(png["data"]))

    def click(self, selector):
        literal = json.dumps(selector)
        self.js(f"document.querySelector({literal}).scrollIntoView({{block:'center',behavior:'instant'}})")
        point = self.js(f"(()=>{{const r=document.querySelector({literal}).getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
        self.call("Input.dispatchMouseEvent", {"type": "mousePressed", **point, "button": "left", "clickCount": 1})
        self.call("Input.dispatchMouseEvent", {"type": "mouseReleased", **point, "button": "left", "clickCount": 1})

    def type_text(self, selector, value):
        self.click(selector)
        self.call("Input.insertText", {"text": value})

    def close(self):
        if self.ws is not None:
            try:
                self._send("Browser.close", {})
            except (OSError, websocket.WebSocketException):
                pass
            finally:
                self.ws.close()
        if self.process is not None and self.process.poll() is None:
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
        self.log.close()
