import streamlit as st
import pandas as pd
import numpy as np
import datetime

# ตั้งค่าหน้าเพจ Dashboard
st.set_page_config(page_title="Lab Instrument Maintenance Dashboard", layout="wide")
st.title("📊 ระบบแดชบอร์ดติดตามการบำรุงรักษาเครื่องมือห้องปฏิบัติการ")

# 1. ฟังก์ชันโหลดข้อมูลออนไลน์ (ปรับปรุงเพื่อรองรับโครงสร้าง Google Sheets จริงของคุณ)
def load_data():
    file_path = "https://docs.google.com/spreadsheets/d/1pCTg6OHRdikrG9iJ2eXckoPX5zvE5HkGea0gHC5zsII/export?format=csv"
    
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, encoding='cp874')
            
    # ค้นหาคอลัมน์ประทับเวลา
    time_col = None
    for col in df.columns:
        if 'ประทับเวลา' in col or 'Timestamp' in col:
            time_col = col
            break
            
    if time_col is not None:
        # บังคับแปลงคอลัมน์ประทับเวลาแบบยืดหยุ่น ยอมรับรูปแบบ day/month/year ทั้งไทยและสากล
        df[time_col] = pd.to_datetime(df[time_col], errors='coerce', dayfirst=True)
        # ล้างแถวที่เป็นค่าว่างเปล่าออกไป
        df = df[df[time_col].notna()].copy()
        
        df['Date'] = df[time_col].dt.date
        df['Month_Year'] = df[time_col].dt.to_period('M')
        df['Year'] = df[time_col].dt.year
    else:
        df['Date'] = datetime.date.today()
        df['Month_Year'] = pd.to_datetime('today').to_period('M')
        df['Year'] = datetime.date.today().year
    
    # ออโต้เสิร์ชหาคอลัมน์เครื่องมือ (ป้องกันปัญหาเว้นวรรคท้ายคำ)
    inst_col = None
    for col in df.columns:
        if "เลือกเครื่องมือ" in col:
            inst_col = col
            break
            
    if inst_col is None:
        st.error(f"❌ ไม่พบคอลัมน์เครื่องมือ คอลัมน์ที่มีอยู่คือ: {list(df.columns[:3])}")
        st.stop()
    
    # ฟังก์ชันรวมคอลัมน์ ผู้ตรวจเช็ค และ หมายเหตุ จากฟอร์มย่อย
    def combine_cols(row, keywords):
        for col in df.columns:
            if any(k in col for k in keywords) and col != inst_col:
                val = str(row[col]).strip()
                if val and val != 'nan' and val != '':
                    return val
        return "ไม่ระบุ"

    df['ชื่อเครื่องมือ'] = df[inst_col].str.strip()
    df['ผู้ตรวจเช็ค_รวม'] = df.apply(lambda r: combine_cols(r, ['ผู้ตรวจเช็ค', 'ผู้ตรวจเช็คเครื่อง', 'ผู้บันทึก']), axis=1)
    df['หมายเหตุ_รวม'] = df.apply(lambda r: combine_cols(r, ['หมายเหตุ', 'ปัญหาที่พบ', 'ปัยหาที่พบ', 'รายละเอียด']), axis=1)
    
    # กรองเฉพาะแถวที่มีวันที่ถูกต้องสมบูรณ์
    df = df[df['Date'].apply(lambda x: isinstance(x, datetime.date))].copy()
    return df

try:
    df_raw = load_data()
except Exception as e:
    st.error(f"❌ เกิดข้อผิดพลาดในการประมวลผลข้อมูล: {e}")
    st.stop()

# 🔔 กล่องรายงานสถานะจำนวนข้อมูลจริงบน Google Sheets
st.info(f"🔄 **สถานะการไหลของข้อมูล:** ดึงข้อมูลสดสำเร็จ! พบรายการบันทึกทั้งหมด **{len(df_raw)} แถว** ในระบบ")

# แถบเมนูด้านซ้ายมือ
st.sidebar.header("⚙️ ตั้งค่าระบบ & ตัวกรองข้อมูล")
TOTAL_INSTRUMENTS_IN_LAB = st.sidebar.number_input("จำนวนเครื่องมือทั้งหมดในแล็บ (เครื่อง)", min_value=1, value=15)

