import streamlit as st
import gspread
import json
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SPREADSHEET_KEY = "1kC6zFlFXRdgPYP5_MX_L8N9gDIokx2BHrCqTqn7qrGg"
JSON_KEY_FILE = "service_account.json"

def get_sh():
    try:
        if "GCP_SERVICE_ACCOUNT_JSON" in st.secrets:
            creds_dict = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
            gc = gspread.service_account_from_dict(creds_dict)
            return gc.open_by_key(SPREADSHEET_KEY)
        elif "gcp_service_account" in st.secrets:
            creds = dict(st.secrets["gcp_service_account"])
            pkey = creds["private_key"]
            if "\\n" in pkey:
                pkey = pkey.replace("\\n", "\n")
            creds["private_key"] = pkey.strip()
            gc = gspread.service_account_from_dict(creds)
            return gc.open_by_key(SPREADSHEET_KEY)
    except Exception:
        pass

    if os.path.exists(JSON_KEY_FILE):
        gc = gspread.service_account(filename=JSON_KEY_FILE)
        return gc.open_by_key(SPREADSHEET_KEY)
        
    raise FileNotFoundError("인증 정보를 찾을 수 없습니다.")

def get_db_client():
    sh = get_sh()
    items_sheet = sh.worksheet("Items")
    rentals_sheet = sh.worksheet("Rentals")
    return items_sheet, rentals_sheet

# ----------------- 공지사항 & 서약(Notice) -----------------
def get_notice():
    try:
        sh = get_sh()
        notice_sheet = sh.worksheet("Notice")
        notice_val = notice_sheet.acell("A2").value
        return str(notice_val).strip() if notice_val else ""
    except Exception:
        return "물품 대여 후 이용 시간을 준수해 주시고, 파손 및 분실에 유의해 주세요."

def get_pledge():
    """관리자가 작성한 서약 내용 조회 (Notice 시트 B2 셀)"""
    try:
        sh = get_sh()
        notice_sheet = sh.worksheet("Notice")
        pledge_val = notice_sheet.acell("B2").value
        return str(pledge_val).strip() if pledge_val else ""
    except Exception:
        return "본인은 생활관 물품 대여 규정을 숙지하였으며, 물품 훼손 및 분실 시 전적으로 변상할 것을 서약합니다."

# ----------------- 물품(Items) -----------------
def get_all_items():
    items_sheet, _ = get_db_client()
    return items_sheet.get_all_records()

def update_item_available_qty(item_name, delta):
    items_sheet, _ = get_db_client()
    items = items_sheet.get_all_records()
    for idx, item in enumerate(items, start=2):
        clean_item = {str(k).strip(): v for k, v in item.items()}
        if clean_item.get("item_name") == item_name:
            new_qty = max(0, int(clean_item.get("available_qty", 0)) + delta)
            items_sheet.update_cell(idx, 4, new_qty)
            return True
    return False

# ----------------- 대여(Rentals) -----------------
def get_all_rentals():
    _, rentals_sheet = get_db_client()
    rows = rentals_sheet.get_all_values()
    if not rows or len(rows) <= 1:
        return []
    
    records = []
    for r in rows[1:]:
        while len(r) < 15:
            r.append("")
            
        record = {
            "rental_id": r[0].strip(),
            "student_id": r[1].strip(),
            "student_name": r[2].strip(),
            "room_no": r[3].strip(),
            "item_name": r[4].strip(),
            "req_time": r[5].strip(),
            "desired_date": r[6].strip(),      # G: 대여 희망 일시
            "confirmed_date": r[7].strip(),    # H: 확정 일시
            "status": r[8].strip(),            # I: 대여 상태
            "admin_memo": r[9].strip(),        # J: 관리자 메모
            "return_time": r[10].strip(),      # K: 반납 시간
            "building_name": r[11].strip(),    # L: 생활관명
            "expected_return": r[12].strip(),  # M: 반납 예정 일자
            "agreement": r[13].strip(),        # N: 서약 동의
            "email": r[14].strip()             # O: 이메일
        }
        if record["rental_id"]:
            records.append(record)
            
    return records

