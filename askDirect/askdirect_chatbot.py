import streamlit as st
import pandas as pd
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError
import urllib.parse #Use urllib.parse.quote to safely encode subject and body


# --- CONFIG ---
GOOGLE_API_KEY = "AIzaSyBYZYrBDcipFft1QH3M4BDedbX-vF8iLIU"  # 🔐 Replace with a valid Gemini API key

# --- PAGE SETUP ---

st.markdown(
    """
    <div style='display: flex; align-items: center; gap:5px; font-size:2.5em; font-weight: bold;'>
        <span>📨</span>
        <span style="color:#4A90E2;">AskDirect</span>
        <span style='font-size: 0.5em; color: grey; font-weight: normal;'> by Ximplicity</span>
            </div>
        </div>
    </div>
    </div>
    """, 
    unsafe_allow_html=True
)

st.markdown("""
<div style='display: flex; align-items: left; justify-content: left; gap: 15px;'>
    <img src="https://cdn1.iconfinder.com/data/icons/internet-marketing-4-1/32/__bot_chatbot_artificial_robot-512.png" alt="Robot Speaking" width="60">
    <p style='font-size:18px;color:#aee6fa; margin: 0;'>
        Hi👋! I’m your email routing assistant.<br>
        Type your request and I'll route it to the appropriate team.
    </p>
</div>
""", unsafe_allow_html=True)


# --- LOAD EMAIL-KEYWORD CSV ---
@st.cache_data
def load_keyword_email_mapping():
    try:
        df = pd.read_csv("askDirect/email_keywords.csv")
        return {row["keywords"].strip().lower(): row["email"].strip() for _, row in df.iterrows()}
    except Exception as e:
        st.error(f"❌ Error loading CSV: {e}")
        return {}

keyword_to_email = load_keyword_email_mapping()

# --- GEMINI SETUP ---
use_gemini = False
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")  # More affordable/faster model
    test_response = model.generate_content("Say OK.")
    if "ok" in test_response.text.strip().lower():
        use_gemini = True
except Exception as e:
    st.warning(f"⚠️ Gemini API not available: {e}")
    use_gemini = False

# --- SMART GEMINI-BASED MATCHING ---
def suggest_email_gemini(user_input):
    mapping_list = "\n".join(
        [f"- {kw}: {email}" for kw, email in keyword_to_email.items()]
    )
    prompt = f"""
You are an intelligent email routing assistant.

Here is a list of keyword-to-email rules:
{mapping_list}

Based on the user's message below, choose the most appropriate email address the message should be routed to. Only return the email address. If none apply, say "none".

User message: "{user_input}"
"""
    try:
        response = model.generate_content(prompt)
        result = response.text.strip().lower()
        if "@" in result:
            return result
        return None
    except GoogleAPIError as e:
        st.warning(f"❌ Gemini API error: {e}")
        return None
    except Exception as e:
        st.warning(f"⚠️ Gemini error: {e}")
        return None

# --- LOCAL BACKUP MATCHING ---
def local_match(user_input):
    for keyword, email in keyword_to_email.items():
        if keyword in user_input.lower():
            return keyword, email
    return None, None

# --- DECISION LOGIC ---
def get_best_match(user_input):
    if use_gemini:
        email = suggest_email_gemini(user_input)
        if email:
            for kw, em in keyword_to_email.items():
                if em.lower() == email:
                    return kw, email
            return None, email  # email found, but no matching keyword
    return local_match(user_input)

# --- SESSION STATE INIT ---
def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []

# --- CHATBOT UI ---
initialize_session_state()


for message in st.session_state.messages:
    avatar = "🤖" if message["role"] == "assistant" else "❓"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"], unsafe_allow_html=True)

if user_input := st.chat_input(placeholder="Enter your task – I’ll find the right team!"):
    with st.chat_message("user",avatar="❓"):
        st.markdown(user_input, unsafe_allow_html=True)
    st.session_state.messages.append({"role": "user", "content": user_input})

    keyword, email = get_best_match(user_input)


    if email:
        subject = urllib.parse.quote(f"Inquiry about {keyword or 'your service'}")
        body = urllib.parse.quote(f"Hi,\n\nI need help with {keyword or 'this matter'}.\n\nThanks.")
        mailto_link = f"mailto:{email}?subject={subject}&body={body}"

        reply = f"""
📬 This seems related to **{keyword or 'your inquiry'}**.  
📧 Recommended email: **{email}**

"""
    else:
        reply = "Oops! I couldn't determine the correct email. Could you please refine your question with a more specific intent?" \
        " If you prefer, you can also send your query to our general support mailbox **acs_inquiries@company.com**, and we’ll be happy to assist you. "


     
    with st.chat_message("assistant",avatar="🤖"):
        st.markdown(reply, unsafe_allow_html=True)
        
    st.session_state.messages.append({"role": "assistant", "content": reply})


