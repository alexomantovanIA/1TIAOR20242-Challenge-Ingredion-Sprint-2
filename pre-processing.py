import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from datetime import datetime

# --- 1. Carregamento dos dados (mock para SATVeg, IBGE, INMET) ---

# NDVI extraído do SATVeg (perfil temporal do talhão)
df_ndvi = pd.read_csv("ndvi_tres_coracoes.csv", parse_dates=["data"])
# Produtividade histórica (kg/ha) via IBGE/PAM
df_prod = pd.read_csv("produtividade_ibge.csv", parse_dates=["ano"])
# Dados climáticos via INMET (chuva, temperatura média etc.)
df_clima = pd.read_csv("clima_inmet.csv", parse_dates=["data"])


# --- 2. Tratamento da Série Temporal NDVI ---

# Preenchimento de datas ausentes (interpolação linear)
df_ndvi = df_ndvi.set_index("data").resample("7D").mean()  # semanal
df_ndvi["ndvi"] = df_ndvi["ndvi"].interpolate(method="linear")

# Sazonalidade (agrupar por mês para análise)
df_ndvi["mes"] = df_ndvi.index.month
ndvi_mensal = df_ndvi.groupby("mes")["ndvi"].agg(["mean", "std"])

# Identificar NDVI máximo, mínimo, média acumulada no ano
df_ndvi["ano"] = df_ndvi.index.year
ndvi_agregado = df_ndvi.groupby("ano").agg({
    "ndvi": ["mean", "max", "min", "std"]
})
ndvi_agregado.columns = ['ndvi_mean', 'ndvi_max', 'ndvi_min', 'ndvi_std']
ndvi_agregado.reset_index(inplace=True)


# --- 3. Processamento dos dados de produtividade (IBGE) ---

# Agrupamento e limpeza
df_prod = df_prod.rename(columns={"ano": "ano", "produtividade": "prod_kg_ha"})
df_prod = df_prod[df_prod["ano"].isin(ndvi_agregado["ano"])]


# --- 4. Processamento dos dados climáticos (INMET) ---

# Agregação por ano (média anual de temperatura e total de chuva)
df_clima["ano"] = df_clima["data"].dt.year
clima_agregado = df_clima.groupby("ano").agg({
    "chuva_mm": "sum",
    "temp_media": "mean"
}).reset_index()


# --- 5. Junção dos dados para modelagem ---

df_final = ndvi_agregado.merge(df_prod, on="ano")
df_final = df_final.merge(clima_agregado, on="ano")

# Normalização (opcional para modelagem)
scaler = StandardScaler()
colunas_para_normalizar = ['ndvi_mean', 'ndvi_max', 'ndvi_min', 'ndvi_std', 'chuva_mm', 'temp_media']
df_final_scaled = df_final.copy()
df_final_scaled[colunas_para_normalizar] = scaler.fit_transform(df_final_scaled[colunas_para_normalizar])


# Exibição do dataset final pronto para modelagem
print(df_final_scaled.head())
