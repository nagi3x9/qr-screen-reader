import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
import qrcode
from PIL import Image
from core import decode, safe_url, load_file, ReadError

PAYLOADS=['QR Screen Reader','日本語のQRコード：なぎ 🎸','https://example.com/path?q=hello#qr','1行目\n2行目\r\n3行目','a'*1200,'tab\tend\x00control']
@pytest.mark.parametrize('text',PAYLOADS)
def test_exact(text):
    result=decode(qrcode.make(text)); assert result.text==text; assert result.raw==text.encode('utf-8')
@pytest.mark.parametrize('extension',['png','jpg','bmp','webp'])
def test_files(tmp_path,extension):
    p=tmp_path/f'日本語画像.{extension}'; qrcode.make('日本語テスト').convert('RGB').save(p)
    assert decode(load_file(p)).text=='日本語テスト'
@pytest.mark.parametrize('url',['https://example.com','http://localhost:8000/x','https://例え.jp/テスト','https://[::1]/'])
def test_good_urls(url): assert safe_url(url)==url
@pytest.mark.parametrize('url',['javascript:alert(1)','file:///C:/x','data:text/plain,x','https://','https://x:99999','https://x\n','https://u:p@x','https://x\\evil','https://x/%0aX','https://bad_host/','https://-bad.com/','plain text'])
def test_bad_urls(url): assert safe_url(url) is None

def test_blank():
    with pytest.raises(ReadError): decode(Image.new('RGB',(200,200),'white'))
def test_corrupt_file(tmp_path):
    p=tmp_path/'broken.png'; p.write_bytes(b'not image')
    with pytest.raises(ReadError): load_file(p)
def test_multi():
    a=qrcode.make('one').convert('RGB'); b=qrcode.make('two').convert('RGB'); im=Image.new('RGB',(a.width+b.width+30,max(a.height,b.height)),'white'); im.paste(a,(0,0)); im.paste(b,(a.width+30,0))
    with pytest.raises(ReadError,match='複数'): decode(im)
def test_binary():
    # Bytes not valid text: ZXing emits escapes in Plain mode, which cannot round trip.
    with pytest.raises(ReadError): decode(qrcode.make(b'\xff\xfe\x80\x00'))
