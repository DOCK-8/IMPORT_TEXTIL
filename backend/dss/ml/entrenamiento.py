"""Entrenamiento y evaluación del predictor de abandono (RF-04).

Protocolo (artículo III.J): la evaluación respeta el orden temporal. En el protocolo estricto
solo se entrena con cortes cuya ventana de etiqueta (24 meses) ya terminó en la fecha del corte
de prueba, de modo que el modelo no usa información posterior a esa fecha. El protocolo
relajado (todas las fechas de corte anteriores) se reporta solo como contraste.

Hipótesis: los ensambles no lineales (Random Forest, XGBoost) superan a los métodos estáticos
(regla de actividad) y lineales (regresión logística).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score, brier_score_loss,
    f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from dss import config
from dss.config import MESES_ABANDONO
from dss.ml.dataset import VARIABLES, construir, cortes_etiquetables, preparar

log = logging.getLogger(__name__)
SEMILLA = 42
MIN_POR_CLASE = 30
N_BOOTSTRAP = 2000


class ReglaEstatica:
    """Línea base 'hoja de cálculo': riesgo = pocos meses activos en el último año."""

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        meses = X[:, VARIABLES.index("meses_activos_12")]
        p = 1 - (np.nan_to_num(meses, nan=0) - 1) / 11
        p = np.clip(p, 0, 1)
        return np.column_stack([1 - p, p])


def modelos(y_train: np.ndarray) -> dict:
    pos = max(int(y_train.sum()), 1)
    return {
        "regla_estatica": ReglaEstatica(),
        "regresion_logistica": make_pipeline(
            SimpleImputer(strategy="median"), StandardScaler(),
            LogisticRegression(class_weight="balanced", max_iter=2000)),
        "random_forest": make_pipeline(
            SimpleImputer(strategy="median"),
            RandomForestClassifier(n_estimators=500, min_samples_leaf=5, class_weight="balanced_subsample",
                                   random_state=SEMILLA, n_jobs=-1)),
        "xgboost": XGBClassifier(
            n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
            eval_metric="logloss", scale_pos_weight=(len(y_train) - pos) / pos, random_state=SEMILLA,
            n_jobs=-1),
    }


def _umbral_oof(modelo, X, y, grupos) -> float:
    """Umbral que maximiza F1 con predicciones fuera de pliegue en entrenamiento (sin mirar la prueba)."""
    if isinstance(modelo, ReglaEstatica):
        p = modelo.predict_proba(X)[:, 1]
    else:
        p = cross_val_predict(clone(modelo), X, y, groups=grupos, cv=GroupKFold(5), method="predict_proba")[:, 1]
    candidatos = np.unique(np.round(p, 3))
    return float(max(candidatos, key=lambda t: f1_score(y, p >= t, zero_division=0)))


def _metricas(y, p, umbral) -> dict:
    pred = p >= umbral
    return {
        "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
        "accuracy": accuracy_score(y, pred), "balanced_accuracy": balanced_accuracy_score(y, pred),
        "f1": f1_score(y, pred, zero_division=0), "precision": precision_score(y, pred, zero_division=0),
        "recall": recall_score(y, pred, zero_division=0), "brier": brier_score_loss(y, p),
        "umbral": umbral,
    }


def _bootstrap_auc(y, pa, pb, rng) -> dict:
    n, difs = len(y), []
    for _ in range(N_BOOTSTRAP):
        i = rng.integers(0, n, n)
        if y[i].min() == y[i].max():
            continue
        difs.append(roc_auc_score(y[i], pa[i]) - roc_auc_score(y[i], pb[i]))
    difs = np.array(difs)
    return {"dif_auc": float(roc_auc_score(y, pa) - roc_auc_score(y, pb)),
            "ic95": [float(np.percentile(difs, 2.5)), float(np.percentile(difs, 97.5))],
            "p_unilateral": float((difs <= 0).mean())}


def _mcnemar(y, pred_a, pred_b) -> dict:
    a_ok, b_ok = pred_a == y, pred_b == y
    solo_a, solo_b = int((a_ok & ~b_ok).sum()), int((~a_ok & b_ok).sum())
    p = binomtest(solo_a, solo_a + solo_b, 0.5).pvalue if solo_a + solo_b else 1.0
    return {"solo_a_acierta": solo_a, "solo_b_acierta": solo_b, "p_valor": float(p)}


def _verificar(df: pd.DataFrame, nombre: str) -> str | None:
    conteo = df["abandono"].value_counts()
    if len(df) == 0 or conteo.get(0, 0) < MIN_POR_CLASE or conteo.get(1, 0) < MIN_POR_CLASE:
        return f"{nombre}: clases insuficientes {conteo.to_dict()} (mínimo {MIN_POR_CLASE} por clase)"
    return None


def evaluar(e: pd.DataFrame, cortes: list[pd.Period], imp_mundo, prueba: pd.Period, entrenamiento: list[pd.Period]) -> dict:
    tr = pd.concat([construir(e, c, imp_mundo) for c in entrenamiento], ignore_index=True)
    te = construir(e, prueba, imp_mundo)
    problemas = [m for m in (_verificar(tr, "entrenamiento"), _verificar(te, "prueba")) if m]
    resultado = {
        "cortes_entrenamiento": [str(c) for c in entrenamiento], "corte_prueba": str(prueba),
        "n_entrenamiento": len(tr), "n_prueba": len(te),
        "tasa_abandono_entrenamiento": float(tr["abandono"].mean()) if len(tr) else None,
        "tasa_abandono_prueba": float(te["abandono"].mean()) if len(te) else None,
    }
    if problemas:
        resultado["omitido"] = problemas
        return resultado

    Xtr, ytr, Xte, yte = tr[VARIABLES].to_numpy(float), tr["abandono"].to_numpy(), te[VARIABLES].to_numpy(float), te["abandono"].to_numpy()
    probs, preds, metricas, ajustados = {}, {}, {}, {}
    for nombre, modelo in modelos(ytr).items():
        umbral = _umbral_oof(modelo, Xtr, ytr, tr["ruc"].to_numpy())
        ajustado = modelo.fit(Xtr, ytr)
        probs[nombre] = ajustado.predict_proba(Xte)[:, 1]
        preds[nombre] = probs[nombre] >= umbral
        metricas[nombre] = {k: round(float(v), 4) for k, v in _metricas(yte, probs[nombre], umbral).items()}
        ajustados[nombre] = ajustado

    mejor = max(["random_forest", "xgboost"], key=lambda m: metricas[m]["roc_auc"])
    rng = np.random.default_rng(SEMILLA)
    contrastes = {
        f"{mejor}_vs_{base}": {
            "auc": _bootstrap_auc(yte, probs[mejor], probs[base], rng),
            "mcnemar": _mcnemar(yte, preds[mejor], preds[base]),
        }
        for base in ("regresion_logistica", "regla_estatica")
    }
    perm = permutation_importance(ajustados[mejor], Xte, yte, scoring="roc_auc", n_repeats=20, random_state=SEMILLA)
    resultado.update({
        "metricas": metricas, "mejor_modelo": mejor, "contrastes": contrastes,
        "importancia_permutacion": dict(sorted(
            {v: round(float(m), 4) for v, m in zip(VARIABLES, perm.importances_mean)}.items(),
            key=lambda kv: -kv[1])),
    })
    return resultado


def entrenar(exportaciones: pd.DataFrame, importaciones_mundo: pd.DataFrame, sa6: str) -> dict:
    e = preparar(exportaciones[exportaciones["sa6"] == sa6])
    primero = pd.Period(f"{config.ANIO_INICIO}-01", "M")
    ultimo = pd.Period(f"{config.ANIO_FIN}-12", "M")
    cortes = cortes_etiquetables(ultimo, primero)
    reporte = {
        "sa6": sa6, "entrenado_en": datetime.now().isoformat(timespec="seconds"),
        "horizonte_meses": MESES_ABANDONO, "variables": VARIABLES,
        "cortes_etiquetables": [str(c) for c in cortes],
    }
    if len(cortes) < 2:
        reporte["omitido"] = "El periodo no permite separar cortes de entrenamiento y prueba."
        return reporte

    prueba = cortes[-1]
    estrictos = [c for c in cortes if c + MESES_ABANDONO <= prueba]
    reporte["protocolo_estricto"] = (
        evaluar(e, cortes, importaciones_mundo, prueba, estrictos) if estrictos
        else {"omitido": ["No hay cortes cuya etiqueta esté cerrada antes del corte de prueba."]}
    )
    reporte["protocolo_relajado"] = evaluar(e, cortes, importaciones_mundo, prueba, cortes[:-1])

    principal = reporte["protocolo_estricto"] if "metricas" in reporte["protocolo_estricto"] else reporte["protocolo_relajado"]
    if "metricas" not in principal:
        reporte["omitido"] = "Ningún protocolo reunió clases suficientes; no se publica predicción."
        return reporte

    # Modelo de producción: el mejor ensamble reentrenado con todos los cortes etiquetados
    mejor = principal["mejor_modelo"]
    todo = pd.concat([construir(e, c, importaciones_mundo) for c in cortes], ignore_index=True)
    modelo = modelos(todo["abandono"].to_numpy())[mejor].fit(todo[VARIABLES].to_numpy(float), todo["abandono"].to_numpy())
    config.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": modelo, "variables": VARIABLES, "nombre": mejor},
                config.ARTIFACTS_DIR / f"modelo_abandono_{sa6}.joblib")

    actuales = construir(e, ultimo, importaciones_mundo, etiquetar=False)
    actuales["p_abandono"] = modelo.predict_proba(actuales[VARIABLES].to_numpy(float))[:, 1]
    reporte["modelo_produccion"] = {"nombre": mejor, "n_entrenamiento": len(todo), "corte_prediccion": str(ultimo)}
    reporte["predicciones_relaciones"] = actuales[["ruc", "iso3", "fob_12", "p_abandono"]].to_dict("records")

    (config.ARTIFACTS_DIR / f"metricas_modelo_{sa6}.json").write_text(
        json.dumps({k: v for k, v in reporte.items() if k != "predicciones_relaciones"}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    return reporte


def riesgo_por_mercado(predicciones: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(predicciones)
    if df.empty:
        return df
    peso = df["fob_12"].clip(lower=1)
    agg = df.assign(pp=df["p_abandono"] * peso, w=peso).groupby("iso3").agg(
        pp=("pp", "sum"), w=("w", "sum"), n_relaciones=("ruc", "nunique"))
    agg["probabilidad"] = agg["pp"] / agg["w"]
    agg["clase"] = pd.cut(agg["probabilidad"], [-0.01, 0.33, 0.66, 1.01], labels=["bajo", "medio", "alto"]).astype(str)
    return agg.reset_index()[["iso3", "probabilidad", "clase", "n_relaciones"]]
