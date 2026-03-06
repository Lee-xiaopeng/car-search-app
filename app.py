import streamlit as st
import pandas as pd
import gspread
import json
import time
import threading
import requests
import logging
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from typing import Optional, Dict, Any

# -------------------------- 日志配置 --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# -------------------------- 全局配置 --------------------------
# 后台任务间隔（秒），原10分钟（600秒），可根据需要调整
BACKGROUND_TASK_INTERVAL = 600
# Google Sheet 名称
SHEET_NAME = "PlateDB"
# 心跳检测URL（替换为实际URL）
HEARTBEAT_URL = "https://your-api-url.com/heartbeat"

# -------------------------- 后台任务优化 --------------------------
class BackgroundTaskManager:
    """后台任务管理器，确保线程唯一且安全退出"""
    _instance = None
    _lock = threading.Lock()
    _thread: Optional[threading.Thread] = None
    _running = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def start_task(self):
        """启动后台任务，确保只启动一次"""
        with self._lock:
            if not self._running and self._thread is None:
                self._running = True
                self._thread = threading.Thread(target=self._background_task, daemon=True)
                self._thread.start()
                logger.info("后台心跳任务线程已启动")

    def _background_task(self):
        """后台心跳任务，增加异常处理和优雅退出"""
        while self._running:
            try:
                response = requests.get(HEARTBEAT_URL, timeout=10)
                if response.status_code == 200:
                    logger.info(f"心跳检测成功，状态码: {response.status_code}")
                else:
                    logger.warning(f"心跳检测异常，状态码: {response.status_code}")
            except requests.exceptions.Timeout:
                logger.error("心跳检测超时")
            except requests.exceptions.RequestException as e:
                logger.error(f"心跳检测请求失败: {str(e)}")
            except Exception as e:
                logger.error(f"心跳任务执行异常: {str(e)}")
            
            # 优雅的等待，支持中断
            for _ in range(BACKGROUND_TASK_INTERVAL):
                if not self._running:
                    break
                time.sleep(1)

    def stop_task(self):
        """停止后台任务"""
        with self._lock:
            self._running = False
            if self._thread is not None:
                self._thread.join(timeout=5)
                self._thread = None
                logger.info("后台心跳任务已停止")

# -------------------------- 页面配置（仅执行一次） --------------------------
def setup_page_config():
    """初始化页面配置，避免重复调用"""
    if not hasattr(st.session_state, "page_config_set"):
        st.set_page_config(
            page_title="车辆信息管理系统",
            page_icon="🚗",
            layout="centered",
            initial_sidebar_state="auto"
        )
        st.session_state.page_config_set = True

