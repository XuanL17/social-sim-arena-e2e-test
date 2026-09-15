# QA 最新状态 · 2026-09-15

## 已完成

- Vercel问卷及上传入口 → 独立私有仓库真实持久写入、重放、冲突和独立重读通过。
- 发布前答案拒绝、可独立使用的答案schema、17道开放题来源URL已修复并部署；线上复核通过。
- 49项契约/存储/生命周期/来源政策组合测试，加28项bundle回归通过；6项免费接口离线故障注入通过。
- 真实21天Wikimedia归档、一次已发生真实周的历史回放已结算；未来周预测已冻结，等待9月29日真实结果。
- 生命周期Actions两次运行通过，第二次恢复artifact且两份冻结预测未变化。
- 两个只读QA工作流每6小时运行，源处理/模型调用限期至9月30日。报告归档，不自动写main或更新公网网页。

## 仍然失败/等待

- 免费模型稳定性首次Actions运行失败：Liquid/Dots200及缓存重放通过，Nex/Gemma502。不能称长期通过。
- 并发冷缓存：Liquid和Dots同一请求各产生两条不同生成/不同sd，严格并发幂等失败。
- Crowd单条预测页仍显示6.70而题目页5.52；多维/排名题状态与成绩模板仍不一致（见qa-ui.md）。
- Friday/断源政策只在独立新QA题纯函数中完成8项测试，不是正式赛季规则或已接入真实Civiqs生产结算。
- 未来真实结算尚未发生；持续报告自动更新公网网页尚未授权。目前网页是本轮发布快照。

## 云端执行证据

- 生命周期首轮：https://github.com/assassin808/social-sim-arena-e2e-test/actions/runs/35037356150
- 生命周期恢复验证：https://github.com/assassin808/social-sim-arena-e2e-test/actions/runs/35037416735
- 免费稳定性失败记录：https://github.com/assassin808/social-sim-arena-e2e-test/actions/runs/35037359038
- `site/qa-storage-hosted.json` / `qa-stability/latest.json` / `qa-lifecycle/report.json`

原始5个问题中，3个API问题已修复；2个P1界面问题尚未修复。本页不会把过去测试报告中的expectedFailure当作当前状态。
