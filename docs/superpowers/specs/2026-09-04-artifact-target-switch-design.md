# 产物输出仓库开关（artifact-target switch）设计

日期：2026-09-04
状态：已与用户确认

## 背景与目标

`wuhan-housing-market-task`（本仓库，原 pekaboo-task）当前由两个 GitHub Actions 工作流
（每日 08:00 CST 的 `daily-production-html.yml` 与手动触发的 `manual-full-enrichment.yml`）
在 runner 上生成静态站点 `site/`，并每日以 "chore: update daily sale-control snapshot"
提交回本仓库，再部署 GitHub Pages。`site/` 工作区约 60MB，仓库 pack 约 50MB，
数据产物已占仓库体积的绝大部分。

目标：做一个开关，把数据产物迁移到独立的数据仓
`pekaboo/wuhan-housing-market-dashboard`，本仓库只留代码，防止代码仓库被数据
撑大/误伤；需要时可一键切回现状。

## 需求

- 开关控制产物（`site/` 快照提交）去向：
  - `local` — 提交回本仓库（完全现状行为）；
  - `external` — 提交到 `pekaboo/wuhan-housing-market-dashboard`。
- 默认方向为 `external`（数据迁移）。
- 开关翻转必须留下 git 历史（用户选型），即以仓库内配置文件实现。
- 增量轮转抓取依赖上次提交的 JSON（`--reuse-enrichment` 读取 `site/data/`），
  数据仓必须同时作为下一次运行的输入。
- GitHub Pages 部署行为与 URL 不变。
- 开关缺失或值非法时立即失败，绝不静默猜测方向。

## 方案选型

| 方案 | 机制 | 结论 |
|---|---|---|
| A | GitHub 仓库变量 `ARTIFACT_TARGET` | 翻转零提交，但开关状态无 git 历史 |
| **B（选用）** | 仓库配置文件 `config/artifact-target.txt` | 翻转 = 一行提交，有历史可审 |
| C | 仅 workflow_dispatch 输入 | 定时任务仍需改 YAML，非真开关 |

## 详细设计

### 1. 开关文件

- `config/artifact-target.txt`：单个词 `local` 或 `external`（大小写不敏感；
  允许 `#` 注释与空行，风格同 `config/featured-projects.txt`）。
- 初始值 `external`。
- 数据仓地址不放配置文件，放两个 workflow 顶层
  `env: DATA_REPO: pekaboo/wuhan-housing-market-dashboard`。
- 解析在 workflow bash 内完成（grep/注释过滤/取首个有效词/小写化）。
- 文件缺失或值不是 `local`/`external` → 该步骤 `exit 1` 并输出明确错误，
  位置在 checkout 之后、pytest 之前（fail fast）。

### 2. 工作流数据流（两个 workflow 相同改法）

```text
checkout 代码仓
→ 解析 config/artifact-target.txt（非法即失败）
→ pytest
→ [external] git clone --depth 1 https://x-access-token:${DATA_REPO_TOKEN}@github.com/${DATA_REPO}.git site
             mv site/.git .artifact-git        # .git 停靠在工作区根
   [local]   不做任何事（site/ 来自本仓库 checkout）
→ 生成到 site/（增量复用读 site/data 既有 JSON）
→ token 泄漏扫描（扫描 site/，.git 停靠在外，范围与现状一致）
→ 提交推送：
   [local]   git add -A site / commit / push（现状，GITHUB_TOKEN）
   [external] GIT_DIR=$PWD/.artifact-git GIT_WORK_TREE=$PWD/site
             git add -A / commit / git push（PAT 认证，remote 已带 token URL）
→ upload-pages-artifact(path: site) + deploy-pages（两模式共用，不变）
```

关键约束与理由：

- 生成器 `write_site` 会 `shutil.rmtree(site)` 后整体重写（`sale_dashboard/generate.py:97-99`），
  但旧 JSON 在重写前已全部读入内存，因此外部模式必须先克隆数据仓到 `site/` 再生成。
- `.git` 从克隆后到任务结束全程停靠在 `site/` 之外，提交推送通过
  `GIT_DIR`/`GIT_WORK_TREE` 指向停靠位置完成，**永不回移**：
  - rmtree 不会误删数据仓 `.git`；
  - Pages 工件永不包含 `.git`；
  - token 扫描范围与现状完全一致。
