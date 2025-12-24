import streamlit as st
import pandas as pd
import datetime
import requests
import json
from neo4j import GraphDatabase

# ================= 1. 核心配置 =================
FEISHU_APP_ID = "cli_a9c143778f78dbde"
FEISHU_APP_SECRET = "ffQcE9o4TnJzR7JC1Myt5epc3b6MQdnq"
FEISHU_APP_TOKEN = "GaNbbhWI9a3OwMsTz8scxeM7n2g"
FEISHU_TABLE_ID = "tblPnIHK49IxILKm"

NEO4J_URI = "neo4j+ssc://7eb127cc.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PWD = "wE7pV36hqNSo43mpbjTlfzE7n99NWcYABDFqUGvgSrk"

QUESTIONS = {
    "q1": {"title": "1. 您目前对AI工具（如豆包、ChatGPT等）的了解和使用程度是？", "options": ["A. 完全不了解", "B. 听说过，但未尝试", "C. 偶尔尝试，未应用", "D. 经常使用，辅助工作", "E. 非常熟练"]},
    "q2": {"title": "2. 您最希望AI帮您解决哪类问题？", "options": ["A. 教学设计与教案", "B. 课件与素材制作", "C. 文档处理与办公效率", "D. 学生评价与作业批改", "E. 科研辅助与数据分析"]},
    "q3": {"title": "3. 您知道或使用过哪些类型的AI工具？", "options": ["A. 语言大模型类", "B. 绘画设计类", "C. PPT生成类", "D. 视频生成类", "E. 办公辅助类"]},
    "q4": {"title": "4. 【大模型专项】您具体了解或使用过哪些大语言模型？", "options": ["A. ChatGPT", "B. Claude", "C. Gemini", "D. Copilot", "E. 文心一言", "F. 通义千问", "G. Kimi", "H. 智谱清言", "I. 讯飞星火", "J. 豆包", "K. 腾讯混元", "L. DeepSeek", "M. 海螺AI", "N. 天工AI", "O. 百川智能"]},
    "q5": {"title": "5. 使用AI工具时，您遇到的最大困难是什么？", "options": ["A. 不知道好工具", "B. 不会写提示词", "C. 担心准确性/版权", "D. 操作太复杂", "E. 缺乏应用场景"]},
    "q6": {"title": "6. 您对本次AI培训最期待的收获是什么？", "options": ["A. 了解AI概念趋势", "B. 掌握实用工具", "C. 学习写提示词", "D. 看教学案例", "E. 现场实操指导"]}
}

# ================= 2. 强制诊断函数 =================
def push_with_debug(name, answers):
    st.write("---")
    st.subheader("🛠️ 飞书同步实时诊断")
    
    # 1. 获取令牌
    t_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    t_res = requests.post(t_url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).json()
    token = t_res.get("tenant_access_token")
    
    if not token:
        st.error(f"❌ 身份验证失败！飞书返回：{t_res.get('msg')}")
        return

    # 2. 构造发送的数据
    def fmt(q_key, val):
        title = QUESTIONS[q_key]["title"]
        ans = "、".join(val) if isinstance(val, list) else (val if val else "未填")
        return f"问：{title}\n答：{ans}"

    # 🚀 请核对：这里的 "姓名", "Q1", "Q2" ... 必须和你飞书表头完全一致
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
    
    st.write("📤 正在发送以下数据：")
    st.json(payload)

    # 3. 写入飞书
    api_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        r = requests.post(api_url, headers=headers, json=payload).json()
        if r.get("code") == 0:
            st.success("🎉 飞书服务器确认：写入成功！")
        else:
            st.error(f"❌ 飞书服务器报错：{r.get('msg')}")
            st.write("服务器返回的原始错误代码：")
            st.code(json.dumps(r, indent=2, ensure_ascii=False))
            st.info("💡 常见原因：1. 表头列名没对上；2. 机器人没加进表格管理里。")
    except Exception as e:
        st.error(f"❌ 网络请求异常：{e}")

# ================= 3. 界面 =================
st.set_page_config(page_title="教师AI调研", layout="centered")
st.title("📝 教师 AI 使用课前调研")

with st.form("debug_form"):
    u_name = st.text_input("姓名 *")
    a1 = st.radio(QUESTIONS["q1"]["title"], QUESTIONS["q1"]["options"], index=None)
    
    st.write(QUESTIONS["q2"]["title"])
    a2 = [o for o in QUESTIONS["q2"]["options"] if st.checkbox(o, key=f"z2_{o}")]
    
    st.write(QUESTIONS["q3"]["title"])
    a3 = [o for o in QUESTIONS["q3"]["options"] if st.checkbox(o, key=f"z3_{o}")]
    
    st.write(QUESTIONS["q4"]["title"])
    a4 = [o for o in QUESTIONS["q4"]["options"] if st.checkbox(o, key=f"z4_{o}")]
    
    a5 = st.radio(QUESTIONS["q5"]["title"], QUESTIONS["q5"]["options"], index=None)
    a6 = st.radio(QUESTIONS["q6"]["title"], QUESTIONS["q6"]["options"], index=None)

    if st.form_submit_button("🚀 点击提交并诊断同步情况", type="primary", use_container_width=True):
        if not u_name or not a1:
            st.warning("请填写姓名和 Q1")
        else:
            push_with_debug(u_name, {"q1":a1, "q2":a2, "q3":a3, "q4":a4, "q5":a5, "q6":a6})
            st.balloons()