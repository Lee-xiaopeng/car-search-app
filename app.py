import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO

# --- 1. 页面基本配置 ---
st.set_page_config(
    page_title="车辆信息查询",
    page_icon="🚗",
    layout="centered" # 保持居中，在手机上会自动铺满
)

# --- 2. 手机端优化样式 (CSS) ---
st.markdown("""
    <style>
    /* 整体背景 */
    .main { background-color: #f8f9fa; }
    
    /* 搜索框在手机上的字体大小优化 */
    .stTextInput input {
        font-size: 18px !important;
        height: 50px !important;
    }

    /* 优化结果卡片：移除阴影改为细边框，增加手机触感 */
    .result-card {
        padding: 15px;
        border-radius: 12px;
        background-color: white;
        border: 1px solid #e0e0e0;
        margin-bottom: 15px;
        color: #31333F;
    }
    
    /* 字段名样式 */
    .field-label {
        color: #6c757d;
        font-size: 14px;
        margin-bottom: 2px;
    }
    
    /* 字段值样式 */
    .field-value {
        color: #1a1a1a;
        font-size: 16px;
        font-weight: 500;
        margin-bottom: 10px;
        border-bottom: 1px dashed #eee;
        padding-bottom: 5px;
    }
    
    .field-value:last-child { border-bottom: none; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 数据库连接 (保持 v1.5 稳定逻辑) ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # 兼容处理反斜杠问题
        json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
        creds_dict = json.loads(json_info)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client.open("PlateDB").sheet1
    except Exception as e:
        st.error(f"数据库连接失败: {e}")
        return None

sheet = init_connection()

# --- 4. 界面头部 ---
st.title("🚗 车辆信息查询")
st.caption("支持输入车牌中任意连续 4 位数字或字母")

# --- 5. 查询交互区域 ---
with st.form("search_form"):
    search_id = st.text_input("车牌号检索", placeholder="输入车牌后4位...", help="例如车牌为粤BQ39L7，输入39L7即可")
    search_btn = st.form_submit_button("开始查询")

# --- 6. 结果展示逻辑 ---
if (search_btn or search_id) and search_id.strip():
    if not sheet:
        st.error("无法访问数据库，请联系管理员检查 Secrets 配置。")
    else:
        with st.spinner("正在检索数据..."):
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # --- 核心改动 1：模糊匹配 (包含查询) ---
            # 将输入和数据库字段都转为大写，并判断输入是否在车牌号列中
            search_query = search_id.strip().upper()
            result = df[df['车牌号'].astype(str).str.upper().str.contains(search_query)]
            
            if not result.empty:
                st.success(f"找到 {len(result)} 条结果")
                
                # 遍历查询到的每一行记录
                for _, row in result.iterrows():
                    # --- 核心改动 2 & 3：手机端优化 + 展示所有字段 ---
                    with st.container():
                        html_content = f'<div class="result-card">'
                        html_content += f'<h3 style="color:#007bff; margin-top:0;">车牌：{row["车牌号"]}</h3>'
                        
                        # 遍历该行的所有列（排除掉已经显示的“车牌号”）
                        for col_name, value in row.items():
                            if col_name != "车牌号":
                                html_content += f'''
                                    <div class="field-label">{col_name}</div>
                                    <div class="field-value">{value if value != "" else "无"}</div>
                                '''
                        
                        html_content += '</div>'
                        st.markdown(html_content, unsafe_allow_html=True)
            else:
                st.warning(f"❌ 未找到包含 '{search_id}' 的车辆信息")

# --- 7. 页脚 ---
st.markdown("---")
st.caption("数据更新时间：2026-01-15 | 内部查询系统")
