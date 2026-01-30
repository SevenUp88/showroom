import streamlit as st
import pdfplumber
import pandas as pd
from fpdf import FPDF
import re
import requests
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Consorzio Showroom", layout="wide")

# URL del tuo logo su GitHub
LOGO_URL = "https://raw.githubusercontent.com/SevenUp88/showroom/main/Showroomlogo_trasp.png"

# --- FUNZIONI DI PULIZIA E DOWNLOAD ---
def clean_stutter(text):
    if not text: return ""
    # Correzione prezzi sdoppiati (Ghosting S400)
    return "".join(text[::2]) if ".." in text or ",," in text else text

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
                # Regex per intercettare le righe articoli del tuo preventivo
                match = re.search(r'^(\d{5,})\s+(\S+)\s+(.+?)\s+([A-Z]{2})\s+(\d+)\s+([\d.,]+)', line)
                if match:
                    items.append({
                        "Codice": match.group(1),
                        "Cod_Fornitore": match.group(2),
                        "Descrizione": match.group(3).strip(),
                        "Quantità": match.group(5),
                        "Prezzo": clean_stutter(match.group(6)),
                        "URL_Immagine": "" # Campo vuoto da riempire a mano
                    })
    return items

# --- INTERFACCIA APP ---
st.title("💎 Showroom Pro - Generatore Proposte")
st.write("Carica il preventivo tecnico e aggiungi i link alle immagini per la versione showroom.")

uploaded_file = st.file_uploader("Carica il PDF dell'S400", type="pdf")

if uploaded_file:
    # Inizializza i dati nella sessione se non presenti
    if 'df_showroom' not in st.session_state:
        st.session_state.df_showroom = pd.DataFrame(parse_s400_pdf(uploaded_file))

    st.subheader("1. Modifica i dati e inserisci i link delle immagini")
    st.info("Puoi incollare i link alle immagini dei prodotti direttamente nella colonna 'URL_Immagine'.")
    
    # Tabella modificabile
    edited_df = st.data_editor(st.session_state.df_showroom, use_container_width=True, num_rows="dynamic")
    st.session_state.df_showroom = edited_df

    st.divider()

    if st.button("📝 Genera PDF per Cliente"):
        with st.spinner("Creazione del documento in corso..."):
            pdf = FPDF()
            
            # --- PAGINA 1: ECONOMICA ---
            pdf.add_page()
            
            # Logo
            logo_img = download_image(LOGO_URL)
            if logo_img:
                temp_logo = "temp_logo.png"
                logo_img.save(temp_logo)
                pdf.image(temp_logo, x=10, y=8, w=45)
            
            pdf.set_font("Helvetica", 'B', 18)
            pdf.ln(25)
            pdf.cell(0, 10, "PROPOSTA COMMERCIALE", 0, 1, 'C')
            pdf.ln(10)
            
            # Intestazione Tabella
            pdf.set_font("Helvetica", 'B', 10)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(30, 10, "Codice", 1, 0, 'C', 1)
            pdf.cell(90, 10, "Descrizione", 1, 0, 'C', 1)
            pdf.cell(20, 10, "Qtà", 1, 0, 'C', 1)
            pdf.cell(50, 10, "Importo", 1, 1, 'C', 1)

            # Righe Tabella
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
                
                # Controllo se c'è spazio nella pagina per un nuovo prodotto
                if y_pos > 230:
                    pdf.add_page()
                    y_pos = 20

                # Testo a sinistra
                pdf.set_font("Helvetica", 'B', 11)
                pdf.cell(100, 7, str(row['Descrizione']), 0, 1)
                pdf.set_font("Helvetica", '', 9)
                pdf.cell(100, 5, f"Cod. Fornitore: {row['Cod_Fornitore']}", 0, 1)
                pdf.cell(100, 5, f"Cod. Interno: {row['Codice']}", 0, 1)

                # Immagine a destra (se il link è presente)
                url = row.get('URL_Immagine', '')
                if url and str(url).startswith('http'):
                    p_img = download_image(url)
                    if p_img:
                        try:
                            t_path = f"temp_{i}.jpg"
                            p_img.convert("RGB").save(t_path)
                            pdf.image(t_path, x=135, y=y_pos, h=35)
                        except:
                            pass
                
                pdf.set_y(y_pos + 40)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())

            # --- INVIO PDF ---
            # Correzione dell'errore AttributeError:
            pdf_out = pdf.output() 
            
            st.download_button(
                label="📥 Scarica Preventivo Showroom",
                data=pdf_out,
                file_name="Proposta_Showroom.pdf",
                mime="application/pdf"
            )
