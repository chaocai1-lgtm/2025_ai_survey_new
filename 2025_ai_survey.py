import streamlit as st
import pandas as pd
import datetime
import requests
import json
from neo4j import GraphDatabase

# ================= 1. 核心配置 (已更新为你提供的新凭证) =================
FEISHU_APP_ID = st.secrets.get("FEISHU_APP_ID", "cli_a9c143778f78dbde")
FEISHU_APP_SECRET = st.secrets.get("FEISHU_APP_SECRET", "ffQcE9o4TnJzR7JC1Myt5epc3b6MQdnq")
FEISHU_APP_TOKEN = "BUCGbklpfaOob5soBs0cLnxDn5f"
FEISHU_TABLE_ID = "tblmi3cmtBGbTZJP"

# Neo4j 凭证
NEO4J_URI = "neo4j+ssc://7eb127cc.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PWD = "wE7pV36hqNSo43mpbjTlfzE7n99NWcYABDFqUGvgSrk"

# 题目定义
QUESTIONS = {
    "q1": {"title": "1. 您目前对AI工具（如豆包、ChatGPT等）的了解和使用程度是？", "options": ["A. 完全不了解", "B. 听说过，但未尝试", "C. 偶尔尝试，未应用", "D. 经常使用，辅助工作", "E. 非常熟练"]},
    "q2": {"title": "2. 您最希望AI帮您解决哪类问题？（多选）", "options": ["A. 教学设计与教案", "B. 课件与素材制作", "C. 文档处理与办公效率", "D. 学生评价与作业批改", "E. 科研辅助与数据分析"]},
    "q3": {"title": "3. 您知道或使用过哪些类型的AI工具？（多选）", "options": ["A. 语言大模型类", "B. 绘画设计类", "C. PPT生成类", "D. 视频生成类", "E. 办公辅助类"]},
    "q4": {"title": "4. 【大模型专项】您具体了解或使用过哪些大语言模型？（多选）", "options": ["A. ChatGPT", "B. Claude", "C. Gemini", "D. Copilot", "E. 文心一言", "F. 通义千问", "G. Kimi", "H. 智谱清言", "I. 讯飞星火", "J. 豆包", "K. 腾讯混元", "L. DeepSeek", "M. 海螺AI", "N. 天工AI", "O. 百川智能"]},
    "q5": {"title": "5. 使用AI工具时，您遇到的最大困难是什么？", "options": ["A. 不知道好工具", "B. 不会写提示词", "C. 担心准确性/版权", "D. 操作太复杂", "E. 缺乏应用场景"]},
    "q6": {"title": "6. 您对本次AI培训最期待的收获是什么？", "options": ["A. 了解AI概念趋势", "B. 掌握实用工具", "C. 学习写提示词", "D. 看教学案例", "E. 现场实操指导"]}
}

# ================= 2. 飞书写入逻辑 =================
def push_to_feishu(name, answers):
    st.info("📡 正在尝试同步数据至飞书多维表格...")
    
    # 1. 获取令牌 (Tenant Access Token)
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    token_res = requests.post(token_url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).json()
    token = token_res.get("tenant_access_token")
    
    if not token:
        st.error(f"❌ 飞书身份验证失败! 消息: {token_res.get('msg')}")
        return False

    # 2. 格式化数据 (题目 + 答案 模式)
    def fmt(q_key, val):
        title = QUESTIONS[q_key]["title"]
        ans_str = "、".join(val) if isinstance(val, list) else (val if val else "未填")
        return f"【题目】{title}\n【答案】{ans_str}"

    # 这里的 Key 必须和飞书列名完全一致
    payload = {
        "fields": {
            "姓名": name,
            "Q1": fmt("q1", answers.get("q1")),
            "Q2": fmt("q2", answers.get("q2")),
            "Q3": fmt("q3", answers.get("q3")),
            "Q4": fmt("q4", answers.get("q4")),
            "Q5": fmt("q5", answers.get("q5")),
            "Q6": fmt("q6", answers.get("q6")),
            "时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    }

    # 3. 执行写入
    api_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        r = requests.post(api_url, headers=headers, json=payload).json()
        if r.get("code") == 0:
            st.success("✅ 飞书同步成功！数据已进入多维表格。")
            return True
        else:
            st.error(f"❌ 飞书服务器报错: {r.get('msg')} (代码: {r.get('code')})")
            with st.expander("🔍 点击查看详细诊断信息"):
                st.write("发送的数据内容：")
                st.json(payload)
                st.write("飞书返回的原始响应：")
                st.json(r)
            return False
    except Exception as e:
        st.error(f"❌ 发生网络异常: {e}")
        return False

# ================= 3. UI 渲染 =================
st.set_page_config(page_title="教师AI调研", layout="centered")
st.title("📝 教师 AI 使用课前调研")

with st.form("survey_form"):
    u_name = st.text_input("您的姓名 *")
    
    q1 = st.radio(QUESTIONS["q1"]["title"], QUESTIONS["q1"]["options"], index=None)
    
    st.write(QUESTIONS["q2"]["title"])
    q2 = [o for o in QUESTIONS["q2"]["options"] if st.checkbox(o, key=f"q2_{o}")]
    
    st.write(QUESTIONS["q3"]["title"])
    q3 = [o for o in QUESTIONS["q3"]["options"] if st.checkbox(o, key=f"q3_{o}")]
    
    st.write(QUESTIONS["q4"]["title"])
    q4 = [o for o in QUESTIONS["q4"]["options"] if st.checkbox(o, key=f"q4_{o}")]
    
    q5 = st.radio(QUESTIONS["q5"]["title"], QUESTIONS["q5"]["options"], index=None)
    q6 = st.radio(QUESTIONS["q6"]["title"], QUESTIONS["q6"]["options"], index=None)

    # 兼容性处理
    submit_btn = st.form_submit_button("🚀 确认提交并同步", type="primary", use_container_width=True)

    if submit_btn:
        if not u_name or not q1:
            st.warning("⚠️ 请确保填写了姓名和第一题。")
        else:
            ans_data = {"q1":q1, "q2":q2, "q3":q3, "q4":q4, "q5":q5, "q6":q6}
            
            # 1. 飞书同步
            push_to_feishu(u_name, ans_data)
            
            # 2. Neo4j 同步 (静默)
            try:
                driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PWD))
                with driver.session() as s:
                    s.run("CREATE (t:Teacher {name:$n, q1:$q1})", n=u_name, q1=q1)
            except: pass
            st.balloons()