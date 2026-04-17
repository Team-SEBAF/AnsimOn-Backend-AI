#!/bin/bash
# testset/case* → 비압축 tar 후 95MB 단위로 분할 (GitHub 파일당 100MB 제한 회피, Git LFS 불필요)
#
# gzip으로 한 번에 묶은 뒤 split 하면 cat으로 이어 붙여도 gzip이 깨져서 복원 불가 → tar만 쓰고 분할.
#
# 기존에 case 폴더가 git에 올라가 있으면 추적 해제:
#   git rm -r --cached testset/case1 testset/case2 testset/case3 testset/case4 testset/caseN 2>/dev/null || true

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d testset/case1 ]; then
  echo "testset/case1 이 없습니다." >&2
  exit 1
fi

rm -f testset-cases.tar testset-cases.tar.part-*
echo "📦 testset/case* → testset-cases.tar (비압축)"
tar cf testset-cases.tar -C testset case1 case2 case3 case4 caseN

echo "✂️  95MB 단위 분할 → testset-cases.tar.part-*"
split -b 95m testset-cases.tar "testset-cases.tar.part-"
rm -f testset-cases.tar

ls -lh testset-cases.tar.part-*
echo "✅ 완료. 커밋 예: git add testset-cases.tar.part-* .gitignore scripts/pack_testset.sh scripts/unpack_testset.sh testset/set_mtime.py"
