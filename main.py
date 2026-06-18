
import streamlit as st
import pandas as pd
import calendar
from datetime import date
import math
import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle
import gspread
from google.oauth2.service_account import Credentials
import gspread
from google.oauth2.service_account import Credentials
def read_salary_records():
    data = sheet.get_all_records()
    return pd.DataFrame(data) if data else pd.DataFrame()


def save_salary_record(save_data):
    old_data = read_salary_records()

    new_data = pd.concat([old_data, save_data], ignore_index=True)

    # 清掉空值，避免 Google Sheet JSON 錯誤
    new_data = new_data.fillna("")
    new_data = new_data.replace([float("inf"), float("-inf")], "")

    sheet.clear()

    values = [new_data.columns.tolist()] + new_data.astype(str).values.tolist()
    sheet.update(values)

    return new_data

SHEET_ID = st.secrets["SHEET_ID"]

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

gc = gspread.authorize(credentials)

sheet = gc.open_by_key(SHEET_ID).worksheet("salary_records")


pdfmetrics.registerFont(
    TTFont("NotoSans", "NotoSansTC-VariableFont_wght.ttf")
)

st.title("每月薪資計算系統 / Hệ thống tính lương hàng tháng")

employees_df = pd.read_csv("employees.csv", encoding="utf-8")

unit_list = ["全部"] + sorted(employees_df["單位"].dropna().unique().tolist())
selected_unit = st.selectbox("選擇單位 / Chọn bộ phận", unit_list)

if selected_unit == "全部":
    filtered_employees = employees_df
else:
    filtered_employees = employees_df[employees_df["單位"] == selected_unit]

employee_names = [""] + filtered_employees["姓名"].tolist()

name = st.selectbox(
    "員工姓名 / Họ tên nhân viên",
    employee_names,
    key="employee_name"
)

if st.button("清除上一位資料 / Xóa dữ liệu"):
    for i in range(1, 32):
        st.session_state[f"ot_{i}"] = 0.0
        st.session_state[f"leave_{i}"] = "無 / Không"
        st.session_state[f"leave_hours_{i}"] = 0.0
        st.session_state[f"holiday_{i}"] = False
        st.session_state[f"night_{i}"] = 0

    st.rerun()

    
if "reset_count" not in st.session_state:
    st.session_state.reset_count = 0

reset_key = st.session_state.reset_count

year = st.number_input("年份 / Năm", min_value=2024, max_value=2035, value=2026)
month = st.number_input("月份 / Tháng", min_value=1, max_value=12, value=5)

if name == "":
    st.warning("請先選擇員工 / Vui lòng chọn nhân viên")
    st.stop()

emp = employees_df[employees_df["姓名"] == name].iloc[0]
company = emp["單位"]

def safe_int(value, default=0):
    if pd.isna(value) or value == "":
        return default
    return int(float(value))

base_salary = st.number_input("月薪 / Lương cơ bản", value=safe_int(emp["月薪"]), step=100)
labor_insurance = st.number_input("勞保扣款 / Bảo hiểm lao động", value=safe_int(emp["勞保"]))
health_insurance = st.number_input("健保扣款 / Bảo hiểm y tế", value=safe_int(emp["健保"]))
arc_fee = st.number_input("居留證費用 / Phí thẻ cư trú", value=safe_int(emp["居留證"]))
agency_fee = st.number_input("仲介服務費 / Phí môi giới", value=safe_int(emp["仲介費"]))
medical_fee = st.number_input("體檢費 / Phí khám sức khỏe", value=safe_int(emp["體檢費"]))
income_tax = st.number_input("所得稅扣款 / Thuế thu nhập", value=0)
night_allowance_total = st.number_input("大夜班津貼 / Phụ cấp ca đêm", value=0)

st.info(f"單位 / Đơn vị：{company}")

hourly_wage = base_salary / 30 / 8
daily_wage = base_salary / 30

st.write(f"時薪 / Lương giờ：約 {hourly_wage:.2f} 元")
st.write(f"日薪 / Lương ngày：約 {daily_wage:.0f} 元")

days = calendar.monthrange(year, month)[1]
records = []

