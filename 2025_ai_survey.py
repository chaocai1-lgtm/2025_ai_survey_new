import streamlit as st
import pandas as pd
import datetime
import requests
import json
from neo4j import GraphDatabase
from streamlit_autorefresh import st_autorefresh

# ================= 1. 基础配置 =================
FEISHU_APP_ID = st.secrets.get("FEISHU_APP_ID", "cli_a9c1c59555f81ceb")
FEISHU_APP_SECRET = st.secrets.get("FEISHU_APP_SECRET", "ldR79n02WB6CeA7OVA39af05RFXgEJqG")
FEISHU_APP_TOKEN = "BUCGbklpfaOob5soBs0cLnxDn5f"
FEISHU_TABLE_ID = "tblmi3cmtBGbTZJP"

NEO4J_URI = st.secrets.get("NEO4J_URI", "neo4j+ssc://7eb127cc.databases.neo4j.io")
NEO4J_USER = st.secrets.get("NEO4J_USERNAME", "neo4j")
NEO4J_PWD = st.secrets.get("NEO4J_PASSWORD", "wE7pV36hqNSo43mpbjTlfzE7n99NWcYABDFqUGvgSrk")
ADMIN_PWD = st.secrets.get("ADMIN_PASSWORD", "admin888")

QUESTIONS = {
    "q1": {"title": "1. 您目前对AI工具（如豆包、ChatGPT等）的了解和使用程度是？", "options": ["A. 完全不了解", "B. 听说过，但未尝试", "C. 偶尔尝试，未应用", "D. 经常使用，辅助工作", "E. 非常熟练"]},
    "q2": {"title": "2. 您最希望AI帮您解决哪类问题？（多选）", "options": ["A. 教学设计与教案", "B. 课件与素材制作", "C. 文档处理与办公效率", "D. 学生评价与作业批改", "E. 科研辅助与数据分析"]},
    "q3": {"title": "3. 您知道或使用过哪些类型的AI工具？（多选）", "options": ["A. 语言大模型类", "B. 绘画设计类", "C. PPT生成类", "D. 视频生成类", "E. 办公辅助类"]},
    "q4": {"title": "4. 【大模型专项】您具体了解或使用过哪些大语言模型？（多选）", "options": ["A. ChatGPT", "B. Claude", "C. Gemini", "D. Copilot", "E. 文心一言", "F. 通义千问", "G. Kimi", "H. 智谱清言", "I. 讯飞星火", "J. 豆包", "K. 腾讯混元", "L. DeepSeek", "M. 海螺AI", "N. 天工AI", "O. 百川智能"]},
    "q5": {"title": "5. 使用AI工具时，您遇到的最大困难是什么？", "options": ["A. 不知道好工具", "B. 不会写提示词", "C. 担心准确性/版权", "D. 操作太复杂", "E. 缺乏应用场景"]},
    "q6": {"title": "6. 您对本次AI培训最期待的收获是什么？", "options": ["A. 了解AI概念趋势", "B. 掌握实用工具", "C. 学习写提示词", "D. 看教学案例", "E. 现场实操指导"]}
}

# ================= 2. 核心功能 =================

class FeishuTool:
    @staticmethod
    def send(name, answers):
        st.write("🔍 正在启动飞书同步...")
        # 1. 获取令牌
        t_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        try:
            t_res = requests.post(t_url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10).json()
            token = t_res.get("tenant_access_token")
            if not token:
                st.error(f"❌ 无法从飞书获取Token: {t_res.get('msg')}")
                return False
        except Exception as e:
            st.error(f"❌ 请求Token时发生错误: {e}")
            return False

        # 2. 准备数据
        def wrap(q_key, val):
            title = QUESTIONS[q_key]["title"]
            ans = "、".join(val) if isinstance(val, list) else (val if val else "未选")
            return f"题：{title}\n答：{ans}"

        fields = {
            "姓名": name,
            "Q1": wrap("q1", answers.get("q1")),
            "Q2": wrap("q2", answers.get("q2")),
            "Q3": wrap("q3", answers.get("q3")),
            "Q4": wrap("q4", answers.get("q4")),
            "Q5": wrap("q5", answers.get("q5")),
            "Q6": wrap("q6", answers.get("q6")),
            "时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        # 3. 发送数据
        api_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
        
        try:
            r = requests.post(api_url, headers=headers, json={"fields": fields}, timeout=10)
            res_data = r.json()
            if res_data.get("code") == 0:
                st.success("✨ 飞书写入成功！")
                return True
            else:
                st.error(f"❌ 飞书服务器拒绝写入: {res_data.get('msg')}")
                st.info("调试详情：")
                st.json(res_data) # 把错误详情直接贴在页面上
                return False
        except Exception as e:
            st.error(f"❌ 发送数据失败: {e}")
            return False

# ================= 3. 页面渲染 =================
st.set_page_config(page_title="AI 调研", layout="wide")

with st.sidebar:
    mode = st.radio("模式选择", ["问卷填报", "看板"])

if mode == "问卷填报":
    st.title("🤖 教师 AI 使用调研")
    with st.form("main_form"):
        u_name = st.text_input("姓名 *")
        ans_q1 = st.radio(QUESTIONS["q1"]["title"], QUESTIONS["q1"]["options"], index=None)
        
        st.write(QUESTIONS["q2"]["title"])
        ans_q2 = [o for o in QUESTIONS["q2"]["options"] if st.checkbox(o, key=f"f2_{o}")]
        
        st.write(QUESTIONS["q3"]["title"])
        ans_q3 = [o for o in QUESTIONS["q3"]["options"] if st.checkbox(o, key=f"f3_{o}")]
        
        st.write(QUESTIONS["q4"]["title"])
        ans_q4 = [o for o in QUESTIONS["q4"]["options"] if st.checkbox(o, key=f"f4_{o}")]
        
        ans_q5 = st.radio(QUESTIONS["q5"]["title"], QUESTIONS["q5"]["options"], index=None)
        ans_q6 = st.radio(QUESTIONS["q6"]["title"], QUESTIONS["q6"]["options"], index=None)
        
        # 为了兼容性，不写新参数
        sub_btn = st.form_submit_button("确认提交", type="primary", use_container_width=True)
        
        if sub_btn:
            if not u_name or not ans_q1:
                st.warning("请填写姓名和 Q1")
            else:
                # 执行飞书同步并显示状态
                FeishuTool.send(u_name, {"q1":ans_q1, "q2":ans_q2, "q3":ans_q3, "q4":ans_q4, "q5":ans_q5, "q6":ans_q6})
                
                # Neo4j 部分（简单处理防止阻塞）
                try:
                    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
                    with driver.session() as s:
                        s.run("CREATE (n:Teacher {name:$n, q1:$q1})", n=u_name, q1=ans_q1)
                except: pass
                st.balloons()

else:
    st.title("数据概览")
    st.write("请在侧边栏切换回填报模式。")