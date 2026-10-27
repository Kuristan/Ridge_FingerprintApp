# v1.3 — TIF/TIFF preview fix

Select or drop `.tif` and `.tiff` directly. The backend converts the first page to a PNG preview before enabling processing. Uncompressed and LZW-compressed 8-bit TIFF uploads were tested. Multipage TIFFs use page one and display a notice. No manual conversion is needed.

## v1.2 update — read first

Denoising now uses edge-preserving bilateral filtering and responds to the strength slider. Zero strength leaves the working image unchanged in every mode. Gentle sharpening uses unsharp masking for mild blur; it is not a reconstruction algorithm. In Controlled reference test, choose Gaussian blur (start at sigma 1.0 px) or Gaussian noise. Blur is applied at working resolution. Select sharpening for mild blur, denoising for noise, and contrast for faint impressions. Older numerical examples below are historical v1.0 results; see VALIDATION.md for current checks.

# RidgeLab — local fingerprint DSP workspace

A local web app for exploring enhancement of single fingerprint impressions. No model training, API key, database, or cloud service is needed. First-time dependency installation needs internet access. Use Python 3.11 or 3.12.

## Presentation theme update (v1.1)

The UI now follows the Group 6 PPT: black background, electric-lime highlights, subtle heading glow, and geometric system-font fallbacks. The exact PPT font was not supplied, so the app uses locally available fonts without requiring internet. Fingerprint image pixels are not tinted by the theme. See `PROJECT_EXPLANATION.md` for the problem statement, enhancement details, relevance, and presentation talking points.

## Start on Windows

1. Extract the ZIP completely (do not run from inside the ZIP).
2. Install Python 3.11 or 3.12 if it is not already installed. Enable the Python launcher and “Add Python to PATH” during installation.
3. Open the extracted RidgeLab folder and double-click `start_windows.bat`.
4. Wait for installation to finish and for the terminal to show that Uvicorn is running.
5. Open http://127.0.0.1:8000 in your browser. Keep the terminal open.
6. Press Ctrl+C in the terminal to stop.

If Windows asks about the batch file, you can instead use the explicit commands below from a terminal in the extracted folder.

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

For later starts without reinstalling dependencies, run only the final command.
If port 8000 is busy, replace it with 8001 and open http://127.0.0.1:8001.
If `py` is not recognized but `python --version` works, replace `py -3` with `python`.

## Start on macOS / Linux

Open Terminal in this folder and run:

```bash
bash start_mac_linux.sh
```

For later runs: `.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000`.
Some Linux distributions require the Python venv package to be installed first.

## First demonstration

1. Click **Try synthetic ridge sample**. This is an analytical test pattern, not a real fingerprint or an accuracy dataset.
2. Choose **Adaptive ridge enhancement**, then click **Enhance image**. Compare input/output and open **DSP stages**.
3. Set **Noise reduction only** and enable **Controlled reference test**.
4. Select **Gaussian noise**, leave noise at 20, then enhance. Read PSNR and SSIM against the clean reference.
5. Try **Adaptive ridge enhancement** with the same reference and noise. Compare the scores and visible ridge structure. Different objectives can produce different metric outcomes.
6. Upload a real fingerprint impression, turn off the reference test, and compare ridge continuity at 100%/200% zoom.
7. Download the output PNG and JSON report.

Changing any processing setting invalidates the previous result and disables downloads until the next run.

## Included functions

- Upload PNG, JPEG, BMP, or TIFF (first frame only).
- Image validation, EXIF orientation correction, transparent pixels composited over white.
- Manual percentage crop. Crop must be at least 64 × 64 pixels.
- Working images resized proportionally to a maximum of 1000 pixels on the long side.
- Heuristic candidate region, largest connected component, ridge direction display.
- Strength-controlled bilateral denoising, CLAHE contrast, adaptive Gabor ridge enhancement.
- Before/after display, fit/100%/200% zoom, intermediate stages, binary visualization, input FFT magnitude.
- Reference testing with fixed-seed Gaussian noise, measured PSNR/SSIM, JSON export.
- Download enhanced PNG. The backend does not save uploaded images or results to disk.

## DSP implementation

