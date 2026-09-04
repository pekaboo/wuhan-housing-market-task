# 产物输出仓库开关（artifact-target switch）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 `config/artifact-target.txt` 开关控制每日/手动工作流把 `site/` 快照提交到本仓库（`local`）还是数据仓 `pekaboo/wuhan-housing-market-dashboard`（`external`，默认）。

**Architecture:** 纯 workflow 层改动——解析开关文件（非法即 fail fast）→ external 模式浅克隆数据仓到 `site/` 并把 `.git` 停靠到工作区根（`.artifact-git/`）→ 生成器照常读写 `site/`（增量复用照旧）→ 按开关分支提交（external 用 `GIT_DIR`/`GIT_WORK_TREE` 指向停靠的 `.git` 推送数据仓）→ GitHub Pages 部署不变。附一次性引导脚本播种数据仓。

**Tech Stack:** GitHub Actions（YAML）、bash、pytest（对 YAML 做文本断言，本仓库既有惯例）、`gh` CLI（仅引导脚本用）。

**Spec:** `docs/superpowers/specs/2026-09-04-artifact-target-switch-design.md`

## Global Constraints

- `sale_dashboard/` Python 包**零改动**（生成器已被 `--site-output` 解耦）。
- 既有测试断言必须继续通过，关键字符串：`--site-output site`、`--page-size 50`、`--reuse-enrichment`（daily）、`--fetch-one-price`（仅 manual）、`--room-page-size 500`、`git add -A site`、`path: site`、`gzip.decompress`、`cron: "0 0 * * *"`、`timeout-minutes: 15`、`workflow_dispatch`、`batch_size:`、`default: 100`、`group: production-site`、`--refresh-featured`、`--featured-projects config/featured-projects.txt`。
- daily workflow 里**不得出现** `--fetch-one-price`（既有负向断言）。
- 开关值只有 `local` / `external`（大小写不敏感）；文件缺失或非法 → 工作流在 pytest 前失败，绝不猜方向。
- external 模式提交信息沿用现状：daily 用 `chore: update daily sale-control snapshot`，manual 用 `chore: increment sale-control enrichment`。
- 数据仓地址：`pekaboo/wuhan-housing-market-dashboard`，写在两个 workflow 顶层 `env.DATA_REPO`。
- 测试命令一律 `.venv/bin/pytest -q`（仓库根目录执行）。
- 提交信息风格沿用仓库惯例（`feat:` / `docs:` / `chore:` 前缀）。

---

### Task 1: 开关配置文件

**Files:**
- Create: `config/artifact-target.txt`
- Test: `tests/test_workflow.py`（追加）

**Interfaces:**
- Consumes: 无
- Produces: `config/artifact-target.txt`，内容为单个小写词 `external`；语义（Task 2/3 依赖）：文件可含 `#` 注释与空行，首个有效词大小写不敏感，仅接受 `local`/`external`

- [ ] **Step 1: Write the failing test**

在 `tests/test_workflow.py` 末尾追加：

```python
def test_artifact_target_config_exists_and_holds_a_single_valid_value():
    value = Path('config/artifact-target.txt').read_text(encoding='utf-8')
    tokens = [line.strip().lower() for line in value.splitlines() if line.strip() and not line.strip().startswith('#')]
    assert len(tokens) == 1
    assert tokens[0] in ('local', 'external')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_workflow.py::test_artifact_target_config_exists_and_holds_a_single_valid_value -q`
Expected: FAIL（`FileNotFoundError: config/artifact-target.txt`）

- [ ] **Step 3: Write minimal implementation**

创建 `config/artifact-target.txt`：

```text
# Where daily/manual workflows commit the site/ snapshot.
# local    -> this repository (legacy behavior)
# external -> pekaboo/wuhan-housing-market-dashboard (data-only repository)
external
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_workflow.py::test_artifact_target_config_exists_and_holds_a_single_valid_value -q`
Expected: PASS（1 passed）

- [ ] **Step 5: Commit**

```bash
git add config/artifact-target.txt tests/test_workflow.py
git commit -m "feat: add artifact-target switch config"
```

---

### Task 2: daily workflow 接入开关

**Files:**
- Modify: `.github/workflows/daily-production-html.yml`（全文替换为下方内容）
- Test: `tests/test_workflow.py`（追加）

**Interfaces:**
- Consumes: `config/artifact-target.txt`（Task 1）
- Produces: step id `target` 输出 `steps.target.outputs.target`（`local`|`external`）；停靠目录 `.artifact-git/`；顶层 `env.DATA_REPO`；secret 名 `DATA_REPO_TOKEN`（Task 3/4 同名复用）

