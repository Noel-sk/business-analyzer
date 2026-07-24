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
    targetw=1000 if mode=="Brief" else 1925
    stime=time.time()
    try:
        with client.messages.stream(model="claude-haiku-4-5-20251001" if mode2=="Simplified" else "claude-sonnet-4-6", max_tokens=1550 if mode=="Brief" else 3250, messages=[{"role": "user", "content": prompt}]) as stream:
            full_text=""
            display_text=""
            last_percent=-1
            first_line_done=False
            for text in stream.text_stream:
                full_text+=text

                if not first_line_done:
                    if "\n" in full_text:
                        first_line_done=True
                        display_text=full_text.split("\n", 1)[1]
                    placeholder.markdown(f'<div id="analysis-card">\n{display_text}\n</div>', unsafe_allow_html=True)
                else:
                    display_text+=text
                    placeholder.markdown(f'<div id="analysis-card">\n{display_text}\n</div>', unsafe_allow_html=True)
                    word_count=len(display_text.split())
                    percent=min(int((word_count/targetw)*100), 100)
                    if percent!=last_percent:
                        progress_bar.progress(percent)
                        last_percent=percent
                    time.sleep(0.33)

            elapsed=round(time.time()-stime, 1)
            final_wc=len(full_text.split())
            return full_text, elapsed, final_wc

    except anthropic.AuthenticationError:
        return "ERROR: API key is missing or invalid.", 0, 0
    except anthropic.RateLimitError:
            if attempt==1:
                return ask_claude_stream(prompt, placeholder, mode2, mode, progress_bar, attempt=2)
            return "ERROR: Rate limit hit twice. Wait a moment and try again.", 0, 0

    except anthropic.APIConnectionError:
        if attempt==1:
            return ask_claude_stream(prompt, placeholder, mode2, mode, progress_bar, attempt=2)
        return "ERROR: Could not connect.", 0, 0
    except Exception as  e:
        return f"ERROR: Something went wrong - {str(e)}", 0, 0



def render_analysis_card(rlabel, rresult, banner_type, banner_color, qcount, wc, elapsed_time, model_used, show_notes=True):
    st.markdown(f'<div id="recognize-msg" style="background-color:{banner_color}; color:white; padding:10px 16px; border-radius:8px; font-weight:bold; font-size:1.1em;">{banner_type}: {rlabel}</div>', unsafe_allow_html=True)
    st.divider()
    rdisplay=rresult.split("\n", 1)[1] if "\n" in rresult else rresult
    rhighlighted=re.sub(r'(\$?\d[\d,]*\.?\d*\s?(?:percent|thousand|trillion dollars|billion dollars|million dollars|dollars|million|billion)?)', r'<span style="background-color:#7e6957; padding:1px 4px; border-radius:3px;">\1</span>', rdisplay)
    rhighlighted=rhighlighted.replace("[Stable]", '<span style="color:#2ecc71;">[Stable]</span>')
    rhighlighted=rhighlighted.replace("[Shifting]", '<span style="color:#f39c12;">[Shifting]</span>')
    rhighlighted=rhighlighted.replace("[Volatile]", '<span style="color:#e74c3c;">[Volatile]</span>')
    st.markdown(f'<div id="analysis-card">\n{rhighlighted}\n</div>', unsafe_allow_html=True)
    if show_notes:
        st.session_state.notes[rlabel]=st.text_area("Analysis Notes", value=st.session_state.notes.get(rlabel, ""), key=f"note_{rlabel}", placeholder="Jot down your reaction")
    st.caption(f"{qcount}/{mqps} analyses used this session.")
    st.caption(f"Words: {wc}  |  Time: {elapsed_time}s | Model: {model_used}")
    rclean=re.sub(r"###\s*", "", rresult)
    rclean=re.sub(r"\[.*?\]", "", rclean).strip()
    st.components.v1.html(f"""<textarea id="copytext" style="display:none;">{rclean}</textarea>
<button id="copybtn" onclick="navigator.clipboard.writeText(document.getElementById('copytext').value);
document.getElementById('copybtn').innerText='✅'; setTimeout(function(){{document.getElementById('copybtn').innerText='📋';}}, 2300);"
style="padding:8px 16px; border-radius:6px; cursor:pointer;">📋</button>""", height=50)

    

