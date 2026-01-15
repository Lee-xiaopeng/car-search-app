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
    initial_sidebar_state="collapsed" # 默认收起，点击左上角 >> 即可新增
)

# --- 2. 深度 UI 优化 (兼容深/浅模式) ---
st.markdown("""
    <style>
    /* 1. 抹除不需要的官方元素 (Fork, GitHub, 右下角小皇冠) */
    [data-testid="stHeaderActionElements"], 
    .stAppDeployButton, 
    [data-testid="stToolbar"],
    footer { 
        display: none !important; 
    }

    /* 2. 强制 Header 透明但保留功能 (确保左上角按钮可见) */
    header[data-testid="stHeader"] {
        background: rgba(0,0,0,0) !important;
    }

    /* 3. 右上角 Logo 定位 (自适应) */
    .logo-container {
        position: absolute;
        top: 2.5rem;
        right: 1rem;
        z-index: 1001;
    }
    .custom-logo { width: 60px; height: auto; }
    @media (min-width: 768px) {
        .custom-logo { width: 90px; }
    }

    /* 4. 标题自适应颜色 (关键修复：根据系统主题变换) */
    .main-title {
        text-align: center;
        margin-top: 2rem;
        margin-bottom: 2rem;
        font-size: 1.6rem;
        font-weight: 800;
        /* 使用主题原生颜色变量 */
        color: var(--text-color) !important; 
    }

    /* 5. 按钮物理居中修复 */
    div.stButton {
        display: flex;
        justify-content: center;
        width: 100%;
    }
    div.stButton > button {
        background-color: #007bff !important;
        color: white !important;
        border-radius: 20px;
        padding: 0.5rem 3rem;
        border: none;
        font-weight: bold;
    }

    /* 6. 结果卡片美化 (自适应深浅色) */
    .vehicle-card {
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-left: 6px solid #007bff;
        /* 动态配色 */
        background-color: var(--secondary-background-color) !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .plate-header {
        color: #007bff;
        font-size: 1.4rem;
        font-weight: bold;
        border-bottom: 1px solid rgba(128,128,128,0.2);
        padding-bottom: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .info-row {
        display: flex;
        justify-content: space-between;
        padding: 0.4rem 0;
    }
    .info-label { color: var(--text-color); opacity: 0.7; }
    .info-value { color: var(--text-color); font-weight: 600; }

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
        st.error("数据库链接异常")
        return None

sheet = init_connection()

# --- 4. 侧边栏：管理后台 ---
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
            if st.form_submit_button("保存到数据库"):
                if f6.strip():
                    try:
                        sheet.append_row([f1, f2, f3, f4, f5, f6.upper().strip()])
                        st.success("✅ 数据已存入")
                        st.cache_resource.clear()
                    except Exception as e:
                        st.error(f"保存失败: {e}")

# --- 5. 主界面 ---
st.markdown('<div class="main-title">🚗 车辆信息智能检索</div>', unsafe_allow_html=True)

with st.form("search_form"):
    search_id = st.text_input(
        "车牌号码", 
        placeholder="请输入车牌中任意连续4位...",
        label_visibility="collapsed" # 隐藏多余的 label 增加简洁度
    )
    # 按钮会受到 CSS 控制自动居中
    submitted = st.form_submit_button("立即搜索")

# --- 6. 结果展示 ---
if (submitted or search_id) and search_id.strip():
    if not sheet:
        st.error("无法访问数据库")
    else:
        with st.spinner("查询中..."):
            df = pd.DataFrame(sheet.get_all_records())
            query = search_id.strip().upper()
            result = df[df['车牌号'].astype(str).str.upper().str.contains(query)]
            
            if not result.empty:
                for _, row in result.iterrows():
                    # 构建卡片内容
                    card_content = ""
                    for col in df.columns:
                        if col != "车牌号":
                            val = str(row[col]).strip() or "无"
                            card_content += f'<div class="info-row"><span class="info-label">{col}</span><span class="info-value">{val}</span></div>'
                    
                    st.markdown(f"""
                        <div class="vehicle-card">
                            <div class="plate-header">车牌：{row['车牌号']}</div>
                            {card_content}
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("未找到匹配记录")
