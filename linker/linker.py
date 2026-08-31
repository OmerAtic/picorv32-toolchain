# ============================================================
# linker/linker.py - PicoRV32 Linker (Pass 1 + Pass 2)
# ============================================================
# Birden fazla .o (PCO v1) dosyasini okur, bir bellek imaji uretir.
#
# PASS 1 - Layout & Sembol Toplama:
#   - .o dosyalarini magic dogrula
#   - Linker script'ten memory bolgelerini al
#   - Her output section icin: input section'lari hizalayarak yerlestir
#   - Memory tasma kontrolu
#   - Global sembolleri topla (ayni isim iki kez = MULTIPLE_DEFINITION)
#   - Entry point sec (_start > start > 0)
#
# PASS 2 - Relocation:
#   - Image olustur (linker script'in en buyuk memory bolgesi kadar)
#   - Tum input section bytes'larini uygun adreslere yerlestir
#   - Her relocation'i tipine gore patchle
#   - Relocation hata kontrolu (UNDEFINED_REFERENCE, range overflow)
# ============================================================

import os
from datetime import datetime

from assembler import obj_format as oof
from linker import script as ld_script
from linker import reloc as ld_reloc


class LinkError(Exception):
    """Linker hatalari icin ozel exception."""
    pass


def _align_up(value, align):
    if align <= 1:
        return value
    return ((value + align - 1) // align) * align


# ============================================================
# Pass 1: Layout
# ============================================================

class LinkContext:
    """Bir link kosmasinin durumu."""

    def __init__(self, script):
        self.script = script

        # Memory bolgesinin mevcut "cursor" pozisyonu (yerlestirme cursor'u)
        # name -> next free address (origin'den baslar)
        self.mem_cursor = {}
        for m in script["memory"]:
            self.mem_cursor[m["name"]] = m["origin"]

        # Object'ler: liste of {filename, obj, section_addrs: {sec_name -> final_addr}}
        self.objects = []

        # Global sembol tablosu: name -> {addr, src_object, section}
        self.global_table = {}

        # Local sembol cozumu icin: input_obj_index -> {name -> addr}
        self.local_tables = []

        # Output section bilgisi (rapor icin)
        # name -> [{addr, size, source_file}]
        self.output_sections = {}


def _pass1_layout(objects, script):
    """Tum input objects icin nihai adresleri hesapla.

    Args:
        objects: [(filepath, obj_dict)] listesi
        script:  loaded linker script

    Returns: LinkContext
    """
    ctx = LinkContext(script)

    # Output section sirasi: script'teki sira (.text once, sonra .data)
    output_section_names = [s["name"] for s in script["sections"]]

    # Once tum objelerin section_addrs'lerini hazirla
    for filepath, obj in objects:
        ctx.objects.append({
            "filename": filepath,
            "obj":      obj,
            "section_addrs": {},
        })
        ctx.local_tables.append({})
        ctx.output_sections.setdefault("__init__", None)

    # Bos output_sections sozlugunu hazirla
    for name in output_section_names:
        ctx.output_sections[name] = []

    # Her output section icin: tum input'ları sirayla yerlestir
    for out_name in output_section_names:
        # Bu output section hangi memory'ye gidecek?
        mem_name = ld_script.get_section_memory(script, out_name)
        if mem_name is None:
            continue
        section_align = ld_script.get_section_align(script, out_name)

        # Bu output section'in baslangic adresi = memory cursor (align ile)
        cur = _align_up(ctx.mem_cursor[mem_name], section_align)

        for entry in ctx.objects:
            obj = entry["obj"]
            input_sec = None
            for s in obj["sections"]:
                if s["name"] == out_name:
                    input_sec = s
                    break
            if input_sec is None:
                continue

            # Bu input section'in nihai adresi (input'un kendi alignment'i)
            in_align = max(section_align, input_sec.get("align", 1))
            cur = _align_up(cur, in_align)

            entry["section_addrs"][out_name] = cur

            # Output section listesi (rapor icin)
            ctx.output_sections[out_name].append({
                "addr":   cur,
                "size":   input_sec["size"],
                "source": entry["filename"],
            })

            cur += input_sec["size"]

        # Memory cursor'i guncelle
        ctx.mem_cursor[mem_name] = cur

        # Memory tasma kontrolu
        mem = ld_script.get_memory(script, mem_name)
        end_addr = mem["origin"] + mem["length"]
        if cur > end_addr:
            raise LinkError(
                f"Memory '{mem_name}' tasildi: kullanilan {cur} > "
                f"sinir {end_addr} (length={mem['length']})"
            )

    return ctx


def _pass1_symbols(ctx):
    """Tum sembolleri tabloya doldur. Multiple definition'i hata olarak isaretler."""
    for idx, entry in enumerate(ctx.objects):
        obj = entry["obj"]
        section_addrs = entry["section_addrs"]
        local_tbl = ctx.local_tables[idx]

        for sym in obj["symbols"]:
            name    = sym["name"]
            sec     = sym["section"]
            value   = sym["value"]
            binding = sym["binding"]

            if binding == oof.BIND_EXTERN:
                # Cozumu daha sonra global_table'dan
                continue

            if sec not in section_addrs:
                # Sembol bilinmeyen section'da (boylesi olmamali)
                # Yine de yerel tabloya ekle, ama adres 0
                addr = 0
            else:
                addr = section_addrs[sec] + value

            # Yerel tabloya ekle (ayni isim ayni dosyada zaten kontrol edildi)
            local_tbl[name] = addr

            if binding == oof.BIND_GLOBAL:
                if name in ctx.global_table:
                    prev = ctx.global_table[name]
                    raise LinkError(
                        f"MULTIPLE_DEFINITION: '{name}' hem "
                        f"{prev['src_object']} hem {entry['filename']} "
                        f"icinde tanimli"
                    )
                ctx.global_table[name] = {
                    "addr":       addr,
                    "src_object": entry["filename"],
                    "section":    sec,
                }


# ============================================================
# Pass 2: Image olustur + Relocation
# ============================================================

def _build_image(ctx):
    """Tum sectionlari birlestirip bellek imajini olustur (en buyuk memory bolgesi kadar).

    Returns: (image_bytearray, image_origin)
        Eger birden fazla memory bolgesi varsa, sadece ilkini kullanir.
    """
    mem = ctx.script["memory"][0]
    origin = mem["origin"]
    length = mem["length"]
    image = bytearray(length)  # tum sifir baslar

    # Her input'un section bytes'larini ilgili adreslere yerlestir
    for entry in ctx.objects:
        obj = entry["obj"]
        for sec in obj["sections"]:
            name = sec["name"]
            if name not in entry["section_addrs"]:
                continue
            addr = entry["section_addrs"][name]
            data = oof.hex_to_bytes(sec["data"])
            # Image icindeki indeks
            idx = addr - origin
            if idx < 0 or idx + len(data) > length:
                raise LinkError(
                    f"Section '{name}' adres aralik disi: addr={addr}"
                )
            image[idx:idx + len(data)] = data

    return image, origin


def _resolve_symbol(name, ctx, in_obj_idx):
    """Bir sembol referansini cozer.

    Once dosya-yerel arar, sonra global'lere bakar.
    Bulamazsa LinkError atar.
    """
    local = ctx.local_tables[in_obj_idx]
    if name in local:
        return local[name]
    if name in ctx.global_table:
        return ctx.global_table[name]["addr"]
    raise LinkError(f"UNDEFINED_REFERENCE: '{name}'")


def _apply_relocations(image, image_origin, ctx):
    """Tum input objelerin relocations'larini uygular."""
    for idx, entry in enumerate(ctx.objects):
        obj = entry["obj"]
        section_addrs = entry["section_addrs"]

        for rel in obj["relocations"]:
            sec_name = rel["section"]
            offset   = rel["offset"]
            rtype    = rel["type"]
            sym_name = rel["symbol"]
            addend   = rel.get("addend", 0)
            line     = rel.get("line", 0)

            if sec_name not in section_addrs:
                raise LinkError(
                    f"Reloc section bulunamadi: {entry['filename']}:{line}  "
                    f"section='{sec_name}'"
                )

            instr_addr = section_addrs[sec_name] + offset

            try:
                sym_addr = _resolve_symbol(sym_name, ctx, idx)
            except LinkError as e:
                raise LinkError(
                    f"{entry['filename']}:{line}  "
                    f"{rtype} -> {e}"
                )

            target = sym_addr + addend
            instr_image_idx = instr_addr - image_origin

            try:
                ld_reloc.apply_reloc(image, rtype, instr_image_idx, target)
            except ld_reloc.RelocError as e:
                raise LinkError(
                    f"{entry['filename']}:{line}  "
                    f"{rtype} '{sym_name}' patch hatasi: {e}"
                )


# ============================================================
# Entry point
# ============================================================

def _find_entry(ctx):
    """Entry point'i bul: _start > start > linker script default."""
    for candidate in ("_start", "start"):
        if candidate in ctx.global_table:
            return ctx.global_table[candidate]["addr"]
    return ctx.script.get("entry", 0)


# ============================================================
# Cikti formatlari: HEX ve MAP
# ============================================================

def write_hex(image, image_origin, entry, hex_path):
    """Verilog $readmemh formatinda hex dosyasi yazar.

    Her satir 32-bit word (8 hex char). Yorum satirlari // ile baslar.
    """
    word_count = len(image) // 4
    last_nonzero = 0
    for i in range(word_count - 1, -1, -1):
        word = (image[i*4] | (image[i*4+1] << 8)
                | (image[i*4+2] << 16) | (image[i*4+3] << 24))
        if word != 0:
            last_nonzero = i + 1
            break
    output_words = max(last_nonzero, 1)

    with open(hex_path, 'w', encoding='utf-8') as f:
        f.write(f"// PicoRV32 linker output\n")
        f.write(f"// Entry point: 0x{entry:08x}\n")
        f.write(f"// Image:       0x{image_origin:08x} .. "
                f"0x{image_origin + output_words*4 - 1:08x}\n")
        f.write(f"// Words:       {output_words}\n")
        f.write("//\n")
        for i in range(output_words):
            word = (image[i*4]
                    | (image[i*4+1] << 8)
                    | (image[i*4+2] << 16)
                    | (image[i*4+3] << 24))
            f.write(f"{word:08x}\n")


def _trimmed_image_size(image):
    """Image'in trailing zero'larini kestiginde kalan boyutu (4'un kati) doner."""
    last_nonzero = 0
    for i in range(len(image) - 1, -1, -1):
        if image[i] != 0:
            last_nonzero = i + 1
            break
    # 4 byte'a yuvarla (word align)
    if last_nonzero == 0:
        return 4
    if last_nonzero % 4 != 0:
        last_nonzero += 4 - (last_nonzero % 4)
    return last_nonzero


def write_bin(image, image_origin, bin_path):
    """Image'in dolu kismini raw binary olarak yazar (LE byte order korunur)."""
    n = _trimmed_image_size(image)
    with open(bin_path, 'wb') as f:
        f.write(bytes(image[:n]))


def _ihex_record(byte_count, addr16, rec_type, payload):
    """Bir Intel HEX kaydini (string + cr/lf hariq) olusturur."""
    record = bytearray()
    record.append(byte_count & 0xFF)
    record.append((addr16 >> 8) & 0xFF)
    record.append(addr16 & 0xFF)
    record.append(rec_type & 0xFF)
    record.extend(payload)
    checksum = (-sum(record)) & 0xFF
    return ":" + record.hex().upper() + f"{checksum:02X}"


def write_ihex(image, image_origin, ihex_path):
    """Intel HEX (I8HEX/I32HEX) formatinda yazar.

    Bir veriyi 16 byte/satir olarak ciktilar. Type 04 (Extended Linear Address)
    ile 64 KB segmentleri yonetir. EOF: type 01.
    """
    n = _trimmed_image_size(image)
    BYTES_PER_LINE = 16

    with open(ihex_path, 'w', encoding='ascii') as f:
        last_segment = -1

        for i in range(0, n, BYTES_PER_LINE):
            chunk = bytes(image[i:i + BYTES_PER_LINE])
            abs_addr = image_origin + i
            segment  = (abs_addr >> 16) & 0xFFFF
            addr16   = abs_addr & 0xFFFF

            # Yeni 64 KB segmentine girdik mi?
            if segment != last_segment:
                ext_payload = bytes([(segment >> 8) & 0xFF, segment & 0xFF])
                f.write(_ihex_record(2, 0x0000, 0x04, ext_payload) + "\n")
                last_segment = segment

            # Veri kaydi (type 00)
            f.write(_ihex_record(len(chunk), addr16, 0x00, chunk) + "\n")

        # EOF (type 01)
        f.write(":00000001FF\n")


def write_map(ctx, entry, map_path):
    """Linker map dosyasi (text formati)."""
    with open(map_path, 'w', encoding='utf-8') as f:
        f.write("# PicoRV32 Linker Map\n")
        f.write(f"# Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")

        # Memory regions
        f.write("## Memory Regions\n")
        for m in ctx.script["memory"]:
            f.write(f"  {m['name']:<8} 0x{m['origin']:08x} .. "
                    f"0x{m['origin'] + m['length'] - 1:08x}  "
                    f"({m['length']} bytes, {m.get('attrs', '-')})\n")

        # Section layout
        f.write("\n## Section Layout\n")
        for out_name, entries in ctx.output_sections.items():
            if out_name == "__init__" or not entries:
                continue
            mem_name = ld_script.get_section_memory(ctx.script, out_name)
            f.write(f"  {out_name}  (mem={mem_name})\n")
            for e in entries:
                f.write(f"    0x{e['addr']:08x}  size={e['size']:<6}B   "
                        f"{os.path.basename(e['source'])}\n")

        # Global symbols
        f.write("\n## Global Symbols\n")
        for name, info in sorted(ctx.global_table.items(),
                                 key=lambda kv: kv[1]['addr']):
            f.write(f"  0x{info['addr']:08x}  {name:<24} "
                    f"[{info['section']}]   "
                    f"{os.path.basename(info['src_object'])}\n")

        # Entry
        f.write("\n## Entry Point\n")
        f.write(f"  0x{entry:08x}\n")


# ============================================================
# Public API
# ============================================================

def link_objects(object_paths, script_path=None,
                 hex_output=None, map_output=None,
                 bin_output=None, ihex_output=None):
    """Bir veya daha fazla .o dosyasini linkler.

    Args:
        object_paths: list of .o dosya yollari
        script_path:  linker script JSON yolu (None ise default)
        hex_output:   Verilog $readmemh dosyasi (None ise yazma)
        map_output:   memory map dosyasi (None ise yazma)

    Returns:
        {
          "image":         bytearray,
          "image_origin":  int,
          "entry":         int,
          "global_table":  dict,
          "ctx":           LinkContext,
        }

    Raises:
        LinkError: link hatalari
    """
    if not object_paths:
        raise LinkError("Hicbir input .o dosyasi verilmedi")

    # Linker script yukle
    script = ld_script.load_script(script_path)

    # Tum object'leri yukle
    objects = []
    for path in object_paths:
        obj = oof.read_object_file(path)
        objects.append((path, obj))

    # PASS 1: layout + symbols
    ctx = _pass1_layout(objects, script)
    _pass1_symbols(ctx)

    # PASS 2: image build + relocations
    image, image_origin = _build_image(ctx)
    _apply_relocations(image, image_origin, ctx)

    entry = _find_entry(ctx)

    # Cikti dosyalari
    if hex_output is not None:
        write_hex(image, image_origin, entry, hex_output)
    if map_output is not None:
        write_map(ctx, entry, map_output)
    if bin_output is not None:
        write_bin(image, image_origin, bin_output)
    if ihex_output is not None:
        write_ihex(image, image_origin, ihex_output)

    return {
        "image":        image,
        "image_origin": image_origin,
        "entry":        entry,
        "global_table": ctx.global_table,
        "ctx":          ctx,
    }
