#!/usr/bin/env python3
# ============================================================
# host_send.py - PC tarafi seri yukleyici (host application)
# ============================================================
# 3. Proje: FPGA tabanli Loader.
#
# Gorevi:
#   1) linker'in urettigi makine kodunu (.bin ham ikili veya .hex)
#      okur,
#   2) kucuk paketlere boler, her paketin sonuna CRC-16 ekler,
#   3) Tang Nano 9K'ya USB seri port (onboard BL702 UART) uzerinden
#      gonderir,
#   4) FPGA'deki Loader FSM'inden ACK/NAK bekler, NAK gelirse paketi
#      tekrar gonderir (veri kaybini kesin onlemek icin),
#   5) tum program yazildiktan sonra RUN komutu gonderir; FPGA
#      islemciyi reset'ten birakir ve program FPGA uzerinde calisir,
#   6) yukleme suresini olcup yazar (rapor "Analiz" bolumu icin).
#
# Kullanim:
#   python3 host/host_send.py --port /dev/ttyUSB1 --file build/test1.bin
#   python3 host/host_send.py --port COM5 --file build/test1.hex --chunk 32
#
# Protokol (host -> FPGA):
#   WRITE : 0x7E 0x01 ADDR_L ADDR_H NWORDS <NWORDS*4 bayt veri> CRC_H CRC_L
#   RUN   : 0x7E 0x02 CRC_H CRC_L
#   ADDR  : word (4 bayt) adres, kucuk-endian (0..2047)
#   CRC   : CMD'den veri sonuna kadarki tum baytlar uzerinden CRC-16/CCITT
# FPGA yaniti: 0x79 = ACK (CRC dogru) / 0x6E = NAK (CRC yanlis)
# ============================================================

import sys
import time
import argparse

# NOT: pyserial sadece gercek seri-port gonderiminde gereklidir.
# Simulasyon (--emit-frames) modunda gerekmez, bu yuzden import
# asagida (seri gonderim dalinda) tembel olarak yapilir.


# ---- Protokol sabitleri (FPGA tarafiyla AYNI olmali) ----
SYNC = 0x7E
CMD_WRITE = 0x01
CMD_RUN = 0x02
ACK = 0x79   # 'y'
NAK = 0x6E   # 'n'


