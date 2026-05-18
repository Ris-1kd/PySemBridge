# Semantic Feature Coverage

PySemBridge 的语义识别层以 Python AST 为主，源码片段只用于 evidence 展示。

Pipeline:

```text
source code
  -> ast.parse
  -> FeatureHit extraction
  -> semantic gap family classification
  -> candidate bridge specs
  -> family-specific bridge synthesis when supported
```

## Coverage Table

| 断链大类 | 当前识别覆盖 | 代表 FeatureHit |
| --- | --- | --- |
| 动态调用目标 | decorator、framework wrapper、route/middleware 注册、插件注册、工厂函数、动态 receiver、dynamic import、async task/event loop | `dynamic_receiver_call`, `decorator_control_flow`, `framework_wrapper`, `framework_registration`, `plugin_registration`, `factory_function`, `dynamic_import`, `async_task_schedule`, `event_loop_dispatch` |
| 容器与元素级语义 | list/tuple/dict literal、subscript、dict key/value、generator expression、list/set/dict comprehension | `list_literal`, `tuple_literal`, `dict_literal`, `container_subscript`, `generator_expression_flow`, `comprehension_flow`, `dict_comprehension_flow` |
| 动态字符串构造 | f-string、`join`、`join(generator)`、`%` 格式化、`.format()`/`format_map()`、字符串拼接、字符串累加 | `f_string_builder`, `string_join_builder`, `string_join_generator`, `percent_string_format_builder`, `string_format_builder`, `string_concat_builder`, `string_accumulator_builder` |
| 名称绑定与平台分支 | alias、函数变量重绑定、条件绑定、条件 import、平台分支、monkey patch | `alias_assignment`, `function_rebinding`, `conditional_binding`, `conditional_import`, `platform_branch`, `monkey_patch_assignment` |
| 反射与动态属性 | `getattr/setattr/hasattr/delattr`、动态属性名、descriptor/property、特殊方法协议、动态方法注入 | `dynamic_attribute_access`, `descriptor_property`, `special_method_protocol`, `dynamic_method_injection` |
| 动态类/元编程 | `type(...)`、class factory、metaclass、动态生成/注入方法、descriptor | `dynamic_type_construction`, `factory_function`, `metaclass_protocol`, `dynamic_method_injection`, `descriptor_property` |
| 闭包与 callback 调度 | nested function、`nonlocal`、callback dict/list/tuple、callback 参数、高阶函数、async/await、event loop | `closure_callback`, `nonlocal_closure_state`, `callback_dict`, `callback_container`, `callback_argument`, `higher_order_function`, `async_function`, `await_expression`, `event_loop_dispatch` |

## Current Pyload Recognition Result

After expanding coverage, `cve-2025-55156-pyload` produces:

```text
feature_count = 35023

container_dict_key_flow        10902
dynamic_receiver_callgraph      9544
callback_parser_dispatch        7495
rebinding_platform_flow         3921
string_builder_flow             1670
dynamic_attribute_protocol       802
serialization_field_flow         720
dynamic_class_metaprogramming    555
```

Newly recognized examples include:

```text
comprehension_flow
dict_comprehension_flow
generator_expression_flow
framework_wrapper
plugin_registration
callback_dict
conditional_import
monkey_patch_assignment
percent_string_format_builder
string_concat_builder
factory_function
```

## Important Boundary

This document describes **recognition coverage**.

It does not mean every recognized family already has a precise executable bridge
synthesizer.

Current status:

```text
generic semantic recognition coverage: broad
candidate gap spec generation: broad
executable bridge synthesis: currently complete for pyload-like
  receiver + container + string_builder pattern
```

Next implementation step:

```text
one concrete bridge synthesizer per semantic family
  -> dynamic receiver/framework/plugin
  -> dict-key/container/comprehension
  -> string builder
  -> rebinding/platform/conditional import
  -> reflection/dynamic attribute
  -> dynamic class/metaprogramming
  -> callback/parser dispatch
```
