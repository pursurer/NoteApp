# 第三课：课堂与家庭作业

依据：`Session 03 Symmetric Encryption.pdf` 第 30 页。第 31 页的 Project 1 材料也已整理。

2026-10-22：AES 已合入默认 `web/app.py`，默认应用与原 8083 入口使用同一份实现。现有 Argon2 保留。运行前由 `runtime.py` 读取持久密钥并放入服务进程环境；应用从环境变量加载 AES 与 HMAC 密钥。

2026-10-21：当前基础应用和本作业版均已加入[第四课 CSV HMAC 导出校验](../session04/README.zh-CN.md)，评语加密保持启用。下述第三课 PDF 和提交包是当时生成的材料，不包含第四课功能。

## 已完成

| 要求 | 实现与结果 |
|---|---|
| 课堂 1：Caesar 与频率分析 | `caesar.py` 实现加密、解密和 26 个位移的频率评分。自建样例找回位移 11；同一样例的全部 26 种位移均通过。 |
| 课堂 2：ECB 与 GCM 图像比较 | `image_modes.py` 对相同 RGB 像素加密。ECB 保留轮廓；GCM 无可见轮廓。两者均能完整解密；GCM 拒绝单字节篡改。 |
| 家庭作业：加密评语列 | 默认 `web/app.py` 和原 8083 兼容入口使用同一份实现。60 条评语已迁移到 AES-256-GCM。新增、更新、页面、API 和 CSV 均已接入。17 项测试通过。 |
| Project 1 | `project1/` 包含扩展数据流图、16 条流、14 项已评分风险、前三项风险的修复建议和 3 分钟讲稿。 |

课件没有给出指定的待破解密文。本次使用明确标注的自建英文样例，未冒充教师题目答案。

## 查看成果

- `REPORT.md`：课堂与家庭作业英文报告。
- `results/ecb_gcm_comparison.png`：原图、ECB、GCM 并排比较。
- `project1/REPORT.md`：Project 1 英文风险分析。
- `project1/data_flow.svg`：可编辑的矢量数据流图。
- `project1/risks.csv`：14 项风险的条件、STRIDE、可能性、影响、分数、修复建议和源码依据。
- 课程目录的 `output/pdf/`：两份可阅读和提交的 PDF。
- 课程目录的 `output/Session03-Submission.zip`：本地提交材料包。

## 运行家庭作业

从 `NoteApp` 目录运行：

```bash
docker compose -p notesapp-session03 -f compose.session03.yml up -d --build --wait
```

打开 <http://127.0.0.1:8083>。测试账号见原项目 `README.md`。

第二课继续使用 `8080`。第三课使用独立 Compose 项目、数据库卷和密钥卷。没有迁移或覆盖第二课数据库。

运行验证：

```bash
docker compose -p notesapp-session03 -f compose.session03.yml exec -T web python runtime.py python test_homework.py
```

需要停止第三课服务时，保留数据和密钥：

```bash
docker compose -p notesapp-session03 -f compose.session03.yml stop
```

不要删除 `notesapp-session03_commentkey` 密钥卷。密钥丢失后，这个数据库中的评语无法解密。密钥没有写入源码、报告或提交包。

## 运行课堂作业

需要 Python 3.11 或更新版本，以及 `cryptography`、`Pillow`。本次使用 Codex 的已有 Python 运行时，未向宿主机全局 Python 安装包。

如果使用自己的独立 Python 环境，可从 `NoteApp` 目录安装固定版本：

```bash
python3 -m venv session03/.venv
session03/.venv/bin/python -m pip install -r session03/requirements.txt
session03/.venv/bin/python session03/make_caesar_fixture.py
session03/.venv/bin/python session03/caesar.py session03/results/caesar_ciphertext.txt --output session03/results/caesar_results.json
session03/.venv/bin/python session03/image_modes.py
```

`caesar.py` 也可以读取另一个英文密文文件。短文本的频率排名可能错误；程序会保留全部候选，供人工检查。

图像实验加密原始像素，而非压缩 PNG 文件。显示图只包含等长密文像素；完整密文、nonce、tag 和尺寸说明另存。实验密钥只在内存中用于即时解密校验，完成后丢弃；重新运行会生成新的输出。

## 代码与验证依据

- `../web/comment_crypto.py`：AES-GCM、格式校验和绑定记录 ID 的 associated data。
- `../web/migrate_comments.py`：表锁、事务迁移、解密验证和明文写入约束。
- `generate_key.py`：只创建一次的 32-byte 密钥，文件权限 `0600`。
- `build_variant.py`：兼容命令，只检查集成状态，不再生成第二份应用。
- `homework_changes.diff`：说明当前唯一实现的位置；原始代码证据固定在 `project1/baseline/`。
- `test_homework.py`：7 项密码处理测试及 10 项真实 PostgreSQL 应用测试。
- `results/homework_test_results.json`：测试结果。
- `results/migration_result.json`：迁移 60 条、验证 60 条，明文摘要一致。
- `results/environment_verification.json`：实际 HTTP 检查、数据库行数和第二课数据库摘要检查。
- `project1/baseline_verification.json`：原环境的数据库 TLS 和角色权限检查。

应用路径测试使用临时成绩记录，并在每个测试后删除。正常 HTTP 检查使用预置学生和教师账号，没有执行攻击。

加密保护范围是当前评语列。原课程应用的认证、授权、CSRF、HTML 输出及命令执行问题仍在。旧备份、WAL 和 seed SQL 也可能保留明文。具体限制见英文报告。

## Project 1 提交前

P1 组员：ZIQIAN YU (2023902046)、HAOJIE SONG (2023905496)。

当前逐项验收及完整运行命令见 [P1-C3-C4-REQUIREMENTS.md](../P1-C3-C4-REQUIREMENTS.md)。原始 2026-10-08 结果保留，2026-10-22 集成复验另存，避免覆盖历史测量。
