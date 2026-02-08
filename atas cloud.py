# -*- coding: utf-8 -*-
"""
Created on Sun Feb  8 17:41:59 2026

@author: Luis
"""

from wordcloud import WordCloud
import matplotlib.pyplot as plt
import nltk
from nltk.corpus import stopwords
import pandas as pd

df_atas_read=pd.read_excel("C:/Users/Luis/Desktop/tese/dados/ata_bc/base_atas_port.xlsx")


df_atas_read = df_atas_read.iloc[:, 1:] # Descarta a coluna de índice

nltk.download('stopwords')
stop_words = stopwords.words('portuguese')
# Adiciona palavras comuns em atas que não trazem significado analítico
stop_words.extend(['copom', 'comitê', 'reunião', 'sobre', 'ainda', 'pode', 'bem', 'nesta'])

def gerar_nuvem(df, filtro_reuniao, titulo):
    # Filtra os dados e junta todo o texto
    texto = " ".join(df[filtro_reuniao]['texto'].fillna(''))
    
    # Gera a nuvem
    wordcloud = WordCloud(
        width=800, height=400,
        background_color='white',
        stopwords=stop_words,
        colormap='viridis',
        max_words=100
    ).generate(texto)
    
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.title(titulo, fontsize=15)
    plt.axis('off')
    plt.show()

# Exemplo de comparação para o post:
# 1. Nuvem da época da Reunião 200 (Ilan Goldfajn)
gerar_nuvem(df_atas_read, (df_atas_read['reuniao'] >= 200) & (df_atas_read['reuniao'] <= 210), "Nuvem de Palavras: Ciclo Ata 200")

# 2. Nuvem das reuniões mais recentes (Roberto Campos Neto)
gerar_nuvem(df_atas_read, df_atas_read['reuniao'] > 260, "Nuvem de Palavras: Ciclo Atual")