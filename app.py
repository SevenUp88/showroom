import streamlit as st
import pdfplumber
import pandas as pd
from fpdf import FPDF
from duckduckgo_search import DDGS
import re
import requests
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Consorzio Showroom Pro", layout="wide")

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

# --- PARSER PDF ---
def parse_s400_pdf(file):
    items = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
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
st.title("💎 Showroom Pro: Preventivi Emozionali")
st.sidebar.header("Impostazioni")
logo_file = st.sidebar.file_uploader("Carica Logo Consorzio (PNG/JPG)", type=["png", "jpg"])

uploaded_file = st.file_uploader("Carica il PDF dell'S400", type="pdf")

if uploaded_file:
    if 'df' not in st.session_state:
        st.session_state.df = pd.DataFrame(parse_s400_pdf(uploaded_file))

    df = st.session_state.df

    st.subheader("1. Verifica i dati")
    st.session_state.df = st.data_editor(df, use_container_width=True)

    if st.button("🔍 Cerca Immagini (Codice + Descrizione)"):
        bar = st.progress(0)
        for i, row in st.session_state.df.iterrows():
            # TENTATIVO 1: Codice Fornitore (Più preciso)
            query = f"{row['Descrizione'].split()[0]} {row['Cod_Fornitore']} prodotto"
            url = get_image_url(query)
            # TENTATIVO 2: Se fallisce, usa la Descrizione
            if not url:
                query = f"{row['Descrizione']} prodotto"
                url = get_image_url(query)
            
            st.session_state.df.at[i, 'Immagine'] = url if url else ""
            bar.progress((i + 1) / len(st.session_state.df))
        st.rerun()

    st.divider()

    st.subheader("2. Revisione Immagini")
    st.write("Se l'immagine non è corretta, incolla un nuovo link nel campo sotto la foto.")
    
    cols = st.columns(3)
    for i, row in st.session_state.df.iterrows():
        with cols[i % 3]:
            st.write(f"**{row['Descrizione'][:30]}...**")
            if row['Immagine']:
                st.image(row['Immagine'], use_container_width=True)
            else:
                st.warning("Nessuna immagine trovata")
            
            # Campo per cambiare il link manualmente
            new_url = st.text_input(f"Link per art. {row['Codice']}", value=row['Immagine'], key=f"img_{i}")
            if new_url != row['Immagine']:
                st.session_state.df.at[i, 'Immagine'] = new_url

    st.divider()

    if st.button("📝 Genera Proposta Finale"):
        pdf = FPDF()
        
        # --- PAGINA 1: ECONOMICA ---
        pdf.add_page()
        if logo_file:
            pdf.image(logo_file, 10, 8, 33)
        
        pdf.set_font("Arial", 'B', 16)
        pdf.ln(20)
        pdf.cell(0, 10, "PROPOSTA ECONOMICA", 0, 1, 'C')
        pdf.ln(10)
        
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(30, 10, "Codice", 1, 0, 'C', 1)
        pdf.cell(90, 10, "Descrizione", 1, 0, 'C', 1)
        pdf.cell(20, 10, "Qtà", 1, 0, 'C', 1)
        pdf.cell(50, 10, "Totale", 1, 1, 'C', 1)

        pdf.set_font("Arial", '', 9)
        for _, row in st.session_state.df.iterrows():
            pdf.cell(30, 10, str(row['Codice']), 1)
            pdf.cell(90, 10, str(row['Descrizione'][:45]), 1)
            pdf.cell(20, 10, str(row['Quantità']), 1, 0, 'C')
            pdf.cell(50, 10, f"Euro {row['Prezzo']}", 1, 1, 'R')

        # --- SEZIONE TECNICA ---
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "SCHEDE TECNICHE PRODOTTI", 0, 1, 'L')
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 5, "*Immagini esemplificative", 0, 1)

        for _, row in st.session_state.df.iterrows():
            pdf.ln(10)
            y_start = pdf.get_y()
            
            # Testo a sinistra
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(100, 7, row['Descrizione'], 0, 1)
            pdf.set_font("Arial", '', 9)
            pdf.cell(100, 5, f"Cod. Fornitore: {row['Cod_Fornitore']}", 0, 1)
            pdf.cell(100, 5, f"Cod. Interno: {row['Codice']}", 0, 1)
            
            # Immagine a destra
            if row['Immagine']:
                try:
                    res = requests.get(row['Immagine'], timeout=5)
                    img = Image.open(BytesIO(res.content))
                    img_path = f"temp_{row['Codice']}.jpg"
                    img.convert("RGB").save(img_path)
                    pdf.image(img_path, x=130, y=y_start, h=30)
                except:
                    pdf.set_xy(130, y_start)
                    pdf.set_font("Arial", 'I', 7)
                    pdf.cell(50, 10, "[Immagine non disponibile]", 0)

            pdf.set_y(y_start + 35)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())

        pdf_bytes = pdf.output(dest='S').encode('latin-1', errors='ignore')
        st.download_button("📥 Scarica Book Showroom PDF", pdf_bytes, "Proposta_Showroom.pdf")
