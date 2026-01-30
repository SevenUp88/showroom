import streamlit as st
import pdfplumber
import pandas as pd
from fpdf import FPDF
import re
import requests
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Consorzio Showroom", layout="wide")

# URL del logo su GitHub
LOGO_URL = "https://raw.githubusercontent.com/SevenUp88/showroom/main/Showroomlogo_trasp.png"

def clean_stutter(text):
    if not text: return ""
    return "".join(text[::2]) if ".." in text or ",," in text else text

def download_image(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
    except:
        return None
    return None

def parse_s400_pdf(file):
    items = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            for line in text.split('\n'):
                # Regex per estrarre i dati dalle righe del preventivo S400
                match = re.search(r'^(\d{5,})\s+(\S+)\s+(.+?)\s+([A-Z]{2})\s+(\d+)\s+([\d.,]+)', line)
                if match:
                    items.append({
                        "Codice": match.group(1),
                        "Cod_Fornitore": match.group(2),
                        "Descrizione": match.group(3).strip(),
                        "Quantità": match.group(5),
                        "Prezzo": clean_stutter(match.group(6)),
                        "URL_Immagine": ""
                    })
    return items

st.title("💎 Showroom Pro - Generatore Proposte")
st.write("Carica il preventivo tecnico e aggiungi i link delle immagini.")

uploaded_file = st.file_uploader("Carica il PDF dell'S400", type="pdf")

if uploaded_file:
    if 'df_showroom' not in st.session_state:
        st.session_state.df_showroom = pd.DataFrame(parse_s400_pdf(uploaded_file))

    st.subheader("1. Tabella Articoli")
    st.info("Incolla i link delle immagini nella colonna 'URL_Immagine'.")
    
    edited_df = st.data_editor(st.session_state.df_showroom, use_container_width=True, num_rows="dynamic")
    st.session_state.df_showroom = edited_df

    st.divider()

    if st.button("📝 Genera Anteprima e Documento"):
        pdf = FPDF()
        
        # --- PAGINA 1: ECONOMICA ---
        pdf.add_page()
        
        # Gestione Logo
        logo_img = download_image(LOGO_URL)
        if logo_img:
            temp_logo = BytesIO()
            logo_img.save(temp_logo, format="PNG")
            pdf.image(temp_logo, x=10, y=8, w=45)
        
        pdf.set_font("Helvetica", 'B', 18)
        pdf.ln(25)
        pdf.cell(0, 10, "PROPOSTA COMMERCIALE", 0, 1, 'C')
        pdf.ln(10)
        
        # Header Tabella
        pdf.set_font("Helvetica", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(30, 10, "Codice", 1, 0, 'C', 1)
        pdf.cell(90, 10, "Descrizione", 1, 0, 'C', 1)
        pdf.cell(20, 10, "Qtà", 1, 0, 'C', 1)
        pdf.cell(50, 10, "Importo", 1, 1, 'C', 1)

        pdf.set_font("Helvetica", '', 9)
        for _, row in edited_df.iterrows():
            pdf.cell(30, 10, str(row['Codice']), 1)
            pdf.cell(90, 10, str(row['Descrizione'][:50]), 1)
            pdf.cell(20, 10, str(row['Quantità']), 1, 0, 'C')
            pdf.cell(50, 10, f"Euro {row['Prezzo']}", 1, 1, 'R')

        # --- PAGINA 2: TECNICA ---
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(0, 10, "DETTAGLIO PRODOTTI", 0, 1, 'L')
        pdf.set_font("Helvetica", 'I', 8)
        pdf.cell(0, 5, "*Immagini a scopo puramente illustrativo", 0, 1)

        for i, row in edited_df.iterrows():
            pdf.ln(10)
            y_pos = pdf.get_y()
            
            if y_pos > 230:
                pdf.add_page()
                y_pos = 20

            pdf.set_font("Helvetica", 'B', 11)
            pdf.cell(100, 7, str(row['Descrizione']), 0, 1)
            pdf.set_font("Helvetica", '', 9)
            pdf.cell(100, 5, f"Cod. Fornitore: {row['Cod_Fornitore']}", 0, 1)
            pdf.cell(100, 5, f"Cod. Interno: {row['Codice']}", 0, 1)

            url = str(row.get('URL_Immagine', ''))
            if url.startswith('http'):
                p_img = download_image(url)
                if p_img:
                    try:
                        temp_p = BytesIO()
                        p_img.convert("RGB").save(temp_p, format="JPEG")
                        pdf.image(temp_p, x=135, y=y_pos, h=35)
                    except:
                        pass
            
            pdf.set_y(y_pos + 40)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())

        # --- FISSA ERRORE DOWNLOAD ---
        # Convertiamo esplicitamente l'output del PDF in bytes
        try:
            pdf_bytes = bytes(pdf.output())
            
            st.success("✅ PDF generato con successo!")
            st.download_button(
                label="📥 Scarica Preventivo Showroom",
                data=pdf_bytes,
                file_name="Proposta_Showroom.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Errore durante la creazione del file: {e}")
