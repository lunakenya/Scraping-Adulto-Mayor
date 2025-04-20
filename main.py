import os
import re
import pytesseract
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
from PyPDF2 import PdfReader
from fpdf import FPDF

# ---------------------- CONFIGURACIÓN ----------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

DATA_IMG_DIR = "data"
DATA_PDF_DIR = "data global"
GRAFICOS_DIR = "graficos"
OUTPUT_PDF = "outputs/informe_final.pdf"
OUTPUT_XLSX = "outputs/resumen_resultados.xlsx"
PORTADA_IMG = "resources/imagen_portada.png"

os.makedirs(GRAFICOS_DIR, exist_ok=True)
os.makedirs("outputs", exist_ok=True)

# ---------------------- FUNCIONES ----------------------
def extraer_votos_por_provincia():
    datos = {}
    for archivo in os.listdir(DATA_PDF_DIR):
        if archivo.endswith(".pdf"):
            provincia = archivo.replace("elecciones-generales-2025-", "").replace(".pdf", "").strip()
            path = os.path.join(DATA_PDF_DIR, archivo)
            try:
                reader = PdfReader(path)
                texto = reader.pages[1].extract_text()

                luisa = re.search(r"LUISA GONZALEZ\s+([\d.]+)\s+([\d.,]+)\s+%", texto)
                noboa = re.search(r"DANIEL NOBOA AZIN\s+([\d.]+)\s+([\d.,]+)\s+%", texto)

                if luisa and noboa:
                    datos[provincia] = {
                        "Luisa": int(luisa.group(1).replace(",", "")),
                        "Noboa": int(noboa.group(1).replace(",", ""))
                    }
            except Exception as e:
                print(f"⚠️ Error leyendo {archivo}: {e}")
    return datos

def crear_grafico_y_dataframe(datos_voto, adultos):
    resumen = []
    for provincia, votos in datos_voto.items():
        if "2025" in provincia:
            continue
        adultos_mayores = adultos.get(provincia.title(), 0)
        total_votos = votos['Luisa'] + votos['Noboa']
        pct_mayores = adultos_mayores / total_votos * 100 if total_votos else 0
        resumen.append({
            "Provincia": provincia.title(),
            "Votos Luisa": votos['Luisa'],
            "Votos Noboa": votos['Noboa'],
            "Adultos Mayores": adultos_mayores,
            "% Adultos Mayores vs Votos": round(pct_mayores, 2)
        })

    df = pd.DataFrame(resumen)
    df.to_excel(OUTPUT_XLSX, index=False)

    df.plot(x="Provincia", y="% Adultos Mayores vs Votos", kind="bar", legend=False, color="#4CAF50")
    plt.ylabel("% Adultos Mayores / Total de Votos")
    plt.title("Influencia relativa de adultos mayores por provincia")
    plt.tight_layout()
    grafico_path = os.path.join(GRAFICOS_DIR, "influencia_adultos_mayores.png")
    plt.savefig(grafico_path)
    plt.close()
    print(df)
    return grafico_path, df

