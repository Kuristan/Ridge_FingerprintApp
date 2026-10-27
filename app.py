from pathlib import Path
from io import BytesIO
import time
import warnings
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from processing import png, sample, enhance, degrade, metrics

ROOT = Path(__file__).resolve().parent
app = FastAPI(title='RidgeLab Local', version='1.0.0')
app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')
Image.MAX_IMAGE_PIXELS = 20_000_000

@app.get('/')
def home():
    return FileResponse(ROOT/'static/index.html')

@app.get('/api/sample')
def demo():
    return {'image': png(sample()), 'label': 'Synthetic ridge pattern — not a real fingerprint'}

@app.get('/api/health')
def health():
    return {'status': 'ok'}

@app.post('/api/preview')
async def preview(file: UploadFile = File(...)):
    data = await file.read(10*1024*1024+1)
    if len(data) > 10*1024*1024:
        raise HTTPException(413, 'Please use an image smaller than 10 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in ('PNG', 'JPEG', 'BMP', 'TIFF'):
                    raise ValueError('Unsupported image type.')
                pages = getattr(source, 'n_frames', 1)
                source.seek(0)
                im = ImageOps.exif_transpose(source).convert('RGBA')
                im = Image.alpha_composite(Image.new('RGBA', im.size, 'white'), im).convert('L')
                if min(im.size) < 64:
                    raise ValueError('Image must be at least 64 × 64 pixels.')
                width, height = im.size
                im.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
                return {'image': png(np.array(im)), 'width': width, 'height': height, 'pages': pages}
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise HTTPException(400, str(e) or 'Could not read image.')

@app.post('/api/process')
async def process(file: UploadFile = File(...), strength: float = Form(.5), method: str = Form('ridge'),
                  verify: bool = Form(False), noise: float = Form(20), degradation: str = Form('noise'), blur_sigma: float = Form(1.0),
                  crop_x: float = Form(0), crop_y: float = Form(0), crop_w: float = Form(1), crop_h: float = Form(1)):
    start = time.perf_counter()
    if method not in ('ridge', 'contrast', 'denoise', 'sharpen') or not 0 <= strength <= 1 or not 1 <= noise <= 60:
        raise HTTPException(422, 'Invalid processing settings.')
    if degradation not in ('noise', 'blur') or not .3 <= blur_sigma <= 3:
        raise HTTPException(422, 'Invalid degradation settings.')
    if not (0 <= crop_x < 1 and 0 <= crop_y < 1 and 0 < crop_w <= 1 and 0 < crop_h <= 1 and crop_x+crop_w <= 1.001 and crop_y+crop_h <= 1.001):
        raise HTTPException(422, 'Crop must stay inside the image.')
    data = await file.read(10*1024*1024+1)
    if len(data) > 10*1024*1024:
        raise HTTPException(413, 'Please use an image smaller than 10 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in ('PNG', 'JPEG', 'BMP', 'TIFF'):
                    raise ValueError('Unsupported image type.')
                im = ImageOps.exif_transpose(source).convert('RGBA')
                bg = Image.new('RGBA', im.size, 'white')
                im = Image.alpha_composite(bg, im).convert('L')
                w, h = im.size
                im = im.crop((round(crop_x*w), round(crop_y*h), round((crop_x+crop_w)*w), round((crop_y+crop_h)*h)))
                if min(im.size) < 64:
                    raise ValueError('Image or crop must be at least 64 × 64 pixels.')
                im.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
                gray = np.array(im)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise HTTPException(400, str(e) or 'Could not read image.')
    reference = gray.copy()
    if verify:
        gray = degrade(reference, noise, kind=degradation, blur_sigma=blur_sigma)
    output, stages, info = enhance(gray, strength, method)
    report = {'method': method, 'strength': strength, 'verification': verify, 'degradation': degradation if verify else None, 'blur_sigma': blur_sigma if verify and degradation == 'blur' else None, 'noise_sigma': noise if verify and degradation == 'noise' else None,
              'noise_seed': 17 if verify and degradation == 'noise' else None, 'width': gray.shape[1], 'height': gray.shape[0], **info,
              'warning': 'Candidate detection is heuristic. Inspect ridges for false joins and breaks. No identity matching is performed.'}
    if verify:
        report['baseline'] = metrics(reference, gray)
        report['enhanced'] = metrics(reference, output)
        report['delta_ssim'] = round(report['enhanced']['ssim']-report['baseline']['ssim'], 4)
    report['processing_seconds'] = round(time.perf_counter()-start, 3)
    return {'input': png(gray), 'output': png(output), 'reference': png(reference) if verify else None,
            'stages': {k: png(v) for k, v in stages.items()}, 'report': report}
