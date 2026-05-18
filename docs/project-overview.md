# PySemBridge Project Overview

## 1. Research Motivation

Python 静态污点分析在真实 CVE 项目中经常出现“传播断链”：

```text
source 已经进入程序
  -> 中间经过 Python 动态特性
  -> 静态分析工具无法继续传播
  -> 最终无法到达真实 sink
```

这些断链不一定是 source/sink 规则写错，而是分析器缺少 Python 动态语义，例如：

```text
动态 receiver / 调用图边
容器元素 / dict key 污点
字符串构造摘要
函数重绑定 / 条件 import / 平台分支
getattr / descriptor / 特殊方法协议
动态类 / metaclass / monkey patch
闭包 callback / parser / event-loop 调度
```

PySemBridge 的目标不是“让 LLM 直接判断漏洞”，而是构造一个可验证的中间语义桥：

```text
Python CVE source project
  -> identify missing dynamic semantics
  -> synthesize Semantic Bridge IR
  -> project IR into analyzer-specific facts/models/rules
  -> rerun static analyzer
  -> verify complete source-to-sink trace
```

## 2. Tool Goal

当前工具已经实现一个 YASA 后端的端到端实验闭环：

```text
输入：
  CVE 源码项目
  YASA source/sink 规则
  expected source/sink 表达式

输出：
  自动生成的 bridge.json
  自动生成的 YASA facts
  YASA-sembridge SARIF 报告
  pipeline-summary.json
  完整 source-to-sink 链路验证结果
```

核心命令：

```bash
python3 -m pysembridge.cli run-yasa \
  --project <cve-source-project> \
  --project-name <cve-name> \
  --output-dir <result-dir> \
  --yasa-dir /home/ubuntu/llm-yasa-repair/YASA-Engine-sembridge \
  --rule-config <yasa-rule.json> \
  --source <source-expr> \
  --sink <bridge-sink-expr> \
  --expected-sink <final-sink-text>
```

## 3. Overall Architecture

```text
PySemBridge
├── recognizer
│   ├── AST feature extraction
│   └── semantic gap classification
├── synthesizer
│   ├── generic auto pipeline
│   ├── pyload synthesizer
│   └── pymysql synthesizer
├── ir
│   └── tool-independent Semantic Bridge schema
├── adapters
│   └── YASA facts compiler
├── verifier
│   ├── bridge reachability verifier
│   └── SARIF complete-trace verifier
└── pipeline
    └── end-to-end YASA runner
```

YASA 侧保持独立副本：

```text
YASA-Engine-upstream      original baseline, unchanged
YASA-Engine-sembridge     experimental backend with --semanticBridgeFacts
```

## 4. From CVE Source to Complete Trace

### Step 1. AST Feature Extraction

入口：

```text
pysembridge/recognizer/features.py
```

工具对项目中的 Python 文件执行：

```text
source text
  -> ast.parse
  -> AST visitor
  -> FeatureHit list
```

FeatureHit 示例：

```json
{
  "kind": "string_join_generator",
  "file": "src/pyload/core/database/file_database.py",
  "line": 270,
  "expr": "statuses = \"','\".join(x[3] for x in data)"
}
```

当前覆盖的特征包括：

```text
dynamic receiver call
framework wrapper / route / middleware registration
plugin registration
factory function
list / tuple / dict / subscript
generator expression / comprehension
f-string / join / format / %-format / string concat
conditional import / platform branch / rebinding / monkey patch
getattr / setattr / descriptor / special method
type(...) / metaclass / dynamic method injection
nested function / nonlocal / callback dict / async / await
```

### Step 2. Semantic Gap Classification

入口：

```text
pysembridge/recognizer/classifier.py
```

FeatureHit 被归入语义断链大类：

| Gap Family | Meaning |
| --- | --- |
| `dynamic_receiver_callgraph` | 动态调用目标、receiver、decorator、framework wrapper |
| `container_dict_key_flow` | list/tuple/dict/key/value/generator/comprehension |
| `string_builder_flow` | f-string、join、format、%-format、拼接 |
| `rebinding_platform_flow` | alias、条件 import、平台分支、monkey patch |
| `dynamic_attribute_protocol` | getattr、descriptor、特殊方法 |
| `dynamic_class_metaprogramming` | type、metaclass、动态方法注入 |
| `callback_parser_dispatch` | callback、闭包、parser/event-loop 调度 |
| `serialization_field_flow` | 反序列化到对象字段传播 |

