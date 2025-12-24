import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
import datetime
import time
import requests
import json
from streamlit_autorefresh import st_autorefresh
from streamlit_echarts import st_pyecharts
from pyecharts import options as opts
from pyecharts.charts import Bar, Pie

# ================= 1. 核心配置信息 =================
# 飞书凭证
FEISHU_APP_ID = st.secrets.get("FEISHU_APP_ID", "cli_a9c1c59555f81ceb")
FEISHU_APP_SECRET = st.secrets.get("FEISHU_APP_SECRET", "ldR79n02WB6CeA7OVA39af05RFXgEJqG")
FEISHU_APP_TOKEN = "BUCGbklpfaOob5soBs0cLnxDn5f"
FEISHU_TABLE_ID = "tblmi3cmtBGbTZJP"

# Neo4j 凭证
NEO4J_URI = st.secrets.get("NEO4J_URI", "neo4j+ssc://7eb127cc.databases.neo4j.io")
NEO4J_USER = st.secrets.get("NEO4J_USERNAME", "neo4j")
NEO4J_PWD = st.secrets.get("NEO4J_PASSWORD", "wE7pV36hqNSo43mpbjTlfzE7n99NWcYABDFqUGvgSrk")
ADMIN_PWD = st.secrets.get("ADMIN_PASSWORD", "admin888")

# 数据库连接驱动
@st.cache_resource
def get_driver():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
        driver.verify_connectivity()
        return driver
    except Exception as e:
        st.error(f"❌ Neo4j 连接失败: {e}")
        return None

# ================= 2. 问卷题目定义 =================
QUESTIONS = {
    "q1": {"title": "1. 您目前对AI工具（如豆包、ChatGPT等）的了解和使用程度是？", "type": "single", "options": ["A. 完全不了解", "B. 听说过，但未尝试", "C. 偶尔尝试，未应用", "D. 经常使用，辅助工作", "E. 非常熟练"]},
    "q2": {"title": "2. 您最希望AI帮您解决哪类问题？（多选）", "type": "multi", "options": ["A. 教学设计与教案", "B. 课件与素材制作", "C. 文档处理与办公效率", "D. 学生评价与作业批改", "E. 科研辅助与数据分析"]},
    "q3": {"title": "3. 您知道或使用过哪些类型的AI工具？（多选）", "type": "multi", "options": ["A. 语言大模型类", "B. 绘画设计类", "C. PPT生成类", "D. 视频生成类", "E. 办公辅助类"]},
    "q4": {"title": "4. 【大模型专项】您具体了解或使用过哪些大语言模型？（多选）", "type": "multi", "options": ["A. ChatGPT", "B. Claude", "C. Gemini", "D. Copilot", "E. 文心一言", "F. 通义千问", "G. Kimi", "H. 智谱清言", "I. 讯飞星火", "J. 豆包", "K. 腾讯混元", "L. DeepSeek", "M. 海螺AI", "N. 天工AI", "O. 百川智能"]},
    "q5": {"title": "5. 使用AI工具时，您遇到的最大困难是什么？", "type": "single", "options": ["A. 不知道好工具", "B. 不会写提示词", "C. 担心准确性/版权", "D. 操作太复杂", "E. 缺乏应用场景"]},
    "q6": {"title": "6. 您对本次AI培训最期待的收获是什么？", "type": "single", "options": ["A. 了解AI概念趋势", "B. 掌握实用工具", "C. 学习写提示词", "D. 看教学案例", "E. 现场实操指导"]}
}

