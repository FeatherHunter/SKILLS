#!/usr/bin/env bash
#
# ilife #45 双包发布 wizard：dsh-life-pack 0.2.0 + dsh-calorie 0.1.4。
# 人在可交互终端里跑；登录走网页审批、发布要 OTP 当场输/当场批。
# Agent 不代跑 publish（非交互必 EOTP，见 references/pitfalls.md 坑 8）。
#
# 运行：bash "D:/2Study/StudyNotes/SKILLS/npm-publish/wizard-ilife-45.sh"
#
# Everything above the "STAGES" marker is the wizard library: do not hand-edit
# it. Author the per-step stages below the marker.

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────
# Wizard library — delightful, consistent UX. Identical across every wizard.
# ──────────────────────────────────────────────────────────────────────────

if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
  BOLD=$(tput bold); DIM=$(tput dim); RESET=$(tput sgr0)
  BLUE=$(tput setaf 4); GREEN=$(tput setaf 2); YELLOW=$(tput setaf 3); RED=$(tput setaf 1)
else
  BOLD=""; DIM=""; RESET=""; BLUE=""; GREEN=""; YELLOW=""; RED=""
fi

# Author sets this at the top of the stages section.
TOTAL_STAGES=0

_STAGE_INDEX=0
ENV_FILE="${ENV_FILE:-.env}"
WRITTEN_ENV=()    # KEYs written to ENV_FILE this run
WRITTEN_SECRET=() # secret NAMEs set this run
SKIPPED=()        # things we couldn't do (e.g. gh missing)

# _clear — wipe the terminal so only the current step is on screen. No-op when
# output isn't a terminal, so piped logs stay readable.
_clear() {
  [[ -t 1 ]] || return 0
  if command -v tput >/dev/null 2>&1; then tput clear; else printf '\033[2J\033[3J\033[H'; fi
}

# banner "Title" — opening frame: what this wizard does.
banner() {
  _clear
  printf '\n%s%s  %s%s\n' "$BOLD" "$BLUE" "$1" "$RESET"
  printf '%s  %s stages%s\n\n' "$DIM" "$TOTAL_STAGES" "$RESET"
  printf '%s  You drive the browser; this wizard tells you exactly what to do and\n' "$DIM"
  printf '  captures the values you copy back. Stop any time with Ctrl-C and re-run\n'
  printf '  later — it remembers values already saved.%s\n' "$RESET"
  pause "Ready to start?"
}

# stage "Name" — clear the screen, then announce a stage and show progress.
# Clearing keeps only the current step on screen.
stage() {
  _clear
  _STAGE_INDEX=$((_STAGE_INDEX + 1))
  printf '\n%s%s▸ Stage %s/%s · %s%s\n' \
    "$BOLD" "$BLUE" "$_STAGE_INDEX" "$TOTAL_STAGES" "$1" "$RESET"
}

# say "..." — a plain instruction line.
say()  { printf '  %s\n' "$1"; }
# step "..." — a numbered-feeling action the human takes in the browser.
step() { printf '  %s•%s %s\n' "$BLUE" "$RESET" "$1"; }
note() { printf '  %s%s%s\n' "$DIM" "$1" "$RESET"; }
warn() { printf '  %s⚠ %s%s\n' "$YELLOW" "$1" "$RESET"; }

# open_url URL — open in the human's browser, cross-platform incl. WSL.
open_url() {
  local url="$1"
  printf '  %s↗ opening%s %s\n' "$GREEN" "$RESET" "$url"
  { if   command -v wslview     >/dev/null 2>&1; then wslview "$url"
    elif command -v explorer.exe >/dev/null 2>&1; then explorer.exe "$url"
    elif command -v xdg-open    >/dev/null 2>&1; then xdg-open "$url"
    elif command -v open        >/dev/null 2>&1; then open "$url"
    else warn "couldn't open a browser — visit it manually: $url"; fi
  } >/dev/null 2>&1 || warn "couldn't open a browser — visit it manually: $url"
}

# pause "msg" — wait for the human to confirm they've done the manual part.
pause() {
  printf '  %s%s%s ' "$DIM" "${1:-Press Enter to continue}" "$RESET"
  read -r _ || true
}

