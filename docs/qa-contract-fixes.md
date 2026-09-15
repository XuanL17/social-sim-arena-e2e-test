# API 契约与发布窗口修复（2026-09-15）

本轮离线验证；未部署、未修改已发布题目、归档或评分定义。

## 已修复

- `answer_schema` 的每个 human/agent 分支携带根 `definitions` 与 JSON Schema 方言声明，可独立解析本地 `$ref`。
- `resolution_source_url` 优先保留题目显式 URL，其次按已发布 `data.tasks` 的 series / series_prefix / target_type 映射获取来源，最后用 `series_provenance → sources.url` 的已存档来源元数据。未知来源保持 null，不猜造链接。当前快照固定到 2026-09-15 的 17 道开放题都有 URL。
- 来源链接可能是发布者入口，不代表特定结算快照的下载链接或当天可达性；没有把这一修复描述为结算证据链已经完备。
- bundle 逐题检查 `batches.published_at(lock_at)`（现有规则：截止前一周）。开放时刻包含，截止时刻不包含；提前答案返回 `not_published`，不产生预测记录。不能用批次最早开放时间提前提交其中后开放的题。
- 三个原 expectedFailure 已改成普通回归测试，避免修复后仍报告“预期失败”。

## Friday 和源失效：已查明的现有行为

依据 `ssa/batches.py`、`ssa/series.py`、`ssa/adapters/civiqs.py`、`ssa/resolve.py` 和 `docs/sources/civiqs.md`：

1. 截止严格使用题目自己的 `lock_at`；Friday 是 Civiqs 的目标观测日，不是所有题统一的提交截止。
2. Civiqs 注册系列声明 `weekday=4`，按日归档并读取仪表盘显示值；不能把底层模型的 Thursday 日期改写为预测 Friday 原始调查结果。
3. 实现里的缺档回补会找目标日及之后最早可用快照，再读取该快照相应值；这与“Friday 当时已显示值”的自然语言存在潜在差异。它并没有证明周五固定时刻的不可变 first print。
4. 上游失败时可服务现有归档并标记运行；无可读归档会拒绝生成空系列。resolver 对未到发布时间、缺少历史或没有新增观测拒绝结算，已有结算不覆盖。不能把“有旧归档可用”当作“当前目标日已经真实结算”。

## 尚需产品确定，未擅自补写为现有规则

- Friday 按哪个时区、几点的快照；同日多次抓取/修订取首次还是最后一次？
- 目标日抓取失败时允许延迟多久，后补快照能否代表原目标日？
- 超过宽限期后延期还是取消，取消题如何退出排行榜分母？
- 原始结算遇到来源更正，维持首次结算还是发布版本化重算？

这些选择会改变已发布题目的答案与得分，不能由测试工程擅自追溯改变。本轮未创建自定义未来规则版本，也未声称统一规则已经上线。确认后应仅先在隔离未来测试题中带版本发布，再测试断源、晚到、同日修订和取消路径。

## 回归结果

```
.local/venv/bin/python -m unittest tests.test_qa_contract_fixes tests.test_qa_api_scoring tests.test_bundle_api -q
# 34 passed
.local/venv/bin/python -m tests.test_bundle
# 28 passed
```

共 62 项通过，包括独立 schema 所有本地引用、来源优先级与未知来源、逐题发布前一秒/恰好发布、恰好截止、既有身份/重复/撤销/迟到拒绝规则。没有进行真实未来结果或上游网络可达性验证。
