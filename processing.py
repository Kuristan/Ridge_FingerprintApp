"""Deterministic DSP, without trained models. Candidate segmentation is heuristic."""
import base64
import cv2
import numpy as np
from skimage.metrics import structural_similarity, peak_signal_noise_ratio


def png(image):
    ok, encoded = cv2.imencode('.png', image)
    if not ok:
        raise ValueError('Could not encode image.')
    return 'data:image/png;base64,' + base64.b64encode(encoded).decode()


def sample():
    y, x = np.mgrid[-1:1:384j, -1:1:384j]
    phase = 2*np.pi*(24*np.sqrt((x+.12)**2 + (.75*y)**2 + .06) + 1.2*y)
    envelope = ((x/.82)**2+(y/.94)**2 < 1)
    return np.where(envelope, 145+85*np.cos(phase), 245).astype('uint8')


def structure(gray):
    f = gray.astype('float32')/255
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
    xx, yy, xy = [cv2.GaussianBlur(a, (0, 0), 4) for a in (gx*gx, gy*gy, gx*gy)]
    coherence = np.sqrt((xx-yy)**2+4*xy*xy)/(xx+yy+1e-6)
    normal = .5*np.arctan2(2*xy, xx-yy)
    mean = cv2.blur(f, (17, 17))
    std = np.sqrt(np.maximum(cv2.blur(f*f, (17, 17))-mean*mean, 0))
    mask = ((std > .035) & (coherence > .35)).astype('uint8')*255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if n > 1:
        i = 1+np.argmax(stats[1:, cv2.CC_STAT_AREA])
        mask = (labels == i).astype('uint8')*255
    if np.count_nonzero(mask) < gray.size*.015:
        mask[:] = 0
    return normal, coherence, mask


def frequency_map(gray, mask):
    # Windowed block spectra: choose strongest plausible ridge frequency.
    h, w = gray.shape
    freqs = np.full((h, w), 1/9, np.float32)
    for y in range(0, h, 32):
        for x in range(0, w, 32):
            y0, x0 = min(y, max(0, h-48)), min(x, max(0, w-48))
            block = gray[y0:y0+48, x0:x0+48].astype(float)
            if min(block.shape) < 32 or np.mean(mask[y:y+32, x:x+32]) < 50:
                continue
            window = np.outer(np.hanning(block.shape[0]), np.hanning(block.shape[1]))
            spec = abs(np.fft.fft2((block-block.mean())*window))
            fy, fx = np.meshgrid(np.fft.fftfreq(block.shape[0]), np.fft.fftfreq(block.shape[1]), indexing='ij')
            radius = np.hypot(fx, fy)
            spec[(radius < 1/16) | (radius > 1/4)] = 0
            freqs[y:y+32, x:x+32] = radius[np.unravel_index(spec.argmax(), spec.shape)]
    return freqs


def enhance(gray, strength=.5, method='ridge'):
    normal, coherence, mask = structure(gray)
    # Edge-preserving smoothing, blended so strength zero is a true no-op.
    filtered = cv2.bilateralFilter(gray, 5, 40, 2)
    denoised = cv2.addWeighted(gray, 1-strength, filtered, strength, 0)
    contrast = cv2.createCLAHE(clipLimit=1.5+strength, tileGridSize=(8, 8)).apply(denoised)
    freq = frequency_map(denoised, mask)
    enhanced = denoised.copy()
    response = np.zeros(gray.shape, np.float32)
    if method == 'ridge' and mask.any():
        idx = np.floor((normal % np.pi)/np.pi*12+.5).astype(int) % 12
        wavelengths = np.array([5., 8., 12., 16.])
        band = np.argmin(abs(1/freq[..., None]-wavelengths), axis=2)
        f = contrast.astype(np.float32)
        for b, wavelength in enumerate(wavelengths):
            for k in range(12):
                selected = (idx == k) & (band == b) & (mask > 0)
                if not selected.any():
                    continue
                kernel = cv2.getGaborKernel((25, 25), wavelength*.55, k*np.pi/12, wavelength, .65, 0, ktype=cv2.CV_32F)
                kernel -= kernel.mean()
                kernel /= np.sum(abs(kernel))+1e-6
                filtered = cv2.filter2D(f, cv2.CV_32F, kernel)
                response[selected] = filtered[selected]
        values = response[mask > 0]
        scale = max(float(np.percentile(abs(values), 95)), 1)
        ridge = np.clip(128+response*100/scale, 0, 255)
        alpha = cv2.GaussianBlur(mask.astype(np.float32)/255, (0, 0), 2)*strength
        enhanced = np.clip(contrast*(1-alpha)+ridge*alpha, 0, 255).astype('uint8')
    elif method == 'contrast':
        enhanced = cv2.addWeighted(gray, 1-strength, contrast, strength, 0)
    elif method == 'sharpen':
        # Unsharp masking improves edge contrast; it is not deconvolution.
        low = cv2.GaussianBlur(gray, (0, 0), 1.0)
        enhanced = cv2.addWeighted(gray, 1+1.5*strength, low, -1.5*strength, 0)
    if strength == 0:
        enhanced = gray.copy()
    binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5)
    binary[mask == 0] = 255
    spectrum = np.log1p(abs(np.fft.fftshift(np.fft.fft2(gray.astype(float)-gray.mean()))))
    spectrum = cv2.normalize(spectrum, None, 0, 255, cv2.NORM_MINMAX).astype('uint8')
    overlay = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(overlay, contours, -1, (110, 170, 20), 2)
    for y in range(12, gray.shape[0], 24):
        for x in range(12, gray.shape[1], 24):
            if mask[y, x]:
                a = normal[y, x]+np.pi/2
                dx, dy = int(8*np.cos(a)), int(8*np.sin(a))
                cv2.line(overlay, (x-dx, y-dy), (x+dx, y+dy), (110, 170, 20), 1)
    return enhanced, {'Grayscale': gray, 'Candidate mask': mask, 'Denoised': denoised, 'Local contrast': contrast, 'Ridge directions': overlay, 'Binary ridges': binary, 'Input FFT spectrum': spectrum}, {
        'candidate_coverage_percent': round(float(np.mean(mask > 0)*100), 1),
        'mean_candidate_coherence': round(float(coherence[mask > 0].mean()), 3) if mask.any() else 0,
        'median_ridge_spacing_px': round(float(np.median(1/freq[mask > 0])), 1) if mask.any() else None,
        'candidate_found': bool(mask.any()),
    }


def degrade(gray, noise, seed=17, kind="noise", blur_sigma=1.0):
    if kind == "blur":
        return cv2.GaussianBlur(gray, (0, 0), blur_sigma)
    rng = np.random.default_rng(seed)
    return np.clip(gray.astype(float)+rng.normal(0, noise, gray.shape), 0, 255).astype('uint8')


def metrics(reference, image):
    value = peak_signal_noise_ratio(reference, image, data_range=255)
    return {'psnr_db': round(float(value), 3) if np.isfinite(value) else None,
            'ssim': round(float(structural_similarity(reference, image, data_range=255)), 4)}
