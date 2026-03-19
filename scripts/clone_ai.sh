#!/bin/bash

set -e

AI_REPO_URL="https://github.com/Team-SEBAF/AnsimOn-AI.git"

echo "🧹 기존 ai 폴더 제거"
rm -rf ai

echo "📥 AI 레포 클론 (ai/src만 유지)"
git clone $AI_REPO_URL ai_temp
mkdir -p ai
mv ai_temp/src ai/
rm -rf ai_temp

echo "✅ AI 코드 세팅 완료"
