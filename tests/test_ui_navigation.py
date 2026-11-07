import re
from fastapi.testclient import TestClient
from app.main import app

def test_top_header_month_stepper_removed():
    """최상단 중앙의 월 이동(month-stepper)이 삭제되었는지 검증"""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # 최상단 header 내부의 month-stepper 요소가 없어야 함
    assert 'class="month-stepper"' not in html
    assert 'headerMonthLabel' not in html
    assert 'title="현재 월로 이동"' not in html


def test_nav_tab_buttons_order():
    """두번째 열 버튼 구성 및 순서 검증:
    (오늘 빠른등록 -> 월간 상세 -> 연간 대시보드 -> 소비 분석 -> monthTabsContainer)
    """
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # 각 탭 버튼의 ID 위치 확인
    pos_today = html.find('id="tab-btn-today"')
    pos_month_detail = html.find('id="tab-btn-month-detail"')
    pos_annual = html.find('id="tab-btn-annual"')
    pos_spending = html.find('id="tab-btn-spending"')
    pos_month_tabs = html.find('id="monthTabsContainer"')

    assert pos_today != -1, "tab-btn-today가 존재해야 합니다."
    assert pos_month_detail != -1, "tab-btn-month-detail(월간 상세)가 존재해야 합니다."
    assert pos_annual != -1, "tab-btn-annual(연간 대시보드)가 존재해야 합니다."
    assert pos_spending != -1, "tab-btn-spending(소비 분석)가 존재해야 합니다."
    assert pos_month_tabs != -1, "monthTabsContainer가 존재해야 합니다."

    # 순서: 오늘 빠른등록 < 월간 상세 < 연간 대시보드 < 소비 분석 < 월별 탭 컨테이너
    assert pos_today < pos_month_detail < pos_annual < pos_spending < pos_month_tabs, (
        f"버튼 순서가 올바르지 않습니다: today({pos_today}) < month_detail({pos_month_detail}) "
        f"< annual({pos_annual}) < spending({pos_spending}) < monthTabs({pos_month_tabs})"
    )

    # 텍스트 라벨 확인
    assert "월간 상세" in html
    assert "오늘 빠른등록" in html
    assert "연간 대시보드" in html
    assert "소비 분석" in html


def test_js_month_tab_click_logic():
    """app.js의 월 탭 선택 로직 검증:
    - 소비 분석 탭일 때: 소비 분석 유지하며 해당 월 데이터 로드
    - 오늘 빠른등록, 연간 대시보드 등일 때: 월간 상세(m월)로 이동
    """
    client = TestClient(app)
    response = client.get("/static/js/app.js")
    assert response.status_code == 200
    js = response.text

    # onMonthTabClick 함수 존재 여부
    assert "function onMonthTabClick" in js

    # spending일 때와 그 외 처리 분기 확인
    spending_branch = re.search(r"if\s*\(\s*STATE\.currentTab\s*===\s*['\"]spending['\"]\s*\)\s*\{([^}]+)\}\s*else\s*\{([^}]+)\}", js)
    assert spending_branch is not None, "onMonthTabClick 내에 spending 조건 분기가 있어야 합니다."

    spending_body = spending_branch.group(1)
    else_body = spending_branch.group(2)

    assert "loadSpendingPatterns" in spending_body, "spending 상태에서는 loadSpendingPatterns가 호출되어야 합니다."
    assert "switchTab(m)" in else_body, "그 외(today, annual 등)에서는 switchTab(m)으로 월간 상세로 이동해야 합니다."

    # switchTab('month') 처리 여부
    assert "tab === 'month'" in js
    assert "tab-btn-month-detail" in js


def test_mobile_smart_month_navigator():
    """모바일 스마트 월 네비게이터 및 월 선택 바텀시트/모달 UI 요소 및 JS 함수 검증"""
    client = TestClient(app)

    # 1. HTML 요소 검증
    res_html = client.get("/")
    assert res_html.status_code == 200
    html = res_html.text

    assert 'id="mobileMonthBar"' in html
    assert 'id="mobileMonthBarLabel"' in html
    assert 'openMonthPickerModal()' in html
    assert 'prevMonth()' in html
    assert 'nextMonth()' in html
    assert 'id="modalMonthPicker"' in html
    assert 'id="monthPickerGrid"' in html

    # 2. JS 함수 검증
    res_js = client.get("/static/js/app.js")
    assert res_js.status_code == 200
    js = res_js.text

    assert "updateMobileMonthBar" in js
    assert "openMonthPickerModal" in js
    assert "closeMonthPickerModal" in js
    assert "renderMonthPickerGrid" in js