def analyze(user_input, mode, tone, input_type=""):
    return f"""You are a contrarian business analyst with deep field experience. You prioritize uncomfortable truths over conventional wisdom. {"If analyzing an idea, lead every section with what is most likely to fail and why, with zero softening. Do not balance negatives with positives" if tone=="Brutal" else ""}
Analysis MUST be about {user_input} only. Don't necessarily go over the examples stated below, they are examples to give you an idea
Maintain one consistent stance throughout - Do not conflict/contradict with previously established statements
Any claim implying scale or data (revenue, market size, failure rates, growth) must include an approximate real number or range - never vague words. For each major data claim, briefly note its basis in parentheses: (public data), (industry estimate), or (inference) - so it's clear how much to trust each figure
During the analysis, explicitly connect two sections = show how a finding in one section explains or causes something stated in another
Immediately after each header's text, on the exact same line, append either: '[Stable]', '[Shifting]', or '[Volatile]' - based on how fast that factor changes in the real world. no explanation


if company, cover each header in order:
### Revenue Structure
{"Break revenue into its actual parts - which products/segments/services generate it, and what share each holds. Then clarify which is actually profitable versus which exists to support the rest even if it loses money or breaks even" if mode=="Extensive" and mode2=="Detailed" else "Revenue breakdown with real numbers where possible. Key misconception about this company's revenue model"}

### Competitive Eye
{"Identify 1 or 2 things this company does that a competitor cannot easily copy, name the ACTUAL mechanism. If none, say so directly, that's a real finding. Flag competitors who look dangerous but aren't(well-funded but structurally can't compete)" if mode=="Extensive" and mode2=="Detailed" else "Competitive points shaping the company. Name real competitors and one insight that gives them a competitive edge over their main competitor"}

### Out Of Sight Risks
{"Identify risks that wouldn't even show up in analysts research. The kind that you ONLY learn by having operated in this field, making the mistakes or managed the day-to-day relationships involved. Be specific. (e.g., dependency on a supplier or partner that isn't visible from the outside)(points-of-failure type risks)" if mode=="Extensive" and mode2=="Detailed" else "Risks that only trial, error and prolonged time investment teach(points-of-failure type risks)(include critical things to avoid)"}

### Counterintuitive Facts
{"Identify 2 facts for how this company makes money or stays competitive is wrong, and the real mechanism is something else entirely(what is true right now, not past). Each in different areas" if mode=="Extensive" and mode2=="Detailed" else "2 facts about this company that go against what a reasonably informed outsider would assume"}

### What Analysts Miss
{"Identify a specific mechanism that gives the company an advantage in how they operate, a capablity being built that hasn't shown up in revenue yet or an advantage that's underweighted" if mode=="Extensive" and mode2=="Detailed" else "Identify one strength that only becomes visible upon closer assessment(e.g., switching cost a customer would have to eat)"}

### Insight-Seeking Questions
One to two sharp, specific questions this analysis surfaces that only someone with real domain insider knowledge could answer - not generic questions, ones pointing directly at what's genuinely uncertain here and its answer can change this analysis' direction

If business idea, cover each header in order:
### Market Demand
{"State the type of consumers who specifically have this problem bad enough to pay to solve it, make it a narrow group for whom this is an active current pain point. Say how they solve this problem today without this idea, if they can't, say so. If the idea is an extra rather than solving something(e.g., robot waiters), look for a group who could use this to make things more efficient, lower costs, etc." if mode=="Extensive" and mode2=="Detailed" else "Evaluate market demand extensively with real numbers. Is demand genuine, manufactured or hyped? Explain why"}

### Competition
{"Identify who is currently already solving or trying to make a solution for this problem/adjacent version of it - direct competitors, indirect substitutes or default non-solution. For each, state specifically what they're missing or what could be done better based on customer thoughts" if mode=="Extensive" and mode2=="Detailed" else "Name specific competitors, their key weaknesses and what we can do about them, and whether genuine room exists"}

### Monetization
{"State the specific mechanism this idea would use to collect money, and whether it matches how the target customer already spends money in this category. A model that fights customer's existing spending habits(e.g., asking for upfront payment when category is used to free-with-ads) is a common failure point and should be flagged if it applies" if mode=="Extensive" and mode2=="Detailed" else "Concrete cashflow path from zero to first dollar given how the world is today, competition, potential risks, and future landscape(be realistic), then to long-term sustainability and growth potential. No vague frameworks"}

### Counterintuitive Insights
{"Identify 1 or 2 assumptions this idea is quietly relying on. The kind of belief that, if wrong, doesn't just hurt the business, it invalidates the whole premise. State it plainly, then argue the case that's false or shakier than it looks using comparable ideas/products where that assumption failed" if mode=="Extensive" and mode2=="Detailed" else "Two concealed facts entrants repeatedly miss, each directly challenging something stated above that would be hard to believe. Confirmed facts ONLY"}

### Underlying Threat
{"Identify the recurring failure pattern specific to this category, not generic startup risks(e.g., running out of money, bad hires), but a specific thing that has sunk multiple businesses in this exact space, repeatedly, often ones that look healthy right up until it hit" if mode=="Extensive" and mode2=="Detailed" else "The underlying issue that repeatedly and quietly sinks businesses in this space. Why it happens, how to try to avoid, and how to survive if it happens"}

### The Angle That Works
{"Identify two specific, narrow segments within this idea's broader space where the idea has real traction potential. For each, state exactly why and a brief execution plan to start" if mode=="Extensive" and mode2=="Detailed" else "Two specific niches with traction potential and exactly why"}

### Insight-Seeking Questions
One to two sharp, specific questions this analysis surfaces that only someone with real domain insider knowledge could answer - not generic questions, ones pointing directly at what's genuinely uncertain here and its answer can change this analysis' direction

Start with exactly: [Company: name] or [Idea: 2-4 word label](long answers: 95% ideas), then a blank line
Each sentence must have a min. of 11 and a max. of 25 words, NEVER MORE. Don't combine different ideas under same paragraph
{"Cover ALL headers while keeping analysis under 1300 words max. Use exactly 2 paragraphs per header, separated by a blank line. Each paragraph MUST contain NO MORE than 3 sentences. Cover the most critical point per header" if mode=="Brief" else "Cover ALL headers with full depth. Depth and corectness matter more than length so write as much as GENUINELY NEEDED. Use exactly 3 to 4 paragraphs per '###header', separated by a blank line. Each paragraph can NOT contain more than 8 sentences. Vary angle per paragraph where natural - rotate between financial, competitive, behavioral, and structural angles across paragraphs"} {"Focus on hard data: real figures, specific percentages." if "Company" in input_type else "Focus on realistic scenarios: first 90 days, similar ideas failure patterns, specific entry barriers."}
Never use special symbols. Write numbers and percentages in plain text

End with exactly these sections:
### Vital Metrics
List the 4 to 5 most load-bearing numbers from this entire analysis in one place - the ones that, if wrong, would change the conclusion. Format each as its own numbered line, structured as: **[where it came from]** - the number and why it matters, written as one full sentence, not a fragment. Pull from what's already stated above, nothing new

### Weak Point
{"Identify 1 critical assumption this analysis is quietly relying on. The kind that, if wrong or suddenly changes, it ivalidates the whole point. Also state where this analysis was most confident based on actual facts" if tone=="Brutal" else "Call out directly where this analysis was overconfident or too certain, and why that confidence isn't fully earned. 3-sentence-max"}

### The Move
{"State one specific action that can be started and produce real signal within 30 days - not a milestone in a long-term plan, but a small, cheap test that would tell you whether this idea is worth pursuing further or should be set aside for good. If it can't be reached within 30 days(e.g., due to licensing or funding), state so directly and what can be done instead to still get a sense of its potential. State exactly what result from that action would give a clear 'keep going' versus 'best to set it aside', it MUST have a real threshold(number, specific reaction)" if mode=="Extensive" and mode2=="Detailed" else "One specific, concrete action tied directly to the biggest finding in this analysis. If it's a company, one thing to watch or investigate. If it's an idea, one thing to validate before going further. 6-sentence-max"}"""


