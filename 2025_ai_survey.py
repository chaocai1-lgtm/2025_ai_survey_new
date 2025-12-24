import streamlit as st
import pandas as pd
import datetime
import requests
import json
from neo4j import GraphDatabase
from streamlit_autorefresh import st_autorefresh
from streamlit_echarts import st_pyecharts
from pyecharts import options as opts
from pyecharts.charts import Bar, Pie

# ================= 1. 配置信息 =================
# 建议在 Streamlit Cloud 后台 Secrets 设置这些值
FEISHU_APP_ID = st.secrets.get("FEISHU_APP_ID", "cli_a9c1c59555f81ceb")
FEISHU_APP_SECRET = st.secrets.get("FEISHU_APP_SECRET", "ldR79n02WB6CeA7OVA39af05RFXgEJqG")
FEISHU_APP_TOKEN = "BUCGbklpfaOob5soBs0cLnxDn5f"
FEISHU_TABLE_ID = "tblmi3cmtBGbTZJP"

NEO4J_URI = st.secrets.get("NEO4J_URI", "neo4j+ssc://7eb127cc.databases.neo4j.io")
NEO4J_USER = st.secrets.get("NEO4J_USERNAME", "neo4j")
NEO4J_PWD = st.secrets.get("NEO4J_PASSWORD", "wE7pV36hqNSo43mpbjTlfzE7n99NWcYABDFqUGvgSrk")
ADMIN_PWD = st.secrets.get("ADMIN_PASSWORD", "admin888")

# 问卷题目
QUESTIONS = {
    "q1": {"title": "1. 您目前对AI工具（如豆包、ChatGPT等）的了解和使用程度是？", "options": ["A. 完全不了解", "B. 听说过，但未尝试", "C. 偶尔尝试，未应用", "D. 经常使用，辅助工作", "E. 非常熟练"]},
    "q2": {"title": "2. 您最希望AI帮您解决哪类问题？（多选）", "options": ["A. 教学设计与教案", "B. 课件与素材制作", "C. 文档处理与办公效率", "D. 学生评价与作业批改", "E. 科研辅助与数据分析"]},
    "q3": {"title": "3. 您知道或使用过哪些类型的AI工具？（多选）", "options": ["A. 语言大模型类", "B. 绘画设计类", "C. PPT生成类", "D. 视频生成类", "E. 办公辅助类"]},
    "q4": {"title": "4. 【大模型专项】您具体了解或使用过哪些大语言模型？（多选）", "options": ["A. ChatGPT", "B. Claude", "C. Gemini", "D. Copilot", "E. 文心一言", "F. 通义千问", "G. Kimi", "H. 智谱清言", "I. 讯飞星火", "J. 豆包", "K. 腾讯混元", "L. DeepSeek", "M. 海螺AI", "N. 天工AI", "O. 百川智能"]},
    "q5": {"title": "5. 使用AI工具时，您遇到的最大困难是什么？", "options": ["A. 不知道好工具", "B. 不会写提示词", "C. 担心准确性/版权", "D. 操作太复杂", "E. 缺乏应用场景"]},
    "q6": {"title": "6. 您对本次AI培训最期待的收获是什么？", "options": ["A. 了解AI概念趋势", "B. 掌握实用工具", "C. 学习写提示词", "D. 看教学案例", "E. 现场实操指导"]}
}

# ================= 2. 核心功能 =================

@st.cache_resource
def get_neo4j_driver():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
        return driver
    except: return None

