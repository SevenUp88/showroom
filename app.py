import streamlit as st
import pdfplumber
import pandas as pd
from fpdf import FPDF
from duckduckgo_search import DDGS
import re
import requests
from io import BytesIO
from PIL import Image
import os

st.set_page_config(page_title="Consorzio Showroom Pro", layout="wide")

# URL del tuo logo su GitHub (Versione RAW per l'accesso diretto)
LOGO_URL = "https://raw.githubusercontent.com/SevenUp88/showroom/main/Showroomlogo_trasp.png"

# --- FUNZIONI DI SERVIZIO ---
def clean_stutter(text):
    if not text: return ""
    return "".join(text[::2]) if ".." in text or ",," in text else text

def get_image_url(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=1))
            return results[0]['image'] if results else None
    except: return None

def download_image(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except:
        return None

# --- PARSER PDF ---
def parse_s400_pdf(file):
    items = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
                # Regex specifica per il tuo formato S400
                match = re.search(r'^(\d{5,})\s+(\S+)\s+(.+?)\s+([A-Z]{2})\s+(\d+)\s+([\d.,]+)', line)
                if match:
                    items.append({
                        "Codice": match.group(1),
                        "Cod_Fornitore": match.group(2),
                        "Descrizione": match.group(3).strip(),
                        "Quantità": match.group(5),
                        "Prezzo": clean_stutter(match.group(6)),
                        "Immagine": ""
                    })
    return items

# --- LOGICA DELL'APP ---
st.title("💎 Showroom Pro: Proposta Emozionale")

# Caricamento file S400
uploaded_file = st.file_uploader("Carica il preventivo PDF dell'S400", type="pdf")

if uploaded_file:
    # Salviamo i dati nella sessione per non perderli al refresh
    if 'df' not in st.session_state:
        st.session_state.df = pd.DataFrame(parse_s400_pdf(uploaded_file))

    st.subheader("1. Ve
