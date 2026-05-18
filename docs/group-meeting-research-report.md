# PySemBridge 课题组会汇报报告

题目建议：

```text
面向 Python 动态语义的静态污点分析断链修复：基于 Semantic Bridge 的可验证增强框架
```

## 1. 背景：为什么关注 Python 静态污点分析断链

静态污点分析是漏洞检测中非常核心的一类程序分析技术。它通常关注：

```text
source -> propagation -> sink
```

例如：

```text
HTTP request 参数
  -> 经过变量、函数、对象、字符串构造
  -> 进入 SQL execute / os.system / file open / network request
```

如果 source 可控数据最终进入危险 sink，就可能形成漏洞链路。

在 Java、C/C++ 等相对静态的语言里，调用图、类型、字段访问等信息虽然也复杂，但静态分析器通常有比较成熟的建模基础。Python 则不同。Python 有大量动态语言特性：

```text
动态 receiver
动态属性
容器元素
dict key/value
字符串动态构造
decorator
callback
monkey patch
metaclass
条件 import
平台分支
```

这些特性会导致静态污点分析出现一种典型问题：**欠污染传播**，也就是工具不是误报太多，而是污点传播不到真实 sink。

我把这个问题称为：

```text
Python dynamic semantics induced taint breakage
```

中文可以叫：

```text
Python 动态语义导致的污点传播断链问题
```

## 2. 最初的问题发现

课题最开始不是直接设计工具，而是从真实 CVE benchmark 和多个静态分析工具的对比实验中发现问题。

我们选取了 Python 真实 CVE 项目，并使用多个静态污点分析工具进行扫描：

```text
YASA
CodeQL
Pysa
Semgrep
```

实验关注点不是只看“是否报一个 finding”，而是看：

```text
工具是否能输出完整 source-to-real-sink 污点链路
```

原因是有些工具可能报到了中间边界函数，比如：

```text
db.update_link_info(data)
```

但真实漏洞 sink 是：

```text
self.c.execute(...)
```

如果工具只报到中间函数，就不能说明它真正理解了漏洞链路。

### 2.1 观察到的典型断链

以 pyload 为例：

```python
url = cve_2025_55156_source()
data = [("name", 1, 2, url)]
return db.update_link_info(data)
```

真实漏洞在：

```python
statuses = "','".join(x[3] for x in data)
self.c.execute(f"SELECT id FROM links WHERE url IN ('{statuses}')")
```

工具的困难在于：

```text
1. db.update_link_info(data) 中 db 的真实类型难以确定
2. url 被放入 tuple/list 的第 4 个元素 data[*][3]
3. x[3] for x in data 通过 generator expression 取出
4. join 构造字符串 statuses
5. f-string 把 statuses 拼入 SQL
```

YASA baseline 只报到：

```text
db.update_link_info(data)
```

没有进入：

```text
file_database.py:270 statuses = "','".join(...)
file_database.py:271 self.c.execute(...)
```

这说明断链不是 source/sink 规则简单缺失，而是中间 Python 语义传播缺失。

### 2.2 PyMySQL 的另一个断链

PyMySQL 例子：

```python
key = cve_2024_36039_source()
args = {key: "safe-value"}
query = "SELECT * FROM users WHERE name=%(name)s"
return FakeCursor().execute(query, args)
```

内部：

```python
return {key: conn.literal(val) for (key, val) in args.items()}
query = query % self._escape_args(args, conn)
self._query(query)
```

这里的困难是：

```text
1. 污点在 dict key 上，不在 value 上
2. dict comprehension 保留 key
3. %-format 使用 mapping key 构造最终 query
4. query 进入 self._query(query)
```

原始 YASA baseline：

```text
findingCount = 0
matchedSinkCount = 4
```

说明工具知道项目里有 sink，但没有恢复出完整污点传播链路。

## 3. 研究问题抽象

