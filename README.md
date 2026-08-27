# pekaboo-task · 武汉楼盘销控每日生产 HTML

这个仓库每天 **08:00（Asia/Shanghai）** 调用五房通生产接口，拉取武汉全部在售楼盘销控数据，生成：

- `site/index.html` — 包含全部楼盘的单页生产仪表盘
- `site/projects/{id}/` — 每个楼盘独立详情页，包含全部字段、原始 JSON、标准销控图、抖音版销控图、历史销控图、可放大查看的户型图与“一房一价”房号明细
- `site/wangqian/` — 昨日网签楼盘与房号变化
- `site/data/sale-data.json` — 楼盘原始生产数据快照
- `site/data/projects/{id}/one-price.json` — 预售证与房号级一房一价快照
- `site/data/projects/{id}/room-types.json` — 户型图、户型、面积与楼栋分布快照
- `site/data/wangqian/{date}.json` — 昨日网签原始快照
- GitHub Pages 生产站点

概览卡片直接展开“全部字段”表格并支持全字段搜索；页面包含最新销控图、已售套数、均价、排序、暗色模式和响应式布局。未来上游新增字段会自动显示，无需修改模板。

## 架构

```text
GitHub Actions schedule (00:00 UTC = 08:00 CST)
  → pytest
  → Python 标准库分页请求 GetLouPanSaleImages
  → 每个楼盘请求 GetLouPanRoomType 获取户型图
  → 每个楼盘请求 GetLouPanPreSaleCertificates
  → 每张预售证分页请求 GetLouPanRoomItems
  → 请求 GetWangQianHouseData 获取昨日网签
  → 生成多页静态 HTML + JSON
  → 安全检查 token 不落盘
  → 提交快照到 main
  → 部署 GitHub Pages
```

项目不依赖第三方运行时包；生产生成器只使用 Python 标准库，避免供应链变化影响每日任务。

## 手动运行

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q

export WFT_TOKEN='你的 wfTToken'
.venv/bin/python -m sale_dashboard \
  --site-output site \
  --page-size 50 \
  --fetch-one-price \
  --room-page-size 500
```

也支持这些可选参数或同名环境变量：

| 参数 | 环境变量 | 默认值 |
|---|---|---|
| `--api-url` | `WFT_API_URL` | 五房通 `GetLouPanSaleImages` |
| `--city-id` | `WFT_CITY_ID` | `4201` |
| `--page-size` | `WFT_PAGE_SIZE` | `50` |
| `--room-page-size` | `WFT_ROOM_PAGE_SIZE` | `500` |
| `--fetch-one-price` | 无 | 关闭；开启后补齐户型图、一房一价与昨日网签 |
| `--max-pages` | `WFT_MAX_PAGES` | `100` |
| `--timeout` | `WFT_REQUEST_TIMEOUT_SECONDS` | `20` |
| `--site-output` | `WFT_SITE_OUTPUT` | `site` |

## GitHub 配置

在仓库 **Settings → Secrets and variables → Actions** 配置：

- `WFT_TOKEN`：五房通登录 token。不要提交到代码。

注意：上游 token 有有效期。过期后每日任务会失败并触发 GitHub 的失败通知，需要重新抓包并更新 secret。

在 **Settings → Pages** 中将 Source 设为 **GitHub Actions**。首次配置后，Actions 会发布到 GitHub Pages。

## 可靠性与安全

- 逐页请求；短页不代表结束，直到上游返回空列表或 `null` 才停止，并按楼盘 ID 去重。
- 使用 `max_pages` 防止上游异常导致无限分页。
- 项目按 `id` 去重，避免分页期间数据移动造成重复。
- HTML 对项目名、预售证名、房号、地址、图片地址等做 HTML 转义；房号表由 DOM API 渲染，避免二次注入。
- 一房一价按“楼盘 → 预售证 → 房号”聚合，保留销售状态与异常状态；单项目失败会写入错误快照，不阻塞其他楼盘。
- 昨日网签接口失败时仍生成当日销控总览，并在网签页显示明确错误。
- Action 生成后会反向扫描整个 `site/` 目录，确保 token 没有落盘。
- 输出文件使用同目录临时文件 + `os.replace` 原子写入。

## 测试

```bash
.venv/bin/pytest -q
```

测试覆盖分页停止条件、去重、上游错误、安全转义、历史图列表选择、全字段动态展示、双销控图、原始 JSON、单页 HTML 生成和 JSON 原子输出。

## 一房一价接口链路

| 步骤 | 接口 | 输入 | 展示用途 |
|---|---|---|---|
| 1 | `GetLouPanSaleImages` | 城市 ID 分页 | 楼盘列表、销控图、总览 KPI |
| 2 | `GetLouPanRoomType` | 楼盘 `id` 作为 `houseid` | 户型图、面积、户型、可售数量、楼栋分布；点击卡片弹出大图 |
| 3 | `GetLouPanPreSaleCertificates` | 楼盘 `id` | 预售证编号、房源/已售/可售/去化摘要 |
| 4 | `GetLouPanRoomItems` | 楼盘 `id` + 预售证 `id` 作为 `evidenceId` | 楼栋、单元、楼层、房号、户型、面积、单价、总价、交付与状态 |
| 5 | `GetWangQianHouseData` | 昨日日期分页 | 昨日网签总量、楼盘变化与房号明细 |

房号状态按上游枚举展示：`saleStatus=1` 为已售，`saleStatus=2` 为可售；`abnormalStatus=1` 追加“异常”标记。
