#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "==================================================="
echo "  🌸 HouseholdAccountBook (스마트 파스텔 가계부)"
echo "==================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[오류] python3 명령을 찾을 수 없습니다."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[안내] 가상환경(.venv)을 생성합니다..."
    python3 -m venv .venv
fi

echo "[안내] 가상환경 활성화 및 패키지 확인..."
source .venv/bin/activate
pip install -r requirements.txt --quiet

echo ""
echo "[안내] 가계부 서버를 시작합니다..."
python3 -m app.main
