# ============================================================
# assemble.py - Section-aware Assembler (Proje-2)
# ============================================================
# Mevcut Proje-1 assembler altyapisini (lexer, encoder, error_handler)
# kullanarak section-aware (.text/.data) ve relocation-aware bir
# assembler insa eder. Cikti: PCO v1 object dosyasi (.o).
#
# Iki gecisli (two-pass) yaklasim:
#   PASS 1: Section yerlesimi + sembol toplama (label, global, extern)
#   PASS 2: Encoding + relocation emit
#
# Linker bu .o dosyalarini birlestirip nihai HEX uretir.
# ============================================================

import os
import re

from assembler.lexer import tokenize_file
from assembler.parser import (
    classify_line, parse_immediate, parse_memory_operand,
    parse_reloc_expr, is_reloc_expr,
)
from assembler.encoder import (
    encode_r_type, encode_i_type, encode_s_type,
    encode_b_type, encode_u_type, encode_j_type,
    encode_i_shift,
)
from assembler.error_handler import ErrorHandler
from assembler import obj_format as oof

from tables.opcode_table import (
    get_instruction_info, get_register_number,
)
from tables.directive import (
    is_directive, parse_string_literal, split_string_operand,
)
from tables.pseudo import is_pseudo, expand_pseudo


# ============================================================
# AssemblerContext: assembler durum sinifi
# ============================================================

class AssemblerContext:
    """Bir assembler kosmasinin durumunu tutar.

    Bircok dict + bytearray yerine tek nesnede toplanir, kod okunur.
    """

    def __init__(self, filename):
        self.filename = filename
        self.current_section = ".text"

        # Section icerikleri (bytearray, byte siralamasi LE)
        self.section_data = {
            ".text": bytearray(),
            ".data": bytearray(),
        }

        # Section hizalama (default 4)
        self.section_align = {
            ".text": 4,
            ".data": 4,
        }

        # Sembol tablosu: name -> {section, value, binding, size, line}
        self.symbols = {}

        # Global olarak isaretlenen sembol isimleri
        self.global_names = set()

        # Extern olarak isaretlenen sembol isimleri
        self.extern_names = set()

        # Relocation listesi (bos bayraklarla baslar)
        self.relocations = []

        # Hata yoneticisi
        self.errors = ErrorHandler()

    def section_offset(self, name=None):
        """Bir section'in mevcut byte offset'i (bayt cinsinden)."""
        if name is None:
            name = self.current_section
        return len(self.section_data.get(name, bytearray()))

    def emit_bytes(self, data):
        """Mevcut section'a bytes ekler."""
        if self.current_section not in self.section_data:
            self.section_data[self.current_section] = bytearray()
        self.section_data[self.current_section].extend(data)

    def patch_word_at(self, section, offset, word):
        """Section'in belirli offset'ine 32-bit word yazar (LE)."""
        buf = self.section_data[section]
        buf[offset+0] = (word >>  0) & 0xFF
        buf[offset+1] = (word >>  8) & 0xFF
        buf[offset+2] = (word >> 16) & 0xFF
        buf[offset+3] = (word >> 24) & 0xFF

    def add_symbol(self, name, section, value, binding=oof.BIND_LOCAL,
                   size=0, line=0):
        """Sembol tablosuna ekler. Duplicate'i hata olarak isaretler."""
        if name in self.symbols and self.symbols[name]["binding"] != oof.BIND_EXTERN:
            self.errors.add_error(line, "semantic",
                                  f"Sembol zaten tanimli: '{name}'")
            return False
        self.symbols[name] = {
            "section": section,
            "value":   value,
            "binding": binding,
            "size":    size,
            "line":    line,
        }
        return True


# ============================================================
# Yardimcilar
# ============================================================

