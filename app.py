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
    # 尝试从 Secrets 读取
    if "gcp_service_account" not in st.secrets:
        st.error("Secrets 中缺少 'gcp_service_account' 配置项！")
        st.stop()
        
    creds_dict = dict(st.secrets["gcp_service_account"])
    # 关键点：强制处理私钥中的换行符
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # 确保表格名称完全一致
    return client.open("PlateDB").sheet1

try:
    sheet = init_connection()
except Exception as e:
    st.error("❌ 数据库连接详细错误报告：")
    st.exception(e)  # 这行会显示红色框框，里面有具体的错误代码
    st.stop()

# --- 2. 路由逻辑 ---
query_params = st.query_params
is_admin = query_params.get("mode") == "admin"

if is_admin:
    st.header("🔒 管理员录入界面")
    password = st.text_input("输入管理密码", type="password")
    
    if password == "8888":  # 管理密码
        with st.form("add_form", clear_on_submit=True):
            id_val = st.text_input("工号")
            name_val = st.text_input("姓名")
            dept_val = st.text_input("部门")
            sub_dept_val = st.text_input("科室")
            phone_val = st.text_input("手机号")
            plate_val = st.text_input("车牌号")
            submit = st.form_submit_button("确认添加")
            
            if submit:
                # 按照表格中文标题顺序添加
                sheet.append_row([id_val, name_val, dept_val, sub_dept_val, phone_val, plate_val])
                st.success("录入成功！")
        
        st.divider()
        if st.button("生成公共查询二维码"):
            # 获取当前应用的访问地址
            qr_img = qrcode.make("https://car-search-app-gfbfcamknbrhacq33icjk5.streamlit.app/") 
            buf = BytesIO()
            qr_img.save(buf)
            st.image(buf.getvalue(), caption="扫码快速查询车辆")

    elif password:
        st.error("密码错误")

else:
    # --- 3. 用户查询界面 ---
    st.header("🚗 车辆信息查询")
    st.info("请输入车牌号进行搜索（例如：BQ39L7）")
    
    search_input = st.text_input("输入车牌号", placeholder="例如：Q39L")
    
    if search_input:
        if len(search_input) < 4: # 建议缩小限制，方便模糊查询
            st.warning("请至少输入4位车牌号")
        else:
            # 获取所有数据
            data = sheet.get_all_records()
            if data:
                df = pd.DataFrame(data)
                # 重要：使用表格中的中文列名“车牌号”
                # 使用 fillna('') 防止表格中有空行导致报错
                match = df[df['车牌号'].astype(str).str.contains(search_input, case=False, na='')]
                
                if not match.empty:
                    st.success(f"找到 {len(match)} 条匹配记录")
                    # 美化显示：隐藏索引并全宽展示
                    st.dataframe(match, use_container_width=True)
                else:
                    st.error("未找到匹配车辆信息，请检查输入是否正确")
            else:
                st.info("数据库暂无数据，请联系管理员录入")
