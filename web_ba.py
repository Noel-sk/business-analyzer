import streamlit as st
import anthropic
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

hcpt=1.00/1000000
hopt=5.00/1000000
scpt=3.00/1000000
sopt=15.00/1000000

color_company="#3498db"
color_idea="#9b59b6"
colorcard_orange="#e67e22"
colorcard_green="#2ecc71"
color_shifting="#f39c12"
color_volatile="#e74c3c"
color_highlight="#b3b792"
bg_light="#ffffff"
bg_dark="#0e1117"
text_light="#000000"
text_dark="#fafafa"
maxt_br=2950
maxt_ex=4350

def ask_claude_stream(prompt, placeholder, mode2, mode, progress_bar, timer_placeholder, attempt=1):
    targetw=1850 if mode=="Brief" else 2325
    stime=time.time()
    try:
        with client.messages.stream(model="claude-haiku-4-5-20251001" if mode2=="Simplified" else "claude-sonnet-4-6", max_tokens=maxt_br if mode=="Brief" else maxt_ex, messages=[{"role": "user", "content": prompt}]) as stream:
            full_text=""
            display_text=""
            last_percent=-1
            first_line_done=False
            for event in stream:
                if event.type=="content_block_delta" and event.delta.type=="text_delta":
                    text=event.delta.text
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
                        seconds_sf=round(time.time()-stime, 1)
                        timer_placeholder.caption(f"{seconds_sf}s elapsed ⏱️")
                        time.sleep(0.33)


            final_message=stream.get_final_message()
            input_tokens=final_message.usage.input_tokens
            output_tokens=final_message.usage.output_tokens
            if mode2=="Simplified":
                input_cost=input_tokens*hcpt
                output_cost=output_tokens*hopt
            else:
                input_cost=input_tokens*scpt
                output_cost=output_tokens*sopt
            call_cost=input_cost+output_cost

            
            placeholder.markdown(f'<div id="analysis-card" class="done">\n{display_text}\n</div>', unsafe_allow_html=True)
            elapsed=round(time.time()-stime, 1)
            time.sleep(3.7)
            final_wc=len(full_text.split())
            was_cut=final_wc<(targetw*0.8)
            return full_text, elapsed, final_wc, call_cost, was_cut

    except anthropic.AuthenticationError:
        return "ERROR: API key is missing or invalid. Check that your API key is set correctly in the app's secrets, then reload the page.", 0, 0, 0, False
    except anthropic.RateLimitError:
            if attempt==1:
                return ask_claude_stream(prompt, placeholder, mode2, mode, progress_bar, timer_placeholder, attempt=2)
            return "ERROR: Rate limit hit twice. Wait about a minute, then click Analyze again - this doesn't count against your session limit.", 0, 0, 0, False

    except anthropic.APIConnectionError:
        if attempt==1:
            return ask_claude_stream(prompt, placeholder, mode2, mode, progress_bar, timer_placeholder, attempt=2)
        return "ERROR: Could not connect after two tries. Check your internet connection, then click Analyze again.", 0, 0, 0, False
    except Exception as  e:
        return f"ERROR: Something went wrong - {str(e)}. Try rephrasing your input, or click Analyze again in a moment.", 0, 0, 0, False



