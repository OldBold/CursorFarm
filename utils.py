def converter_valor_br(texto):
    if not texto: return 0.0
    texto = str(texto).strip()
    if "." in texto and "," not in texto:
        texto = texto.replace(".", "")
    return float(texto)


def formatar_moeda(valor, decimais=2):
    """
    Formata um valor numérico como moeda usando o locale do sistema.
    Retorna string no formato: $ 1.234,56 (ou $ 1,234.56 dependendo do locale)
    """
    import locale
    
    try:
        # Tenta usar o locale padrão do sistema
        locale.setlocale(locale.LC_ALL, '')
    except (locale.Error, ValueError):
        # Se falhar, tenta usar locale padrão UTF-8
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except (locale.Error, ValueError):
            try:
                locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
            except (locale.Error, ValueError):
                # Fallback: usa formato padrão
                locale.setlocale(locale.LC_ALL, 'C')
    
    try:
        # Usa locale.format_string que respeita os separadores do sistema
        formato_num = f"%.{decimais}f"
        valor_formatado = locale.format_string(formato_num, valor, grouping=True)
        return f"$ {valor_formatado}"
    except (AttributeError, ValueError, TypeError):
        # Fallback: usa formatação manual com separador de milhares
        # Python 3.10+ pode não ter locale.format_string, então usamos formatação nativa
        formato = f"{{:,.{decimais}f}}"
        return f"$ {formato.format(valor)}"

