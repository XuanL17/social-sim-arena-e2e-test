# Independent simulated AI backend

Hosted in the separate Vercel project `social-sim-arena-e2e-agent`:

- HTTPS endpoint: https://social-sim-arena-e2e-agent.vercel.app/forecast
- Health: https://social-sim-arena-e2e-agent.vercel.app/healthz

`api/index.py` is the Vercel entry point. It verifies the test platform signature
and uses `server.forecast` to simulate scalar, profile and ranking answers.
It uses no paid LLM. Equal inputs produce equal answers across stateless
function instances; Vercel mode does not claim durable SQLite storage.
Only public verification keys are deployed here; the private signing key stays
in the platform project's environment variables.

Deploy this backend from this directory, whose `.vercel` binding is independent
of the repository root's platform binding:

```sh
vercel deploy --prod --yes --scope yangs-projects-36e22525
```

The root-level `server.py` and Dockerfile also support a standalone VM/container
with SQLite persistence, but that is an optional alternative and not the chosen
hosting setup. No SSH server or custom domain is required for Vercel mode.
