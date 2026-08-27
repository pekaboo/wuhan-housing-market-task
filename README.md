# pekaboo-task · 武汉楼盘销控每日生产 HTML

这个仓库每天 **08:00（Asia/Shanghai）** 调用五房通生产接口，拉取武汉全部在售楼盘销控数据，生成：

- `site/index.html` — 第 1 页生产仪表盘
- `site/page/2/`、`site/page/3/` … — 后续楼盘分页
- `site/projects/{id}/` — 每个楼盘独立详情页，包含全部字段、原始 JSON、标准销控图、抖音版销控图与历史销控图
- `site/data/sale-data.json` — 原始生产数据快照
- GitHub Pages 生产站点

概览卡片直接展开“全部字段”表格并支持全字段搜索；页面包含最新销控图、已售套数、均价、分页、排序、暗色模式和响应式布局。未来上游新增字段会自动显示，无需修改模板。

## 架构

```text
GitHub Actions schedule (00:00 UTC = 08:00 CST)
  → pytest
  → Python 标准库分页请求 GetLouPanSaleImages
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
  --projects-per-page 6
```

也支持这些可选参数或同名环境变量：

| 参数 | 环境变量 | 默认值 |
|---|---|---|
| `--api-url` | `WFT_API_URL` | 五房通 `GetLouPanSaleImages` |
| `--city-id` | `WFT_CITY_ID` | `4201` |
| `--page-size` | `WFT_PAGE_SIZE` | `10` |
| `--max-pages` | `WFT_MAX_PAGES` | `100` |
| `--timeout` | `WFT_REQUEST_TIMEOUT_SECONDS` | `20` |
| `--site-output` | `WFT_SITE_OUTPUT` | `site` |
| `--projects-per-page` | `WFT_PROJECTS_PER_PAGE` | `6` |

## GitHub 配置

在仓库 **Settings → Secrets and variables → Actions** 配置：

- `WFT_TOKEN`：五房通登录 token。不要提交到代码。

注意：上游 token 有有效期。过期后每日任务会失败并触发 GitHub 的失败通知，需要重新抓包并更新 secret。

在 **Settings → Pages** 中将 Source 设为 **GitHub Actions**。首次配置后，Actions 会发布到 GitHub Pages。

## 可靠性与安全

- 逐页请求；当返回数量小于 `page_size` 时停止。
- 使用 `max_pages` 防止上游异常导致无限分页。
- 项目按 `id` 去重，避免分页期间数据移动造成重复。
- HTML 对项目名、地址、图片地址等做 HTML 转义。
- Action 生成后会反向扫描 `index.html` 和 JSON，确保 token 没有落盘。
- 输出文件使用同目录临时文件 + `os.replace` 原子写入。

## 测试

```bash
.venv/bin/pytest -q
```

测试覆盖分页停止条件、去重、上游错误、安全转义、历史图列表选择、全字段动态展示、双销控图、原始 JSON、多页 HTML 生成和 JSON 原子输出。