# confirm "question" — y/N gate; returns success on yes.
confirm() {
  local reply=""
  printf '  %s? %s [y/N] ' "$YELLOW" "$1"
  read -r reply || true
  [[ "$reply" =~ ^[Yy] ]]
}

# _existing KEY — current value of KEY in ENV_FILE, if any.
_existing() {
  [[ -f "$ENV_FILE" ]] || return 1
  local line; line=$(grep -E "^${1}=" "$ENV_FILE" | tail -n1) || return 1
  printf '%s' "${line#*=}"
}

# ask KEY "Prompt" — read a value into $KEY. Offers the existing .env value as
# a default on re-runs (Enter keeps it). Visible input (non-secret).
ask() {
  local key="$1" prompt="$2" current input
  current=$(_existing "$key" || true)
  if [[ -n "$current" ]]; then
    printf '  %s%s%s %s[Enter keeps current]%s ' "$BOLD" "$prompt" "$RESET" "$DIM" "$RESET"
  else
    printf '  %s%s%s ' "$BOLD" "$prompt" "$RESET"
  fi
  read -r input || true
  [[ -z "$input" && -n "$current" ]] && input="$current"
  printf -v "$key" '%s' "$input"
}

# ask_secret KEY "Prompt" — like ask, but input is hidden.
ask_secret() {
  local key="$1" prompt="$2" current input
  current=$(_existing "$key" || true)
  if [[ -n "$current" ]]; then
    printf '  %s%s%s %s[Enter keeps current]%s ' "$BOLD" "$prompt" "$RESET" "$DIM" "$RESET"
  else
    printf '  %s%s%s ' "$BOLD" "$prompt" "$RESET"
  fi
  read -rs input || true
  printf '\n'
  [[ -z "$input" && -n "$current" ]] && input="$current"
  printf -v "$key" '%s' "$input"
}

# write_env KEY VALUE — upsert KEY=VALUE into ENV_FILE (creates it; replaces
# any existing line). Idempotent.
write_env() {
  local key="$1" value="$2" tmp
  touch "$ENV_FILE"
  tmp=$(mktemp)
  grep -vE "^${key}=" "$ENV_FILE" > "$tmp" || true
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
  mv "$tmp" "$ENV_FILE"
  WRITTEN_ENV+=("$key")
  printf '  %s✓ wrote%s %s → %s\n' "$GREEN" "$RESET" "$key" "$ENV_FILE"
}

# set_secret NAME VALUE — set a GitHub Actions repo secret via gh. Falls back
# to a warning (and records it) if gh is unavailable or unauthenticated.
set_secret() {
  local name="$1" value="$2"
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if printf '%s' "$value" | gh secret set "$name" >/dev/null 2>&1; then
      WRITTEN_SECRET+=("$name")
      printf '  %s✓ set%s GitHub secret %s\n' "$GREEN" "$RESET" "$name"
      return
    fi
  fi
  SKIPPED+=("GitHub secret $name (set it manually: gh secret set $name)")
  warn "skipped GitHub secret $name — gh not ready; set it later"
}

# set_var NAME VALUE — set a GitHub Actions repo variable (non-secret).
set_var() {
  local name="$1" value="$2"
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if gh variable set "$name" --body "$value" >/dev/null 2>&1; then
      printf '  %s✓ set%s GitHub variable %s\n' "$GREEN" "$RESET" "$name"
      return
    fi
  fi
  SKIPPED+=("GitHub variable $name")
  warn "skipped GitHub variable $name — gh not ready; set it later"
}

