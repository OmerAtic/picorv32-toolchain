# ============================================================
# main.py - PicoRV32 Assembler Ana Calistirici
# ============================================================
# Two-pass assembler akisini yurutur:
#   1) Kaynak dosyayi oku
#   2) Lexer ile tokenize et
#   3) Pseudo-komutlari genislet (bonus)
#   4) Pass 1: Label'lari topla, symbol table olustur
#   5) Pass 2: Her instruction icin makine kodu uret
#   6) Sonuclari goster
# ============================================================

import sys
from assembler.lexer import tokenize_file
from assembler.parser import classify_line, parse_immediate
from assembler.encoder import encode_instruction
from assembler.error_handler import ErrorHandler
from tables.opcode_table import get_instruction_info, OPCODE_TABLE, REGISTER_TABLE
from tables.symbol_table import SymbolTable
from tables.directive import process_directive, is_directive
from tables.pseudo import is_pseudo, expand_pseudo
from assembler.simulator import simulate, print_registers, print_memory


def print_opcode_table():
    """Opcode tablosunu ekrana yazdirir."""
    print(f"\n{'='*75}")
    print(f"  OPCODE TABLE ({len(OPCODE_TABLE)} komut)")
    print(f"{'='*75}")
    print(f"  {'Komut':<8} {'Tip':<6} {'Opcode':<12} {'Funct3':<10} {'Funct7'}")
    print(f"  {'-'*8} {'-'*6} {'-'*12} {'-'*10} {'-'*10}")

    # Tipe gore grupla
    for inst_type in ["R", "I", "S", "B", "U", "J"]:
        for name, info in OPCODE_TABLE.items():
            if info["type"] == inst_type:
                opcode_str = f"0b{info['opcode']:07b}"
                funct3_str = f"0b{info['funct3']:03b}" if info['funct3'] is not None else "-"
                funct7_str = f"0b{info['funct7']:07b}" if info['funct7'] is not None else "-"
                print(f"  {name:<8} {info['type']:<6} {opcode_str:<12} {funct3_str:<10} {funct7_str}")


