#!/bin/bash
# testset-cases.tar.part-* 분할본을 이어 붙여 testset/ 아래에 풀기

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

shopt -s nullglob
parts=(testset-cases.tar.part-*)
shopt -u nullglob

if [ ${#parts[@]} -eq 0 ]; then
  echo "testset-cases.tar.part-* 파일이 없습니다. 저장소에 분할 아카이브가 있는지 확인하세요." >&2
  exit 1
fi

echo "📂 testset-cases.tar.part-* → testset/"
mkdir -p testset
# 분할 순서 보장 (aa, ab, …)
IFS=$'\n' sorted=($(printf '%s\n' "${parts[@]}" | sort))
cat "${sorted[@]}" | tar xf - -C testset
echo "✅ 완료"