weekday_list = [
    "一 / Thứ Hai",
    "二 / Thứ Ba",
    "三 / Thứ Tư",
    "四 / Thứ Năm",
    "五 / Thứ Sáu",
    "六 / Thứ Bảy",
    "日 / Chủ Nhật",
]

leave_options = [
    "無 / Không",
    "事假 / Nghỉ việc riêng",
    "病假 / Nghỉ bệnh",
    "特休 / Nghỉ phép năm",
    "曠職 / Vắng mặt",
]

st.subheader("出勤輸入 / Nhập chấm công")

for d in range(1, days + 1):
    weekday = weekday_list[date(year, month, d).weekday()]
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.write(f"{month}/{d}（{weekday}）")

    with col2:
        overtime = st.number_input(
            f"加班時數 / Giờ tăng ca {d}",
            min_value=0.0,
            max_value=12.0,
            step=0.5,
            key=f"ot_{d}"
        )

    with col3:
        leave = st.selectbox(
            f"請假原因 / Lý do nghỉ {d}",
            leave_options,
            key=f"leave_{d}"
        )

        leave_hours = st.number_input(
            f"請假時數 / Giờ nghỉ {d}",
            min_value=0.0,
            max_value=8.0,
            step=0.5,
            key=f"leave_hours_{d}"
        ) 

    with col4:
        is_holiday = st.checkbox(
            f"國定假日 / Ngày lễ {d}",
            key=f"holiday_{d}"
        )

    records.append({
        "日期 / Ngày": f"{year}/{month}/{d}",
        "星期 / Thứ": weekday,
        "加班時數 / Giờ tăng ca": overtime,
        "請假原因 / Lý do nghỉ": leave,
        "請假時數 / Số giờ nghỉ": leave_hours,
        "國定假日 / Ngày lễ": "是 / Có" if is_holiday else "否 / Không"
    })

df = pd.DataFrame(records)

def calc_normal_ot_pay(hours):
    if hours <= 0:
        return 0
    elif hours <= 2:
        return hours * hourly_wage * 1.34
    else:
        return (2 * hourly_wage * 1.34) + ((hours - 2) * hourly_wage * 1.67)

def calc_holiday_ot_pay(hours):
    if hours <= 0:
        return 0
    if hours <= 8:
        return daily_wage
    extra_hours = hours - 8
    return daily_wage + calc_normal_ot_pay(extra_hours)

def calc_ot_pay(row):
    hours = row["加班時數 / Giờ tăng ca"]
    is_holiday = row["國定假日 / Ngày lễ"] == "是 / Có"

    if is_holiday:
        return calc_holiday_ot_pay(hours)

    return calc_normal_ot_pay(hours)

df["加班費 / Tiền tăng ca"] = df.apply(
    lambda row: math.ceil(calc_ot_pay(row)),
    axis=1
)

def calc_leave_deduct(row):

    leave = row["請假原因 / Lý do nghỉ"]
    leave_hours = row["請假時數 / Số giờ nghỉ"]

    amount = hourly_wage * leave_hours

    if leave == "事假 / Nghỉ việc riêng":
        return amount

    elif leave == "病假 / Nghỉ bệnh":
        return amount * 0.5

    elif leave == "曠職 / Vắng mặt":
        return amount

    else:
        return 0

df["請假扣薪 / Trừ lương nghỉ"] = df.apply(
    lambda row: math.ceil(calc_leave_deduct(row)),
    axis=1
)


total_ot_hours = df["加班時數 / Giờ tăng ca"].sum()
total_ot_pay = df["加班費 / Tiền tăng ca"].sum()
total_leave_deduct = df["請假扣薪 / Trừ lương nghỉ"].sum()

total_other_deduct = (
    labor_insurance
    + health_insurance
    + arc_fee
    + agency_fee
    + medical_fee
    + income_tax
)

final_salary = (
    base_salary
    + total_ot_pay
    + night_allowance_total
    - total_leave_deduct
    - total_other_deduct
)


def to_number(value, default=0):
    try:
        if pd.isna(value) or value == "":
            return default
        return float(value)
    except Exception:
        return default


