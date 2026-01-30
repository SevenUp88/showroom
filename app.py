import streamlit as st
import pdfplumber
import pandas as pd
from fpdf import FPDF
from duckduckgo_search import DDGS
import re

st.set_page_config(page_title="Consorzio - Visualizzatore Preventivi", layout="wide")

# --- FUNZIONE RICERCA IMMAGINI (GRATUITA) ---
def get_image_url(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=1))
            if results:
                return results[0]['image']
    except:
        return None
    return None

# --- FUNZIONE PARSING PDF S400 ---
def parse_s400_pdf(file):
    items = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            for line in lines:
                # Esempio riga: 702353 404891 MULTI U.EST.P/CAL... NR 1 3.445,00
                # Cerchiamo righe che iniziano con un codice numerico (es. 6-7 cifre)
                match = re.match(r'^(\d{5,})\s+(\S+)\s+(.+?)\s+([A-Z]{2})\s+(\d+)\s+([\d.,]+)', line)
                if match:
                    items.append({
                        "Codice": match.group(1),
                        "Fornitore": match.group(2),
                        "Descrizione": match.group(3),
                        "Quantità": match.group(5),
                        "Prezzo": match.group(6),
                        "Immagine": "" # Placeholder
                    })
    return items

# --- GENERAZIONE PDF FINALE ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'PROPOSTA COMMERCIALE - CONSORZIO IDRAULICI', 0, 1, 'C')
        self.ln(5)

st.title("🚀 Trasformatore Preventivi S400")
st.write("Carica il PDF grezzo e ottieni una proposta elegante con foto.")

uploaded_file = st.file_uploader("Scegli il preventivo PDF dell'S400", type="pdf")

if uploaded_file:
    with st.spinner('Analisi del preventivo in corso...'):
        data = parse_s400_pdf(uploaded_file)
        df = pd.DataFrame(data)

    if not df.empty:
        st.subheader("📦 Articoli Trovati")
        st.write("Puoi modificare le descrizioni o aggiungere link alle immagini se non trovate correttamente.")
        
        # Tentativo di recupero immagini automatico
        if st.button("🔍 Cerca Immagini Automaticamente"):
            progress_bar = st.progress(0)
            for i, row in df.iterrows():
                query = f"{row['Fornitore']} {row['Descrizione']}"
                img_url = get_image_url(query)
                if img_url:
                    df.at[i, 'Immagine'] = img_url
                progress_bar.progress((i + 1) / len(df))
            st.success("Ricerca completata!")

        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

        if st.button("📄 Genera Preventivo Moderno"):
            pdf = PDF()
            
            # SEZIONE 1: PROPOSTA ECONOMICA
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "PROPOSTA ECONOMICA", 0, 1, 'L')
            pdf.set_font("Arial", '', 10)
            pdf.ln(10)
            
            # Intestazione Tabella
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(30, 10, "Codice", 1, 0, 'C', 1)
            pdf.cell(90, 10, "Descrizione", 1, 0, 'C', 1)
            pdf.cell(20, 10, "Qtà", 1, 0, 'C', 1)
            pdf.cell(50, 10, "Prezzo Netto", 1, 1, 'C', 1)

            for i, row in edited_df.iterrows():
                pdf.cell(30, 10, str(row['Codice']), 1)
                pdf.cell(90, 10, str(row['Descrizione'][:45]), 1)
                pdf.cell(20, 10, str(row['Quantità']), 1, 0, 'C')
                pdf.cell(50, 10, f"Euro {row['Prezzo']}", 1, 1, 'R')

            # SEZIONE 2: PROPOSTA TECNICA
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "PROPOSTA TECNICA", 0, 1, 'L')
            pdf.ln(5)
            pdf.set_font("Arial", 'I', 8)
            pdf.cell(0, 10, "*Le immagini sono fornite a scopo puramente esemplificativo", 0, 1)
            pdf.ln(5)

            for i, row in edited_df.iterrows():
                if row['Immagine']:
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, f"Art: {row['Descrizione']}", 0, 1)
                    # Nota: In una versione cloud reale, l'immagine andrebbe scaricata localmente prima di inserirla nel PDF
                    pdf.set_font("Arial", '', 10)
                    pdf.cell(0, 5, f"Codice Fornitore: {row['Fornitore']}", 0, 1)
                    pdf.ln(40) # Spazio per l'immagine (da implementare download)
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                    pdf.ln(5)

            pdf_output = pdf.output(dest='S').encode('latin-1', errors='ignore')
            st.download_button(label="📥 Scarica Preventivo PDF", 
                               data=pdf_output, 
                               file_name="preventivo_consorzio.pdf", 
                               mime="application/pdf")
    else:
        st.error("Non sono riuscito a leggere i dati dal PDF. Controlla il formato.")