- [ ] **Step 1: Write the failing test**

在 `tests/test_workflow.py` 末尾追加：

```python
def test_daily_workflow_switches_artifact_target_between_local_and_external():
    workflow = Path('.github/workflows/daily-production-html.yml').read_text(encoding='utf-8')

    assert 'DATA_REPO: pekaboo/wuhan-housing-market-dashboard' in workflow
    assert 'config/artifact-target.txt' in workflow
    assert 'DATA_REPO_TOKEN' in workflow
    assert "steps.target.outputs.target == 'local'" in workflow
    assert "steps.target.outputs.target == 'external'" in workflow
    assert 'rm -rf site' in workflow
    assert 'mv site/.git .artifact-git' in workflow
    assert 'GIT_DIR' in workflow
    assert 'GIT_WORK_TREE' in workflow


def test_daily_workflow_fails_fast_on_bad_switch_and_scans_token_before_commit():
    workflow = Path('.github/workflows/daily-production-html.yml').read_text(encoding='utf-8')

    assert workflow.index('config/artifact-target.txt') < workflow.index('pytest -q')
    assert '::error::' in workflow
    assert workflow.index('gzip.decompress') < workflow.index('Commit production snapshot')
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_workflow.py -q -k "switches_artifact or fails_fast"`
Expected: FAIL（新断言的 `DATA_REPO:` / `config/artifact-target.txt` 等不存在；Task 1 的测试仍 PASS）

- [ ] **Step 3: Write minimal implementation**

将 `.github/workflows/daily-production-html.yml` 全文替换为：

```yaml
name: Daily Production HTML

on:
  schedule:
    # 08:00 Asia/Shanghai = 00:00 UTC. GitHub may queue cron runs for a few minutes.
    - cron: "0 0 * * *"
  workflow_dispatch:

concurrency:
  group: production-site
  cancel-in-progress: false

env:
  DATA_REPO: pekaboo/wuhan-housing-market-dashboard

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Check out repository
        uses: actions/checkout@v7

      - name: Resolve artifact target
        id: target
        run: |
          value=$(grep -v '^[[:space:]]*#' config/artifact-target.txt | grep -v '^[[:space:]]*$' | head -n 1 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
          case "$value" in
            local|external)
              echo "artifact target: $value"
              echo "target=$value" >> "$GITHUB_OUTPUT"
              ;;
            *)
              echo "::error::config/artifact-target.txt must contain exactly 'local' or 'external' (found '${value:-<missing>}')."
              exit 1
              ;;
          esac

      - name: Set up Python
        uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements-dev.txt

      - name: Run tests
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements-dev.txt
          pytest -q

      - name: Check out dashboard repository snapshot
        if: ${{ steps.target.outputs.target == 'external' }}
        env:
          DATA_REPO_TOKEN: ${{ secrets.DATA_REPO_TOKEN }}
        run: |
          test -n "$DATA_REPO_TOKEN" || { echo "::error::Set the DATA_REPO_TOKEN repository secret."; exit 1; }
          rm -rf site
          git clone --depth 1 "https://x-access-token:${DATA_REPO_TOKEN}@github.com/${DATA_REPO}.git" site
          mv site/.git .artifact-git

      - name: Generate homepage snapshot and reuse committed enrichment
        env:
          WFT_TOKEN: ${{ secrets.WFT_TOKEN }}
        run: |
          test -n "$WFT_TOKEN" || { echo "::error::Set the WFT_TOKEN repository secret."; exit 1; }
          python -m sale_dashboard \
            --site-output site \
            --page-size 50 \
            --room-page-size 500 \
            --reuse-enrichment \
            --refresh-featured \
            --featured-projects config/featured-projects.txt

      - name: Ensure token is absent from generated artifacts
        env:
          WFT_TOKEN: ${{ secrets.WFT_TOKEN }}
        run: |
          python - <<'PY'
          import gzip
          import os
          from pathlib import Path

          token = os.environ["WFT_TOKEN"].encode("utf-8")
          for path in Path("site").rglob("*"):
              if not path.is_file():
                  continue
              content = path.read_bytes()
              if content.startswith(b"\x1f\x8b"):
                  content = gzip.decompress(content)
              if token in content:
                  raise SystemExit(f"Generated artifacts contain the upstream token: {path}")
          PY

      - name: Commit production snapshot (local)
        if: ${{ steps.target.outputs.target == 'local' }}
        run: |
          git config user.name "pekaboo-task[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -A site
          if git diff --cached --quiet; then
            echo "No production snapshot changes."
          else
            git commit -m "chore: update daily sale-control snapshot"
            git push
          fi

      - name: Commit production snapshot (external)
        if: ${{ steps.target.outputs.target == 'external' }}
        run: |
          export GIT_DIR="$PWD/.artifact-git"
          export GIT_WORK_TREE="$PWD/site"
          git config user.name "pekaboo-task[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -A
          if git diff --cached --quiet; then
            echo "No production snapshot changes."
          else
            git commit -m "chore: update daily sale-control snapshot"
            git push
          fi

      - name: Configure GitHub Pages
        id: pages
        uses: actions/configure-pages@v6

      - name: Upload production HTML
        uses: actions/upload-pages-artifact@v5
        with:
          path: site

      - name: Deploy GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_workflow.py -q`