def split_overtime_by_day(daily_df, monthly_salary):
    """依每日資料拆分：前2小時/後2小時、46小時內/超出46小時、國定假日。"""
    hourly = monthly_salary / 30 / 8 if monthly_salary else 0
    total_ot = to_number(daily_df["加班時數 / Giờ tăng ca"].sum())

    result = {
        "46小時內前2小時時數": 0.0,
        "46小時內後2小時時數": 0.0,
        "46小時內前2小時加班費": 0,
        "46小時內後2小時加班費": 0,
        "46小時內加班時數": 0.0,
        "46小時內加班費": 0,
        "46小時內國定假日加班時數": 0.0,
        "46小時內國定假日加班費": 0,
        "超出46小時前2小時時數": 0.0,
        "超出46小時後2小時時數": 0.0,
        "超出46小時前2小時加班費": 0,
        "超出46小時後2小時加班費": 0,
        "超出46小時加班時數": 0.0,
        "超出46小時加班費": 0,
        "超出46小時國定假日加班時數": 0.0,
        "超出46小時國定假日加班費": 0,
    }

    used_hours = 0.0

    for _, drow in daily_df.iterrows():
        day_ot = to_number(drow.get("加班時數 / Giờ tăng ca", 0))
        day_pay = to_number(drow.get("加班費 / Tiền tăng ca", 0))
        is_holiday = str(drow.get("國定假日 / Ngày lễ", "")).startswith("是")

        if day_ot <= 0:
            continue

        remaining_under46 = max(46 - used_hours, 0)
        put_under46 = min(day_ot, remaining_under46)
        put_over46 = day_ot - put_under46

        if is_holiday:

           under_holiday = min(day_ot, remaining_under46)
           over_holiday = day_ot - under_holiday

            if day_ot > 0:
                under_pay = round(day_pay * under_holiday / day_ot)
            else:
                under_pay = 0

            over_pay = day_pay - under_pay

            result["46小時內國定假日加班時數"] += under_holiday
            result["46小時內國定假日加班費"] += under_pay

            result["超出46小時國定假日加班時數"] += over_holiday
            result["超出46小時國定假日加班費"] += over_pay

            used_hours += day_ot   
        else:
            day_first2 = min(day_ot, 2)
            day_after2 = max(day_ot - 2, 0)

            first2_under = min(day_first2, put_under46)
            first2_over = day_first2 - first2_under

            remaining_put_under46 = put_under46 - first2_under
            after2_under = min(day_after2, remaining_put_under46)
            after2_over = day_after2 - after2_under

            result["46小時內前2小時時數"] += first2_under
            result["46小時內後2小時時數"] += after2_under
            result["超出46小時前2小時時數"] += first2_over
            result["超出46小時後2小時時數"] += after2_over

            result["46小時內前2小時加班費"] += round(first2_under * hourly * 1.34)
            result["46小時內後2小時加班費"] += round(after2_under * hourly * 1.67)
            result["超出46小時前2小時加班費"] += round(first2_over * hourly * 1.34)
            result["超出46小時後2小時加班費"] += round(after2_over * hourly * 1.67)

        used_hours += day_ot

    result["46小時內加班時數"] = result["46小時內前2小時時數"] + result["46小時內後2小時時數"]
    result["46小時內加班費"] = result["46小時內前2小時加班費"] + result["46小時內後2小時加班費"]
    result["超出46小時加班時數"] = result["超出46小時前2小時時數"] + result["超出46小時後2小時時數"]
    result["超出46小時加班費"] = result["超出46小時前2小時加班費"] + result["超出46小時後2小時加班費"]
    result["加班費總計"] = (
        result["46小時內加班費"]
        + result["46小時內國定假日加班費"]
        + result["超出46小時加班費"]
        + result["超出46小時國定假日加班費"]
    )
    return result


