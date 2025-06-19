import streamlit as st
import pandas as pd
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError
import urllib.parse

# --- CONFIG ---
GOOGLE_API_KEY = "st.secrets["api_key"]"  # 🔐 Replace with your valid Gemini API key

# --- PAGE SETUP ---
st.markdown("""
<div style='display: flex; align-items: center; gap:5px; font-size:2.5em; font-weight: bold;'>
    <span style="color:#4A90E2;">AskDirect</span>
    <span style='font-size: 0.5em; color: grey; font-weight: normal;'> by Ximplicity</span>
    <span style='font-size: 0.5em;'>📨</span>

</div>
""", unsafe_allow_html=True)

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
        df = pd.read_csv("email_keywords.csv")
        df['keywords'] = df['keywords'].str.strip().str.lower()
        return df
    except Exception as e:
        st.error(f"❌ Error loading CSV: {e}")
        return pd.DataFrame()

df_keywords = load_keyword_email_mapping()

# Dict format for backup/local match
keyword_to_email = {
    row["keywords"]: {"email": row["email"], "team": row["team"]}
    for _, row in df_keywords.iterrows()
}

# --- GEMINI SETUP ---
use_gemini = False
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    test_response = model.generate_content("Say OK.")
    if "ok" in test_response.text.strip().lower():
        use_gemini = True
except Exception as e:
    st.warning(f"⚠️ Gemini API not available: {e}")
    use_gemini = False

# --- GEMINI MULTI-KEYWORD MATCHING ---
def suggest_emails_gemini(user_input):
    mapping_list = "\n".join(
        [f"- {row['keywords']}: {row['email']} ({row['team']})" for _, row in df_keywords.iterrows()]
    )
    prompt = f"""
You are a smart email routing assistant.

Here is a list of keyword to email and team mappings:
{mapping_list}

Analyze the user's message and extract all relevant keyword matches from the list above.

Respond only with valid matches in the following format:
keyword | email | team

User message:
\"{user_input}\"
"""

    try:
        response = model.generate_content(prompt)
        lines = response.text.strip().split("\n")
        results = []
        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3 and "@" in parts[1]:
                results.append((parts[0], parts[1], parts[2]))
        return results
    except Exception as e:
        st.warning(f"⚠️ Gemini error: {e}")
        return []

# --- FALLBACK LOCAL MATCHING ---
def local_match(user_input):
    matches = []
    for keyword, info in keyword_to_email.items():
        if keyword in user_input.lower():
            matches.append((keyword, info["email"], info["team"]))
    return matches

# --- MATCHING LOGIC ---
def get_best_matches(user_input):
    if use_gemini:
        matches = suggest_emails_gemini(user_input)
        if matches:
            return matches
    return local_match(user_input)

# --- SESSION STATE ---
def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []

initialize_session_state()

for message in st.session_state.messages:
    avatar = "https://cdn1.iconfinder.com/data/icons/internet-marketing-4-1/32/__bot_chatbot_artificial_robot-512.png" if message["role"] == "assistant" else "❓"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"], unsafe_allow_html=True)

# --- CHAT INPUT & RESPONSE ---
if user_input := st.chat_input("Enter your task – I’ll find the right team!"):
    with st.chat_message("user", avatar="❓"):
        st.markdown(user_input, unsafe_allow_html=True)
    st.session_state.messages.append({"role": "user", "content": user_input})

    matches = get_best_matches(user_input)

    if matches:
        reply = "I found the following relevant teams for your request:\n\n"
        for keyword, email, team in matches:
            subject = urllib.parse.quote(f"Inquiry about {keyword}")
            body = urllib.parse.quote(f"Hi {team} team,\n\nI need help with {keyword}.\n\nThanks.")
            mailto_link = f"mailto:{email}?subject={subject}&body={body}"
            reply += f"🔹 **Keyword**: _{keyword}_  \n**Team**: {team}  \n **Email**: {email}\n\n"
            # reply += f"🔹 **Task**: _{keyword}_  \n**Team**: {team}  \n **Email**: {email} \n({mailto_link} )\n\n"
    else:
        reply = (
            "Oops! I couldn't determine the correct email. Could you please refine your question with a more specific intent?" \
        " If you prefer, you can also send your query to our general support mailbox **acs_inquiries@company.com**, and we’ll be happy to assist you. "
        )

    with st.chat_message("assistant", avatar="https://cdn1.iconfinder.com/data/icons/internet-marketing-4-1/32/__bot_chatbot_artificial_robot-512.png"):
        st.markdown(reply, unsafe_allow_html=True)
    st.session_state.messages.append({"role": "assistant", "content": reply})