Expected: PASS（全部，含 Task 1 与既有 4 个测试）

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/daily-production-html.yml tests/test_workflow.py
git commit -m "feat: switch daily snapshot target via artifact-target config"
```

---

### Task 3: manual workflow 接入开关

**Files:**
- Modify: `.github/workflows/manual-full-enrichment.yml`（全文替换为下方内容）
- Test: `tests/test_workflow.py`（追加）

**Interfaces:**
- Consumes: `config/artifact-target.txt`（Task 1）；与 Task 2 完全相同的开关语义、`.artifact-git` 停靠、`DATA_REPO`/`DATA_REPO_TOKEN` 命名
- Produces: 无（末端消费者）

- [ ] **Step 1: Write the failing test**

在 `tests/test_workflow.py` 末尾追加：

```python
def test_manual_workflow_switches_artifact_target_between_local_and_external():
    workflow = Path('.github/workflows/manual-full-enrichment.yml').read_text(encoding='utf-8')

    assert 'DATA_REPO: pekaboo/wuhan-housing-market-dashboard' in workflow
    assert 'config/artifact-target.txt' in workflow
    assert 'DATA_REPO_TOKEN' in workflow
    assert "steps.target.outputs.target == 'local'" in workflow
    assert "steps.target.outputs.target == 'external'" in workflow
    assert 'rm -rf site' in workflow
    assert 'mv site/.git .artifact-git' in workflow
    assert 'GIT_DIR' in workflow
    assert 'GIT_WORK_TREE' in workflow
    assert workflow.index('gzip.decompress') < workflow.index('Commit enriched production snapshot')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_workflow.py::test_manual_workflow_switches_artifact_target_between_local_and_external -q`
Expected: FAIL（`AssertionError`，YAML 中无这些字符串）

- [ ] **Step 3: Write minimal implementation**

将 `.github/workflows/manual-full-enrichment.yml` 全文替换为：

```yaml
name: Manual Full Enrichment

on:
  workflow_dispatch:
    inputs:
      batch_size:
        description: Number of projects to enrich incrementally in this run
        required: true
        default: 100
        type: number

concurrency:
  group: production-site
  cancel-in-progress: false