def _align_up(value, align):
    """value'yu align'in katina yuvarlar."""
    if align <= 1:
        return value
    return ((value + align - 1) // align) * align


def _word_to_le_bytes(word):
    return bytes([(word >> 0) & 0xFF, (word >> 8) & 0xFF,
                  (word >> 16) & 0xFF, (word >> 24) & 0xFF])


# ============================================================
# Section ve direktif islemcisi
# ============================================================

def _process_section_change(operands, ctx, line_num):
    """.section .text / .section .data isleyicisi."""
    if len(operands) < 1:
        ctx.errors.add_error(line_num, "directive",
                             ".section bir isim gerektirir")
        return
    name = operands[0]
    if name not in (".text", ".data", ".bss"):
        ctx.errors.add_error(line_num, "directive",
                             f"Desteklenmeyen section: {name}")
        return
    ctx.current_section = name
    if name not in ctx.section_data:
        ctx.section_data[name] = bytearray()
        ctx.section_align[name] = 4


def _process_data_directive(token, ctx, pass_num):
    """Veri direktiflerini isler (.word/.byte/.half/.string/.asciz/.ascii/.space/.align).

    pass_num: 1 veya 2. Pass 1'de sadece offset hesabi yapilir,
              pass 2'de gercek bytes section'a yazilir.
    """
    directive = token["mnemonic"].lower()
    operands = token["operands"]
    line_num = token["line_num"]
    sec_name = ctx.current_section

    if directive == ".word":
        for op in operands:
            value = parse_immediate(op)
            if value is None:
                # Sembol referansi olabilir - linker icin reloc
                # .word sym -> 32-bit absolute reloc gerekirdi ama spec'te yok
                # Bu durumda hata
                ctx.errors.add_error(line_num, "directive",
                                     f".word icin gecersiz deger: '{op}'")
                continue
            if pass_num == 2:
                ctx.emit_bytes(_word_to_le_bytes(value & 0xFFFFFFFF))
            else:
                # Pass 1'de yer tutucu
                ctx.section_data[sec_name].extend(b"\x00\x00\x00\x00")

    elif directive == ".byte":
        for op in operands:
            value = parse_immediate(op)
            if value is None:
                ctx.errors.add_error(line_num, "directive",
                                     f".byte icin gecersiz deger: '{op}'")
                continue
            if pass_num == 2:
                ctx.emit_bytes(bytes([value & 0xFF]))
            else:
                ctx.section_data[sec_name].append(0x00)

    elif directive == ".half":
        for op in operands:
            value = parse_immediate(op)
            if value is None:
                ctx.errors.add_error(line_num, "directive",
                                     f".half icin gecersiz deger: '{op}'")
                continue
            v = value & 0xFFFF
            if pass_num == 2:
                ctx.emit_bytes(bytes([v & 0xFF, (v >> 8) & 0xFF]))
            else:
                ctx.section_data[sec_name].extend(b"\x00\x00")

    elif directive in (".string", ".asciz", ".ascii"):
        # Lexer string'i virgule gore boldu; orijinal satirdan al
        raw = _extract_string_from_line(token["original"])
        if raw is None:
            ctx.errors.add_error(line_num, "directive",
                                 f"{directive} icin gecerli string yok")
            return
        data = parse_string_literal(raw)
        if data is None:
            ctx.errors.add_error(line_num, "directive",
                                 f"String parse hatasi: {raw}")
            return

        # .string ve .asciz null-terminator ekler; .ascii eklemez
        if directive in (".string", ".asciz"):
            data = data + b"\x00"

        if pass_num == 2:
            ctx.emit_bytes(data)
        else:
            ctx.section_data[sec_name].extend(b"\x00" * len(data))

    elif directive in (".space", ".skip"):
        if len(operands) == 0:
            ctx.errors.add_error(line_num, "directive",
                                 f"{directive} bir boyut gerektirir")
            return
        size = parse_immediate(operands[0])
        if size is None or size < 0:
            ctx.errors.add_error(line_num, "directive",
                                 f"{directive} icin gecersiz boyut: '{operands[0]}'")
            return
        ctx.section_data[sec_name].extend(b"\x00" * size)

    elif directive == ".align":
        # .align N -> 2^N byte hizalama (RISC-V GAS davranisi: sayilir 2^N)
        # Ama bizim icin daha basit: N byte hizalama (powers of 2)
        if len(operands) == 0:
            return
        n = parse_immediate(operands[0])
        if n is None or n <= 0:
            return
        # Hem 2^N hem N destegi: kullanici 2 yazarsa 2 byte hizalanir,
        # 4 yazarsa 4 byte, vb. (basit yaklasim - dokumanda belirtilir)
        cur = ctx.section_offset()
        target = _align_up(cur, n)
        ctx.section_data[sec_name].extend(b"\x00" * (target - cur))


def _extract_string_from_line(original_line):
    """Bir asm satirindan tirnak icindeki bolumu yakalar.

    Lexer virgule gore parcaladigi icin string icindeki virguller bozulur.
    Bu fonksiyon orijinal satirdan dogrudan tirnakli bolumu cekip alir.
    """
    if original_line is None:
        return None
    # Yorumu temizle
    line = original_line
    for cc in ('#', ';'):
        if cc in line:
            line = line[:line.index(cc)]
    return split_string_operand(_strip_label_and_directive(line))


def _strip_label_and_directive(line):
    """Label ve direktif adini atar, gerisini doner.

    Ornek: '   greet: .string "Hello, World"' -> '"Hello, World"'
    """
    s = line.strip()
    # Label varsa at
    if ':' in s:
        s = s.split(':', 1)[1].strip()
    # Direktif adini at (.string vb.)
    parts = s.split(None, 1)
    if len(parts) < 2:
        return ""
    return parts[1]


# ============================================================
# Pass 1: layout + sembol tablosu
# ============================================================

def _pass1(tokens, ctx):
    """Section yerlesimini ve sembol tablosunu hesaplar.

    Bu gecisten sonra ctx.symbols dolu olur (forward reference cozumu).
    """
    # Once .global ve .extern direktiflerini topla (bunlar sembol bagini etkiler)
    # Ayni anda label ve instruction layout'u yap.
    ctx.current_section = ".text"

    for token in tokens:
        line_num = token["line_num"]
        mnem = token["mnemonic"]

        # Label varsa kayit et (mevcut section + offset)
        if token["label"]:
            sec = ctx.current_section
            off = ctx.section_offset(sec)
            binding = oof.BIND_GLOBAL if token["label"] in ctx.global_names else oof.BIND_LOCAL
            ctx.add_symbol(token["label"], sec, off, binding=binding,
                           line=line_num)

        # Sadece label satiri
        if mnem is None:
            continue

        # Direktifler
        if mnem.startswith('.'):
            directive = mnem.lower()

            if directive == ".section":
                _process_section_change(token["operands"], ctx, line_num)

            elif directive == ".text":
                ctx.current_section = ".text"

            elif directive == ".data":
                ctx.current_section = ".data"

            elif directive in (".global", ".globl"):
                # Global isaretleme. Once gelirse sembolu gormeyiz, listeye al.
                for op in token["operands"]:
                    ctx.global_names.add(op)
                    if op in ctx.symbols:
                        ctx.symbols[op]["binding"] = oof.BIND_GLOBAL

            elif directive == ".extern":
                # Extern sembol: *UND* section'inda
                for op in token["operands"]:
                    ctx.extern_names.add(op)
                    ctx.symbols[op] = {
                        "section": oof.SECTION_UNDEF,
                        "value":   0,
                        "binding": oof.BIND_EXTERN,
                        "size":    0,
                        "line":    line_num,
                    }

            elif directive == ".end":
                break

            elif directive == ".org":
                # .org pass-1'de su anki section'da pad ekle
                target = parse_immediate(token["operands"][0]) if token["operands"] else None
                if target is not None:
                    cur = ctx.section_offset()
                    if target > cur:
                        ctx.section_data[ctx.current_section].extend(b"\x00" * (target - cur))
                # Eski semantik: PC'yi degistirir. Section icinde takip ediyoruz.

            else:
                # Veri direktifi - pass 1'de yer tutucu byte ekle
                _process_data_directive(token, ctx, pass_num=1)

            continue

        # Pseudo-komut: section icinde her birisi 4 byte yer tutar
        if is_pseudo(mnem):
            expanded = expand_pseudo(token)
            for _ in expanded:
                ctx.section_data[ctx.current_section].extend(b"\x00\x00\x00\x00")
            continue

        # Normal instruction
        info = get_instruction_info(mnem)
        if info is None:
            ctx.errors.add_error(line_num, "syntax",
                                 f"Bilinmeyen komut: '{mnem}'")
            continue
        # Her instruction 4 byte
        ctx.section_data[ctx.current_section].extend(b"\x00\x00\x00\x00")

    # Pass 1 sonu: global isaretlemeleri sembol tablosuna uygula
    for name in ctx.global_names:
        if name in ctx.symbols and ctx.symbols[name]["binding"] != oof.BIND_EXTERN:
            ctx.symbols[name]["binding"] = oof.BIND_GLOBAL


# ============================================================
# Pass 2: encoding + relocation emit
# ============================================================

def _pass2(tokens, ctx):
    """Gercek encoding'i yapar ve relocation listesini olusturur."""
    # Section'lari sifirla, yeniden doldur
    for name in list(ctx.section_data.keys()):
        ctx.section_data[name] = bytearray()
    ctx.relocations = []
    ctx.current_section = ".text"

    for token in tokens:
        line_num = token["line_num"]
        mnem = token["mnemonic"]

        if mnem is None:
            continue

        # Direktifler
        if mnem.startswith('.'):
            directive = mnem.lower()

            if directive == ".section":
                _process_section_change(token["operands"], ctx, line_num)
            elif directive == ".text":
                ctx.current_section = ".text"
            elif directive == ".data":
                ctx.current_section = ".data"
            elif directive in (".global", ".globl", ".extern"):
                pass  # Pass 1'de islendi
            elif directive == ".end":
                break
            elif directive == ".org":
                target = parse_immediate(token["operands"][0]) if token["operands"] else None
                if target is not None:
                    cur = ctx.section_offset()
                    if target > cur:
                        ctx.section_data[ctx.current_section].extend(b"\x00" * (target - cur))
            else:
                _process_data_directive(token, ctx, pass_num=2)
            continue

        # Pseudo: expand et, her bir gercek komutu encode et
        if is_pseudo(mnem):
            expanded = expand_pseudo(token)
            for sub in expanded:
                _encode_real_instruction(sub, ctx)
            continue

        # Normal instruction
        _encode_real_instruction(token, ctx)


def _encode_real_instruction(token, ctx):
    """Tek bir gercek (pseudo olmayan) instruction'i encode eder.

    Gerekirse relocation listesine ekler. Her instruction 4 byte yer alir.
    """
    line_num = token["line_num"]
    mnem = token["mnemonic"].upper()
    operands = token["operands"]
    info = get_instruction_info(mnem)
    if info is None:
        ctx.errors.add_error(line_num, "encoding",
                             f"Bilinmeyen komut: '{mnem}'")
        ctx.emit_bytes(b"\x00\x00\x00\x00")
        return

    inst_type = info["type"]
    opcode    = info["opcode"]
    funct3    = info["funct3"]
    funct7    = info["funct7"]

    # Bu komutun yazilacagi byte offset (section icinde)
    instr_offset = ctx.section_offset()
    instr_section = ctx.current_section

    word = 0  # encoded instruction (varsayilan 0; reloc varsa linker patchler)

    # ---- R-Type ----
    if inst_type == "R":
        if len(operands) != 3:
            _err_operand(ctx, line_num, mnem, "rd, rs1, rs2")
        else:
            rd  = _reg(operands[0], ctx, line_num)
            rs1 = _reg(operands[1], ctx, line_num)
            rs2 = _reg(operands[2], ctx, line_num)
            if None not in (rd, rs1, rs2):
                word = encode_r_type(rd, rs1, rs2, funct3, funct7, opcode)

    # ---- I-Shift (SLLI/SRLI/SRAI): rd, rs1, shamt(0..31) ----
    elif inst_type == "I_SHIFT":
        if len(operands) != 3:
            _err_operand(ctx, line_num, mnem, "rd, rs1, shamt(0..31)")
        else:
            rd  = _reg(operands[0], ctx, line_num)
            rs1 = _reg(operands[1], ctx, line_num)
            if None not in (rd, rs1):
                shamt = parse_immediate(operands[2])
                if shamt is None:
                    ctx.errors.add_error(line_num, "syntax",
                                         f"Gecersiz shamt: '{operands[2]}'")
                elif shamt < 0 or shamt > 31:
                    ctx.errors.add_error(line_num, "encoding",
                                         f"Shamt 0..31 arasinda olmali: {shamt}")
                else:
                    word = encode_i_shift(rd, rs1, shamt, funct3, funct7, opcode)

    # ---- I-Type ----
    elif inst_type == "I":
        # Load: LW rd, offset(rs1)
        if mnem in ("LW", "LH", "LB"):
            if len(operands) != 2:
                _err_operand(ctx, line_num, mnem, "rd, offset(rs1)")
            else:
                rd = _reg(operands[0], ctx, line_num)
                mem = parse_memory_operand(operands[1])
                if rd is None or mem is None:
                    if mem is None:
                        ctx.errors.add_error(line_num, "syntax",
                                             f"Gecersiz bellek operandi: '{operands[1]}'")
                else:
                    rs1 = _reg(mem["register"], ctx, line_num)
                    if rs1 is not None:
                        if "offset_expr" in mem:
                            # %lo(sym) -> reloc emit
                            kind, sym = mem["offset_expr"]
                            if kind != "lo":
                                ctx.errors.add_error(line_num, "encoding",
                                                     f"Load icin sadece %lo destekleniyor")
                            else:
                                ctx.relocations.append(oof.make_relocation(
                                    instr_section, instr_offset,
                                    oof.R_LO12_I, sym, 0, line_num))
                                word = encode_i_type(rd, rs1, 0, funct3, opcode)
                        else:
                            imm = mem["offset"]
                            if not (-2048 <= imm <= 2047):
                                ctx.errors.add_error(line_num, "encoding",
                                                     f"Load offset 12-bit asti: {imm}")
                            else:
                                word = encode_i_type(rd, rs1, imm, funct3, opcode)

        elif mnem == "JALR":
            if len(operands) != 3:
                _err_operand(ctx, line_num, mnem, "rd, rs1, imm")
            else:
                rd = _reg(operands[0], ctx, line_num)
                rs1 = _reg(operands[1], ctx, line_num)
                if None not in (rd, rs1):
                    # imm: sayi veya %pcrel_lo(sym)
                    op_imm = operands[2]
                    reloc = parse_reloc_expr(op_imm)
                    if reloc is not None:
                        kind, sym = reloc
                        if kind in ("lo", "pcrel_lo"):
                            rtype = oof.R_LO12_I if kind == "lo" else oof.R_PCREL_LO12
                            ctx.relocations.append(oof.make_relocation(
                                instr_section, instr_offset, rtype, sym, 0, line_num))
                            word = encode_i_type(rd, rs1, 0, funct3, opcode)
                        else:
                            ctx.errors.add_error(line_num, "encoding",
                                                 f"JALR icin uygun olmayan reloc: %{kind}")
                    else:
                        imm = parse_immediate(op_imm)
                        if imm is None:
                            ctx.errors.add_error(line_num, "syntax",
                                                 f"Gecersiz immediate: '{op_imm}'")
                        elif not (-2048 <= imm <= 2047):
                            ctx.errors.add_error(line_num, "encoding",
                                                 f"JALR imm 12-bit asti: {imm}")
                        else:
                            word = encode_i_type(rd, rs1, imm, funct3, opcode)

        else:
            # ADDI, ANDI, ORI, XORI, SLTI, SLTIU
            if len(operands) != 3:
                _err_operand(ctx, line_num, mnem, "rd, rs1, imm")
            else:
                rd = _reg(operands[0], ctx, line_num)
                rs1 = _reg(operands[1], ctx, line_num)
                if None not in (rd, rs1):
                    op_imm = operands[2]
                    reloc = parse_reloc_expr(op_imm)
                    if reloc is not None:
                        kind, sym = reloc
                        if kind in ("lo", "pcrel_lo"):
                            rtype = oof.R_LO12_I if kind == "lo" else oof.R_PCREL_LO12
                            ctx.relocations.append(oof.make_relocation(
                                instr_section, instr_offset, rtype, sym, 0, line_num))
                            word = encode_i_type(rd, rs1, 0, funct3, opcode)
                        else:
                            ctx.errors.add_error(line_num, "encoding",
                                                 f"{mnem} icin uygun olmayan reloc: %{kind}")
                    else:
                        imm = parse_immediate(op_imm)
                        if imm is None:
                            ctx.errors.add_error(line_num, "syntax",
                                                 f"Gecersiz immediate: '{op_imm}'")
                        elif not (-2048 <= imm <= 2047):
                            ctx.errors.add_error(line_num, "encoding",
                                                 f"{mnem} imm 12-bit asti: {imm}")
                        else:
                            word = encode_i_type(rd, rs1, imm, funct3, opcode)

    # ---- S-Type ----
    elif inst_type == "S":
        if len(operands) != 2:
            _err_operand(ctx, line_num, mnem, "rs2, offset(rs1)")
        else:
            rs2 = _reg(operands[0], ctx, line_num)
            mem = parse_memory_operand(operands[1])
            if rs2 is None or mem is None:
                if mem is None:
                    ctx.errors.add_error(line_num, "syntax",
                                         f"Gecersiz bellek operandi: '{operands[1]}'")
            else:
                rs1 = _reg(mem["register"], ctx, line_num)
                if rs1 is not None:
                    if "offset_expr" in mem:
                        kind, sym = mem["offset_expr"]
                        if kind != "lo":
                            ctx.errors.add_error(line_num, "encoding",
                                                 f"Store icin sadece %lo")
                        else:
                            ctx.relocations.append(oof.make_relocation(
                                instr_section, instr_offset,
                                oof.R_LO12_S, sym, 0, line_num))
                            word = encode_s_type(rs1, rs2, 0, funct3, opcode)
                    else:
                        imm = mem["offset"]
                        if not (-2048 <= imm <= 2047):
                            ctx.errors.add_error(line_num, "encoding",
                                                 f"Store offset 12-bit asti: {imm}")
                        else:
                            word = encode_s_type(rs1, rs2, imm, funct3, opcode)

    # ---- B-Type ----
    elif inst_type == "B":
        if len(operands) != 3:
            _err_operand(ctx, line_num, mnem, "rs1, rs2, label/offset")
        else:
            rs1 = _reg(operands[0], ctx, line_num)
            rs2 = _reg(operands[1], ctx, line_num)
            if None not in (rs1, rs2):
                target_op = operands[2]
                imm = parse_immediate(target_op)
                if imm is None:
                    # Sembol: ayni section'da local mi?
                    sym = ctx.symbols.get(target_op)
                    if (sym is not None
                            and sym["binding"] != oof.BIND_EXTERN
                            and sym["section"] == instr_section):
                        # Local cozumlemesi mumkun (offset farki)
                        offset = sym["value"] - instr_offset
                        if not (-4096 <= offset <= 4094):
                            ctx.errors.add_error(line_num, "encoding",
                                                 f"Branch offset asti: {offset}")
                            offset = 0
                        word = encode_b_type(rs1, rs2, offset, funct3, opcode)
                    else:
                        # Cross-section veya extern: linker'a birak
                        ctx.relocations.append(oof.make_relocation(
                            instr_section, instr_offset,
                            oof.R_BRANCH, target_op, 0, line_num))
                        word = encode_b_type(rs1, rs2, 0, funct3, opcode)
                else:
                    if not (-4096 <= imm <= 4094):
                        ctx.errors.add_error(line_num, "encoding",
                                             f"Branch immediate asti: {imm}")
                    else:
                        word = encode_b_type(rs1, rs2, imm, funct3, opcode)

    # ---- U-Type (LUI/AUIPC) ----
    elif inst_type == "U":
        if len(operands) != 2:
            _err_operand(ctx, line_num, mnem, "rd, imm")
        else:
            rd = _reg(operands[0], ctx, line_num)
            if rd is not None:
                op_imm = operands[1]
                reloc = parse_reloc_expr(op_imm)
                if reloc is not None:
                    kind, sym = reloc
                    if mnem == "LUI" and kind == "hi":
                        ctx.relocations.append(oof.make_relocation(
                            instr_section, instr_offset,
                            oof.R_HI20, sym, 0, line_num))
                        word = encode_u_type(rd, 0, opcode)
                    elif mnem == "AUIPC" and kind == "pcrel_hi":
                        ctx.relocations.append(oof.make_relocation(
                            instr_section, instr_offset,
                            oof.R_PCREL_HI20, sym, 0, line_num))
                        word = encode_u_type(rd, 0, opcode)
                    else:
                        ctx.errors.add_error(line_num, "encoding",
                                             f"{mnem} icin uygun olmayan reloc: %{kind}")
                else:
                    imm = parse_immediate(op_imm)
                    if imm is None:
                        ctx.errors.add_error(line_num, "syntax",
                                             f"Gecersiz immediate: '{op_imm}'")
                    elif imm < 0 or imm > 0xFFFFF:
                        ctx.errors.add_error(line_num, "encoding",
                                             f"U-type imm 20-bit asti: {imm}")
                    else:
                        word = encode_u_type(rd, imm, opcode)

    # ---- J-Type (JAL) ----
    elif inst_type == "J":
        if len(operands) != 2:
            _err_operand(ctx, line_num, mnem, "rd, label/offset")
        else:
            rd = _reg(operands[0], ctx, line_num)
            if rd is not None:
                target_op = operands[1]
                imm = parse_immediate(target_op)
                if imm is None:
                    sym = ctx.symbols.get(target_op)
                    if (sym is not None
                            and sym["binding"] != oof.BIND_EXTERN
                            and sym["section"] == instr_section):
                        offset = sym["value"] - instr_offset
                        if not (-1048576 <= offset <= 1048574):
                            ctx.errors.add_error(line_num, "encoding",
                                                 f"JAL offset asti: {offset}")
                            offset = 0
                        word = encode_j_type(rd, offset, opcode)
                    else:
                        ctx.relocations.append(oof.make_relocation(
                            instr_section, instr_offset,
                            oof.R_JAL, target_op, 0, line_num))
                        word = encode_j_type(rd, 0, opcode)
                else:
                    if not (-1048576 <= imm <= 1048574):
                        ctx.errors.add_error(line_num, "encoding",
                                             f"JAL imm asti: {imm}")
                    else:
                        word = encode_j_type(rd, imm, opcode)

    # 4 byte yaz
    ctx.emit_bytes(_word_to_le_bytes(word & 0xFFFFFFFF))


def _reg(name, ctx, line_num):
    """Register adini numaraya cevirir, hata ekleyebilir."""
    n = get_register_number(name)
    if n is None:
        ctx.errors.add_error(line_num, "syntax",
                             f"Gecersiz register: '{name}'")
    return n


def _err_operand(ctx, line_num, mnem, fmt):
    ctx.errors.add_error(line_num, "syntax",
                         f"{mnem} formati: {fmt}")


# ============================================================
# Public API
# ============================================================

def assemble_source(source_code, filename="<source>"):
    """Bir asm kaynagini PCO object dict'ine cevirir.

    Returns: (obj_dict, ErrorHandler)
    """
    ctx = AssemblerContext(filename)

    # Lexer
    lines = source_code.split('\n')
    tokens = tokenize_file(lines)

    _pass1(tokens, ctx)
    _pass2(tokens, ctx)

    # PCO object yapisi olustur
    sections = []
    for name, data in ctx.section_data.items():
        if len(data) == 0:
            continue
        sections.append(oof.make_section(name, bytes(data),
                                         align=ctx.section_align.get(name, 4)))

    symbols = []
    # Yerel sembolleri once, sonra global'leri (ELF aliskanligi)
    for name, info in ctx.symbols.items():
        symbols.append(oof.make_symbol(
            name, info["section"], info["value"],
            size=info.get("size", 0),
            binding=info["binding"],
            line=info.get("line", 0),
        ))

    obj = oof.make_object(filename, sections=sections,
                          symbols=symbols, relocations=ctx.relocations)
    return obj, ctx.errors


def assemble_file(input_path, output_path=None, listing_path=None):
    """Bir .s dosyasini .o dosyasina cevirir.

    Args:
        input_path:  .s dosya yolu
        output_path: cikti .o dosya yolu (None ise input_path.o)
        listing_path: opsiyonel listing dosya yolu

    Returns: (obj_dict, errors_list)
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        source = f.read()

    obj, errors = assemble_source(source, filename=os.path.basename(input_path))

    if output_path is None:
        base, _ = os.path.splitext(input_path)
        output_path = base + ".o"

    if not errors.has_errors():
        oof.write_object_file(obj, output_path)

    if listing_path is not None and not errors.has_errors():
        _write_listing(obj, listing_path)

    return obj, errors.get_errors()


def _write_listing(obj, listing_path):
    """Insan-okunur bir listing dosyasi yazar."""
    with open(listing_path, 'w', encoding='utf-8') as f:
        f.write(f"# Listing: {obj['filename']}\n")
        f.write(f"# Generated: {obj['timestamp']}\n\n")

        for sec in obj["sections"]:
            f.write(f"## Section {sec['name']}  size={sec['size']}  "
                    f"align={sec['align']}  flags={sec['flags']}\n")
            data = oof.hex_to_bytes(sec["data"])
            for i in range(0, len(data), 4):
                word_bytes = data[i:i+4]
                if len(word_bytes) == 4:
                    word = (word_bytes[0]
                            | (word_bytes[1] << 8)
                            | (word_bytes[2] << 16)
                            | (word_bytes[3] << 24))
                    f.write(f"  {i:08x}: {word:08x}\n")
                else:
                    f.write(f"  {i:08x}: " + " ".join(f"{b:02x}" for b in word_bytes) + "\n")
            f.write("\n")

        f.write("## Symbols\n")
        for sym in obj["symbols"]:
            f.write(f"  {sym['binding']:<7} {sym['section']:<10} "
                    f"{sym['value']:08x}  {sym['name']}\n")

        f.write("\n## Relocations\n")
        for rel in obj["relocations"]:
            f.write(f"  {rel['section']}+{rel['offset']:08x}  "
                    f"{rel['type']:<24}  {rel['symbol']}+{rel['addend']}\n")
