# Independent server entrant

This backend runs separately from Vercel, accepts signed Agent API requests,
and simulates an AI without calling a paid model. It forecasts from the supplied
history and supports scalar, profile and ranking questions. SQLite preserves
answers across process restarts using request ID and canonical input hash.

Deploy this directory to the selected server. Copy only the test platform's
public `site/keys.json` to `keys.json` beside it; never copy signing private keys.
Build the Docker image and mount `keys.json` read-only and a persistent `/data`
volume. Bind the HTTP port to loopback behind the server's HTTPS reverse proxy.

- `GET /healthz`: process and database health.
- `POST /forecast`: signed questions; malformed/expired signatures return 401.
- `OPTIONS /forecast`: browser onboarding CORS.
- Environment: `HOST`, `PORT`, `KEYS_FILE`, `DB_FILE`.

Server and HTTPS domain are awaiting user selection. This backend has not yet
been deployed remotely; passing local tests does not prove a Vercel-to-server
round trip. The existing Vercel example endpoint is not this backend.
