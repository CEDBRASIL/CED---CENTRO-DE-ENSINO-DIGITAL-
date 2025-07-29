# Funções utilitárias para o sistema.


def formatar_numero_whatsapp(numero: str) -> str:
    """Formata o telefone para envio via WhatsApp.

    - Garante o prefixo brasileiro ``55``.
    - Remove quaisquer caracteres não numéricos.
    - Remove o nono dígito logo após o DDD, caso presente.
    """

    # Extrai apenas os dígitos informados
    digitos = "".join(filter(str.isdigit, numero or ""))

    if not digitos:
        return ""

    if digitos.startswith("55"):
        # Remove prefixo Brasil caso já esteja presente
        digitos = digitos[2:]
        # Remove o nono dígito após o DDD, se houver
        if len(digitos) >= 10 and digitos[2] == "9":
            digitos = digitos[:2] + digitos[3:]
    else:
        # Números locais devem conter o nono dígito
        if len(digitos) == 10:
            digitos = digitos[:2] + "9" + digitos[2:]

    return "55" + digitos


def parse_valor(valor) -> float | None:
    """Converte valores recebidos como string ou numérico em ``float``.

    Aceita formatos com vírgula ou ponto como separador decimal e ignora o
    símbolo ``R$`` e espaços. Retorna ``None`` se a conversão falhar.
    """

    if valor is None:
        return None

    if isinstance(valor, (int, float)):
        try:
            return float(valor)
        except ValueError:
            return None

    if isinstance(valor, str):
        valor = valor.strip().replace("R$", "").replace(" ", "")
        if "," in valor and "." in valor:
            valor = valor.replace(".", "").replace(",", ".")
        else:
            valor = valor.replace(",", ".")
        try:
            return float(valor)
        except ValueError:
            return None

    try:
        return float(valor)
    except Exception:
        return None


def parse_valor_centavos(valor) -> float | None:
    """Converte valores expressos em centavos para ``float`` em reais."""

    if valor is None:
        return None

    if isinstance(valor, int):
        return valor / 100

    if isinstance(valor, str) and valor.isdigit():
        try:
            return int(valor) / 100
        except ValueError:
            return None

    valor_float = parse_valor(valor)
    if valor_float is None:
        return None
    return valor_float / 100 if valor_float.is_integer() else valor_float