| Operation | Implementation and role |
| --- | --- |
| Grayscale | Pillow luminance conversion gives a 2D intensity signal. |
| Candidate segmentation | Local standard deviation and structure-tensor coherence; close gaps, retain largest component. This is not a trained fingerprint classifier. |
| Denoising | 5-pixel bilateral filter, blended with the input according to strength. |
| Contrast | CLAHE with 8 × 8 tiles and adjustable clipping limit. |
| Ridge orientation | Sobel gradients, Gaussian-smoothed structure tensor; ridge tangent is perpendicular to gradient normal. |
| Ridge frequency | Mean-subtracted, Hann-windowed local FFT; strongest frequency in 1/16–1/4 cycles/pixel. Frequency quantized to four Gabor wavelengths. |
| Ridge enhancement | 12 normal orientations × four wavelengths; zero-mean normalized Gabor kernels; blend filtered response with CLAHE according to strength inside candidate mask. |
| Binary view | Adaptive Gaussian threshold, masked to candidate area. Visualization only. |
| Spectrum | Centered, log-scaled 2D FFT magnitude of the working input. This display itself does not filter the output. |
| Evaluation | PSNR and SSIM with data range 255, identical dimensions, grayscale output. |

The stages panel includes diagnostic/alternative stages even when a simpler output method is chosen. Noise reduction only returns the denoised stage; local contrast returns CLAHE; adaptive ridge returns the Gabor blend. If no candidate is found, adaptive ridge falls back to denoising.

## Verification and interpretation

In reference mode, the uploaded working crop is treated as the clean reference. Seed 17 generates reproducible Gaussian noise. Both the noisy input and processed output are compared against that same reference. Values refer to the working resolution after cropping/resizing. A poor uploaded reference is not ground truth simply because reference mode is enabled.

Scores can decrease. Contrast or Gabor enhancement may make ridge lines more visible while moving pixel intensities farther from the clean image. The app reports the actual results, including negative changes. It does not fabricate an “accuracy percentage.”

For project evaluation, use 10–20 distinct, consented or appropriately licensed real fingerprint images. Keep evaluation images separate from examples used to tune settings. Test several noise levels and record all outcomes, including failures. Inspect fixed regions for false ridge joins, missing branches, breaks, and loss of detail. Include blank images and striped textures as negative cases. Higher contrast or coherence alone does not establish successful restoration.

## Known scope and limits

- Intended for one close-up ink/scanned fingerprint impression on a plain background.
- No person identification, biometric matching, arbitrary-scene detector, or liveness detection.
- Textures can trigger the candidate mask. Detection is not validated on a real dataset yet.
- Strong blur, saturated regions, smudged ink, and missing detail cannot be reliably reconstructed.
- Local ridge-frequency estimation is approximate; very fine/coarse ridges outside the supported working scale can be processed poorly.
- Synthetic sample tests are engineering checks, not evidence of real-world fingerprint accuracy.
- Reference tests support Gaussian noise or Gaussian blur; lighting degradation is not simulated.
- Initial browser visual/end-to-end QA could not run because the available preview service lacks the Python runtime. Backend integration tests and JavaScript syntax checks passed. Verify the browser flow on your laptop before presenting.

## Tests

From the project folder, after installing requirements:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

macOS/Linux: `.venv/bin/python -m unittest discover -s tests -v`.
Seven test methods cover routes, processing modes, PNG encoding, deterministic reference metrics, blank-image rejection, invalid inputs/settings, cropping, and resizing.

## Files

- `app.py`: local FastAPI endpoints and image validation.
- `processing.py`: signal-processing operations and metrics.
- `static/`: minimal interface, styles, and browser interactions.
- `tests/test_app.py`: integration checks.
- `VALIDATION.md`: initial measured results and validation boundaries.
- `requirements.txt`: compatible dependency ranges.
- `requirements-tested.txt`: exact direct dependency versions used for this build.

## Presentation outline

1. Problem: faint or noisy fingerprint ridges.
2. App workflow: upload, crop, enhance, inspect, download.
3. DSP: show the actual processing stages and explain their roles.
4. Verification: clean reference → noisy copy → processed output → PSNR/SSIM.
5. Results and limits: show both improvement and failure cases.

Source background: Hong, Wan & Jain, “Fingerprint Image Enhancement: Algorithm and Performance Evaluation” (1998); scikit-image metrics documentation at https://scikit-image.org/docs/stable/api/skimage.metrics.html. This is a simplified educational implementation, not a reproduction or certification of that research.