def render_analysis_card(rlabel, rkey, rresult, banner_type, banner_color, qcount, wc, elapsed_time, model_used, call_cost=0, show_notes=True):
    st.markdown(f'<div id="recognize-msg" style="background-color:{banner_color}; color:white; padding:10px 16px; border-radius:8px; font-weight:bold; font-size:1.1em;">{banner_type}: {rlabel}</div>', unsafe_allow_html=True)
    st.divider()
    
    rdisplay=rresult.split("\n", 1)[1] if "\n" in rresult else rresult
    rdisplay="\n".join(line.lstrip() for line in rdisplay.split("\n"))
    rhighlighted=re.sub(r'(\$?\d[\d,]*\.?\d*\s?(?:percent|thousand|trillion dollars|billion dollars|million dollars|dollars|million|billion)?)', rf'<span style="background-color:{color_highlight}; padding:1px 4px; border-radius:3px;">\1</span>', rdisplay)
    rhighlighted=rhighlighted.replace("[Stable]", f'<span style="color:{colorcard_green};">[Stable]</span>')
    rhighlighted=rhighlighted.replace("[Shifting]", f'<span style="color:{color_shifting};">[Shifting]</span>')
    rhighlighted=rhighlighted.replace("[Volatile]", f'<span style="color:{color_volatile};">[Volatile]</span>')
    rhighlighted=rhighlighted.replace("(confirmed public data)", f'<span style="color:{colorcard_green};">(confirmed public data)</span>')
    rhighlighted=rhighlighted.replace("(industry estimate)", f'<span style="color:{color_shifting};">(industry estimate)</span>')
    rhighlighted=rhighlighted.replace("(inference)", f'<span style="color:{color_volatile};">(inference)</span>')


    header_matches=list(re.finditer(r"(?m)^### [^\n\[]+.*", rresult))
    header_wcs=[]
    for match_index in range(len(header_matches)):
        body_start=header_matches[match_index].end()
        if match_index+1<len(header_matches):
            body_end=header_matches[match_index+1].start()
        else:
            body_end=len(rresult)
        section_body=rresult[body_start:body_end]
        header_wcs.append(len(section_body.split()))

    highlighted_header_matches=list(re.finditer(r"(?m)^### [^\n\[]+.*", rhighlighted))
    text_pieces=[]
    last_position=0
    for match_index in range(len(highlighted_header_matches)):
        current_match=highlighted_header_matches[match_index]
        body_start=current_match.end()
        if match_index+1<len(highlighted_header_matches):
            body_end=highlighted_header_matches[match_index+1].start()
        else:
            body_end=len(rhighlighted)
        section_body_html=rhighlighted[body_start:body_end]

        section_body_trimmed=section_body_html.rstrip()
        trailing_whitespace=section_body_html[len(section_body_trimmed):]
        text_pieces.append(rhighlighted[last_position:current_match.start()])
        text_pieces.append(current_match.group(0))
        if match_index<len(header_wcs):
            wc_tag=f'<span style="color:#888; font-size:0.85em;"> ({header_wcs[match_index]}w)</span>'
        else:
            wc_tag=""
        text_pieces.append(section_body_trimmed+wc_tag)
        text_pieces.append(trailing_whitespace)
        last_position=body_end
    text_pieces.append(rhighlighted[last_position:])
    rhighlighted="".join(text_pieces)



    st.markdown(f'<div id="analysis-card" class="done">\n{rhighlighted}\n</div>', unsafe_allow_html=True)

    if show_notes:
        st.session_state.notes[rkey]=st.text_area("**Analysis Notes**", value=st.session_state.notes.get(rkey, ""), key=f"note_{rkey}", placeholder="Write down your notes")
    st.caption(f"{qcount}/{mqps} analyses used this session.")
    st.caption(f"Words: {wc}  |  Time: {elapsed_time}s | Model: {model_used} | Cost: ${call_cost:.4f}")
                            

    if rkey not in st.session_state.trends:
        try:
            trend_prompt=f'For "{rlabel}", is general public/media interest currently rising, flat, or declining? Reply with one word. If possible, usea real-time data, if not give a rough guess'
            trend_response=client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=10, messages=[{"role": "user", "content": trend_prompt}])
            trend_word=trend_response.content[0].text.strip()
            if trend_word not in ["Rising", "Flat", "Declining"]:
                trend_word="Unclear"
            st.session_state.trends[rkey]=trend_word
        except Exception:
            st.session_state.trends[rkey]="Unclear"
    trend_icon={"Rising": "📈", "Flat": "➡️", "Declining": "📉", "Unclear": "❔"}[st.session_state.trends[rkey]]
    st.caption(f"{trend_icon} Interest trend (rough estimate, not live data): {st.session_state.trends[rkey]}")


    if st.button("Sanity Check 🔍 (verify no contradictions)", key=f"sanity_btn{rkey}"):
        try:
            sanity_prompt=f"Read this business analysis carefully:\n\n{rresult}\n\nCheck wether any section contradicts or conflicts with another section - If you find a contradiction, name the two sections and briefly state the conflict in 3 sentences. If none, reply: 'No contradictions found'"
            sanity_response=client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=100, messages=[{"role": "user", "content": sanity_prompt}])
            sanity_result=sanity_response.content[0].text.strip()
            st.session_state.sanity[rkey]=sanity_result
        except Exception as sanity_error:
            st.session_state.sanity[rkey]=f"Couldn't run sanity check: {str(sanity_error)}"

    if rkey in st.session_state.sanity:
        if st.session_state.sanity[rkey]=="No contradictions found":
            st.success(f"✅ {st.session_state.sanity[rkey]}")
        else:
            st.warning(f"⚠️ {st.session_state.sanity[rkey]}")

    if rkey not in st.session_state.followups:
        st.session_state.followups[rkey]=[]
    if f"show_q{rkey}" not in st.session_state:
        st.session_state[f"show_q{rkey}"]=False
    if st.button("Questions❓", key=f"qbtn_{rkey}"):
        st.session_state[f"show_q{rkey}"]=not st.session_state[f"show_q{rkey}"]
    if st.session_state[f"show_q{rkey}"]:
        for past_q, past_a in st.session_state.followups[rkey]:
            st.markdown(f"**Q:** {past_q}")
            st.markdown(f"**A:** {past_a}")
        follow_q=st.text_area("Ask a question about this analysis", key=f"followup_input{rkey}", placeholder="Type your question")
        if st.button("Ask", key=f"followup_btn{rkey}"):
            if follow_q.strip():
                fu_messages=[{"role": "user", "content": f"Here is a business analysis:\n\n{rresult}\n\nAnswer questions about it, stay consistent with its conclusion and don't contradict the analysis"}]
                fu_messages.append({"role": "assistant", "content": "Understood, ask your question"})
                for past_q, past_a in st.session_state.followups[rkey]:
                    fu_messages.append({"role": "user", "content": past_q})
                    fu_messages.append({"role": "assistant", "content": past_a})
                fu_messages.append({"role": "user", "content": follow_q})
                try:
                    fu_response=client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=300, messages=fu_messages)
                    fu_answer=fu_response.content[0].text.strip()
                    st.session_state.followups[rkey].append((follow_q, fu_answer))
                    st.rerun()
                except Exception as fu_error:
                    st.error(f"Couldn't get an answer: {str(fu_error)}")
                    

    section_matches=re.findall(r"### ([^\n\[]+)", rresult)
    if section_matches:
        regen_meta=st.session_state.entry_meta.get(rkey)
        if regen_meta:
            regen1, regen2=st.columns([3,1])
            with regen1:
                regen_choice=st.selectbox("Regenerate a section", section_matches, key=f"regen_select{rkey}")
            with regen2:
                if st.button("Regenerate", key=f"regen_btn{rkey}"):
                    section_pattern=rf"### {re.escape(regen_choice)}.*?(?=\n### |\Z)"
                    old_section=re.search(section_pattern, rresult, re.DOTALL)
                    if old_section:
                        old_section_text=old_section.group(0)
                        regen_prompt=f"Here is one section from a larger business analysis of {rlabel}:\n\n{old_section_text}\n\nRewrite ONLY this section with fresh wording and possibly new angles. Keep same header, paragraph & sentence count same as the original. Stay consistent with the analysis:\n\n{rresult}\n\nReturn only the rewritten section. Format: '### {regen_choice}'"
                        try:
                            regen_model="claude-sonnet-4-6" if regen_meta["mode2"]=="Detailed" else "claude-haiku-4-5-20251001"
                            regen_response=client.messages.create(model=regen_model, max_tokens=375, messages=[{"role": "user", "content": regen_prompt}])
                            new_section=regen_response.content[0].text.strip()
                            updated_result=rresult.replace(old_section_text, new_section)
                            st.session_state.historyd[rkey]=updated_result
                            if rkey in st.session_state.cache:
                                old_cache=st.session_state.cache[rkey]
                                st.session_state.cache[rkey]=(updated_result, old_cache[1], old_cache[2], old_cache[3], old_cache[4])
                            if st.session_state.get("last_key")==rkey:
                                st.session_state.last_result=updated_result
                            st.rerun()
                        except Exception as regen_error:
                            st.error(f"Couldn't regenerate: {str(regen_error)}")

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
Any claim implying scale, or data (revenue, market size, failure rates, growth) must include an approximate real number or range - never vague words. For each major data claim, briefly note its basis in parentheses: (confirmed public data), (industry estimate), or (inference) - so it's clear how much to trust each figure. Both the '(' & ')' are required every single time you make the claim - never the closing parenthesis without its opening. NEVER mix it with other text
Immediately after each header's text, on the exact same line, append either: '[Stable]', '[Shifting]', or '[Volatile]' - based on how fast that factor changes in the real world, no explanation. ONLY add it where it makes a difference(not on e.g, Insight-Seeking Questions)

