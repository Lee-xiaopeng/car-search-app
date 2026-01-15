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
    /* 1. 只隐藏Streamlit部署的多余元素，保留工具栏按钮 */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stStatusWidget"] { display: none; }
    .stDeployButton { display: none; }
    
    /* 恢复工具栏相关元素 */
    [data-testid="stToolbar"] { 
        visibility: visible !important; 
        opacity: 1 !important; 
    }
    [data-testid="stHeader"] { 
        visibility: visible !important; 
        background: rgba(0,0,0,0) !important; 
    }
    
    /* 2. 调整右上角 Logo 位置和大小 */
    .logo-container {
        position: fixed;
        top: 25px; /* 下移Logo位置，为工具栏留出空间 */
        right: 15px;
        z-index: 9999;
    }
    .custom-logo { 
        width: 75px; /* 放大Logo尺寸 */
        height: auto;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
    }
    
    /* 3. 标题样式优化 */
    .main-title {
        text-align: center; 
        margin: 2.5rem 0 2rem 0; 
        font-size: 1.8rem; 
        white-space: nowrap; 
        color: var(--text-color) !important; 
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    /* 4. 立即搜索按钮 - 移动端居中处理 */
    .stButton {
        display: flex;
        justify-content: center;
        width: 100%;
    }
    
    /* 移动端特定样式 */
    @media (max-width: 768px) {
        /* 移动端标题字体调整 */
        .main-title {
            font-size: 1.5rem;
            margin: 2rem 0 1.5rem 0;
        }
        
        /* 移动端Logo调整 */
        .custom-logo { 
            width: 65px; /* 移动端稍小但比之前大 */
        }
        .logo-container {
            top: 20px; /* 移动端下移 */
            right: 10px;
        }
        
        /* 移动端按钮优化 */
        .stButton button {
            width: 100% !important;
            max-width: 300px;
            margin: 0 auto;
        }
        
        /* 移动端输入框优化 */
        .stTextInput input {
            font-size: 16px !important; /* 防止iOS自动放大 */
        }
        
        /* 移动端工具栏调整 */
        [data-testid="stToolbar"] {
            right: 5px !important;
        }
    }
    
    /* 桌面端特定样式 */
    @media (min-width: 769px) {
        .custom-logo { 
            width: 90px; /* 桌面端更大 */
        }
        .logo-container { 
            top: 30px; /* 下移位置 */
            right: 25px; 
        }
    }
    
    /* 5. 结果卡片美化 - 更现代的设计 */
    .vehicle-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        border: 1px solid #e9ecef;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .vehicle-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.12);
    }
    
    .vehicle-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 5px;
        height: 100%;
        background: linear-gradient(to bottom, #4dabf7, #339af0);
    }
    
    .plate-header { 
        color: #1c7ed6; 
        font-size: 1.5rem; 
        font-weight: 700; 
        margin: 0 0 1.2rem 0; 
        padding-bottom: 0.8rem; 
        border-bottom: 2px solid #e9ecef;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .plate-header::before {
        content: '🚗';
        font-size: 1.2rem;
    }
    
    .info-row { 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        padding: 0.8rem 0; 
        border-bottom: 1px solid #f1f3f5;
        transition: background-color 0.2s;
    }
    
    .info-row:hover {
        background-color: rgba(241, 243, 245, 0.3);
        border-radius: 6px;
        padding: 0.8rem 0.5rem;
    }
    
    .info-row:last-child {
        border-bottom: none;
    }
    
    .info-label { 
        color: #495057; 
        font-size: 0.95rem;
        font-weight: 600;
        min-width: 60px;
    }
    
    .info-value { 
        color: #212529; 
        font-weight: 500; 
        font-size: 1rem;
        text-align: right;
        flex: 1;
        padding-left: 1rem;
    }
    
    /* 空值样式 */
    .info-value:empty::before {
        content: "—";
        color: #adb5bd;
        font-style: italic;
    }
    
    /* 6. 成功/警告消息样式优化 */
    .stSuccess {
        background: linear-gradient(135deg, #d3f9d8, #b2f2bb) !important;
        border-left: 4px solid #2b8a3e !important;
    }
    
    .stWarning {
        background: linear-gradient(135deg, #fff3bf, #ffec99) !important;
        border-left: 4px solid #e67700 !important;
    }
    
    .stError {
        background: linear-gradient(135deg, #ffe3e3, #ffc9c9) !important;
        border-left: 4px solid #e03131 !important;
    }
    
    /* 7. 输入框样式优化 */
    .stTextInput input {
        border-radius: 10px !important;
        border: 2px solid #e9ecef !important;
        padding: 0.8rem 1rem !important;
        font-size: 1rem !important;
        transition: all 0.3s !important;
    }
    
    .stTextInput input:focus {
        border-color: #339af0 !important;
        box-shadow: 0 0 0 3px rgba(51, 154, 240, 0.1) !important;
    }
    
    /* 8. 按钮样式优化 */
    .stButton button {
        background: linear-gradient(135deg, #339af0, #228be6) !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.8rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        transition: all 0.3s !important;
    }
    
    .stButton button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 12px rgba(51, 154, 240, 0.3) !important;
    }
    
    /* 9. 页面整体调整 - 为Logo和工具栏留出空间 */
    .main .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 800px !important;
    }
    
    /* 10. 侧边栏样式优化 */
    [data-testid="stSidebar"] {
        padding-top: 2rem;
    }
    
    [data-testid="stSidebarNav"] {
        padding-top: 1rem;
    }
    
    /* 11. 调整整体页面内容，避免被Logo和工具栏遮挡 */
    .stApp {
        padding-top: 0.5rem;
    }
    </style>
    
    <!-- Logo 容器 -->
    <div class="logo-container">
        <img src="https://cloud-assets-brwq.bcdn8.com/weice0314/uploads/20230314/46fd5ef88f68a88ea9858999c63b6362.svg" 
             class="custom-logo" 
             alt="Logo">
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
    st.markdown('<div style="font-size: 1.3rem; font-weight: 700; margin-bottom: 1rem;">⚙️ 管理后台</div>', unsafe_allow_html=True)
    admin_pwd = st.text_input("请输入管理密码", type="password")
    
    if admin_pwd == "admin888":
        st.success("身份验证成功")
        st.divider()
        st.subheader("📝 新增记录")
        with st.form("add_form", clear_on_submit=True):
            f1 = st.text_input("工号")
            f2 = st.text_input("姓名")
            f3 = st.text_input("部门")
            f4 = st.text_input("厂区")
            f5 = st.text_input("手机号")
            f6 = st.text_input("车牌号 *", help="此为必填项")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.form_submit_button("✅ 保存到云端", use_container_width=True):
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

# 创建搜索表单
with st.form("search_form"):
    search_id = st.text_input(
        "车牌号码查询", 
        placeholder="请输入车牌中任意连续4位...", 
        label_visibility="visible",
        help="支持模糊查询，输入车牌号中的任意连续4位即可"
    )
    
    # 使用st.columns确保按钮在移动端居中
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        submitted = st.form_submit_button("🔍 立即搜索", use_container_width=True)

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
                with st.spinner("🔍 正在检索数据库..."):
                    try:
                        df = pd.DataFrame(sheet.get_all_records())
                        # 4. 逻辑修改：转大写后进行包含匹配 (Contains)
                        # contains 默认就是匹配连续字符串，且不区分位置
                        search_term = query.upper()
                        
                        # 核心查询语句：车牌号列转字符串 -> 转大写 -> 检查是否包含用户输入的搜索词
                        result = df[df['车牌号'].astype(str).str.upper().str.contains(search_term)]
                        
                        if not result.empty:
                            #st.success(f"✅ 找到 {len(result)} 条包含「{search_term}」的记录")
                            
                            # 添加结果统计卡片
                            st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #e7f5ff, #d0ebff); 
                                            border-radius: 12px; 
                                            padding: 1rem; 
                                            margin: 1rem 0; 
                                            text-align: center;
                                            border-left: 4px solid #339af0;">
                                    <div style="font-size: 1.1rem; color: #1c7ed6; font-weight: 600;">
                                        📊 共找到 {len(result)} 条匹配记录
                                    </div>
                                    <div style="font-size: 0.9rem; color: #495057; margin-top: 0.5rem;">
                                        搜索关键词: <span style="font-weight: 700; color: #e03131;">{search_term}</span>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            for _, row in result.iterrows():
                                card_html = f'<div class="vehicle-card"><div class="plate-header">车牌：{row["车牌号"]}</div>'
                                for col in df.columns:
                                    if col != "车牌号":
                                        val = str(row[col]).strip() if str(row[col]).strip() != "" else "—"
                                        card_html += f'<div class="info-row"><span class="info-label">{col}</span><span class="info-value">{val}</span></div>'
                                card_html += '</div>'
                                st.markdown(card_html, unsafe_allow_html=True)
                        else:
                            st.warning(f"❌ 未找到包含「{search_term}」的车辆信息")
                    except Exception as e:
                        st.error(f"查询过程发生错误: {e}")