st.sidebar.markdown("---")
st.sidebar.header("🔍 ตัวควบคุมสำหรับ ข้อ 2 ถึง ข้อ 6")
filter_type = st.sidebar.selectbox("เลือกรูปแบบการดึงรายงาน", ["ดึงตามช่วงวันที่ (วัน/เดือน/ปี)", "ดึงรายเดือน/รายปี"])

# ตั้งค่าปฏิทินเริ่มต้นให้ตรงกับช่วงข้อมูลปี 2026
if filter_type == "ดึงตามช่วงวันที่ (วัน/เดือน/ปี)":
    if not df_raw.empty:
        max_date = df_raw['Date'].max()
        min_date = df_raw['Date'].min()
    else:
        max_date = datetime.date.today()
        min_date = max_date - datetime.timedelta(days=30)
        
    start_date = st.sidebar.date_input("จากวันที่", min_date)
    end_date = st.sidebar.date_input("ถึงวันที่", max_date)
    
    df_filtered = df_raw[(df_raw['Date'] >= start_date) & (df_raw['Date'] <= end_date)]
    report_label = f"ระหว่างวันที่ {start_date.strftime('%d/%m/%Y')} ถึง {end_date.strftime('%d/%m/%Y')}"
    year_for_matrix = end_date.year
    month_for_matrix = end_date.month
else:
    available_months = df_raw['Month_Year'].dropna().unique().astype(str)
    selected_month = st.sidebar.selectbox("เลือกเดือน/ปี", sorted(available_months, reverse=True))
    df_filtered = df_raw[df_raw['Month_Year'].astype(str) == selected_month]
    report_label = f"ประจำเดือน {selected_month}"
    current_period = pd.Period(selected_month)
    year_for_matrix = current_period.year
    month_for_matrix = current_period.month

# ตัวควบคุมข้อ 7
st.sidebar.markdown("---")
st.sidebar.header("🔬 ตัวควบคุมสำหรับ ข้อ 7")
all_unique_instruments = sorted(df_raw['ชื่อเครื่องมือ'].dropna().unique())
selected_instrument = st.sidebar.selectbox("🎯 เลือกเครื่องมือที่ต้องการดูหัวข้อย่อย", all_unique_instruments if all_unique_instruments else ["ไม่มีข้อมูล"])


# ==========================================
# ข้อ 1 ถึง ข้อ 3
# ==========================================
st.markdown("---")
st.header("1️⃣ ข้อ 1: สถิติการบำรุงรักษารายวัน (คิดเป็นร้อยละเทียบกับเครื่องมือทั้งหมด)")
if not df_raw.empty:
    latest_date = df_raw['Date'].max()
    df_today = df_raw[df_raw['Date'] == latest_date]
    maintained_today = df_today['ชื่อเครื่องมือ'].nunique()
    pct_today = (maintained_today / TOTAL_INSTRUMENTS_IN_LAB) * 100
    col1, col2 = st.columns(2)
    with col1: st.metric(label=f"จำนวนเครื่องมือที่ตรวจเช็ค ณ วันล่าสุดที่มีการบันทึก ({latest_date.strftime('%d/%m/%Y')})", value=f"{maintained_today} เครื่อง")
    with col2: st.metric(label="คิดเป็นร้อยละ (เทียบกับเครื่องมือทั้งหมดในแล็บ)", value=f"{pct_today:.2f} %")