Immediately after the opening [Company:] or [Idea:] line and blank line, before the first '### header', state the general base rate for this category - how often businesses or ideas like this one actually succeed or fail in the real world, using an approximate percentage or fraction. In the same paragraph, state specifically how this case compares to that baseline and why. This paragraph is separate from all limits
In a separate unlabeled paragraph immediately after the base rate paragraph, state one to two specific, observable real-world signals that would indicate this analysis's core conclusion needs to be revised - concrete things a person could actually notice happening, not vague warnings. State early enough that noticing them still leaves time to change course based on the correction. This paragraph is also separate from all limits

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
Within this header(What Analysts Miss), explicitly reference one specific finding from an earlier header by name and state how it directly explains or causes the point being made here. Do not introduce this connection anywhere else in the analysis. Reference the header name as plain text within a sentence (e.g. "as the '**Revenue Structure**' section showed") - NEVER reproduce the '### ' symbol or format it as a new header

Immediately after this header's content and before ### Insight-Seeking Questions, add an unlabeled paragraph projecting how this specific case plausibly shifts at three points: 6 months, 12 months, and 24 months out. State one concrete, distinct change expected at each mark, each point MUST describe a different kind of change

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
Within this header(The Angle That Works), explicitly reference one specific finding from an earlier header by name and state how it directly explains or causes the point being made here. Do not introduce this connection anywhere else in the analysis. Reference the header name as plain text within a sentence (e.g. "as the '**Market Demand**' section showed") - NEVER reproduce the '### ' symbol or format it as a new header

Immediately after this header's content and before ### Insight-Seeking Questions, add an unlabeled paragraph projecting how this specific case plausibly shifts at three points: 6 months, 12 months, and 24 months out. State one concrete, distinct change expected at each mark, each point must describe a different kind of change

### Insight-Seeking Questions
One to two sharp, specific questions this analysis surfaces that only someone with real domain insider knowledge could answer - not generic questions, ones pointing directly at what's genuinely uncertain here and its answer can change this analysis' direction