# finish — clear, then a closing summary of everything configured.
finish() {
  _clear
  printf '\n%s%s  ✓ Setup complete%s\n' "$BOLD" "$GREEN" "$RESET"
  (( ${#WRITTEN_ENV[@]} ))    && note "wrote ${#WRITTEN_ENV[@]} value(s) to $ENV_FILE: ${WRITTEN_ENV[*]}"
  (( ${#WRITTEN_SECRET[@]} )) && note "set ${#WRITTEN_SECRET[@]} GitHub secret(s): ${WRITTEN_SECRET[*]}"
  if (( ${#SKIPPED[@]} )); then
    printf '\n'; warn "still to do by hand:"
    for s in "${SKIPPED[@]}"; do note "  - $s"; done
  fi
  printf '\n'
}

# ──────────────────────────────────────────────────────────────────────────
# STAGES — ilife #45 双包发布。纯动作，无落盘值（登录态由 npm 自己管 ~/.npmrc，
# OTP 绝不记录）。发布不可逆（72h 窗口），每次发布前 confirm。
# ──────────────────────────────────────────────────────────────────────────

TOTAL_STAGES=4
REG="https://registry.npmjs.org"

banner "ilife #45 双包发布（dsh-life-pack 0.2.0 + dsh-calorie 0.1.4）"

# ── Stage 1：登录 ─────────────────────────────────────────────────────────
stage "登录官方源"
say "发布必须走官方源（你本机默认是镜像源，只读不写）。"
if npm whoami --registry="$REG" >/dev/null 2>&1; then
  say "已登录：$(npm whoami --registry="$REG")，跳过登录。"
else
  step "下面跑网页登录：按提示回车 → 浏览器里登录 + 2FA 审批 → 回终端。"
  pause "回车开始登录（npm login --auth-type=web）"
  npm login --auth-type=web --registry="$REG"
  if npm whoami --registry="$REG" >/dev/null 2>&1; then
    say "登录成功：$(npm whoami --registry="$REG")。"
  else
    warn "登录态仍无效——停在这里，别往下发。重跑本脚本或找 Agent 看。"
    SKIPPED+=("npm 登录（token 401/过期）")
    finish
    exit 1
  fi
fi

# ── Stage 2：发 dsh-life-pack 0.2.0 ────────────────────────────────────────
stage "发布 dsh-life-pack 0.2.0"
say "目录：D:/ilife/packages/plugin-manager（已是待发版 0.2.0，注册表现有 0.1.1）。"
cd "D:/ilife/packages/plugin-manager"
printf '  %s确认发布 dsh-life-pack@0.2.0 到官方源（不可逆）：直接回车=发布，输入 n 跳过%s ' "$YELLOW" "$RESET"
read -r _pub1 || true
if [[ ! "$_pub1" =~ ^[Nn] ]]; then
  npm publish --registry="$REG"
  got=$(npm view dsh-life-pack version --registry="$REG" --prefer-online 2>/dev/null || true)
  if [[ "$got" == "0.2.0" ]]; then
    say "✓ 注册表已是 0.2.0。"
  else
    warn "注册表读到 [$got]，不是 0.2.0——停在这里，别发下一个。"
    SKIPPED+=("dsh-life-pack 0.2.0 复核（读到 $got）")
    finish
    exit 1
  fi
else
  note "已跳过本包。"
  SKIPPED+=("dsh-life-pack 0.2.0（人跳过）")
fi

# ── Stage 3：发 dsh-calorie 0.1.4 ──────────────────────────────────────────
stage "发布 dsh-calorie 0.1.4"
say "目录：D:/ilife/packages/plugin-calorie（已是待发版 0.1.4，注册表现有 0.1.3）。"
cd "D:/ilife/packages/plugin-calorie"
printf '  %s确认发布 dsh-calorie@0.1.4 到官方源（不可逆）：直接回车=发布，输入 n 跳过%s ' "$YELLOW" "$RESET"
read -r _pub2 || true
if [[ ! "$_pub2" =~ ^[Nn] ]]; then
  npm publish --registry="$REG"
  got=$(npm view dsh-calorie version --registry="$REG" --prefer-online 2>/dev/null || true)
  if [[ "$got" == "0.1.4" ]]; then
    say "✓ 注册表已是 0.1.4。"
  else
    warn "注册表读到 [$got]，不是 0.1.4——别往下走，找 Agent 看。"
    SKIPPED+=("dsh-calorie 0.1.4 复核（读到 $got）")
    finish
    exit 1
  fi
else
  note "已跳过本包。"
  SKIPPED+=("dsh-calorie 0.1.4（人跳过）")
fi

# ── Stage 4：下一步 ───────────────────────────────────────────────────────
stage "收尾"
say "两个包都发出去了。回 Agent 说一声，Agent 给你一条重装命令 + 重启验证。"
note "（不要自己先装别的 ilife 单品包：bill/chef/home/memo/schedule 还是坏的，同批会炸。）"

finish