class PDF(FPDF):
    def header(self):
        if self.page_no() == 1 and os.path.exists(PORTADA_IMG):
            # Imagen pequeña y centrada
            img_width = 70
            page_width = self.w - 2 * self.l_margin
            img_x = (page_width - img_width) / 2 + self.l_margin
            self.image(PORTADA_IMG, x=img_x, y=20, w=img_width)

            self.ln(85)
            self.set_font("Times", "B", 17)
            self.cell(0, 10, "UNIVERSIDAD CENTRAL DEL ECUADOR", ln=True, align="C")
            self.set_font("Times", "B", 16)
            self.cell(0, 10, "FACULTAD DE INGENIERIA Y CIENCIAS APLICADAS", ln=True, align="C")
            self.cell(0, 10, "SISTEMAS DE INFORMACION", ln=True, align="C")
            self.cell(0, 10, "LEGISLACIÓN", ln=True, align="C")
            self.ln(10)
            self.set_font("Times", "", 13)
            self.multi_cell(0, 10, "INFLUENCIA DE LOS ADULTOS MAYORES O IGUAL A 65 AÑOS EN LA SEGUNDA VUELTA - ELECCIONES ECUADOR 2025", align="C")
            self.ln(20)

    def tabla_datos(self, df):
        self.set_font("Times", "B", 10)
        col_widths = [45, 35, 35, 40, 45]
        table_width = sum(col_widths)
        page_width = self.w - 2 * self.l_margin
        x_start = (page_width - table_width) / 2 + self.l_margin
        self.set_x(x_start)

        headers = df.columns.tolist()
        for i in range(len(headers)):
            self.cell(col_widths[i], 10, headers[i], border=1, align="C")
        self.ln()

        self.set_font("Times", "", 10)
        fill = False
        for _, row in df.iterrows():
            self.set_fill_color(230, 230, 230) if fill else self.set_fill_color(255, 255, 255)
            self.set_x(x_start)
            self.cell(col_widths[0], 8, str(row["Provincia"]), border=1, fill=True)
            self.cell(col_widths[1], 8, f'{row["Votos Luisa"]:,}', border=1, align="R", fill=True)
            self.cell(col_widths[2], 8, f'{row["Votos Noboa"]:,}', border=1, align="R", fill=True)
            self.cell(col_widths[3], 8, f'{row["Adultos Mayores"]:,}', border=1, align="R", fill=True)
            self.cell(col_widths[4], 8, f'{row["% Adultos Mayores vs Votos"]:.2f}%', border=1, align="R", fill=True)
            self.ln()
            fill = not fill

    def analisis_texto(self, df):
        max_row = df.loc[df["% Adultos Mayores vs Votos"].idxmax()]
        self.ln(10)
        self.set_font("Times", "B", 12)
        self.cell(0, 10, "Análisis Automático", ln=True)
        self.set_font("Times", "", 11)
        texto = (
            f"La provincia con mayor proporción de adultos mayores en relación al total de votos es {max_row['Provincia']}, "
            f"con un {max_row['% Adultos Mayores vs Votos']:.2f}% del total. "
            f"Esto indica una influencia electoral significativa por parte de este grupo etario."
        )
        self.multi_cell(0, 10, texto)

def generar_pdf(grafico_path, df):
    pdf = PDF()

    # Página 1: Portada automática (se genera en el header)
    pdf.add_page()

    # Página 2: Título principal + gráfico + tabla + análisis
    pdf.add_page()

    # Título centrado en la segunda página
    pdf.set_font("Times", "B", 11)
    pdf.cell(0, 8, "INFLUENCIA RELATIVA DE ADULTOS MAYORES EN LA REELECCIÓN DEL PRESIDENTE DANIEL NOBOA", ln=True, align="C")

    # Espaciado antes de la imagen
    pdf.ln(8)

    # Imagen centrada y más pequeña
    img_width = 130
    page_width = pdf.w - 2 * pdf.l_margin
    img_x = (page_width - img_width) / 2 + pdf.l_margin
    pdf.image(grafico_path, x=img_x, w=img_width)

    # Espaciado
    pdf.ln(10)

    # Tabla y análisis
    pdf.tabla_datos(df)
    pdf.analisis_texto(df)

    # Guardar el archivo PDF
    pdf.output(OUTPUT_PDF)

# ---------------------- FLUJO PRINCIPAL ----------------------
if __name__ == "__main__":
    print("\U0001F4CA Extrayendo datos de votos por provincia desde PDFs...")
    votos = extraer_votos_por_provincia()

    print("\U0001F4C8 Generando gráfico y resumen...")
    grafico, df = crear_grafico_y_dataframe(votos, {
        "Azuay": 92210,
        "Guayas": 437488,
        "Pichincha": 232337,
        "Los Rios": 88121,
        "Manabi": 177979,
        "Santo Domingo Tsachilas": 43063,
    })

    print("\U0001F4DD Generando PDF final...")
    generar_pdf(grafico, df)

    print("\n📅 Proceso finalizado. Revisa 'outputs/informe_final.pdf'")
