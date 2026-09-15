# 端到端验证报告 · 2026-09-15

## 结论

**局部通过，尚不能认定整个赛季自动流程通过。** 测试使用独立 Vercel 后端、现有 OpenRouter key 和明确的免费模型。真实题目能够拉取并回答；免费模型可用性、源数据更新和旧提交入口仍有风险。未来题目尚无真实结果，不生成虚构成绩。

## 四模型 × 三种真实题型

测试：Civiqs angry share、Civiqs 16-cell net approval、Wikipedia 10-article ranking。全部题目与上游公开题库原文一致。请求从本地验证器发到真实 Vercel 后端；此前的三题合成测试另已验证 Vercel 平台→Vercel 后端链路。本轮的接收/截止判断在本地调用生产规则，没有写入正式参赛记录。

| 免费模型 | 标量 | 16 维 profile | 排名 |
|---|---|---|---|
| liquid/lfm-2.5-2.6b:free | 通过 | 通过 | 无效排名被拒绝 |
| nex-agi/nex-n2.5-mini:free | 超时 | 通过 | 后端失败 |
| google/gemma-4-31b-it:free | 失败 | 失败 | 失败 |
| dots-studio/dots-3-note-preview:free | 通过 | 通过 | 通过 |

6/12 项通过。每项通过都包含真实生成、生产解析器验证、相同请求缓存重放、当前时间接收与截止后拒绝。6 条生成均另外查询 OpenRouter generation API，total_cost = 0。失败不会切换付费模型。Gemma 的结果只说明当前严格 schema 配置不兼容/不可用，不能推断该模型完全不可用。单次测试不是可靠性统计。

机器证据：`site/validation-live-free.json`，保留失败而不覆盖成全绿。

## 题目拉取与数据来源

- 上游公开 `season0.json`：HTTP 200，151 道题。
- 测试平台 questionnaire：修复前 99 道，99 道题的文字均与上游一致。
- 其中 82 道尚未到 published_at；UI 实际只显示 17 道开放题。已修复接口发布窗口判断，避免机器参赛者提前收到未发布题。
- GitHub Raw 上的本周题包：HTTP 200，17 道题；网站 `/questions/bundles/...` 未提供该路由，返回 404。使用官方已存在的 Raw 文件链接可下载。
- Civiqs 官方页面 HTTP 200，生产适配器解析 603 个观测点，最新 2026-09-14，净支持率 -26.5；Wikimedia 官方 daily top API HTTP 200，生产解析器保留 999 个条目。
- **注意**：测试站快照仍标记 Civiqs stale/failing（旧归档），与当下页面可解析不同。当前源可达不能证明自动归档及未来结算已恢复。测试环境刷新本来就关闭。

## 评分验证

- 按原始 forecasts 文件（包括 crowd 的 quantiles，而非仅看展示的 mean/sd）重算 **1,911 条已发布 CRPS**，与公开四位小数分数一致。
- profile energy、ranking/RBO、真实历史示例、bundle 接收、截止、resolver、适配器时间规则等测试已执行。
- 旧测试有三处失败：导航源码断言过时、404 两份文件不一致、测试 fork 维护者/禁用工作流与原仓库假设不同。已修复对应问题并复测。
- 未来真实题的结果只能在实际结果发布后结算。本轮真实题均标记 pending，不把合成分数或回测分数冒充未来成绩。

## 浏览器交互

实际操作了参赛页 Run test：浏览器 Ed25519 签名、跨域 POST、真实 LLM 响应，HTTP 200，约 7.45 秒。填写注册信息后 JSON 与 GitHub 链接指向测试 fork；改为 HTTP 地址后阻止测试并禁用提交。未创建重复注册 PR。

实际操作题目页 Open 筛选、Civiqs 搜索；题卡显示正确题型、16-cell 数量、截止时间和来源链接。页面渲染测试覆盖榜单、日历、模型筛选及详情数据。未声称覆盖所有设备、无障碍或长时间负载。

**额外发现的评分展示错误**：Michigan August prelim 的 Crowd 权威 CRPS 为 5.523，但详情页把分位数预测当正态分布重算，实际浏览器显示 6.70。已修改详情页优先采用发布的权威 CRPS。后端 1,911 条复算一致仍成立。

**尚未修复的详情页问题**：真实 16-cell profile 详情仍使用标量模板，显示 CRPS 列与“no number forecasts”，并未正确展示 energy 成绩。这是界面契约缺口，不能用榜单渲染测试通过掩盖。

浏览器原来仅测标量却说“整个 API 兼容”，已改为明确只通过标量，profile/ranking 需另测。404 页面已同步测试环境标识和链接。

## 题目是否合理

1. **标量态度题**：人群、指标、单位、日期清晰，适合预测“该来源会发布什么”。不应把它解释为无误差的全体民众真实态度。Civiqs 是建模调查结果，而非人口普查。
2. **16-cell profile**：同时预测人口分组结构有意义；这些分组存在重叠，不能把 16 个数当作互斥群体相加。单位是 approve − disapprove 的净百分点，不是 0–100% 支持率。历史能量分数验证通过，但不能据此证明模型预测能力高。
3. **Wikipedia 排名**：周区间、排除命名空间、并列规则均已说明。实际目标是“每天 top-1000 的截断列表汇总排名”，不严格等于所有文章完整周浏览量排名。题目正文第一句话过于宽泛，建议直接将截断统计定义写进标题。RBO 衡量点排名质量，不是概率校准。
4. **可复核性缺口**：修复前 99 道 manifest 的 resolution_source_url 全为空，UI 却有源链接。机器 API 应明确给出 source URL、observed_at、抓取时间、修订/延期/取消规则；尤其“Friday dashboard”必须固定时区和读取时间，避免同一天多次更新造成争议。
5. **问卷 schema**：返回的 human answer_schema 内含 `#/definitions/round_id` 引用，片段没有携带根 definitions；不能直接当独立 schema 使用。旧问卷存储目前未配置，不等于当前 endpoint 注册路径已持久接收。

## 尚未通过的部分

- 问卷/上传旧入口的真实持久写入（未配置独立存储）。
- 定时拉取→新归档→真实未来结果结算→排行榜自动发布的完整赛季流程（测试 cron 关闭，结果尚未发生）。
- 多免费模型在重复/并发/限流下的长期稳定性。
- API 源链接与独立 schema 的完善，以及 Friday 截点和源失效规则的统一。

## 复现

`.local/venv/bin/python tools/validate_live_free.py` 拉取题目并测试四模型；会消耗免费调用额度，绝不调用付费模型。

`tools/audit_question_quality.py` 审计 `.local/validation-*.json` 下载快照并重算本地原始预测的分数。`site/validation-quality.json` 为本次修复前审计证据。

来源：[Civiqs 方法](https://civiqs.com/content/methodology)、[Wikimedia top-1000 API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/examples/project-metrics.html)。