分类输出会进入 `auto-bundle.json`。

### Step 3. Bridge Synthesis

入口：

```text
pysembridge/synthesizer/auto.py
```

流程：

```text
classifications
  -> select concrete synthesizer
  -> synthesize bridge.json
```

当前已经实现两个 concrete synthesizer：

```text
pysembridge/synthesizer/pyload.py
  receiver + tuple/list element + generator/join string builder

pysembridge/synthesizer/pymysql.py
  receiver + dict key + %-format string builder
```

未来每类断链应继续补独立 synthesizer：

```text
receiver.py
container.py
string_builder.py
rebinding.py
reflection.py
metaprogramming.py
callback.py
serialization.py
```

### Step 4. Semantic Bridge IR

Bridge 是工具无关中间表示：

```json
{
  "gap_types": ["receiver", "dict_key", "string_builder"],
  "graph_facts": {
    "type_facts": [],
    "call_edges": []
  },
  "flow_facts": {
    "dict_key_transfers": [],
    "string_transfers": []
  },
  "evidence": [],
  "validation": {
    "expected_sink": {}
  }
}
```

语义补充分成几类：

| Semantic Fact | Purpose |
| --- | --- |
| Graph facts | 补调用图边、receiver 类型、callback 边 |
| Flow facts | 补污点传播边、容器元素、dict key、字符串构造 |
| Binding facts | 补 alias、条件 import、平台分支 |
| Object/class facts | 补动态类、descriptor、动态方法 |
| Evidence/validation | 记录证据位置和 expected sink |

### Step 5. Bridge Verification

入口：

```text
pysembridge/verifier/chain.py
```

验证 bridge 内部是否存在 source 到 sink 的补充路径。

例如 PyMySQL：

```text
key
  -> args.keys
  -> _escape_args.return.keys
  -> query
  -> self._query.arg0
```

如果 bridge 内部不可达，pipeline 会失败。

### Step 6. Adapter Projection

当前实现 YASA adapter：

```text
pysembridge/adapters/yasa/compiler.py
```

它把通用 Bridge IR 编译成：

```text
*.yasa-facts.json
```

YASA-sembridge 通过新增参数读取：

```bash
--semanticBridgeFacts <facts.json>
```

YASA 侧相关文件：

```text
YASA-Engine-sembridge/src/config.ts
YASA-Engine-sembridge/src/interface/starter.ts
YASA-Engine-sembridge/src/engine/analyzer/common/semantic-bridge-facts-loader.ts
YASA-Engine-sembridge/src/engine/analyzer/common/semantic-bridge-report-augmenter.ts
```

当前 YASA 后端采用 report-level completion：

```text
YASA baseline result
  + Semantic Bridge facts
  -> enhanced complete-chain SARIF result
```

如果 baseline 没有 finding，YASA-sembridge 也可以根据 facts 创建 synthetic enhanced result。

### Step 7. SARIF Complete Trace Verification

入口：

```text
pysembridge/verifier/sarif.py
```

验证：

```text
report.sarif exists
semanticBridgeEnhanced == true
expected sink appears
required trace fragments appear
```

最终写入：

```text
pipeline-summary.json
```

## 5. End-to-End Command

以 PyMySQL 为例：

```bash
python3 -m pysembridge.cli run-yasa \
  --project /home/ubuntu/llm-yasa-repair/py-bench/cve-2024-36039-pymysql \
  --project-name cve-2024-36039-pymysql \
  --output-dir experiments/results/tool-pipeline/cve-2024-36039-pymysql \
  --yasa-dir /home/ubuntu/llm-yasa-repair/YASA-Engine-sembridge \
  --rule-config /home/ubuntu/llm-yasa-repair/py-result/tool-rules/yasa/cve-2024-36039-pymysql-precise.json \
  --source key \
  --sink self._query.arg0 \
  --expected-sink self._query \
  --expected-trace-contains _escape_args \
  --expected-trace-contains "query = query %"
```