# ================= 3. 飞书服务逻辑 (带详细报错) =================
class FeishuService:
    @staticmethod
    def get_token():
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        try:
            r = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET})
            res_json = r.json()
            if res_json.get("code") != 0:
                st.error(f"飞书鉴权失败: {res_json.get('msg')}")
                return None
            return res_json.get("tenant_access_token")
        except Exception as e:
            st.error(f"飞书Token获取网络错误: {e}")
            return None

    @staticmethod
    def push_data(name, answers):
        token = FeishuService.get_token()
        if not token: return False
        
        api_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
        
        def format_cell(q_key, val):
            title = QUESTIONS[q_key]["title"]
            ans = "、".join(val) if isinstance(val, list) else (val if val else "未选")
            return f"题目：{title}\n回答：{ans}"

        # 🚀 重要：请确保这些 key ("姓名", "Q1"...) 与飞书表头完全一致
        payload = {
            "fields": {
                "姓名": name,
                "Q1": format_cell("q1", answers.get("q1")),
                "Q2": format_cell("q2", answers.get("q2")),
                "Q3": format_cell("q3", answers.get("q3")),
                "Q4": format_cell("q4", answers.get("q4")),
                "Q5": format_cell("q5", answers.get("q5")),
                "Q6": format_cell("q6", answers.get("q6")),
                "时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
        }
        
        try:
            res = requests.post(api_url, headers=headers, json=payload)
            res_json = res.json()
            if res_json.get("code") != 0:
                st.error(f"飞书同步报错: {res_json.get('msg')} (代码: {res_json.get('code')})")
                st.info("💡 提示：请检查飞书列名是否被改动，或机器人是否已添加至该多维表格。")
                return False
            return True
        except Exception as e:
            st.error(f"同步飞书时发生网络异常: {e}")
            return False

# ================= 4. 后端核心逻辑 =================
class SurveyBackend:
    def __init__(self):
        self.driver = get_driver()

    def submit_response(self, name, answers):
        # 1. 存入 Neo4j
        if self.driver:
            with self.driver.session() as session:
                query = """CREATE (r:SurveyResponse {name: $name, submitted_at: datetime(), 
                           q1: $q1, q2: $q2, q3: $q3, q4: $q4, q5: $q5, q6: $q6})"""
                session.run(query, name=name, **answers)
        
        # 2. 存入 飞书
        with st.spinner("🚀 正在同步数据至飞书..."):
            success = FeishuService.push_data(name, answers)
            if success:
                st.toast("✅ 飞书同步成功！")
                return True
            return False

    def get_all_data(self):
        if not self.driver: return []
        with self.driver.session() as session:
            result = session.run("MATCH (r:SurveyResponse) RETURN r ORDER BY r.submitted_at DESC")
            data = [dict(record['r']) for record in result]
            for d in data:
                if 'submitted_at' in d:
                    d['submitted_at'] = d['submitted_at'].iso_format().split('.')[0].replace('T', ' ')
            return data

# ================= 5. 可视化组件 =================
def plot_pie(df, col, title):
    if df.empty: return None
    counts = df[col].value_counts()
    data_pair = [list(z) for z in zip(counts.index.tolist(), counts.values.tolist())]
    return (Pie().add("", data_pair, radius=["35%", "60%"])
            .set_global_opts(title_opts=opts.TitleOpts(title=title, pos_left="center"))
            .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)")))

def plot_bar(df, col, title):
    if df.empty: return None
    all_options = [item for sublist in df[col] for item in (sublist if isinstance(sublist, list) else [sublist])]
    if not all_options: return None
    counts = pd.Series(all_options).value_counts().sort_values(ascending=True)
    return (Bar().add_xaxis(counts.index.tolist()).add_yaxis("人数", counts.values.tolist())
            .reversal_axis().set_global_opts(title_opts=opts.TitleOpts(title=title)))

# ================= 6. 主程序 UI 界面 =================
st.set_page_config(page_title="AI 调研问卷", page_icon="📝", layout="wide")
app = SurveyBackend()

# 侧边栏导航
with st.sidebar:
    st.title("📝 问卷系统")
    role = st.radio("当前身份", ["👨‍🏫 我是老师 (填报)", "🔧 管理员后台 (查看)"])

# 场景 A：填报界面
if role == "👨‍🏫 我是老师 (填报)":
    st.header("🤖 AI使用情况课前调研问卷")
    st.info("老师您好！数据将实时同步至分析系统，请放心填写。")
    
    with st.form("survey_form"):
        st.subheader("基本信息")
        name = st.text_input("请输入您的姓名 *", placeholder="必填")

        st.subheader("问卷内容")
        # 渲染题目
        a1 = st.radio(QUESTIONS["q1"]["title"] + " *", QUESTIONS["q1"]["options"], index=None)
        
        st.markdown(f"**{QUESTIONS['q2']['title']}**")
        a2 = [opt for opt in QUESTIONS["q2"]["options"] if st.checkbox(opt, key=f"q2_{opt}")]
        
        st.markdown(f"**{QUESTIONS['q3']['title']}**")
        a3 = [opt for opt in QUESTIONS["q3"]["options"] if st.checkbox(opt, key=f"q3_{opt}")]
        
        st.markdown(f"**{QUESTIONS['q4']['title']}**")
        a4 = [opt for opt in QUESTIONS["q4"]["options"] if st.checkbox(opt, key=f"q4_{opt}")]
        
        a5 = st.radio(QUESTIONS["q5"]["title"] + " *", QUESTIONS["q5"]["options"], index=None)
        a6 = st.radio(QUESTIONS["q6"]["title"] + " *", QUESTIONS["q6"]["options"], index=None)

        submitted = st.form_submit_button("✅ 提交问卷", type="primary", use_container_width=True)

        if submitted:
            if not name.strip() or not a1 or not a5 or not a6:
                st.error("⚠️ 姓名和所有单选题（带*号）均为必填项！")
            else:
                answers = {"q1": a1, "q2": a2, "q3": a3, "q4": a4, "q5": a5, "q6": a6}
                if app.submit_response(name.strip(), answers):
                    st.success(f"🎉 提交成功！谢谢 {name.strip()} 老师。")
                    st.balloons()

# 场景 B：管理后台
elif role == "🔧 管理员后台 (查看)":
    # 简单的密码保护（可选，目前使用默认配置中的 ADMIN_PWD）
    pwd = st.sidebar.text_input("管理密码", type="password")
    if pwd == ADMIN_PWD:
        st.title("📊 调研结果实时看板")
        # 自动刷新
        st_autorefresh(interval=10000, key="data_refresh")
        
        raw_data = app.get_all_data()
        df = pd.DataFrame(raw_data)
        
        if not df.empty:
            st.metric("已成功参与人数", len(df))
            tab1, tab2 = st.tabs(["📈 图表可视化", "📋 原始数据明细"])
            
            with tab1:
                col1, col2 = st.columns(2)
                with col1:
                    st_pyecharts(plot_pie(df, "q1", "AI 熟悉度分布"), height="400px")
                with col2:
                    st_pyecharts(plot_pie(df, "q5", "核心困难分布"), height="400px")
                
                st.divider()
                st_pyecharts(plot_bar(df, "q2", "教师 Top 需求场景"), height="400px")
            
            with tab2:
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 导出 CSV 备份", df.to_csv(index=False).encode('utf-8-sig'), "survey_export.csv")
        else:
            st.info("目前还没有老师填写问卷哦。")
    elif pwd != "":
        st.error("密码不正确")
    else:
        st.warning("请输入侧边栏的管理密码以查看看板")