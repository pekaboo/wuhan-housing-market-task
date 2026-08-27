# pekaboo-task · 武汉楼盘销控静态总览 + 实时 FastAPI

这个仓库包含两条链路：

1. GitHub Actions 每天 **08:00（Asia/Shanghai）** 生成轻量静态总览，发布到 GitHub Pages；
2. FastAPI 实时服务按楼盘点击获取户型图与一房一价，并使用 SQLite 缓存支持预热中断后继续。

静态输出：

- `site/index.html` — 包含全部楼盘的单页仪表盘；
- `site/projects/{id}/` — 基础楼盘详情、全部字段、标准/抖音/历史销控图；
- `site/data/sale-data.json` — 楼盘列表生产快照。

实时输出：

- `/` — 实时全部楼盘总览；
- `/projects/{id}/` — 实时户型图与一房一价详情；
- `/api/*` — JSON 接口与预热/恢复状态。

## 架构

```text
GitHub Actions schedule (00:00 UTC = 08:00 CST)
  → pytest
  → 分页请求 GetLouPanSaleImages（短页不终止，null/空列表终止，按 ID 去重）
  → 生成全部楼盘单页总览与基础详情
  → token 扫描、提交快照、部署 GitHub Pages

FastAPI
  → / 与 /projects/{id}/ 复用同一套渲染层
  → 点击楼盘时请求 GetLouPanRoomType / GetLouPanPreSaleCertificates / GetLouPanRoomItems
  → SQLite 持久缓存项目、预售证、房号与户型图响应
  → POST /api/warm 后台顺序预热；重启后跳过已完成项目继续
```

静态生成器只使用 Python 标准库；FastAPI 运行时依赖见 `requirements.txt`。

## 手动运行

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q

export WFT_TOKEN='你的 wfTToken'
.venv/bin/python -m sale_dashboard \
  --site-output site \
  --page-size 50 \
  --room-page-size 500
```

## 实时 FastAPI 运行

```bash
.venv/bin/pip install -r requirements.txt
export WFT_TOKEN='你的 wfTToken'
.venv/bin/uvicorn sale_dashboard.api:app --host 127.0.0.1 --port 8000 --reload
```

打开 `http://127.0.0.1:8000/`：

- `/` — 实时全部楼盘单页总览；
- `/projects/{id}/` — 点击楼盘后实时获取户型图与一房一价；
- `/api/projects` — 楼盘列表 JSON，支持 `?refresh=true` 强制刷新；
- `/api/projects/{id}/room-types` — 户型图 JSON，支持 `?refresh=true`；
- `/api/projects/{id}/one-price` — 一房一价 JSON，支持 `?refresh=true`；
- `POST /api/warm` — 后台顺序预热全部楼盘，立即返回；
- `GET /api/warm/status` — 查看预热进度；
- `POST /api/warm/stop` — 停止预热。

默认 SQLite 缓存位于 `.wft-cache/responses.sqlite3`，缓存 TTL 为 21600 秒（6 小时）。可用 `WFT_CACHE_PATH` 与 `WFT_CACHE_TTL_SECONDS` 调整。预热会把每个完成的楼盘快照和预售证/房号原始响应写入缓存；进程重启后再次 `POST /api/warm` 会跳过已完成项目，从中断附近继续，而不是从零开始。

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

上游 token 有有效期。过期后每日静态任务会失败；FastAPI 健康检查仍可用，但数据接口会返回 503/502，需要重新抓包并更新环境变量。

在 **Settings → Pages** 中将 Source 设为 **GitHub Actions**。首次配置后，Actions 会发布静态总览。

## 可靠性与安全

- 逐页请求；短页不代表结束，直到上游返回空列表或 `null` 才停止，并按楼盘 ID 去重。
- 使用 `max_pages` 防止上游异常导致无限分页。
- 项目按 `id` 去重，避免分页期间数据移动造成重复。
- HTML 对项目名、预售证名、房号、地址、图片地址等做 HTML 转义；房号表由 DOM API 渲染，避免二次注入。
- 一房一价按“楼盘 → 预售证 → 房号”聚合，保留销售状态与异常状态；单项目失败会写入错误快照，不阻塞其他楼盘。
- 昨日网签接口失败时仍生成当日销控总览，并在网签页显示明确错误。
- Action 只生成楼盘总览，不再批量拉取全量一房一价；实时详情由 FastAPI 按点击获取并缓存。
- Action 生成后会反向扫描整个 `site/` 目录，确保 token 没有落盘。
- 输出文件使用同目录临时文件 + `os.replace` 原子写入。

## 测试

```bash
.venv/bin/pytest -q
```

测试覆盖分页停止条件、去重、进度日志、持久缓存与断点恢复、FastAPI JSON/HTML 路由、安全转义、历史图列表选择、全字段动态展示、双销控图、原始 JSON 和单页 HTML 生成。

## 一房一价接口链路

| 步骤 | 接口 | 输入 | 展示用途 |
|---|---|---|---|
| 1 | `GetLouPanSaleImages` | 城市 ID 分页 | 楼盘列表、销控图、总览 KPI |
| 2 | `GetLouPanRoomType` | 楼盘 `id` 作为 `houseid` | 户型图、面积、户型、可售数量、楼栋分布；点击卡片弹出大图 |
| 3 | `GetLouPanPreSaleCertificates` | 楼盘 `id` | 预售证编号、房源/已售/可售/去化摘要 |
| 4 | `GetLouPanRoomItems` | 楼盘 `id` + 预售证 `id` 作为 `evidenceId` | 楼栋、单元、楼层、房号、户型、面积、单价、总价、交付与状态 |
| 5 | `GetWangQianHouseData` | 昨日日期分页 | 昨日网签总量、楼盘变化与房号明细 |

房号状态按上游枚举展示：`saleStatus=1` 为已售，`saleStatus=2` 为可售；`abnormalStatus=1` 追加“异常”标记。