st.set_page_config(page_title="Business Analyzer", layout="wide")
st.title("Business Analyzer 📊 ")
st.markdown("<p style='text-align: center; color: gray; font-size: 0.9em;'>Drop a company or idea, get it analyzed thoroughly</p>", unsafe_allow_html=True)
st.markdown("<style>h1 {text-align: center;}</style>", unsafe_allow_html=True)
st.markdown("""<style>div[data-testid="stButton"] button { transition: transform 0.15s ease, box-shadow 0.15s ease;}
div[data-testid="stButton"] button:hover {transform: scale(1.15); box-shadow: 0 2px 8px rgba(0,0,0,0.2);}</style>""", unsafe_allow_html=True)
st.divider()
st.markdown("""<style> #analysis-card {border: 3px solid #2ecc71; border-radius:10px; padding: 20px; transition: border-color 3.5s; animation: fadeIn 1.0s ease-in;} @keyframes fadeIn {from {opacity: 0;} to {opacity: 1;}}
</style>""", unsafe_allow_html=True)

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
if "psugs" not in st.session_state:
    st.session_state.psugs=None
if "cache" not in st.session_state:
    st.session_state.cache={}
if "notes" not in st.session_state:
    st.session_state.notes={}
    
if st.session_state.psugs:
    st.session_state[f"input_{st.session_state.input_key}"]=st.session_state.psugs
    st.session_state.psugs=None



