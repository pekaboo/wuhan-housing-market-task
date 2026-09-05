# wuhan-housing-market-task · 武汉楼盘销控静态总览 + 实时 FastAPI

这个仓库包含两条链路：

1. GitHub Actions 每天 **08:00（Asia/Shanghai）** 生成静态总览，并分批补齐户型图与一房一价，发布到 GitHub Pages；
2. FastAPI 实时服务按楼盘点击获取户型图与一房一价，并使用 SQLite 缓存支持预热中断后继续；静态链路会复用已提交 JSON 继续轮转抓取。

数据产物（`site/` 快照）默认提交到独立数据仓 [`pekaboo/wuhan-housing-market-dashboard`](https://github.com/pekaboo/wuhan-housing-market-dashboard)，本仓库只保留代码，由 [`config/artifact-target.txt`](config/artifact-target.txt) 开关控制（见 [产物输出仓库开关](#产物输出仓库开关)）。

## 目录

- [快速开始](#快速开始)
- [架构](#架构)
- [输出](#输出)
- [配置](#配置)
- [可靠性安全与测试](#可靠性安全与测试)
- [一房一价接口链路](#一房一价接口链路)

## 快速开始

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
```

**静态生成**（一次性生成全部输出）：

```bash
export WFT_TOKEN='你的 wfTToken'
.venv/bin/python -m sale_dashboard \
  --site-output site \
  --page-size 50 \
  --room-page-size 500 \
  --fetch-one-price \
  --enrichment-batch-size 80
```

**实时 FastAPI**：

```bash
.venv/bin/pip install -r requirements.txt
export WFT_TOKEN='你的 wfTToken'
.venv/bin/uvicorn sale_dashboard.api:app --host 127.0.0.1 --port 8000 --reload
```

打开 `http://127.0.0.1:8000/` 即可使用（路由见[实时输出](#实时输出)）。

## 架构

```text
GitHub Actions schedule (00:00 UTC = 08:00 CST)
  → pytest
  → 分页请求 GetLouPanSaleImages（短页不终止，null/空列表终止，按 ID 去重）
  → 每次轮转抓取 80 个楼盘的预售证、房号、户型图与昨日网签（重点楼盘每日优先刷新）
  → 复用 site/data 中未轮到楼盘的既有 JSON，生成全部楼盘总览与详情
  → 写入 enrichment-state.json、token 扫描、提交快照、部署 GitHub Pages

FastAPI
  → / 与 /projects/{id}/ 复用同一套渲染层
  → 点击楼盘时请求 GetLouPanRoomType / GetLouPanPreSaleCertificates / GetLouPanRoomItems
  → SQLite 持久缓存项目、预售证、房号与户型图响应
  → POST /api/warm 后台顺序预热；重启后跳过已完成项目继续
```

静态生成器只使用 Python 标准库；FastAPI 运行时依赖见 `requirements.txt`。

## 输出

### 静态输出

- `site/index.html` — 包含全部楼盘的单页仪表盘；
- `site/projects/{id}/` — 楼盘详情、全部字段、销控图，以及已抓取批次的户型图与一房一价双视图；
- `site/data/projects/{id}/one-price.json.gz` — 该楼盘一房一价持久 gzip JSON；浏览器端自动解压，显著控制仓库体积；
- `site/data/projects/{id}/room-types.json` — 该楼盘户型图持久 JSON；
- `site/data/enrichment-state.json` — 下一批增量抓取游标；
- `site/data/sale-data.json` — 楼盘列表生产快照。

### 实时输出

- `/` — 实时全部楼盘总览；
- `/projects/{id}/` — 实时户型图与一房一价详情；
- `/api/projects` — 楼盘列表 JSON，支持 `?refresh=true` 强制刷新；
- `/api/projects/{id}/room-types` — 户型图 JSON，支持 `?refresh=true`；
- `/api/projects/{id}/one-price` — 一房一价 JSON，支持 `?refresh=true`；
- `POST /api/warm` — 后台顺序预热全部楼盘，立即返回；
- `GET /api/warm/status` — 查看预热进度；
- `POST /api/warm/stop` — 停止预热。

默认 SQLite 缓存位于 `.wft-cache/responses.sqlite3`，缓存 TTL 为 21600 秒（6 小时）。可用 `WFT_CACHE_PATH` 与 `WFT_CACHE_TTL_SECONDS` 调整。预热会把每个完成的楼盘快照和预售证/房号原始响应写入缓存；进程重启后再次 `POST /api/warm` 会跳过已完成项目，从中断附近继续，而不是从零开始。

### 一房一价双视图

一房一价详情提供两种视图：

**明细表**

- 支持预售证、楼栋、单元、状态、关键字、单价区间与总价区间筛选；
- 分页显示但不截断已获取 JSON 数据。

**楼层分布**

- 按楼栋 / 单元从左到右、真实楼层从上到下排成整体矩阵，同一楼层的全部房源保持横向一排；
- 空缺楼层格用 `—` 占位保持楼栋对齐；已售为红色，可售为绿色，并展示房号、户型、面积、单价与总价；
- 可售房源相同单价使用同一个价格色块，价格文本与状态文本同时保留，避免只依赖颜色；
- 点击「全屏地图」进入真全屏：顶部保留可收起的筛选面板（预售证、楼栋、单元、搜索、状态、单价与总价），底部为缩放工具，筛选与缩放区域不会遮挡初始矩阵；
- `清除` 可一键恢复全部筛选，Esc 或「退出全屏」返回原位置；
- 窄屏时矩阵在卡片内横向滚动，页面本身不横向溢出。

## 配置

### 重点楼盘清单

编辑 `config/featured-projects.txt`，一行一个项目 ID 或项目名称（名称必须与 HTML 中显示的项目名一致；`#` 后为注释）：

```text
334502133780562
武汉雅居乐花园
```

匹配到的项目会固定展示在首页最上方的 **重点楼盘** 区域，且不会在下方全部列表重复出现。每日自动 Action 会在复用既有增量数据的同时，强制刷新这些项目的一房一价与户型详情；手动全量增量任务也会优先处理它们。清单为空时，首页自动隐藏该区域；未匹配的行会被忽略，不影响其他项目生成。

### 命令行参数与环境变量

| 参数 | 环境变量 | 默认值 |
|---|---|---|
| `--api-url` | `WFT_API_URL` | 五房通 `GetLouPanSaleImages` |
| `--city-id` | `WFT_CITY_ID` | `4201` |
| `--page-size` | `WFT_PAGE_SIZE` | `50` |
| `--room-page-size` | `WFT_ROOM_PAGE_SIZE` | `500` |
| `--fetch-one-price` | 无 | 关闭；开启后分批补齐户型图、一房一价与昨日网签 |
| `--enrichment-batch-size` | `WFT_ENRICHMENT_BATCH_SIZE` | `80`；按项目列表游标轮转，未轮到的项目复用已提交 JSON |
| `--featured-projects` | `WFT_FEATURED_PROJECTS` | `config/featured-projects.txt`；支持项目 ID 或名称 |
| `--refresh-featured` | 无 | 关闭；复用增量数据时仍强制刷新重点楼盘详情 |
| `--max-pages` | `WFT_MAX_PAGES` | `100` |
| `--timeout` | `WFT_REQUEST_TIMEOUT_SECONDS` | `20` |
| `--site-output` | `WFT_SITE_OUTPUT` | `site` |

### 产物输出仓库开关

`config/artifact-target.txt` 决定每日/手动任务把 `site/` 快照提交到哪里：

- `external`（默认）— 提交到数据仓 `pekaboo/wuhan-housing-market-dashboard`，本仓库只保留代码；增量复用与轮转游标都从数据仓读取。
- `local` — 提交回本仓库（旧行为）。

翻转开关 = 改一行并提交。文件缺失或值非法时任务会在测试前立即失败，不会猜方向。数据仓地址配置在两个 workflow 的顶层 `env.DATA_REPO`。

external 模式前置条件（一次性，约 2 分钟）：

```bash
# 1) 创建 fine-grained PAT（GitHub → Settings → Developer settings）：
#    Repository access 仅勾选 pekaboo/wuhan-housing-market-dashboard，
#    Permissions 仅勾 Contents: Read and write
# 2) 把 PAT 存为本仓库 secret
gh secret set DATA_REPO_TOKEN -R pekaboo/wuhan-housing-market-task
# 3) 播种数据仓：自动建仓，并把当前已提交的 site/（含增量游标）推为首个提交
./scripts/bootstrap-dashboard-repo.sh
```

GitHub Pages 部署策略（双地址都保持最新）：

- task 仓每次运行都部署主站 `https://pages.wangyitu.tech/wuhan-housing-market-task/`（自定义域名，两种模式下都是最新）；
- external 模式下，dashboard 仓每次收到快照推送还会自动发布它自己的 Pages：`https://pekaboo.github.io/wuhan-housing-market-dashboard/`（由数据仓内的 `deploy-pages.yml` 用自身 `GITHUB_TOKEN` 完成，零额外凭证；local 模式期间该地址停留在最后一次 external 快照）。

注意：external 模式稳定运行后，可手动 `git rm -r site` 让本仓库彻底只留代码。删除后如切回 `local`，增量明细会冷启动，约 5 次运行重建（首页总览不受影响）。

### GitHub Secrets 与 Pages

在仓库 **Settings → Secrets and variables → Actions** 配置：

- `WFT_TOKEN`：五房通登录 token。不要提交到代码。
- `DATA_REPO_TOKEN`：跨仓推送产物用的 fine-grained PAT（见上一节）。

上游 token 有有效期。过期后每日静态任务会失败；FastAPI 健康检查仍可用，但数据接口会返回 503/502，需要重新抓包并更新环境变量。

在 **Settings → Pages** 中将 Source 设为 **GitHub Actions**。首次配置后，Actions 会发布静态总览。

## 可靠性安全与测试

- 逐页请求；短页不代表结束，直到上游返回空列表或 `null` 才停止，并按楼盘 ID 去重。
- 使用 `max_pages` 防止上游异常导致无限分页。
- 项目按 `id` 去重，避免分页期间数据移动造成重复。
- HTML 对项目名、预售证名、房号、地址、图片地址等做 HTML 转义；房号表由 DOM API 渲染，避免二次注入。
- 一房一价按"楼盘 → 预售证 → 房号"聚合，保留销售状态与异常状态；单项目失败不阻塞其他楼盘。
- 静态增量抓取每次处理 80 个项目；未轮到的项目复用上次提交的 JSON。若上游临时失败且本地已有成功快照，则保留旧成功快照，不用错误占位覆盖。约 5 次运行覆盖全部 390 个项目，之后继续按游标轮转刷新。
- 昨日网签接口失败时仍生成当日销控总览，并在网签页显示明确错误。
- Action 会分批拉取全量一房一价与户型图；实时详情仍由 FastAPI 提供最新点击数据与 SQLite 断点缓存。
- Action 生成后会反向扫描整个 `site/` 目录，并对 gzip JSON 解压后检查，确保 token 没有落盘。
- 一房一价 JSON 使用 minify + gzip + 确定性 mtime 写入；避免数百 MB 明文 JSON 直接进入 Git 历史。
- 输出文件使用同目录临时文件 + `os.replace` 原子写入。

测试：

```bash
.venv/bin/pytest -q
```

覆盖分页停止条件、去重、进度日志、静态增量批次轮转、旧快照保留、持久缓存与断点恢复、FastAPI JSON/HTML 路由、安全转义、历史图列表选择、全字段动态展示、双销控图、一房一价双视图、原始 JSON 和单页 HTML 生成。

## 一房一价接口链路

| 步骤 | 接口 | 输入 | 展示用途 |
|---|---|---|---|
| 1 | `GetLouPanSaleImages` | 城市 ID 分页 | 楼盘列表、销控图、总览 KPI |
| 2 | `GetLouPanRoomType` | 楼盘 `id` 作为 `houseid` | 户型图、面积、户型、可售数量、楼栋分布；点击卡片弹出大图 |
| 3 | `GetLouPanPreSaleCertificates` | 楼盘 `id` | 预售证编号、房源/已售/可售/去化摘要 |
| 4 | `GetLouPanRoomItems` | 楼盘 `id` + 预售证 `id` 作为 `evidenceId` | 楼栋、单元、楼层、房号、户型、面积、单价、总价、交付与状态 |
| 5 | `GetWangQianHouseData` | 昨日日期分页 | 昨日网签总量、楼盘变化与房号明细 |

房号状态按上游枚举展示：`saleStatus=1` 为已售，`saleStatus=2` 为可售；`abnormalStatus=1` 追加"异常"标记。
