# NotesApp 实验使用说明

已经 Fork 到 https://github.com/pursurer/NoteApp ，本地分支为 `codex/notesapp-threat-model`。

## 打开应用

网页地址： http://127.0.0.1:8080 。测试账号见项目根目录 `README.md`；不需要个人或学校账号。

从项目根目录运行：

```bash
docker compose -p notesapp-lab -f docker-compose.yml -f compose.lab.yml up -d --build --wait
```

`compose.lab.yml` 是本地隔离配置：网页只开放本机端口，数据库不开放宿主机端口，移除网页容器的宿主机目录和 Docker socket 挂载。数据库使用内部网络；网页额外连接 frontend 网络以供本机访问。网页没有配置出站过滤。老师提供的应用代码与教学漏洞没有修改。

停止并保留数据库：

```bash
docker compose -p notesapp-lab -f docker-compose.yml -f compose.lab.yml stop
```

## 实验成果

- `NotesApp-data-flow.excalidraw`：在 https://excalidraw.com/ 用“打开”载入。总图和五个分组细图都可编辑。每条箭头的编号对应表格同一行。
- `NotesApp-data-flow-overview.png`：通过 Excalidraw 网页原生导出的总图，适合放入报告。
- `flows.csv`：9 条数据流的发送方、接收方、数据、边界和依据。
- `STRIDE.csv`：9 行初步 STRIDE 分析，每条数据流都考虑 S/T/R/I/D/E。
- `STRIDE.html`：可搜索的表格阅读版。
- `REPORT.md`：英文实验报告初稿，含实验范围、实际观察、流程、威胁表和代码依据。
- `observations.json`：正常请求证据，只保留状态、重定向、表单字段等元数据，不保存密码、Cookie 或 JWT。
- `screenshots/`：网页观察截图；画图截图来自 Excalidraw 网页。`teacher-grade-ids.jpg` 显示教师页的成绩 ID 列；学生成绩页原设计不显示 ID 列。

## 阅读时注意

NotesApp 是成绩管理应用。`notes` 表里的记录是成绩与教师评语。

`Observed` 表示实际观察到正常网页或 HTTP 请求。`Code` 表示从源码确认的处理路径，数据库流没有抓包。成绩写入、用户增删、管理员 Ping 的表单已查看，但没有提交。潜在威胁与代码中明显缺失的防护不等于攻击测试成功。

实际观察覆盖未登录、学生、教师和管理员，共 41 次正常请求；数据库摘要前后相同。学生读取了自己的成绩详情。没有访问其他学生的 API 记录，没有注入、伪造令牌、CSRF、XSS 或压力测试。

提交前补上组员姓名，并与组员复核图和表。本阶段是老师要求的“观察并列出”，两份成果保留用于 Project 1。

## Docker 恢复记录

Docker Desktop 4.93.0 从官方 Apple Silicon 安装包恢复到 `/Applications/Docker.app`；安装包 SHA-256 与 Homebrew 当时提供的值一致，应用代码签名检查通过。现有 CLI/Compose 链接已恢复，Engine 29.8.1 与 Compose v5.5.1 可用。

这次采用官方安装包直接恢复应用，Homebrew 的旧安装收据仍可能显示旧版本；当前实际版本以 Docker Desktop 和 `docker version` 为准。未重置 Docker 用户数据或读取 Docker 登录凭据。

重新观察与生成材料：

```bash
python3 lab/observe.py
python3 lab/build_report.py
```

`build_report.py` 生成可编辑图的输入文件；交付图需要再在 Excalidraw 网页载入、检查，并通过网页保存或导出。不要在手动改图后直接重跑生成器覆盖文件。