st.markdown("---")
st.header("2️⃣ ข้อ 2: รายงานการบำรุงรักษาแยกตามช่วงเวลาที่ดึงข้อมูล (วัน/เดือน/ปี)")
st.info(f"📅 **สรุปช่วงเวลาการดึงรายงาน:** กำลังแสดงข้อมูล {report_label}")
if not df_filtered.empty:
    df_report_view = df_filtered[['ประทับเวลา', 'ชื่อเครื่องมือ', 'ผู้ตรวจเช็ค_รวม', 'หมายเหตุ_รวม']].copy()
    df_report_view.columns = ['วัน-เวลา ที่บันทึก', 'เครื่องมือที่ได้รับการตรวจเช็ค', 'ผู้ตรวจเช็ค', 'หมายเหตุ / ปัญหา']
    st.dataframe(df_report_view, use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ ไม่มีข้อมูลการบันทึกในช่วงวันที่เลือก")

st.markdown("---")
st.header("3️⃣ ข้อ 3: สถิติการบำรุงรักษาเครื่องมือแต่ละตัว (นับจำนวนครั้งที่ได้รับการตรวจเช็ค)")
if not df_filtered.empty:
    df_stats_count = df_filtered['ชื่อเครื่องมือ'].value_counts().reset_index()
    df_stats_count.columns = ['ชื่อเครื่องมือ', 'จำนวนครั้งที่ได้รับการตรวจเช็ค']
    st.bar_chart(data=df_stats_count, x='ชื่อเครื่องมือ', y='จำนวนครั้งที่ได้รับการตรวจเช็ค')
    st.dataframe(df_stats_count, use_container_width=True, hide_index=True)


# ==========================================
# ข้อ 4: ตาราง Matrix ภาพรวมแล็บประจำเดือน
# ==========================================
st.markdown("---")
st.header("4️⃣ ข้อ 4: ตารางบันทึกการบำรุงรักษาเครื่องมือในแต่ละวันประจำเดือน (ภาพรวมแล็บ)")
num_days = pd.Period(freq='M', year=year_for_matrix, month=month_for_matrix).days_in_month
all_days_in_month = range(1, num_days + 1)
df_current_month = df_filtered[(pd.to_datetime(df_filtered['Date']).dt.year == year_for_matrix) & (pd.to_datetime(df_filtered['Date']).dt.month == month_for_matrix)].copy()

if not df_current_month.empty:
    df_current_month['Day'] = pd.to_datetime(df_current_month['Date']).dt.day
    matrix_data = []
    for inst in all_unique_instruments:
        row_dict = {'ชื่อเครื่องมือ': inst}
        for day in all_days_in_month:
            is_maintained = any((df_current_month['ชื่อเครื่องมือ'] == inst) & (df_current_month['Day'] == day))
            row_dict[f"{day}"] = "/" if is_maintained else ""
        matrix_data.append(row_dict)
    df_matrix = pd.DataFrame(matrix_data)
    
    column_configuration = {"ชื่อเครื่องมือ": st.column_config.TextColumn("ชื่อเครื่องมือ", width="medium")}
    for day in all_days_in_month:
        column_configuration[f"{day}"] = st.column_config.TextColumn(f"{day}", width=35)
    st.dataframe(df_matrix, use_container_width=True, hide_index=True, column_config=column_configuration)
else:
    st.write(f"⚠️ ไม่มีข้อมูลในเดือน {month_for_matrix}/{year_for_matrix}")


# ==========================================
# ข้อ 5 ถึง ข้อ 6
# ==========================================
st.markdown("---")
st.header("5️⃣ ข้อ 5: ข้อมูลหมายเหตุหรือปัญหาที่พบในเครื่องมือ")
if not df_filtered.empty:
    df_issues = df_filtered[~df_filtered['หมายเหตุ_รวม'].isin(['', 'nan', 'ไม่ระบุ'])][['ประทับเวลา', 'ชื่อเครื่องมือ', 'ผู้ตรวจเช็ค_รวม', 'หมายเหตุ_รวม']]
    if not df_issues.empty:
        df_issues.columns = ['วัน-เวลา บันทึก', 'เครื่องมือที่พบปัญหา', 'ผู้รายงาน', 'รายละเอียดหมายเหตุ / ปัญหา']
        st.warning(f"⚠️ พบรายการแจ้งปัญหาทั้งหมด {len(df_issues)} รายการ:")
        st.dataframe(df_issues, use_container_width=True, hide_index=True)
    else: st.success("✨ สภาพปกติ: ไม่พบข้อมูลการแจ้งปัญหาใดๆ")

st.markdown("---")
st.header("6️⃣ ข้อ 6: ข้อมูลร้อยละของพนักงานแต่ละคนในการบำรุงรักษา")
if not df_filtered.empty:
    df_staff = df_filtered[~df_filtered['ผู้ตรวจเช็ค_รวม'].isin(['', 'nan', 'ไม่ระบุ'])]
    if not df_staff.empty:
        df_staff_stats = df_staff['ผู้ตรวจเช็ค_รวม'].value_counts().reset_index()
        df_staff_stats.columns = ['ชื่อพนักงาน / ผู้ตรวจเช็ค', 'จำนวนครั้งที่ปฏิบัติงาน']
        total_staff_actions = df_staff_stats['จำนวนครั้งที่ปฏิบัติงาน'].sum()
        df_staff_stats['ร้อยละการปฏิบัติงาน (%)'] = (df_staff_stats['จำนวนครั้งที่ปฏิบัติงาน'] / total_staff_actions) * 100
        st.dataframe(df_staff_stats[['ชื่อพนักงาน / ผู้ตรวจเช็ค', 'ร้อยละการปฏิบัติงาน (%)']].style.format({'ร้อยละการปฏิบัติงาน (%)': '{:.2f}%'}), use_container_width=True, hide_index=True)


# ==========================================
# ข้อ 7: ตารางตรวจเช็คลิสต์ย่อยรายเครื่อง
# ==========================================
st.markdown("---")
st.header(f"7️⃣ ข้อ 7: ตารางเช็คลิสต์หัวข้อย่อยสำหรับเครื่อง [{selected_instrument}]")
st.write(f"📅 ประจำเดือน **{month_for_matrix}/{year_for_matrix}**")

df_sub = df_raw[
    (df_raw['ชื่อเครื่องมือ'] == selected_instrument) & 
    (pd.to_datetime(df_raw['Date']).dt.year == year_for_matrix) & 
    (pd.to_datetime(df_raw['Date']).dt.month == month_for_matrix)
].copy()

if not df_sub.empty:
    df_sub['Day'] = pd.to_datetime(df_sub['Date']).dt.day
    exclude_keywords = ['ประทับเวลา', 'Date', 'Month_Year', 'Year', 'ชื่อเครื่องมือ', 'ผู้ตรวจเช็ค', 'หมายเหตุ', 'ปัญหา', 'เลือกเครื่องมือ']
    sub_task_cols = [col for col in df_raw.columns if not any(ex in col for ex in exclude_keywords)]
    
    active_sub_cols = []
    for col in sub_task_cols:
        valid_records = df_sub[col].dropna().astype(str).str.strip()
        valid_records = valid_records[~valid_records.isin(['', 'nan', 'NaN'])]
        if len(valid_records) > 0:
            active_sub_cols.append(col)

    if active_sub_cols:
        sub_matrix_data = []
        for sub_col in active_sub_cols:
            clean_title = sub_col.replace("[", "").replace("]", "").strip()
            row_dict = {'รายละเอียดการบำรุงรักษาย่อย': clean_title}
            for day in all_days_in_month:
                day_records = df_sub[df_sub['Day'] == day]
                has_sub_record = False
                if not day_records.empty:
                    val_check = day_records[sub_col].dropna().astype(str).str.strip()
                    val_check = val_check[~val_check.isin(['', 'nan', 'NaN', 'ไม่ระบุ'])]
                    if len(val_check) > 0:
                        has_sub_record = True
                row_dict[f"{day}"] = "/" if has_sub_record else ""
            sub_matrix_data.append(row_dict)
            
        df_sub_matrix = pd.DataFrame(sub_matrix_data)
        sub_column_config = {"รายละเอียดการบำรุงรักษาย่อย": st.column_config.TextColumn("รายละเอียดการบำรุงรักษาย่อย", width="large")}
        for day in all_days_in_month:
            sub_column_config[f"{day}"] = st.column_config.TextColumn(f"{day}", width=35)
        st.dataframe(df_sub_matrix, use_container_width=True, hide_index=True, column_config=sub_column_config)
    else:
        st.info("ℹ️ ไม่พบหัวข้อประเมินย่อยที่มีข้อมูลบันทึกสำหรับเครื่องมือนี้")
else:
    st.write("⚠️ ไม่มีข้อมูลการบันทึกย่อยของเครื่องมือชิ้นนี้ในเดือนที่เลือก")
