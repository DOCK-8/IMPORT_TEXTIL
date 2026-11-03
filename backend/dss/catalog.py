"""Catálogo de prendas y matriz de homologación arancelaria (RF-02).

Transcribe la tabla 4 del SRS: subpartida nacional SUNAT (10 dígitos) -> subpartida
del Sistema Armonizado (6 dígitos) usada por UN Comtrade.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Prenda:
    codigo: str
    nombre: str


@dataclass(frozen=True)
class Subpartida:
    sa6: str
    prenda: str
    descripcion: str
    nacionales: tuple[str, ...]
    nota_agregacion: str = ""


PRENDAS = [
    Prenda("chompas", "Chompas y suéteres"),
    Prenda("chalinas", "Chalinas y ponchos"),
    Prenda("gorros", "Gorros y accesorios"),
    Prenda("guantes", "Guantes y mitones"),
]

SUBPARTIDAS = [
    Subpartida("611019", "chompas", "Chompas/chalecos de punto de pelo fino (alpaca/llama)",
               ("6110191010", "6110191090", "6110190010", "6110190090"),
               "SA 6110.19 agrupa pelo fino distinto de cachemira (alpaca, llama, vicuña, camello, mohair): los datos internacionales no son exclusivos de alpaca."),
    Subpartida("611011", "chompas", "Chompas/chalecos de punto de lana o pelo de ovino",
               ("6110110000",),
               "Incluye toda prenda de punto de lana; no distingue lana peruana de otras procedencias."),
    Subpartida("611710", "chalinas", "Chales, bufandas, chalinas y artículos similares de punto",
               ("6117100000",),
               "SA 6117.10 incluye chales y bufandas de punto de cualquier materia textil."),
    Subpartida("621420", "chalinas", "Chales, bufandas, mantillas y similares de lana o pelo fino",
               ("6214200000",),
               "SA 6214.20 agrupa lana y pelo fino sin distinguir alpaca."),
    Subpartida("650500", "gorros", "Sombreros, gorros y chullos de punto",
               ("6505000010", "6505000090"),
               "SA 6505.00 incluye sombreros y tocados de punto de cualquier materia."),
    Subpartida("611691", "guantes", "Guantes, mitones y manoplas de punto de lana o pelo fino",
               ("6116910000",)),
    Subpartida("611699", "guantes", "Guantes, mitones y manoplas de punto de las demás materias",
               ("6116990000",),
               "SA 6116.99 corresponde a otras materias; su relación con alpaca/lana debe verificarse por composición."),
]

_POR_SA6 = {s.sa6: s for s in SUBPARTIDAS}
_NACIONAL_A_SA6 = {n: s.sa6 for s in SUBPARTIDAS for n in s.nacionales}


def homologar(subpartida_nacional: str) -> str | None:
    """Convierte una subpartida nacional (10 dígitos) a SA de 6 dígitos.

    Si el código no está en la matriz pero pertenece a un capítulo del catálogo,
    se usa el prefijo de 6 dígitos (el SA es común a todos los países hasta ese nivel).
    """
    codigo = "".join(ch for ch in str(subpartida_nacional) if ch.isdigit())
    if codigo in _NACIONAL_A_SA6:
        return _NACIONAL_A_SA6[codigo]
    if len(codigo) >= 6 and codigo[:6] in _POR_SA6:
        return codigo[:6]
    return None


def subpartida(sa6: str) -> Subpartida:
    return _POR_SA6[sa6]


def sa6_de_prenda(prenda: str) -> list[str]:
    return [s.sa6 for s in SUBPARTIDAS if s.prenda == prenda]
