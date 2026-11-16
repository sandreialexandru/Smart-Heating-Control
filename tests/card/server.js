// A small HTTP server for the card tests. Browsers load ES modules only over
// HTTP, not from file://, so the tests open page.html through it.
//
//   const { start } = require("./server");
//   const srv = await start();                 // the repository as it is
//   const old = await start({ card: "/tmp/base" });  // the card of another version
//   page.goto(srv.url + "/tests/card/page.html"); ... await srv.close();
//
// Everything is served from the repository, except the files of the
// integration (/custom_components/...), which come from `card` when given:
// the tests and their fixtures stay the same while the card under test changes.
const http = require("http");
const fs = require("fs");
const path = require("path");

const REPO = path.resolve(__dirname, "..", "..");
const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
};

function start({ card = REPO } = {}) {
  const roots = { repo: REPO, card: path.resolve(card) };
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent(new URL(req.url, "http://x").pathname);
    const root = url.startsWith("/custom_components/") ? roots.card : roots.repo;
    const file = path.normalize(path.join(root, url));
    if (!file.startsWith(root + path.sep)) {
      res.writeHead(403).end();
      return;
    }
    fs.readFile(file, (err, data) => {
      if (err) {
        res.writeHead(404).end();
        return;
      }
      res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream", "Cache-Control": "no-store" });
      res.end(data);
    });
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({ url: `http://127.0.0.1:${port}`, close: () => new Promise((r) => server.close(r)) });
    });
  });
}

module.exports = { start, REPO };
