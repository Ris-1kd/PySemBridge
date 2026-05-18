# YASA Semantic Bridge Integration

## Directory Strategy

Keep the original YASA engine unchanged:

```text
YASA-Engine-upstream      baseline, do not edit
YASA-Engine-sembridge     experimental copy with PySemBridge API
PySemBridge               tool-independent bridge IR and adapters
```

This layout keeps the experiment defensible:

```text
same benchmark + same source/sink rules + original YASA
vs.
same benchmark + same source/sink rules + YASA-sembridge + bridge facts
```

## Current API

The experimental YASA copy adds one command-line option:

```bash
--semanticBridgeFacts <file>
```

The option loads a PySemBridge-generated facts JSON file and stores it in:

```ts
Config.semanticBridgeFacts
```

Implemented files:

```text
YASA-Engine-sembridge/src/config.ts
YASA-Engine-sembridge/src/interface/starter.ts
YASA-Engine-sembridge/src/engine/analyzer/common/semantic-bridge-facts-loader.ts
```

## Current Capability

The current integration is an API/bootstrap layer only:

```text
CLI flag -> facts JSON validation -> Config.semanticBridgeFacts
```

It does not yet change propagation behavior. The next step is to consume these
facts inside analyzer-level call resolution and taint-transfer logic.

## Recommended Injection Levels

### Analyzer Call Resolution

Use `graph_facts.call_edges`, `type_facts`, and `callback_facts` to supplement
missing dynamic call edges.

Good insertion area:

```text
src/engine/analyzer/common/analyzer.ts
processCallExpression / processCall
```

### Analyzer Taint Transfer

Use `flow_facts.container_transfers`, `dict_key_transfers`,
`string_transfers`, and `field_transfers` to supplement missing intra/inter
procedural taint propagation.

Good insertion area:

```text
src/engine/analyzer/common/analyzer.ts
processLibFuncTagPropagation / processLibArgToRet / assignment handling
```

### Checker Rules

Keep checker rules limited to source/sink/sanitizer declarations.

Do not encode dynamic Python semantic gaps as fake sinks because that produces
boundary findings instead of complete vulnerability traces.

## Pyload Test Script

Run:

```bash
bash experiments/scripts/run_yasa_sembridge_pyload.sh
```

Expected behavior:

- facts file is loaded successfully
- YASA reports the baseline boundary trace
- YASA-sembridge appends a PySemBridge enhanced complete-chain SARIF finding

## Verified Result

The script was executed successfully.

Observed loader log:

```text
[YASA][semantic-bridge] Loaded semantic bridge facts:
.../cve-2025-55156-pyload.yasa-facts.json
bridge=cve_2025_55156_pyload_receiver_container_string facts=6
```

Observed baseline finding:

```text
Line 18: db.update_link_info(data)
SINK RULE: db.update_link_info
SINK Attribute: CVE-2025-55156-pyload-update-link-info-boundary
```

Observed enhanced finding in `report.sarif`:

```text
semanticBridgeEnhanced: true
sinkRule: self.c.execute(...)
sinkAttribute: PySemBridge-complete-chain
```

Observed enhanced trace:

```text
Step 0: poc_cve_2025_55156_pyload.py:16 cve_2025_55156_source()
Step 1: poc_cve_2025_55156_pyload.py:16 url
Step 2: poc_cve_2025_55156_pyload.py:17 data
Step 3: poc_cve_2025_55156_pyload.py:18 db.update_link_info
Step 4: file_database.py:261 FileDatabaseMethods.update_link_info
Step 5: file_database.py:270 statuses
Step 6: file_database.py:271 self.c.execute
```

The current implementation consumes facts at the report augmentation layer. It
does not yet alter YASA's internal symbolic execution or taint propagation.

Next implementation step:

```text
Config.semanticBridgeFacts
  -> SemanticBridgeRuntime
  -> processCallExpression/processCall uses call_edges/type_facts
  -> assignment/string/container handlers use flow_facts
  -> checker receives a real self.c.execute finding
```
