# Gerar código completo como script .py
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import matplotlib.pyplot as plt

# --- 1. Leitura e processamento dos dados climáticos ---
def carregar_clima(paths):
    def try_read(path):
        return pd.read_csv(path, sep=';', encoding='latin1', on_bad_lines='skip')
    df_clima = pd.concat([try_read(p) for p in paths], ignore_index=True)
    df_clima.columns = [c.strip().lower() for c in df_clima.columns]
    df_clima = df_clima.rename(columns={
        'temperatura do ar - bulbo seco, horaria (ï¿½c)': 'temp_media'
    })
    col_chuva = next((col for col in df_clima.columns if "precipita" in col and "mm" in col), None)
    df_clima = df_clima.rename(columns={col_chuva: "chuva_mm"})
    df_clima["chuva_mm"] = pd.to_numeric(df_clima["chuva_mm"].astype(str).str.replace(",", "."), errors="coerce")
    df_clima["temp_media"] = pd.to_numeric(df_clima["temp_media"].astype(str).str.replace(",", "."), errors="coerce")
    df_clima["data"] = pd.to_datetime(df_clima["data"], errors="coerce", dayfirst=True)
    df_clima = df_clima[["data", "chuva_mm", "temp_media"]].dropna()
    df_clima["ano"] = df_clima["data"].dt.year
    return df_clima.groupby("ano").agg({
        "chuva_mm": "sum",
        "temp_media": "mean"
    }).reset_index()

# --- 2. NDVI ---
def carregar_ndvi(path):
    df_ndvi = pd.read_csv(path, sep=";", encoding="latin1")
    df_ndvi = df_ndvi.rename(columns={"Data": "data", "NDVI": "ndvi"})
    df_ndvi["data"] = pd.to_datetime(df_ndvi["data"], errors="coerce", dayfirst=True)
    df_ndvi["ndvi"] = pd.to_numeric(df_ndvi["ndvi"].astype(str).str.replace(",", "."), errors="coerce")
    df_ndvi = df_ndvi[["data", "ndvi"]].dropna()
    df_ndvi = df_ndvi.set_index("data").resample("7D").mean()
    df_ndvi["ndvi"] = df_ndvi["ndvi"].interpolate(method="linear")
    df_ndvi["mes"] = df_ndvi.index.month
    df_ndvi["ano"] = df_ndvi.index.year
    ndvi_agg = df_ndvi.groupby("ano").agg({
        "ndvi": ["mean", "max", "min", "std"]
    })
    ndvi_agg.columns = ['ndvi_mean', 'ndvi_max', 'ndvi_min', 'ndvi_std']
    return ndvi_agg.reset_index()

# --- 3. Produtividade ---
def carregar_produtividade(path):
    df = pd.read_csv(path)
    df = df.rename(columns={"rendimento_kg_ha": "prod_kg_ha"})
    return df[["ano", "prod_kg_ha"]]

# --- 4. Pipeline principal ---
def executar_pipeline(ndvi_path, prod_path, clima_paths):
    clima_agregado = carregar_clima(clima_paths)
    ndvi_agregado = carregar_ndvi(ndvi_path)
    prod = carregar_produtividade(prod_path)
    prod = prod[prod["ano"].isin(ndvi_agregado["ano"])]

    df_final = ndvi_agregado.merge(prod, on="ano")
    df_final = df_final.merge(clima_agregado, on="ano")

    scaler = StandardScaler()
    features = ['ndvi_mean', 'ndvi_max', 'ndvi_min', 'ndvi_std', 'chuva_mm', 'temp_media']
    df_scaled = df_final.copy()
    df_scaled[features] = scaler.fit_transform(df_scaled[features])

    X = df_scaled[features]
    y = df_scaled["prod_kg_ha"]
    X_train, X_test = X[y.index != 2], X[y.index == 2]
    y_train, y_test = y[y.index != 2], y[y.index == 2]

    modelos = {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(random_state=42),
        "XGBoost": XGBRegressor(random_state=42, verbosity=0)
    }

    resultados = []
    for nome, modelo in modelos.items():
        modelo.fit(X_train, y_train)
        y_pred = modelo.predict(X_test)
        resultados.append({
            "Modelo": nome,
            "MAE": mean_absolute_error(y_test, y_pred),
            "RMSE": np.sqrt(mean_squared_error(y_test, y_pred)),
            "R²": r2_score(y_test, y_pred)
        })
        joblib.dump(modelo, f"modelo_{nome}.joblib")

    df_resultados = pd.DataFrame(resultados)
    df_resultados.to_csv("metricas_modelos.csv", index=False)

    plt.figure()
    for nome, modelo in modelos.items():
        y_pred = modelo.predict(X_test)
        plt.scatter(y_test, y_pred, label=nome)
    plt.plot(y_test, y_test, color="black", linestyle="--", label="Ideal")
    plt.xlabel("Produtividade Observada (escala normalizada)")
    plt.ylabel("Produtividade Predita")
    plt.title("Produtividade Observada vs Predita (Ano 2023)")
    plt.legend()
    plt.grid(True)
    plt.savefig("grafico_predicao.png")
    plt.close()

# --- Execução ---
executar_pipeline(
    ndvi_path="files/ndvi_tres_coracoes.csv",
    prod_path="files/producao_cafe_tres_coracoes.csv",
    clima_paths=[
        "files/INMET_SE_MG_A515_VARGINHA_01-01-2021_A_31-12-2021.CSV",
        "files/INMET_SE_MG_A515_VARGINHA_01-01-2022_A_31-12-2022.CSV",
        "files/INMET_SE_MG_A515_VARGINHA_01-01-2023_A_31-12-2023.CSV"
    ]
)