col1, col2, col3=st.columns(3)
with col1:
    mode=st.radio("Structure", ["Brief", "Extensive"], horizontal=True, help="**Brief**: short & focused. **Extensive**: longer, multi-angle breakdown.")
with col2:
    mode2=st.radio("Configuration", ["Simplified", "Detailed"], horizontal=True, help="**Simplified** uses 'Haiku' (faster, lighter). **Detailed** uses 'Sonnet' (slower, sharper reasoning).")
with col3:
    tone=st.radio("Character", ["Neutral", "Brutal"], horizontal=True, help="**Neutral**: balanced tone. **Brutal**: leads with what's most likely to fail, no softening.")



def handle_analyze():
    pending_input=st.session_state[f"input_{st.session_state.input_key}"].strip()
    if not pending_input:
        st.session_state.pending_warning="Please enter something."
    elif len(pending_input)>100:
             st.session_state.pending_warning="Input 2 long, please keep under 100 characters."
    else:
        st.session_state.pending_warning=None
        similar=None
        for past_l in st.session_state.history:
            past_w=set(past_l.lower().split())
            new_w=set(pending_input.lower().split())
            if past_w & new_w:
                similar=past_l
                break

        cache_key=f"{pending_input.lower()} | {mode} | {mode2} | {tone}"
        if cache_key in st.session_state.cache:
            st.session_state.cached_hit=cache_key
        elif similar and "confirm_dup" not in st.session_state:
            st.session_state.pending_input=pending_input
            st.session_state.show_dup_warning=True
        else:
            st.session_state.is_running=True
            st.session_state.pending_input=pending_input
            st.session_state.show_dup_warning=False




input_col, sugs_col=st.columns([4,1.3])
with input_col:
    user_input=st.text_input("Input", key=f"input_{st.session_state.input_key}", on_change=handle_analyze)
    st.caption(f"{len(user_input)}/100 characters")
    
