# -*- coding: utf-8 -*-
import streamlit as st
from neo4j import GraphDatabase
from pyecharts import options as opts
from pyecharts.charts import Bar, Pie
from streamlit_echarts import st_pyecharts
import pandas as pd
import datetime
import time
import requests
import json

# ✨✨✨ 新增库：用于自动刷新 ✨✨✨
from streamlit_autorefresh import st_autorefresh

# ================= 1. 配置与连接 =================
# 飞书配置 (已验证可用)
FEISHU_APP_ID = "cli_a9c143778f78dbde"
FEISHU_APP_SECRET = "ffQcE9o4TnJzR7JC1Myt5epc3b6MQdnq"
FEISHU_APP_TOKEN = "GaNbbhWI9a3OwMsTz8scxeM7n2g"
FEISHU_TABLE_ID = "tblPnIHK49IxILKm"

# Neo4j 配置
try:
    if st.secrets and "NEO4J_URI" in st.secrets:
        URI = st.secrets["NEO4J_URI"]
        AUTH = ("neo4j", st.secrets["NEO4J_PASSWORD"])
        ADMIN_PWD = st.secrets.get("ADMIN_PASSWORD", "admin888")
    else:
        raise Exception("No secrets config")
except Exception:
    URI = "neo4j+ssc://7eb127cc.databases.neo4j.io"
    AUTH = ("neo4j", "wE7pV36hqNSo43mpbjTlfzE7n99NWcYABDFqUGvgSrk")
    ADMIN_PWD = "admin888"

# 数据库连接缓存
@st.cache_resource
def get_driver():
    try:
        driver = GraphDatabase.driver(URI, auth=AUTH)
        driver.verify_connectivity()
        return driver
    except Exception as e:
        st.error(f"❌ 无法连接数据库: {e}")
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

# ================= 3. 飞书同步服务 =================
class FeishuService:
    @staticmethod
    def get_token():
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        try:
            r = requests.post(url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10)
            return r.json().get("tenant_access_token")
        except:
            return None

    @staticmethod
    def push_data(name, answers):
        token = FeishuService.get_token()
        if not token:
            return False
        
        api_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
        
        def format_cell(q_key, val):
            title = QUESTIONS[q_key]["title"]
            ans = "、".join(val) if isinstance(val, list) else (val if val else "未选")
            return f"【题目】{title}\n【回答】{ans}"

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
            res = requests.post(api_url, headers=headers, json=payload, timeout=10)
            return res.json().get("code") == 0
        except:
            return False

# ================= 4. 后端逻辑 =================
class SurveyBackend:
    def __init__(self):
        self.driver = get_driver()

    def submit_response(self, name, answers):
        # 1. 存入 Neo4j
        if self.driver:
            with self.driver.session() as session:
                query = """CREATE (r:SurveyResponse {name: $name, submitted_at: datetime(), q1: $q1, q2: $q2, q3: $q3, q4: $q4, q5: $q5, q6: $q6})"""
                session.run(query, name=name, **answers)
        
        # 2. ✨ 同步到飞书多维表格 ✨
        feishu_success = FeishuService.push_data(name, answers)
        return feishu_success

    def get_all_data(self):
        if not self.driver:
            return []
        with self.driver.session() as session:
            result = session.run("MATCH (r:SurveyResponse) RETURN r ORDER BY r.submitted_at DESC")
            data = [dict(record['r']) for record in result]
            for d in data:
                if 'submitted_at' in d:
                    d['submitted_at'] = d['submitted_at'].iso_format().split('.')[0].replace('T', ' ')
            return data

    def reset_database(self):
        if not self.driver:
            return
        with self.driver.session() as session:
            result = session.run("MATCH (r:SurveyResponse) DETACH DELETE r")
            result.consume()

# ================= 5. 可视化组件 =================
def plot_pie(df, col, title):
    if df.empty:
        return None
    counts = df[col].value_counts()
    data_pair = [list(z) for z in zip(counts.index.tolist(), counts.values.tolist())]
    return (Pie(init_opts=opts.InitOpts(width="100%"))
            .add("", data_pair, radius=["35%", "60%"])
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title, pos_left="center"),
                legend_opts=opts.LegendOpts(orient="vertical", pos_left="left", type_="scroll")
            )
            .set_series_opts(label_opts=opts.LabelOpts(formatter="{b}: {c} ({d}%)")))

def plot_bar(df, col, title):
    if df.empty:
        return None
    all_options = [item for sublist in df[col] for item in (sublist if isinstance(sublist, list) else [sublist])]
    if not all_options:
        return None
    counts = pd.Series(all_options).value_counts().sort_values(ascending=True)
    return (Bar(init_opts=opts.InitOpts(width="100%"))
            .add_xaxis(counts.index.tolist())
            .add_yaxis("人数", counts.values.tolist(), color="#5470c6")
            .reversal_axis()
            .set_global_opts(
                title_opts=opts.TitleOpts(title=title),
                xaxis_opts=opts.AxisOpts(name="人数"),
                yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(interval=0))
            )
            .set_series_opts(label_opts=opts.LabelOpts(position="right")))

# ================= 6. 主程序界面 =================
st.set_page_config(page_title="AI 调研问卷", page_icon="📝", layout="wide")
app = SurveyBackend()

