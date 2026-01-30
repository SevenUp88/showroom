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

    st.subheader("1. Verifica e correggi i dati")
    st.session_state.df = st.data_editor(st.session_state.df, use_container_width=True)

    if st.button("🔍 Cerca Immagini Automaticamente"):
        bar = st.progress(0)
        for i, row in st.session_state.df.iterrows():
            # Ricerca: Prima parola della descrizione (Marca) + Codice Fornitore
            query = f"{row['Descrizione'].split()[0]} {row['Cod_Fornitore']} prodotto idraulica"
            url = get_image_url(query)
            if not url:
                url = get_image_url(f"{row['Descrizione']} scheda tecnica")
            
            st.session_state.df.at[i, 'Immagine'] = url if url else ""
            bar.progress((i + 1) / len(st.session_state.df))
        st.rerun()

    st.divider()

    st.subheader("2. Revisione Gallerie")
    cols = st.columns(3)
    for i, row in st.session_state.df.iterrows():
        with cols[i % 3]:
            st.write(f"**{row['Descrizione'][:35]}**")
            if row['Immagine']:
                st.image(row['Immagine'], use_container_width=True)
            else:
                st.info("Nessuna immagine")
            
            # Possibilità di cambiare il link a mano
            new_url = st.text_input(f"Cambia link immagine (Art {row['Codice']})", value=row['Immagine'], key=f"inp_{i}")
            if new_url != row['Immagine']:
                st.session_state.df.at[i, 'Immagine'] = new_url

    st.divider()

    if st.button("📝 Genera Book Showroom"):
        with st.spinner("Generazione PDF in corso..."):
            pdf = FPDF()
            
            # --- PAGINA 1: ECONOMICA ---
            pdf.add_page()
            
            # Inserimento Logo da GitHub
            logo_img = download_image(LOGO_URL)
            if logo_img:
                temp_logo = "temp_logo.png"
                logo_img.save(temp_logo)
                pdf.image(temp_logo, x=10, y=8, w=40)
            
            pdf.set_font("Helvetica", 'B', 18)
            pdf.set_text_color(40, 40, 40)
            pdf.ln(25)
            pdf.cell(0, 10, "PROPOSTA COMMERCIALE", 0, 1, 'C')
            pdf.ln(10)
            
            # Tabella Economica
            pdf.set_font("Helvetica", 'B', 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(30, 10, "Codice", 1, 0, 'C', 1)
            pdf.cell(90, 10, "Descrizione Prodotto", 1, 0, 'C', 1)
            pdf.cell(20, 10, "Qtà", 1, 0, 'C', 1)
            pdf.cell(50, 10, "Importo", 1, 1, 'C', 1)

            pdf.set_font("Helvetica", '', 9)
            for _, row in st.session_state.df.iterrows():
                pdf.cell(30, 10, str(row['Codice']), 1)
                pdf.cell(90, 10, str(row['Descrizione'][:50]), 1)
                pdf.cell(20, 10, str(row['Quantità']), 1, 0, 'C')
                pdf.cell(50, 10, f"Euro {row['Prezzo']}", 1, 1, 'R')

            # --- SEZIONE TECNICA (DETTAGLI) ---
            pdf.add_page()
            pdf.set_font("Helvetica", 'B', 16)
            pdf.cell(0, 10, "PROPOSTA TECNICA", 0, 1, 'L')
            pdf.set_font("Helvetica", 'I', 8)
            pdf.cell(0, 5, "*Le immagini sono a scopo puramente esemplificativo", 0, 1)

            for i, row in st.session_state.df.iterrows():
                pdf.ln(12)
                y_pos = pdf.get_y()
                
                # Testo descrittivo
                pdf.set_font("Helvetica", 'B', 12)
                pdf.cell(100, 7, row['Descrizione'], 0, 1)
                pdf.set_font("Helvetica", '', 9)
                pdf.cell(100, 5, f"Codice Fornitore: {row['Cod_Fornitore']}", 0, 1)
                pdf.cell(100, 5, f"Codice Interno: {row['Codice']}", 0, 1)

                # Inserimento immagine prodotto
                if row['Immagine']:
                    p_img = download_image(row['Immagine'])
                    if p_img:
                        t_path = f"temp_p_{i}.jpg"
                        p_img.convert("RGB").save(t_path)
                        pdf.image(t_path, x=135, y=y_pos, h=35)
                
                pdf.set_y(y_pos + 40)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())

            pdf_out = pdf.output(dest='S').encode('latin-1', errors='ignore')
            st.download_button("📥 Scarica PDF Emozionale", pdf_out, "Proposta_Showroom.pdf", "application/pdf")
