import json,time
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from core import decode
expected=json.loads(Path('test_images/expected.json').read_text(encoding='utf-8'))
rows=[]
for name,text in expected.items():
    image=Image.open(f'test_images/{name}.png').convert('RGB')
    t=time.perf_counter(); result=decode(image); zx=time.perf_counter()-t
    t=time.perf_counter()
    try:
        value,_,_=cv2.QRCodeDetector().detectAndDecode(np.asarray(image)); ok=value==text
    except Exception:
        ok=False
    cv=time.perf_counter()-t
    rows.append({'sample':name,'zxing_exact':result.text==text,'opencv_exact':ok,'zxing_ms':round(zx*1000,2),'opencv_ms':round(cv*1000,2)})
Path('decoder_comparison.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(rows,indent=2))
