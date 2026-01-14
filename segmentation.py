# Mapeie prefixos de CNAE -> segmento
# Ex.: "5611" cobre restaurantes, "47" cobre varejo etc.
CNAE_SEGMENTOS = {
    "5611": "restaurante",
    "47": "varejo",
    "10": "industria",
    "11": "industria",
    "12": "industria",
    "13": "industria",
    "14": "industria",
    "15": "industria",
    "16": "industria",
    "17": "industria",
    "18": "industria",
    "19": "industria",
    "20": "industria",
    "21": "industria",
    "22": "industria",
    "23": "industria",
    "24": "industria",
    "25": "industria",
    "26": "industria",
    "27": "industria",
    "28": "industria",
    "29": "industria",
    "30": "industria",
    "31": "industria",
    "32": "industria",
    "33": "industria",
    "62": "tecnologia",
    "69": "servicos",
    "70": "servicos",
}

SEGMENTO_TEMPLATE = {
    "restaurante": "template_restaurante",
    "industria": "template_industria",
    "varejo": "template_varejo",
    "servicos": "template_servicos",
    "tecnologia": "template_servicos",
}


def segmento_por_cnae(cnae: str) -> str:
    if not cnae:
        return "servicos"
    c = str(cnae)
    for prefixo, seg in CNAE_SEGMENTOS.items():
        if c.startswith(prefixo):
            return seg
    return "servicos"


def template_por_segmento(segmento: str) -> str:
    return SEGMENTO_TEMPLATE.get(segmento, "template_servicos")
