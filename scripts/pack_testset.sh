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