def crc16_ccitt(data):
    """CRC-16/CCITT-FALSE hesaplar.

    poly = 0x1021, baslangic = 0xFFFF, yansima yok.
    FPGA'deki crc16 modulu ile birebir ayni algoritma.
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= (byte << 8)          # baytI ust 8 bite XOR'la
        for _ in range(8):          # 8 bit kaydir
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


def load_words(path):
    """Program kodunu 32-bit word listesi olarak okur.

    .bin  -> ham ikili (kucuk-endian, linker --bin ciktisi)
    .hex  -> her satirda bir 32-bit word, hex (linker $readmemh ciktisi)
    """
    words = []
    if path.endswith(".hex"):
        # $readmemh formati: her satirda bir 8 haneli hex word
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line == "" or line.startswith("//") or line.startswith("@"):
                    continue
                words.append(int(line, 16) & 0xFFFFFFFF)
    else:
        # ham .bin: 4'er bayt oku, kucuk-endian word yap
        with open(path, "rb") as f:
            raw = f.read()
        # 4'un kati degilse sona sifir bayt ekle (hizalama)
        while len(raw) % 4 != 0:
            raw += b"\x00"
        for i in range(0, len(raw), 4):
            w = raw[i] | (raw[i+1] << 8) | (raw[i+2] << 16) | (raw[i+3] << 24)
            words.append(w)
    return words


def make_write_frame(word_addr, words):
    """Bir WRITE paketi (bytearray) olusturur."""
    body = bytearray()
    body.append(CMD_WRITE)
    body.append(word_addr & 0xFF)         # ADDR_L
    body.append((word_addr >> 8) & 0xFF)  # ADDR_H
    body.append(len(words) & 0xFF)        # NWORDS
    for w in words:                       # veri (her word 4 bayt, LE)
        body.append(w & 0xFF)
        body.append((w >> 8) & 0xFF)
        body.append((w >> 16) & 0xFF)
        body.append((w >> 24) & 0xFF)
    crc = crc16_ccitt(body)
    frame = bytearray([SYNC]) + body
    frame.append((crc >> 8) & 0xFF)       # CRC_H
    frame.append(crc & 0xFF)              # CRC_L
    return frame


def make_run_frame():
    """RUN paketi olusturur (islemciyi baslat)."""
    body = bytearray([CMD_RUN])
    crc = crc16_ccitt(body)
    return bytearray([SYNC]) + body + bytearray([(crc >> 8) & 0xFF, crc & 0xFF])


def send_with_ack(ser, frame, retries=5, name=""):
    """Cerceveyi gonderir, ACK bekler; NAK/timeout olursa tekrar dener."""
    for attempt in range(1, retries + 1):
        ser.reset_input_buffer()
        ser.write(frame)
        ser.flush()
        resp = ser.read(1)              # 1 bayt yanit bekle (timeout'lu)
        if len(resp) == 1 and resp[0] == ACK:
            return True
        print(f"  [{name}] dene {attempt}/{retries}: "
              f"yanit={'NAK' if (resp and resp[0]==NAK) else 'timeout'}, tekrar...")
    return False


def main():
    ap = argparse.ArgumentParser(description="FPGA Loader - PC tarafi gonderici")
    ap.add_argument("--port", default=None, help="seri port (orn /dev/ttyUSB1 veya COM5)")
    ap.add_argument("--file", required=True, help="program dosyasi (.bin veya .hex)")
    ap.add_argument("--baud", type=int, default=115200, help="baud (default 115200)")
    ap.add_argument("--addr", type=lambda x: int(x, 0), default=0,
                    help="baslangic word adresi (default 0)")
    ap.add_argument("--chunk", type=int, default=32,
                    help="paket basina word sayisi (default 32)")
    ap.add_argument("--timeout", type=float, default=2.0, help="ACK timeout (s)")
    ap.add_argument("--listen", type=float, default=None,
                    help="RUN sonrasi UART'i bu kadar saniye dinle, sonra cik (otomatik test icin)")
    ap.add_argument("--emit-frames", default=None,
                    help="seri port yerine tum cerceve baytlarini bu dosyaya yaz "
                         "(simulasyon icin; her satirda bir hex bayt)")
    args = ap.parse_args()

    words = load_words(args.file)
    total_bytes = len(words) * 4
    print(f"[host] {args.file}: {len(words)} word ({total_bytes} bayt) okundu")

    # ---- Simulasyon modu: cerceveleri dosyaya yaz, seri port acma ----
    # Bicim: her cerceve icin once bayt sayisi, sonra o kadar hex bayt.
    # Boylece testbench her cerceveyi gonderip ACK bekleyebilir
    # (gercek host_send davranisi ile ayni el sikisma).
    if args.emit_frames:
        frames = []
        addr = args.addr
        i = 0
        while i < len(words):
            block = words[i:i + args.chunk]
            frames.append(make_write_frame(addr, block))
            addr += len(block)
            i += args.chunk
        frames.append(make_run_frame())

        with open(args.emit_frames, "w") as f:
            for fr in frames:
                f.write("%d\n" % len(fr))      # cerceve uzunlugu
                for b in fr:
                    f.write("%02x\n" % b)       # cerceve baytlari
        total = sum(len(fr) for fr in frames)
        print(f"[host] {len(frames)} cerceve, {total} bayt -> {args.emit_frames} "
              f"(simulasyon icin)")
        return

    if not args.port:
        print("HATA: --port gerekli (veya simulasyon icin --emit-frames kullan).")
        sys.exit(1)
    try:
        import serial  # pyserial (sadece gercek gonderim icin)
    except ImportError:
        print("HATA: pyserial kurulu degil. Kur: pip install pyserial")
        sys.exit(1)
    print(f"[host] port={args.port} baud={args.baud} chunk={args.chunk} word/paket")

    ser = serial.Serial(args.port, args.baud, timeout=args.timeout)
    time.sleep(0.2)  # port acilsin

    t0 = time.time()
    addr = args.addr
    pkt_no = 0
    i = 0
    while i < len(words):
        block = words[i:i + args.chunk]
        frame = make_write_frame(addr, block)
        pkt_no += 1
        if not send_with_ack(ser, frame, name=f"WRITE#{pkt_no}@{addr}"):
            print(f"HATA: WRITE paketi {pkt_no} icin ACK alinamadi. Cikiliyor.")
            ser.close()
            sys.exit(2)
        addr += len(block)
        i += args.chunk

    # tum veri yazildi -> RUN
    if not send_with_ack(ser, make_run_frame(), name="RUN"):
        print("HATA: RUN icin ACK alinamadi.")
        ser.close()
        sys.exit(3)

    t1 = time.time()
    dt = t1 - t0
    print(f"[host] Yukleme TAMAM. {pkt_no} paket, {total_bytes} bayt, "
          f"{dt*1000:.1f} ms, {total_bytes/dt/1024:.2f} KB/s")
    print("[host] Islemci reset'ten birakildi, program FPGA'de calisiyor.")

    # RUN sonrasi: program UART'a bir sey basarsa burada okuyup gosterelim
    if args.listen is not None:
        print(f"[host] Program UART ciktisi ({args.listen}s dinleniyor):")
        t_end = time.time() + args.listen
        while time.time() < t_end:
            data = ser.read(64)
            if data:
                sys.stdout.write(data.decode("latin-1"))
                sys.stdout.flush()
        print("\n[host] dinleme bitti.")
    else:
        print("[host] Program UART ciktisi (Ctrl+C ile cik):")
        try:
            while True:
                data = ser.read(64)
                if data:
                    sys.stdout.write(data.decode("latin-1"))
                    sys.stdout.flush()
        except KeyboardInterrupt:
            pass
    ser.close()


if __name__ == "__main__":
    main()
