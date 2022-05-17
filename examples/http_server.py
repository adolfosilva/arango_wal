import datetime
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

from arango_wal import ArangoWAL

handler = logging.StreamHandler()
f_format = logging.Formatter("%(asctime)s: %(name)s (%(levelname)s): %(message)s")
handler.setFormatter(f_format)


def cb(event, data):
    print(f"{event}: {json.dumps(data)}")


def main():
    wal = ArangoWAL("http://127.0.0.1:8529", polling_interval=3)
    wal.logger.setLevel(logging.INFO)
    wal.logger.addHandler(handler)

    wal.connect(name="_system", username="root", password="supersecretpassword")
    wal.subscribe("measurements", cb)
    wal.on("error", print)
    print(wal.event_names())

    class Server(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/start":
                wal.start()
                self.wfile.write("started\n".encode("utf-8"))
                self.send_response(200)
            elif self.path == "/stop":
                wal.stop()
                self.wfile.write("stopped\n".encode("utf-8"))
                self.send_response(200)
            elif self.path == "/doc":
                from arango import ArangoClient

                client = ArangoClient("http://127.0.0.1:8529")
                db = client.db(
                    name="_system", username="root", password="supersecretpassword"
                )
                col = db.collection("measurements")
                col.insert({"time": str(datetime.datetime.utcnow())})
                self.wfile.write("new doc\n".encode("utf-8"))
                self.send_response(200)
            else:
                self.send_response(404)
            return

    try:
        hostname = "localhost"
        port = 5050
        server = HTTPServer((hostname, port), Server)
        print("Server started http://%s:%s" % (hostname, port))
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    server.server_close()
    print("Server stopped.")


if __name__ == "__main__":
    main()