def split_from_saved_row(row):
    """總表顯示用：優先讀取已儲存的拆分欄位；舊資料沒有欄位時用總數簡易補值。"""
    split_cols = [
        "46小時內前2小時時數", "46小時內後2小時時數", "46小時內前2小時加班費", "46小時內後2小時加班費",
        "46小時內加班時數", "46小時內加班費", "46小時內國定假日加班時數", "46小時內國定假日加班費",
        "超出46小時前2小時時數", "超出46小時後2小時時數", "超出46小時前2小時加班費", "超出46小時後2小時加班費",
        "超出46小時加班時數", "超出46小時加班費", "超出46小時國定假日加班時數", "超出46小時國定假日加班費", "加班費總計"
    ]
    if any(col in row.index and str(row.get(col, "")) != "" for col in split_cols):
        return {col: to_number(row.get(col, 0)) for col in split_cols}

    total_ot = to_number(row.get("加班總時數", row.get("加班時數", 0)))
    total_pay = to_number(row.get("加班費總計", row.get("加班費", 0)))
    holiday_ot = to_number(row.get("國定假日總時數", 0))
    holiday_pay = to_number(row.get("國定假日加班費", 0))
    normal_ot = max(total_ot - holiday_ot, 0)
    normal_pay = max(total_pay - holiday_pay, 0)

    result = {col: 0 for col in split_cols}
    if total_ot > 46:
        result["超出46小時國定假日加班時數"] = holiday_ot
        result["超出46小時國定假日加班費"] = holiday_pay
    else:
        result["46小時內國定假日加班時數"] = holiday_ot
        result["46小時內國定假日加班費"] = holiday_pay

    result["46小時內加班時數"] = min(normal_ot, 46)
    result["超出46小時加班時數"] = max(normal_ot - 46, 0)
    result["46小時內加班費"] = min(normal_pay, total_pay)
    result["超出46小時加班費"] = max(normal_pay - result["46小時內加班費"], 0)
    result["加班費總計"] = total_pay
    return result

st.subheader("薪資結果 / Kết quả lương")
st.write(f"員工姓名 / Họ tên：{name}")
st.write(f"單位 / Đơn vị：{company}")
st.write(f"月薪 / Lương cơ bản：{base_salary:.0f} 元")
st.write(f"總加班時數 / Tổng giờ tăng ca：{total_ot_hours:.1f} 小時")
st.write(f"加班費 / Tiền tăng ca：{total_ot_pay:.0f} 元")
st.write(f"大夜班津貼 / Phụ cấp ca đêm：{night_allowance_total:.0f} 元")
st.write(f"請假扣薪 / Trừ lương nghỉ phép：{total_leave_deduct:.0f} 元")
st.write(f"勞保扣款 / Bảo hiểm lao động：{labor_insurance:.0f} 元")
st.write(f"健保扣款 / Bảo hiểm y tế：{health_insurance:.0f} 元")
st.write(f"居留證費用 / Phí thẻ cư trú：{arc_fee:.0f} 元")
st.write(f"仲介服務費 / Phí môi giới：{agency_fee:.0f} 元")
st.write(f"體檢費 / Phí khám sức khỏe：{medical_fee:.0f} 元")
st.write(f"所得稅扣款 / Thuế thu nhập：{income_tax:.0f} 元")
st.write(f"扣款合計 / Tổng khấu trừ：{(total_leave_deduct + total_other_deduct):.0f} 元")

st.success(f"實發薪資 / Lương thực lãnh：約 {final_salary:.0f} 元")

st.subheader("明細表 / Bảng chi tiết")
st.table(df)

detail_rows = [
    ["員工姓名 / Họ tên", name],
    ["單位 / Đơn vị", company],
    ["月薪 / Lương cơ bản", base_salary],
    ["總加班時數 / Tổng giờ tăng ca", total_ot_hours],
    ["加班費 / Tiền tăng ca", total_ot_pay],
    ["大夜班津貼 / Phụ cấp ca đêm", night_allowance_total],
    ["請假扣薪 / Trừ lương nghỉ phép", total_leave_deduct],
    ["勞保扣款 / Bảo hiểm lao động", labor_insurance],
    ["健保扣款 / Bảo hiểm y tế", health_insurance],
    ["居留證費用 / Phí thẻ cư trú", arc_fee],
    ["仲介服務費 / Phí môi giới", agency_fee],
    ["體檢費 / Phí khám sức khỏe", medical_fee],
    ["所得稅扣款 / Thuế thu nhập", income_tax],
    ["扣款合計 / Tổng khấu trừ", total_leave_deduct + total_other_deduct],
    ["實發薪資 / Lương thực lãnh", final_salary],
]

excel_file = "salary_result.xlsx"

