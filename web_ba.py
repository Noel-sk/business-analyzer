import streamlit as st
import anthropic
import os

try:
    api_key=st.secrets["ant_api1"]
except Exception:
    api_key=os.environ.get("ant_api1")
client=anthropic.Anthropic(api_key=api_key)
mqps=3


def ask_claude_stream(prompt, placeholder, mode2):
    try:
        with client.messages.stream(model="claude-haiku-4-5-20251001" if mode2=="Haiku" else "claude-sonnet-4-6", max_tokens=1625, messages=[{"role": "user", "content": prompt}]) as stream:
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
            return full_text
    except anthropic.AuthenticationError:
        return "ERROR: API key is missing or invalid."
    except anthropic.RateLimitError:
        return "ERROR: Rate limit hit. Wait a moment and try again."
    except anthropic.APIConnectionError:
        return "ERROR: Could not connect to Anthropic."
    except Exception as e:
        return f"ERROR: Something went wrong - {str(e)}"



def analyze(user_input, mode):
    return f"""You are a contrarian business analyst with deep field experience. You prioritize uncomfortable truths over conventional wisdom. Determine if "{user_input}" is an existing company or a business idea, then analyze it

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
Use 2-sentence maximum paragraphs. Max 3 paragraphs per header. Don't combine different ideas under same paragraph.
{"Keep the entire analysis under 465 words." if mode=="Quick" else "Be thourough & detailed. Prioritize depth over breadth"}
Never use special symbols. Write numbers and percentages in plain text"""



st.set_page_config(page_title="Business Analyzer", layout="centered")
st.title("Business Analyzer")
st.markdown("Enter a company name or business idea.\n Get A Straight-Forward Analysis. ")
st.divider()

if "query_count" not in st.session_state:
    st.session_state.query_count=0
if "history" not in st.session_state:
    st.session_state.history=[]
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done=False
if "is_running" not in st.session_state:
    st.session_state.is_running=False
if "input_key" not in st.session_state:
    st.session_state.input_key=0

col1, col2=st.columns(2)
with col1:
    mode=st.radio("Analysis depth: ", ["Quick", "Full"], horizontal=True)
with col2:
    mode2=st.radio("Model: ", ["Haiku", "Sonnet"], horizontal=True)
user_input=st.text_input("Your input:", key=f"input_{st.session_state.input_key}")
st.caption(f"{len(user_input)}/100 characters")



if st.session_state.query_count>=mqps:
    st.warning(f"Limit reached ({mqps} analyses). Refresh the page to continue.")
else:
    if st.button("Analyze", disabled=st.session_state.is_running):
        cleaned_input=user_input.strip()
        if not cleaned_input: 
            st.warning("Please enter something.")
        elif len(cleaned_input)> 100:
            st.warning("Input too long, please keep under 100 characters.")
        else:
            st.session_state.is_running=True
            st.session_state.query_count+=1
            
            with st.spinner("Recognizing..."):
                peek=client.messages.create(model="claude-haiku-4-5-20251001" if mode2=="Haiku" else "claude-sonnet-4-6", max_tokens=10, messages=[{"role": "user", "content": f'Is "{cleaned_input}" a real existing company or a business idea? Reply with one word: [Company: name] or [Idea: 2-4 word label]'}])
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
            placeholder=st.empty()
            with st.spinner("Analyzing..."):
                result=ask_claude_stream(analyze(cleaned_input, mode), placeholder, mode2)
            if result and result.startswith("ERROR"):
                placeholder.error(result)

            st.session_state.is_running=False
            st.toast("Analysis complete ✅")
            st.session_state.analysis_done=True
            st.session_state.history.append(label)
            st.caption(f"{st.session_state.query_count}/{mqps} analyses used this session.")

            if st.session_state.get("analysis_done"):
                if st.button(" New analysis 🔄"):
                    st.session_state.analysis_done=False
                    st.session_state.input_key+=1
                    st.rerun()
with st.expander("Session history"):
    if st.session_state.history:
        for item in st.session_state.history:
            st.caption(f" - {item}")
    else: st.caption("No analysis yet.")
