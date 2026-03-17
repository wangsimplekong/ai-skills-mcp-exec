# 漳河水利 MCP Skills 汇总

## 📦 已创建的 Skills

| Skill 名称 | 目录 | 功能 | 问题数 |
|-----------|------|------|--------|
| **zh-water-conditions** | `~/.openclaw/skills/zh-water-conditions` | 实时水雨情查询 | ~15 |
| **zh-water-resources** | `~/.openclaw/skills/zh-water-resources` | 水资源数据查询 | ~12 |
| **zh-hydro-history** | `~/.openclaw/skills/zh-hydro-history` | 历史水文数据查询 | ~10 |
| **zh-flood-control** | `~/.openclaw/skills/zh-flood-control` | 防汛调度查询 | ~8 |
| **zh-warning-plan** | `~/.openclaw/skills/zh-warning-plan` | 预报预警预案 | ~5 |
| **zh-irrigation** | `~/.openclaw/skills/zh-irrigation` | 灌溉调度查询 | ~2 |
| **zh-device-control** | `~/.openclaw/skills/zh-device-control` | 设备运行控制 | ~2 |
| **zh-weather** | `~/.openclaw/skills/zh-weather` | 天气预报查询 | ~2 |

---

## 🔧 MCP 服务器配置

已配置 3 个 MCP 服务器：

| 服务器名称 | 地址 | 工具数 | 主要功能 |
|-----------|------|--------|----------|
| Evangelion-mcp-zh-flood | 192.168.100.180:18011/sse | 16 | 洪水预报、水雨情、预警、调度 |
| Evangelion-mcp-zh-schedule | 192.168.100.180:18012/sse | 6 | 灌溉调度、供需预报 |
| Evangelion-mcp-zh-search-info | 192.168.100.180:18010/sse | 32 | 综合信息查询、历史数据 |

---

## 📋 问题分类映射

### 1️⃣ 实时水雨情 (zh-water-conditions)

| 标准问题 | MCP 工具 |
|---------|----------|
| 漳河水库当前水位是多少？ | getWaterAndRainData |
| 帮我查询漳河水库当前水位 | getWaterAndRainData |
| 帮我查询当前的库容 | getWaterAndRainData |
| 漳河水库当前库容是多少？ | getWaterAndRainData |
| 漳河水库入库流量是多少？ | getWaterAndRainData |
| 漳河水库出库流量是多少？ | getWaterAndRainData |
| 漳河水库未来 24 小时降雨量是多少？ | getWaterAndRainData |
| 明日灌区平均面雨量是多少？ | getRainForecastData |
| 明日流域平均面雨量是多少？ | getRainForecastData |
| 明日灌区和流域的平均面雨量是多少？ | getRainForecastData |

### 2️⃣ 水资源数据 (zh-water-resources)

| 标准问题 | MCP 工具 |
|---------|----------|
| 漳河当前发电供水流量是多少？ | getWaterSupplyFlow |
| 漳河当前工业供水流量是多少？ | getWaterSupplyFlow |
| 漳河当前农业供水流量是多少？ | getWaterSupplyFlow |
| 漳河当前生活供水流量是多少？ | getWaterSupplyFlow |
| 漳河灌区总库容/蓄水能力是多少 | getWrmStorageRes |
| 漳河灌区有效水量是多少？ | getWrmStorageRes |
| 漳河计划供水总量是多少？ | querySupplyDemandContrast |
| 漳河计划还需供水总量是多少？ | querySupplyDemandContrast |
| 帮我查询漳河灌区近 3 天的农业供需对比情况 | querySupplyDemandContrast |
| 帮我查询一干渠本月的供水总量是多少 | queryIrrWaterSupply |
| 漳河灌区今年降雨量多少？ | queryRainSituation |
| 今年农业灌溉水方是多少？ | selectWarehouseAndWaterTotalTable |

### 3️⃣ 历史数据查询 (zh-hydro-history)

