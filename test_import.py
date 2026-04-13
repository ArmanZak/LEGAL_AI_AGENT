import sys
import pathlib

out = pathlib.Path('C:/Users/PC/Desktop/Programs/LEGAL_AI_AGENT/test_out.txt')

def log(msg):
    current = out.read_text() if out.exists() else ''
    out.write_text(current + msg + '\n')

log('step 1: starting')

try:
    import os
    log('step 2: os ok')
    import json
    log('step 3: json ok')
    from groq import Groq
    log('step 4: groq ok')
    from dotenv import load_dotenv
    log('step 5: dotenv ok')
    load_dotenv('C:/Users/PC/Desktop/Programs/LEGAL_AI_AGENT/.env')
    log('step 6: dotenv loaded')
    import streamlit
    log('step 7: streamlit imported - version ' + streamlit.__version__)
except Exception as e:
    import traceback
    log(f'ERROR: {e}\n{traceback.format_exc()}')
