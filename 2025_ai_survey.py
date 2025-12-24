import streamlit as st
import requests
import json
import datetime

# ================= 1. 飞书核心配置 =================
# 这是你最新的应用和表格 ID
APP_ID = "cli_a9c143778f78dbde"
APP_SECRET = "ffQcE9o4TnJzR7JC1Myt5epc3b6MQdnq"
APP_TOKEN = "GaNbbhWI9a3OwMsTz8scxeM7n2g"
TABLE_ID = "tblPnIHK49IxILKm"

# 题目定义
QUESTIONS = {
    "q1": {"title": "1. 您目前对AI工具（如豆包、ChatGPT等）的了解和使用程度是？", "options": ["A. 完全不了解", "B. 听说过，但未尝试", "C. 偶尔尝试，未应用", "D. 经常使用，辅助工作", "E. 非常熟练"]},
    "q2": {"title": "2. 您最希望AI帮您解决哪类问题？", "options": ["A. 教学设计与教案", "B. 课件与素材制作", "C. 文档处理与办公效率", "D. 学生评价与作业批改", "E. 科研辅助与数据分析"]},
    "q3": {"title": "3. 您知道或使用过哪些类型的AI工具？", "options": ["A. 语言大模型类", "B. 绘画设计类", "C. PPT生成类", "D. 视频生成类", "E. 办公辅助类"]},
    "q4": {"title": "4. 【大模型专项】您具体了解或使用过哪些大语言模型？", "options": ["A. ChatGPT", "B. Claude", "C. Gemini", "D. Copilot", "E. 文心一言", "F. 通义千问", "G. Kimi", "H. 智谱清言", "I. 讯飞星火", "J. 豆包", "K. 腾讯混元", "L. DeepSeek", "M. 海螺AI", "N. 天工AI", "O. 百川智能"]},
    "q5": {"title": "5. 使用AI工具时，您遇到的最大困难是什么？", "options": ["A. 不知道好工具", "B. 不会写提示词", "C. 担心准确性/版权", "D. 操作太复杂", "E. 缺乏应用场景"]},
    "q6": {"title": "6. 您对本次AI培训最期待的收获是什么？", "options": ["A. 了解AI概念趋势", "B. 掌握实用工具", "C. 学习写提示词", "D. 看教学案例", "E. 现场实操指导"]}
}

# ================= 2. 界面渲染 =================
st.set_page_config(page_title="教师AI调研", layout="centered")
st.title("📝 教师 AI 使用课前调研")
st.write("---")

# 基本信息
u_name = st.text_input("您的姓名 *", key="user_name")

# 渲染题目
st.subheader(QUESTIONS["q1"]["title"])
a1 = st.radio("请选择一项", QUESTIONS["q1"]["options"], index=None, key="ans_q1")

st.subheader(QUESTIONS["q2"]["title"])
a2 = [o for o in QUESTIONS["q2"]["options"] if st.checkbox(o, key=f"q2_{o}")]

st.subheader(QUESTIONS["q3"]["title"])
a3 = [o for o in QUESTIONS["q3"]["options"] if st.checkbox(o, key=f"q3_{o}")]

st.subheader(QUESTIONS["q4"]["title"])
a4 = [o for o in QUESTIONS["q4"]["options"] if st.checkbox(o, key=f"q4_{o}")]

st.subheader(QUESTIONS["q5"]["title"])
a5 = st.radio("请选择一项 ", QUESTIONS["q5"]["options"], index=None, key="ans_q5")

st.subheader(QUESTIONS["q6"]["title"])
a6 = st.radio("请选择一项  ", QUESTIONS["q6"]["options"], index=None, key="ans_q6")

st.write("---")

# ================= 3. 提交逻辑 =================
if st.button("🚀 确认提交并同步到飞书", type="primary", use_container_width=True):
    if not u_name:
        st.warning("⚠️ 姓名还没填呢！")
    elif not a1:
        st.warning("⚠️ 第一题还没选呢！")
    else:
        # 开始执行同步，每一步都直接打印在屏幕上
        status = st.empty()
        status.info("⏳ 正在启动同步程序...")
        
        try:
            # 1. 获取 Token
            status.info("第一步：正在获取飞书访问令牌...")
            t_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            t_res = requests.post(t_url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10).json()
            token = t_res.get("tenant_access_token")
            
            if not token:
                st.error(f"❌ 飞书身份验证失败：{t_res.get('msg')}")
            else:
                # 2. 构造数据
                status.info("第二步：正在封装调研数据...")
                def fmt(q_key, user_val):
                    title = QUESTIONS[q_key]["title"]
                    ans_str = "、".join(user_val) if isinstance(user_val, list) else (user_val if user_val else "未填")
                    return f"问：{title}\n答：{ans_str}"

                fields = {
                    "姓名": u_name,
                    "Q1": fmt("q1", a1),
                    "Q2": fmt("q2", a2),
                    "Q3": fmt("q3", a3),
                    "Q4": fmt("q4", a4),
                    "Q5": fmt("q5", a5),
                    "Q6": fmt("q6", a6),
                    "时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                }

                # 3. 写入飞书
                status.info("第三步：正在向飞书多维表格发送数据...")
                api_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                r = requests.post(api_url, headers=headers, json={"fields": fields}, timeout=10).json()
                
                if r.get("code") == 0:
                    status.success("🎉 大功告成！数据已成功同步到飞书多维表格。")
                    st.balloons()
                else:
                    status.error(f"❌ 飞书服务器返回错误：{r.get('msg')}")
                    st.write("错误代码详情：")
                    st.json(r)
        
        except Exception as e:
            st.error(f"❌ 发生网络异常：{e}")