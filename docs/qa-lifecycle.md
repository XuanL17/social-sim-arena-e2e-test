# 隔离测试赛季生命周期

## 实现与权限

`tools/qa_lifecycle.py` 只读取两道真实 Wikipedia weekly-top10 题，写 `qa-lifecycle/`。测试参赛者固定为 `qa-persistence-public-source`，算法是复制截止前已完成周的真实排名；不调用任何 LLM 或正式 refresh/harness。它和免费 LLM 参赛测试是不同的测试层，不能称作 LLM 自动赛季已通过。

- `sources/YYYY-MM-DD.json`：Wikimedia 官方 daily top API 原文、来源 URL、首次抓取时间、SHA-256；重复运行复用并校验原文摘要，不覆盖首次归档。
- `forecasts/`：预测排名、真实 `filed_at`、输入周和输入摘要；首次写入后保留，不把迟交回填成及时提交。
- `resolutions/`：真实七日结果与来源摘要，全部七天成功才结算。
- `report.json` / `index.html`：独立测试榜，明确历史回放和实时测试、pending/blocked/missed_deadline，不合并正式排行榜。

公开源 HTTP 429 有最多三次尝试、每次至少1.2秒节流、有限 Retry-After 等待。持续失败输出 blocked 和非零退出码；已取到的归档不丢失。执行器在 **2026-10-01 00:00 UTC** 后停止拉取与改写。

## 已执行的真实验证

2026-09-15 使用真实官方 API 取得 **21 个日归档**。第一次因429输出 blocked，加入节流后的续跑复用既有归档并成功。

| 真实题 | 模式 | 当前结果 |
|---|---|---|
| wiki-top10-2026-09-06 | historical_replay | resolved，生产 RBO loss **0.9466326921358921** |
| wiki-top10-2026-09-27 | live_test | 预测已在9/18 14:00 UTC截止前冻结，真实结果 **pending** |

历史回放预测在本次运行时生成，用赛前历史周构造，但不是2026年8月真实及时提交。未来题的截止是 **9/18 14:00 UTC**，预定发布是 **9/29 14:00 UTC**。目标周已完成的天会逐日归档，但发布时刻之前不生成 outcome 或 score；缺日、源错误也不生成成绩。真实未来结算只能等真实结果到来。

`python -m unittest tests.test_qa_lifecycle` 验证 pending→resolved、重复执行不重新抓取/不覆盖预测、迟交拒绝、错误日期/不完整周不结算、摘要篡改拒绝。测试夹具中的数据只用于单元测试，不进入公开真实报告。

## 工作流与发布边界

`.github/workflows/qa-lifecycle.yml` 配置了 `workflow_dispatch` 与每6小时执行；推送至测试仓库后生效，2026-10-01 UTC停止源处理。workflow 只允许测试 fork，权限是 `contents:read`、`actions:read`。它通过内置短期 token 下载上一轮 `qa-lifecycle-state` artifact 恢复持久归档和预测，再运行、上传30天保留的完整 artifact。

它**不自动 git push，不修改主分支，不部署平台**。本轮主代理可审核后一次性发布 `qa-lifecycle/`；未来自动公开发布需要另行具体授权和部署方案。Artifact 内含静态榜单，满足每次执行产物检查，但不等于未来公网榜单已自动更新。workflow 没有 push 触发，避免自触发循环。

## 复现

```sh
.local/venv/bin/python -m unittest tests.test_qa_lifecycle
.local/venv/bin/python tools/qa_lifecycle.py
```

只从真实墙钟判断截止/发布，命令行没有伪造 now 的入口。`--output` 可指定另一个隔离目录；不要指向正式数据目录。
