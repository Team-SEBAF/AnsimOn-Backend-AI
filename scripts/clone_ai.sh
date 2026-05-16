#!/bin/bash

set -e

AI_REPO_URL="https://github.com/Team-SEBAF/AnsimOn-AI.git"
BRANCH="${1:-main}"

usage() {
  echo "Usage: $0 [branch]"
  echo "  branch  클론할 브랜치 (기본값: main)"
  echo ""
  echo "Examples:"
  echo "  $0              # main 브랜치"
  echo "  $0 develop      # develop 브랜치"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

BACKUP_DIR="$(mktemp -d)"

# Backend-AI에서만 수정한 파일은 클론으로 덮어쓰지 않도록 백업
if [ -f "ai/src/ansimon_ai/caching/caching.py" ]; then
  echo "📦 백업: ansimon_ai/caching/caching.py"
  mkdir -p "$BACKUP_DIR/caching"
  cp -a ai/src/ansimon_ai/caching/caching.py "$BACKUP_DIR/caching/"
fi

echo "🧹 기존 ai 폴더 제거"
rm -rf ai

echo "📥 AI 레포 클론 (branch: ${BRANCH}, ai/src만 유지)"
git clone --branch "$BRANCH" --single-branch "$AI_REPO_URL" ai_temp
mkdir -p ai
mv ai_temp/src ai/
rm -rf ai_temp

if [ -f "$BACKUP_DIR/caching/caching.py" ]; then
  echo "♻️  복원: ansimon_ai/caching/caching.py"
  mkdir -p ai/src/ansimon_ai/caching
  cp -a "$BACKUP_DIR/caching/caching.py" ai/src/ansimon_ai/caching/
fi

rm -rf "$BACKUP_DIR"
echo "✅ AI 코드 세팅 완료"