通过多个 CVE 和工具扫描，我们把问题抽象为：

```text
现有静态污点分析器对 Python 动态语义支持不足，导致真实漏洞链路中 source 到 sink 的传播断裂。
```

进一步可以拆成三个研究问题。

### RQ1：Python 真实 CVE 中有哪些共性的动态语义断链模式？

我们目前归纳出以下大类：

| 类别 | 典型特性 | 为什么静态分析困难 |
| --- | --- | --- |
| 动态调用目标 | receiver、decorator、framework wrapper、工厂函数、插件注册 | 不知道 `obj.method()` 实际进入哪个函数 |
| 容器与元素级语义 | list、tuple、dict、dict key/value、generator、comprehension | 污点在容器某个元素或 key 上，粗粒度变量 taint 容易丢 |
| 动态字符串构造 | f-string、join、format、`%`、拼接 | source 被嵌入 SQL/命令/URL 字符串，需要字符串摘要 |
| 名称绑定与平台分支 | alias、条件 import、平台 fallback、函数重绑定 | 同一个名字在不同路径指向不同实现 |
| 反射与动态属性 | getattr、setattr、descriptor、特殊方法 | 方法名/属性名运行期决定，源码没有显式调用边 |
| 动态类/元编程 | type、metaclass、class factory、monkey patch | 方法和类结构运行期生成 |
| 闭包与 callback 调度 | nested function、nonlocal、callback dict、parser/event loop | 调用点隐含在框架调度里 |

严格论文中可以把“动态类/元编程”和“反射/动态属性”合并，也可以把“serialization/field flow”作为容器/字段传播的子类。

### RQ2：这些断链是规则问题，还是分析器语义模型不足？

实验中发现，很多 case 即使 source/sink 规则已经写好，工具仍然不能输出完整链路。

例如 PyMySQL：

```text
matchedSinkCount = 4
findingCount = 0
```

说明 sink 能匹配到，但 source 到 sink 的传播没连上。

因此这类问题更接近：

```text
静态分析器缺少 Python 动态语义传播模型
```

而不是简单的：

```text
source/sink rule 写错
```

### RQ3：能否设计一种工具无关的语义补充层，辅助多个静态污点分析工具恢复完整链路？

这是本课题的核心目标。

我们不希望只修 YASA 的某个 bug，也不希望直接让 LLM 输出漏洞结论。我们希望设计一个中间层：

```text
Semantic Bridge IR
```

它表达的是：

```text
这里缺一条调用边
这里缺一个容器元素传播
这里缺一个字符串构造传播
这里缺一个 callback 调度关系
```

然后再把这个 IR 适配到不同工具：

```text
YASA facts
CodeQL additional flow predicates
Pysa models
Semgrep pattern propagators
```

## 4. 核心思想：Semantic Bridge

Semantic Bridge 的作用是补充静态分析器缺失的动态语义。

它不是 source/sink 规则本身，而是 source 和 sink 之间的“中间传播语义”。

### 4.1 Semantic Bridge 补什么？

大致分为五类。

| 补充语义类别 | 解决的问题 | 例子 |
| --- | --- | --- |
| Graph Facts | 调用图断链 | `db.update_link_info -> FileDatabaseMethods.update_link_info` |
| Flow Facts | 数据流断链 | `url -> data[*][3] -> statuses` |
| Binding Facts | 名称绑定不确定 | `run -> win_run / posix_run` |
| Object/Class Facts | 动态类/对象结构缺失 | `Cls.run -> run` |
| Evidence/Validation | 可解释和可验证 | expected sink、trace suffix、源码位置 |

### 4.2 Semantic Bridge IR 示例

pyload 的 bridge 核心信息：