def assemble(source_code):
    """Assembly kaynak kodunu makine koduna donusturur.

    Args:
        source_code: Assembly kaynak kodu (string)

    Returns:
        dict: {
            "object_code": [(adres, hex, binary, kaynak), ...],
            "symbol_table": {label: adres, ...},
            "errors": [{line, type, message}, ...],
            "data_memory": {adres: deger, ...}
        }
    """
    error_handler = ErrorHandler()
    symbol_table = SymbolTable()
    data_memory = {}  # .word, .byte direktifleri icin

    # --- ADIM 1: Opcode Table ---
    print_opcode_table()

    # --- ADIM 2: Lexer - Tokenize ---
    lines = source_code.split('\n')
    tokens = tokenize_file(lines)

    print(f"\n{'='*75}")
    print(f"  LEXER CIKTISI - Sozcuksel Analiz ({len(tokens)} satir islendi)")
    print(f"{'='*75}")
    print(f"  {'Satir':<8} {'Label':<12} {'Komut':<10} {'Operandlar'}")
    print(f"  {'-'*8} {'-'*12} {'-'*10} {'-'*30}")
    for t in tokens:
        label_str = t['label'] if t['label'] else "-"
        mnemonic_str = t['mnemonic'] if t['mnemonic'] else "-"
        ops_str = ", ".join(t['operands']) if t['operands'] else "-"
        print(f"  {t['line_num']:<8} {label_str:<12} {mnemonic_str:<10} {ops_str}")

    # --- ADIM 3: Pseudo-komutlari genislet (bonus) ---
    expanded_tokens = []
    for token in tokens:
        if token["mnemonic"] and is_pseudo(token["mnemonic"]):
            expanded = expand_pseudo(token)
            expanded_tokens.extend(expanded)
        else:
            expanded_tokens.append(token)

    # --- ADIM 4: Pass 1 - Sembol Cozumleme ---
    pc = 0  # Program Counter (baslangic adresi: 0)

    for token in expanded_tokens:
        # Label varsa symbol table'a ekle
        if token["label"]:
            success = symbol_table.add_symbol(token["label"], pc)
            if not success:
                error_handler.add_error(token["line_num"], "semantic",
                                        f"Label zaten tanimli: '{token['label']}'")

        # Mnemonic yoksa (sadece label satiri) atla
        if token["mnemonic"] is None:
            continue

        # Satir turunu belirle
        line_type = classify_line(token)

        if line_type == "directive":
            pc = process_directive(token, pc, data_memory, error_handler)
        elif line_type in ["instruction", "pseudo"]:
            pc += 4
        elif line_type == "unknown":
            error_handler.add_error(token["line_num"], "syntax",
                                    f"Bilinmeyen komut: '{token['mnemonic']}'")

    # Symbol Table goster
    symbol_table.print_table()

    # --- ADIM 5: Pass 2 - Makine Kodu Uretimi (Object Code) ---
    print(f"{'='*90}")
    print(f"  OBJECT CODE - Makine Kodu Ciktisi")
    print(f"{'='*90}")
    print(f"  {'Adres':<12} {'Hex':<14} {'Binary':<36} {'Kaynak Kod'}")
    print(f"  {'-'*12} {'-'*14} {'-'*36} {'-'*30}")

    pc = 0
    object_code = []

    for token in expanded_tokens:
        if token["mnemonic"] is None:
            continue

        line_type = classify_line(token)

        if line_type == "directive":
            old_pc = pc
            pc = process_directive(token, pc, data_memory, error_handler)

            # .word ve .byte icin cikti goster
            if token["mnemonic"].lower() in [".word", ".byte"]:
                value = data_memory.get(old_pc, 0)
                hex_str = f"0x{value:08X}"
                bin_str = f"{value:032b}"
                print(f"  0x{old_pc:08X}   {hex_str:<14} {bin_str:<36} {token['original']}")
                object_code.append((old_pc, hex_str, bin_str, token['original']))

        elif line_type in ["instruction", "pseudo"]:
            machine_code = encode_instruction(token, pc, symbol_table, error_handler)

            if machine_code is not None:
                hex_str = f"0x{machine_code:08X}"
                bin_str = f"{machine_code:032b}"
                print(f"  0x{pc:08X}   {hex_str:<14} {bin_str:<36} {token['original']}")
                object_code.append((pc, hex_str, bin_str, token['original']))

            pc += 4

    # --- ADIM 6: Hata Raporu ---
    error_handler.print_errors()

    # --- ADIM 7: Simulasyon - Register Degerleri ---
    if not error_handler.has_errors():
        registers, final_memory, steps = simulate(
            expanded_tokens, symbol_table, data_memory
        )
        print_registers(registers)
        print_memory(final_memory)
        print(f"  Simulasyon {steps} adimda tamamlandi.")
    else:
        registers = [0] * 32
        final_memory = data_memory

    return {
        "object_code": object_code,
        "symbol_table": symbol_table.get_all_symbols(),
        "errors": error_handler.get_errors(),
        "data_memory": final_memory,
        "registers": registers
    }


def main():
    """Komut satirindan .asm dosyasini okuyup assemble eder."""
    if len(sys.argv) < 2:
        print("Kullanim: python main.py <dosya.asm>")
        print("Ornek:    python main.py examples/basic.asm")
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, 'r') as f:
            source_code = f.read()
    except FileNotFoundError:
        print(f"Hata: Dosya bulunamadi: '{filename}'")
        sys.exit(1)

    print(f"\n{'='*90}")
    print(f"  PicoRV32 Assembler - RV32I Alt Kumesi")
    print(f"  Dosya: {filename}")
    print(f"{'='*90}")

    # Assemble et
    result = assemble(source_code)

    # Ozet
    print(f"\n{'='*90}")
    print(f"  OZET")
    print(f"{'='*90}")
    print(f"  Toplam instruction: {len(result['object_code'])}")
    print(f"  Toplam sembol:      {len(result['symbol_table'])}")
    print(f"  Toplam hata:        {len(result['errors'])}")
    print(f"{'='*90}")


if __name__ == "__main__":
    main()
