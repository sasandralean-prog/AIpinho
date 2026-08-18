# Artifact Bundles

Bundles package selected ready artifacts into a new zip artifact with `BUNDLE_MANIFEST.json`.

Rules:

- blocked/failed/deleted artifacts are rejected;
- resulting bundle receives a new artifact id;
- bundle download uses the same Authorization-header flow;
- no token is placed in the URL.
