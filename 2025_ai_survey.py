import streamlit as st
import requests
import json
import datetime

# ================= 1. 核心 ID 配置 (严禁改动) =================
# 这里的 ID 是根据你提供的最新信息填写的
FEISHU_APP_ID = "cli_a9c143778f78dbde"
FEISHU_APP_SECRET = "ffQcE9o4TnJzR7JC1Myt5epc3b6MQdnq"
FEISHU_APP_TOKEN = "GaNbbhWI9a3OwMsTz8scxeM7n2g"
FEISHU_TABLE_ID = "tblPnIHK49IxILKm"

# 问卷题目定义
QUESTIONS = {
    "q1": {"title": "1. 您目前对AI工具（如豆包、ChatGPT等）的了解和使用程度是？", "options": ["A. 完全不了解", "B. 听说过，但未尝试", "C. 偶尔尝试，未应用", "D. 经常使用，辅助工作", "E. 非常熟练"]},
    "q2": {"title": "2. 您最希望AI帮您解决哪类问题？", "options": ["A. 教学设计与教案", "B. 课件与素材制作", "C. 文档处理与办公效率", "D. 学生评价与作业批改", "E. 科研辅助与数据分析"]},
    "q3": {"title": "3. 您知道或使用过哪些类型的AI工具？", "options": ["A. 语言大模型类", "B. 绘画设计类", "C. PPT生成类", "D. 视频生成类", "E. 办公辅助类"]},
    "q4": {"title": "4. 【大模型专项】您具体了解或使用过哪些大语言模型？", "options": ["A. ChatGPT", "B. Claude", "C. Gemini", "D. Copilot", "E. 文心一言", "F. 通义千问", "G. Kimi", "H. 智谱清言", "I. 讯飞星火", "J. 豆包", "K. 腾讯混元", "L. DeepSeek", "M. 海螺AI", "N. 天工AI", "O. 百川智能"]},
    "q5": {"title": "5. 使用AI工具时，您遇到的最大困难是什么？", "options": ["A. 不知道好工具", "B. 不会写提示词", "C. 担心准确性/版权", "D. 操作太复杂", "E. 缺乏应用场景"]},
    "q6": {"title": "6. 您对本次AI培训最期待的收获是什么？", "options": ["A. 了解AI概念趋势", "B. 掌握实用工具", "C. 学习写提示词", "D. 看教学案例", "E. 现场实操指导"]}
}

# ================= 2. 页面界面 =================
st.set_page_config(page_title="教师AI调研系统", layout="centered")
st.title("📝 教师 AI 使用课前调研")
st.info("数据将直接同步至飞书多维表格。")

# --- 输入区 ---
user_name = st.text_input("您的姓名 *", placeholder="请输入真实姓名")

st.markdown("---")
q1_ans = st.radio(QUESTIONS["q1"]["title"], QUESTIONS["q1"]["options"], index=None)

st.write(QUESTIONS["q2"]["title"])
q2_ans = [o for o in QUESTIONS["q2"]["options"] if st.checkbox(o, key=f"c2_{o}")]

st.write(QUESTIONS["q3"]["title"])
q3_ans = [o for o in QUESTIONS["q3"]["options"] if st.checkbox(o, key=f"c3_{o}")]

st.write(QUESTIONS["q4"]["title"])
q4_ans = [o for o in QUESTIONS["q4"]["options"] if st.checkbox(o, key=f"c4_{o}")]

q5_ans = st.radio(QUESTIONS["q5"]["title"], QUESTIONS["q5"]["options"], index=None)
q6_ans = st.radio(QUESTIONS["q6"]["title"], QUESTIONS["q6"]["options"], index=None)

# ================= 3. 提交与诊断逻辑 =================
st.markdown("---")
if st.button("🚀 确认提交并同步到飞书", type="primary", use_container_width=True):
    if not user_name:
        st.error("请输入姓名！")
    elif not q1_ans:
        st.error("请选择第一题！")
    else:
        with st.spinner("🚀 正在为您拼命同步数据..."):
            log_area = st.expander("🛠️ 点击查看实时同步诊断日志", expanded=True)
            
            try:
                # 1. 获取 Token
                log_area.write("1️⃣ 正在请求飞书令牌 (Token)...")
                t_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
                t_res = requests.post(t_url, json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10).json()
                token = t_res.get("tenant_access_token")
                
                if not token:
                    log_area.error(f"❌ 飞书身份认证失败: {t_res.get('msg')}")
                else:
                    log_area.success("✅ 飞书身份认证成功！")
                    
                    # 2. 构造数据
                    log_area.write("2️⃣ 正在打包调研数据 (格式化为题目+答案)...")
                    def wrap(q_key, val):
                        title = QUESTIONS[q_key]["title"]
                        ans = "、".join(val) if isinstance(val, list) else (val if val else "未选")
                        return f"【题目】{title}\n【回答】{ans}"

                    # 这里对应的 Key 必须和你的飞书列名一字不差
                    fields = {
                        "姓名": user_name,
                        "Q1": wrap("q1", q1_ans),
                        "Q2": wrap("q2", q2_ans),
                        "Q3": wrap("q3", q3_ans),
                        "Q4": wrap("q4", q4_ans),
                        "Q5": wrap("q5", q5_ans),
                        "Q6": wrap("q6", q6_ans),
                        "时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    
                    # 3. 写入飞书
                    log_area.write(f"3️⃣ 正在写入表格 (Table ID: {FEISHU_TABLE_ID})...")
                    api_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_APP_TOKEN}/tables/{FEISHU_TABLE_ID}/records"
                    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                    
                    r = requests.post(api_url, headers=headers, json={"fields": fields}, timeout=10).json()
                    
                    if r.get("code") == 0:
                        rec_id = r.get("data", {}).get("record", {}).get("record_id")
                        st.success(f"🎉 提交成功！飞书已接收，记录ID: {rec_id}")
                        st.balloons()
                        log_area.success(f"✅ 飞书服务器确认收妥！记录已存入。")
                    else:
                        st.error(f"❌ 飞书服务器拒绝写入: {r.get('msg')}")
                        log_area.error(f"飞书返回错误码: {r.get('code')}")
                        log_area.json(r)
                        st.info("💡 提示：请检查飞书表头名称是否为 '姓名', 'Q1'...'Q6', '时间'，并且机器人已添加至管理列表。")
            except Exception as e:
                st.error(f"❌ 发生错误: {str(e)}")
                log_area.error(f"异常详情: {str(e)}")