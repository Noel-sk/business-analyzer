import streamlit as st
import anthropic
import threading
import random
import time
import os
import re


try:
    api_key=st.secrets["ant_api1"]
except Exception:
    api_key=os.environ.get("ant_api1")
client=anthropic.Anthropic(api_key=api_key)
mqps=3

def ask_claude_stream(prompt, placeholder, mode2, mode, progress_bar, attempt=1):
    targetw=655 if mode=="Brief" else 1300
    stime=time.time()
    try:
        with client.messages.stream(model="claude-haiku-4-5-20251001" if mode2=="Simplified" else "claude-sonnet-4-6", max_tokens=1100 if mode=="Brief" else 2050, messages=[{"role": "user", "content": prompt}]) as stream:
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

            elapsed=round(time.time()-stime, 1)
            final_wc=len(full_text.split())

            return full_text, elapsed, final_wc
    except anthropic.AuthenticationError:
        return "ERROR: API key is missing or invalid.", 0, 0
    except anthropic.RateLimitError:
        return "ERROR: Rate limit hit. Wait a moment and try again.", 0, 0
    except anthropic.APIConnectionError:
        return "ERROR: Could not connect.", 0, 0
    except Exception as  e:
        if attempt==1:
            return ask_claude_stream(prompt, placeholder, mode2, mode, progress_bar, attempt=2)
        return f"ERROR: Something went wrong - {str(e)}", 0, 0



def analyze(user_input, mode, tone, input_type=""):
    return f"""You are a contrarian business analyst with deep field experience. You prioritize uncomfortable truths over conventional wisdom. {"If analyzing an idea, lead every section with what is most likely to fail and why, with zero softening. Do not balance negatives with positives" if tone=="Brutal" else ""}
Analysis MUST be about {user_input} only.
Maintain one consistent stance throughout - Do not conflict/contradict with previously established statements
Any claim implying scale or data (revenue, market size, failure rates, growth) must include an approximate real number or range - never vague words
For each header, tag either '[Stable]', '[Shifting]', '[Volatile]' next to it - based on how fast that factor changes in the real world, no explanation

if company, cover each header in order:
### Revenue & Misconceptions
Revenue breakdown with real numbers. Key misconceptions about this company's revenue model

### Competitive Eye
Competitive points shaping the company

### Out Of Sight Risks
Risks that only trial, error and deep invested time in the field can teach

### Counterintuitive Facts
Three counterintuitive facts, each directly challenging or complicating something stated in an earlier section above

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
Three concealed facts entrants miss, each directly challenging or complicating something stated in an earlier section above

### Underlying Threat
The underlying issue that quietly sinks businesses in this space and how to survive it

### The Angle That Works
Two specific niches with traction potential and exactly why

Start with exactly: [Company: name] or [Idea: 2-4 word label](long answers: 95% ideas), then a blank line
Use 2-sentence maximum paragraphs. Max 3 paragraphs per header. Don't combine different ideas under same paragraph
{"Keep analysis under 650 words, but always finish 'The Move' & 'Blind Spot' completely regardless of word limit. Cover the most critical point per header. " + ("Focus on hard data: real figures, specific percentages." if "Company" in input_type else "Focus on realistic scenarios: first 90 days, similar ideas failure patterns, specific entry barriers.") if mode=="Brief" else "Write 2-3 paragraphs per header, each covering a distinct angle - rotate between financial, competitive, behavioral, and structural angles across paragraphs, never repeat same angle within one header"}
Never use special symbols. Write numbers and percentages in plain text

End with exactly this section:
### Blind Spot
{"Call out directly where this analysis was overconfident or too certain, and why that confidence isn't fully earned" if tone=="Brutal" else "State one assumption THIS analysis made that could be wrong - not a market risk, but a flaw in the reasoning above"} 3-sentence-max

### The Move
One specific, concrete action tied directly to the biggest finding in this analysis. If it's a company, one thing to watch or investigate. If it's an idea, one thing to validate before going further. 4-sentence-max"""



st.set_page_config(page_title="Business Analyzer", layout="wide")
st.title("Business Analyzer 📊 ")
st.markdown("<p style='text-align: center; color: gray; font-size: 0.9em;'>Drop a company or idea, get it analyzed thoroughly</p>", unsafe_allow_html=True)
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
    st.session_state.sugs="AirBNB"
if "psugs" not in st.session_state:
    st.session_state.psugs=None
    
if st.session_state.psugs:
    st.session_state[f"input_{st.session_state.input_key}"]=st.session_state.psugs
    st.session_state.psugs=None


col1, col2, col3=st.columns(3)
with col1:
    mode=st.radio("Structure", ["Brief", "Extensive"], horizontal=True)
with col2:
    mode2=st.radio("Configuration", ["Simplified", "Detailed"], horizontal=True)
with col3:
    tone=st.radio("Character", ["Neutral", "Brutal"], horizontal=True)


input_col, sugs_col=st.columns([4,1.3])
with input_col:
    user_input=st.text_input("Input", key=f"input_{st.session_state.input_key}")
    st.caption(f"{len(user_input)}/100 characters")


with sugs_col:
    examples=["AirBNB", "Street Food Cart", "SaaS For Bio-Engineers", "Adidas", "Subscription Meal Kits", "Equinox", "Corporate Meditation Studios"]
    st.text_input("Inspiration Panel", value=st.session_state.sugs, disabled=True)
    use_col, new_col=st.columns(2)
    with use_col:
        if st.button("Use"):
            st.session_state.psugs=st.session_state.sugs
            st.rerun()
    with new_col:
        if st.button("New 🔀"):
            st.session_state.sugs=random.choice(examples)
            st.rerun()



        
if st.session_state.query_count>=mqps:
    st.warning(f"You've used all {mqps} analyses this session. Refresh the page to start over.")
    st.subheader("Session Recap")
    for past_l in st.session_state.history:
        full_analysis=st.session_state.historyd[past_l]
        if "### The Move" in full_analysis:
            move_section=full_analysis.split("### The Move")[1]
            move_section=move_section.split("###")[0].strip()
        else:
            move_section="No move identified."
        st.markdown(f"**{past_l}** - {move_section}")
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
        card=st.container(border=True)
        with card:
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
            result, elapsed, final_wc=ask_claude_stream(analyze(cleaned_input, mode, tone, first_line), placeholder, mode2, mode, progress_bar)
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
        if result and not result.startswith("ERROR"):
            model_used="Sonnet" if mode2=="Detailed" else "Haiku"
            st.caption(f"Model: {model_used}  |  Words: {final_wc}  |  Time: {elapsed}s")

        if result and not result.startswith("ERROR"):
            clean_text=re.sub(r"###\s*", "", result)
            clean_text=re.sub(r"\[.*?\]", "", clean_text)
            clean_text=clean_text.strip()
            st.components.v1.html(f"""<textarea id="copytext" style="display:none;">{clean_text}</textarea>
<button id="copybtn" onclick="navigator.clipboard.writeText(document.getElementById('copytext').value);
document.getElementById('copybtn').innerText='Copied ✅'; setTimeout(function(){{document.getElementById('copybtn').innerText='Copy 📋';}}, 2500);"
style="padding:8px 16px; border-radius:6px; cursor:pointer;"> Copy 📋</button>""", height=50)
            

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
