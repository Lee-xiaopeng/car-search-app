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

# --- 2. 核心 CSS 样式 ---
st.markdown("""
    <style>
    /* 1. 隐藏多余元素，确保左侧侧边栏按钮可见 */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); } 

    /* 2. 右上角 Logo 定位：下移至 GitHub 图标下方 */
    .logo-container {
        position: absolute;
        top: 10px; /* 调整此值可微调上下位置 */
        right: 10px;
        z-index: 1000;
    }
    .custom-logo { width: 60px; height: auto; }
    
    /* 针对大屏幕的适配 */
    @media (min-width: 768px) {
        .custom-logo { width: 85px; }
        .logo-container { top: 15px; right: 10px; }
    }

    /* 3. 标题单行强制显示 - 颜色修复版 */
    .main-title {
        text-align: center; 
        margin-top: 2rem; /* 增加顶部间距防止被下移的Logo遮挡 */
        margin-bottom: 1.5rem; 
        font-size: 1.4rem; 
        white-space: nowrap; 
        
        /* 关键修改：使用系统变量，自动适配深色/浅色模式 */
        color: var(--text-color) !important; 
        
        font-weight: bold;
    }

    /* 4. 立即搜索按钮居中布局 */
    .stButton {
        display: flex;
        justify-content: center;
        margin-top: 10px;
    }

    /* 5. 结果卡片美化 */
    .vehicle-card {
        background-color: white; border-radius: 12px; padding: 1.2rem;
        margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 5px solid #007bff; color: #31333F;
    }
    .plate-header { 
        color: #007bff; font-size: 1.3rem; font-weight: bold; 
        margin-bottom: 0.8rem; border-bottom: 1px solid #eee; padding-bottom: 0.5rem; 
    }
    .info-row { display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px dashed #f5f5f5; }
    .info-label { color: #777; font-size: 0.9rem; }
    .info-value { color: #111; font-weight: 500; font-size: 0.95rem; }

    /* 整体页面顶部下移，为 Logo 留出空间 */
    .block-container { padding-top: 5rem !important; }
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
        st.error(f"数据库连接失败，请检查配置")
        return None

sheet = init_connection()

# --- 4. 侧边栏：管理功能 ---
with st.sidebar:
    st.header("⚙️ 管理后台")
    admin_pwd = st.text_input("请输入管理密码", type="password")
    
    if admin_pwd == "admin888":
        st.success("身份验证成功")
        st.divider()
        st.subheader("新增记录")
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
                        st.success("✅ 保存成功！")
                        st.cache_resource.clear()
                    except Exception as e:
                        st.error(f"保存失败: {e}")
                else:
                    st.warning("车牌号为必填项")

# --- 5. 主界面：查询部分 ---
st.markdown('<div class="main-title">🚗 车辆信息智能检索</div>', unsafe_allow_html=True)

with st.form("search_form"):
    search_id = st.text_input(
        "车牌号码查询", 
        placeholder="请输入车牌中任意连续4位...", 
        label_visibility="visible"
    )
    submitted = st.form_submit_button("立即搜索")

# --- 6. 结果展示与逻辑 ---
if submitted or search_id:
    query = search_id.strip() # 去除前后空格
    
    # 1. 逻辑修改：如果输入不为空
    if query:
        # 2. 逻辑修改：判断长度是否小于 4 位
        if len(query) < 4:
            st.warning("⚠️ 关键词太短，请至少输入 4 位字符以确保查询准确性")
        else:
            # 3. 长度合格，连接数据库
            if not sheet:
                st.error("数据库无法连接")
            else:
                with st.spinner("正在检索数据库..."):
                    try:
                        df = pd.DataFrame(sheet.get_all_records())
                        # 4. 逻辑修改：转大写后进行包含匹配 (Contains)
                        # contains 默认就是匹配连续字符串，且不区分位置
                        search_term = query.upper()
                        
                        # 核心查询语句：车牌号列转字符串 -> 转大写 -> 检查是否包含用户输入的搜索词
                        result = df[df['车牌号'].astype(str).str.upper().str.contains(search_term)]
                        
                        if not result.empty:
                            st.success(f"✅ 找到 {len(result)} 条包含“{search_term}”的记录")
                            for _, row in result.iterrows():
                                card_html = f'<div class="vehicle-card"><div class="plate-header">车牌：{row["车牌号"]}</div>'
                                for col in df.columns:
                                    if col != "车牌号":
                                        val = str(row[col]).strip() if str(row[col]).strip() != "" else "无"
                                        card_html += f'<div class="info-row"><span class="info-label">{col}</span><span class="info-value">{val}</span></div>'
                                card_html += '</div>'
                                st.markdown(card_html, unsafe_allow_html=True)
                        else:
                            st.warning(f"❌ 未找到包含“{search_term}”的车辆信息")
                    except Exception as e:
                        st.error(f"查询过程发生错误: {e}")
