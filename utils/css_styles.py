import streamlit as st

def inject_custom_css():
    """Injects custom CSS to apply a high-end dark glassmorphic theme to the Streamlit app."""
    css_code = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    /* Target main containers and body */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        background: linear-gradient(135deg, #0A0E1A 0%, #121829 100%) !important;
        color: #F3F4F6 !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: rgba(10, 14, 26, 0.95) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.3) !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown h1, 
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: #818CF8 !important;
        font-weight: 600;
    }

    /* Glassmorphic card styling for content divs and native containers */
    .glass-card, div[data-testid="stVerticalBlockBorder"] {
        background: rgba(22, 28, 45, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.25) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        margin-bottom: 20px !important;
        transition: transform 0.3s ease, border-color 0.3s ease !important;
    }
    
    .glass-card:hover, div[data-testid="stVerticalBlockBorder"]:hover {
        transform: translateY(-2px) !important;
        border-color: rgba(99, 102, 241, 0.3) !important;
    }
    
    /* Elegant Title and Header styling */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    .main-title {
        background: linear-gradient(90deg, #6366F1 0%, #A5B4FC 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem !important;
        font-weight: 800 !important;
        text-align: center;
        margin-bottom: 5px;
        filter: drop-shadow(0px 2px 8px rgba(99, 102, 241, 0.15));
    }
    
    .subtitle {
        text-align: center;
        color: #9CA3AF;
        font-size: 1.15rem;
        margin-bottom: 35px;
        font-weight: 300;
    }

    /* Metric cards styling */
    .metric-container {
        display: flex;
        justify-content: space-between;
        gap: 15px;
        margin: 20px 0;
    }

    .metric-card {
        flex: 1;
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #818CF8, #C084FC);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Custom Chat bubbles */
    .chat-bubble {
        padding: 15px 20px;
        border-radius: 18px;
        margin-bottom: 12px;
        line-height: 1.5;
        max-width: 85%;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
        font-size: 1rem;
    }

    .chat-bubble.ai {
        background: rgba(31, 41, 55, 0.7);
        border-left: 4px solid #6366F1;
        border-top-left-radius: 4px;
        margin-right: auto;
        color: #E5E7EB;
    }

    .chat-bubble.user {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(129, 140, 248, 0.15) 100%);
        border-right: 4px solid #EC4899;
        border-top-right-radius: 4px;
        margin-left: auto;
        color: #F9FAFB;
    }
    
    /* Interactive status banners */
    .status-banner {
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 500;
    }
    
    .status-banner.success {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34D399;
    }
    
    .status-banner.warning {
        background: rgba(245, 158, 11, 0.15);
        border: 1px solid rgba(245, 158, 11, 0.3);
        color: #FBBF24;
    }

    /* Custom scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(10, 14, 26, 0.1);
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(99, 102, 241, 0.3);
    }
    
    /* Streamlit overrides for inputs and widgets */
    div[data-baseweb="input"] {
        background-color: rgba(17, 24, 39, 0.8) !important;
        border-color: rgba(255, 255, 255, 0.1) !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #6366F1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25) !important;
    }
    
    div[data-testid="stFileUploader"] {
        background-color: rgba(22, 28, 45, 0.5) !important;
        border: 2px dashed rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px;
        padding: 10px;
        transition: border-color 0.3s;
    }
    
    div[data-testid="stFileUploader"]:hover {
        border-color: #6366F1 !important;
    }

    /* Custom interview question spotlight */
    .question-spotlight {
        font-size: 1.35rem;
        font-weight: 600;
        color: #FFFFFF;
        line-height: 1.6;
        border-left: 5px solid #818CF8;
        padding-left: 20px;
        margin: 25px 0;
        background: linear-gradient(90deg, rgba(129, 140, 248, 0.08) 0%, rgba(129, 140, 248, 0) 100%);
        border-radius: 0 8px 8px 0;
        padding-top: 12px;
        padding-bottom: 12px;
    }
    
    /* Audio recorder custom aligner */
    .recorder-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        background: rgba(30, 41, 59, 0.4);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin: 20px 0;
    }

    .recorder-title {
        font-size: 0.9rem;
        color: #9CA3AF;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    </style>
    """
    st.markdown(css_code, unsafe_allow_html=True)
