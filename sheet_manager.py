import streamlit as st
import gspread
from datetime import datetime

# 구글 스프레드시트 키값
SPREADSHEET_KEY = "1kC6zFlFXRdgPYP5_MX_L8N9gDIokx2BHrCqTqn7qrGg"
JSON_KEY_FILE = "service_account.json"

def get_db_client():
    # 1. 클라우드 Secrets 환경 우선 확인
    if "gcp_service_account" in st.secrets:
        creds = dict(st.secrets["gcp_service_account"])
        # PEM 줄바꿈 포맷 완벽 대응
        pkey = creds["private_key"]
        if "\\n" in pkey:
            pkey = pkey.replace("\\n", "\n")
        creds["private_key"] = pkey.strip()
        gc = gspread.service_account_from_dict(creds)
    # 2. 로컬 컴퓨터 개발 환경
    else:
        gc = gspread.service_account(filename=JSON_KEY_FILE)
        
    sh = gc.open_by_key(SPREADSHEET_KEY)
    items_sheet = sh.worksheet("Items")
    rentals_sheet = sh.worksheet("Rentals")
    return items_sheet, rentals_sheet