输出结构：

```text
experiments/results/tool-pipeline/<cve>/
  pipeline-summary.json
  generated/
    <cve>.auto-bundle.json
    <cve>.bridge.json
    <cve>.yasa-facts.json
  yasa/
    report.sarif
    semantic_bridge_summary.json
    scan_summary.json
    yasa.stdout.log
    yasa.stderr.log
```

## 6. Verified CVE Benchmarks

### CVE-2025-55156 / pyload

Dynamic gap:

```text
receiver
  + container/tuple element
  + generator/join string builder
```

Bridge path:

```text
url
  -> data[*][3]
  -> generator.element
  -> statuses
  -> self.c.execute.arg0
```

Enhanced trace:

```text
poc_cve_2025_55156_pyload.py:16 cve_2025_55156_source()
poc_cve_2025_55156_pyload.py:16 url
poc_cve_2025_55156_pyload.py:17 data
poc_cve_2025_55156_pyload.py:18 db.update_link_info
file_database.py:261 FileDatabaseMethods.update_link_info
file_database.py:270 statuses
file_database.py:271 self.c.execute
```

Pipeline result:

```json
{
  "ok": true,
  "result_count": 2,
  "enhanced_result_count": 1
}
```

### CVE-2024-36039 / PyMySQL

Dynamic gap:

```text
receiver
  + dict-key propagation
  + %-format string builder
```

Original YASA baseline:

```text
findingCount = 0
matchedSinkCount = 4
```

Bridge path:

```text
key
  -> args.keys
  -> _escape_args.return.keys
  -> query
  -> self._query.arg0
```

Enhanced trace:

```text
poc_cve_2024_36039_pymysql.py:33 FakeCursor().execute(query, args)
pymysql/cursors.py:133 Cursor.execute
pymysql/cursors.py:151 Cursor.mogrify
pymysql/cursors.py:100 {key: conn.literal(val) for (key, val) in args.items()}
pymysql/cursors.py:129 query = query % self._escape_args(args, conn)
pymysql/cursors.py:153 self._query(query)
```

Pipeline result:

```json
{
  "ok": true,
  "result_count": 1,
  "enhanced_result_count": 1
}
```

## 7. Role of LLM

当前实现主要是规则化 AST 识别和模板化 synthesis。LLM 后续适合放在：

```text
ambiguous feature ranking
local code window explanation
candidate bridge fact generation
missing edge repair proposal
```

但 LLM 输出必须受限为 schema-constrained Semantic Bridge IR，并经过：

```text
schema validation
bridge verifier
tool rerun
SARIF trace verifier
```

因此 LLM 不是直接判漏洞，而是辅助生成可验证语义补丁。

## 8. Current Boundary

已经实现：

```text
AST feature recognition for major Python dynamic families
generic semantic gap classification
tool-independent Semantic Bridge IR
YASA facts adapter
YASA-sembridge backend
end-to-end pipeline command
bridge verifier
SARIF verifier
two executable CVE synthesizers: pyload and PyMySQL
```

仍需补齐：

```text
more concrete synthesizers:
  reflection/getattr
  dynamic class/metaprogramming
  callback/parser dispatch
  rebinding/platform branch
  serialization/field propagation

more tool adapters:
  CodeQL additional flow predicates
  Pysa model generation
  Semgrep pattern-propagators

deeper YASA integration:
  analyzer-level call graph and taint propagation injection
```

## 9. Suggested Paper Framing

推荐表述：

```text
PySemBridge is a semantic-bridge framework for repairing under-tainting caused
by Python dynamic features. It extracts AST-level dynamic-feature evidence,
classifies semantic gap families, synthesizes tool-independent bridge facts,
projects them to analyzer-specific backends, and validates whether complete
source-to-sink traces are recovered.
```

不要表述为：

```text
YASA analyzer itself has been fully fixed.
```

当前准确表述是：

```text
YASA-sembridge uses report-level completion to validate that generated semantic
facts are sufficient to recover complete taint traces. Analyzer-level injection
is a future backend improvement.
```
