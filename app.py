import streamlit as st
import pandas as pd
import gspread
import json
import time
import threading
import requests
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import traceback

# --- 全局变量：线程控制标志 ---
if 'thread_stop_flag' not in st.session_state:
    st.session_state.thread_stop_flag = False

# --- 优化：后台定时任务函数（增加异常捕获/退出机制） ---
def background_task():
    """
    每小时执行一次的后台任务
    访问指定的URL，可以用于保持应用活跃或执行定时任务
    """
    target_url = "https://your-api-url.com/heartbeat"  # 请替换为实际的URL
    retry_interval = 60  # 单次失败后重试间隔（秒）
    hour_interval = 600  # 1小时=3600秒
    
    while not st.session_state.thread_stop_flag:  # 增加退出标志
        try:
            # 记录任务执行时间
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] 执行后台任务，访问URL: {target_url}")
            
            # 访问URL（增加超时+重试）
            response = requests.get(
                target_url, 
                timeout=10,
                headers={"User-Agent": "Streamlit App/1.0"}  # 增加UA避免被拦截
            )
            
            if response.status_code == 200:
                print(f"[{current_time}] URL访问成功: {response.status_code}")
            else:
                print(f"[{current_time}] URL访问异常: {response.status_code}")
                
        except requests.exceptions.Timeout:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] 后台任务超时：URL请求超过10秒")
            time.sleep(retry_interval)  # 短重试后继续
            continue
        except requests.exceptions.ConnectionError:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] 后台任务连接失败：网络/URL不可达")
            time.sleep(retry_interval)
            continue
        except Exception as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] 后台任务执行失败: {str(e)}")
            print(traceback.format_exc())  # 打印完整堆栈，便于排查
        
        # 等待1小时（修复休眠时间），同时检测退出标志
        for _ in range(hour_interval // 10):  # 每10秒检查一次退出标志
            if st.session_state.thread_stop_flag:
                break
            time.sleep(10)

# --- 优化：启动后台任务（更健壮的线程管理） ---
@st.cache_resource(ttl=3600)  # 增加缓存过期，避免永久缓存
def start_background_task():
    """
    启动后台任务线程
    确保线程唯一且可退出
    """
    # 停止旧线程（如果存在）
    if hasattr(st.session_state, 'background_thread') and st.session_state.background_thread.is_alive():
        st.session_state.thread_stop_flag = True
        st.session_state.background_thread.join(timeout=30)  # 等待线程退出
    
    # 重置退出标志
    st.session_state.thread_stop_flag = False
    
    try:
        # 创建并启动后台线程
        task_thread = threading.Thread(target=background_task, daemon=True)
        task_thread.start()
        st.session_state.background_thread = task_thread
        st.session_state.background_task_started = True
        print("后台任务线程已启动")
    except Exception as e:
        print(f"启动后台任务失败: {str(e)}")
        print(traceback.format_exc())
    return True

# --- 1. 页面配置（修复重复调用问题） ---
if not hasattr(st.session_state, 'page_config_set'):
    st.set_page_config(
        page_title="车辆信息管理系统",
        page_icon="🚗",
        layout="centered",
        initial_sidebar_state="auto"
    )
    st.session_state.page_config_set = True

# 启动后台任务
start_background_task()

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
        top: 45px; /* 下移Logo位置，为工具栏留出空间 */
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
            top: 45px; /* 移动端下移 */
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
            width: 250px; /* 桌面端更大 */
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

# --- 3. 数据库连接（增加重试/超时） ---
@st.cache_resource(ttl=1800)  # 30分钟刷新一次连接，避免长期连接失效
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    max_retries = 3  # 连接失败重试次数
    retry_delay = 5  # 重试间隔（秒）
    
    for attempt in range(max_retries):
        try:
            json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
            creds_dict = json.loads(json_info)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            # 增加连接超时
            client = gspread.authorize(creds, timeout=30)
            sheet = client.open("PlateDB").sheet1
            print(f"数据库连接成功（第{attempt+1}次尝试）")
            return sheet
        except Exception as e:
            print(f"数据库连接失败（第{attempt+1}次尝试）: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                st.error(f"数据库连接失败（已重试{max_retries}次）：{str(e)}")
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
                            # 清除缓存但不影响线程
                            st.cache_resource.clear(exceptions=[start_background_task])
                        except Exception as e:
                            st.error(f"保存失败: {e}")
                            print(traceback.format_exc())
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

# --- 6. 结果展示与逻辑（增加异常防护 + 修复continue语法错误） ---
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
                st.error("数据库无法连接，请稍后重试")
            else:
                with st.spinner("🔍 正在检索数据库..."):
                    try:
                        # 增加数据读取超时
                        data = sheet.get_all_records(timeout=30)
                        df = pd.DataFrame(data)
                        
                        # 空数据处理（修复continue语法错误）
                        if df.empty:
                            st.warning("📊 数据库中暂无车辆信息")
                        else:
                            # 4. 逻辑修改：转大写后进行包含匹配 (Contains)
                            search_term = query.upper()
                            result = df[df['车牌号'].astype(str).str.upper().str.contains(search_term, na=False)]
                            
                            if not result.empty:
                                # 添加结果统计卡片
                                st.markdown(f"""
                                    <div style="background: linear-gradient(135deg, #e7f5ff, #d0ebff); 
                                                border-radius: 12px; 
                                                padding: 1rem; 
                                                margin: 1rem 0; 
                                                text-align: center;
                                                border-left: 4px solid #339af0;">
                                        <div style="font-size: 1.1rem; color: #1c7ed6; font-weight: 600;">
                                            📊 共找到 {len(result)} 辆车
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
                    except gspread.exceptions.APIError as e:
                        st.error(f"📡 数据库接口错误：{e}，请稍后重试")
                        print(traceback.format_exc())
                    except Exception as e:
                        st.error(f"❌ 查询过程发生错误：{str(e)}，请稍后重试")
                        print(traceback.format_exc())

# --- 7. 应用退出清理（可选） ---
def cleanup():
    """应用退出时清理资源"""
    st.session_state.thread_stop_flag = True
    if hasattr(st.session_state, 'background_thread'):
        st.session_state.background_thread.join(timeout=10)
    print("应用资源已清理")

# Streamlit 关闭时触发清理（需配合服务器配置）
import atexit
atexit.register(cleanup)
