# app/utils/image_utils.py

import io, base64, requests, logging
from datetime import datetime
from dateutil import tz
from PIL import Image, ImageDraw, ImageEnhance

def _hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0,2,4))

def _create_enhanced_gradient(colors, size=(1080,1350)) -> bytes:
    w,h = size
    img = Image.new("RGB",(w,h))
    draw = ImageDraw.Draw(img)
    stops = [_hex_to_rgb(c) for c in colors]

    for y in range(h):
        pos = y/h
        if pos<=0.5: t=pos*2; sc,ec=stops[0],stops[1] if len(stops)>1 else stops[0]
        else: t=(pos-0.5)*2; sc,ec=stops[1] if len(stops)>1 else stops[0], stops[2] if len(stops)>2 else stops[-1]
        r=int(sc[0]+(ec[0]-sc[0])*t)
        g=int(sc[1]+(ec[1]-sc[1])*t)
        b=int(sc[2]+(ec[2]-sc[2])*t)
        draw.line([(0,y),(w,y)], fill=(r,g,b))

    # Enhance
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)
    buf = io.BytesIO()
    img.save(buf,format="JPEG",quality=92)
    return buf.getvalue()

def _image_to_data_uri(img_bytes: bytes) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(img_bytes).decode("ascii")

def _cover_resize(img: Image.Image, size=(1080,1350)):
    w,h=size; sw,sh=img.size
    scale=max(w/sw, h/sh)
    nw,nh=int(sw*scale), int(sh*scale)
    img=img.resize((nw,nh), Image.LANCZOS)
    left,top=(nw-w)//2,(nh-h)//2
    return img.crop((left,top,left+w,top+h))

def _process_background_image(urls, theme):
    for url in (urls or []):
        try:
            resp=requests.get(url,timeout=10)
            if resp.ok and resp.headers["content-type"].startswith("image/"):
                img=Image.open(io.BytesIO(resp.content)).convert("RGB")
                img=_cover_resize(img,(1080,1350))
                buf=io.BytesIO(); img.save(buf,format="JPEG",quality=90)
                return _image_to_data_uri(buf.getvalue())
        except Exception as e:
            logging.warning(f"failed {url}: {e}")
    # fallback
    return _image_to_data_uri(_create_enhanced_gradient(theme["gradient"]))

def _get_ist_timestamp():
    now=datetime.utcnow().replace(tzinfo=tz.UTC)
    ist=now.astimezone(tz.gettz("Asia/Kolkata"))
    return ist.strftime("%d %b %Y, %I:%M %p IST")

def _determine_headline_size(title: str):
    l=len(title)
    if l<50: return "h-xl"
    if l<70: return "h-lg"
    if l<90: return "h-md"
    return "h-sm"