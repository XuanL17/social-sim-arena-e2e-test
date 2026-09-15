# 独立测试工程审计：API、题目与评分

日期：2026-09-15。只读测试站与本地生产规则；未访问密钥、未提交线上预测、未调用 LLM、未部署。仓库/父目录检索未发现 AGENTS.md。

## 结论

已修复的 manifest 发布窗口仍正确；线上可拉取 17 道题。评分及 bundle 已有 71 项测试通过；新增 6 项为 **3 通过、3 expectedFailure（未修复缺陷）**，不能写成全部通过。

## P2：可复现问题

1. **human answer_schema 不能独立使用（旧问题仍在）**。`ssa/questionnaire_api.py` 的 `_schema_branches` 只取分支，丢掉根 definitions。对 manifest 的连续题 human schema 验证合法 `{round_id,target_type,response:{value:0}}`，抛出 `PointerToNowhere: /definitions/round_id`。自动参赛/表单生成客户端无法直接消费返回的 schema。回归：`test_human_manifest_schema_is_standalone`。本地复现；线上相同 schema 结构，未做线上写入。

2. **bundle 在发布前接受预测（新发现的生产规则缺口）**。使用仓库 sandbox bundle，在 `published_at=2027-12-29T14:00:00Z` 的前 1 秒调用 `bundle.normalise`，返回 accepted=3 并生成 3 条 records。接收路径只检查截止，未检查开始时刻。与 manifest 的未发布不可见规则不一致；已知未来 batch 文件的上传客户端可以提前通过 normalise。回归：`test_bundle_rejects_before_publication`。这是本地真实函数验证，**未证明线上已配置上传存储或已经发生提前入库**。若产品明确允许提前提交，应明确文档而不是把开放窗口当作全链路约束。

3. **17/17 线上题 resolution_source_url 为 null（旧问题仍在）**。`GET /api/v1/questionnaire` HTTP 200，generated_at=`2026-09-15T23:20:30Z`，17 道题全部缺少机器可读来源 URL。resolution_rule 的文本仍可阅读，但自动获取权威结果需要另查代码/站点映射。回归：`test_manifest_supplies_machine_readable_resolution_sources`。不要误报为“题目没有任何来源信息”。

## 题意与可结算性复核

- 当前 Civiqs angry 题：人群、百分比指标明确，截止 `2026-09-16T14:00:00Z`；结算文字仍是 `dashboard Friday value, from the daily archive`。未声明 Friday 的时区、同日多次修订取哪个快照。Profile 16-cell 同样依赖 Friday archive；这是争议处理规则缺口，不是证明结果无法抓取。
- 当前 Wikipedia 题 `wiki-top10-2026-09-27` 已在问题正文明确“七个 daily top-1000 汇总”、命名空间排除；resolution_rule 明确缺席日贡献零及并列按标题升序。**旧报告关于截断统计定义不明显的意见应降低优先级，当前正文和规则已足够具体**。这是截断榜单的周汇总，不应解释为全量浏览量排名。
- 真实未来结果仍未发生；本轮没有把离线 CRPS/energy 正确性当作未来自动结算成功。未重新抓取 Civiqs/Wikimedia 上游或验证归档 cron。

## 通过项及复现

```
.local/venv/bin/python -m unittest tests.test_bundle_api -q
.local/venv/bin/python -m tests.test_bundle
.local/venv/bin/python -m tests.test_profile_scoring
.local/venv/bin/python -m tests.test_scoring
.local/venv/bin/python -m unittest tests.test_qa_api_scoring -v
```

- 已有：bundle API 25、bundle 28、profile scoring 14、基础 scoring 4，合计 71 项通过。
- 新增通过：发布前一秒/恰好发布/截止前一秒/恰好截止；bundle 恰好截止拒绝；CRPS 平移/尺度不变性及非负性。
- 已有通过覆盖：未知/重复 round、错误题型、缺失 profile cell、篮子外排名、零方差、身份/撤销、迟到不覆盖、缓存式重复上传、存储不可用返回失败；profile 能量分数确定性及退化边界。
- 测试没有连接真实提交存储；API 存储测试用隔离临时目录与 mock。未测并发/负载、未来 cron、全部上游来源、浏览器交互或付费/免费模型（其他测试工程分工）。

在线只读复现：从 [公开问卷 API](https://social-sim-arena-e2e-test.vercel.app/api/v1/questionnaire) 检查 questions 长度、resolution_source_url 与 answer_schema。线上数量随真实时间变化；本报告的 17 是上述响应时刻快照。
