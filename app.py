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
    initial_sidebar_state="collapsed" # 默认收起侧边栏，保持界面纯净
)

# --- 2. 核心 CSS 样式（美化、隐藏元素、自适应布局） ---
st.markdown("""
    <style>
    /* 1. 彻底隐藏顶部彩虹条、GitHub Fork按钮和底部水印 */
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
        .logo-container { top: -40px; right: -40px; }
    }

    /* 3. 卡片自适应美化 */
    .vehicle-card {
        background-color: white; 
        border-radius: 12px; 
        padding: 1.2rem;
        margin-bottom: 1rem; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 5px solid #007bff; 
        color: #31333F;
    }
    .plate-header { 
        color: #007bff; 
        font-size: 1.3rem; 
        font-weight: bold; 
        margin-bottom: 0.8rem; 
        border-bottom: 1px solid #eee; 
        padding-bottom: 0.5rem; 
    }
    .info-row { 
        display: flex; 
        justify-content: space-between; 
        padding: 0.5rem 0; 
        border-bottom: 1px dashed #f5f5f5; 
    }
    .info-label { color: #777; font-size: 0.9rem; }
    .info-value { color: #111; font-weight: 500; font-size: 0.95rem; }
    
    /* 4. 移除移动端顶部多余留白 */
    .block-container {
        padding-top: 3.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    </style>
    
    <div class="logo-container">
        <img src="https://cloud-assets-brwq.bcdn8.com/weice0314/uploads/20230314/46fd5ef88f68a88ea9858999c63b6362.svg" class="custom-logo">
    </div>
    """, unsafe_allow_html=True) # 关键参数：确保HTML样式生效

# --- 3. 数据库连接逻辑 ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # 从 Secrets 获取凭证并修复转义问题
        json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
        creds_dict = json.loads(json_info)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # 对应您的 Google Sheets 文件名
        return client.open("PlateDB").sheet1
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        return None

sheet = init_connection()

# --- 4. 侧边栏：管理员维护功能 (对应 image_6aebca.png 字段) ---
with st.sidebar:
    st.header("⚙️ 后台管理")
    admin_pwd = st.text_input("管理密码", type="password")
    if admin_pwd == "admin888": # 请在此处自定义您的密码
        st.success("身份验证成功")
        st.divider()
        with st.form("add_record_form", clear_on_submit=True):
            st.write("新增车辆记录")
            f1 = st.text_input("工号")
            f2 = st.text_input("姓名")
            f3 = st.text_input("部门")
            f4 = st.text_input("厂区")
            f5 = st.text_input("手机号")
            f6 = st.text_input("车牌号 *")
            
            if st.form_submit_button("确认保存"):
                if f6:
                    try:
                        # 严格按照 A-F 列顺序追加: 工号, 姓名, 部门, 厂区, 手机号, 车牌号
                        sheet.append_row([f1, f2, f3, f4, f5, f6.upper()])
                        st.success("数据已成功同步至数据库！")
                        st.cache_resource.clear() # 更新缓存以同步查询结果
                    except Exception as e:
                        st.error(f"写入失败: {e}")
                else:
                    st.warning("车牌号为必填项")

# --- 5. 主界面：查询功能 ---
# 优化标题：缩小字号并禁止换行
st.markdown("""
    <h2 style='
        text-align: center; 
        margin-bottom: 1.5rem; 
        font-size: 1.4rem; 
        white-space: nowrap; 
        color: #FFFFFF;'>
        🚗 车辆信息智能检索
    </h2>
    """, unsafe_allow_html=True)

with st.container():
    with st.form("search_form"):
        search_id = st.text_input("车牌检索", placeholder="输入车牌中任意连续4位...", help="支持模糊匹配")
        submitted = st.form_submit_button("立即搜索")

# --- 6. 结果展示逻辑 ---
if (submitted or search_id) and search_id.strip():
    if not sheet:
        st.error("数据库连接未就绪")
    else:
        with st.spinner("正在查询数据库..."):
            # 获取所有数据转为 DataFrame
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # 模糊匹配逻辑
            query_str = search_id.strip().upper()
            result_df = df[df['车牌号'].astype(str).str.upper().str.contains(query_str)]
            
            if not result_df.empty:
                st.success(f"找到 {len(result_df)} 条记录")
                for _, row in result_df.iterrows():
                    # 动态生成结果卡片
                    card_html = f'<div class="vehicle-card"><div class="plate-header">车牌：{row["车牌号"]}</div>'
                    
                    # 动态遍历 image_6aebca.png 中的所有数据库字段
                    for col in df.columns:
                        if col != "车牌号":
                            val = str(row[col]).strip() if str(row[col]).strip() != "" else "无"
                            card_html += f'<div class="info-row"><span class="info-label">{col}</span><span class="info-value">{val}</span></div>'
                    
                    card_html += '</div>'
                    # 确保解析HTML以展示卡片样式而非源码
                    st.markdown(card_html, unsafe_allow_html=True)
            else:
                st.warning(f"❌ 未找到与 '{search_id}' 相关的记录")
