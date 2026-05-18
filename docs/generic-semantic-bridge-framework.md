# Generic Semantic Bridge Framework

## Goal

PySemBridge should not be a pyload-specific patch. The intended architecture is
a reusable middle layer:

```text
CVE source project
  -> AST/source feature extraction
  -> semantic gap classification
  -> family-specific bridge synthesis
  -> tool-independent Semantic Bridge IR
  -> adapter projection to YASA / CodeQL / Pysa / Semgrep
  -> static analyzer output + enhanced complete trace
```

## Six Core Gap Families

The generic recognizer currently classifies Python source features into these
families:

| Family | Typical Python features | Bridge repair layer |
| --- | --- | --- |
| dynamic_receiver_callgraph | receiver method calls, decorators, dynamic import, async scheduling | `graph_facts.call_edges`, `type_facts`, `callback_facts` |
| container_dict_key_flow | list/tuple/dict construction, subscript extraction, dict key lookup | `flow_facts.container_transfers`, `dict_key_transfers` |
| string_builder_flow | f-string, `str.format`, `str.join(generator)` | `flow_facts.string_transfers` |
| rebinding_platform_flow | alias assignment, function rebinding, platform branch | `graph_facts.alias_facts` + guarded flow facts |
| dynamic_attribute_protocol | `getattr`, descriptor/property, special methods | dynamic field facts + call edges |
| callback_parser_dispatch | nested functions, callbacks, higher-order functions, await/async parser dispatch | callback registration/invocation facts |

An additional practical family is recognized:

| Family | Purpose |
| --- | --- |
| serialization_field_flow | JSON/YAML/pickle object-to-field propagation |

This seventh family can be folded into container/field flow in the paper if a
strict six-family taxonomy is preferred.

## Implemented Generic Modules

```text
pysembridge/recognizer/features.py
  AST feature extractor.

pysembridge/recognizer/classifier.py
  Maps feature hits to semantic gap families.

pysembridge/synthesizer/auto.py
  Generic pipeline that emits:
    - classifications
    - candidate gap specs
    - executable bridges when a concrete synthesizer supports the pattern

pysembridge/synthesizer/pyload.py
  First concrete family synthesizer:
    receiver + container + string_builder
```

## CLI

Classify and synthesize a bridge when possible:

```bash
python3 -m pysembridge.cli synthesize-auto \
  --project /path/to/cve-project \
  --project-name cve-name \
  --format bridge \
  --output generated.bridge.json
```

Output full classification/spec bundle:

```bash
python3 -m pysembridge.cli synthesize-auto \
  --project /path/to/cve-project \
  --project-name cve-name \
  --format bundle \
  --output auto-bundle.json
```

## Current Verified Case

For `CVE-2025-55156 / pyload`, the generic pipeline detected:

```text
dynamic_receiver_callgraph
container_dict_key_flow
string_builder_flow
serialization_field_flow
dynamic_attribute_protocol
rebinding_platform_flow
callback_parser_dispatch
```

It then selected the concrete pyload-like synthesizer and generated an
executable bridge for:

```text
receiver + container + string_builder
```

Verified enhanced output:

```text
result_count = 2
0. baseline: db.update_link_info
1. semanticBridgeEnhanced: true, sink = self.c.execute(...)
```

Artifacts:

```text
experiments/results/generated/cve-2025-55156-pyload.auto-bundle.json
experiments/results/generated/cve-2025-55156-pyload.auto.bridge.json
experiments/results/generated/cve-2025-55156-pyload.auto.yasa-facts.json
experiments/results/yasa-sembridge-generic-auto/cve-2025-55156-pyload/report.sarif
```

## Important Boundary

The generic middle layer is now present, but only one concrete executable
synthesizer is implemented end to end.

Implemented end to end:

```text
receiver + container/tuple element + generator/join string_builder
```

Implemented as classification/spec candidates:

```text
dynamic receiver/callgraph
container/dict key flow
string builder flow
rebinding/platform branch
dynamic attribute/protocol
callback/parser dispatch
serialization/field flow
```

Still needed for a fully general system:

```text
one concrete bridge synthesizer per family
LLM-assisted evidence extraction for ambiguous cases
bridge verifier per family
adapter projection tests for CodeQL/Pysa/Semgrep
ranking/filtering using baseline trace and expected sink locations
```

## Recommended Research Framing

Do not frame the current tool as a universal automatic CVE repair engine yet.

Accurate framing:

```text
PySemBridge implements a generic semantic-gap recognition and bridge generation
architecture. It currently provides end-to-end executable synthesis for one
representative family and emits structured gap specs for the remaining families.
```
