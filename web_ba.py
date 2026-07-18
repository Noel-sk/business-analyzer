import streamlit as st
import anthropic
import threading
import random
import time
import os


try:
    api_key=st.secrets["ant_api1"]
except Exception:
    api_key=os.environ.get("ant_api1")
client=anthropic.Anthropic(api_key=api_key)
mqps=3

def ask_claude_stream(prompt, placeholder, mode2, mode, progress_bar, attempt=1):
    targetw=635 if mode=="Quick" else 1150
    try:
        with client.messages.stream(model="claude-haiku-4-5-20251001" if mode2=="Surface Level" else "claude-sonnet-4-6", max_tokens=1000 if mode=="Quick" else 2025, messages=[{"role": "user", "content": prompt}]) as stream:
            full_text=""
            display_text=""
            first_line_done=False
            for text in stream.text_stream:
                full_text+=text
                if not first_line_done:
                    if "\n" in full_text:
                        first_line_done=True
                        display_text=full_text.split("\n", 1)[1]
                    placeholder.markdown(display_text)
                else:
                    display_text+=text
                    placeholder.markdown(display_text)
                    word_count=len(display_text.split())
                    percent=min(int((word_count/targetw)*100), 100)
                    progress_bar.progress(percent)
                    time.sleep(0.33)
            return full_text
    except anthropic.AuthenticationError:
        return "ERROR: API key is missing or invalid."
    except anthropic.RateLimitError:
        return "ERROR: Rate limit hit. Wait a moment and try again."
    except anthropic.APIConnectionError:
        return "ERROR: Could not connect."
    except Exception as  e:
        if attempt==1:
            return ask_claude_stream(prompt, placeholder, mode2, mode, progress_bar, attempt=2)
        return f"ERROR: Something went wrong - {str(e)}"



def analyze(user_input, mode, tone, input_type=""):
    return f"""You are a contrarian business analyst with deep field experience. You prioritize uncomfortable truths over conventional wisdom. {"If analyzing an idea, lead every section with what is most likely to fail and why, with zero softening. Do not balance negatives with positives" if tone=="Brutal" else ""}
Analysis MUST be about {user_input} only.
For each header, tag either '[Stable]', '[Shifting]', '[Volatile]' next to it - based on how fast that factor changes in the real world, no explanation

if company, cover each header in order:
### Revenue & Misconceptions
Revenue breakdown with real numbers. Key misconceptions about this company's revenue model

### Competitive Eye
Competitive points shaping the company

### Out Of Sight Risks
Risks that only trial, error and deep invested time in the field can teach

### Counterintuitive Facts
Three insightfully counterintuitive facts 

### What Analysts Miss
What only emerges upon closer assessment


If business idea, cover each header in order:
### Market Demand
Evaluate market demand extensively with real numbers. Is demand genuine or manufactured?

### Competition
Name specific competitors, their key weaknesses, and whether genuine room exists

### Monetization
Concrete cashflow path from zero to first dollar(be realistic and average), then to sustainability. No vague frameworks

### Counterintuitive Insights
Three concealed facts entrants miss

### The Underlying Threat
The underlying issue that quietly sinks businesses in this space and how to survive it

### The Angle That Works
Two specific niches with traction potential and exactly why

Start with exactly: [Company: name] or [Idea: 2-4 word label](long answers: 95% ideas), then a blank line
Use 2-sentence maximum paragraphs. Max 3 paragraphs per header. Don't combine different ideas under same paragraph
{"Keep analysis under 550 words. Cover the most critical point per header. " + ("Focus on hard data: real figures, specific percentages." if "Company" in input_type else "Focus on realistic scenarios: first 90 days, similar ideas failure patterns, specific entry barriers.") if mode=="Quick" else "Write 2-3 paragraphs per header, each with a new angle"}
Never use special symbols. Write numbers and percentages in plain text

End with exactly this section:
### The Move
One specific, concrete action tied directly to the biggest finding in this analysis. If it's a company, one thing to watch or investigate. If it's an idea, one thing to validate before going further. 3-sentence-max

### Blind Spot
State the biggest assumption this analysis relied on and why it could be wrong. 3-sentence-max"""



st.set_page_config(page_title="Business Analyzer", layout="wide")
st.title("Business Analyzer 📊 ")
st.caption("Drop a company or idea, get it analyzed thoroughly")
st.markdown("<style>h1 {text-align: center;}</style>", unsafe_allow_html=True)
st.divider()

if "query_count" not in st.session_state:
    st.session_state.query_count=0
if "history" not in st.session_state:
    st.session_state.history=[]
