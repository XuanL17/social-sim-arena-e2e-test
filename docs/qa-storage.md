# 独立持久化验证 · 2026-09-15

## 产品边界

旧问卷仍有 schema、HTTP handler 和路由；`docs/submission-design.md` 描述该路径，但当前测试参赛主流程是 endpoint 注册。`docs/bundle-submission.md` 明确 bundle 上传是可选能力、Season 0 尚未开启。以下验证检查现有入口能力，**不宣称正式平台已开启它们**。

## 已完成：真实存储，不是 mock

创建私有仓库 `assassin808/social-sim-arena-e2e-test-intake`；源码已固定此独立目标，不改变正式资源。运行原 HTTP handler 的本地 HTTP 服务，将合成 QA 记录通过实际 GitHub Contents API 写入该仓库，再以独立 gh 请求重读：

| 场景 | 实测 |
|---|---|
| 问卷首次创建 | HTTP 201 |
| 相同 Idempotency-Key / 相同正文 | HTTP 200，原 received_at 保留 |
| 相同 key / 改答案 | HTTP 409，原文件未覆盖 |
| 独立读取 | submission、receipt_hash 与预期一致 |
| bundle 无上传凭据 | HTTP 401 |
| bundle 有专用临时测试凭据 | HTTP 200，15 接收、2 late 拒绝 |
| bundle 相同正文重放 | HTTP 200，原 receipt 与 results 不变 |
| bundle 独立读取 | 原始 response 与 receipt 完整一致 |

两条 late：`mc-2026-w38-approval`、`aaii-2026-09-17`。不是存储失败，真实运行时已经截止。

问卷记录 ID `ssa_7b7c70214d47baea3ba2d1a4`；hash `b9f015c795f559bd0c522759def7f09c17a29d675aeeb5a0ab115c3e09dd1e8e`。
Bundle hash `1b20d9b11294983c645bc593af07ca9c6345abca7e66e15dbbfd3f4a364ce2f9`。
机器报告位于忽略目录 `.local/qa-storage-real.json`。仓库保留两份合成记录，未写入正式仓库、未创建正式预测文件、无真实联系人信息。

## 未通过：Vercel → 持久存储

真实测试站问卷 POST 仍返回 **503 `submission_storage_unavailable`**。平台当前仅配置 E2E/signing 相关变量，无 intake 存储凭据；当前进程也未发现专用 INTAKE/GitHub App/installation 凭据。没有把本机 gh 全账户长期 token 复制到 Vercel。

完成 hosted 验证所需最小外部输入：对 **仅此私有测试仓库**具有 Contents read/write 权限的短有效期 fine-grained PAT（Metadata read 为 GitHub 默认），配置为测试 Vercel 项目 production 的 `INTAKE_REPO_TOKEN`。不要在对话中粘贴凭据。或提供可签发该仓库 installation token 的现有 GitHub App 接入。

若还需 hosted bundle 验证：测试项目配置随机专用 `SSA_UPLOAD_KEY_E2E_REMOTE_BACKEND`；本机同值用 `SSA_QA_UPLOAD_TOKEN`，仅用于既有测试 entrant。重新部署后由主代理统一运行 `--hosted`。不需创建新服务、购买服务或变更正式环境。

## 复现

```
.local/venv/bin/python -m unittest tests.test_qa_storage -v
.local/venv/bin/python tools/qa_storage.py --report .local/qa-storage-real.json
# 专用凭据配置及测试平台重新部署后：
.local/venv/bin/python tools/qa_storage.py --hosted --report .local/qa-storage-hosted.json
```

默认模式借用本机 gh 身份，仅在该进程内存中使用并在退出时恢复环境；不写 token 文件、不打印 token、不配置云端 token。脚本首先核对仓库固定为测试仓库且 private。每次运行生成新幂等键并保留新的合成审计记录；不要拿它当无写入的探针。

3 项离线测试只验证 harness 合同与隔离约束，不能替代上表真实读写证据。尚未证明云端持久化、并发写入竞争、长时间稳定性、人工复核后到正式评分的落盘转换。