# -------------------------- 数据库连接优化 --------------------------
@st.cache_resource(ttl=3600)  # 1小时自动刷新连接，避免长期连接泄漏
def init_connection() -> Optional[gspread.Worksheet]:
    """初始化Google Sheet连接，增加重试和详细错误处理"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    max_retries = 3
    
    for retry in range(max_retries):
        try:
            # 从secrets加载配置
            json_info = st.secrets["gcp_service_account"]["json_data"].replace("\\\\n", "\\n")
            creds_dict = json.loads(json_info)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            
            # 授权并连接
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            logger.info("Google Sheet连接成功")
            return sheet
        
        except json.JSONDecodeError as e:
            st.error(f"配置解析失败（JSON格式错误）: {str(e)}")
            break
        except KeyError as e:
            st.error(f"配置缺失关键字段: {str(e)}")
            break
        except Exception as e:
            logger.warning(f"连接失败（重试 {retry+1}/{max_retries}）: {str(e)}")
            if retry == max_retries - 1:
                st.error(f"数据库连接失败（已重试{max_retries}次）: {str(e)}")
            time.sleep(2)  # 重试间隔
    
    return None

# -------------------------- CSS样式（优化版） --------------------------
def load_custom_css():
    """加载自定义CSS样式"""
    st.markdown("""
    <style>
    /* 基础隐藏样式 */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    [data-testid="stStatusWidget"] { display: none; }
    .stDeployButton { display: none; }
    
    /* 工具栏样式 */
    [data-testid="stToolbar"] { 
        visibility: visible !important; 
        opacity: 1 !important; 
    }
    [data-testid="stHeader"] { 
        visibility: visible !important; 
        background: rgba(0,0,0,0) !important; 
    }
    
    /* Logo容器 */
    .logo-container {
        position: fixed;
        top: 45px;
        right: 15px;
        z-index: 9999;
    }
    .custom-logo { 
        width: 75px;
        height: auto;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
    }
    
    /* 标题样式 */
    .main-title {
        text-align: center; 
        margin: 2.5rem 0 2rem 0; 
        font-size: 1.8rem; 
        white-space: nowrap; 
        color: var(--text-color) !important; 
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    
    /* 按钮样式 */
    .stButton {
        display: flex;
        justify-content: center;
        width: 100%;
    }
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
    
    /* 结果卡片样式 */
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
    .info-value:empty::before {
        content: "—";
        color: #adb5bd;
        font-style: italic;
    }
    
    /* 输入框样式 */
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
    
    /* 消息提示样式 */
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
    
    /* 页面布局 */
    .main .block-container {
        padding-top: 2.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 800px !important;
    }
    [data-testid="stSidebar"] {
        padding-top: 2rem;
    }
    [data-testid="stSidebarNav"] {
        padding-top: 1rem;
    }
    .stApp {
        padding-top: 0.5rem;
    }
    
    /* 移动端适配 */
    @media (max-width: 768px) {
        .main-title {
            font-size: 1.5rem;
            margin: 2rem 0 1.5rem 0;
        }
        .custom-logo { 
            width: 65px;
        }
        .logo-container {
            top: 45px;
            right: 10px;
        }
        .stButton button {
            width: 100% !important;
            max-width: 300px;
            margin: 0 auto;
        }
        .stTextInput input {
            font-size: 16px !important;
        }
        [data-testid="stToolbar"] {
            right: 5px !important;
        }
    }
    
    /* 桌面端适配 */
    @media (min-width: 769px) {
        .custom-logo { 
            width: 250px;
        }
        .logo-container { 
            top: 30px;
            right: 25px; 
        }
    }
    </style>
    
    <!-- Logo 容器 -->
    <div class="logo-container">
        <img src="https://cloud-assets-brwq.bcdn8.com/weice0314/uploads/20230314/46fd5ef88f68a88ea9858999c63b6362.svg" 
             class="custom-logo" 
             alt="Logo">
    </div>
    """, unsafe_allow_html=True)

# -------------------------- 数据查询优化 --------------------------
def search_vehicle_info(sheet: gspread.Worksheet, search_term: str) -> pd.DataFrame:
    """
    优化的车辆信息查询函数
    - 减少内存占用
    - 增加数据类型处理
    - 避免重复计算
    """
    try:
        # 批量获取数据并转换为DataFrame
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # 空数据处理
        if df.empty:
            logger.info("数据库中无数据")
            return pd.DataFrame()
        
        # 确保车牌号列是字符串类型，避免类型错误
        df["车牌号"] = df["车牌号"].astype(str).str.upper().str.strip()
        search_term = search_term.upper().strip()
        
        # 执行包含查询（连续4位匹配）
        result = df[df["车牌号"].str.contains(search_term, na=False)]
        logger.info(f"查询关键词「{search_term}」，找到 {len(result)} 条记录")
        
        return result
    
    except Exception as e:
        logger.error(f"查询失败: {str(e)}")
        raise

# -------------------------- 主程序逻辑 --------------------------
def main():
    # 1. 初始化页面配置
    setup_page_config()
    
    # 2. 加载CSS样式
    load_custom_css()
    
    # 3. 启动后台任务
    task_manager = BackgroundTaskManager()
    task_manager.start_task()
    
    # 4. 初始化数据库连接
    sheet = init_connection()
    
    # 5. 侧边栏管理功能
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
                                # 数据清洗
                                new_row = [
                                    f1.strip(), f2.strip(), f3.strip(),
                                    f4.strip(), f5.strip(), f6.upper().strip()
                                ]
                                sheet.append_row(new_row)
                                st.success("✅ 保存成功！")
                                # 清除连接缓存，强制重新加载数据
                                st.cache_resource.clear()
                                logger.info(f"新增记录: {new_row}")
                            except Exception as e:
                                st.error(f"保存失败: {str(e)}")
                                logger.error(f"保存记录失败: {str(e)}")
                        else:
                            st.warning("车牌号为必填项")
        
    # 6. 主界面查询功能
    st.markdown('<div class="main-title">🚗 车辆信息智能检索</div>', unsafe_allow_html=True)
    
    with st.form("search_form"):
        search_id = st.text_input(
            "车牌号码查询", 
            placeholder="请输入车牌中任意连续4位...", 
            label_visibility="visible",
            help="支持模糊查询，输入车牌号中的任意连续4位即可"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("🔍 立即搜索", use_container_width=True)
    
    # 7. 处理查询请求
    if submitted or (search_id and search_id.strip()):
        query = search_id.strip()
        
        if not query:
            st.warning("⚠️ 请输入查询关键词")
        elif len(query) < 4:
            st.warning("⚠️ 关键词太短，请至少输入 4 位字符以确保查询准确性")
        else:
            if not sheet:
                st.error("❌ 数据库无法连接，请稍后重试")
            else:
                with st.spinner("🔍 正在检索数据库..."):
                    try:
                        result_df = search_vehicle_info(sheet, query)
                        
                        if not result_df.empty:
                            # 显示结果统计
                            st.markdown(f"""
                                <div style="background: linear-gradient(135deg, #e7f5ff, #d0ebff); 
                                            border-radius: 12px; 
                                            padding: 1rem; 
                                            margin: 1rem 0; 
                                            text-align: center;
                                            border-left: 4px solid #339af0;">
                                    <div style="font-size: 1.1rem; color: #1c7ed6; font-weight: 600;">
                                        📊 共找到 {len(result_df)} 辆车
                                    </div>
                                    <div style="font-size: 0.9rem; color: #495057; margin-top: 0.5rem;">
                                        搜索关键词: <span style="font-weight: 700; color: #e03131;">{query.upper()}</span>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            # 展示每条记录
                            for _, row in result_df.iterrows():
                                card_html = f'<div class="vehicle-card"><div class="plate-header">车牌：{row["车牌号"]}</div>'
                                for col in result_df.columns:
                                    if col != "车牌号":
                                        val = str(row[col]).strip() if pd.notna(row[col]) and str(row[col]).strip() else "—"
                                        card_html += f'<div class="info-row"><span class="info-label">{col}</span><span class="info-value">{val}</span></div>'
                                card_html += '</div>'
                                st.markdown(card_html, unsafe_allow_html=True)
                        else:
                            st.warning(f"❌ 未找到包含「{query.upper()}」的车辆信息")
                    
                    except Exception as e:
                        st.error(f"查询过程发生错误: {str(e)}")
                        logger.error(f"查询错误: {str(e)}")

# -------------------------- 程序入口 --------------------------
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"程序异常退出: {str(e)}")
        st.error(f"系统异常: {str(e)}")
    finally:
        # 确保后台任务优雅退出
        task_manager = BackgroundTaskManager()
        task_manager.stop_task()
