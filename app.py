import streamlit as st
from pathlib import Path
import sys
import os
import time

# 将项目根目录添加到 sys.path 以允许从 src 导入模块
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- Page Config ---
# THIS MUST BE THE FIRST STREAMLIT COMMAND
st.set_page_config(page_title="MindX", page_icon="💡", layout="wide")

try:
    from main import ContentProcessor
except ImportError as e:
    st.error(f"无法导入 ContentProcessor: {e}. 请确保 main.py 和相关模块在正确的位置，并且 PYTHONPATH 设置正确。")
    st.info(f"当前 sys.path: {sys.path}")
    st.info(f"项目根目录: {project_root}")
    st.stop()

# --- Custom CSS for Light Theme (inspired by the provided image) ---
custom_css = """
<style>
    /* Base for light theme */
    body {
        color: #333333; /* Dark gray text */
        background-color: #F8F9FA; /* Light gray background */
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }

    /* Main title (e.g., "MindX: 一键生成思维导图") */
    h1 {
        color: #007BFF; /* Blue color for main title */
        text-align: center;
        padding-top: 1rem;
        padding-bottom: 0.5rem;
    }
    
    /* Subheaders */
    h2, h3 {
        color: #212529; /* Darker gray for subheaders */
    }

    /* General Button Styling (like "登录" button in image - bordered) */
    div.stButton > button {
        border: 1px solid #007BFF; /* Blue border */
        border-radius: 0.375rem; /* 6px */
        background-color: #FFFFFF; /* White background */
        color: #007BFF; /* Blue text */
        padding: 0.5rem 1rem; /* 8px 16px */
        font-weight: 600; /* semibold */
        transition: background-color 0.2s, color 0.2s;
    }
    div.stButton > button:hover {
        background-color: #007BFF; /* Blue background on hover */
        color: #FFFFFF; /* White text on hover */
        border-color: #007BFF;
    }
    div.stButton > button:disabled {
        background-color: #E9ECEF; /* Light gray when disabled */
        border-color: #CED4DA;
        color: #6C757D;
        cursor: not-allowed;
    }

    /* Specific for the main action button (e.g., "生成导图" - orange like "免费试用") */
    /* This targets the submit button in a form. May need adjustment if structure changes. */
    div[data-testid="stForm"] div.stButton > button[kind="formSubmit"] {
        background-color: #FFA500; /* Orange background */
        border-color: #FFA500;
        color: #FFFFFF; /* White text */
    }
    div[data-testid="stForm"] div.stButton > button[kind="formSubmit"]:hover {
        background-color: #E69500; /* Darker orange on hover */
        border-color: #E69500;
    }
    div[data-testid="stForm"] div.stButton > button[kind="formSubmit"]:disabled {
        background-color: #FFD699; /* Lighter orange when disabled */
        border-color: #FFD699;
        color: #FFFFFF;
    }
    
    /* Specific for "停止处理" button - making it red */
    div.stButton > button:contains("停止处理") { 
        background-color: #DC3545; /* Red background */
        border-color: #DC3545;
        color: #FFFFFF;
    }
    div.stButton > button:contains("停止处理"):hover {
        background-color: #C82333; /* Darker red on hover */
        border-color: #C82333;
    }


    /* Text Input */
    div.stTextInput > div > div > input, div.stTextArea > div > textarea {
        border: 1px solid #CED4DA; /* Medium gray border */
        background-color: #FFFFFF; /* White input background */
        color: #495057; /* Dark gray text in input */
        border-radius: 0.375rem;
        padding: 0.5rem 0.75rem;
    }
    div.stTextInput > div > div > input:focus, div.stTextArea > div > textarea:focus {
        border-color: #80BDFF; /* Lighter blue border on focus */
        box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
    }
    /* Input Label */
    label.st-emotion-cache-ue6h3e { /* This selector might be fragile, inspect if needed */
        color: #495057; /* Match input text color or slightly darker */
        font-size: 1rem;
        margin-bottom: 0.5rem;
    }


    /* Tabs */
    div[data-baseweb="tabs"] {
        border-radius: 0.375rem;
        overflow: hidden;
        border: 1px solid #DEE2E6;
    }
    div[data-baseweb="tab-list"] {
        background-color: #F8F9FA; /* Tab list background */
        padding: 0.25rem;
        border-bottom: 1px solid #DEE2E6;
    }
    div[data-baseweb="tab"] {
        background-color: transparent;
        color: #007BFF; /* Blue for inactive tab text */
        border-radius: 0.375rem;
        margin: 0.25rem;
        padding: 0.5rem 1rem;
    }
    div[data-baseweb="tab--selected"] {
        background-color: #007BFF; /* Active tab background - primary blue */
        color: #FFFFFF !important; /* Active tab text */
    }
    div[data-baseweb="tab-highlight"] {
        background-color: transparent !important;
    }


    /* Code blocks */
    pre {
        background-color: #F8F9FA !important; /* Light background for code */
        border: 1px solid #DEE2E6 !important; 
        border-radius: 0.375rem !important;
        padding: 1rem !important;
        font-size: 0.875rem; /* 14px */
    }
    pre code { 
        color: #212529 !important; /* Dark text for code */
    }

    /* Info, Success, Warning, Error boxes */
    div.stAlert {
        border-radius: 0.375rem;
        border-width: 1px;
        border-style: solid;
        padding: 1rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    div.stAlert[data-testid="stInfo"] {
        background-color: #E7F3FF; 
        border-color: #CCE5FF; 
        color: #004085; 
    }
    div.stAlert[data-testid="stSuccess"] {
        background-color: #D4EDDA;
        border-color: #C3E6CB;
        color: #155724;
    }
     div.stAlert[data-testid="stWarning"] {
        background-color: #FFF3CD;
        border-color: #FFEEBA;
        color: #856404;
    }
    div.stAlert[data-testid="stError"] {
        background-color: #F8D7DA;
        border-color: #F5C6CB;
        color: #721C24;
    }
    
    /* Sidebar styling */
    div[data-testid="stSidebar"] {
        background-color: #E9ECEF; /* Lighter gray for sidebar */
        padding: 1.5rem 1rem;
        border-right: 1px solid #DEE2E6;
    }
    div[data-testid="stSidebar"] h1, 
    div[data-testid="stSidebar"] h2, 
    div[data-testid="stSidebar"] h3,
    div[data-testid="stSidebar"] p,
    div[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] { /* Target markdown text in sidebar */
        color: #343A40; /* Dark gray for sidebar text */
    }
    div[data-testid="stSidebar"] a {
        color: #0056B3; /* Darker blue for links in sidebar */
    }

    /* Make Streamlit code copy button's header always visible */
    div[data-testid="stCodeBlock"] > div:nth-child(1) { /* Targets the first child div (header) */
        opacity: 1 !important;
    }

    /* Style the copy button for better visibility on light theme */
    div[data-testid="stCodeBlock"] > div:nth-child(1) button {
        background-color: #f0f2f6 !important; /* Light grey, distinct from code block bg */
        border: 1px solid #d9d9d9 !important; /* Subtle border */
        color: #333333 !important; /* Darker icon color for contrast on light bg */
        border-radius: 4px !important;
        padding: 3px 7px !important; 
        margin-right: 4px !important; 
        line-height: 1 !important; 
    }

    div[data-testid="stCodeBlock"] > div:nth-child(1) button svg {
        fill: #333333 !important; /* Ensure SVG icon color matches button text color */
    }

    div[data-testid="stCodeBlock"] > div:nth-child(1) button:hover {
        background-color: #e6e6e6 !important; /* Slightly darker on hover */
        border-color: #cccccc !important;
    }

</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


st.title("MindX") # Updated title

# --- Initialize Session State ---
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False
if 'current_url_to_process' not in st.session_state:
    st.session_state.current_url_to_process = ""
if 'results_data' not in st.session_state:
    st.session_state.results_data = None
if 'processor_instance' not in st.session_state:
    with st.spinner("正在初始化应用资源，请稍候..."):
        try:
            st.session_state.processor_instance = ContentProcessor()
            st.toast("应用资源初始化成功!", icon="🎉")
        except Exception as e:
            st.error(f"初始化 ContentProcessor 时出错: {e}")
            st.stop()

processor = st.session_state.processor_instance

# --- Input Form ---
with st.form(key="url_form"):
    url_input_val = st.text_input(
        "粘贴链接 (YouTube, Bilibili, 小宇宙) 或文本内容:", # Updated label
        value=st.session_state.current_url_to_process if st.session_state.is_processing else "",
        placeholder="例如：https://www.youtube.com/watch?v=... 或直接粘贴文字", # Updated placeholder
        disabled=st.session_state.is_processing,
        label_visibility="collapsed" # Hide label if title is descriptive enough, or keep visible
    )
    # Adding a sub-description text like in the image
    st.markdown(
        "<p style='text-align: center; color: #6C757D; font-size: 0.9rem; margin-top: -10px; margin-bottom:15px;'>输入音视频链接或文本内容，自动生成结构化笔记，提升学习效率</p>",
        unsafe_allow_html=True
    )

    submitted = st.form_submit_button(
        label="生成导图" if not st.session_state.is_processing else "处理中...", # Updated button text
        disabled=st.session_state.is_processing,
        use_container_width=True # Make button wider
    )

if submitted and not st.session_state.is_processing:
    if not url_input_val:
        st.warning("请输入链接！", icon="⚠️")
    else:
        st.session_state.is_processing = True
        st.session_state.current_url_to_process = url_input_val
        st.session_state.results_data = None # Clear previous results
        st.rerun() # Changed from st.experimental_rerun()

# --- Processing Logic and Stop Button ---
if st.session_state.is_processing:
    # Make the stop button less prominent or style it differently if needed
    # The CSS :contains("停止处理") selector will attempt to style it.
    if st.button("停止处理"): # Text changed for CSS selector
        st.session_state.is_processing = False
        st.session_state.results_data = {"message": "处理已由用户停止。"} # Show a message
        st.rerun() # Changed from st.experimental_rerun()
    else:
        st.info(f"🔗 正在处理链接: {st.session_state.current_url_to_process}", icon="⏳")
        
        # Placeholder for future detailed progress bar integration
        # st.info("提示: 详细进度条功能正在开发中。")
        # progress_bar_placeholder = st.empty() 
        # def update_streamlit_progress(current_step, total_steps, message_progress):
        #     if total_steps > 0:
        #         progress_bar_placeholder.progress(current_step / total_steps, text=f"{message_progress} ({current_step}/{total_steps})")

        with st.spinner("内容处理中，这可能需要一些时间... 请耐心等待..."):
            try:
                # In a future update, ContentProcessor.process_content could accept a callback
                # e.g., processor.process_content(st.session_state.current_url_to_process, progress_callback=update_streamlit_progress)
                original_text, translated_text, mindmap_file_path_str = \
                    processor.process_content(st.session_state.current_url_to_process)
                
                # This check is mostly for completion; stop button click causes a rerun,
                # so this part might not be reached if stop was effective.
                if st.session_state.is_processing: # Check if still in processing state (not stopped)
                    st.session_state.results_data = {
                        "original": original_text,
                        "translated": translated_text,
                        "mindmap_path": mindmap_file_path_str,
                        "processed_url": st.session_state.current_url_to_process # Store for context
                    }
            except ValueError as ve:
                st.session_state.results_data = {"error": f"处理失败: {ve}"}
            except Exception as e:
                st.session_state.results_data = {"error": f"发生意外错误: {e}"}
                # import traceback # For debugging
                # st.text_area("错误详情:", traceback.format_exc(), height=200)
            finally:
                st.session_state.is_processing = False # Mark processing as done
                # if hasattr(progress_bar_placeholder, 'empty'): progress_bar_placeholder.empty()
                st.rerun() # Changed from st.experimental_rerun() # Rerun to display results or error

# --- Display Results ---
if st.session_state.results_data:
    results = st.session_state.results_data
    
    if results.get("message"): # For messages like "处理已由用户停止"
        st.info(results["message"])
    elif results.get("error"):
        st.error(results["error"], icon="🔥")
    elif "original" in results:
        # Use st.success for the main "Processing complete" message
        st.success(f"处理完成！ 🎉 (源链接: {results.get('processed_url', 'N/A')})")


        original_text = results["original"]
        translated_text = results["translated"]
        mindmap_file_path_str = results["mindmap_path"]

        st.subheader("转写文本:")
        if translated_text: 
            tab_chinese, tab_original = st.tabs(["中文翻译 (机器)", "原文"])
            with tab_chinese:
                st.code(translated_text, language=None) 
            with tab_original:
                st.code(original_text, language=None)
        elif original_text: # Original text exists, but no translation
            st.code(original_text, language=None)
            st.caption("原文内容已显示。如需翻译但未显示，请检查原文语言或翻译服务状态。")
        else: # Neither original nor translated text is available
            st.info("转写文本数据为空。")

        st.subheader("思维导图 (Markdown):")
        if mindmap_file_path_str:
            mindmap_file_path = Path(mindmap_file_path_str).resolve()
            if mindmap_file_path.exists() and mindmap_file_path.suffix.lower() == ".md":
                try:
                    with open(mindmap_file_path, "r", encoding="utf-8") as f:
                        md_content = f.read()
                    st.code(md_content, language="markdown")
                    st.caption(f"Markdown 文件: `{mindmap_file_path.name}` (位于输出目录)")
                except Exception as e:
                    st.error(f"读取 Markdown 思维导图文件时出错: {e}")
            else:
                st.warning(f"思维导图文件路径为: {mindmap_file_path_str}，但未能正确加载为 Markdown。请检查文件格式和路径。")
        else:
            st.error("未能生成或找到思维导图文件。", icon="❌")

# --- Sidebar ---
st.sidebar.header("关于应用")
st.sidebar.info(
    "本应用可以将 YouTube、Bilibili、小宇宙等平台的音视频内容，"
    "通过 ASR 技术转写为文本，并利用大语言模型（如 DeepSeek V3）生成 Markdown 格式的思维导图。"
    "如果内容为英文，还会尝试进行中文翻译。"
)
st.sidebar.markdown("---")
st.sidebar.markdown("开发者：GPTinsight") # Updated developer name
st.sidebar.markdown("Powered by [Streamlit](https://streamlit.io)")