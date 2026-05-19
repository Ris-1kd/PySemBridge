# Repository Structure

本文档说明 PySemBridge 仓库中各目录的用途，帮助使用者快速定位工具代码、集成版 YASA 和实验入口。

## Top-Level Layout

```text
pysembridge/          PySemBridge Python 工具源码
bridges/              已整理的 Semantic Bridge IR 示例
benchmarks/py-bench/  Python CVE benchmark 说明与入口
experiments/          可复现实验脚本；results/ 为生成输出，不提交
integrations/yasa/    集成版 YASA-sembridge 工具
docs/                 工具介绍、流程和仓库结构说明
```

## PySemBridge Source

```text
pysembridge/
  cli.py              命令行入口
  ir/                 Semantic Bridge IR schema 和加载器
  recognizer/         Python AST 语义特征识别
  synthesizer/        bridge 候选生成与案例合成
  adapters/yasa/      将 bridge 编译为 YASA facts
  verifier/           bridge 链路和 SARIF 结果验证
  pipeline/           端到端 YASA-sembridge runner
```

常用命令入口都在 `pysembridge.cli` 中，例如：

```bash
python3 -m pysembridge.cli scan-gaps
python3 -m pysembridge.cli compile-yasa
python3 -m pysembridge.cli run-yasa
python3 -m pysembridge.cli verify-sarif
```

## YASA Integration

```text
integrations/yasa/YASA-Engine-sembridge/
```

该目录保存完整的改动版 YASA 工具。它包含 `--semanticBridgeFacts` 参数、facts 加载逻辑、SARIF 增强逻辑和运行所需的 YASA 源码/资源。

不提交的内容包括：

- `node_modules/`
- `logs/`
- `report/`
- 生成的 SARIF 和实验输出

依赖版本由 `integrations/yasa/YASA-Engine-sembridge/package-lock.json` 固定。

## Bridge And Experiment Files

```text
bridges/
  cve-2025-55156-pyload/bridge.json

experiments/scripts/
  compile_pyload_yasa.sh
  run_yasa_sembridge_pyload.sh
  run_auto_pyload_sembridge.sh
```

`bridges/` 中提交稳定的 bridge IR。`experiments/scripts/` 中提交可复现脚本。`experiments/results/` 是运行输出目录，默认由 `.gitignore` 忽略。

## Documentation Scope

`docs/` 只保留三类文档：

- 仓库结构说明：`repository-structure.md`
- 整体工具流程：`tool-development-flow-yasa.md`
- 集成版 YASA 操作指南：`yasa-sembridge-tool-guide.md`

其他过程性材料不放在仓库文档目录中。
