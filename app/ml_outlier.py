import statistics


def detectar_outliers(precos):
    """
    Recebe uma lista de preços cotados pro mesmo produto no mesmo mês.
    Retorna lista de tuplas (preco, é_suspeito) usando o método IQR
    (mesmo raciocínio que usamos pra achar o erro real na planilha do depósito).
    """
    if len(precos) < 3:
        return [(p, False) for p in precos]  # poucos dados pra julgar outlier com segurança

    q1, _, q3 = statistics.quantiles(precos, n=4)
    iqr = q3 - q1
    limite_superior = q3 + 1.5 * iqr

    return [(p, p > limite_superior) for p in precos]
