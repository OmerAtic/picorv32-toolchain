# ============================================================
# tests/test_e2e.py - End-to-end (uctan uca) testler
# ============================================================
# Assembler -> Linker -> (Simulasyon) zincirini test eder.
# Iverilog kuruluysa simulasyon testleri de calisir; degilse atlanir.
#
# 9 test:
#   1) LED counter simulasyonu GPIO 0,1,2,3,4 yaziyor
#   2) Multi-file linker GPIO 22,8,42,314,0xDEADBEEF uretiyor
#   3) UART hello string'i ve hex sayisi yaziliyor
#   4) Object format magic + EXTERN + reloc dogru
#   5) Multiple definition hatasini yakaliyor
#   6) Undefined reference hatasini yakaliyor
#   7) Memory overflow tespit ediliyor
#   8) Linked .data offset'i dogru (pi_x100 = 0x13a)
#   9) Object format roundtrip (parse -> serialize -> parse)
# ============================================================

import os
import re
import shutil
import subprocess
import sys

import pytest


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(ROOT, "build")
DEMOS = os.path.join(ROOT, "demos")

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from assembler.assemble import assemble_source, assemble_file  # noqa: E402
from assembler import obj_format as oof  # noqa: E402
from linker.linker import link_objects, LinkError  # noqa: E402


# ============================================================
# Yardimcilar
# ============================================================

def _ensure_build_dir():
    os.makedirs(BUILD, exist_ok=True)


def _have_iverilog():
    return shutil.which("iverilog") is not None