detail_df = pd.DataFrame(
    detail_rows,
    columns=["項目","內容"]
)

with pd.ExcelWriter(excel_file) as writer:

    # 先寫摘要
    detail_df.to_excel(
        writer,
        sheet_name="薪資明細",
        index=False,
        startrow=0
    )

    # 再寫每日明細
    df.to_excel(
        writer,
        sheet_name="薪資明細",
        index=False,
        startrow=len(detail_df) + 3
    )
    
file_name = f"{name}_薪資明細.xlsx"

with open(excel_file, "rb") as file:
    st.download_button(
        label="下載 Excel / Tải Excel",
        data=file,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

detail_rows = [
    ["員工姓名 / Họ tên", name],
    ["單位 / Đơn vị", company],
    ["月薪 / Lương cơ bản", base_salary],
    ["總加班時數 / Tổng giờ tăng ca", total_ot_hours],
    ["加班費 / Tiền tăng ca", total_ot_pay],
    ["大夜班津貼 / Phụ cấp ca đêm", night_allowance_total],
    ["請假扣薪 / Trừ lương nghỉ phép", total_leave_deduct],
    ["勞保扣款 / Bảo hiểm lao động", labor_insurance],
    ["健保扣款 / Bảo hiểm y tế", health_insurance],
    ["居留證費用 / Phí thẻ cư trú", arc_fee],
    ["仲介服務費 / Phí môi giới", agency_fee],
    ["體檢費 / Phí khám sức khỏe", medical_fee],
    ["所得稅扣款 / Thuế thu nhập", income_tax],
    ["扣款合計 / Tổng khấu trừ", total_leave_deduct + total_other_deduct],
    ["實發薪資 / Lương thực lãnh", final_salary],
]

pdf_file = f"{name}_薪資明細.pdf"

excel_file = "salary_result.xlsx"

detail_df = pd.DataFrame(
    detail_rows,
    columns=["項目","內容"]
)

with pd.ExcelWriter(excel_file) as writer:

    # 先寫摘要
    detail_df.to_excel(
        writer,
        sheet_name="薪資明細",
        index=False,
        startrow=0
    )

    # 再寫每日明細
    df.to_excel(
        writer,
        sheet_name="薪資明細",
        index=False,
        startrow=len(detail_df) + 3
    )

doc = SimpleDocTemplate(
    pdf_file,
    pagesize=landscape(A4),
    rightMargin=5,
    leftMargin=5,
    topMargin=5,
    bottomMargin=5
)

style = ParagraphStyle(
    name="PDFStyle",
    fontName="NotoSans",
    fontSize=5,
    leading=6,
    wordWrap="CJK"
)

table_data = []



page_width, page_height = landscape(A4)
usable_width = page_width - 10

summary_df = pd.DataFrame(detail_rows, columns=["項目", "內容"]).astype(str)
daily_df = df.copy().astype(str)

summary_data = []
summary_data.append([
    Paragraph("項目", style),
    Paragraph("內容", style)
])

for row in summary_df.values.tolist():
    summary_data.append([
        Paragraph(str(row[0]), style),
        Paragraph(str(row[1]), style)
    ])

summary_col_widths = [usable_width * 0.45, usable_width * 0.55]

summary_table = Table(
    summary_data,
    colWidths=summary_col_widths,
    repeatRows=1
)

daily_data = []
daily_data.append([
    Paragraph(str(col), style) for col in daily_df.columns.tolist()
])

for row in daily_df.values.tolist():
    daily_data.append([
        Paragraph(str(cell), style) for cell in row
    ])

daily_col_width = usable_width / len(daily_df.columns)

daily_table = Table(
    daily_data,
    colWidths=[daily_col_width] * len(daily_df.columns),
    repeatRows=1
)

summary_table.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), "NotoSans"),
    ("FONTSIZE", (0, 0), (-1, -1), 6),
    ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]))

daily_table.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), "NotoSans"),
    ("FONTSIZE", (0, 0), (-1, -1), 4),
    ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]))

doc.build([summary_table, daily_table])

with open(pdf_file, "rb") as pdf:
    st.download_button(
        label="下載 PDF / Tải PDF",
        data=pdf,
        file_name=pdf_file,
        mime="application/pdf",
        key=f"download_pdf_{name}"
    )

