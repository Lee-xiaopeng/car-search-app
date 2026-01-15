import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 页面基本配置 ---
st.set_page_config(
    page_title="车辆信息管理系统",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="expanded" # 改为默认展开，方便您立即看到新增功能
)

# --- 2. 核心 CSS 样式（隐藏多余元素、自适应布局、单行标题） ---
st.markdown("""
    <style>
    /* 1. 彻底隐藏顶部装饰、GitHub链接、底部水印 */
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    
    /* 2. 右上角 Logo 自适应 */
    .logo-container {
        position: absolute;
        top: -65px;
        right: 0px;
        z-index: 1000;
    }
    .custom-logo { width: 70px; height: auto; }
    @media (min-width: 768px) {
        .custom-logo { width: 100px; }
        .logo-container { top: -45px; right: -40px; }
    }

    /* 3. 查询结果卡片美化 */
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
    
    /* 4. 移除移动端顶部多余留白 */
    .block-container { padding-top: 3.5rem !important; }

    /* 5. 标题强制单行显示 */
    .main-title {
        text-align: center; 
        margin-bottom: 1.5rem; 
        font-size: 1.4rem; 
        white-space: nowrap; 
        overflow: hidden;
        text-overflow: ellipsis;
        color: #FFFFFF;
    }
    </style>
    
    <div class="logo-container">
        <img src="https://cloud-assets-brwq.bcdn8.com/weice0314/uploads/20230314/46fd5ef88f68a88ea9858999c63b6362.svg" class="custom-logo">
    </div>
    """, unsafe_allow_html=True) #

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
        st.error(f"连接失败: {e}")
        return None

sheet = init_connection()

# --- 4. 【恢复重点】侧边栏：管理员新增功能 ---
with st.sidebar:
    st.header("⚙️ 数据维护后台")
    admin_pwd = st.text_input("请输入管理密码", type="password")
    
    if admin_pwd == "admin888": # 验证通过
        st.success("验证通过，您可以新增记录")
        st.divider()
        with st.form("add_form", clear_on_submit=True):
            # 字段顺序完全匹配 image_6aebca.png
            f1 = st.text_input("工号")
            f2 = st.text_input("姓名")
            f3 = st.text_input("部门")
            f4 = st.text_input("厂区")
            f5 = st.text_input("手机号")
            f6 = st.text_input("车牌号 *")
            
            submit_btn = st.form_submit_button("确认新增并上传")
            
            if submit_btn:
                if f6.strip():
                    try:
                        # 追加数据到 Google Sheets
                        sheet.append_row([f1, f2, f3, f4, f5, f6.upper().strip()])
                        st.balloons()
                        st.success("✅ 数据已同步至 Google Sheets！")
                        st.cache_resource.clear() # 刷新缓存
                    except Exception as e:
                        st.error(f"保存失败: {e}")
                else:
                    st.warning("车牌号是必填项")

# --- 5. 主界面：查询部分 ---
st.markdown('<div class="main-title">🚗 车辆信息智能检索</div>', unsafe_allow_html=True) #

with st.form("search_form"):
    search_id = st.text_input("车牌检索", placeholder="请输入车牌中任意连续4位...")
    submitted = st.form_submit_button("立即搜索")

# --- 6. 结果展示 ---
if (submitted or search_id) and search_id.strip():
    if not sheet:
        st.error("数据库连接异常")
    else:
        with st.spinner("检索中..."):
            df = pd.DataFrame(sheet.get_all_records())
            query = search_id.strip().upper()
            result = df[df['车牌号'].astype(str).str.upper().str.contains(query)]
            
            if not result.empty:
                st.info(f"为您找到 {len(result)} 条匹配记录")
                for _, row in result.iterrows():
                    # 生成展示卡片
                    card_html = f'<div class="vehicle-card"><div class="plate-header">车牌：{row["车牌号"]}</div>'
                    # 动态遍历数据库所有列名显示信息
                    for col in df.columns:
                        if col != "车牌号":
                            val = str(row[col]).strip() if str(row[col]).strip() != "" else "无"
                            card_html += f'<div class="info-row"><span class="info-label">{col}</span><span class="info-value">{val}</span></div>'
                    card_html += '</div>'
                    st.markdown(card_html, unsafe_allow_html=True)
            else:
                st.warning("未找到匹配记录")
