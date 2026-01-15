import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
import qrcode
from io import BytesIO

# --- 1. 页面基本配置 ---
st.set_page_config(
    page_title="车辆信息管理系统",
    page_icon="🚗",
    layout="centered"
)

# --- 2. 自定义美化样式 (CSS) ---
# 修复了 unsafe_allow_html 参数名
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .result-card {
        padding: 20px;
        border-radius: 10px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        color: #31333F;
    }
    .status-badge {
        padding: 5px 12px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.8em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 数据库连接逻辑 (V1.5 稳定版) ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # 获取 Secrets 中的 JSON 数据并修复可能的转义错误
        json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
        creds_dict = json.loads(json_info)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # 表格名称需与 Google Sheets 一致
        return client.open("PlateDB").sheet1
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        return None

sheet = init_connection()

# --- 4. 界面头部 ---
st.title("🚗 车辆信息智能查询")
st.info("请输入连续4位车牌号码进行检索")

# --- 5. 查询交互区域 ---
# 增加一个表单，按下回车即可触发查询
with st.form("search_form"):
    search_id = st.text_input("车牌号检索", placeholder="例如: B123")
    search_btn = st.form_submit_button("立即查询")

# --- 6. 结果展示逻辑 ---
if search_btn and search_id:
    if not sheet:
        st.error("数据库未连接，请检查后台配置。")
    else:
        with st.spinner("数据检索中..."):
            # 获取所有数据并转为 DataFrame
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # 匹配逻辑 (不区分大小写)
            result = df[df['车牌号'].astype(str).str.upper() == search_id.strip().upper()]
            
            if not result.empty:
                st.success(f"✅ 已找到匹配记录")
                row = result.iloc[0]
                
                # HTML 卡片展示
                st.markdown(f"""
                <div class="result-card">
                    <h3 style="margin-top:0;">车牌号：{row['车牌号']}</h3>
                    <p><b>品牌型号：</b> {row.get('品牌', '未知')} {row.get('型号', '')}</p>
                    <p><b>车身颜色：</b> {row.get('颜色', '未知')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 状态显示
                status = row.get('状态', '正常')
                st.metric("当前状态", status)
                
            else:
                st.error("❌ 抱歉，数据库中没有该车牌的信息。")

# --- 7. 页脚 ---
st.markdown("---")