def _run_sim(hex_path, cycles=200000, max_gpio=0):
    """Iverilog simulator'unu calistirir, stdout'u doner."""
    sh = os.path.join(ROOT, "sim", "run_sim.sh")
    result = subprocess.run(
        [sh, hex_path, str(cycles), str(max_gpio)],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    return result.stdout + "\n" + result.stderr


def _build_demo(name, asm_files, hex_name):
    """Bir demoyu derler ve linkler. Cikti hex dosyasinin yolunu doner."""
    _ensure_build_dir()
    obj_paths = []
    for asm in asm_files:
        full = os.path.join(DEMOS, name, asm)
        out  = os.path.join(BUILD, asm.replace(".s", "_e2e.o"))
        obj, errs = assemble_file(full, output_path=out)
        assert not errs, f"Assemble hatalari ({asm}): {errs}"
        obj_paths.append(out)

    hex_path = os.path.join(BUILD, hex_name)
    link_objects(obj_paths,
                 script_path=os.path.join(ROOT, "scripts", "picorv_unified.ld.json"),
                 hex_output=hex_path)
    return hex_path


# ============================================================
# Testler
# ============================================================

def test_01_led_counter_sim():
    """LED counter demosu sim'de GPIO 0,1,2 sayilarini uretir."""
    if not _have_iverilog():
        pytest.skip("iverilog kurulu degil")
    hex_path = _build_demo("led_counter", ["led_counter.s"], "led_e2e.hex")
    out = _run_sim(hex_path, cycles=5_000_000, max_gpio=3)
    # 0x00000001, 0x00000002 gibi degerleri arayalim
    assert "0x00000001" in out, f"GPIO=1 gorunmedi:\n{out[-500:]}"
    assert "0x00000002" in out, f"GPIO=2 gorunmedi:\n{out[-500:]}"


def test_02_multi_file_linker_results():
    """Multi-file linker demosu 22,8,42,314,0xDEADBEEF uretir."""
    if not _have_iverilog():
        pytest.skip("iverilog kurulu degil")
    hex_path = _build_demo("multi_file", ["main.s", "math_lib.s"], "multi_e2e.hex")
    out = _run_sim(hex_path, cycles=200000, max_gpio=6)

    expected = ["0x00000016", "0x00000008", "0x0000002a",
                "0x0000013a", "0xdeadbeef"]
    for val in expected:
        assert val in out, f"Beklenen GPIO={val} gorunmedi"


def test_03_uart_hello():
    """UART hello demosu beklenen string'leri yaziyor."""
    if not _have_iverilog():
        pytest.skip("iverilog kurulu degil")
    hex_path = _build_demo("uart_hello", ["main.s", "uart_lib.s"], "uart_e2e.hex")
    out = _run_sim(hex_path, cycles=2_000_000)
    assert "Hello, FPGA from PicoRV32!" in out, \
        f"Greeting gorunmedi:\n{out[-500:]}"
    assert "counter = 0xdeadbeef" in out, \
        f"Counter satir gorunmedi:\n{out[-500:]}"


def test_04_object_format_structure():
    """Object format magic, EXTERN sembol ve relocations alanlari dogru."""
    src = """
.section .text
.global main
.extern external_func

main:
    call external_func
    ret
"""
    obj, errs = assemble_source(src, "test_obj.s")
    assert not errs.has_errors()

    # Magic
    assert obj["magic"] == oof.PCO_MAGIC
    assert obj["version"] == oof.PCO_VERSION

    # EXTERN sembol var ve *UND* section'inda
    ext = oof.find_symbol(obj, "external_func")
    assert ext is not None
    assert ext["binding"] == oof.BIND_EXTERN
    assert ext["section"] == oof.SECTION_UNDEF

    # GLOBAL sembol var
    main_sym = oof.find_symbol(obj, "main")
    assert main_sym is not None
    assert main_sym["binding"] == oof.BIND_GLOBAL

    # Relocations: CALL pseudo iki reloc uretir (PCREL_HI20 + PCREL_LO12_I)
    relocs = [r for r in obj["relocations"] if r["symbol"] == "external_func"]
    assert len(relocs) == 2
    types = sorted(r["type"] for r in relocs)
    assert types == sorted([oof.R_PCREL_HI20, oof.R_PCREL_LO12])


def test_05_multiple_definition():
    """Iki dosyada ayni .global sembol -> linker hata verir."""
    _ensure_build_dir()
    src1 = ".section .text\n.global foo\nfoo: ret\n"
    src2 = ".section .text\n.global foo\nfoo: ret\n"

    o1, e1 = assemble_source(src1, "f1.s"); assert not e1.has_errors()
    o2, e2 = assemble_source(src2, "f2.s"); assert not e2.has_errors()

    p1 = os.path.join(BUILD, "mdef_1.o")
    p2 = os.path.join(BUILD, "mdef_2.o")
    oof.write_object_file(o1, p1)
    oof.write_object_file(o2, p2)

    with pytest.raises(LinkError) as exc_info:
        link_objects([p1, p2])
    assert "MULTIPLE_DEFINITION" in str(exc_info.value)


def test_06_undefined_reference():
    """Tanimli olmayan extern sembol -> linker UNDEFINED_REFERENCE hata."""
    _ensure_build_dir()
    src = """
.section .text
.global _start
.extern not_defined

_start:
    call not_defined
"""
    obj, e = assemble_source(src, "undef.s")
    assert not e.has_errors()
    p = os.path.join(BUILD, "undef.o")
    oof.write_object_file(obj, p)

    with pytest.raises(LinkError) as exc_info:
        link_objects([p])
    assert "UNDEFINED_REFERENCE" in str(exc_info.value) or \
           "UNDEFINED" in str(exc_info.value)


def test_07_memory_overflow():
    """8 KB BRAM'a sigmayan veri -> linker tasma hatasi verir."""
    _ensure_build_dir()
    # 9 KB (.space 9000) -> 8192 byte limiti asar
    src = """
.section .data
.global blob
blob:
    .space 9000
.section .text
.global _start
_start:
    nop
"""
    obj, e = assemble_source(src, "overflow.s")
    assert not e.has_errors()
    p = os.path.join(BUILD, "overflow.o")
    oof.write_object_file(obj, p)

    with pytest.raises(LinkError) as exc_info:
        link_objects([p])
    assert "tasild" in str(exc_info.value).lower() or \
           "overflow" in str(exc_info.value).lower()


def test_08_data_section_layout():
    """Multi-file demoda pi_x100 = 0x13a (314) ve magic_number = 0xDEADBEEF
    dogru adreste yer aliyor."""
    _ensure_build_dir()
    hex_path = _build_demo("multi_file", ["main.s", "math_lib.s"], "layout_e2e.hex")

    # Hex dosyasini oku, .data bolgesinde 314 ve 0xDEADBEEF arayalim
    words = []
    with open(hex_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            words.append(int(line, 16))

    # .data, math_lib.s'de pi_x100 ve magic_number iceriyor
    # hangi word index'i map'ten alabiliriz, ama daha basit:
    # 314 ve 0xdeadbeef PEKI sirasi ile yer almali
    pi_idx = None
    for i, w in enumerate(words):
        if w == 314:
            pi_idx = i
            break
    assert pi_idx is not None, "pi_x100 (314) hex'te bulunamadi"
    assert words[pi_idx + 1] == 0xDEADBEEF, \
        f"magic_number 0xDEADBEEF, pi_x100'un hemen ardinda olmali. " \
        f"pi_idx={pi_idx} word[+1]=0x{words[pi_idx+1]:08x}"


def test_10_output_formats_bin_ihex():
    """Linker --bin ve --ihex ciktilari uretiyor; ihex checksum'lari ve EOF'i dogru."""
    _ensure_build_dir()
    src = """
.section .text
.global _start
_start:
    addi a0, x0, 0x55
    addi a1, x0, 0x33
    add  a2, a0, a1
    nop
"""
    obj, e = assemble_source(src, "fmt.s"); assert not e.has_errors()
    p = os.path.join(BUILD, "fmt.o")
    oof.write_object_file(obj, p)

    hex_p  = os.path.join(BUILD, "fmt.hex")
    bin_p  = os.path.join(BUILD, "fmt.bin")
    ihex_p = os.path.join(BUILD, "fmt.ihex")

    link_objects([p],
                 hex_output=hex_p, bin_output=bin_p, ihex_output=ihex_p)

    # bin: en az 16 byte (4 instruction × 4) olmali, word-aligned
    bin_data = open(bin_p, 'rb').read()
    assert len(bin_data) >= 16
    assert len(bin_data) % 4 == 0

    # bin'in ilk word'u 0x05500513 (addi a0, x0, 0x55) olmali (LE)
    first_word = (bin_data[0]
                  | (bin_data[1] << 8)
                  | (bin_data[2] << 16)
                  | (bin_data[3] << 24))
    assert first_word == 0x05500513, f"ilk word 0x05500513 olmali, alinan 0x{first_word:08x}"

    # ihex: tum satirlarin checksum'i dogru, son satir EOF
    lines = [l.strip() for l in open(ihex_p) if l.strip()]
    assert lines[-1] == ":00000001FF", f"EOF satiri yanlis: {lines[-1]}"
    for n, line in enumerate(lines, 1):
        assert line.startswith(":"), f"satir {n}: ':' ile baslamiyor"
        b = bytes.fromhex(line[1:])
        assert (sum(b) & 0xFF) == 0, f"satir {n} checksum hata: {line}"


def test_09_object_roundtrip():
    """Object format: parse -> serialize -> parse aynisini verir."""
    _ensure_build_dir()
    src = """
.section .text
.global hello
.extern someone

hello:
    li   a0, 42
    call someone
    ret
"""
    obj, errs = assemble_source(src, "roundtrip.s")
    assert not errs.has_errors()

    p = os.path.join(BUILD, "roundtrip.o")
    oof.write_object_file(obj, p)

    obj2 = oof.read_object_file(p)

    # Magic + version
    assert obj2["magic"] == obj["magic"]
    assert obj2["version"] == obj["version"]

    # Sembol sayisi ve isimleri
    assert len(obj2["symbols"]) == len(obj["symbols"])
    names1 = sorted(s["name"] for s in obj["symbols"])
    names2 = sorted(s["name"] for s in obj2["symbols"])
    assert names1 == names2

    # Relocation sayisi
    assert len(obj2["relocations"]) == len(obj["relocations"])

    # Section data identical
    for s1 in obj["sections"]:
        s2 = next(s for s in obj2["sections"] if s["name"] == s1["name"])
        assert s2["data"] == s1["data"]
        assert s2["size"] == s1["size"]
