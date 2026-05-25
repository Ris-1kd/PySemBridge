# 20 CVE Summary Table

| CVE | 项目版本 | 漏洞类型 | 代表 Python 特性 | YASA 扫描结果 | 链路完整性 | 断链位置 |
|---|---|---|---|---|---|---|
| CVE-2022-24065 | cookiecutter（漏洞样本） | 命令注入 | helper 转发、repo_type 动态分派、argv 元素传播 | baseline 主要看到 checkout 参数进入执行边界；sembridge 可补全 | 不完整 | `checkout` 经 helper 进入 Mercurial 执行边界前断 |
| CVE-2023-5752 | pip（漏洞样本） | 命令注入 | VCS backend registry、对象字段 `RevOptions`、值重绑定 | baseline 先看到后半段命令构造；sembridge 已补全 | 不完整 | `url -> backend -> RevOptions.revision -> sink` 中段断 |
| CVE-2024-32027 | kohya_ss（漏洞样本） | 命令注入 | `dict -> SimpleNamespace`、平台分支、分支内命令构造 | baseline 只到平台/分支后的后半段；sembridge 已补全 | 不完整 | `ui dict -> namespace -> generate_caption_database` 分支前断 |
| CVE-2024-52803 | LLaMA-Factory（漏洞样本） | 命令注入 | `args` 字典字段、helper return value、f-string 命令 | baseline 只到 `cmd -> Popen`；sembridge 已补全 | 不完整 | `args["output_dir"] -> save_cmd(args) -> cmd` 前半段断 |
| CVE-2024-6345 | setuptools（漏洞样本） | 命令注入 | URL 解析、`rsplit('@', 1)`、helper dispatch | baseline 只看到后半段 hg 命令；sembridge 已补全 | 不完整 | `vcs_url -> revision split -> hg cmd` 中段断 |
| CVE-2025-12763 | pgAdmin 4（漏洞样本） | 命令注入 | nested helper、argv list 追加、shell 执行切换 | baseline 只到 `command -> Popen`；sembridge 已补全 | 不完整 | `filepath -> short_filepath() -> args.append(filepath)` 断 |
| CVE-2025-49835 | GPT-SoVITS（漏洞样本） | 命令注入 | dataclass 字段、helper return、`cmd +=` 累积 | baseline 只到 `shell_command -> Popen`；sembridge 已补全 | 不完整 | `request.asr_inp_dir -> select_input_path() -> cmd +=` 断 |
| CVE-2025-54072 | yt-dlp（漏洞样本） | 命令注入 | `info` dict lookup、placeholder replacement、Windows 分支 | baseline 只看到后半段 shell quote / exec；sembridge 已补全 | 不完整 | `info dict -> placeholder replace -> shell_quote` 断 |
| CVE-2026-45369 | python-utcp（漏洞样本） | 命令注入 | `tool_args` 字典、正则回调/嵌套函数、shell script builder | baseline 只到 `full_command -> Popen`；sembridge 已补全 | 不完整 | `tool_args["id"] -> replace_placeholder() -> script_lines/script` 断 |
| CVE-2025-47273 | setuptools（漏洞样本） | 路径穿越 / 任意文件写入 | `urlparse` / `unquote`、helper forwarding、`os.path.join` 语义 | baseline 只到 `filename -> open`；sembridge 已补全 | 不完整 | `url -> egg_info_for_url() -> name -> os.path.join(tmpdir, name)` 断 |
| CVE-2026-40576 | excel-mcp-server（漏洞样本） | 路径穿越 / 任意文件写入 | `tool_args` 字典字段、helper return、`EXCEL_FILES_PATH + join` | baseline 只到 `target_file -> open`；sembridge 已补全 | 不完整 | `tool_args["filepath"] -> select_filepath() -> get_excel_path()` 断 |
| CVE-2022-28346 | Django（漏洞样本） | SQL 注入 | ORM alias、容器传播、查询编译链 | baseline 只到近端 SQL 执行边界；sembridge 已补全 | 不完整 | alias source 经 ORM 聚合/编译链到 `cursor.execute` 前断 |
| CVE-2023-47128 | Piccolo（漏洞样本） | SQL 注入 | 构造器字段、临时对象 `Savepoint`、async method dispatch | baseline 到临时对象或近端执行；sembridge 已补全 | 不完整 | `Savepoint.name -> connection.execute` 前断 |
| CVE-2023-49736 | Apache Superset（漏洞样本） | SQL 注入 | closure capture、`replace`/f-string、helper return | baseline 只到后半段 SQL wrapper；sembridge 已补全 | 不完整 | closure 中字符串构造返回到 sink wrapper 前断 |
| CVE-2024-9774 | python-sql（漏洞样本） | SQL 注入 | list 容器、DSL 对象、`__str__` 特殊方法分发 | baseline 只到最终 `sql -> run_sql`；sembridge 已补全 | 不完整 | `conditions -> And(...) -> Select.__str__ / NaryOperator.__str__` 断 |
| CVE-2025-59681 | Django（漏洞样本） | SQL 注入 | `**kwargs` 展开、helper chain、注释语义 | baseline 到近端聚合 SQL；sembridge 已补全 | 不完整 | `alias kwargs -> aggregate() -> compiler` 断 |
| CVE-2025-64104 | langgraph-checkpoint-sqlite（漏洞样本） | SQL 注入 | dict key 传播、条件拼接、tuple query return | baseline 只到近端 query execute；sembridge 已补全 | 不完整 | `filter key -> filter_conditions -> prepared query tuple` 断 |
| CVE-2025-67644 | langgraph-checkpoint-sqlite（漏洞样本） | SQL 注入 | dict key、helper composition、WHERE fragment | baseline 只到后半段 SQL statement；sembridge 已补全 | 不完整 | `_metadata_predicate() -> search_where() -> list()` 断 |
| CVE-2026-29080 | Rucio（漏洞样本） | SQL 注入 | filter key/value 到局部变量、dialect 分支、`sqlalchemy.text` 格式化 | baseline 到近端 raw SQL 构造；sembridge 设计为补全 | 不完整 | `HTTP filter key/value -> Oracle branch -> text(...)` 断 |
| CVE-2026-41490 | dagster-snowflake（漏洞样本） | SQL 注入 | 容器字段、helper chain、静态分区子句字符串化 | baseline 到近端 WHERE clause 构造；sembridge 设计为补全 | 不完整 | `partition key -> TablePartitionDimension -> _static_where_clause` 断 |