```json
{
  "gap_types": ["receiver", "container", "string_builder"],
  "graph_facts": {
    "call_edges": [
      {
        "from": "db.update_link_info(data)",
        "to": "FileDatabaseMethods.update_link_info"
      }
    ]
  },
  "flow_facts": {
    "container_transfers": [
      {"from": "url", "to": "data[*][3]"},
      {"from": "data[*][3]", "to": "generator.element"}
    ],
    "string_transfers": [
      {"from": "generator.element", "to": "statuses"},
      {"from": "statuses", "to": "self.c.execute.arg0"}
    ]
  }
}
```

PyMySQL 的 bridge 核心信息：

```json
{
  "gap_types": ["receiver", "dict_key", "string_builder"],
  "flow_facts": {
    "dict_key_transfers": [
      {"from": "key", "to": "args.keys"},
      {"from": "args.keys", "to": "_escape_args.return.keys"}
    ],
    "string_transfers": [
      {"from": "_escape_args.return.keys", "to": "query"},
      {"from": "query", "to": "self._query.arg0"}
    ]
  }
}
```

## 5. 方法设计

整体方法分为六步。

```text
CVE source project
  -> AST feature extraction
  -> semantic gap classification
  -> bridge synthesis
  -> adapter projection
  -> analyzer run
  -> complete trace verification
```

### 5.1 AST 特征提取

实现位置：

```text
pysembridge/recognizer/features.py
```

我们不使用简单字符串 grep，而是使用 Python AST：

```text
source code -> ast.parse -> AST visitor -> FeatureHit
```

例如：

```python
statuses = "','".join(x[3] for x in data)
```

会识别出：

```text
string_join_generator
generator_expression_flow
container_subscript
```

例如：

```python
query = query % self._escape_args(args, conn)
```

会识别出：

```text
percent_string_format_builder
dynamic_receiver_call
```

当前已覆盖的特征：

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

### 5.2 语义断链分类

实现位置：

```text
pysembridge/recognizer/classifier.py
```

FeatureHit 被映射到 gap family：

```text
dynamic_receiver_callgraph
container_dict_key_flow
string_builder_flow
rebinding_platform_flow
dynamic_attribute_protocol
dynamic_class_metaprogramming
callback_parser_dispatch
serialization_field_flow
```

输出结果写入：

```text
auto-bundle.json
```

它告诉我们：

```text
这个项目可能有哪些动态语义断链风险
每一类命中了哪些 AST 特征
后续应该由哪个 synthesizer 处理
```

### 5.3 Bridge 合成

实现位置：

```text
pysembridge/synthesizer/auto.py
pysembridge/synthesizer/pyload.py
pysembridge/synthesizer/pymysql.py
```

现在已经实现两个 concrete synthesizer：

| Synthesizer | 支持模式 | 已验证 CVE |
| --- | --- | --- |
| `pyload.py` | receiver + tuple/list element + join/f-string | CVE-2025-55156 |
| `pymysql.py` | receiver + dict key + %-format | CVE-2024-36039 |

未来要继续补：

```text
reflection/getattr synthesizer
callback/parser synthesizer
dynamic class/metaprogramming synthesizer
rebinding/platform synthesizer
serialization/field synthesizer
```

### 5.4 Bridge 内部验证

实现位置：

```text
pysembridge/verifier/chain.py
```

在把 bridge 交给分析器前，先检查 bridge 自己能否形成 source 到 sink 的路径。

例如 PyMySQL：

```text
key
  -> args.keys
  -> _escape_args.return.keys
  -> query
  -> self._query.arg0
```

如果 bridge 自己内部都连不上，就不应该进入工具扫描阶段。

### 5.5 工具适配

当前后端是 YASA。

PySemBridge 侧：

```text
pysembridge/adapters/yasa/compiler.py
```

YASA 侧：

```text
YASA-Engine-sembridge/src/config.ts
YASA-Engine-sembridge/src/interface/starter.ts
YASA-Engine-sembridge/src/engine/analyzer/common/semantic-bridge-facts-loader.ts
YASA-Engine-sembridge/src/engine/analyzer/common/semantic-bridge-report-augmenter.ts
```

