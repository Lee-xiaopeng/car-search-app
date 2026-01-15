import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import qrcode
from io import BytesIO

# 页面设置
st.set_page_config(page_title="车辆信息查询", layout="centered")

# --- 1. 数据库连接 ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # 从 Streamlit 的机密设置中读取 JSON 密钥
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("PlateDB").sheet1

try:
    sheet = init_connection()
except Exception as e:
    st.error("数据库连接失败，请检查密钥配置。")
    st.stop()

# --- 2. 路由逻辑 ---
query_params = st.query_params
is_admin = query_params.get("mode") == "admin"

if is_admin:
    st.header("🔒 管理员录入界面")
    password = st.text_input("输入管理密码", type="password")
    
    if password == "8888":  # 这里设置你的管理密码
        with st.form("add_form", clear_on_submit=True):
            id_val = st.text_input("数字ID")
            name_val = st.text_input("姓名")
            dept_val = st.text_input("部门")
            sub_dept_val = st.text_input("分厂")
            phone_val = st.text_input("电话号码")
            plate_val = st.text_input("车牌号")
            submit = st.form_submit_button("确认添加")
            
            if submit:
                sheet.append_row([id_val, name_val, dept_val, sub_dept_val, phone_val, plate_val])
                st.success("录入成功！")
        
        st.divider()
        if st.button("生成公共查询二维码"):
            # 注意：这里的 URL 需要在你部署完后修改成实际地址
            qr_img = qrcode.make("https://share.streamlit.io/") 
            buf = BytesIO()
            qr_img.save(buf)
            st.image(buf.getvalue(), caption="公共查询二维码")
    elif password:
        st.error("密码错误")

else:
    # --- 3. 用户查询界面 ---
    st.header("🚗 车辆信息查询")
    st.write("请输入车牌号后4位或以上进行搜索")
    
    search_input = st.text_input("车牌号", placeholder="例如：A888")
    
    if search_input:
        if len(search_input) < 4:
            st.warning("请至少输入4位车牌号")
        else:
            # 获取数据
            df = pd.DataFrame(sheet.get_all_records())
            if not df.empty:
                # 模糊搜索
                match = df[df['plate'].astype(str).str.contains(search_input, case=False)]
                
                if not match.empty:
                    st.success(f"找到 {len(match)} 条匹配记录")
                    # 直接展示结果表格
                    st.table(match)
                else:
                    st.error("未找到匹配车辆信息")
            else:
                st.info("数据库暂无数据")
