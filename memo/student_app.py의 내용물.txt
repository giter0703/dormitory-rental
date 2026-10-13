import streamlit as st
from datetime import datetime, date, timedelta
import sheet_manager as sm

# 페이지 설정
st.set_page_config(
    page_title="생활관 자치회 물품 대여 신청 포털",
    page_icon="📦",
    layout="wide"
)

# ==========================================
# [설정 변수]
# ==========================================
NOTICE_FONT_SIZE = "16px"
BUILDING_OPTIONS = ["선택하세요", "웅지관", "창조관", "진리관", "청운관", "향림1관", "향림2관", "향림3관"]
TIME_OPTIONS = ["선택하세요", "20:00~20:30", "20:30~21:00"]
MAX_RENTAL_DAYS = 79  # 사생 최대 대여 가능 일수

# ==========================================
# [모바일/데스크탑 반응형 CSS]
# ==========================================
st.markdown(
    """
    <style>
    /* 물품 카드 스타일 */
    .item-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .item-info {
        font-size: 16px;
        font-weight: 600;
        color: #111111;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .item-badge {
        font-size: 16px;
        font-weight: 700;
        color: #1e88e5;
        margin-left: 6px;
        white-space: nowrap;
    }
    .item-badge-empty {
        font-size: 14px;
        font-weight: 700;
        color: #d32f2f;
        margin-left: 6px;
        white-space: nowrap;
    }

    /* 모바일 반응형: 768px 이하에서 1행 2열 배치 */
    @media screen and (max-width: 768px) {
        div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 8px !important;
            margin-bottom: 0px !important;
        }
        div[data-testid="stColumn"] {
            width: 100% !important;
            min-width: 0 !important;
            flex: unset !important;
        }
        .item-card {
            padding: 10px 8px;
            margin-bottom: 8px;
        }
        .item-info {
            font-size: 14px;
        }
        .item-badge {
            font-size: 14px;
        }
        .item-badge-empty {
            font-size: 12px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📦 생활관 자치회 물품 대여 신청")
st.caption("관생 전용 대여 신청 및 승인 결과 확인 포털")

# --- 생활관 자치회 안내사항 ---
try:
    admin_notice = sm.get_notice()
    if admin_notice:
        formatted_notice = admin_notice.replace("\n", "<br>")
        st.markdown(
            f"""
            <div style="background-color: #f0f7ff; border-left: 6px solid #1e88e5; padding: 14px 18px; border-radius: 6px; margin-top: 10px; margin-bottom: 18px; color: #0d47a1; font-size: {NOTICE_FONT_SIZE}; line-height: 1.5; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
                <div style="font-weight: bold; font-size: calc({NOTICE_FONT_SIZE} + 1px); margin-bottom: 6px;">📢 [생활관 물품 대여 중요 안내사항]</div>
                {formatted_notice}
            </div>
            """,
            unsafe_allow_html=True
        )
except Exception as e:
    st.error(f"🚨 공지사항 로드 중 오류 발생: {e}")

st.markdown("---")

tab_status, tab_apply, tab_query = st.tabs(["📦 대여 가능 물품", "📝 대여 신청하기", "🔍 내 신청 결과 조회"])

# 물품 데이터 로드
raw_items = []
try:
    raw_items = sm.get_all_items()
except Exception as e:
    st.error(f"🚨 구글 시트 물품 데이터를 불러오는 중 오류가 발생했습니다: {e}")
    raw_items = []

# total_qty와 available_qty 정제 및 대여 가능 물품 선별
processed_items = []
item_qty_map = {}
available_items = []

for it in raw_items:
    clean_it = {str(k).strip(): v for k, v in it.items()}
    i_name = str(clean_it.get("item_name", "")).strip()
    if not i_name:
        continue

    # 수량 파싱 및 정합성 보정 (available_qty <= total_qty)
    raw_total = clean_it.get("total_qty", 0)
    raw_avail = clean_it.get("available_qty", 0)
    
    total_qty = int(raw_total) if str(raw_total).isdigit() else 0
    avail_qty = int(raw_avail) if str(raw_avail).isdigit() else 0
    
    if avail_qty > total_qty:
        avail_qty = total_qty
    if avail_qty < 0:
        avail_qty = 0

    item_record = {
        "item_name": i_name,
        "available_qty": avail_qty,
        "total_qty": total_qty
    }
    processed_items.append(item_record)
    item_qty_map[i_name] = {"avail": avail_qty, "total": total_qty}

    if avail_qty > 0:
        available_items.append(i_name)

# ==========================================
# [탭 1: 대여 가능 물품 현황]
# ==========================================
with tab_status:
    st.subheader("실시간 대여 가능 물품")
    
    if not processed_items:
        st.info("현재 등록된 물품이 없습니다.")
    else:
        for i in range(0, len(processed_items), 6):
            chunk = processed_items[i:i+6]
            cols = st.columns(6)
            for j, item in enumerate(chunk):
                with cols[j]:
                    name = item["item_name"]
                    avail = item["available_qty"]
                    total = item["total_qty"]
                    
                    if avail > 0:
                        status_icon = "🟢"
                        badge_html = f'<span class="item-badge">{avail}/{total}</span>'
                    else:
                        status_icon = "🔴"
                        badge_html = f'<span class="item-badge-empty">0/{total}</span>'

                    st.markdown(
                        f"""
                        <div class="item-card">
                            <span class="item-info">{status_icon} {name}</span>
                            {badge_html}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

# ==========================================
# [탭 2: 대여 신청]
# ==========================================
with tab_apply:
    st.subheader("대여 신청서 작성")

    if not available_items:
        st.warning("⚠️ 현재 대여 가능한 물품 재고가 없습니다. '대여 가능 물품' 탭에서 잔여 수량을 확인해 주세요.")
    else:
        # 실시간 연동 및 탭 보존을 위해 일반 컨테이너와 고유 key 사용
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                s_building = st.selectbox("생활관명 선택 *", BUILDING_OPTIONS, index=0, key="s_building")
                s_room = st.text_input("호실 번호 *", placeholder="예: 402호", key="s_room")
                s_id = st.text_input("학번 *", placeholder="예: 20241001", max_chars=10, key="s_id")
                s_name = st.text_input("이름 *", placeholder="예: 홍길동", key="s_name")
                s_email = st.text_input("이메일 (학교 웹메일 또는 G메일) *", placeholder="예: user@s.scnu.ac.kr", key="s_email")
            
            with col2:
                item_dropdown_options = ["선택하세요"] + available_items
                s_item = st.selectbox(
                    "신청 물품 선택 *", 
                    item_dropdown_options,
                    index=0,
                    format_func=lambda x: f"{x} (이용가능: {item_qty_map[x]['avail']}/{item_qty_map[x]['total']})" if x in item_qty_map else x,
                    key="s_item"
                )
                
                # 대여 희망 날짜 변경 시 실시간으로 아래 반납 예정 일자 달력 연동
                r_date = st.date_input("대여 희망 날짜 *", min_value=date.today(), value=date.today(), key="r_date")
                r_time = st.selectbox("대여 희망 시간 *", TIME_OPTIONS, index=0, key="r_time")
                
                max_return_date = r_date + timedelta(days=MAX_RENTAL_DAYS)
                exp_ret_date = st.date_input(
                    "반납 예정 일자 *", 
                    min_value=r_date,  # 희망일자 이전 날짜는 원천 차단됨
                    max_value=max_return_date, 
                    value=r_date,
                    key="exp_ret_date"
                )

            st.markdown("---")
            st.subheader("서약서 동의")
            try:
                pledge_text = sm.get_pledge()
                if pledge_text:
                    formatted_pledge = pledge_text.replace("\n", "<br>")
                    st.markdown(
                        f"""
                        <div style="
                            background-color: #f8f9fa; 
                            border: 1px solid #dee2e6;
                            border-left: 6px solid #6c757d; 
                            padding: 14px 18px; 
                            border-radius: 6px; 
                            margin-top: 8px;
                            margin-bottom: 12px;
                            color: #333333;
                            font-size: 14px;
                            line-height: 1.6;
                        ">
                            {formatted_pledge}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
            except Exception:
                pass
            
            # 비동의/동의 2지선다
            agreement = st.radio("위 서약 내용에 동의하십니까? *", ["비동의", "동의"], index=0, horizontal=True, key="agreement")

            submit_btn = st.button("신청서 제출", use_container_width=True, type="primary")

            if submit_btn:
                missing_fields = []
                if s_building == "선택하세요":
                    missing_fields.append("생활관명")
                if not s_room.strip():
                    missing_fields.append("호실 번호")
                if not s_id.strip():
                    missing_fields.append("학번")
                if not s_name.strip():
                    missing_fields.append("이름")
                if not s_email.strip():
                    missing_fields.append("이메일")
                if s_item == "선택하세요":
                    missing_fields.append("신청 물품")
                if r_time == "선택하세요":
                    missing_fields.append("대여 희망 시간")

                if missing_fields:
                    st.error(f"⚠️ 다음 필수 항목을 모두 입력하거나 선택해 주세요: {', '.join(missing_fields)}")
                elif agreement != "동의":
                    st.error("⚠️ 서약 내용에 '동의'하셔야 대여 신청이 완료됩니다.")
                elif "@" not in s_email or "." not in s_email:
                    st.error("⚠️ 올바른 이메일 주소 형식을 입력해 주세요.")
                else:
                    desired_str = f"{r_date.strftime('%Y-%m-%d')} {r_time}"
                    exp_ret_str = exp_ret_date.strftime('%Y-%m-%d')
                    try:
                        with st.spinner("신청서를 접수하는 중입니다..."):
                            new_id = sm.add_rental_request(
                                student_id=s_id.strip(),
                                student_name=s_name.strip(),
                                building_name=s_building,
                                room_no=s_room.strip(),
                                item_name=s_item,
                                desired_date=desired_str,
                                expected_return=exp_ret_str,
                                agreement=agreement,
                                email=s_email.strip()
                            )
                            
                        # 1) 사생 접수 확인 이메일 발송
                        student_subj = f"[생활관 자치회] {s_item} 물품 대여 신청이 정상 접수되었습니다."
                        student_body = f"""
                        <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                            <h2 style="color: #1e88e5;">📦 물품 대여 신청 접수 안내</h2>
                            <p><b>{s_name}</b>님, 생활관 자치회 물품 대여 신청이 정상 접수되었습니다.</p>
                            <table style="border-collapse: collapse; width: 100%; max-width: 500px; margin: 15px 0;">
                                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; background: #f9f9f9; width: 120px;"><b>신청 번호</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{new_id}</td></tr>
                                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; background: #f9f9f9;"><b>신청 물품</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{s_item}</td></tr>
                                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; background: #f9f9f9;"><b>소속 호실</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{s_building} {s_room}호</td></tr>
                                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; background: #f9f9f9;"><b>대여 희망일시</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{desired_str}</td></tr>
                                <tr><td style="padding: 8px; border-bottom: 1px solid #ddd; background: #f9f9f9;"><b>반납 예정일</b></td><td style="padding: 8px; border-bottom: 1px solid #ddd;">{exp_ret_str}</td></tr>
                            </table>
                            <p style="color: #666; font-size: 13px;">※ 자치회 검토 후 승인 결과 메일이 추가로 발송됩니다.</p>
                        </div>
                        """
                        sm.send_email_notification(s_email.strip(), student_subj, student_body)

                        # 2) 관리자 신규 접수 알림 이메일 발송
                        if "smtp" in st.secrets and "admin_email" in st.secrets["smtp"]:
                            admin_recv = st.secrets["smtp"]["admin_email"]
                            admin_subj = f"[신규 대여신청] {s_building} {s_name}님 ({s_item})"
                            admin_body = f"""
                            <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                                <h3 style="color: #d32f2f;">🔔 새로운 물품 대여 신청이 접수되었습니다.</h3>
                                <p>관리자 포털에서 승인 또는 반려 처리를 진행해 주세요.</p>
                                <ul>
                                    <li><b>신청자:</b> {s_name} ({s_id} / {s_building} {s_room}호)</li>
                                    <li><b>신청 물품:</b> {s_item}</li>
                                    <li><b>희망 일시:</b> {desired_str}</li>
                                    <li><b>반납 예정:</b> {exp_ret_str}</li>
                                </ul>
                            </div>
                            """
                            sm.send_email_notification(admin_recv, admin_subj, admin_body)

                        st.success(f"신청이 정상 접수되었습니다! (신청번호: {new_id})")
                        st.info("입력하신 이메일로 접수 확인 메일이 발송되었습니다. 생활관 자치회 검토 후 승인 결과가 확정됩니다.")
                    except Exception as err:
                        st.error(f"신청서 저장 중 오류가 발생했습니다: {err}")

# ==========================================
# [탭 3: 결과 조회]
# ==========================================
with tab_query:
    st.subheader("신청 상태 조회(학번)")
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        q_id = st.text_input("학번 입력", placeholder="예: 20241234", label_visibility="collapsed")
    with col_btn:
        search_btn = st.button("🔍 조회하기", use_container_width=True)
    
    if search_btn:
        if not q_id.strip():
            st.warning("⚠️ 학번을 입력한 후 조회 버튼을 눌러주세요.")
        else:
            try:
                my_records = sm.get_rentals_by_student(q_id.strip())
                if not my_records:
                    st.warning(f"학번 [{q_id.strip()}]으로 접수된 대여 신청 내역이 없습니다.")
                else:
                    st.info(f"총 {len(my_records)}건의 신청 내역이 조회되었습니다.")
                    for raw_r in reversed(my_records):
                        r = {str(k).strip(): v for k, v in raw_r.items()}
                        status = r.get("status", "확인 중")
                        item_name = r.get("item_name", "물품")
                        req_time = r.get("req_time", "-")
                        desired_date = r.get("desired_date", "-")
                        confirmed_date = r.get("confirmed_date", "-")
                        exp_ret = r.get("expected_return", "-")
                        admin_memo = r.get("admin_memo", "")

                        with st.expander(f"[{status}] {item_name} (신청일시: {req_time})", expanded=True):
                            st.write(f"- **신청 물품:** {item_name}")
                            st.write(f"- **대여 희망시간:** {desired_date}")
                            st.write(f"- **반납 예정일자:** {exp_ret}")
                            
                            if status == "승인대기":
                                st.info("⏳ 생활관 자치회에서 신청을 검토 중입니다.")
                            elif status == "승인완료":
                                st.success(f"✅ **대여 승인 완료!** 확정 수령일시: **{confirmed_date}**")
                            elif status == "대여중":
                                st.warning("📦 현재 물품을 대여하여 사용 중입니다.")
                            elif status == "반려":
                                st.error("❌ **대여 신청이 반려되었습니다.**")
                                st.write(f"📌 반려 사유: {admin_memo}")
            except Exception as err:
                st.error(f"조회 중 오류가 발생했습니다: {err}")