新增 YASA 参数：

```bash
--semanticBridgeFacts <facts.json>
```

当前 YASA 集成方式是：

```text
report-level completion
```

即：

```text
YASA baseline finding
  + Semantic Bridge facts
  -> enhanced complete-chain SARIF finding
```

如果 baseline 没有 finding，也可以创建 synthetic enhanced result。这一点对 PyMySQL 很重要。

### 5.6 完整链路验证

实现位置：

```text
pysembridge/verifier/sarif.py
```

检查：

```text
report.sarif 是否存在
是否有 semanticBridgeEnhanced == true
是否包含 expected sink
trace 是否包含关键中间语句
```

最后输出：

```text
pipeline-summary.json
```

## 6. 工具实现

当前已经有一个端到端命令：

```bash
python3 -m pysembridge.cli run-yasa \
  --project <CVE source project> \
  --project-name <CVE name> \
  --output-dir <output dir> \
  --yasa-dir /home/ubuntu/llm-yasa-repair/YASA-Engine-sembridge \
  --rule-config <YASA rule config> \
  --source <source expr> \
  --sink <bridge sink expr> \
  --expected-sink <final sink text>
```

这个命令自动完成：

```text
1. AST feature extraction
2. semantic gap classification
3. bridge synthesis
4. bridge verification
5. YASA facts compilation
6. YASA-sembridge scan
7. SARIF verification
8. pipeline-summary output
```

输出目录结构：

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

## 7. 实验验证

### 7.1 CVE-2025-55156 / pyload

漏洞类型：

```text
SQL injection
```

动态特性：

```text
receiver + tuple/list element + generator/join + f-string
```

原始断链：

```text
YASA 只能报到 db.update_link_info(data)
没有进入 self.c.execute(...)
```

Bridge 路径：

```text
url
  -> data[*][3]
  -> generator.element
  -> statuses
  -> self.c.execute.arg0
```

最终 enhanced trace：

```text
poc_cve_2025_55156_pyload.py:16 cve_2025_55156_source()
poc_cve_2025_55156_pyload.py:16 url
poc_cve_2025_55156_pyload.py:17 data
poc_cve_2025_55156_pyload.py:18 db.update_link_info
file_database.py:261 FileDatabaseMethods.update_link_info
file_database.py:270 statuses
file_database.py:271 self.c.execute
```

验证结果：

```json
{
  "ok": true,
  "result_count": 2,
  "enhanced_result_count": 1
}
```

### 7.2 CVE-2024-36039 / PyMySQL

漏洞类型：

```text
SQL query construction issue
```

动态特性：

```text
receiver + dict-key propagation + %-format string builder
```

原始 YASA baseline：

```text
findingCount = 0
matchedSinkCount = 4
```

Bridge 路径：

```text
key
  -> args.keys
  -> _escape_args.return.keys
  -> query
  -> self._query.arg0
```

最终 enhanced trace：

```text
poc_cve_2024_36039_pymysql.py:33 FakeCursor().execute(query, args)
pymysql/cursors.py:133 Cursor.execute
pymysql/cursors.py:151 Cursor.mogrify
pymysql/cursors.py:100 {key: conn.literal(val) for (key, val) in args.items()}
pymysql/cursors.py:129 query = query % self._escape_args(args, conn)
pymysql/cursors.py:153 self._query(query)
```

验证结果：

```json
{
  "ok": true,
  "result_count": 1,
  "enhanced_result_count": 1
}
```

## 8. 创新点

### 8.1 从工具规则问题转向动态语义断链问题

传统工作常关注：

```text
source/sink specification extraction
```

本课题强调：

```text
即使 source/sink 规则存在，Python 动态语义也会导致传播断链。
```

因此研究对象是：

```text
middle-chain semantic gaps
```

而不是只做 source/sink 规则生成。

### 8.2 工具无关 Semantic Bridge IR

