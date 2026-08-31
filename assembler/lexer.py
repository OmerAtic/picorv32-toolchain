# ============================================================
# lexer.py - Sozcuksel Analiz (Tokenizer)
# ============================================================
# Assembly kaynak kodunu satirlar halinde okur ve her satiri
# parcalarina ayirir: label, mnemonic, operandlar.
# Yorumlari temizler, bos satirlari eler.
# ============================================================


def tokenize_line(line, line_number):
    """Tek bir assembly satirini token'lara ayirir.

    Ornek giris:  "loop: ADD x1, x2, x3  # toplama islemi"
    Ornek cikti:  {
        "line_num": 5,
        "label": "loop",
        "mnemonic": "ADD",
        "operands": ["x1", "x2", "x3"],
        "original": "loop: ADD x1, x2, x3  # toplama islemi"
    }
    """
    result = {
        "line_num": line_number,
        "label": None,
        "mnemonic": None,
        "operands": [],
        "original": line.rstrip()
    }

    # Yorumu temizle (# veya ; sonrasi)
    code = line
    for comment_char in ['#', ';']:
        if comment_char in code:
            code = code[:code.index(comment_char)]

    # Bosluklari temizle
    code = code.strip()

    # Bos satir kontrolu
    if not code:
        return None  # Bos satir, atla

    # Label kontrolu (iki nokta ile biten kisim)
    if ':' in code:
        # Label'i ayir
        label_part, rest = code.split(':', 1)
        result["label"] = label_part.strip()
        code = rest.strip()

        # Sadece label olan satir (ornek: "loop:")
        if not code:
            return result

    # Mnemonic ve operandlari ayir
    parts = code.split(None, 1)  # Ilk bosluktaan bol

    # Mnemonic (komut adi veya direktif)
    result["mnemonic"] = parts[0].strip()

    # Operandlar (varsa)
    if len(parts) > 1:
        operand_str = parts[1].strip()
        # Virgul ile ayir ve boslulari temizle
        operands = [op.strip() for op in operand_str.split(',')]
        # Bos operandlari filtrele
        result["operands"] = [op for op in operands if op]

    return result


def tokenize_file(lines):
    """Tum kaynak kod satirlarini tokenize eder.

    Args:
        lines: Satir listesi (list of str)

    Returns:
        Token listesi (bos satirlar haric)
    """
    tokens = []
    for i, line in enumerate(lines):
        token = tokenize_line(line, i + 1)  # Satir numarasi 1'den baslar
        if token is not None:
            tokens.append(token)
    return tokens
