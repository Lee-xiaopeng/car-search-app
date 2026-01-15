import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 页面配置 ---
st.set_page_config(page_title="车辆检索系统", layout="centered")

# --- 2. 核心 CSS 样式 ---
st.markdown("""
    <style>
    .vehicle-card {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 5px solid #007bff;
        color: #31333F;
    }
    .plate-number {
        color: #007bff;
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 10px;
        border-bottom: 1px solid #eee;
    }
    .info-row {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px dashed #f0f0f0;
    }
    .info-label { color: #666; font-size: 14px; }
    .info-value { color: #1a1a1a; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True) # <--- 这里的参数必须正确！

# --- 3. 数据库连接 ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # 修复密钥转义
        json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
        creds_dict = json.loads(json_info)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("PlateDB").sheet1
    except Exception as e:
        st.error(f"连接失败: {e}")
        return None

sheet = init_connection()

# --- 4. 搜索界面 ---
st.title("🚗 车辆信息查询")

with st.form("search_form"):
    search_id = st.text_input("车牌号检索", placeholder="请输入4位车牌内容...")
    submitted = st.form_submit_button("立即搜索")

# --- 5. 结果显示 ---
if (submitted or search_id) and search_id.strip():
    if not sheet:
        st.error("数据库未连接")
    else:
        with st.spinner("检索中..."):
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # 模糊匹配
            query = search_id.strip().upper()
            result = df[df['车牌号'].astype(str).str.upper().str.contains(query)]
            
            if not result.empty:
                st.success(f"找到 {len(result)} 条记录")
                
                # 为每条结果生成一个独立的卡片
                for _, row in result.iterrows():
                    # 1. 先构建该卡片的完整 HTML 字符串
                    card_content = f'<div class="vehicle-card">'
                    card_content += f'<div class="plate-number">车牌：{row["车牌号"]}</div>'
                    
                    for col, val in row.items():
                        if col != "车牌号":
                            val = val if str(val).strip() != "" else "无"
                            card_content += f'''
                            <div class="info-row">
                                <span class="info-label">{col}</span>
                                <span class="info-value">{val}</span>
                            </div>'''
                    
                    card_content += '</div>'
                    
                    # 2. 【最重要】通过 st.markdown 渲染该 HTML
                    st.markdown(card_content, unsafe_allow_html=True) 
            else:
                st.warning(f"未找到 '{search_id}'")