Start with exactly: [Company: name] or [Idea: 2-4 word label](long answers: 95% ideas), then a blank line
Each sentence must have a min. of 10 and a max. of 30 words, NEVER FEWER, NEVER MORE. Don't combine different ideas under same paragraph
{"Write as much as needed following these rules: Use EXACTLY 2 paragraphs per header, separated by a blank line. Each paragraph MUST contain 2 to 4 sentences, NEVER FEWER OR MORE. Cover the most critical point per header" if mode=="Brief" else "Cover ALL headers with full depth. Write as much as needed, keep depth as priority. Use exactly 3 paragraphs per '###header', separated by a blank line. Each paragraph MUST contain 4 to 8 sentences, NEVER FEWER OR MORE. Vary angle per paragraph where natural - rotate between financial, competitive, behavioral, and structural angles across paragraphs"} {"Focus on hard data: real figures, specific percentages" if "Company" in input_type else "Focus on realistic scenarios: first 90 days, similar ideas failure patterns, specific entry barriers"}
Never use special symbols. Write numbers and percentages in plain text


End with exactly these sections:
{"### Comparables" + chr(10) + "Name 3 real, companies or ideas genuinely comparable to " + user_input + " - not vague category peers, but ones close enough that a real number comparison means something. For each, state one concrete number and how " + user_input + " compares against it directly. If no real comparable exists, say so plainly and explain why this case is unusually novel" if mode=="Extensive" and mode2=="Detailed" else ""}

### Vital Metrics
List the 3 most load-bearing numbers from this entire analysis in one place - format each structured as: **[where it came from]** - the number and why it matters to the user, written as one full sentence. Pull from what's already stated above

### Fragile Assumptions
{"Identify 1 critical assumption this analysis is quietly relying on. The kind that if wrong or suddenly changes, it shifts the whole analysis. Also state where this analysis was most confident based on actual facts" if tone=="Brutal" else "Call out directly where this analysis was overconfident or too certain, and why that confidence isn't fully earned. 3-sentence-max"}

### Devil's Advocate
{"Argue the strongest real case against this analysis's own main conclusion, as if hired specifically to prove it wrong. Use real comparable failures or counter-evidence, not hypothetical doubt. Do not soften it or hedge back toward the original conclusion afterward" if mode=="Extensive" and mode2=="Detailed" else "State the single strongest argument against this analysis's main conclusion, using one real comparable case where a similar conclusion turned out wrong. 3-sentence-max"}

### Ways 2 Validate
{"State 3 specific action that can be started and produce real signal within 30 days - a small, cheap test that would tell you whether this idea is worth pursuing further or should be set aside for good. If it can't be reached within 30 days(e.g, due to licensing or funding), state so directly and what can be done instead to still get a sense of its potential. State exactly what result from that action would give a clear 'keep going' versus 'best to set it aside', it MUST have a real threshold(number, specific reaction). Min. 8 sentences" if mode=="Extensive" and mode2=="Detailed" else "One specific, concrete action tied directly to the biggest finding in this analysis. If it's a company, one thing to investigate. If it's an idea, one thing to validate before going further. 5-sentence-max"}

### Execution Sequence
{"List 6 concrete steps for building this out in the real world, starting from zero - order them by what must happen first. Steps are not limited to findings already stated above; introduce whatever practical fundamentals apply. Do not repeat the test from 'Ways 2 Validate' as a step - this sequence assumes it already passed 'Ways 2 Validate'. Don't include infrastructure the person would not realistically have at this stage. Reply format: '[1] first step'" if mode=="Extensive" and mode2=="Detailed" else "List 4 concrete steps for building this out in the real world, starting from zero - Order them by what must happen first. Steps are not limited to findings already stated above; introduce whatever practical fundamentals apply. Do not repeat the test from 'Ways 2 Validate' as a step - this sequence assumes it already passed 'Ways 2 Validate'. Don't include infrastructure the person would not realistically have at this stage"}"""



st.set_page_config(page_title="Business Analyzer", page_icon="📊", layout="wide")
st.title("Business Analyzer 📊 ")
st.markdown("<p style='text-align: center; color: gray; font-size: 0.9em;'>Drop a company or idea, get it analyzed thoroughly</p>", unsafe_allow_html=True)
st.markdown('<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)
st.markdown("""<style> html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
h1 {text-align: center;}</style>""", unsafe_allow_html=True)
st.markdown("""<style>div[data-testid="stButton"] button { transition: transform 0.15s ease, box-shadow 0.15s ease;}
div[data-testid="stButton"] button:hover {transform: scale(1.11); box-shadow: 0 2px 8px rgba(0,0,0,0.2);}</style>""", unsafe_allow_html=True)

st.divider()
st.markdown(f"""<style> #analysis-card {{border:3px solid {colorcard_orange}; border-radius:10px; padding:20px; transition:border-color 3.5s; animation:fadeIn 1.0s ease-in;}}
#analysis-card.done {{border-color:{colorcard_green};}}@keyframes fadeIn {{from {{opacity:0;}} to {{opacity:1;}}}}
#analysis-card h3 {{color:{colorcard_orange}; border-left:4px solid {colorcard_orange}; padding-left:10px; margin-top:1.4em;}}
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
    st.session_state.sugs=("Airbnb", "Company")
