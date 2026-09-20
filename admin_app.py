import streamlit as st
import streamlit_authenticator as stauth
import sheet_manager as sm

st.set_page_config(
    page_title="생활관 자치회 물품 대여 관리자 포털",
    page_icon="🔐",
    layout="wide"
)

# 1. 관리자 인증 설정
hasher = stauth.Hasher()
hashed_pw_admin1 = hasher.hash("admin1234")
hashed_pw_admin2 = hasher.hash("master5678")

credentials = {
    "usernames": {
        "admin1": {
            "name": "생활관 자치회원1",
            "password": hashed_pw_admin1,
            "email": "admin1@dormitory.com"
        },
        "admin2": {
            "name": "생활관 자치회원2",
            "password": hashed_pw_admin2,
            "email": "master@dormitory.com"
        }
    }
}

authenticator = stauth.Authenticate(
    credentials,
    cookie_name="dorm_admin_auth_cookie",
    key="dorm_super_secret_cookie_key_2026",
    cookie_expiry_days=1
)

authenticator.login(location="main")

if st.session_state.get("authentication_status") is False:
    st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("🔒 생활관 자치회 관리자 전용 포털입니다. 로그인 정보를 입력해주세요.")
    st.stop()

# 2. 관리자 메인 업무 화면
with st.sidebar:
    st.write(f"👤 접속 관리자: **{st.session_state.get('name')}**님")
    authenticator.logout(button_name="로그아웃", location="sidebar")

st.title("🏢 생활관 자치회 물품 대여 관리 센터")
st.caption("실시간 승인·반려 및 물품 반납 관리 대시보드")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["🔔 승인 / 반려 대기", "📦 물품 전달 및 반납 관리", "📊 전체 내역"])

all_rentals = sm.get_all_rentals()

# [탭 1: 승인 / 반려 처리]
with tab1:
    st.subheader("신규 대여 신청 검토")
    pending = [r for r in all_rentals if r.get("status") == "승인대기"]
    
    if not pending:
        st.info("현재 대기 중인 신청 건이 없습니다.")
    else:
        for idx, r in enumerate(pending):
            rental_id = r.get("rental_id", "")
            item_name = r.get("item_name", "물품")
            student_name = r.get("student_name", "미상")
            student_id = r.get("student_id", "-")
            building_name = r.get("building_name", "")
            room_no = r.get("room_no", "-")
            req_time = r.get("req_time", "-")
            
            location_info = f"{building_name} {room_no}호" if building_name else f"{room_no}호"
            
            # 관생이 입력한 대여 희망 날짜 + 시간
            desired_date = r.get("desired_date", "").strip()
            display_desired = desired_date if desired_date else "-"

            with st.container(border=True):
                col_info, col_action = st.columns([1.1, 1.9])
                with col_info:
                    st.markdown(f"**#{idx+1} {item_name}**")
                    st.write(f"- 신청자: **{student_name}** ({student_id})")
                    st.write(f"- 소속: **{location_info}**")
                    st.write(f"- 신청접수시각: {req_time}")
                    st.write(f"- 관생 희망일시: `{display_desired}`")
                
                with col_action:
                    # 관리자가 일시를 수정할 수 있는 입력란 (관생 입력값이 기본 세팅)
                    edit_desired = st.text_input(
                        "대여 희망일시 (관리자 수정 가능)",
                        value=display_desired,
                        key=f"edit_desired_{rental_id}"
                    )
                    c_date = st.text_input(
                        "확정 대여일시 안내 문구", 
                        value=f"{edit_desired} 생활관 자치회실 방문 수령", 
                        key=f"c_{rental_id}"
                    )
                    c_memo = st.text_input(
                        "관생 안내 메모 / 반려 사유", 
                        placeholder="예: 시간 준수 요망", 
                        key=f"m_{rental_id}"
                    )
                    
                    btn_col1, btn_col2, _ = st.columns([1, 1, 1.5])
                    with btn_col1:
                        if st.button("🟢 승인", key=f"app_{rental_id}", use_container_width=True):
                            with st.spinner("승인 처리 중..."):
                                success = sm.approve_rental(
                                    rental_id=rental_id,
                                    item_name=item_name,
                                    confirmed_date=c_date,
                                    admin_memo=c_memo,
                                    updated_desired_date=edit_desired
                                )
                            if success:
                                st.toast(f"{student_name}님의 신청이 승인되었습니다.", icon="✅")
                                st.rerun()
                            else:
                                st.error("승인 처리에 실패했습니다. 재고를 확인해 주세요.")
                    with btn_col2:
                        if st.button("🔴 반려", key=f"rej_{rental_id}", use_container_width=True):
                            with st.spinner("반려 처리 중..."):
                                sm.reject_rental(
                                    rental_id=rental_id,
                                    reject_reason=c_memo if c_memo else "생활관 자치회 사정으로 반려"
                                )
                            st.toast("신청이 반려되었습니다.", icon="❌")
                            st.rerun()

# [탭 2: 수령 및 반납 처리]
with tab2:
    st.subheader("1. 물품 전달 처리 (승인완료 $\\rightarrow$ 대여중)")
    approved = [r for r in all_rentals if r.get("status") == "승인완료"]
    if not approved:
        st.caption("수령 대기 건이 없습니다.")
    else:
        for r in approved:
            rental_id = r.get("rental_id", "")
            item_name = r.get("item_name", "물품")
            student_name = r.get("student_name", "미상")
            student_id = r.get("student_id", "-")
            confirmed_date = r.get("confirmed_date", "-")

            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"**{item_name}** | {student_name} ({student_id})")
                c2.write(f"수령 약속: {confirmed_date}")
                if c3.button("물품 인출 완료", key=f"take_{rental_id}", use_container_width=True):
                    with st.spinner("처리 중..."):
                        sm.start_rental(rental_id)
                    st.rerun()

    st.markdown("---")
    st.subheader("2. 물품 반납 처리 (대여중 $\\rightarrow$ 반납완료)")
    renting = [r for r in all_rentals if r.get("status") == "대여중"]
    if not renting:
        st.caption("현재 대여 중인 물품이 없습니다.")
    else:
        for r in renting:
            rental_id = r.get("rental_id", "")
            item_name = r.get("item_name", "물품")
            student_name = r.get("student_name", "미상")
            building_name = r.get("building_name", "")
            room_no = r.get("room_no", "-")
            location_info = f"{building_name} {room_no}호" if building_name else f"{room_no}호"
            confirmed_date = r.get("confirmed_date", "-")

            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"**{item_name}** | {student_name} ({location_info})")
                c2.write(f"대여 일시: {confirmed_date}")
                if c3.button("반납 완료", key=f"ret_{rental_id}", use_container_width=True):
                    with st.spinner("반납 처리 중..."):
                        sm.complete_return(rental_id, item_name)
                    st.toast(f"{item_name} 반납이 정상 처리되었습니다.", icon="🏁")
                    st.rerun()

# [탭 3: 전체 내역]
with tab3:
    st.subheader("전체 대여 이력")
    st.dataframe(all_rentals, use_container_width=True)