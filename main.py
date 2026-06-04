
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
        "請假時數": leave_hours,
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
    leave_hours = row["請假時數"]

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

    st.write(df.columns.tolist())
    st.write(holiday_rows)

    
    save_data = pd.DataFrame([{
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
        "大夜班津貼": night_allowance_total,
        "請假扣款": total_leave_deduct,
        "勞保": labor_insurance,
        "健保": health_insurance,
        "居留證": arc_fee,
        "仲介費": agency_fee,
        "體檢費": medical_fee,
        "所得稅": income_tax,
        "應領": base_salary + total_ot_pay + night_allowance_total,
        "實發薪資": final_salary
    }])

    save_data = save_salary_record(save_data)

    st.write("目前總表筆數：", len(save_data))
    st.success("薪資資料已儲存成功！")

    group_1 = [
    "邱是傑",
    "阮功聰",
    "阮文善",
    "阮氏越",
    "陽功福",
    "阮庭香",
    "嚴鄧新",
    "阮進當",
]

group_2 = [
    "阮氏環",
    "阮氏垂玲",
    "黎文英",
    "周氏春年",
    "阮氏草兒",
]

group_3 = [
    "杜氏莊",
    "阮氏藍",
    "范玉遍",
    "陳文誠",
    "廖氏清心",
    "黃文雄",
    "范氏玉",
    "阮氏鶯",
    "陳氏蓮",
    "陳氏璧玉",
    "阮德倫",
    "范玉成",
    "阮氏演",
    "黃強雄",
    "裴德善",
]

def get_group(employee_name):
    if employee_name in group_1:
        return "巴恩斯-第一組"
    elif employee_name in group_2:
        return "巴恩斯-第二組"
    elif employee_name in group_3:
        return "巴恩斯-第三組"
    else:
        return "未分組"
    group_1 = [
    "邱是傑",
    "阮功聰",
    "阮文善",
    "阮氏越",
    "陽功福",
    "阮庭香",
    "嚴鄧新",
    "阮進當",
]

group_2 = [
    "阮氏環",
    "阮氏垂玲",
    "黎文英",
    "周氏春年",
    "阮氏草兒",
]

group_3 = [
    "杜氏莊",
    "阮氏藍",
    "范玉遍",
    "陳文誠",
    "廖氏清心",
    "黃文雄",
    "范氏玉",
    "阮氏鶯",
    "陳氏蓮",
    "陳氏璧玉",
    "阮德倫",
    "范玉成",
    "阮氏演",
    "黃強雄",
    "裴德善",
]

def get_group(employee_name):
    if employee_name in group_1:
        return "巴恩斯-第一組"
    elif employee_name in group_2:
        return "巴恩斯-第二組"
    elif employee_name in group_3:
        return "巴恩斯-第三組"
    else:
        return "未分組"
group_1 = [
    "邱是傑",
    "阮功聰",
    "阮文善",
    "阮氏越",
    "陽功福",
    "阮庭香",
    "嚴鄧新",
    "阮進當",
]

group_2 = [
    "阮氏環",
    "阮氏垂玲",
    "黎文英",
    "周氏春年",
    "阮氏草兒",
]

group_3 = [
    "杜氏莊",
    "阮氏藍",
    "范玉遍",
    "陳文誠",
    "廖氏清心",
    "黃文雄",
    "范氏玉",
    "阮氏鶯",
    "陳氏蓮",
    "陳氏璧玉",
    "阮德倫",
    "范玉成",
    "阮氏演",
    "黃強雄",
    "裴德善",
]
# ===== 巴恩斯分組 =====

group_1 = [
    "邱是傑",
    "阮功聰",
    "阮文善",
    "阮氏越",
    "陽功福",
    "阮庭香",
    "嚴鄧新",
    "阮進當"
]

group_2 = [
    "阮氏環",
    "阮氏垂玲",
    "黎文英",
    "周氏春年",
    "阮氏草兒"
]

group_3 = [
    "杜氏莊",
    "阮氏藍",
    "范玉遍",
    "陳文誠",
    "廖氏清心",
    "黃文雄",
    "范氏玉",
    "阮氏鶯",
    "陳氏蓮",
    "陳氏璧玉",
    "阮德倫",
    "范玉成",
    "阮氏演",
    "黃強雄",
    "裴德善"
]

def get_group(employee_name):
    if employee_name in group_1:
        return "巴恩斯-第一組"
    elif employee_name in group_2:
        return "巴恩斯-第二組"
    elif employee_name in group_3:
        return "巴恩斯-第三組"
    else:
        return "未分組"


# ===== 所有員工薪資總表 =====

st.subheader("所有員工薪資總表")