if "psugs" not in st.session_state:
    st.session_state.psugs=None
if "cache" not in st.session_state:
    st.session_state.cache={}
if "notes" not in st.session_state:
    st.session_state.notes={}
if "history_keys" not in st.session_state:
    st.session_state.history_keys=[]
if "entry_meta" not in st.session_state:
    st.session_state.entry_meta={}
if "total_cost" not in st.session_state:
    st.session_state.total_cost=0.0
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode=False
if "haiku_count" not in st.session_state:
    st.session_state.haiku_count=0
if "sonnet_count" not in st.session_state:
    st.session_state.sonnet_count=0
if "company_count" not in st.session_state:
    st.session_state.company_count=0
if "idea_count" not in st.session_state:
    st.session_state.idea_count=0
if "timing_log" not in st.session_state:
    st.session_state.timing_log=[]
if "drift" not in st.session_state:
    st.session_state.drift=None
if "confirm" not in st.session_state:
    st.session_state.confirm=False
if "confirm_dup_proceed" not in st.session_state:
    st.session_state.confirm_dup_proceed=False
if "do_focus" not in st.session_state:
    st.session_state.do_focus=False
if "just_reset" not in st.session_state: 
    st.session_state.just_reset=False
if st.session_state.just_reset:
    st.toast("Session Reset ✅")
    st.session_state.just_reset=False
if "sugs_seen" not in st.session_state:
    st.session_state.sugs_seen=["Airbnb"]
if  "sug_last" not in st.session_state:
    st.session_state.sug_last="Company"
if "followups" not in st.session_state:
    st.session_state.followups={}
if "trends" not in st.session_state:
    st.session_state.trends={}
if "sanity" not in st.session_state:
    st.session_state.sanity={}
    
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

current_combo=f"{mode}|{mode2}|{tone}"
if st.session_state.drift is not None and st.session_state.drift!=current_combo:
    st.toast("Settings changed ⚠️")
st.session_state.drift=current_combo




est_output=maxt_br if mode=="Brief" else maxt_ex
est_input=800
if mode2=="Simplified":
    est_cost=(est_input*hcpt)+(est_output*hopt)
else:
    est_cost=(est_input*scpt)+(est_output*sopt)
st.caption(f"Estimated run cost: ~${est_cost:.4f} (actual may vary)")
st.caption(f"Session cost: ${st.session_state.total_cost:.4f}")



with st.expander("Session Summary"):
    st.markdown(f"**Total Analysis:** {st.session_state.query_count}/{mqps}")
    st.markdown(f"**Total Cost:** {st.session_state.total_cost:.4f}")
    st.markdown(f"**Model Split:** Haiku, ({st.session_state.haiku_count}). Sonnet, ({st.session_state.sonnet_count})")
    st.markdown(f"**Type Split:** Company, ({st.session_state.company_count}). Idea, ({st.session_state.idea_count})")
    if st.session_state.timing_log:
        avg_time=sum(st.session_state.timing_log)/len(st.session_state.timing_log)
        st.markdown(f"**Avg. time per analysis:** {avg_time:.1f}s")
        st.markdown(f"**Individual Times:** {', '.join(f'{t:.1f}s' for t in st.session_state.timing_log)}")


col4, col5=st.columns(2)
with col4:
    if st.session_state.get("confirm"):
        st.warning("Sure? This action can't be undone.")
        confirm_col, cancel_col=st.columns(2)
        with confirm_col:
            if st.button("Yes, reset"):
                keep_dark=st.session_state.dark_mode
                st.session_state.clear()
                st.session_state.dark_mode=keep_dark
                st.session_state.just_reset=True
                st.rerun()
        with cancel_col:
             if st.button("Cancel"):
                st.session_state.confirm=False
                st.rerun()
    else:
        if st.button("Reset Session 🔄"):
            st.session_state.confirm=True
            st.rerun()
with col5:
    if st.button("Dark Mode 🌙" if not st.session_state.dark_mode else "Light Mode ☀️"):
        st.session_state.dark_mode=not st.session_state.dark_mode
        st.rerun()




page_bg=bg_dark if st.session_state.dark_mode else bg_light
page_text=text_dark if st.session_state.dark_mode else text_light
divider_color="#444444" if st.session_state.dark_mode else "#dddddd"  
st.markdown(f"""<style> .stApp {{background-color:{page_bg}; color:{page_text};}}
.stApp p, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp div:not([id]), .stApp span:not([style]) {{color:{page_text} !important;}}
div[data-testid="stButton"] button {{background-color:{page_bg}; color:{page_text}; border:1px solid {page_text};}}
div[data-testid="stExpander"] {{background-color:{page_bg} !important;}}
div[data-testid="stExpander"] * {{background-color:transparent !important; color:{page_text} !important;}}
hr {{border-color:{divider_color} !important;}}</style>""", unsafe_allow_html=True)