if st.button("儲存薪資紀錄 / Lưu dữ liệu lương"):
    holiday_col = "國定假日 / Ngày lễ"
    ot_col = "加班時數 / Giờ tăng ca"
    pay_col = "加班費 / Tiền tăng ca"

    holiday_rows = df[df[holiday_col].astype(str).str.contains("是", na=False)]

    holiday_total_hours = holiday_rows[ot_col].sum()
    holiday_total_pay = holiday_rows[pay_col].sum()


    
    split_result = split_overtime_by_day(df, base_salary)
    total_split_ot_pay = split_result["加班費總計"]
    other_deduct_for_save = arc_fee + agency_fee + medical_fee + income_tax
    total_deduct_for_save = total_leave_deduct + labor_insurance + health_insurance + other_deduct_for_save
    should_receive_for_save = base_salary + total_split_ot_pay + night_allowance_total
    final_salary_for_save = should_receive_for_save - total_deduct_for_save

    save_row = {
        "年月": f"{year}-{month:02d}",
        "姓名": name,
        "單位": company,
        "月薪": base_salary,
        "日薪": daily_wage,
        "時薪": hourly_wage,
        "加班時數": total_ot_hours,
        "加班費": total_ot_pay,
        "國定假日總時數": holiday_total_hours,
        "國定假日加班費": holiday_total_pay,
        **split_result,
        "大夜班津貼": night_allowance_total,
        "請假扣款": total_leave_deduct,
        "勞保": labor_insurance,
        "健保": health_insurance,
        "居留證": arc_fee,
        "仲介費": agency_fee,
        "體檢費": medical_fee,
        "所得稅": income_tax,
        "其他扣款": other_deduct_for_save,
        "扣款總計": total_deduct_for_save,
        "應領": round(should_receive_for_save),
        "實發薪資": round(final_salary_for_save)
    }
    save_data = pd.DataFrame([save_row])

    save_data = save_salary_record(save_data)

    st.write("目前總表筆數：", len(save_data))
    st.success("薪資資料已儲存成功！")


# ===== 巴恩斯分組 =====
group_1 = [
    "邱是傑", "阮功聰", "阮文善", "阮氏越", "陽功福", "阮庭香", "嚴鄧新", "阮進當"
]

group_2 = [
    "阮氏環", "阮氏垂玲", "黎文英", "周氏春年", "阮氏草兒"
]

group_3 = [
    "杜氏莊", "阮氏藍", "范玉遍", "陳文誠", "廖氏清心", "黃文雄", "范氏玉", "阮氏鶯",
    "陳氏蓮", "陳氏璧玉", "阮德倫", "范玉成", "阮氏演", "黃強雄", "裴德善"
]

def get_group(employee_name):
    if employee_name in group_1:
        return "巴恩斯-第一組"
    if employee_name in group_2:
        return "巴恩斯-第二組"
    if employee_name in group_3:
        return "巴恩斯-第三組"
    return "未分組"


# ===== 所有員工薪資總表 =====
st.subheader("所有員工薪資總表")

history_df = read_salary_records()

