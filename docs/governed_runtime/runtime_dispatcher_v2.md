# Runtime Dispatcher V2

GR3 adds a dispatcher that accepts only Runtime Contract Bundles.

It validates contracts, selects roles from Role Contracts, resolves an execution
route, and records trace. It does not interpret prompt text, call the semantic
interpreter, or mutate contracts.