env:
  DATA_REPO: pekaboo/wuhan-housing-market-dashboard

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  enrich-and-publish:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Check out repository
        uses: actions/checkout@v7

      - name: Resolve artifact target
        id: target
        run: |
          value=$(grep -v '^[[:space:]]*#' config/artifact-target.txt | grep -v '^[[:space:]]*$' | head -n 1 | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')
          case "$value" in
            local|external)
              echo "artifact target: $value"
              echo "target=$value" >> "$GITHUB_OUTPUT"
              ;;
            *)
              echo "::error::config/artifact-target.txt must contain exactly 'local' or 'external' (found '${value:-<missing>}')."
              exit 1
              ;;
          esac

      - name: Set up Python
        uses: actions/setup-python@v7
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements-dev.txt

      - name: Run tests
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements-dev.txt
          pytest -q

      - name: Check out dashboard repository snapshot
        if: ${{ steps.target.outputs.target == 'external' }}
        env:
          DATA_REPO_TOKEN: ${{ secrets.DATA_REPO_TOKEN }}
        run: |
          test -n "$DATA_REPO_TOKEN" || { echo "::error::Set the DATA_REPO_TOKEN repository secret."; exit 1; }
          rm -rf site
          git clone --depth 1 "https://x-access-token:${DATA_REPO_TOKEN}@github.com/${DATA_REPO}.git" site
          mv site/.git .artifact-git

      - name: Generate enriched production snapshot
        env:
          WFT_TOKEN: ${{ secrets.WFT_TOKEN }}
        run: |
          test -n "$WFT_TOKEN" || { echo "::error::Set the WFT_TOKEN repository secret."; exit 1; }
          python -m sale_dashboard \
            --site-output site \
            --page-size 50 \
            --room-page-size 500 \
            --fetch-one-price \
            --enrichment-batch-size ${{ inputs.batch_size }} \
            --featured-projects config/featured-projects.txt

      - name: Ensure token is absent from generated artifacts
        env:
          WFT_TOKEN: ${{ secrets.WFT_TOKEN }}
        run: |
          python - <<'PY'
          import gzip
          import os
          from pathlib import Path

          token = os.environ["WFT_TOKEN"].encode("utf-8")
          for path in Path("site").rglob("*"):
              if not path.is_file():
                  continue
              content = path.read_bytes()
              if content.startswith(b"\x1f\x8b"):
                  content = gzip.decompress(content)
              if token in content:
                  raise SystemExit(f"Generated artifacts contain the upstream token: {path}")
          PY

      - name: Commit enriched production snapshot (local)
        if: ${{ steps.target.outputs.target == 'local' }}
        run: |
          git config user.name "pekaboo-task[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -A site
          if git diff --cached --quiet; then
            echo "No enriched production snapshot changes."
          else
            git commit -m "chore: increment sale-control enrichment"
            git push
          fi

      - name: Commit enriched production snapshot (external)
        if: ${{ steps.target.outputs.target == 'external' }}
        run: |
          export GIT_DIR="$PWD/.artifact-git"
          export GIT_WORK_TREE="$PWD/site"
          git config user.name "pekaboo-task[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -A
          if git diff --cached --quiet; then
            echo "No enriched production snapshot changes."
          else
            git commit -m "chore: increment sale-control enrichment"
            git push
          fi

      - name: Configure GitHub Pages
        id: pages
        uses: actions/configure-pages@v6

      - name: Upload production HTML
        uses: actions/upload-pages-artifact@v5
        with:
          path: site

      - name: Deploy GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_workflow.py -q`
Expected: PASS（全部）

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/manual-full-enrichment.yml tests/test_workflow.py
git commit -m "feat: switch manual enrichment target via artifact-target config"
```

---

### Task 4: 数据仓一次性引导脚本

**Files:**
- Create: `scripts/bootstrap-dashboard-repo.sh`（可执行）
- Test: `tests/test_workflow.py`（追加）

**Interfaces:**
- Consumes: 数据仓地址 `pekaboo/wuhan-housing-market-dashboard`（与 `env.DATA_REPO` 一致）
- Produces: 数据仓首个提交 = 本仓库 `HEAD:site` 的原样内容（含 `site/data/enrichment-state.json` 游标），首次 external 运行无缝续上轮转

- [ ] **Step 1: Write the failing test**

在 `tests/test_workflow.py` 末尾追加：

```python
def test_bootstrap_dashboard_repo_script_seeds_from_committed_site_snapshot():
    script = Path('scripts/bootstrap-dashboard-repo.sh').read_text(encoding='utf-8')

    assert 'set -euo pipefail' in script
    assert 'pekaboo/wuhan-housing-market-dashboard' in script
    assert 'git archive HEAD:site' in script
    assert 'refusing to seed' in script
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_workflow.py::test_bootstrap_dashboard_repo_script_seeds_from_committed_site_snapshot -q`
Expected: FAIL（`FileNotFoundError: scripts/bootstrap-dashboard-repo.sh`）

- [ ] **Step 3: Write minimal implementation**

创建 `scripts/bootstrap-dashboard-repo.sh`：

```bash
#!/usr/bin/env bash
# One-time seed of the dashboard repository from the committed site/ snapshot.
# Keeps the enrichment cursor and all fetched JSON so the first external-mode
# run continues the rotation seamlessly.
#
# Requires: gh CLI authenticated (gh auth login) and push rights to both repos.
# Usage:   ./scripts/bootstrap-dashboard-repo.sh
# Env:     DATA_REPO (default pekaboo/wuhan-housing-market-dashboard)
#          DATA_REPO_VISIBILITY (default public)
set -euo pipefail

DATA_REPO="${DATA_REPO:-pekaboo/wuhan-housing-market-dashboard}"
DATA_REPO_VISIBILITY="${DATA_REPO_VISIBILITY:-public}"

command -v gh >/dev/null 2>&1 || { echo "error: gh CLI is required (gh auth login)."; exit 1; }
[ -d site ] || { echo "error: run from the repository root; site/ is missing."; exit 1; }

remote="https://github.com/${DATA_REPO}.git"
if [ -n "$(git ls-remote "$remote" HEAD 2>/dev/null)" ]; then
  echo "error: refusing to seed, ${DATA_REPO} already has commits."
  exit 1
fi

gh repo view "$DATA_REPO" >/dev/null 2>&1 || gh repo create "$DATA_REPO" "--${DATA_REPO_VISIBILITY}"

gh auth setup-git >/dev/null

seed="$(mktemp -d)"
trap 'rm -rf "$seed"' EXIT
git archive HEAD:site | tar -x -C "$seed"
git -C "$seed" init --initial-branch=main >/dev/null
git -C "$seed" add -A
git -C "$seed" \
  -c user.name='pekaboo-task[bot]' \
  -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
  commit -m 'chore: seed dashboard repository from the task repository site snapshot' >/dev/null
git -C "$seed" push "$remote" main:main

echo "seeded ${DATA_REPO} from HEAD:site"
```