if len(history_df) > 0:
    history_df.columns = history_df.columns.astype(str).str.strip()
    history_df["分組"] = history_df["姓名"].apply(get_group)

    unit_filter = st.selectbox(
        "單位篩選",
        ["全部"] + sorted(history_df["單位"].dropna().unique().tolist()),
        index=0
    )

    group_filter = st.selectbox(
        "分組篩選",
        ["全部", "巴恩斯-第一組", "巴恩斯-第二組", "巴恩斯-第三組", "未分組"],
        index=0
    )

    month_filter = st.selectbox(
        "月份篩選",
        ["全部"] + sorted(history_df["年月"].astype(str).unique().tolist()),
        index=0
    )

    summary_df = history_df.copy()

    if unit_filter != "全部":
        summary_df = summary_df[summary_df["單位"] == unit_filter]

    if group_filter != "全部":
        summary_df = summary_df[summary_df["分組"] == group_filter]

    if month_filter != "全部":
        summary_df = summary_df[summary_df["年月"].astype(str) == month_filter]

    formatted_rows = []

    for _, row in summary_df.iterrows():
        monthly_salary = to_number(row.get("月薪", row.get("底薪", row.get("基本薪資", 0))))
        split_result = split_from_saved_row(row)

        total_ot = to_number(row.get("加班總時數", row.get("加班時數", 0)))
        if total_ot == 0:
            total_ot = (
                split_result["46小時內加班時數"]
                + split_result["46小時內國定假日加班時數"]
                + split_result["超出46小時加班時數"]
                + split_result["超出46小時國定假日加班時數"]
            )

        ot_pay_total = split_result.get("加班費總計", to_number(row.get("加班費", 0)))
        night_pay = to_number(row.get("大夜班津貼", 0))
        leave_deduct = to_number(row.get("請假扣款", 0))
        labor = to_number(row.get("勞保", 0))
        health = to_number(row.get("健保", 0))
        arc = to_number(row.get("居留證", 0))
        agency = to_number(row.get("仲介費", 0))
        medical = to_number(row.get("體檢費", 0))
        tax = to_number(row.get("所得稅", 0))
        other_deduct = arc + agency + medical + tax
        total_deduct = leave_deduct + labor + health + other_deduct
        should_receive = monthly_salary + ot_pay_total + night_pay
        final_pay = should_receive - total_deduct

        one_row = {
            "年月": row.get("年月", ""),
            "姓名": row.get("姓名", ""),
            "單位": row.get("單位", ""),
            "分組": row.get("分組", ""),
            "月薪": monthly_salary,
            **split_result,
            "加班總時數": total_ot,
            "加班費總計": ot_pay_total,
            "大夜班津貼": night_pay,
            "請假扣款": leave_deduct,
            "勞保": labor,
            "健保": health,
            "居留證": arc,
            "仲介費": agency,
            "體檢費": medical,
            "所得稅": tax,
            "其他扣款": other_deduct,
            "扣款總計": total_deduct,
            "應領": round(should_receive),
            "實發薪資": round(final_pay),
        }
        formatted_rows.append(one_row)

    formatted_df = pd.DataFrame(formatted_rows)

    st.table(formatted_df)

    complex_excel = "薪資總表.xlsx"
    formatted_df.to_excel(complex_excel, index=False)

    with open(complex_excel, "rb") as file:
        st.download_button(
            label="下載薪資總表 Excel",
            data=file,
            file_name="薪資總表.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_complex_salary"
        )

    # ===== 簡化版總表 =====
    st.subheader("簡化版總表")

    simple_cols = [
        "年月", "姓名", "單位", "分組", "月薪",
        "加班總時數", "加班費總計",
        "大夜班津貼", "請假扣款", "勞保", "健保",
        "其他扣款", "扣款總計", "應領", "實發薪資"
    ]

    simple_cols = [c for c in simple_cols if c in formatted_df.columns]
    simple_df = formatted_df[simple_cols]

    st.table(simple_df)

    simple_excel = "簡化版薪資總表.xlsx"
    simple_df.to_excel(simple_excel, index=False)

    with open(simple_excel, "rb") as file:
        st.download_button(
            label="下載簡化版總表 Excel",
            data=file,
            file_name="簡化版薪資總表.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_simple_salary"
        )

    # ===== 刪除總表紀錄 =====
    st.subheader("刪除總表紀錄")

    delete_options = [
        f"{idx} | {row['年月']} | {row['姓名']} | 實發 {row['實發薪資']}"
        for idx, row in summary_df.iterrows()
    ]

    if len(delete_options) > 0:
        delete_choice = st.selectbox(
            "選擇要刪除的紀錄",
            delete_options,
            key="delete_salary_record_select"
        )

        if st.button("刪除選取紀錄", key="delete_salary_record_btn"):
            selected_index = int(delete_choice.split("|")[0].strip())
            new_data = history_df.drop(index=selected_index).reset_index(drop=True)

            sheet.clear()
            if len(new_data) > 0:
                new_data = new_data.fillna("").replace([float("inf"), float("-inf")], "")
                sheet.update([new_data.columns.tolist()] + new_data.astype(str).values.tolist())

            st.success("已刪除紀錄")
            st.rerun()
else:
    st.info("目前還沒有薪資紀錄，請先儲存薪資資料。")
