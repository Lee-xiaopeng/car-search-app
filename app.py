import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 页面配置 ---
st.set_page_config(page_title="车辆信息管理系统", layout="centered")

# --- 2. 核心 CSS 样式 ---
st.markdown("""
    <style>
    .vehicle-card {
        background-color: white; border-radius: 12px; padding: 15px;
        margin-bottom: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 5px solid #007bff; color: #31333F;
    }
    .plate-number { color: #007bff; font-size: 20px; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #eee; }
    .info-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dashed #f0f0f0; }
    .info-label { color: #666; font-size: 14px; }
    .info-value { color: #1a1a1a; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True) # 确保 HTML 解析生效

# --- 3. 数据库连接 (复用稳定逻辑) ---
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
        st.error(f"数据库连接失败: {e}")
        return None

sheet = init_connection()

# --- 4. 侧边栏：管理员登录 ---
with st.sidebar:
    st.title("⚙️ 管理员入口")
    admin_password = st.text_input("请输入管理密码", type="password")
    # 你可以在这里设置你的密码，例如 "plate123"
    is_admin = (admin_password == "admin888") 
    
    if is_admin:
        st.success("已进入管理模式")
        st.divider()
        st.subheader("新增车辆记录")
        with st.form("add_data_form", clear_on_submit=True):
            new_plate = st.text_input("车牌号 *")
            new_brand = st.text_input("品牌")
            new_model = st.text_input("型号")
            new_color = st.selectbox("颜色", ["白色", "黑色", "蓝色", "红色", "灰色", "其它"])
            new_status = st.selectbox("状态", ["正常", "维修中", "已注销"])
            new_note = st.text_area("备注")
            
            submit_add = st.form_submit_button("确认新增并上传")
            
            if submit_add:
                if new_plate:
                    try:
                        # 将数据追加到 Google Sheets 底部
                        sheet.append_row([new_plate, new_brand, new_model, new_color, new_status, new_note])
                        st.balloons()
                        st.success(f"车辆 {new_plate} 已成功存入数据库！")
                        # 清除缓存以便立即能搜到新数据
                        st.cache_resource.clear()
                    except Exception as e:
                        st.error(f"写入失败: {e}")
                else:
                    st.warning("车牌号是必填项")

# --- 5. 主界面：查询功能 ---
st.title("🚗 车辆信息查询")
st.info("普通用户直接在下方输入查询即可")

with st.form("search_form"):
    search_id = st.text_input("请输入车牌号关键词 (任意连续4位)", placeholder="例如: 39L7")
    submitted = st.form_submit_button("立即搜索")

# --- 6. 结果展示 ---
if (submitted or search_id) and search_id.strip():
    if not sheet:
        st.error("数据库未连接")
    else:
        with st.spinner("检索中..."):
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            # 模糊匹配逻辑
            query = search_id.strip().upper()
            result = df[df['车牌号'].astype(str).str.upper().str.contains(query)]
            
            if not result.empty:
                st.success(f"找到 {len(result)} 条记录")
                for _, row in result.iterrows():
                    card_content = f'<div class="vehicle-card">'
                    card_content += f'<div class="plate-number">车牌：{row["车牌号"]}</div>'
                    for col, val in row.items():
                        if col != "车牌号":
                            val = val if str(val).strip() != "" else "无"
                            card_content += f'<div class="info-row"><span class="info-label">{col}</span><span class="info-value">{val}</span></div>'
                    card_content += '</div>'
                    st.markdown(card_content, unsafe_allow_html=True)
            else:
                st.warning(f"未找到相关信息")
