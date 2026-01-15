import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
import qrcode
from io import BytesIO

# --- 1. 页面基本配置 ---
st.set_page_config(
    page_title="车辆信息管理系统",
    page_icon="🚗",
    layout="centered"
)

# --- 2. 自定义美化样式 (CSS) ---
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .result-card {
        padding: 20px;
        border-radius: 10px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .status-badge {
        padding: 5px 12px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.8em;
    }
    </style>
    """, unsafe_allow_stdio=True)

# --- 3. 数据库连接逻辑 (V1.5 稳定版) ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # 从 Secrets 获取 JSON 并修复转义
        json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
        creds_dict = json.loads(json_info)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # 确保表格名称为 PlateDB
        return client.open("PlateDB").sheet1
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        return None

sheet = init_connection()

# --- 4. 侧边栏/头部 ---
st.title("🚗 车辆信息智能查询")
st.info("请输入连续4位车牌号码进行实时数据检索")

# --- 5. 查询交互区域 ---
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        search_id = st.text_input("车牌号检索", placeholder="例如: B1234", label_visibility="collapsed")
    with col2:
        search_btn = st.button("立即查询")

# --- 6. 结果展示逻辑 ---
if search_btn or search_id:
    if not sheet:
        st.warning("数据库未就绪，请检查 Secrets 配置。")
    else:
        with st.spinner("正在检索数据库..."):
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # 匹配逻辑 (假设列名为 '车牌号')
            result = df[df['车牌号'].astype(str).str.upper() == search_id.strip().upper()]
            
            if not result.empty:
                st.success(f"找到 {len(result)} 条匹配记录")
                row = result.iloc[0]
                
                # 美化显示卡片
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns(3)
                c1.metric("品牌型号", f"{row.get('品牌', '未知')} {row.get('型号', '')}")
                c2.metric("车身颜色", row.get('颜色', '未知'))
                
                # 状态标签美化
                status = row.get('状态', '未知')
                status_color = "#28a745" if "正常" in status else "#dc3545"
                st.markdown(f"**当前状态:** <span class='status-badge' style='background-color:{status_color}; color:white;'>{status}</span>", unsafe_allow_html=True)
                
                st.markdown("---")
                st.write(f"**其它备注:** {row.get('备注', '无')}")
                st.markdown('</div>', unsafe_allow_html=True)
                
            else:
                st.error("❌ 未找到该车牌信息，请核实后再试。")

# --- 7. 页脚 ---
st.markdown("---")
