# 隔离测试来源政策 qa-friday-utc-v1

仅用于新建 `qa-*` 合成测试题。**不是正式赛季规则，不修改既有题、resolver、归档或真实排行榜。** 实现为 `tools/qa_source_policy.py` 的纯函数；调用方提供快照和时钟，可离线重复验证。

## 明确测试约定

- 目标日是 UTC Friday，截点 23:59:59Z。
- 观测必须发生在目标 Friday UTC 当天且不晚于截点，不能拿前一天旧缓存顶替。
- 抓取时间不得早于观测时间、不得晚于调用时钟；最迟允许截点后 24 小时归档。允许 Friday 当天已归档的数据，避免误拒正常提前抓取。
- 宽限期到期前保持 pending，不提前冻结可能仍有更新的目标日值。期满选合法快照中最新 observed_at，其次最新 fetched_at；完全同刻冲突以规范 JSON 排序提供确定性测试选择。这只是 QA 确定性约定，不是来源权威性保证。
- 宽限期到期后无合法数据为 cancelled；cancelled/pending 均不计评分分母。
- 完成后不静默覆盖/复活。后续不同合法候选记录 `revision_requires_review`；超出归档窗口的候选记录 `late_archive_ignored`。重复事件去重。
- 每个决定带 `policy_version`、`decision_version` 与选中快照 SHA256。当前只产生 decision_version=1；人工批准版本2重算不在此工具范围。

## 边界与限制

工具信任传入的观测/抓取时钟，不证明远端时钟或抓取真实性。输出事件是返回值，**未自动持久化**；生命周期调用方需另存。未声明真实未来周五已经发生，也未将测试约定追溯应用于公开 Season 0。

正式采用前仍需决定时区、固定观测时间、冲突证据优先级、宽限期、取消对正式榜单的处理，以及修订审批与版本重算流程。

验证：`.local/venv/bin/python -m unittest tests.test_qa_source_policy -q`，8项通过，覆盖时区边界、缺源、旧缓存、截止宽限边界、未来/倒置时钟、修改冻结、取消不复活及评分分母、限定QA与Friday。