def add_rental_request(student_id, student_name, building_name, room_no, item_name, desired_date, expected_return, agreement, email):
    _, rentals_sheet = get_db_client()
    rental_id = f"R{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    req_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # A~O열 (총 15개) 순서대로 배치
    new_row = [
        str(rental_id),          # A
        str(student_id),         # B
        str(student_name),       # C
        str(room_no),            # D
        str(item_name),          # E
        str(req_time),           # F
        str(desired_date),       # G
        "",                      # H: confirmed_date
        "승인대기",                # I: status
        "",                      # J: admin_memo
        "",                      # K: return_time
        str(building_name),      # L
        str(expected_return),    # M
        str(agreement),          # N
        str(email)               # O
    ]
    rentals_sheet.append_row(new_row, value_input_option="USER_ENTERED")
    return rental_id

def approve_rental(rental_id, item_name, confirmed_date, admin_memo="", updated_desired_date=None):
    items_sheet, rentals_sheet = get_db_client()
    records = rentals_sheet.get_all_records()
    
    for idx, r in enumerate(records, start=2):
        clean_r = {str(k).strip(): v for k, v in r.items()}
        if str(clean_r.get("rental_id")) == str(rental_id):
            if updated_desired_date:
                rentals_sheet.update_cell(idx, 7, str(updated_desired_date))
            rentals_sheet.update_cell(idx, 8, str(confirmed_date))
            rentals_sheet.update_cell(idx, 9, "승인완료")
            rentals_sheet.update_cell(idx, 10, str(admin_memo))
            update_item_available_qty(item_name, -1)
            return True
    return False

def reject_rental(rental_id, reject_reason):
    _, rentals_sheet = get_db_client()
    records = rentals_sheet.get_all_records()
    for idx, r in enumerate(records, start=2):
        clean_r = {str(k).strip(): v for k, v in r.items()}
        if str(clean_r.get("rental_id")) == str(rental_id):
            rentals_sheet.update_cell(idx, 9, "반려")
            rentals_sheet.update_cell(idx, 10, str(reject_reason))
            return True
    return False

def start_rental(rental_id):
    _, rentals_sheet = get_db_client()
    records = rentals_sheet.get_all_records()
    for idx, r in enumerate(records, start=2):
        clean_r = {str(k).strip(): v for k, v in r.items()}
        if str(clean_r.get("rental_id")) == str(rental_id):
            rentals_sheet.update_cell(idx, 9, "대여중")
            return True
    return False

def complete_return(rental_id, item_name):
    _, rentals_sheet = get_db_client()
    records = rentals_sheet.get_all_records()
    return_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for idx, r in enumerate(records, start=2):
        clean_r = {str(k).strip(): v for k, v in r.items()}
        if str(clean_r.get("rental_id")) == str(rental_id):
            rentals_sheet.update_cell(idx, 9, "반납완료")
            rentals_sheet.update_cell(idx, 11, return_time)
            update_item_available_qty(item_name, +1)
            return True
    return False

def get_rentals_by_student(student_id):
    all_rentals = get_all_rentals()
    return [r for r in all_rentals if str(r.get("student_id")).strip() == str(student_id).strip()]

# ----------------- 이메일 알림 전송 모듈 -----------------
def send_email_notification(to_email, subject, body_html):
    """사생 및 관리자에게 이메일 알림을 전송하는 함수"""
    try:
        if "smtp" not in st.secrets:
            return False
            
        smtp_conf = st.secrets["smtp"]
        sender_email = smtp_conf.get("sender_email")
        app_password = smtp_conf.get("app_password")
        server = smtp_conf.get("server", "smtp.gmail.com")
        port = int(smtp_conf.get("port", 465))
        
        if not sender_email or not app_password or not to_email:
            return False
            
        msg = MIMEMultipart()
        msg["From"] = f"생활관 자치회 <{sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html", "utf-8"))
        
        with smtplib.SMTP_SSL(server, port, timeout=10) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
            
        return True
    except Exception as e:
        print(f"이메일 발송 중 오류: {e}")
        return False