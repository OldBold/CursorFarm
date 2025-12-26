import random


def atualizar_multiplicadores(multiplicadores, variacao_min=-0.05, variacao_max=0.05, limite_min=0.4, limite_max=1.6):
    resultado = {}
    for cultura, multiplicador in multiplicadores.items():
        variacao = random.uniform(variacao_min, variacao_max)
        novo_multiplicador = multiplicador + variacao
        resultado[cultura] = max(limite_min, min(limite_max, novo_multiplicador))
    return resultado

