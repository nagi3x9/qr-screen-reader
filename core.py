"""Offline QR decoding. No network, history or payload logging."""
from dataclasses import dataclass
from urllib.parse import urlsplit
import ipaddress
import re
import numpy as np
from PIL import Image, ImageOps
import zxingcpp

class ReadError(Exception):
    pass

@dataclass(frozen=True)
class Result:
    text: str
    raw: bytes
    url: str | None

def safe_url(text):
    if not text or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in text):
        return None
    if '\\' in text or re.search(r'%0[ad]', text, re.I):
        return None
    try:
        p = urlsplit(text)
        if p.scheme.lower() not in ('http', 'https') or not p.hostname or p.username is not None or p.password is not None:
            return None
        if p.port is not None and not 1 <= p.port <= 65535:
            return None
        host = p.hostname
        try:
            ipaddress.ip_address(host)
        except ValueError:
            ascii_host = host.encode('idna').decode('ascii')
            if len(ascii_host) > 253 or any(not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label) for label in ascii_host.rstrip('.').split('.')):
                return None
        return text
    except (ValueError, UnicodeError):
        return None

def exact_text(barcode):
    raw = bytes(barcode.bytes)
    # ZXing interprets explicit ECI/Kanji modes; require a lossless round trip.
    text = barcode.text
    if barcode.content_type == zxingcpp.ContentType.Binary:
        try:
            raw.decode('utf-8', errors='strict')
        except UnicodeError as exc:
            raise ReadError('バイナリデータのため文字列を正確に復元できませんでした。') from exc
    if '\ufffd' in text:
        raise ReadError('文字列を正確に復元できませんでした（置換文字を検出）。')
    for encoding in ('utf-8', 'shift_jis', 'iso-8859-1', 'utf-16-be', 'gb18030', 'big5'):
        try:
            if text.encode(encoding) == raw:
                return text, raw
        except UnicodeError:
            pass
    raise ReadError('文字コードを確認できず、文字列を正確に復元できませんでした。')

def decode(image):
    image = ImageOps.exif_transpose(image).convert('RGB')
    if image.width * image.height > 40_000_000:
        raise ReadError('画像が大きすぎます。40メガピクセル以下に切り出してください。')
    variants = [image]
    def scan(im):
        return zxingcpp.read_barcodes(np.asarray(im), formats=zxingcpp.BarcodeFormat.QRCode, text_mode=zxingcpp.TextMode.Plain)
    found = scan(image)
    if not found:
        gray = ImageOps.grayscale(image)
        padded = ImageOps.expand(gray, border=32, fill=255)
        for variant in (padded, ImageOps.autocontrast(padded), padded.resize((padded.width*2,padded.height*2)) if padded.width*padded.height < 4_000_000 else padded):
            found = scan(variant)
            if found:
                break
    if not found:
        raise ReadError('QRコードを読み取れませんでした。余白を含めて選択し直してください。')
    if len(found) > 1:
        raise ReadError('複数のQRコードが見つかりました。1つだけ選択してください。')
    text, raw = exact_text(found[0])
    return Result(text, raw, safe_url(text))

def load_file(path):
    try:
        with Image.open(path) as im:
            if im.width * im.height > 40_000_000:
                raise ReadError('画像が大きすぎます（上限40メガピクセル）。')
            im.load()
            return im.copy()
    except ReadError:
        raise
    except Exception as exc:
        raise ReadError('画像ファイルを読み込めませんでした。形式やファイルを確認してください。') from exc