if "historyd" not in st.session_state:
    st.session_state.historyd={}
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done=False
if "is_running" not in st.session_state:
    st.session_state.is_running=False
if "input_key" not in st.session_state:
    st.session_state.input_key=0
if "pending_input" not in st.session_state:
    st.session_state.pending_input=""
if "sugs" not in st.session_state:
    st.session_state.sugs="Airbnb"


col1, col2, col3=st.columns(3)
with col1:
    mode=st.radio("Analysis Depth: ", ["Quick", "Full"], horizontal=True)
with col2:
    mode2=st.radio("Analysis Type: ", ["Surface Level", "In Depth"], horizontal=True)
with col3:
    tone=st.radio("Tone: ", ["Balanced", "Brutal"], horizontal=True)


input_col, sugs_col=st.columns([4,1.3])
with input_col:
    user_input=st.text_input("Your input:", key=f"input_{st.session_state.input_key}")
    st.caption(f"{len(user_input)}/100 characters")
with sugs_col:
    examples=["AirBNB", "Street Food Cart", "SaaS For Bio-Engineers", "Adidas", "Subscription Meal Kits", "Equinox", "Corporate Meditation Studios"]
    st.text_input("Suggestions", value=st.session_state.sugs, disabled=True)
    if st.button("New Idea 🔀"):
        st.session_state.sugs=random.choice(examples)
        st.rerun()

        
if st.session_state.query_count>=mqps:
    st.warning(f"You've used all {mqps} analyses this session. Refresh the page to start over.")
else:
    if st.button("Analyze", disabled=st.session_state.is_running):
        pending_input=user_input.strip()
        if not pending_input: 
            st.warning("Please enter something.")
        elif len(pending_input)> 100:
            st.warning("Input too long, please keep under 100 characters.")
        else:
            st.session_state.is_running=True
            st.session_state.pending_input=pending_input
            st.rerun()

    if st.session_state.is_running:
        cleaned_input=st.session_state.pending_input
            
        with st.spinner("Recognizing..."):
            peek=client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=25, messages=[{"role": "user", "content": f'Is "{cleaned_input}" a real existing company or a business idea? Reply with exactly: [Company: name] or [Idea: 2-4 word label]'}])
            first_line=peek.content[0].text.strip()
        if "Company"  not in first_line and "Idea" not in first_line:
            st.warning("Couldn't recognize input type. Try rephrasing.")
            st.session_state.is_running=False
            st.stop()
        if "Company" in first_line:                                                                                          
            label=first_line.replace("[Company:", "").replace("]", "").strip()
            st.success("Recognized as an existing company")
            st.subheader(f"Company: {label}")
        else:
            label=first_line.replace("[Idea:", "").replace("]", "").strip()
            st.success("Recognized as a business idea")
            st.subheader(f"Idea: {label}")
        st.session_state.query_count+=1
        st.divider()
        placeholder=st.empty()

        st.markdown("""
<style>
div[data-testid="stProgress"] {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    z-index: 999;
    background: white;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)
        with st.spinner("Analyzing..."):
            progress_bar=st.progress(0)
            result=ask_claude_stream(analyze(cleaned_input, mode, tone, first_line), placeholder, mode2, mode, progress_bar)
            progress_bar.empty()
        if result and result.startswith("ERROR"):
            placeholder.error(result)
            st.session_state.query_count-=1


        st.session_state.is_running=False
        st.toast("Analysis complete ✅")
        st.session_state.analysis_done=True
        st.session_state.history.append(label)
        st.session_state.historyd[label]=result
        st.caption(f"{st.session_state.query_count}/{mqps} analyses used this session.")

        if st.session_state.get("analysis_done"):
            if st.button(" New analysis 🔄"):
                st.session_state.analysis_done=False
                st.session_state.input_key+=1
                st.rerun()

with st.expander("Session history"):
    if st.session_state.history:
        selected=st.radio("Past Analyses:", ["- select 2 view -"] + st.session_state.history, key="history_select")
        if selected and selected in st.session_state.historyd and selected != "- select 2 view -":
            st.markdown(st.session_state.historyd[selected].split("\n", 1)[1] if "\n" in st.session_state.historyd[selected] else st.session_state.historyd[selected])
            
    else: st.caption("No analysis yet.")
    
with st.expander("About this tool"):
    st.markdown("""**Business Analyzer** uses AI to break down companies and business ideas beyond surface-level takes.
**How 2 Use:**
- Type a company name or business idea and hit 'Analyze'
- Quick mode gives you the sharpest single insight per section
- Full mode goes deeper with multiple angles per section
- Haiku is faster and less acute. Sonnet is slower but sharper

**Limit:** 3 analysis per session, refresh to reset.""")
