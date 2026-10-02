#!/usr/bin/env python3
# MjrFts - servidor local en Termux
# Recibe las fotos mejoradas desde la app y las guarda directo en DCIM/Camera.
# Solo escucha dentro del teléfono (127.0.0.1); nada sale a internet.
import http.server, json, os, re, shutil, subprocess, urllib.parse

VERSION = 1
PUERTO = 8765
CAMARA = os.path.expanduser('~/storage/dcim/Camera')
MAX_BYTES = 60_000_000


def avisar_galeria(ruta):
    """Pide a Android que registre la foto nueva para que salga en la Galería."""
    real = os.path.realpath(ruta)
    try:
        if shutil.which('termux-media-scan'):
            subprocess.run(['termux-media-scan', real], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        else:
            subprocess.run(['am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
                            '-d', 'file://' + real], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    except Exception:
        pass


class Manejador(http.server.BaseHTTPRequestHandler):
    def encabezados_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')

    def responder(self, codigo, datos):
        cuerpo = json.dumps(datos).encode('utf-8')
        self.send_response(codigo)
        self.encabezados_cors()
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        self.send_response(204)
        self.encabezados_cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/ping'):
            self.responder(200, {'ok': True, 'version': VERSION, 'camara': os.path.isdir(CAMARA)})
        else:
            self.responder(404, {'ok': False})

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path != '/guardar':
            return self.responder(404, {'ok': False})
        q = urllib.parse.parse_qs(url.query)
        nombre = os.path.basename(q.get('nombre', ['foto_mjr.jpg'])[0])
        nombre = re.sub(r'[^\w.\-]', '_', nombre) or 'foto_mjr.jpg'
        if not nombre.lower().endswith('.jpg'):
            nombre += '.jpg'
        n = int(self.headers.get('Content-Length', 0) or 0)
        if n <= 0 or n > MAX_BYTES:
            return self.responder(400, {'ok': False, 'error': 'tamaño no válido'})
        datos = self.rfile.read(n)
        if datos[:2] != b'\xff\xd8':
            return self.responder(400, {'ok': False, 'error': 'no es JPG'})
        if not os.path.isdir(CAMARA):
            return self.responder(500, {'ok': False, 'error': 'no encuentro la carpeta Camera'})
        ruta = os.path.join(CAMARA, nombre)
        base, ext = os.path.splitext(ruta)
        i = 1
        while os.path.exists(ruta):
            ruta = f'{base}_{i}{ext}'
            i += 1
        temporal = os.path.join(os.path.dirname(ruta), '.' + os.path.basename(ruta) + '.part')
        with open(temporal, 'wb') as f:
            f.write(datos)
        os.replace(temporal, ruta)
        avisar_galeria(ruta)
        print('  Guardada en Cámara:', os.path.basename(ruta), flush=True)
        self.responder(200, {'ok': True, 'archivo': os.path.basename(ruta)})

    def log_message(self, *args):
        pass


def main():
    if not os.path.isdir(CAMARA):
        print('No encuentro', CAMARA)
        print('Corre primero:  termux-setup-storage   y dale Permitir.')
        return
    servidor = http.server.ThreadingHTTPServer(('127.0.0.1', PUERTO), Manejador)
    print(f'MjrFts servidor v{VERSION} listo en el puerto {PUERTO}')
    print('Guarda en:', os.path.realpath(CAMARA))
    print('Deja Termux abierto. Para detener: CTRL + C')
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido.')


if __name__ == '__main__':
    main()
