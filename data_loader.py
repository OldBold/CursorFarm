import csv
import os


def _resolve_path(nome_arquivo):
    if os.path.exists(nome_arquivo):
        return nome_arquivo
    caminho_cwd = os.path.join(os.getcwd(), nome_arquivo)
    if os.path.exists(caminho_cwd):
        return caminho_cwd
    caminho_file = os.path.join(os.path.dirname(__file__), nome_arquivo)
    if os.path.exists(caminho_file):
        return caminho_file
    return None


def ler_csv_generico(nome_arquivo):
    dados = []
    caminho_resolvido = _resolve_path(nome_arquivo)
    if caminho_resolvido is None:
        return dados
    try:
        with open(caminho_resolvido, newline='', encoding='utf-8-sig') as csvfile:
            primeira = csvfile.readline()
            sep = ';' if ';' in primeira else ','
            csvfile.seek(0)
            leitor = csv.DictReader(csvfile, delimiter=sep)
            for linha in leitor:
                linha_limpa = {k.strip(): v for k, v in linha.items() if k is not None}
                dados.append(linha_limpa)
    except Exception as e:
        try:
            with open(caminho_resolvido, newline='', encoding='latin-1') as csvfile:
                primeira = csvfile.readline()
                sep = ';' if ';' in primeira else ','
                csvfile.seek(0)
                leitor = csv.DictReader(csvfile, delimiter=sep)
                for linha in leitor:
                    linha_limpa = {k.strip(): v for k, v in linha.items() if k is not None}
                    dados.append(linha_limpa)
        except: pass
    return dados