with sugs_col:
    examples=["Airbnb", "AI-automated Air Traffic Controller System", "SaaS For Bio-Engineers", "Adidas", "Subscription Meal Kits", "Equinox", "Corporate Meditation Studios"]
    st.text_input("Inspiration Panel", value=st.session_state.sugs, disabled=True)
    use_col, new_col=st.columns(2)
    with use_col:
        if st.button("Use"):
            st.session_state.psugs=st.session_state.sugs
            st.rerun()
    with new_col:
        if st.button("New"):
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
    if st.button("Analyze", disabled=st.session_state.is_running, on_click=handle_analyze):
       pass
    if st.session_state.get("pending_warning"):
        st.warning(st.session_state.pending_warning)
        st.session_state.pending_warning=None 
    if st.session_state.get("show_dup_warning"):
        st.warning("You may have already analyzed something similar. Check 'Session History' below")



        proceed_col, cancel_col=st.columns(2)
        with proceed_col:
            if st.button("Analyze anyway"):
                st.session_state.is_running=True
                st.session_state.show_dup_warning=False
                st.session_state.pending_input=user_input.strip()
                st.rerun()
        with cancel_col:
            if st.button("Cancel"):
                st.session_state.show_dup_warning=False
                st.rerun()



    if st.session_state.get("cached_hit"):
        key=st.session_state.cached_hit
        cached_result, cached_elapsed, cached_wc, cached_label=st.session_state.cache[key]
        st.info("Instant⚡")
        st.subheader(cached_label)
        st.divider()
        card=st.container(border=True)
        with card:
            st.markdown(cached_result.split("\n", 1)[1] if "\n" in cached_result else cached_result)
        st.caption(f"Words: {cached_wc} | Time: {cached_elapsed}s")
        if st.button("Clear"):
            st.session_state.cached_hit=None
            st.rerun()


        if st.session_state.get("last_result") and not st.session_state.is_running:
            render_analysis_card(st.session_state.last_label, st.session_state.last_result, st.session_state.last_banner_type, st.session_state.last_banner_color, st.session_state.last_qcount, st.session_state.last_wc, st.session_state.last_elapsed, st.session_state.last_model)

            if st.button(" New analysis 🔄"):
                st.session_state.last_result=None
                st.session_state.analysis_done=False
                st.session_state.input_key+=1
                st.rerun()

    
    if st.session_state.is_running:
        cleaned_input=st.session_state.pending_input


        
        with st.spinner("Recognizing..."):
            peek=client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=25, messages=[{"role": "user", "content": f'"{cleaned_input}": company or a business idea? Reply exactly: [Company: name] or [Idea: 2-5 word label]'}])
            first_line=peek.content[0].text.strip()
        if "Company"  not in first_line and "Idea" not in first_line:
            st.warning("Couldn't recognize input type. Try rephrasing.")
            st.session_state.is_running=False
            st.stop()
        st.markdown("""<style>@keyframes recognizeFade{from{opacity: 0;} to {opacity: 1;}} #recognize-msg{animation:recognizeFade 1.9s ease-in;}</style>""", unsafe_allow_html=True)
        if "Company" in first_line:                                                                                          
            label=first_line.replace("[Company:", "").replace("]", "").strip()
            bannert="Company"
            bannerc="#3498db"
        else:
            label=first_line.replace("[Idea:", "").replace("]", "").strip()
            bannert="Idea"
            bannerc="#9b59b6"
        st.markdown(f'<div id="recognize-msg" style="background-color:{bannerc}; color:white; padding:10px 16px; border-radius:8px; font-weight:bold; font-size:1.1em;">{bannert}: {label}</div>', unsafe_allow_html=True)
        st.divider()

        st.session_state.query_count+=1
        st.divider()
        st.markdown("""<style>div[data-testid="stProgress"] {position: fixed;
bottom: 0; left: 0; width: 100%; z-index: 999; background: white; padding: 10px;}
div[data-testid="stProgress"] div[role="progressbar"] > div {animation: barPulse 1.7s ease-in-out infinite;}
@keyframes barPulse{0%{opacity:1;}50%{opacity:0.6;}100%{opacity:1;}}</style>""", unsafe_allow_html=True)


        placeholder=st.empty()
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
        st.session_state.last_result=result
        st.session_state.last_label=label
        st.session_state.last_banner_type=bannert
        st.session_state.last_banner_color=bannerc
        

       
        if result and not result.startswith("ERROR"):
            cache_key=f"{cleaned_input.lower()} | {mode} | {mode2} | {tone}"
            full_label=f"{'Company' if 'Company' in first_line else 'Idea'}: {label}"
            st.session_state.cache[cache_key]=(result, elapsed, final_wc, full_label)
        st.session_state.last_qcount=st.session_state.query_count
        st.session_state.last_model=model_used="Sonnet" if mode2=="Detailed" else "Haiku"
        st.session_state.last_wc=final_wc
        st.session_state.last_elapsed=elapsed
        st.rerun()


with st.expander("Session history"):
    if st.session_state.history:
        selected=st.radio("Past Analyses:", ["- select 2 view -"] + st.session_state.history, key="history_select")
        if selected and selected in st.session_state.historyd and selected != "- select 2 view -":
            st.markdown(st.session_state.historyd[selected].split("\n", 1)[1] if "\n" in st.session_state.historyd[selected] else st.session_state.historyd[selected])
        else: 
            st.caption("No analysis yet.")

with st.expander("About this tool"):
    st.markdown("""**Business Analyzer** uses AI to break down companies and business ideas beyond surface-level takes.
**How 2 Use:**
- Type a company name or business idea and hit 'Analyze'
- Quick mode gives you the sharpest single insight per section
- Full mode goes deeper with multiple angles per section
- Haiku is faster and less acute. Sonnet is slower but sharper

**Limit:** 3 analysis per session, refresh to reset.""")
