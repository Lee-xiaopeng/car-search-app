import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. 页面配置 ---
st.set_page_config(page_title="车辆信息查询系统", layout="centered")

# --- 2. 核心 CSS 样式（确保 HTML 正常解析并美化） ---
st.markdown("""
    <style>
    /* 卡片容器美化 */
    .vehicle-card {
        background-color: white; border-radius: 12px; padding: 20px;
        margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-left: 5px solid #007bff; color: #31333F;
    }
    .plate-header { color: #007bff; font-size: 22px; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
    .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #f0f0f0; }
    .info-label { color: #666; font-size: 14px; }
    .info-value { color: #1a1a1a; font-weight: 500; font-size: 15px; }
    /* 侧边栏表单美化 */
    .stButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True) # 核心修复点：参数必须准确

# --- 3. 数据库连接 ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # 处理密钥转义问题
        json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
        creds_dict = json.loads(json_info)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        # 打开名为 PlateDB 的表格
        return client.open("PlateDB").sheet1
    except Exception as e:
        st.error(f"连接失败: {e}")
        return None

sheet = init_connection()

# --- 4. 侧边栏：管理员后台 (匹配 image_6aebca.png 字段) ---
with st.sidebar:
    st.title("⚙️ 数据维护")
    pwd = st.text_input("管理密码", type="password")
    if pwd == "admin888": # 请自行修改此密码
        st.success("验证通过")
        st.divider()
        with st.form("add_form", clear_on_submit=True):
            f1 = st.text_input("工号")
            f2 = st.text_input("姓名")
            f3 = st.text_input("部门")
            f4 = st.text_input("厂区")
            f5 = st.text_input("手机号")
            f6 = st.text_input("车牌号 *")
            
            if st.form_submit_button("保存到数据库"):
                if f6:
                    try:
                        # 严格按照表格 A-F 列顺序追加
                        sheet.append_row([f1, f2, f3, f4, f5, f6.upper()])
                        st.success("✅ 新增成功！")
                        st.cache_resource.clear() # 刷新缓存
                    except Exception as e:
                        st.error(f"保存失败: {e}")
                else:
                    st.warning("车牌号不能为空")

# --- 5. 主界面：查询功能 ---
st.title("🚗 车辆信息智能检索")

with st.form("search_form"):
    search_query = st.text_input("车牌号检索", placeholder="输入车牌中任意连续4位...")
    submitted = st.form_submit_button("立即搜索")

# --- 6. 结果展示 (修复 image_6a89f0.png 的显示问题) ---
if (submitted or search_query) and search_query.strip():
    if not sheet:
        st.error("数据库未就绪")
    else:
        with st.spinner("查询中..."):
            df = pd.DataFrame(sheet.get_all_records())
            
            # 模糊匹配
            q = search_query.strip().upper()
            res = df[df['车牌号'].astype(str).str.upper().str.contains(q)]
            
            if not res.empty:
                st.success(f"找到 {len(res)} 条结果")
                for _, row in res.iterrows():
                    # 构建美化卡片 HTML
                    html = f'<div class="vehicle-card"><div class="plate-header">车牌：{row["车牌号"]}</div>'
                    
                    # 动态显示所有字段（如：工号、姓名、部门等）
                    for col in df.columns:
                        if col != "车牌号":
                            val = row[col] if str(row[col]).strip() != "" else "无"
                            html += f'<div class="info-row"><span class="info-label">{col}</span><span class="info-value">{val}</span></div>'
                    
                    html += '</div>'
                    # 【关键】使用 unsafe_allow_html=True 确保不显示源码
                    st.markdown(html, unsafe_allow_html=True)
            else:
                st.warning("❌ 未找到匹配记录")