class FeishuBitable:
    @staticmethod
    def post_to_feishu(name, answers):
        # 获取 Token
        t_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        t_res = requests.post(t_url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).json()
        token = t_res.get("tenant_access_token")
        
        if not token:
            st.error(f"❌ 飞书鉴权失败: {t_res.get('msg')}")
            return False

        # 写入数据
        api_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
        
        def wrap(q_key, val):
            title = QUESTIONS[q_key]["title"]
            ans = "、".join(val) if isinstance(val, list) else (val if val else "未选")
            return f"题目：{title}\n回答：{ans}"

        payload = {"fields": {
            "姓名": name,
            "Q1": wrap("q1", answers.get("q1")),
            "Q2": wrap("q2", answers.get("q2")),
            "Q3": wrap("q3", answers.get("q3")),
            "Q4": wrap("q4", answers.get("q4")),
            "Q5": wrap("q5", answers.get("q5")),
            "Q6": wrap("q6", answers.get("q6")),
            "时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }}

        res = requests.post(api_url, headers=headers, json=payload).json()
        if res.get("code") == 0:
            st.success("✅ 飞书同步成功！")
            return True
        else:
            st.error(f"❌ 飞书报错: {res.get('msg')}")
            st.json(res) # 强制显示错误细节
            return False

# ================= 3. 页面渲染 =================
st.set_page_config(page_title="AI 调研系统", layout="wide")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 导航")
    mode = st.radio("请选择模式", ["问卷填报", "数据看板"])

# 模式1：问卷填报
if mode == "问卷填报":
    st.title("🤖 AI 使用情况课前调研")
    st.markdown("---")
    
    with st.form("survey_form"):
        user_name = st.text_input("您的姓名 *")
        
        q1_ans = st.radio(QUESTIONS["q1"]["title"], QUESTIONS["q1"]["options"], index=None)
        
        st.write(QUESTIONS["q2"]["title"])
        q2_ans = [o for o in QUESTIONS["q2"]["options"] if st.checkbox(o, key=f"q2_{o}")]
        
        st.write(QUESTIONS["q3"]["title"])
        q3_ans = [o for o in QUESTIONS["q3"]["options"] if st.checkbox(o, key=f"q3_{o}")]
        
        st.write(QUESTIONS["q4"]["title"])
        q4_ans = [o for o in QUESTIONS["q4"]["options"] if st.checkbox(o, key=f"q4_{o}")]
        
        q5_ans = st.radio(QUESTIONS["q5"]["title"], QUESTIONS["q5"]["options"], index=None)
        q6_ans = st.radio(QUESTIONS["q6"]["title"], QUESTIONS["q6"]["options"], index=None)
        
        # 修复日志警告：改用 width='stretch'
        submit_btn = st.form_submit_button("✅ 提交问卷", type="primary", width='stretch')
        
        if submit_btn:
            if not user_name or not q1_ans:
                st.warning("⚠️ 请确保填写了姓名和必答题")
            else:
                data = {"q1":q1_ans, "q2":q2_ans, "q3":q3_ans, "q4":q4_ans, "q5":q5_ans, "q6":q6_ans}
                # 1. 尝试同步飞书
                FeishuBitable.post_to_feishu(user_name, data)
                
                # 2. 尝试同步 Neo4j
                driver = get_neo4j_driver()
                if driver:
                    with driver.session() as s:
                        s.run("CREATE (r:SurveyRes {name:$n, q1:$q1})", n=user_name, q1=q1_ans)
                    st.toast("Neo4j 同步完成")
                st.balloons()

# 模式2：数据看板
else:
    st.title("📊 数据实时看板")
    admin_pwd = st.sidebar.text_input("管理员密码", type="password")
    
    if admin_pwd == ADMIN_PWD:
        st.info("数据每 10 秒自动刷新一次")
        st_autorefresh(interval=10000, key="refresh")
        
        driver = get_neo4j_driver()
        if driver:
            with driver.session() as s:
                res = s.run("MATCH (r:SurveyRes) RETURN r.name as name, r.q1 as q1")
                df = pd.DataFrame([dict(record) for record in res])
                if not df.empty:
                    st.metric("累计填报", len(df))
                    st.dataframe(df, width='stretch')
                else:
                    st.write("暂无数据")
    else:
        st.warning("请输入正确的管理密码")