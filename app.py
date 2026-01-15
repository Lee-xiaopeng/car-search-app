import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="车辆信息管理系统",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="auto"
)

# --- 2. 强力 CSS 注入 ---
st.markdown("""
    <style>
    /* 1. 隐藏右侧 GitHub、Fork、小皇冠图标，但【绝对保留】左侧侧边栏按钮 */
    [data-testid="stHeaderActionElements"], .stAppDeployButton, [data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* 2. 让顶部 Header 背景透明，不遮挡自定义内容，同时确保侧边栏按钮可见 */
    header[data-testid="stHeader"] {
        background: rgba(0,0,0,0) !important;
        color: #1f1f1f !important;
    }
    
    /* 3. 右上角 Logo 定位 (下移至 GitHub 图标原位置下方) */
    .logo-container {
        position: absolute;
        top: 25px;
        right: 15px;
        z-index: 1000;
    }
    .custom-logo { width: 65px; height: auto; }
    @media (min-width: 768px) {
        .custom-logo { width: 90px; }
        .logo-container { top: 30px; right: 20px; }
    }

    /* 4. 标题文字：强制深色，白底黑底均可见 */
    .main-title {
        text-align: center; 
        margin-top: 4.5rem;
        margin-bottom: 2rem; 
        font-size: 1.6rem; 
        white-space: nowrap; 
        color: #1f1f1f !important;
        font-weight: 800;
    }

    /* 5. 【修复居中】强制立即搜索按钮在手机端居中 */
    .stButton {
        display: flex !important;
        justify-content: center !important;
        margin: 20px 0 !important;
    }
    .stButton > button {
        background-color: #007bff !important; /* 明显的蓝色按钮 */
        color: white !important;
        border-radius: 25px !important;
        padding: 0.6rem 3.5rem !important;
        border: none !important;
        font-weight: bold !important;
        box-shadow: 0 4px 15px rgba(0,123,255,0.4) !important;
    }

    /* 6. 结果卡片样式 */
    .vehicle-card {
        background-color: white !important; 
        border-radius: 12px; 
        padding: 1.2rem;
        margin-bottom: 1rem; 
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border-left: 6px solid #007bff; 
        color: #1f1f1f !important;
    }
    .plate-header { color: #007bff; font-size: 1.4rem; font-weight: bold; margin-bottom: 0.5rem; }
    .info-row { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px dashed #eee; }
    
    /* 隐藏底部水印 */
    footer { visibility: hidden !important; }
    
    /* 页面整体下移适配 */
    .block-container { padding-top: 7rem !important; }
    </style>
    
    <div class="logo-container">
        <img src="https://cloud-assets-brwq.bcdn8.com/weice0314/uploads/20230314/46fd5ef88f68a88ea9858999c63b6362.svg" class="custom-logo">
    </div>
    """, unsafe_allow_html=True)

# --- 3. 数据库连接 ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
        creds_dict = json.loads(json_info)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("PlateDB").sheet1
    except Exception as e:
        st.error("数据库连接配置有误")
        return None

sheet = init_connection()

# --- 4. 侧边栏：新增功能 ---
# 只要点击左上角的 >> 按钮，这里的内容就会出现
with st.sidebar:
    st.header("⚙️ 后台管理")
    admin_pwd = st.text_input("管理密码", type="password")
    if admin_pwd == "admin888":
        st.success("验证通过")
        with st.form("add_form", clear_on_submit=True):
            f1 = st.text_input("工号")
            f2 = st.text_input("姓名")
            f3 = st.text_input("部门")
            f4 = st.text_input("厂区")
            f5 = st.text_input("手机号")
            f6 = st.text_input("车牌号 *")
            if st.form_submit_button("保存到云端"):
                if f6.strip():
                    try:
                        sheet.append_row([f1, f2, f3, f4, f5, f6.upper().strip()])
                        st.success("✅ 数据已存入！")
                        st.cache_resource.clear()
                    except Exception as e:
                        st.error(f"失败: {e}")

# --- 5. 主界面 ---
st.markdown('<div class="main-title">🚗 车辆信息智能检索</div>', unsafe_allow_html=True)

with st.form("search_form"):
    search_id = st.text_input(
        "车牌号码查询", 
        placeholder="请输入车牌中任意连续4位...", 
        label_visibility="visible"
    )
    # CSS 已强制此按钮居中
    submitted = st.form_submit_button("立即搜索")

# --- 6. 结果展示 ---
if (submitted or search_id) and search_id.strip():
    if not sheet:
        st.error("数据库无法连接")
    else:
        with st.spinner("查询中..."):
            df = pd.DataFrame(sheet.get_all_records())
            query = search_id.strip().upper()
            result = df[df['车牌号'].astype(str).str.upper().str.contains(query)]
            
            if not result.empty:
                for _, row in result.iterrows():
                    card_html = f'<div class="vehicle-card"><div class="plate-header">车牌：{row["车牌号"]}</div>'
                    for col in df.columns:
                        if col != "车牌号":
                            val = str(row[col]).strip() if str(row[col]).strip() != "" else "无"
                            card_html += f'<div class="info-row"><span style="color:#666">{col}</span><span style="color:#111;font-weight:600">{val}</span></div>'
                    card_html += '</div>'
                    st.markdown(card_html, unsafe_allow_html=True)
            else:
                st.warning("未找到匹配记录")