- [ ] **Step 4: Make script executable and run test**

```bash
chmod +x scripts/bootstrap-dashboard-repo.sh
.venv/bin/pytest tests/test_workflow.py -q
```

Expected: PASS（全部）

- [ ] **Step 5: Commit**

```bash
git add scripts/bootstrap-dashboard-repo.sh tests/test_workflow.py
git commit -m "feat: add dashboard repository bootstrap script"
```

---

### Task 5: README 文档与全量验证

**Files:**
- Modify: `README.md`（在「GitHub 配置」一节之前插入新节）

**Interfaces:**
- Consumes: 前四个任务的全部产物（开关文件、workflow 分支、引导脚本）
- Produces: 无（文档）

- [ ] **Step 1: Insert documentation section**

在 `README.md` 的 `## GitHub 配置` 标题之前插入：

```markdown
## 产物输出仓库开关

`config/artifact-target.txt` 决定每日/手动任务把 `site/` 快照提交到哪里：

- `external`（默认）— 提交到数据仓 `pekaboo/wuhan-housing-market-dashboard`，本仓库只保留代码；增量复用与轮转游标都从数据仓读取。
- `local` — 提交回本仓库（旧行为）。

翻转开关 = 改一行并提交。文件缺失或值非法时任务会在测试前立即失败，不会猜方向。数据仓地址配置在两个 workflow 的顶层 `env.DATA_REPO`。

external 模式前置条件（一次性）：

1. 运行 `./scripts/bootstrap-dashboard-repo.sh`，把当前已提交的 `site/`（含增量游标）播种为数据仓首个提交；
2. 在 **Settings → Secrets and variables → Actions** 添加 `DATA_REPO_TOKEN`：fine-grained PAT，仅授权 `pekaboo/wuhan-housing-market-dashboard`，权限仅 Contents: Read/Write。

GitHub Pages 部署不受开关影响：部署打包的是 runner 上刚生成的 `site/`，URL 不变。

注意：external 模式稳定运行后，可手动 `git rm -r site` 让本仓库彻底只留代码。删除后如切回 `local`，增量明细会冷启动，约 5 次运行重建（首页总览不受影响）。

```

- [ ] **Step 2: Verify documentation renders and nothing else drifted**

Run: `grep -n "产物输出仓库开关\|bootstrap-dashboard-repo\|DATA_REPO_TOKEN" README.md`
Expected: 三者都能在 README.md 中找到

- [ ] **Step 3: Run the full test suite**

Run: `.venv/bin/pytest -q`
Expected: 全部 PASS，无失败

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: explain the artifact-target switch and dashboard repository setup"
```

---

## 实施后手动步骤（用户操作，非代码任务）

1. GitHub 创建 fine-grained PAT（仅授权 `pekaboo/wuhan-housing-market-dashboard`，Contents: Read/Write），添加为本仓库 secret `DATA_REPO_TOKEN`。
2. 本地运行 `./scripts/bootstrap-dashboard-repo.sh` 播种数据仓。
3. 观察下一次定时任务（或手动触发）在 external 模式跑绿：数据仓出现新提交、Pages 正常部署。
4. external 稳定数日后，手动提交 `git rm -r site`（单独一笔提交，可回滚）。

## Self-Review 记录

- 规格覆盖：①开关文件=Task 1；②workflow 数据流=Task 2/3（含 `rm -rf site`、`.git` 停靠、fail fast、token 扫描顺序）；③认证=Task 2/3 secret 引用+Task 5 文档+手动步骤；④首次迁移=Task 4 脚本；⑤测试=各任务 TDD 步骤。无缺口。
- 占位符扫描：无 TBD/TODO；所有代码步骤给出完整内容。
- 类型/命名一致性：`steps.target.outputs.target`、`.artifact-git`、`DATA_REPO`、`DATA_REPO_TOKEN`、`config/artifact-target.txt` 在各任务间一致；daily/manual 提交信息与现状逐字一致。
