
import streamlit as st
import pandas as pd
import calendar
from datetime import date
import math
import os
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(
    TTFont("NotoSans", "NotoSansTC-Regular.ttf")
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
name = st.selectbox("員工姓名 / Họ tên nhân viên", employee_names)

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

def calc_leave_deduct(leave):
    if leave == "事假 / Nghỉ việc riêng":
        return daily_wage
    elif leave == "病假 / Nghỉ bệnh":
        return daily_wage / 2
    elif leave == "曠職 / Vắng mặt":
        return daily_wage
    else:
        return 0

df["請假扣薪 / Trừ lương nghỉ"] = df["請假原因 / Lý do nghỉ"].apply(
    lambda x: math.ceil(calc_leave_deduct(x))
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

excel_file = "salary_result.xlsx"
df.to_excel(excel_file, index=False)

file_name = f"{name}_薪資明細.xlsx"

with open(excel_file, "rb") as file:
    st.download_button(
        label="下載 Excel / Tải Excel",
        data=file,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

pdf_file = f"{name}_薪資明細.pdf"

pdfmetrics.registerFont(TTFont("NotoSans", "NotoSansHK-Regular.ttf"))

pdf_data = df.copy().astype(str)

doc = SimpleDocTemplate(
    pdf_file,
    pagesize=landscape(A4),
    rightMargin=10,
    leftMargin=10,
    topMargin=10,
    bottomMargin=10
)

table_data = [pdf_data.columns.tolist()] + pdf_data.values.tolist()

table = Table(table_data, repeatRows=1)

table.setStyle(TableStyle([
   ("FONTNAME", (0, 0), (-1, -1), "NotoSans"),
    ("FONTSIZE", (0, 0), (-1, -1), 6),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]))

doc.build([table])

with open(pdf_file, "rb") as pdf:
    st.download_button(
        label="下載 PDF / Tải PDF",
        data=pdf,
        file_name=pdf_file,
        mime="application/pdf",
        key=f"download_pdf_{name}"
    )

if st.button("儲存薪資紀錄 / Lưu dữ liệu lương"):
    save_data = pd.DataFrame([{
        "年月": f"{year}-{month:02d}",
        "姓名": name,
        "單位": company,
        "月薪": base_salary,
        "日薪": daily_wage,
        "時薪": hourly_wage,
        "加班時數": total_ot_hours,
        "加班費": total_ot_pay,
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

    save_file = "salary_records.csv"

    if os.path.exists(save_file):
        old_data = pd.read_csv(save_file)
        save_data = pd.concat([old_data, save_data], ignore_index=True)

    save_data.to_csv(save_file, index=False, encoding="utf-8-sig")
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

if os.path.exists("salary_records.csv"):

    history_df = pd.read_csv(
        "salary_records.csv",
        encoding="utf-8-sig"
    )

    history_df["分組"] = history_df["姓名"].apply(get_group)

    unit_filter = st.selectbox(
        "單位篩選",
        ["全部"] + sorted(history_df["單位"].dropna().unique().tolist())
    )

    group_filter = st.selectbox(
        "分組篩選",
        ["全部", "巴恩斯-第一組", "巴恩斯-第二組", "巴恩斯-第三組", "未分組"]
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

    formatted_rows = []

    for _, row in summary_df.iterrows():

        total_ot = row["加班時數"]

holiday_ot = 0
if "固定假日加班時數" in summary_df.columns:
    holiday_ot = row["固定假日加班時數"]

normal_ot = max(total_ot - holiday_ot, 0)

normal_under_46 = min(normal_ot, 46)
normal_over_46 = max(normal_ot - 46, 0)

holiday_under_46 = min(holiday_ot, 46)
holiday_over_46 = max(holiday_ot - 46, 0)

hourly_wage = row["月薪"] / 30 / 8

normal_over_46_pay = round(normal_over_46 * hourly_wage * 1.67)

holiday_under_46_pay = 0
holiday_over_46_pay = 0

normal_under_46_pay = row["加班費"] - normal_over_46_pay - holiday_under_46_pay - holiday_over_46_pay

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

formatted_rows.append({
    "年月": row["年月"],
    "姓名": row["姓名"],
    "單位": row["單位"],
    "分組": row["分組"],
    "月薪": row["月薪"],

    "46小時內加班時數": normal_under_46,
    "46小時內加班費": normal_under_46_pay,

    "46小時內國定假日時數": holiday_under_46,
    "46小時內國定假日加班費": holiday_under_46_pay,

    "超出46小時加班時數": normal_over_46,
    "超出46小時加班費": normal_over_46_pay,

    "超出46小時國定假日時數": holiday_over_46,
    "超出46小時國定假日加班費": holiday_over_46_pay,

    "國定假日總時數": holiday_under_46 + holiday_over_46,

    "國定假日加班費":holiday_under_46_pay + holiday_over_46_pay,
     

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
})

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

simple_cols = [
    "年月", "姓名", "單位", "分組", "月薪",
    "加班總時數", "加班費總計",
    "46小時內固定假日時數", "46小時內固定假日加班費",
    "超出46小時固定假日時數", "超出46小時固定假日加班費",
    "大夜班津貼",
    "請假扣款", "勞保", "健保", "居留證",
    "仲介費", "體檢費", "所得稅",
    "應領", "實發薪資"
]

simple_cols = [c for c in simple_cols if c in formatted_df.columns]
simple_df = formatted_df[simple_cols]
st.table(simple_df)

simple_excel = "simple_salary_summary.xlsx"
simple_df.to_excel(simple_excel, index=False)

with open(simple_excel, "rb") as file:
    st.download_button(
        label="下載簡化版總表 Excel",
        data=file,
        file_name="簡化版薪資總表.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_simple_salary"
    )

    complex_excel = "complex_salary_summary.xlsx"

    formatted_df.to_excel(
        complex_excel,
        index=False
    )

with open(complex_excel, "rb") as file:
    st.download_button(
        label="下載薪資總表 Excel",
        data=file,
        file_name="薪資總表.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_complex_salary"
    )

st.subheader("刪除總表紀錄")

delete_options = [
    f"{idx}｜{row['年月']}｜{row['姓名']}｜實發 {row['實發薪資']}"
     for idx, row in summary_df.iterrows()
]

if len(delete_options) > 0:

    delete_choice = st.selectbox(
        "選擇要刪除的紀錄",
        delete_options
    )

    if st.button("刪除選取紀錄"):

         delete_index = int(
            delete_choice.split("｜")[0]
        )

         history_df = history_df.drop(
            index=delete_index
         )

         history_df.to_csv(
             "salary_records.csv",
            index=False,
             encoding="utf-8-sig"
         )

         st.success("已刪除紀錄")

else:

    st.info(
        "目前還沒有薪資紀錄，請先儲存薪資資料。"
    )
