import gspread

# 1. 서비스 계정 인증
gc = gspread.service_account(filename="service_account.json")

# 2. 구글 스프레드시트 열기
spreadsheet = gc.open("기숙사_물품대여_DB")

# 3. Items 시트 데이터 읽기
items_sheet = spreadsheet.worksheet("Items")
data = items_sheet.get_all_records()

print("✅ 구글 시트 연결 성공!")
print("조회된 물품 데이터:", data)