| 标准问题 | MCP 工具 |
|---------|----------|
| 帮我查询观音寺今年的最高水位是多少 | getHydroData |
| 观音寺历史最高水位及发生时间 | getHydroData |
| 观音寺历史最大流量及发生时间 | getHydroData |
| 观音寺历史最大雨强及发生时间 | getHydroData |
| 帮我查询打鼓台过去的流量数据 | getHydroData |
| 帮我查询马河今年的最大流量 | getHydroData |
| 当前 1 小时最大降雨量在哪？ | getHydroData |
| 帮我查询车桥水库最近三个月的最大雨强 | getHydroData |
| 帮我查询漳河水库过去一个月的工业生活出库水方 | selectWarehouseAndWaterTotalTable |
| 帮我查询漳河灌区本月的总供水量是多少 | getWaterUse |
| 帮我查询各维修单位 2025 年度的维修养护次数 | getRepair |
| 帮我查询漳河水库 2025 年份的月度水量平衡数据 | getWaterBalanceAnalysisMarkdown |

### 4️⃣ 防汛调度 (zh-flood-control)

| 标准问题 | MCP 工具 |
|---------|----------|
| 漳河水库当前可抗雨量是多少？ | getResistanceData |
| 帮我查询漳河水库当前的可抗雨量 | getResistanceData |
| 帮我查询漳河水库的防洪高水位是多少 | selectReservoirBasicInfo |
| 帮我查询车桥水库的汛限水位是多少 | selectReservoirBasicInfo |
| 帮我查询漳河水库设计洪水位的可抗雨量是多少 | getResistanceData |
| 假设当前的目标水位是 200 米，帮我计算可抗雨量 | calcResistanceData |
| 假设观音寺水位是 200，鸡公尖水位也是 200，计算漳河水库库容 | calculateReservoirCapacity |

### 5️⃣ 预报/预警/预演/预案 (zh-warning-plan)

| 标准问题 | MCP 工具 |
|---------|----------|
| 帮我查询最新的防洪预演洪水调度计算数据 | calculateHydroDispatch |
| 帮我查询防洪预案的典型预案数据 | getTypicalPlanData |
| 帮我查询最新的洪水预报方案对比数据 | getLatestSchemeCompareData |
| 帮我查询漳河 2025 年 10 月到 2025 年 12 月监测预警数据 | getWarningData |

### 6️⃣ 水资源调度 (zh-irrigation)

| 标准问题 | MCP 工具 |
|---------|----------|
| 未来 10 天漳河水库预测作物需水量是多少 | queryDefaultCalculationResult |
| 帮我查询水库按 190 万亩灌溉配置的抗旱天数是多少 | getDroughtResistanceDays |

### 7️⃣ 设备运行控制 (zh-device-control)

| 标准问题 | MCP 工具 |
|---------|----------|
| 查询崔家沟非常溢洪道坝内的摄像头实时画面 | hkCamera |
| 请根据 1 号闸门调度令调整闸门开度 | navigateToSchedulingPage |

### 8️⃣ 天气预报 (zh-weather)

| 标准问题 | MCP 工具 |
|---------|----------|
| 帮我查询荆门的天气情况 | getCityForecast |

---

## 🔑 Token 配置

当前使用的 Token:
```
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NjI5MDk2MzgsInVzZXJuYW1lIjoid2FuZ2tvbmcifQ.voVc7NzdQ5kStsxgMHpxisBHBC1o5evzYxK89mGsD5o
```

**注意**: Token 有过期时间，请定期检查更新。

---

## 🚀 使用方式

### 自动触发
当用户提问匹配到上述标准问题时，系统会自动：
1. 识别问题类型
2. 调用对应的 MCP 工具
3. 获取实时数据
4. 分析并返回结果

### 手动调用
```bash
# 示例：查询实时水雨情
mcporter call Evangelion-mcp-zh-flood.getWaterAndRainData

# 示例：查询供水流量
mcporter call Evangelion-mcp-zh-search-info.getWaterSupplyFlow userToken=<token>
```

---

## 📝 扩展说明

如需添加新的标准问题：
1. 确定问题所属分类
2. 找到对应的 MCP 工具
3. 更新对应 skill 的 SKILL.md
4. 在本文件中添加映射记录

---

_最后更新：2026-03-12_
