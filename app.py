import streamlit as st
import time
import threading
import requests

# 保活函数：定时访问自己的应用，避免空闲超时
def keep_alive():
    # 替换为你的 share.streamlit 应用地址
    app_url = "https://your-username-your-repo-name.streamlit.app/"
    while True:
        try:
            requests.get(app_url, timeout=10)
            st.write(f"保活请求发送成功 - {time.ctime()}")
        except Exception as e:
            st.write(f"保活请求失败: {e}")
        # 每10分钟发送一次请求（小于15分钟超时阈值）
        time.sleep(600)

# 启动保活线程（仅在部署环境运行）
if not st.runtime.exists():
    threading.Thread(target=keep_alive, daemon=True).start()

# 你的主应用代码
st.title("我的 Streamlit 应用")
