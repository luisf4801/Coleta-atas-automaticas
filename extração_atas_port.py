# -*- coding: utf-8 -*-
"""
Created on Tue Dec  2 11:02:20 2025

@author: Luis
"""

# 1. IMPORTS (Todos aqui)
import requests
import pandas as pd
import fitz # PyMuPDF
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field


# --- Suas classes e funções de limpeza (mantidas) ---
from pydantic import BaseModel, Field
from typing import List, Optional




import matplotlib.pyplot as plt
import seaborn as sns


def extrair_copom_robusto(url):
    response = requests.get(url)
    doc = fitz.open(stream=response.content, filetype="pdf")
    texto_ordenado = ""
    
    # Começamos na página 3 (índice 2)
    for i in range(2, len(doc)):
        pagina = doc[i]
        
        # Divide a página ao meio para lidar com as colunas
        largura = pagina.rect.width
        meio = largura / 2
        altura = pagina.rect.height
        
        # Define as áreas das colunas (esquerda e direita)
        # Rect(x0, y0, x1, y1)
        col_esq = fitz.Rect(0, 0, meio * 1.03, altura)
        col_dir = fitz.Rect(meio * 1.03, 0, largura, altura)
        
        for area in [col_esq, col_dir]:
            # 'dict' extrai metadados, permitindo filtrar pelo tamanho da fonte
            blocks = pagina.get_text("dict", clip=area)["blocks"]
            for b in blocks:
                if "lines" in b:
                    for l in b["lines"]:
                        for s in l["spans"]:
                            # IGNORA SOBRESCRITOS: 
                            # Filtra fontes menores (notas de rodapé/sobrescritos)
                            if s["size"] > 8.5:
                                texto_ordenado += s["text"]
                        texto_ordenado += " "
                texto_ordenado += "\n"

    # Separação dos parágrafos numerados
    paragrafos = []
    # Encontra padrões como "1. ", "2. " no início de blocos
    matches = re.finditer(r'(\d+\.\s.*?)(?=\n\d+\.\s|\Z)', texto_ordenado, re.DOTALL)
    
    for match in matches:
        p = match.group(1)
        # Limpeza final de quebras de linha e espaços duplos
        p_limpo = re.sub(r'\s+', ' ', p).strip()
        paragrafos.append(p_limpo)
        
    doc.close()
    return paragrafos

# URL da API do Banco Central do Brasil para as atas do COPOM
URL_API = "https://www.bcb.gov.br/api/servico/sitebcb/atascopom/ultimas?quantidade=1000&filtro="
# URL base para construir o link completo do PDF
BASE_URL_BCB = "https://www.bcb.gov.br"

 # 1. Faz a requisição HTTP
response = requests.get(URL_API, timeout=10)
response.raise_for_status() # Lança exceção para status codes 4xx/5xx

# 2. Carrega o JSON
data = response.json()
df_urls = pd.DataFrame(data["conteudo"])
df_urls["url_cheia"]="https://www.bcb.gov.br"+df_urls["Url"]


urls_cheios=df_urls["url_cheia"]
reunioes=df_urls["Titulo"]

df_urls["reuniao"]=df_urls['Titulo'].str.extract('(\d+)')

df_urls["reuniao"]=df_urls["reuniao"].apply(int)




####################


class AtaDetalhe(BaseModel):
    # Usamos alias para converter o 'nro_reuniao' do JSON para o padrão Python
    nroReuniao: int = Field(alias="nro_reuniao")
    dataReferencia: str
    titulo: str
    textoAta: Optional[str] = None

    class Config:
        # Permite que você popule a classe usando tanto 'nro_reuniao' quanto 'nroReuniao'
        populate_by_name = True



def limpar_html(html):
    if not html: return ""
    soup = BeautifulSoup(html, "html.parser")
    texto = soup.get_text(separator=" ", strip=True)
    texto = re.sub(r"\s+", " ", texto)
    return texto

# --- Função de processamento individual ---

try:
    url_ata_detalhe = "https://www.bcb.gov.br/api/servico/sitebcb/copom/comunicados?quantidade=1"

    response = requests.get(url_ata_detalhe,  timeout=15)
    response.raise_for_status()
    text = response.json()
    ultima_reuniao=text["conteudo"][0]["nro_reuniao"]