def handle_analyze():
    pending_input=st.session_state[f"input_{st.session_state.input_key}"].strip()
    if not pending_input:
        st.session_state.pending_warning="Please enter something."
        st.session_state.show_dup_warning=False
    elif len(pending_input)>100:
        st.session_state.pending_warning="Input 2 long, please keep under 100 characters."
        st.session_state.show_dup_warning=False                   
    else:
        st.session_state.pending_warning=None
        if st.session_state.get("show_dup_warning") and st.session_state.get("dup_warned_input")==pending_input:
            st.session_state.is_running=True
            st.session_state.pending_input=pending_input
            st.session_state.show_dup_warning=False
        else:
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
                st.session_state.show_dup_warning=False
            elif similar:
                st.session_state.pending_input=pending_input
                st.session_state.dup_warned_input=pending_input
                st.session_state.show_dup_warning=True
            else:
                st.session_state.is_running=True
                st.session_state.pending_input=pending_input
                st.session_state.show_dup_warning=False




input_col, sugs_col=st.columns([4,1.3])
with input_col:
    user_input=st.text_input("Input", key=f"input_{st.session_state.input_key}", on_change=handle_analyze)
    st.caption(f"{len(user_input)}/100 characters")  
    if st.session_state.get("do_focus"):
        st.components.v1.html("""<script> var inputs=window.parent.document.querySelectorAll('input[type="text"]');
if(inputs.length>0){inputs[inputs.length-1].focus();} </script>""", height=0)
        st.session_state.do_focus=False       

with sugs_col:
    examples=[("Airbnb", "Company"), ("AI-automated Air Traffic Controller System", "Idea"), ("SaaS For Bio-Engineers", "Idea"), ("Adidas", "Company"), ("Subscription Meal Kits", "Idea"), ("Equinox", "Company"), ("Corporate Meditation Studios", "Idea")]
    def fresh_sugs(current_name):
        try:
            next_type="Idea" if st.session_state.sug_last=="Company" else "Company"
            avoid_list=", ".join(st.session_state.sugs_seen[-8:])

            sug_response=client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=15, messages=[{"role": "user", "content": f'Give one real {"well-known company" if next_type=="Company" else "interesting uncommon business idea(e.g. SaaS for Bio-Engineers)(be creative, but stay realistic & grounded)"} different from "{current_name}". Reply format: "{"Company: name" if next_type=="Company" else "Idea: 2 to 8 word label"}"'}])
            sug_text=sug_response.content[0].text.strip()
            if sug_text.startswith("Company:"):
                 new_name=sug_text.replace("Company:", "").strip()
                 new_type="Company"
            elif sug_text.startswith("Idea:"):
                new_name=sug_text.replace("Idea:", "").strip()
                new_type="Idea"
            else:
                new_name, new_type=random.choice(examples)
            st.session_state.sugs_seen.append(new_name)
            st.session_state.sug_last=new_type
            return (new_name, new_type)
        except Exception:
            return random.choice(examples)
        
    sug_name=st.session_state.sugs[0]
    sug_type=st.session_state.sugs[1]
    sug_badge=color_company if sug_type=="Company" else color_idea


    st.markdown("**Inspiration Panel**")
    st.markdown(f'''<div style="border:1px solid #555; border-radius:6px; padding:8px 12px; margin-bottom:14px;
background-color:rgba(255,255,255,0.05); display:flex; align-items:center; justify-content:space-between;"> <span>{sug_name}</span>
<span style="background-color:{sug_badge}; color:white; padding:2px 10px; border-radius:12px; font-size:0.8em; font-weight:bold;">{sug_type}</span>
</div>''', unsafe_allow_html=True)


    use_col, new_col=st.columns(2)
    with use_col:
        if st.button("Use"):
            st.session_state.psugs=st.session_state.sugs[0]
            st.session_state.do_focus=True
            st.rerun()
    with new_col:
        if st.button("New"):
            st.session_state.sugs=fresh_sugs(st.session_state.sugs[0])
            st.rerun()
    if st.button("Surprise Me"):
        st.session_state.sugs=fresh_sugs(st.session_state.sugs[0])
        st.session_state.psugs=st.session_state.sugs[0]
        st.session_state.do_focus=True
        st.rerun()


if not st.session_state.get("last_result") and not st.session_state.get("cached_hit") and not st.session_state.is_running and st.session_state.query_count<mqps:
    st.markdown(f"""<div style="text-align:center; padding:10px 10px; color:{colorcard_orange}; opacity:0.5;">
Drop a company or idea above and hit 'Analyze' to get started 🔍</div>""", unsafe_allow_html=True)


        
if st.session_state.query_count>=mqps:
    st.warning(f"You've used all {mqps} analyses this session. Refresh the page to start over.")
    st.subheader("Session Recap")
    for entry_key in st.session_state.history_keys:
        full_analysis=st.session_state.historyd[entry_key]
        meta=st.session_state.entry_meta[entry_key]
        if "### Ways 2 Validate" in full_analysis:
            move_section=full_analysis.split("### Ways 2 Validate")[1]
            move_section=move_section.split("###")[0].strip()
        else:
            move_section="No move identified."
        st.markdown(f"**{meta['label']} ({meta['mode']}/{meta['mode2']}/{meta['tone']})** - {move_section}")    