st.markdown("""
<style>
    div[data-testid="stCheckbox"] { margin-bottom: -12px !important; min-height: auto; }
    div[data-testid="stRadio"] > div { gap: 6px !important; }
    .question-title { font-size: 16px; font-weight: 600; color: #333; margin-top: 25px; margin-bottom: 10px; }
    .stButton { margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

if 'admin_auth' not in st.session_state:
    st.session_state['admin_auth'] = False

with st.sidebar:
    st.title("📝 问卷系统")
    role = st.radio("当前身份", ["👨‍🏫 我是老师 (填报)", "🔧 管理员后台 (查看)"])

    if role == "🔧 管理员后台 (查看)":
        if not st.session_state['admin_auth']:
            pwd = st.text_input("请输入管理密码", type="password")
            if st.button("🔐 确认登录"):
                if pwd == ADMIN_PWD:
                    st.session_state['admin_auth'] = True
                    st.success("登录成功")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("密码错误")
        else:
            st.success("✅ 管理员已登录")
            
            # ✨✨✨ 新增功能：自动刷新开关 ✨✨✨
            st.markdown("---")
            do_refresh = st.toggle("⚡ 开启实时刷新 (5s)", value=True)
            if st.button("退出登录"):
                st.session_state['admin_auth'] = False
                st.rerun()

# --- 场景 A：教师/学员填报 ---
if role == "👨‍🏫 我是老师 (填报)":
    st.header("🤖 AI使用情况课前调研问卷")
    st.markdown("老师您好！请填写以下问卷，带 * 号为必选。数据将同步至飞书多维表格。")
    st.markdown("---")

    with st.form("survey_form"):
        st.subheader("基本信息")
        name = st.text_input("请输入您的姓名 *", placeholder="必填")

        st.subheader("问卷内容")
        
        def render_question(q_key, is_required=False):
            q = QUESTIONS[q_key]
            title_text = q['title'] + (" *" if is_required else "")
            st.markdown(f'<p class="question-title">{title_text}</p>', unsafe_allow_html=True)
            if q['type'] == 'single':
                return st.radio("label_hidden", q['options'], index=None, label_visibility="collapsed")
            elif q['type'] == 'multi':
                selected = []
                for opt in q['options']:
                    if st.checkbox(opt, key=f"{q_key}_{opt}"):
                        selected.append(opt)
                return selected

        a1 = render_question("q1", True)
        a2 = render_question("q2", False)
        a3 = render_question("q3", False)
        a4 = render_question("q4", False)
        a5 = render_question("q5", True)
        a6 = render_question("q6", True)

        submitted = st.form_submit_button("✅ 提交问卷", type="primary", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("⚠️ 姓名不能为空！")
            elif a1 is None:
                st.error("⚠️ 第1题尚未选择！")
            elif a5 is None:
                st.error("⚠️ 第5题尚未选择！")
            elif a6 is None:
                st.error("⚠️ 第6题尚未选择！")
            else:
                answers = {"q1": a1, "q2": a2, "q3": a3, "q4": a4, "q5": a5, "q6": a6}
                with st.spinner("提交中，正在同步至飞书..."):
                    feishu_ok = app.submit_response(name.strip(), answers)
                
                if feishu_ok:
                    st.success(f"🎉 提交成功！谢谢 {name.strip()} 老师。数据已同步至 Neo4j 和飞书。")
                else:
                    st.warning(f"⚠️ 提交成功！但飞书同步失败，请联系管理员。")
                st.balloons()

# --- 场景 B：管理员后台 ---
elif role == "🔧 管理员后台 (查看)":
    if st.session_state['admin_auth']:
        
        # ✨✨✨ 注入自动刷新逻辑 ✨✨✨
        if do_refresh:
            st_autorefresh(interval=5000, limit=None, key="admin_dashboard_refresh")

        st.title("📊 调研结果看板")
        raw_data = app.get_all_data()
        df = pd.DataFrame(raw_data)
        
        col_k1, col_k2, col_k3 = st.columns(3)
        col_k1.metric("已填报人数", len(df))
        col_k2.metric("最新提交", df.iloc[0]['name'] if not df.empty else "-")
        col_k3.metric("最后同步", datetime.datetime.now().strftime("%H:%M:%S"))
        
        if not df.empty:
            tab1, tab2, tab3 = st.tabs(["📈 图表分析", "📋 原始数据", "⚙️ 管理"])
            
            with tab1:
                st.info("💡 提示：看板每 5 秒自动刷新数据。")
                
                st.markdown("#### Q1: AI 熟悉程度")
                chart = plot_pie(df, "q1", "")
                if chart:
                    st_pyecharts(chart, height="400px")
                st.divider()

                st.markdown("#### Q2: Top 需求")
                chart = plot_bar(df, "q2", "")
                if chart:
                    st_pyecharts(chart, height="400px")
                st.divider()

                st.markdown("#### Q3: 熟悉的工具")
                chart = plot_bar(df, "q3", "")
                if chart:
                    st_pyecharts(chart, height="400px")
                st.divider()

                st.markdown("#### Q4: 大语言模型分布")
                chart = plot_bar(df, "q4", "")
                if chart:
                    st_pyecharts(chart, height="500px")
                st.divider()

                st.markdown("#### Q5: 最大困难")
                chart = plot_pie(df, "q5", "")
                if chart:
                    st_pyecharts(chart, height="400px")
                st.divider()

                st.markdown("#### Q6: 期待收获")
                chart = plot_pie(df, "q6", "")
                if chart:
                    st_pyecharts(chart, height="400px")

            with tab2:
                st.dataframe(df, use_container_width=True)
                st.download_button("📥 下载 .csv", df.to_csv(index=False).encode('utf-8-sig'), "data.csv")
            
            with tab3:
                st.warning("⚠️ 危险区域")
                confirm_clear = st.checkbox("我确认要清空所有数据", key="confirm_delete")
                if confirm_clear:
                    if st.button("🔴 立即清空数据库", type="primary"):
                        app.reset_database()
                        st.toast("🗑️ 数据库已清空")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("暂无数据，等待填报...")
            if st.button("强制重置数据库"):
                app.reset_database()
                st.rerun()
