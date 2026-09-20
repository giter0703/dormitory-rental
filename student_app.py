import streamlit as st
from datetime import datetime, date, time
import sheet_manager as sm

st.set_page_config(
    page_title="자치회 물품 대여 신청 포털",
    page_icon="📦",
    layout="wide"
)

# =========================================================
# [디자인 설정] 안내사항 텍스트 크기 조절 변수 (원하는 크기로 변경 가능)
# 예: "15px"(기본), "17px"(조금 크게), "20px"(매우 크게)
# =========================================================
NOTICE_FONT_SIZE = "16px"
# =========================================================

st.title("📦 자치회 물품 대여 신청")
st.caption("관생 전용 대여 신청 및 승인 결과 확인 포털")

# --- 자치회 안내사항 영역 (글자 크기 조절 및 줄바꿈 지원) ---
try:
    admin_notice = sm.get_notice()
    if admin_notice:
        # 개행 문자를 HTML 줄바꿈 태그로 변환
        formatted_notice = admin_notice.replace("\n", "<br>")
        st.markdown(
            f"""
            <div style="
                background-color: #f0f7ff; 
                border-left: 6px solid #1e88e5; 
                padding: 16px 20px; 
                border-radius: 6px; 
                margin-top: 10px;
                margin-bottom: 20px;
                color: #0d47a1;
                font-size: {NOTICE_FONT_SIZE};
                line-height: 1.6;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            ">
                <div style="font-weight: bold; font-size: calc({NOTICE_FONT_SIZE} + 2px); margin-bottom: 8px;">
                    📢 [물품 대여 관련 중요 안내사항]
                </div>
                {formatted_notice}
            </div>
            """,
            unsafe_allow_html=True
        )
except Exception:
    pass

st.markdown("---")

tab_apply, tab_query = st.tabs(["📋 대여 신청하기", "🔍 내 신청 결과 조회"])

# [탭 1: 대여 신청]
with tab_apply:
    st.subheader("대여 가능 물품 현황")
    
    items = []
    try:
        items = sm.get_all_items()
    except Exception as e:
        st.error("⚠️ 서버와 통신할 수 없습니다. 시트 KEY 설정 및 네트워크 상태를 확인해주세요.")
        st.caption(f"상세 에러 내용: {e}")

    if items:
        cols = st.columns(len(items))
        for idx, item in enumerate(items):
            clean_item = {str(k).strip(): v for k, v in item.items()}
            with cols[idx]:
                name = clean_item.get("item_name", "물품")
                try:
                    avail = int(clean_item.get("available_qty", 0))
                except (ValueError, TypeError):
                    avail = 0
                total = clean_item.get("total_qty", "-")
                loc = clean_item.get("location", "자치회실")

                status_icon = "🟢" if avail > 0 else "🔴"
                st.metric(
                    label=f"{status_icon} {name}",
                    value=f"{avail}개 남음",
                    delta=f"총 {total}개",
                    delta_color="off"
                )
                st.caption(f"보관 위치: {loc}")
    elif not items and "e" not in locals():
        st.info("등록된 물품이 없습니다.")

    st.markdown("---")
    st.subheader("신청서 작성")

    available_names = []
    if items:
        for it in items:
            clean_it = {str(k).strip(): v for k, v in it.items()}
            try:
                if int(clean_it.get("available_qty", 0)) > 0:
                    available_names.append(clean_it.get("item_name", ""))
            except (ValueError, TypeError):
                continue

    if not available_names:
        st.error("현재 대여 가능한 물품이 없습니다.")
    else:
        with st.form("apply_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                s_id = st.text_input("학번", placeholder="예: 20241001", max_chars=10)
                s_name = st.text_input("이름", placeholder="예: 홍길동")
                s_room = st.text_input("호실 번호", placeholder="예: 402호")
            with col2:
                s_item = st.selectbox("신청 물품 선택", available_names)
                r_date = st.date_input("대여 희망 날짜", min_value=date.today(), value=date.today())
                r_time = st.time_input("대여 희망 시간", value=time(17, 30))

            submit_btn = st.form_submit_button("신청서 제출", use_container_width=True)

            if submit_btn:
                if not (s_id.strip() and s_name.strip() and s_room.strip()):
                    st.warning("⚠️ 학번, 이름, 호실을 모두 입력해주세요.")
                else:
                    desired_str = f"{r_date.strftime('%Y-%m-%d')} {r_time.strftime('%H:%M')}"
                    try:
                        with st.spinner("신청서를 접수하는 중입니다..."):
                            new_id = sm.add_rental_request(
                                student_id=s_id.strip(),
                                student_name=s_name.strip(),
                                room_no=s_room.strip(),
                                item_name=s_item,
                                desired_date=desired_str
                            )
                        st.success(f"신청이 정상 접수되었습니다! (신청번호: {new_id})")
                        st.info("관리자 검토 후 승인 결과가 확정됩니다. '내 신청 결과 조회' 탭에서 확인하세요.")
                    except Exception as err:
                        st.error(f"신청서 저장 중 오류가 발생했습니다: {err}")

# [탭 2: 결과 조회]
with tab_query:
    st.subheader("신청 상태 조회")
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
                with st.spinner("신청 내역을 조회하는 중입니다..."):
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
                        admin_memo = r.get("admin_memo", "")
                        return_time = r.get("return_time", "")

                        with st.expander(f"[{status}] {item_name} (신청일시: {req_time})", expanded=True):
                            st.write(f"- **신청 물품:** {item_name}")
                            st.write(f"- **대여 희망시간:** {desired_date}")
                            
                            if status == "승인대기":
                                st.info("⏳ 자치회에서 신청을 검토 중입니다. 잠시만 기다려 주세요.")
                            elif status == "승인완료":
                                st.success(f"✅ **대여 승인 완료!** 확정 수령일시: **{confirmed_date}**")
                                if admin_memo:
                                    st.caption(f"📌 자치회 안내사항: {admin_memo}")
                            elif status == "대여중":
                                st.warning("📦 현재 물품을 대여하여 사용 중입니다. 사용 후 자치회실로 반납해 주세요.")
                            elif status == "반려":
                                st.error("❌ **대여 신청이 반려되었습니다.**")
                                st.write(f"📌 반려 사유: {admin_memo}")
                            elif status == "반납완료":
                                st.write(f"🏁 반납 처리가 완료되었습니다. (반납일시: {return_time})")
            except Exception as err:
                st.error(f"조회 중 오류가 발생했습니다: {err}")