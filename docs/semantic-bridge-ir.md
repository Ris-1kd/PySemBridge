# Semantic Bridge IR

Semantic Bridge IR describes missing Python dynamic semantics independently of
any concrete analyzer. Adapters compile the same bridge into YASA external
facts, CodeQL predicates, Pysa models, or Semgrep boundary rules.

The IR separates:

- `graph_facts`: call graph, receiver type, alias, callback, dynamic class facts.
- `flow_facts`: taint propagation facts for containers, strings, fields, and
  other expression-level transfers.

YASA should consume graph facts after base call-graph construction and flow
facts before taint propagation.
