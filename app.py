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

# --- 2. 核心 CSS 样式（彻底修复居中与文字可见度） ---
st.markdown("""
    <style>
    /* 1. 基础隐藏 */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); } 

    /* 2. 右上角 Logo 定位 */
    .logo-container {
        position: absolute;
        top: 20px;
        right: 15px;
        z-index: 1000;
    }
    .custom-logo { width: 60px; height: auto; }
    @media (min-width: 768px) {
        .custom-logo { width: 85px; }
        .logo-container { top: 25px; right: 20px; }
    }

    /* 3. 【修复】标题文字在白底模式下的可见度 */
    .main-title {
        text-align: center; 
        margin-top: 3.5rem;
        margin-bottom: 2rem; 
        font-size: 1.6rem; 
        white-space: nowrap; 
        /* 改为深色，确保白底可见；同时增加一点发光阴影提升质感 */
        color: #1f1f1f !important; 
        font-weight: 800;
        text-shadow: 0px 0px 1px rgba(255,255,255,0.8);
    }

    /* 4. 【修复】强制按钮居中（穿透多层容器） */
    div[data-testid="stForm"] {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
    }
    
    div[data-testid="stForm"] > div {
        width: 100% !important;
    }

    /* 专门定位按钮所在的 div 并居中 */
    div.stButton {
        text-align: center !important;
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
    }

    /* 按钮颜色与样式升级 */
    div.stButton > button {
        background-color: #007bff !important;
        color: white !important;
        border-radius: 25px !important;
        padding: 0.6rem 3rem !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(0,123,255,0.4) !important;
    }

    /* 5. 结果卡片样式 */
    .vehicle-card {
        background-color: white !important; 
        border-radius: 12px; 
        padding: 1.2rem;
        margin-bottom: 1rem; 
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border-left: 6px solid #007bff; 
        color: #1f1f1f !important;
    }
    .plate-header { 
        color: #007bff; font-size: 1.4rem; font-weight: bold; 
        margin-bottom: 0.8rem; border-bottom: 2px solid #f0f2f6; padding-bottom: 0.5rem; 
    }
    .info-row { display: flex; justify-content: space-between; padding: 0.6rem 0; border-bottom: 1px dashed #eee; }
    .info-label { color: #666 !important; font-size: 0.9rem; }
    .info-value { color: #111 !important; font-weight: 600; font-size: 1rem; }

    .block-container { padding-top: 6rem !important; }
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
        st.error("数据库连接失败")
        return None

sheet = init_connection()

# --- 4. 侧边栏管理 ---
with st.sidebar:
    st.header("⚙️ 管理后台")
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
            if st.form_submit_button("确认保存到云端"):
                if f6.strip():
                    try:
                        sheet.append_row([f1, f2, f3, f4, f5, f6.upper().strip()])
                        st.success("保存成功")
                        st.cache_resource.clear()
                    except Exception as e:
                        st.error(f"失败: {e}")

# --- 5. 主界面查询 ---
st.markdown('<div class="main-title">🚗 车辆信息智能检索</div>', unsafe_allow_html=True)

with st.form("search_form"):
    search_id = st.text_input(
        "车牌号码查询", 
        placeholder="请输入车牌中任意连续4位...", 
        label_visibility="visible"
    )
    # CSS 已经强制居中 stButton，这里直接放置即可
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
                st.toast(f"找到 {len(result)} 条匹配记录")
                for _, row in result.iterrows():
                    card_html = f'<div class="vehicle-card"><div class="plate-header">车牌：{row["车牌号"]}</div>'
                    for col in df.columns:
                        if col != "车牌号":
                            val = str(row[col]).strip() if str(row[col]).strip() != "" else "无"
                            card_html += f'<div class="info-row"><span class="info-label">{col}</span><span class="info-value">{val}</span></div>'
                    card_html += '</div>'
                    st.markdown(card_html, unsafe_allow_html=True)
            else:
                st.warning("未找到匹配记录")
