import json
from pathlib import Path
import qrcode
from PIL import Image
out=Path('test_images'); out.mkdir(exist_ok=True)
payloads={'ascii':'QR Screen Reader','japanese':'日本語のQRコード：なぎ 🎸','url':'https://example.com/path?q=hello#qr','multiline':'1行目\n2行目\r\n3行目','long':'a'*1200,'controls':'tab\tend\x00control'}
for name,text in payloads.items():
    im=qrcode.make(text).convert('RGB'); im.save(out/f'{name}.png')
    if name=='japanese':
        for ext in ('jpg','bmp','webp'): im.save(out/f'{name}.{ext}')
Image.new('RGB',(240,240),'white').save(out/'no_qr.png')
qrcode.make(b'\xff\xfe\x80\x00').save(out/'binary.png')
(out/'expected.json').write_text(json.dumps(payloads,ensure_ascii=False,indent=2),encoding='utf-8')
