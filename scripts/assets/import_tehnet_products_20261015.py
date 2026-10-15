#!/usr/bin/env python3
"""Prepare the user-requested static TehNet image collection. No website publishing.

Only the 23 reviewed source images are accepted. Changed source bytes, a changed
catalogue, missing files or edits outside the reviewed masks stop the import.
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import html
import io
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'assets/tehran-network/products/2026-10-15'
CACHE = ROOT / '.cache/tehnet-product-assets-20261015'
API = 'https://saieedshabake.ir/wp-json/wc/store/v1/products?per_page=100'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
EXPECTED_PRODUCTS = {18002,17991,17989,17982,17941,17935,17929,17927,17920,17888,17873,17871,17868,17866,17863,17860,17857,17855,17851,17831,17829,17827,17824,16585,16584}
EXPECTED_SHA = {
16602:'85dd4de82e92913577b3f61c2a8be4859b7b6a1b3e4c09ecc1ed0929082346de',
16605:'f68e4cf522b57a82f9d75f16580a9601e3ed30ebc3c6f1e369fe699f4315277f',
17852:'4695c03d8db785e3c9435b406a484e42e0749224ff8b44b173888d601545c42e',
17859:'15b41891aa75ca17e4c5d2e7505e68fe52ae74d9d2bb4e9430a46d4b0519ff71',
17864:'7b0356edfc40616185624e440f9776cf2f00d66e25055bc57b2dfbc3ee240260',
17869:'020a31d98c6df47ecf83568eb50a9c144d22866e49998085641ed255339b54aa',
17874:'ab1863c055bb66d8823ca06478594033f5414568ede9b4639b3624b05de8eddb',
17885:'328f394963fd456521664fc1cbb77b775bbe2f01da29f6f609e44601ccaa252d',
17917:'9bce2ca05ddc5909ed876cb28211c79541badc9a6b363d1580b36a0226048fc5',
17921:'4792fe02e7789590d7287ecc48fe22ddffcec0c27d0ebc3bfc91a722704c9d0f',
17922:'b1cac31686abec60daca9faae6832efb1d07c24f19684574259ade3aacd6245c',
17926:'4c69aba5c3985e284a5c609d19dc01d2ee46b97dccc9e6a3a79daa812a26fad5',
17930:'5d9a1a58e85af4d27a3951ba721f06aef1169dbad956f8ff9fb52eacb66cac1c',
17931:'558b905defd7bb7b507cd79bf93d5c6e161efa0b0b8bc498bc1b23bbf502eb37',
17937:'a7a9e2bd0683409d25484e0e11eb050a8b9c6d1773759e9e5b71be0547ae29af',
17943:'bb925d0c3989548e74abdbf308a5d2c9f45cc0d7ad27e17d518f70b94762cab9',
17945:'efbda3232f8082d0725c8a577042e24c1e41ab05da6b16b70451b13851a4b5e4',
17970:'d601c7cc1c1cd6967fdb551ab3964b2a24ef35e42299e5a87e221d50108e23e5',
17977:'a4b1d26b8aa160bd724de5c7774f4d109898ae94c5b6369bafe21dc5dec1ac83',
17987:'ab82eea17c2daaeb2e815a6f3f52b426fb045e838c4233250d307f8f584cbcc6',
17992:'4cf83fd97f812b1d0ef5c25844a10439f5194c7ba05a0b5d43cbe411c2ffa2a9',
17998:'4f5490263e977da1f07804e92f8ec51e443528c2c2baebfbb44068c12ea46671',
17999:'52019247f419567234562c9a28919d669962f68138d8f51b88d7f549203b68ad'}
POLYGONS = {
17999:[[(287,191),(755,191),(755,320),(287,320)]],
17998:[[(308,163),(740,163),(740,278),(308,278)]],
17992:[[(65,144),(970,144),(970,278),(65,278)]],
17977:[[(158,726),(880,726),(880,881),(158,881)]],
17987:[[(30,117),(994,117),(994,287),(30,287)]],
17943:[[(452,689),(983,812),(987,874),(448,753)]],
17945:[[(57,625),(985,821),(994,903),(57,700)]],
17937:[[(182,899),(975,765),(994,822),(198,970)]],
17931:[[(83,123),(968,123),(968,303),(83,303)]],
17930:[[(120,69),(1100,69),(1100,254),(120,254)]],
17926:[[(553,919),(1023,919),(1023,1007),(553,1007)]],
17922:[[(716,981),(1023,981),(1023,1023),(716,1023)]],
17921:[[(718,449),(947,523),(947,574),(718,494)]],
17917:[[(45,147),(1025,147),(1025,328),(45,328)]],
17970:[[(22,894),(1023,894),(1023,1002),(22,1002)]]}
PROTECT = {
17987:[[(234,244),(789,244),(797,247),(799,256),(799,807),(792,815),(236,817),(226,811),(223,794),(223,258),(226,249)]],
17917:[[(631,327),(637,299),(636,276),(646,244),(652,238),(698,233),(720,231),(738,233),(745,264),(755,303),(765,341),(817,801),(717,827),(446,733),(425,395),(531,344),(613,329)]]}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def get_bytes(url: str) -> bytes:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'saieedshabake.ir':
        raise ValueError('Unexpected source host')
    request = urllib.request.Request(urllib.parse.quote(url, safe=':/?&=%'), headers={'User-Agent':'TehNet-Product-Asset-Import/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                data = response.read(12_000_001)
            if len(data) > 12_000_000:
                raise ValueError('Unexpectedly large source')
            return data
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError('Download failed')

def make_mask(shape: tuple, polygons: list) -> np.ndarray:
    mask = np.zeros(shape[:2], np.uint8)
    for polygon in polygons:
        cv2.fillPoly(mask, [np.array(polygon,np.int32)], 255)
    return mask

def background_fill(rgb: np.ndarray, mask: np.ndarray, protect: np.ndarray, image_id: int) -> np.ndarray:
    """Blend sampled clean texture inside the manually reviewed label regions."""
    if not np.any(mask):
        return rgb.copy()
    h,w = mask.shape
    patches = {17977:(35,890,420,1010),17943:(25,670,145,755),17945:(20,830,170,980),17937:(15,845,165,995),17921:(25,625,145,745),17970:(22,737,154,862),17992:(30,380,200,620),17987:(25,365,170,585),17917:(35,332,410,412),17926:(300,800,500,980),17922:(530,977,700,1024)}
    x1,y1,x2,y2 = patches.get(image_id,(20,30,170,150))
    patch = rgb[y1:y2,x1:x2].astype(np.float32)
    grain = patch-cv2.GaussianBlur(patch,(0,0),3)
    grain = np.concatenate([grain,grain[:,::-1]],axis=1)
    grain = np.concatenate([grain,grain[::-1]],axis=0)
    tile = np.tile(grain,(math.ceil(h/grain.shape[0]),math.ceil(w/grain.shape[1]),1))[:h,:w]
    source = np.clip(128+tile,0,255).astype(np.uint8)
    if image_id in (17999,17998):
        dy = -135 if image_id == 17999 else -120
        source = cv2.warpAffine(rgb,np.float32([[1,0,0],[0,1,-dy]]),(w,h),borderMode=cv2.BORDER_REFLECT_101)
    elif image_id == 17931:
        source[123:304] = cv2.resize(rgb[0:113],(w,181),interpolation=cv2.INTER_LINEAR)
    elif image_id == 17930:
        source[69:255] = cv2.resize(rgb[0:68],(w,186),interpolation=cv2.INTER_LINEAR)
    elif image_id == 17917:
        source[:261] = rgb[:261]
        source[147:261] = rgb[10:124]
        base = np.median(rgb[338:420,30:420],axis=(0,1))
        source[261:] = np.clip(base+tile[261:],0,255).astype(np.uint8)
    destination = rgb.copy()
    if image_id == 17987:
        destination[protect>0] = [18,22,25]
    elif image_id == 17917:
        destination[protect>0] = [42,63,77]
    pad=32
    sm=cv2.copyMakeBorder(mask,pad,pad,pad,pad,cv2.BORDER_CONSTANT,value=0)
    sr=cv2.copyMakeBorder(source,pad,pad,pad,pad,cv2.BORDER_REFLECT_101)
    dst=cv2.copyMakeBorder(destination,pad,pad,pad,pad,cv2.BORDER_REFLECT_101)
    x,y,ww,hh=cv2.boundingRect(sm)
    restored=cv2.seamlessClone(sr,dst,sm,(x+ww//2,y+hh//2),cv2.NORMAL_CLONE)[pad:pad+h,pad:pad+w]
    result=rgb.copy()
    result[mask>0]=restored[mask>0]
    return result

def annotate(image: Image.Image) -> tuple:
    """Render the exact requested lowercase domain at native pixel dimensions."""
    w,h=image.size
    margin=max(15,round(min(w,h)*.027))
    fs=max(20,round(min(w,h)*.034))
    font=ImageFont.truetype(FONT,fs)
    layer=Image.new('RGBA',image.size)
    draw=ImageDraw.Draw(layer)
    box=draw.textbbox((0,0),'tehnet.ir',font=font)
    tw,th=box[2]-box[0],box[3]-box[1]
    px,py=round(fs*.55),round(fs*.4)
    bw,bh=tw+2*px,th+2*py
    left,top=w-margin-bw,margin
    draw.rounded_rectangle((left,top,left+bw,top+bh),radius=max(5,round(fs*.25)),fill=(13,18,24,213),outline=(224,230,235,120),width=1)
    draw.text((left+px,top+py-box[1]),'tehnet.ir',font=font,fill=(255,255,255,255))
    result=Image.alpha_composite(image.convert('RGBA'),layer).convert('RGB')
    return result,np.array(layer.getchannel('A'))>0,[left,top,left+bw+1,top+bh+1]

def process(record: dict) -> dict:
    image_id=record['image_id']
    data=get_bytes(record['source_url'])
    if digest(data)!=EXPECTED_SHA[image_id]:
        raise ValueError(f'Source bytes changed for image {image_id}; fresh visual review required')
    original=Image.open(io.BytesIO(data))
    original.load()
    rgb=np.asarray(original.convert('RGB'))
    mask=make_mask(rgb.shape,POLYGONS.get(image_id,[]))
    protect=make_mask(rgb.shape,PROTECT.get(image_id,[]))
    mask[protect>0]=0
    cleaned=background_fill(rgb,mask,protect,image_id)
    if image_id==17999:
        (CACHE/'cleaned-sample').mkdir(parents=True,exist_ok=True)
        Image.fromarray(cleaned).save(CACHE/'cleaned-sample/tehnet-17999.png')
    final,brand_mask,brand_box=annotate(Image.fromarray(cleaned))
    pixels=np.asarray(final)
    allowed=(mask>0)|brand_mask
    assert np.array_equal(pixels[~allowed],rgb[~allowed]),f'Pixels outside approved regions changed: {image_id}'
    assert np.array_equal(pixels[protect>0],rgb[protect>0]),f'Protected pixels changed: {image_id}'
    assert final.size==original.size
    name=f'tehnet-{image_id}'
    master=OUT/'masters'/f'{name}.png'
    webp=OUT/'webp'/f'{name}.webp'
    final.save(master,optimize=True)
    final.save(webp,'WEBP',quality=94,method=6)
    with Image.open(master) as check:
        assert np.array_equal(np.asarray(check),pixels)
    with Image.open(webp) as check:
        assert check.size==original.size
        check.load()
    result=dict(record,source_sha256=digest(data),width=original.width,height=original.height,
        master=str(master.relative_to(OUT)),webp=str(webp.relative_to(OUT)),
        master_sha256=digest(master.read_bytes()),webp_sha256=digest(webp.read_bytes()),
        brand_text='tehnet.ir',brand_box=brand_box,seller_mark_removed=bool(np.any(mask)),
        seller_mark_regions=POLYGONS.get(image_id,[]),unchanged_outside_edit_mask=True,
        editorial_status='prepared-for-human-review; not-published')
    if image_id in (17987,17917,17930):
        result['review_note']='Large background lettering was reconstructed; inspect remaining edge lighting before publication.'
    print(f'PASS image={image_id} native={original.size} seller_region={bool(np.any(mask))}',flush=True)
    return result

def write_json(path: Path,value) -> None:
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def write_gallery(images: list,products: list) -> None:
    font=ImageFont.truetype(FONT,18)
    for start in range(0,len(images),12):
        group=images[start:start+12]
        sheet=Image.new('RGB',(1320,math.ceil(len(group)/4)*365),'#e7e7e7')
        draw=ImageDraw.Draw(sheet)
        for k,record in enumerate(group):
            with Image.open(OUT/record['master']) as image:
                tile=ImageOps.contain(image,(320,320))
                x=(k%4)*330+(330-tile.width)//2
                y=(k//4)*365+5
                sheet.paste(tile,(x,y))
            draw.text(((k%4)*330+8,(k//4)*365+330),f"tehnet-{record['image_id']}",font=font,fill='black')
        sheet.save(OUT/f'preview-{start//12+1}.jpg',quality=93)
    rows=['# فهرست تصاویر ۲۵ محصول','', 'نام‌ها از کاتالوگ منبع ثبت شده‌اند و تأیید مستقل مشخصات فنی نیستند.','']
    for product in products:
        rows.extend([f"## {product['product_id']} — {product['name']}",''])
        for image in product['images']:
            rows.append(f"![{product['product_id']} / {image['position']}]({image['webp']})")
            rows.append(f"[PNG اصلی]({image['master']}) · [WebP]({image['webp']})")
        rows.append('')
    (OUT/'catalog.md').write_text('\n'.join(rows),encoding='utf-8')
    fa='''# تصاویر محصولات — tehnet.ir

مجموعهٔ ثابت تصاویر، به درخواست صریح کاربر در ۱۵ اکتبر ۲۰۲۶، در مخزن تولید محتوا ذخیره شده است. این پوشه اطلاعات runtime پنل نیست.

**۲۵ محصول، ۳۱ ارجاع تصویری، ۲۳ تصویر یکتا.** در ۱۵ تصویر ناحیهٔ نام فروشنده پاک‌سازی شد؛ روی هر ۲۳ تصویر عبارت دقیق `tehnet.ir` قرار گرفت. هشت تصویر دیگر فقط نشان جدید دریافت کردند.

## استفاده
- `masters/`: تعداد ۲۳ فایل PNG در ابعاد واقعی منبع، بدون برش یا بزرگ‌نمایی مصنوعی.
- `webp/`: تعداد ۲۳ فایل WebP برای مصرف وب.
- `catalog.md` و `products.json`: ارتباط همهٔ محصولات و تصاویر اصلی/گالری.
- `image-manifest.json` و `qa.json`: منبع، هش فایل‌ها، ابعاد و نتیجهٔ کنترل پیکسلی.

![پیش‌نمایش اول](preview-1.jpg)
![پیش‌نمایش دوم](preview-2.jpg)

[مشاهدهٔ فهرست همهٔ محصولات](catalog.md)

## کنترل و محدودیت
در نسخهٔ PNG، تمام پیکسل‌های بیرون از ناحیهٔ ترمیم پس‌زمینه و نشان جدید بدون تغییر حفظ شده‌اند. کنترل ابعاد، بازخوانی فایل‌ها، تطبیق SHA-256 منابع و پوشش کامل ۲۵ محصول انجام می‌شود. نسخهٔ WebP فشرده‌سازی تصویری دارد.

در تصاویر 17987، 17917 و 17930 نوشتهٔ بزرگ پس‌زمینه بازسازی شده است؛ نور لبه‌ها و ترمیم پس‌زمینه قبل از انتشار بازبینی شود. ترمیم، بازیابی قطعی جزئیات پنهان‌شدهٔ عکس اصلی نیست.

این فایل‌ها برای بازبینی انسانی آماده‌اند؛ هیچ انتشار روی سایت زنده یا شبکه‌های اجتماعی انجام نشده است. نام و مشخصات سازنده از روی کالا حذف نشده و ویژگی جدیدی برای کالا ادعا نشده است. منبع برای رهگیری در manifest حفظ شده؛ تغییر نشان، مجوز مالکیت یا استفادهٔ تازه‌ای برای تصاویر ایجاد نمی‌کند.
'''
    (OUT/'README.md').write_text(fa,encoding='utf-8')
    (OUT/'README.en.md').write_text('''# TehNet product images — 2026-10-15

Static assets saved to this repository at the user's explicit request; not panel runtime state.

25 products, 31 image references, 23 unique photographs; 15 seller-label regions retouched and the exact lowercase domain `tehnet.ir` added to all 23 photographs. Eight photographs only needed the new domain mark.

`masters/` contains 23 native-size lossless PNGs. `webp/` contains 23 web derivatives. `catalog.md` and `products.json` map every main/gallery image to its product. The image manifest records source URLs, source/output SHA-256 values, dimensions and edit regions. `qa.json` records count, decoding, dimension and pixel-preservation checks. Two contact sheets provide a visual overview.

No cropping or artificial upscaling. PNG pixels outside the reviewed background-retouch regions and new brand mark are exactly preserved; WebP uses lossy compression. Large background lettering in images 17987, 17917 and 17930 was reconstructed: inspect edge lighting before publishing. This does not claim exact recovery of previously obscured pixels.

Prepared for human review, not published to any live website or social account. Manufacturer markings remain; source product names are not independent verification of technical specifications. Source provenance is retained. Rebranding does not create new image ownership or usage rights.
''',encoding='utf-8')

def main() -> None:
    cv2.setNumThreads(1)
    if not Path(FONT).is_file():
        raise FileNotFoundError('DejaVu Sans is required for reproducible text rendering')
    raw=get_bytes(API)
    source=json.loads(raw)
    assert {p['id'] for p in source}==EXPECTED_PRODUCTS and len(source)==25,'Catalogue changed; review required'
    records={}
    for product in source:
        for position,image in enumerate(product.get('images',[]),1):
            image_id=image['id']
            record=records.setdefault(image_id,dict(image_id=image_id,source_url=image['src'],products=[]))
            assert record['source_url']==image['src'],'Conflicting image URLs'
            record['products'].append(dict(product_id=product['id'],position=position))
    assert set(records)==set(EXPECTED_SHA),'Image inventory changed; review required'
    assert sum(len(record['products']) for record in records.values())==31
    for sub in ('masters','webp'):
        (OUT/sub).mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        images=list(executor.map(process,records.values()))
    by_id={image['image_id']:image for image in images}
    products=[]
    for product in source:
        entries=[]
        for position,image in enumerate(product['images'],1):
            edited=by_id[image['id']]
            entries.append(dict(position=position,role='main' if position==1 else 'gallery',image_id=image['id'],master=edited['master'],webp=edited['webp']))
        products.append(dict(product_id=product['id'],name=html.unescape(product['name']),source_product_url=product['permalink'],images=entries))
    assert len(list((OUT/'masters').glob('*.png')))==23
    assert len(list((OUT/'webp').glob('*.webp')))==23
    assert all((OUT/image[k]).is_file() for image in images for k in ('master','webp'))
    qa=dict(status='PASS',collection_date='2026-10-15',brand='tehnet.ir',products=25,image_references=31,unique_images=23,
        seller_mark_regions_removed=sum(image['seller_mark_removed'] for image in images),png_files=23,webp_files=23,
        verified_source_hashes=23,verified_native_dimensions=23,verified_png_pixel_preservation=23,
        artificial_upscaling=False,cropping=False,live_publication=False,
        human_review_recommended=[17987,17917,17930],source_api_sha256=digest(raw),
        checks_scope='Technical file/mask checks; not a claim of pixel-perfect hidden-background recovery or product authenticity')
    assert qa['seller_mark_regions_removed']==15
    write_json(OUT/'image-manifest.json',images)
    write_json(OUT/'products.json',products)
    write_json(OUT/'qa.json',qa)
    write_gallery(images,products)
    print(json.dumps(qa,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    main()
