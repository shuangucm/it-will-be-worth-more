# It Will Be Worth More · 剁手前想一想

花钱买非必需品之前（比如一块 $350 的手表），看看这笔钱如果拿去买 **QQQ** 或 **VOO**，
按过去 6 个月的平均涨幅估算，一年后会值多少钱。

## 架构 — 全部跑在 GitHub 上

| 部分 | 位置 | 说明 |
| --- | --- | --- |
| 前端 | `docs/index.html` | 纯静态页面，通过 GitHub Pages 发布；手机上可“添加到主屏幕”当 app 用 |
| 数据 | `docs/data/prices.json` | QQQ / VOO 近 6 个月涨幅、近 5 年年化收益及走势 |
| 后端 | `.github/workflows/update-prices.yml` + `scripts/update_prices.py` | 每个交易日收盘后自动拉取价格、计算 6 个月涨幅、提交回仓库 |

剁手记录保存在浏览器本地（localStorage），不会上传。

## 计算方法

用 6 个月前的价格和今天的价格算出涨幅，再按复利延续一年（价格已包含分红）：

```
一年后价值 = 价格 × (1 + 6个月涨幅)²
```

只看近 6 个月外推波动很大：半年涨 20% 年化就是 44%，赶上回调甚至会是负数。
所以每个结果下面还有一行 **“按近 5 年平均”**（5 年年化收益）作为更稳的参照。
页面里也可以手动填写年化收益覆盖自动值。

输入物品和价格后，点 **“先不买了”** 或 **“还是买了”**：app 会累计你忍住的钱，以及这些钱一年后的预估价值。

> 这个 app 是用来给消费冲动降温的，不是用来预测收益的。不构成投资建议。

## 启用步骤

1. **Settings → Pages**：Source 选 *Deploy from a branch*，分支选 `main`，目录选 `/docs`。
2. **Settings → Actions → General → Workflow permissions**：选 *Read and write permissions*（让 Action 能提交价格数据）。
3. **Actions → Update ETF prices → Run workflow**：手动跑一次，生成第一份 `prices.json`。
4. 打开 https://shuangucm.github.io/it-will-be-worth-more/ ，在手机浏览器里“添加到主屏幕”。

## 本地运行

```bash
python3 scripts/update_prices.py          # 拉取价格，写入 docs/data/prices.json
python3 -m http.server -d docs 8000       # 打开 http://localhost:8000
```