- 克隆使用 `--depth 1`：数据仓历史逐日增长，浅克隆保证每日任务耗时稳定；
  追加提交后 push 不受浅克隆影响。
- external 模式的提交信息沿用现状文案（`chore: update daily sale-control
  snapshot` / `chore: increment sale-control enrichment`），仅落仓库不同。

### 3. 认证

- 本仓库新增 secret `DATA_REPO_TOKEN`：fine-grained PAT，仅授权
  `pekaboo/wuhan-housing-market-dashboard`，权限仅 Contents: Read/Write。
- external 分支克隆与推送均使用该 token；local 分支沿用默认 `GITHUB_TOKEN`。

### 4. 首次迁移与回切语义

- 一次性引导脚本 `scripts/bootstrap-dashboard-repo.sh`（本地执行，脚本留档；
  创建仓库需已登录的 `gh` CLI，推送需对本仓与数据仓的 push 权限）：
  创建数据仓 → 将当前 `site/` 内容原样推为首个提交（保留增量游标与全部
  已抓取 JSON），首次 external 运行即可无缝续上轮转。
- 本仓库现有 `site/` **不在本任务删除**。external 模式连续运行正常后，
  由用户手动 `git rm -r site` 单独提交（渐进迁移，防丢失优先）。
- 删除 `site/` 后若切回 `local`：增量复用冷启动——首页照常生成，明细数据
  约需 5 次运行重建（游标重置重新轮转，不是数据损坏）。此行为写入 README。

### 5. 错误处理

| 故障 | 行为 |
|---|---|
| 开关文件缺失/值非法 | pytest 前即失败，明确报错 |
| 数据仓克隆失败（secret 未配/无权限/仓库不存在） | 生成前失败，任何仓库都不写入 |
| 生成中途失败 | runner 临时环境，无影响 |
| 推送失败 | 任务红；数据仓游标未推进，下次重试同一批 |
| token 泄漏扫描命中 | 提交/推送前失败（与现状一致） |

两 workflow 共享 `concurrency: production-site`，任一模式都不会并发写同一仓库。

### 6. 测试计划

- 更新 `tests/test_workflow.py`：
  - 断言两个 workflow 均解析 `config/artifact-target.txt`、均有 `external` 与
    `local` 两分支、引用 `DATA_REPO` 与 `DATA_REPO_TOKEN`；
  - 断言 token 扫描仍位于提交推送之前；
  - 保留并按需调整既有断言（如 `git add -A site`、`path: site`）。
- 新增测试：`config/artifact-target.txt` 存在且值为合法值之一。
- Python 包零改动：开关解析位于 workflow bash，生成器已被 `--site-output` 解耦。

## 非目标

- 不删除本仓库现有 `site/`（后续手动操作）。
- 不修改 `sale_dashboard/` Python 代码。
- 不做双仓同时备份（用户已明确为单目标迁移模式）。

## 修订：2026-09-05

应用户要求增加 **dashboard 仓自动部署**（推翻原"不迁移 Pages"的非目标，采用双地址策略）：

- dashboard 仓新增 `.github/workflows/deploy-pages.yml`：`on: push(main)` 用自身 `GITHUB_TOKEN` 把仓库根部署为 Pages（`pekaboo.github.io/wuhan-housing-market-dashboard/`），rsync 排除 `.git`/`.github` 后打包；
- task 仓的 Pages 部署保持无条件执行（两种模式下主地址 `pages.wangyitu.tech/wuhan-housing-market-task/` 永远最新，避免任一地址出现僵尸站）；
- task 仓 external 提交步骤改为 `git add -A -- . ':(exclude).github'`，防止把 dashboard 仓的部署 workflow 当作缺失文件删除。

## 实施清单（概要）

1. 新增 `config/artifact-target.txt`（值 `external`）。
2. 修改两个 workflow：解析开关 + 准备分支 + 提交分支 + `env.DATA_REPO`。
3. 新增 `scripts/bootstrap-dashboard-repo.sh` 并本地执行一次性迁移。
4. 配置 secret `DATA_REPO_TOKEN`（用户在 GitHub 网页操作）。
5. 更新 `tests/test_workflow.py` 与 README（开关说明、回切语义）。