else:
    if st.session_state.query_count==mqps-1:
        st.warning(f"Last analysis this session ⚠️ ({st.session_state.query_count+1}/{mqps})")

    if st.session_state.get("show_dup_warning") and st.session_state.get("confirm_dup_proceed"):
        analyze_button_label="Confirm Analyze Anyway"
    elif st.session_state.get("show_dup_warning"):
        analyze_button_label="Analyze Anyway"
    elif st.session_state.query_count==mqps-1:
        analyze_button_label="Analyze (Final)"
    else:
        analyze_button_label="Analyze"




    if st.session_state.get("show_dup_warning"):
        col6, col7=st.columns(2)
        with col6:
            if st.session_state.get("confirm_dup_proceed"):
                if st.button(analyze_button_label, disabled=st.session_state.is_running, on_click=handle_analyze):
                    pass
            else:
                if st.button(analyze_button_label):
                    st.session_state.confirm_dup_proceed=True
                    st.rerun()
        with col7:
            if st.button("Cancel"):
                st.session_state.show_dup_warning=False
                st.session_state.confirm_dup_proceed=False
                st.rerun()   
    else:
        if st.button(analyze_button_label, disabled=st.session_state.is_running, on_click=handle_analyze):
            pass
        



    if st.session_state.get("pending_warning"):
        st.warning(st.session_state.pending_warning)
        st.session_state.pending_warning=None 
    if st.session_state.get("show_dup_warning"):
        st.warning("You may have already analyzed something similar. Check 'Session History' below")




    if st.session_state.get("cached_hit"):
        key=st.session_state.cached_hit
        cached_result, cached_elapsed, cached_wc, cached_label, cached_cost=st.session_state.cache[key]
        st.info("Instant⚡")
        cached_type, cached_name=cached_label.split(": ", 1) if ": " in cached_label else ("Company", cached_label)
        cached_color=color_company if cached_type=="Company" else color_idea
        render_analysis_card(cached_name, key, cached_result, cached_type, cached_color, st.session_state.query_count, cached_wc, cached_elapsed, "Sonnet" if mode2=="Detailed" else "Haiku", cached_cost)
        if st.button("Clear"):
            st.session_state.cached_hit=None
            st.rerun()
        



    if st.session_state.get("last_result") and not st.session_state.is_running:
        render_analysis_card(st.session_state.last_label, st.session_state.last_key, st.session_state.last_result, st.session_state.last_banner_type, st.session_state.last_banner_color, st.session_state.last_qcount, st.session_state.last_wc, st.session_state.last_elapsed, st.session_state.last_model, st.session_state.last_cost)
        if st.session_state.get("last_cut"):
            if st.button("Extend ⏩(continue where it cut off)"):
                extend_prompt=f"This business analyis was cut off before finishing:\n\n{st.session_state.last_result}\n\nContinue EXACTLY where it left off - do NOT repeat any part, restart, add new opening. Pick up mid-sentence or mid-section and keep going until analysis is properly complete, ending with 'Execution Sequence'"
                try:
                    extend_model="claude-sonnet-4-6" if st.session_state.entry_meta[st.session_state.last_key]["mode2"]=="Detailed" else "claude-haiku-4-5-20251001"
                    extend_response=client.messages.create(model=extend_model, max_tokens=300, messages=[{"role": "user", "content": extend_prompt}])
                    extend_text=extend_response.content[0].text.strip()
                    extended_result=st.session_state.last_result+"\n\n"+extend_text
                    st.session_state.last_result=extended_result
                    st.session_state.historyd[st.session_state.last_key]=extended_result
                    if st.session_state.last_key in st.session_state.cache:
                        old_cache=st.session_state.cache[st.session_state.last_key]
                        st.session_state.cache[st.session_state.last_key]=(extended_result, old_cache[1], old_cache[2], old_cache[3], old_cache[4])
                    st.session_state.last_cut=False
                    st.rerun()
                except Exception as extend_error:
                    st.error(f"Couldn't extend: {str(extend_error)}")
                    

        if st.button(" New analysis 🔄"):
            st.session_state.last_result=None
            st.session_state.cached_hit=None
            st.session_state.analysis_done=False
            st.session_state.input_key+=1
            st.session_state.do_focus=True
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
            bannerc=color_company
        else:
            label=first_line.replace("[Idea:", "").replace("]", "").strip()
            bannert="Idea"
            bannerc=color_idea
        st.markdown(f'<div id="recognize-msg" style="background-color:{bannerc}; color:white; padding:10px 16px; border-radius:8px; font-weight:bold; font-size:1.1em;">{bannert}: {label}</div>', unsafe_allow_html=True)
        st.divider()

        st.session_state.query_count+=1
        st.markdown(f"""<style>div[data-testid="stProgress"] {{position: fixed;
bottom: 0; left: 0; width: 100%; z-index: 999; background: {page_bg}; padding: 10px;}}
div[data-testid="stProgress"] div[role="progressbar"] > div {{background-color:{color_company}; animation: barPulse 1.7s ease-in-out infinite;}}
@keyframes barPulse{{0%{{opacity:1;}}50%{{opacity:0.6;}}100%{{opacity:1;}}}}
div[data-testid="stSpinner"] p {{font-family:'Inter', sans-serif; color:{page_text} !important;}}</style>""", unsafe_allow_html=True)



        placeholder=st.empty()
        with st.spinner("Analyzing..."):
            progress_bar=st.progress(0)
            timer_placeholder=st.empty()
            result, elapsed, final_wc, call_cost, was_cut=ask_claude_stream(analyze(cleaned_input, mode, tone, first_line), placeholder, mode2, mode, progress_bar, timer_placeholder)
            progress_bar.empty()
            timer_placeholder.empty()
        st.session_state.is_running=False
        if result and result.startswith("ERROR"):
            placeholder.error(result)
            st.session_state.query_count-=1
            st.stop()
        no_tag=["Insight-Seeking Questions", "Vital Metrics", "Fragile Assumptions", "Ways 2 Validate", "Execution Sequence", "Comparables"]
        for header_name in no_tag:
            result=re.sub(rf"(### {header_name})\s*\[(Stable|Shifting|Volatile)\]", r"\1", result)
            


        
        st.toast("Analysis complete ✅")
        if was_cut:
            st.warning("This analysis may have been cut short b4 it finished. Consider re-running if incomplete.")
        st.session_state.analysis_done=True
        cache_key=f"{cleaned_input.lower()} | {mode} | {mode2} | {tone}"
        st.session_state.history.append(label)
        st.session_state.history_keys.append(cache_key)
        st.session_state.entry_meta[cache_key]={"label":label, "mode":mode, "mode2":mode2, "tone":tone}
        st.session_state.historyd[cache_key]=result
        st.session_state.last_result=result
        st.session_state.last_label=label
        st.session_state.last_key=cache_key
        st.session_state.last_banner_type=bannert
        st.session_state.last_banner_color=bannerc
        st.session_state.total_cost=st.session_state.total_cost+call_cost


        if mode2=="Simplified":
            st.session_state.haiku_count=st.session_state.haiku_count+1
        else:
            st.session_state.sonnet_count=st.session_state.sonnet_count+1
        if bannert=="Company":
            st.session_state.company_count=st.session_state.company_count+1
        else:
            st.session_state.idea_count=st.session_state.idea_count+1


        st.session_state.timing_log.append(elapsed)
        full_label=f"{'Company' if 'Company' in first_line else 'Idea'}: {label}"
        st.session_state.cache[cache_key]=(result, elapsed, final_wc, full_label, call_cost)
        st.session_state.last_qcount=st.session_state.query_count
        st.session_state.last_model=model_used="Sonnet" if mode2=="Detailed" else "Haiku"
        st.session_state.last_wc=final_wc
        st.session_state.last_elapsed=elapsed
        st.session_state.last_cost=call_cost
        st.session_state.last_cut=was_cut
        st.rerun()


