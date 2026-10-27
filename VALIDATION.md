## v1.3 TIFF checks

Eight test methods passed, including TIF/TIFF preview and enhancement with uncompressed/LZW files, multipage first-page notice, and corrupt TIFF rejection. JavaScript syntax passed. Browser interaction remains unverified here.

# v1.2 validation

Seven backend integration test methods passed; JavaScript syntax check passed. New checks cover zero-strength identity, denoising-strength response, blur-reference metrics, and invalid degradation settings.

Synthetic pattern, strength 0.5, noise sigma 20 (seed 17) or blur sigma 1.0 pixels:

| Test | Degraded vs reference | Processed vs reference |
|---|---|---|
| noise / denoise | {'psnr_db': 22.902, 'ssim': 0.6711} | {'psnr_db': 25.115, 'ssim': 0.7583} |
| blur / sharpen | {'psnr_db': 28.572, 'ssim': 0.9778} | {'psnr_db': 33.7, 'ssim': 0.9906} |

These are synthetic tests, not real fingerprint accuracy. No browser visual or click-through validation was possible in this environment. A screenshot from the user confirmed earlier UI rendering, but the revised controls still need local browser verification.
