import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 页面配置 ---
st.set_page_config(page_title="车辆检索系统", layout="centered")

# --- 2. 核心 CSS 样式（针对手机端优化） ---
st.markdown("""
    <style>
    /* 搜索按钮美化 */
    .stButton>button {
        width: 100%;
        background-color: #007bff;
        color: white;
        border-radius: 8px;
        height: 45px;
    }
    /* 卡片容器 */
    .vehicle-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 5px solid #007bff;
    }
    .plate-number {
        color: #007bff;
        font-size: 22px;
        font-weight: bold;
        margin-bottom: 15px;
        border-bottom: 1px solid #eee;
        padding-bottom: 10px;
    }
    .info-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        border-bottom: 1px dashed #f0f0f0;
        padding-bottom: 5px;
    }
    .info-label {
        color: #666;
        font-size: 14px;
    }
    .info-value {
        color: #1a1a1a;
        font-weight: 500;
        font-size: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 数据库连接（稳定版逻辑） ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # 修复 Secrets 转义问题
        json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
        creds_dict = json.loads(json_info)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("PlateDB").sheet1
    except Exception as e:
        st.error(f"连接失败: {e}")
        return None

sheet = init_connection()

# --- 4. 界面展示 ---
st.title("🚗 车辆信息查询")

with st.form("search_form"):
    search_id = st.text_input("车牌号检索", placeholder="请输入连续4位车牌内容...")
    submitted = st.form_submit_button("立即搜索")

# --- 5. 搜索逻辑 ---
if (submitted or search_id) and search_id.strip():
    if not sheet:
        st.error("数据库未连接")
    else:
        with st.spinner("正在查询..."):
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # 模糊匹配：车牌号包含输入内容
            query = search_id.strip().upper()
            result = df[df['车牌号'].astype(str).str.upper().str.contains(query)]
            
            if not result.empty:
                st.success(f"找到 {len(result)} 条结果")
                
                # 多条记录生成多个卡片
                for _, row in result.iterrows():
                    # 构建卡片内容
                    card_html = f"""
                    <div class="vehicle-card">
                        <div class="plate-number">车牌：{row['车牌号']}</div>
                    """
                    
                    # 动态遍历所有字段（除车牌号外）
                    for col, val in row.items():
                        if col != '车牌号':
                            display_val = val if str(val).strip() != "" else "无"
                            card_html += f"""
                            <div class="info-row">
                                <span class="info-label">{col}</span>
                                <span class="info-value">{display_val}</span>
                            </div>
                            """
                    
                    card_html += "</div>"
                    
                    # 【关键点】必须确保 unsafe_allow_html=True 才能显示卡片
                    st.markdown(card_html, unsafe_allow_html=True)
            else:
                st.warning(f"未找到包含 '{search_id}' 的记录")
