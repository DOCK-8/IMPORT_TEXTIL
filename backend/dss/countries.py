"""Normalización de países: nombres en español de PROMPERÚ -> ISO 3166-1 alfa-3, y región."""

from __future__ import annotations

import unicodedata

NOMBRE_ES_A_ISO3 = {
    "alemania": "DEU", "arabia saudita": "SAU", "argentina": "ARG", "aruba": "ABW",
    "australia": "AUS", "austria": "AUT", "bolivia": "BOL", "brasil": "BRA",
    "bulgaria": "BGR", "belgica": "BEL", "canada": "CAN", "chile": "CHL", "china": "CHN",
    "colombia": "COL", "costa rica": "CRI", "dinamarca": "DNK", "ecuador": "ECU",
    "el salvador": "SLV", "emiratos arabes unidos": "ARE", "espana": "ESP",
    "estados unidos": "USA", "estonia": "EST", "finlandia": "FIN", "francia": "FRA",
    "georgia": "GEO", "honduras": "HND", "hong kong": "HKG", "hungria": "HUN", "india": "IND",
    "irlanda": "IRL", "islandia": "ISL", "islas feroe": "FRO", "israel": "ISR", "italia": "ITA",
    "japon": "JPN", "letonia": "LVA", "lituania": "LTU", "luxemburgo": "LUX", "mexico": "MEX",
    "noruega": "NOR", "nueva zelanda": "NZL", "panama": "PAN", "paraguay": "PRY",
    "paises bajos": "NLD", "polonia": "POL", "portugal": "PRT", "puerto rico": "PRI",
    "reino unido": "GBR", "republica checa (chequia)": "CZE", "republica checa": "CZE",
    "chequia": "CZE", "republica de corea (corea del sur)": "KOR", "corea del sur": "KOR",
    "rumania": "ROU", "rusia": "RUS", "singapur": "SGP", "suecia": "SWE", "suiza": "CHE",
    "taipei": "TWN", "taiwan": "TWN", "trinidad y tobago": "TTO", "uruguay": "URY",
    "venezuela": "VEN", "peru": "PER", "grecia": "GRC", "turquia": "TUR", "eslovenia": "SVN",
    "eslovaquia": "SVK", "croacia": "HRV", "chipre": "CYP", "malta": "MLT",
}

ISO3_A_NOMBRE_ES = {
    "DEU": "Alemania", "SAU": "Arabia Saudita", "ARG": "Argentina", "ABW": "Aruba",
    "AUS": "Australia", "AUT": "Austria", "BOL": "Bolivia", "BRA": "Brasil", "BGR": "Bulgaria",
    "BEL": "Bélgica", "CAN": "Canadá", "CHL": "Chile", "CHN": "China", "COL": "Colombia",
    "CRI": "Costa Rica", "DNK": "Dinamarca", "ECU": "Ecuador", "SLV": "El Salvador",
    "ARE": "Emiratos Árabes Unidos", "ESP": "España", "USA": "Estados Unidos", "EST": "Estonia",
    "FIN": "Finlandia", "FRA": "Francia", "GEO": "Georgia", "HND": "Honduras", "HKG": "Hong Kong",
    "HUN": "Hungría", "IND": "India", "IRL": "Irlanda", "ISL": "Islandia", "FRO": "Islas Feroe",
    "ISR": "Israel", "ITA": "Italia", "JPN": "Japón", "LVA": "Letonia", "LTU": "Lituania",
    "LUX": "Luxemburgo", "MEX": "México", "NOR": "Noruega", "NZL": "Nueva Zelanda",
    "PAN": "Panamá", "PRY": "Paraguay", "NLD": "Países Bajos", "POL": "Polonia",
    "PRT": "Portugal", "PRI": "Puerto Rico", "GBR": "Reino Unido", "CZE": "Chequia",
    "KOR": "Corea del Sur", "ROU": "Rumanía", "RUS": "Rusia", "SGP": "Singapur", "SWE": "Suecia",
    "CHE": "Suiza", "TWN": "Taiwán", "TTO": "Trinidad y Tobago", "URY": "Uruguay",
    "VEN": "Venezuela", "PER": "Perú", "GRC": "Grecia", "TUR": "Turquía", "SVN": "Eslovenia",
    "SVK": "Eslovaquia", "HRV": "Croacia", "CYP": "Chipre", "MLT": "Malta", "VNM": "Vietnam",
    "THA": "Tailandia", "MYS": "Malasia", "IDN": "Indonesia", "PHL": "Filipinas",
    "ZAF": "Sudáfrica", "EGY": "Egipto", "MAR": "Marruecos", "QAT": "Catar", "KWT": "Kuwait",
    "UKR": "Ucrania", "KAZ": "Kazajistán", "CUB": "Cuba", "DOM": "República Dominicana",
    "GTM": "Guatemala", "NIC": "Nicaragua", "JAM": "Jamaica", "MAC": "Macao", "MNG": "Mongolia",
    "LKA": "Sri Lanka", "PAK": "Pakistán", "BGD": "Bangladés", "NPL": "Nepal", "SRB": "Serbia",
    "BIH": "Bosnia y Herzegovina", "MKD": "Macedonia del Norte", "ALB": "Albania",
    "BLR": "Bielorrusia", "ARM": "Armenia", "AZE": "Azerbaiyán", "UZB": "Uzbekistán",
    "OMN": "Omán", "BHR": "Baréin", "JOR": "Jordania", "LBN": "Líbano", "TUN": "Túnez",
    "NGA": "Nigeria", "KEN": "Kenia", "MUS": "Mauricio", "BRN": "Brunéi", "KHM": "Camboya",
    "MDA": "Moldavia", "MNE": "Montenegro", "AND": "Andorra", "BHS": "Bahamas",
    "BRB": "Barbados", "BMU": "Bermudas", "CYM": "Islas Caimán", "GRL": "Groenlandia",
}

_REGIONES = {
    "Norteamérica": "USA CAN MEX PRI BMU GRL",
    "Centroamérica y Caribe": "CRI SLV GTM HND NIC PAN CUB DOM JAM TTO ABW BHS BRB CYM",
    "Sudamérica": "ARG BOL BRA CHL COL ECU PRY PER URY VEN",
    "Europa": (
        "DEU AUT BEL BGR HRV CYP CZE DNK EST FIN FRA GRC HUN IRL ITA LVA LTU LUX MLT NLD POL "
        "PRT ROU SVK SVN ESP SWE GBR CHE NOR ISL FRO RUS UKR SRB BIH MKD ALB BLR MDA MNE AND TUR"
    ),
    "Asia": (
        "CHN JPN KOR HKG TWN SGP IND VNM THA MYS IDN PHL MAC MNG LKA PAK BGD NPL KAZ UZB GEO "
        "ARM AZE BRN KHM"
    ),
    "Medio Oriente": "ARE SAU ISR QAT KWT OMN BHR JOR LBN",
    "Oceanía": "AUS NZL",
    "África": "ZAF EGY MAR NGA KEN MUS TUN",
}
ISO3_A_REGION = {iso: reg for reg, codigos in _REGIONES.items() for iso in codigos.split()}


def _clave(nombre: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def iso3_desde_nombre(nombre: str) -> str | None:
    return NOMBRE_ES_A_ISO3.get(_clave(nombre))


def region(iso3: str) -> str:
    return ISO3_A_REGION.get(iso3, "Otras regiones")


def nombre_es(iso3: str, respaldo: str | None = None) -> str:
    return ISO3_A_NOMBRE_ES.get(iso3, respaldo or iso3)
