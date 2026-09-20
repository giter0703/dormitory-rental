import gspread
from datetime import datetime

# 구글 스프레드시트 키값 입력
SPREADSHEET_KEY = "1kC6zFlFXRdgPYP5_MX_L8N9gDIokx2BHrCqTqn7qrGg"
JSON_KEY_FILE = "service_account.json"

def get_db_client():
    gc = gspread.service_account(filename=JSON_KEY_FILE)
    sh = gc.open_by_key(SPREADSHEET_KEY)
    items_sheet = sh.worksheet("Items")
    rentals_sheet = sh.worksheet("Rentals")
    return items_sheet, rentals_sheet

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
            items_sheet.update_cell(idx, 4, new_qty)  # D열: available_qty
            return True
    return False

# ----------------- 대여(Rentals) -----------------
def get_all_rentals():
    """모든 대여 내역을 시트 열 순서(G열: desired_date) 기반으로 안전하게 파싱"""
    _, rentals_sheet = get_db_client()
    rows = rentals_sheet.get_all_values()
    if not rows or len(rows) <= 1:
        return []
    
    # 2행부터 실제 데이터 파싱
    records = []
    for r in rows[1:]:
        # 데이터가 부족한 행 방어 (최소 11열 확보)
        while len(r) < 11:
            r.append("")
            
        record = {
            "rental_id": r[0].strip(),
            "student_id": r[1].strip(),
            "student_name": r[2].strip(),
            "room_no": r[3].strip(),
            "item_name": r[4].strip(),
            "req_time": r[5].strip(),
            "desired_date": r[6].strip(),      # G열 (대여 희망 날짜 및 시간)
            "confirmed_date": r[7].strip(),    # H열 (확정 일시)
            "status": r[8].strip(),            # I열 (대여 상태)
            "admin_memo": r[9].strip(),        # J열 (관리자 메모)
            "return_time": r[10].strip()       # K열 (반납 시간)
        }
        if record["rental_id"]:
            records.append(record)
            
    return records

def add_rental_request(student_id, student_name, room_no, item_name, desired_date):
    """사생의 신규 대여 신청 등록"""
    _, rentals_sheet = get_db_client()
    rental_id = f"R{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    req_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # A~K열 (총 11개) 순서대로 배치
    new_row = [
        str(rental_id),          # A: rental_id
        str(student_id),         # B: student_id
        str(student_name),       # C: student_name
        str(room_no),            # D: room_no
        str(item_name),          # E: item_name
        str(req_time),           # F: req_time
        str(desired_date),       # G: desired_date (희망일시)
        "",                      # H: confirmed_date
        "승인대기",                # I: status
        "",                      # J: admin_memo
        ""                       # K: return_time
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
                rentals_sheet.update_cell(idx, 7, str(updated_desired_date))  # G열: desired_date
            rentals_sheet.update_cell(idx, 8, str(confirmed_date))           # H열: confirmed_date
            rentals_sheet.update_cell(idx, 9, "승인완료")                      # I열: status
            rentals_sheet.update_cell(idx, 10, str(admin_memo))              # J열: admin_memo
            
            # 재고 차감 (-1)
            update_item_available_qty(item_name, -1)
            return True
    return False

def reject_rental(rental_id, reject_reason):
    _, rentals_sheet = get_db_client()
    records = rentals_sheet.get_all_records()
    for idx, r in enumerate(records, start=2):
        clean_r = {str(k).strip(): v for k, v in r.items()}
        if str(clean_r.get("rental_id")) == str(rental_id):
            rentals_sheet.update_cell(idx, 9, "반려")                          # I열: status
            rentals_sheet.update_cell(idx, 10, str(reject_reason))           # J열: admin_memo
            return True
    return False

def start_rental(rental_id):
    _, rentals_sheet = get_db_client()
    records = rentals_sheet.get_all_records()
    for idx, r in enumerate(records, start=2):
        clean_r = {str(k).strip(): v for k, v in r.items()}
        if str(clean_r.get("rental_id")) == str(rental_id):
            rentals_sheet.update_cell(idx, 9, "대여중")                        # I열: status
            return True
    return False

def complete_return(rental_id, item_name):
    _, rentals_sheet = get_db_client()
    records = rentals_sheet.get_all_records()
    return_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for idx, r in enumerate(records, start=2):
        clean_r = {str(k).strip(): v for k, v in r.items()}
        if str(clean_r.get("rental_id")) == str(rental_id):
            rentals_sheet.update_cell(idx, 9, "반납완료")                      # I열: status
            rentals_sheet.update_cell(idx, 11, return_time)                  # K열: return_time
            # 재고 복구 (+1)
            update_item_available_qty(item_name, +1)
            return True
    return False

def get_rentals_by_student(student_id):
    all_rentals = get_all_rentals()
    return [r for r in all_rentals if str(r.get("student_id")).strip() == str(student_id).strip()]

def get_notice():
    """사감실 공지사항 텍스트 조회 (Notice 시트 A2 셀)"""
    try:
        gc = gspread.service_account(filename=JSON_KEY_FILE)
        sh = gc.open_by_key(SPREADSHEET_KEY)
        notice_sheet = sh.worksheet("Notice")
        notice_val = notice_sheet.acell("A2").value
        return notice_val if notice_val else ""
    except Exception:
        return "물품 대여 후 이용 시간을 준수해 주시고, 파손 및 분실에 유의해 주세요."