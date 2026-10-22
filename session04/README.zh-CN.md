# 第四课：CSV 导出完整性校验

实现依据：`Class 4 — Hashing, integrity & asymmetric encryption（副本）.pptx`，实际幻灯片 32–34（页脚 13 / 25）（NotesApp: Protect the Grades Export）。

教师导出的 `grades.csv` 保留原始数据，末尾追加：

```text
# HMAC: <64 个小写十六进制字符>
```

使用 Python 标准库 `hmac` 的 HMAC-SHA256。摘要覆盖完整 CSV 的 UTF-8 字节，包括表头、所有行和 CRLF 换行，不包括 HMAC 末行。验证时先验证原始字节，再允许调用方使用内容；使用 `hmac.compare_digest` 比较摘要。

HMAC 验证文件完整性和持有服务器密钥的来源，不隐藏 CSV 内容。不要把它称为可解密的加密。Excel 另存文件可能改变格式并使验证失败；验证时使用原始下载文件。读取数据时，先验证并去掉 HMAC 末行，再交给 CSV parser。

## 使用

现有两个环境均支持此功能，各自使用独立的 HMAC 密钥：

- 当前 HTTPS 环境：<https://localhost/teacher>；新安装的默认 HTTP 环境：<http://127.0.0.1:8080/teacher>
- 评语加密作业版：<http://127.0.0.1:8083/teacher>

用原有教师测试账号登录，在教师页面选择班级的 `export CSV` 或 `Export all grades as CSV`。然后进入 `Verify a CSV export`，选择刚下载的 CSV 并点击 `Verify HMAC`。原文件显示 `HMAC valid.`；修改任一分数、表头、评语或摘要后显示 `HMAC check failed.`。验证页面也可以直接访问 `/verify-export`。

验证不导入成绩，不修改数据库，不保存业务附件。最大文件大小为 10 MiB；无效文件返回 HTTP 400，超限返回 413。只允许教师 session 导出和验证，沿用课程的认证模型。

## 密钥

应用通过 `CsvIntegrity.from_environment()` 从 **`NOTESAPP_CSV_HMAC_KEY`** 读取 64 位十六进制密钥，解码后为 32 bytes。AES 使用独立的 `NOTESAPP_COMMENT_KEY`，两把密钥不能相同。

`runtime.py` 启动器将 `_FILE` 指定的持久文件放入子进程环境，兼顾老师的环境变量读取口径和旧文件兼容。原 `csvhmackey` 卷和原密钥继续使用，因此旧 CSV 仍可验证。只有新安装首次启动才生成随机密钥，权限 `0600`。环境变量无效、旧文件无效或两把密钥相同均停止启动，不静默更换。

密钥不写入 CSV、源码、日志或交付包。不要删除数据库或密钥卷。

## 运行与验证

从 `NoteApp` 目录运行现有环境：

```bash
docker compose -p notesapp-lab -f docker-compose.yml -f compose.lab.yml up -d --build --wait
docker compose -p notesapp-session03 -f compose.session03.yml up -d --build --wait
```

密码与文件格式测试只使用 Python 标准库，无新增依赖：

```bash
python3 -m unittest discover -s web -p test_csv_integrity.py -v
```

在两个实际应用容器中运行完整测试（读取真实导出，不修改成绩）：

```bash
docker compose -p notesapp-lab -f docker-compose.yml -f compose.lab.yml exec -T -e NOTESAPP_RUN_APP_TESTS=1 web python runtime.py python -m unittest test_csv_integrity -v
docker compose -p notesapp-session03 -f compose.session03.yml exec -T -e NOTESAPP_RUN_APP_TESTS=1 web python runtime.py python -m unittest test_csv_integrity -v
docker compose -p notesapp-session03 -f compose.session03.yml exec -T web python runtime.py python test_homework.py
```

最后一个命令回归验证原有评语加密功能，会建立并清理临时测试成绩。

2026-10-21 验证结果：两个运行环境各 18 项 HMAC 测试全部通过，原有 17 项评语加密测试全部通过。两个应用重启后均能验证重启前签发的文件，HTTP health check 通过；两套数据库的成绩行数和表内容摘要均与修改前一致。结果见 `results/verification.json`。

实现位于 `web/csv_integrity.py`、`web/app.py` 和 `web/templates/verify_export.html`。C3 和 C4 的唯一应用实现均在 `web/`；原 `session03/` 命令保留为兼容入口。

本次只完成导出校验。课程应用原有的认证和授权弱点仍存在，因此不能仅凭 HMAC 将此教学应用视为生产安全系统。

参考：[Python hmac 官方文档](https://docs.python.org/3/library/hmac.html)。

2026-10-22 集成复验：默认应用及 8083 环境各 45 项检查通过，含 17 项 AES、18 项 HMAC、5 项密钥配置、5 项现有密码迁移回归。迁移前签发的 CSV 均仍有效，成绩和评语逻辑内容一致。逐项依据见 [验收表](../P1-C3-C4-REQUIREMENTS.md)。