except:
    print("erro ao descobrir a ultima reunião, Input manualmente:")
    ultima_reuniao=input()
    ultima_reuniao=int(ultima_reuniao)



def baixar_ata(nro_reuniao):
    url_ata_detalhe = f"https://www.bcb.gov.br/api/servico/sitebcb/copom/atas_detalhes?nro_reuniao={nro_reuniao}"
    headers = {"Accept": "application/json"}
    
    try:
        response = requests.get(url_ata_detalhe, headers=headers, timeout=15)
        response.raise_for_status()
        
        text = response.json()
        if not text.get("conteudo"):
            return None, nro_reuniao, "Sem conteúdo"

        textoAta = text["conteudo"][0]["textoAta"]
        dataPublicacao = text["conteudo"][0]["dataReferencia"]
        
        textos_limpos = limpar_html(textoAta)
        
        titulo=text["conteudo"][0]["titulo"]
        return {
            "reuniao": nro_reuniao,
            "titulo": titulo,
            "data_publi": dataPublicacao, 
            "texto": textos_limpos
        }, None, None
        
    except Exception as e:
        return None, nro_reuniao, str(e)









# --- Execução Multithreading ---


lista_text = []
lista_erros = []

# Ajuste max_workers entre 10 e 20 para não ser bloqueado pelo servidor
with ThreadPoolExecutor(max_workers=12) as executor:
    # Cria um dicionário mapeando a 'future' ao número da reunião
    future_to_reuniao = {executor.submit(baixar_ata, i): i for i in range(21,ultima_reuniao+1 )}
    
    for future in as_completed(future_to_reuniao):
        reuniao_num = future_to_reuniao[future]
        try:
            resultado, erro_id, msg_erro = future.result()
            
            if resultado:
                if resultado["texto"]=='':
                    url_pdf=df_urls[df_urls["reuniao"]==reuniao_num]["url_cheia"]
                    
                    
                    lista=extrair_copom_robusto(url_pdf.iloc[0])
                    texto = " ".join(lista)
                    resultado["texto"]=texto

                    
                    
                lista_text.append(resultado)

                    
                print(f"comunicado {reuniao_num} processada com sucesso.")
            else:
                print(f"Erro na comunicado {erro_id}: {msg_erro}")
                lista_erros.append(erro_id)
                
        except Exception as e:
            print(f"Falha crítica na thread da comunicado {reuniao_num}: {e}")
            lista_erros.append(reuniao_num)

# --- Salvando os dados ---

df_atas = pd.DataFrame(lista_text)
# Ordenar pelo número da reunião, pois o multithreading entrega em ordem aleatória
df_atas = df_atas.sort_values("reuniao").reset_index(drop=True)

#df_atas.to_excel("C:/Users/Luis/Desktop/tese/dados/comunicado_bc/base_comunicados_api.xlsx", index=False)

print(f"\nProcesso concluído! {len(lista_text)} atas baixadas. {len(lista_erros)} erros.")

df_atas['contagem_palavras'] = df_atas['texto'].fillna('').str.split().str.len()


























# 1. Garantir a contagem e a ordenação
df_atas = df_atas.sort_values('reuniao')

# 2. Configurar o estilo do gráfico
plt.figure(figsize=(12, 6))
sns.set_style("whitegrid")

# 3. Criar o gráfico de linha com pontos
plt.plot(df_atas['reuniao'], df_atas['contagem_palavras'], 
         marker='o', linestyle='-', color='b', markersize=4, linewidth=1.5)

# 4. Customização acadêmica
plt.title('Evolução do Tamanho das Atas/Comunicados do COPOM', fontsize=14)
plt.xlabel('Número da Reunião', fontsize=12)
plt.ylabel('Contagem de Palavras', fontsize=12)

# Opcional: Adicionar uma linha de tendência (Moving Average) para suavizar
df_atas['media_movel'] = df_atas['contagem_palavras'].rolling(window=10).mean()
plt.plot(df_atas['reuniao'], df_atas['media_movel'], color='red', label='Média Móvel (10 reuniões)')

plt.legend()
plt.tight_layout()
plt.show()


df_atas.to_excel("C:/Users/Luis/Desktop/tese/dados/ata_bc/base_atas_port.xlsx")