不是直接修 YASA，也不是写某个工具专用规则，而是设计：

```text
tool-independent semantic bridge
```

再投影到不同工具。

这为后续适配 CodeQL/Pysa/Semgrep 留出了空间。

### 8.3 可验证语义补全

Bridge 生成后不是直接相信，而是经过：

```text
bridge reachability verification
tool rerun
SARIF complete-trace verification
```

这使得 LLM 或规则生成的语义补丁有验证闭环。

### 8.4 按动态特性分类的可组合 synthesizer

不同于每个 CVE 写一个脚本，目标是：

```text
one synthesizer per semantic family
```

例如：

```text
receiver synthesizer
container/dict synthesizer
string builder synthesizer
callback synthesizer
reflection synthesizer
```

一个 CVE 链路可以由多个 synthesizer 组合完成。

## 9. 与 LLM 的关系

当前实现主要是规则化 AST 识别和模板化合成。

LLM 后续适合放在：

```text
复杂代码窗口理解
ambiguous feature ranking
bridge fact candidate generation
缺失 edge/transfer 修复建议
```

但 LLM 不直接输出漏洞结论。

推荐流程：

```text
AST recognizer finds candidate gap
  -> LLM receives local code window + baseline trace
  -> LLM emits schema-constrained bridge facts
  -> verifier checks facts
  -> analyzer reruns
  -> SARIF verifier validates complete trace
```

这样可以避免“只是借助 LLM”的质疑，而是把 LLM 放入可验证程序分析框架中。

## 10. 当前局限

当前已经实现：

```text
AST feature extraction
semantic gap classification
Semantic Bridge IR
YASA facts adapter
YASA-sembridge backend
end-to-end run-yasa pipeline
pyload synthesizer
PyMySQL synthesizer
bridge verifier
SARIF verifier
```

仍需补充：

```text
reflection/getattr synthesizer
dynamic class/metaprogramming synthesizer
callback/parser dispatch synthesizer
rebinding/platform branch synthesizer
serialization/field synthesizer
CodeQL adapter
Pysa adapter
Semgrep adapter
YASA analyzer-level injection
更多 CVE benchmark 验证
```

## 11. 后续工作计划

### 短期

```text
1. 把 pyload synthesizer 拆成 receiver/container/string_builder 三个可组合模块
2. 把 PyMySQL synthesizer 拆成 receiver/dict-key/percent-format 三个可组合模块
3. 增加 RPyC getattr/reflection synthesizer
4. 增加 python-multipart callback/parser synthesizer
5. 对 6 个 CVE bench 跑统一 pipeline
```

### 中期

```text
1. 实现 CodeQL additional flow adapter
2. 实现 Semgrep pattern-propagator adapter
3. 实现 Pysa model adapter
4. 对比不同工具消费同一个 Semantic Bridge IR 的能力差异
```

### 长期

```text
1. 引入 LLM 作为 bridge candidate generator
2. 加入 iterative repair loop
3. 将 YASA report-level completion 下沉到 analyzer-level propagation
4. 扩大 benchmark，评估 precision/recall/trace completeness
```

## 12. 组会讲解重点

建议汇报时按下面逻辑讲：

```text
1. 真实 CVE 扫描发现：工具不是不会匹配 sink，而是中间传播断链
2. Python 动态特性导致共性断链
3. 仅生成 source/sink spec 不够，需要补 middle-chain semantics
4. 提出 Semantic Bridge IR
5. 实现 PySemBridge：识别、分类、生成、适配、验证
6. 在 pyload 和 PyMySQL 上恢复完整链路
7. 后续扩展到更多动态特性和更多静态分析工具
```

一句话总结：

```text
PySemBridge 不是替代静态分析器，而是在静态分析器缺失 Python 动态语义时，自动生成可验证的语义桥，帮助工具恢复完整 source-to-sink 污点链路。
```
