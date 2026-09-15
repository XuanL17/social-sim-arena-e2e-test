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

## 已通过：Vercel → 持久存储

用户配置仓库限定专用凭据后已重新部署。2026-09-15T23:53:38Z 从实际测试站入口验证：问卷201创建、200原样重放、409同键改文；独立GitHub重读hash与正文一致，原文件未覆盖。Bundle无凭据401，正确凭据200创建与200重放，15接收、2正确late拒绝，独立重读一致。

机器证据：`site/qa-storage-hosted.json`。只使用该私有测试仓库的专用凭据，没有把本机gh广权限token复制到云端。云端上传token也仅用于测试entrant。真实持久化这一缺口已关闭；不代表正式平台启用了旧入口。

## 复现

```
.local/venv/bin/python -m unittest tests.test_qa_storage -v
.local/venv/bin/python tools/qa_storage.py --report .local/qa-storage-real.json
# 专用凭据配置及测试平台重新部署后：
.local/venv/bin/python tools/qa_storage.py --hosted --report .local/qa-storage-hosted.json
```

默认模式借用本机 gh 身份，仅在该进程内存中使用并在退出时恢复环境；不写 token 文件、不打印 token、不配置云端 token。脚本首先核对仓库固定为测试仓库且 private。每次运行生成新幂等键并保留新的合成审计记录；不要拿它当无写入的探针。

3 项离线测试只验证 harness 合同与隔离约束，不能替代上表真实读写证据。尚未证明并发写入竞争、长时间稳定性、人工复核后到正式评分的落盘转换。
