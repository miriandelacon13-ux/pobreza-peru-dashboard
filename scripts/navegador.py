"""Controla Edge o Chrome sin interfaz (headless) por el protocolo DevTools, para probar el dashboard.

Lo usa scripts/probar_dashboard.py. Registra los mensajes de consola, los errores de JavaScript y las peticiones que
fallan, para que una prueba no pase en silencio si la página tiene errores.
"""

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request

import websocket

CANDIDATOS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Navegador:
    def __init__(self, ancho=1366, alto=900):
        ejecutable = next((c for c in CANDIDATOS if os.path.exists(c)), None) or shutil.which("chrome") or shutil.which("msedge")
        if not ejecutable:
            raise RuntimeError("No se encontró Edge ni Chrome")
        self.perfil = tempfile.mkdtemp(prefix="navegador_")
        self.puerto = puerto_libre()
        self.proceso = subprocess.Popen(
            [ejecutable, "--headless=new", f"--remote-debugging-port={self.puerto}", f"--user-data-dir={self.perfil}",
             "--no-first-run", "--no-default-browser-check", "--disable-extensions", f"--window-size={ancho},{alto}",
             "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        destino = None
        for _ in range(100):
            try:
                pestañas = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{self.puerto}/json", timeout=1).read())
                destino = next(p for p in pestañas if p.get("type") == "page")
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.2)
        if not destino:
            raise RuntimeError("El navegador no abrió el puerto de depuración")
        # Sin encabezado Origin: así no hace falta abrir --remote-allow-origins a otros orígenes
        self.ws = websocket.create_connection(destino["webSocketDebuggerUrl"], max_size=None, timeout=120,
                                              suppress_origin=True)
        self.n = 0
        self.consola, self.errores, self.fallos_red = [], [], []
        for metodo in ["Runtime.enable", "Page.enable", "Network.enable", "Log.enable"]:
            self.enviar(metodo)
        self.enviar("Emulation.setDeviceMetricsOverride", width=ancho, height=alto, deviceScaleFactor=1, mobile=ancho < 600)

    def _evento(self, m):
        metodo, p = m.get("method"), m.get("params", {})
        if metodo == "Runtime.consoleAPICalled":
            texto = " ".join(str(a.get("value", a.get("description", ""))) for a in p.get("args", []))
            self.consola.append((p.get("type"), texto))
        elif metodo == "Runtime.exceptionThrown":
            d = p.get("exceptionDetails", {})
            self.errores.append(d.get("exception", {}).get("description") or d.get("text"))
        elif metodo == "Network.loadingFailed" and not p.get("canceled"):
            self.fallos_red.append(p.get("errorText"))
        elif metodo == "Network.responseReceived" and p.get("response", {}).get("status", 200) >= 400:
            self.fallos_red.append(f"{p['response']['status']} {p['response']['url']}")
        elif metodo == "Log.entryAdded" and p.get("entry", {}).get("level") == "error":
            self.errores.append(p["entry"].get("text"))

    def enviar(self, metodo, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": metodo, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.n:
                if "error" in m:
                    raise RuntimeError(f"{metodo}: {m['error']}")
                return m.get("result", {})
            self._evento(m)

    def evaluar(self, js):
        r = self.enviar("Runtime.evaluate", expression=js, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(f"Error al evaluar: {r['exceptionDetails'].get('exception', {}).get('description')}")
        return r.get("result", {}).get("value")

    def esperar(self, condicion_js, segundos=60):
        fin = time.time() + segundos
        while time.time() < fin:
            if self.evaluar(f"Boolean({condicion_js})"):
                return True
            time.sleep(0.25)
        raise TimeoutError(f"No se cumplió: {condicion_js}")

    def ir(self, url, condicion_js="document.readyState === 'complete'", segundos=60):
        self.enviar("Page.navigate", url=url)
        time.sleep(0.5)
        self.esperar(condicion_js, segundos)

    def captura(self, ruta, completa=True):
        import base64
        r = self.enviar("Page.captureScreenshot", format="png", captureBeyondViewport=completa)
        with open(ruta, "wb") as f:
            f.write(base64.b64decode(r["data"]))

    def cerrar(self):
        try:
            self.enviar("Browser.close")
        except Exception:  # noqa: BLE001
            self.proceso.kill()
        self.proceso.wait(timeout=20)
        shutil.rmtree(self.perfil, ignore_errors=True)
