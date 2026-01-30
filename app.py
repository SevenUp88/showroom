import streamlit as st
import pdfplumber
import pandas as pd
from fpdf import FPDF
from duckduckgo_search import DDGS
import re

st.set_page_config(page_title="Consorzio - Showroom", layout="wide")

# --- FUNZIONE PER PULIRE IL TESTO "SDOPPIATO" (GHOSTING) ---
def clean_stutter(text):
    if not text:
        return ""
    # Se il testo ha caratteri doppi strani (es. "33..44") 
    # prendiamo un carattere ogni due per pulire il ghosting
    if ".." in text or ",," in text:
        return "".join(text[::2])
    return text

# --- FUNZIONE RICERCA IMMAGINI ---
def get_image_url(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.images(query, max_results=1))
            if results:
                return results[0]['image']
    except:
        return None
    return None

# --- FUNZIONE PARSING PDF S400 AGGIORNATA ---
def parse_s400_pdf(file):
    items = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')
            for line in lines:
                # Regex migliorata per intercettare i tuoi prezzi sdoppiati
                # Cerchiamo: Codice, Fornitore, Descrizione, UM (NR/MT), Qta, Prezzo (anche sporco)
                match = re.search(r'^(\d{5,})\s+(\S+)\s+(.+?)\s+([A-Z]{2})\s+(\d+)\s+([\d.,]+)', line)
                if match:
                    raw_price = match.group(6)
                    clean_price = clean_stutter(raw_price)
                    
                    items.append({
                        "Codice": match.group(1),
                        "Fornitore": match.group(2),
                        "Descrizione": match.group(3).strip(),
                        "Quantità": match.group(5),
                        "Prezzo": clean_price,
                        "Immagine": ""
                    })
    return items

# --- GENERAZIONE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'PROPOSTA COMMERCIALE SHOWROOM', 0, 1, 'C')
        self.ln(5)

st.title("🚀 Showroom Designer - Consorzio")
st.write("Trasforma il preventivo tecnico in una proposta emozionale.")

uploaded_file = st.file_uploader("Trascina qui il PDF dell'S400", type="pdf")

if uploaded_file:
    data = parse_s400_pdf(uploaded_file)
    if data:
        df = pd.DataFrame(data)
        
        st.subheader("📋 Verifica i dati estratti")
        st.info("Abbiamo pulito gli importi che sembravano duplicati. Controlla se sono corretti.")
        
        # Editor per correggere descrizioni o prezzi
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Trova Foto Prodotti"):
                with st.spinner("Cercando le immagini migliori..."):
                    for i, row in edited_df.iterrows():
                        query = f"{row['Fornitore']} {row['Descrizione']}"
                        img_url = get_image_url(query)
                        if img_url:
                            edited_df.at[i, 'Immagine'] = img_url
                    st.rerun()

        with col2:
            if st.button("🎨 Crea Proposta per Cliente"):
                pdf = PDF()
                
                # SEZIONE ECONOMICA
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, "PROPOSTA ECONOMICA", 0, 1, 'L')
                pdf.ln(5)
                
                # Header Tabella
                pdf.set_font("Arial", 'B', 10)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(25, 10, "Codice", 1, 0, 'C', 1)
                pdf.cell(95, 10, "Descrizione Prodotto", 1, 0, 'C', 1)
                pdf.cell(15, 10, "Qtà", 1, 0, 'C', 1)
                pdf.cell(50, 10, "Prezzo Totale", 1, 1, 'C', 1)

                pdf.set_font("Arial", '', 9)
                for _, row in edited_df.iterrows():
                    pdf.cell(25, 10, str(row['Codice']), 1)
                    pdf.cell(95, 10, str(row['Descrizione'][:50]), 1)
                    pdf.cell(15, 10, str(row['Quantità']), 1, 0, 'C')
                    pdf.cell(50, 10, f"Euro {row['Prezzo']}", 1, 1, 'R')

                # SEZIONE TECNICA
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, "PROPOSTA TECNICA (DETTAGLI)", 0, 1, 'L')
                pdf.set_font("Arial", 'I', 8)
                pdf.cell(0, 10, "*Immagini a scopo puramente illustrativo", 0, 1)

                for _, row in edited_df.iterrows():
                    pdf.ln(10)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 10, f"{row['Descrizione']}", 0, 1)
                    if row['Immagine']:
                        pdf.set_font("Arial", '', 9)
                        pdf.cell(0, 5, f"Link Immagine: {row['Immagine'][:80]}...", 0, 1)
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y())

                pdf_out = pdf.output(dest='S').encode('latin-1', errors='ignore')
                st.download_button("📥 Scarica Proposta Showroom", pdf_out, "proposta_showroom.pdf", "application/pdf")
    else:
        st.warning("Nessun articolo trovato. Il PDF potrebbe avere un formato diverso dal solito.")