with st.expander("Session history"):
    if st.session_state.history_keys:
        display_to_key={}
        for k in st.session_state.history_keys:
            m=st.session_state.entry_meta[k]
            disp=f"{m['label']} **({m['mode']}/{m['mode2']}/{m['tone']})**"
            display_to_key[disp]=k
        selected_disp=st.radio("Past Analyses:", ["- select 2 view -"] + list(display_to_key.keys()), key="history_select")

        if selected_disp and selected_disp != "- select 2 view -":
            sel_key=display_to_key[selected_disp]
            sel_result=st.session_state.historyd[sel_key]
            sel_meta=st.session_state.entry_meta[sel_key]
            sel_cached=st.session_state.cache.get(sel_key)
            if sel_cached:
                sel_full=sel_cached[3]
                sel_type, sel_name=sel_full.split(": ", 1) if ": " in sel_full else ("Company", sel_full)
                sel_color=color_company if sel_type=="Company" else color_idea
                render_analysis_card(sel_name, sel_key, sel_result, sel_type, sel_color, st.session_state.query_count, sel_cached[2], sel_cached[1], "Sonnet" if sel_meta["mode2"]=="Detailed" else "Haiku", sel_cached[4])
            else:
                st.warning("Full details for this entry weren't cached - showing basic text only")
                st.markdown(sel_result.split("\n", 1)[1] if "\n" in sel_result else sel_result)
        else: 
            st.caption("Select an analysis above to view it")
    else:
        st.markdown(f"""<div style="text-align:center; padding:30px 10px; color:{colorcard_orange}; opacity:0.6;">
No analysis yet</div>""", unsafe_allow_html=True)


with st.expander("About this tool"):
    st.markdown("""**Business Analyzer** uses AI to break down companies and business ideas beyond surface-level takes.

**How 2 Use:**
- Type a company name or business idea and hit 'Analyze'.
- **Brief** mode gives you the sharpest single insight per section. **Extensive** mode goes deeper with multiple angles per section.
- **Simplified** is faster and less acute. **Detailed** is slower but sharper.
- **Neutral** mode limits judgment. **Brutal** mode adds an extra judgment lens.

**Limit:** 3 analysis per session, refresh to reset.""")
