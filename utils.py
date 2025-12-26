def converter_valor_br(texto):
    if not texto: return 0.0
    texto = str(texto).strip()
    if "." in texto and "," not in texto:
        texto = texto.replace(".", "")
    return float(texto)

