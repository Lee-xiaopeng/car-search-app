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
    initial_sidebar_state="collapsed" # 初始隐藏侧边栏，页面更干净
)

# --- 2. 核心 CSS 样式（自适应、隐藏元素、右上角Logo） ---
st.markdown("""
    <style>
    /* 1. 彻底隐藏顶部装饰、GitHub图标、底部水印 */
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    
    /* 2. 右上角 Logo 自适应布局 */
    .logo-container {
        position: absolute;
        top: -50px; /* 调整到标题上方 */
        right: 0px;
        z-index: 1000;
    }
    .custom-logo {
        width: 80px; /* 手机端较小的尺寸 */
        height: auto;
    }
    @media (min-width: 768px) {
        .custom-logo { width: 120px; } /* 电脑端较大的尺寸 */
        .logo-container { top: -20px; right: -50px; }
    }

    /* 3. 卡片自适应排版 */
    .vehicle-card {
        background-color: white; 
        border-radius: 15px; 
        padding: 1.5rem;
        margin-bottom: 1rem; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 6px solid #007bff; 
        color: #31333F;
    }
    .plate-header { 
        color: #007bff; 
        font-size: 1.4rem; 
        font-weight: 800; 
        margin-bottom: 1rem; 
        border-bottom: 2px solid #f0f2f6; 
        padding-bottom: 0.5rem; 
    }
    .info-row { 
        display: flex; 
        justify-content: space-between; 
        padding: 0.6rem 0; 
        border-bottom: 1px dashed #eee; 
    }
    .info-label { color: #666; font-size: 0.9rem; }
    .info-value { color: #111; font-weight: 600; font-size: 1rem; }
    
    /* 移除手机端多余边距 */
    .block-container {
        padding-top: 4rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    </style>
    
    <div class="logo-container">
        <img src="https://cloud-assets-brwq.bcdn8.com/weice0314/uploads/20230314/46fd5ef88f68a88ea9858999c63b6362.svg" class="custom-logo">
    </div>
    """, unsafe_allow_html=True) # 确保 HTML 被正确渲染而非显示源码

# --- 3. 数据库连接 ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # 处理密钥转义与 JSON 解析
        json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
        creds_dict = json.loads(json_info)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("PlateDB").sheet1
    except Exception as e:
        st.error(f"数据库连接失败，请检查配置")
        return None

sheet = init_connection()

# --- 4. 侧边栏：管理员维护 (匹配 image_6aebca.png 字段) ---
with st.sidebar:
    st.header("⚙️ 数据维护")
    pwd = st.text_input("管理密码", type="password")
    if pwd == "admin888":
        st.success("验证通过")
        with st.form("add_form", clear_on_submit=True):
            f1 = st.text_input("工号")
            f2 = st.text_input("姓名")
            f3 = st.text_input("部门")
            f4 = st.text_input("厂区")
            f5 = st.text_input("手机号")
            f6 = st.text_input("车牌号 *")
            if st.form_submit_button("保存到数据库"):
                if f6:
                    try:
                        # 严格按照 A-F 列顺序追加
                        sheet.append_row([f1, f2, f3, f4, f5, f6.upper()])
                        st.success("✅ 已同步至 Google Sheets")
                        st.cache_resource.clear()
                    except Exception as e:
                        st.error(f"保存失败: {e}")
                else:
                    st.warning("车牌号为必填项")

# --- 5. 主界面：查询 ---
st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>🚗 车辆信息智能检索</h1>", unsafe_allow_html=True)

with st.container():
    with st.form("search_form"):
        search_query = st.text_input("车牌检索", placeholder="请输入车牌中任意连续4位...")
        submitted = st.form_submit_button("立即搜索")

# --- 6. 结果展示 ---
if (submitted or search_query) and search_query.strip():
    if not sheet:
        st.error("数据库未就绪")
    else:
        with st.spinner("正在检索数据库..."):
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            q = search_query.strip().upper()
            res = df[df['车牌号'].astype(str).str.upper().str.contains(q)]
            
            if not res.empty:
                st.toast(f"找到 {len(res)} 条结果")
                for _, row in res.iterrows():
                    # 动态生成自适应卡片
                    html = f'<div class="vehicle-card"><div class="plate-header">车牌：{row["车牌号"]}</div>'
                    # 遍历显示 image_6aebca.png 中的所有字段
                    for col in df.columns:
                        if col != "车牌号":
                            val = row[col] if str(row[col]).strip() != "" else "无"
                            html += f'<div class="info-row"><span class="info-label">{col}</span><span class="info-value">{val}</span></div>'
                    html += '</div>'
                    st.markdown(html, unsafe_allow_html=True)
            else:
                st.warning("❌ 未找到匹配记录")