history_df = read_salary_records()
history_df.columns = history_df.columns.astype(str).str.strip()


if len(history_df) > 0:

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
        ["全部"] + sorted(history_df["年月"].astype(str).unique().tolist())
    )

    summary_df = history_df.copy()

    if unit_filter != "全部":
        summary_df = summary_df[
            summary_df["單位"] == unit_filter
        ]

    if group_filter != "全部":
        summary_df = summary_df[
            summary_df["分組"] == group_filter
        ]

    if month_filter != "全部":
        summary_df = summary_df[
            summary_df["年月"].astype(str) == month_filter
        ]
    st.write("history_df筆數：", len(history_df))
    st.write("summary_df筆數：", len(summary_df))
    st.write(summary_df[["年月", "姓名", "單位", "分組"]])
    
    formatted_rows = []
formatted_rows = []

for _, row in summary_df.iterrows():
    total_ot = float(row.get("加班總時數", row.get("加班時數", 0)) or 0)

    holiday_ot = float(row.get("國定假日總時數", 0) or 0)

    holiday_pay = float(row.get("國定假日加班費", 0) or 0)

    

    normal_ot = max(total_ot - holiday_ot, 0)
    normal_pay = row.get("加班費", 0) - holiday_pay

    normal_under_46 = min(normal_ot, 46)
    normal_over_46 = max(normal_ot - 46, 0)

    if total_ot > 46:
        holiday_under_46 = 0
        holiday_under_46_pay = 0
        holiday_over_46 = holiday_ot
        holiday_over_46_pay = holiday_pay
    else:
        holiday_under_46 = holiday_ot
        holiday_under_46_pay = holiday_pay
        holiday_over_46 = 0
        holiday_over_46_pay = 0

    monthly_salary = float(row.get("月薪", row.get("底薪", row.get("基本薪資", 0))) or 0)
    hourly_wage = monthly_salary / 30 / 8

    normal_over_46_pay = round(normal_over_46 * hourly_wage * 1.67)
    normal_under_46_pay = normal_pay - normal_over_46_pay


    other_deduct = (
        row["居留證"]
        + row["仲介費"]
        + row["體檢費"]
        + row["所得稅"]
    )

    total_deduct = (
        row["請假扣款"]
        + row["勞保"]
        + row["健保"]
        + other_deduct
    )

    one_row = {
        "年月": row["年月"],
        "姓名": row["姓名"],
        "單位": row["單位"],
        "分組": row["分組"],
        "月薪": monthly_salary,
        "46小時內加班時數": normal_under_46,
        "46小時內加班費": normal_under_46_pay,
        "46小時內國定假日加班時數": holiday_under_46,
        "46小時內國定假日加班費": holiday_under_46_pay,
        "超出46小時加班時數": normal_over_46,
        "超出46小時加班費": normal_over_46_pay,
        "超出46小時國定假日加班時數": holiday_over_46,
        "超出46小時國定假日加班費": holiday_over_46_pay,
        "加班總時數": total_ot,
        "加班費總計": row["加班費"],
        "大夜班津貼": row["大夜班津貼"],
        "請假扣款": row["請假扣款"],
        "勞保": row["勞保"],
        "健保": row["健保"],
        "其他扣款": other_deduct,
        "扣款總計": total_deduct,
        "應領": row["應領"],
        "實發薪資": row["實發薪資"]
    }  

    formatted_rows.append(one_row)
    
formatted_df = pd.DataFrame(formatted_rows)
    

st.table(formatted_df)

# 下載薪資總表 Excel
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

# 簡化版總表
st.subheader("簡化版總表")

simple_cols = [
    "年月", "姓名", "單位", "分組", "月薪",

    "加班總時數",
    "加班費總計",
    
    "國定假日總時數",
    "國定假日加班費",

    "大夜班津貼",
    
    "請假扣款",
    "勞保",
    "健保",
    "其他扣款",
    "扣款總計",
    "應領",
    "實發薪資"
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




# 下載完整薪資總表 Excel
complex_excel = "complex_salary_summary.xlsx"
formatted_df.to_excel(complex_excel, index=False)

with open(complex_excel, "rb") as file:
    st.download_button(
        label="下載薪資總表 Excel",
        data=file,
        file_name="薪資總表.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_complex_salary_final"
    )


# 刪除總表紀錄
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

        new_data = history_df.drop(index=selected_index)
        new_data = new_data.reset_index(drop=True)

        sheet.clear()

        if len(new_data) > 0:
            sheet.update(
                [new_data.columns.tolist()] + new_data.values.tolist()
            )

        st.success("已刪除紀錄")
        st.rerun()
else:
    st.info("目前還沒有薪資紀錄，請先儲存薪資資料。")
