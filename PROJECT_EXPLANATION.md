## v1.2 update — read first

Denoising now uses edge-preserving bilateral filtering and responds to the strength slider. Zero strength leaves the working image unchanged in every mode. Gentle sharpening uses unsharp masking for mild blur; it is not a reconstruction algorithm. In Controlled reference test, choose Gaussian blur (start at sigma 1.0 px) or Gaussian noise. Blur is applied at working resolution. Select sharpening for mild blur, denoising for noise, and contrast for faint impressions. Older numerical examples below are historical v1.0 results; see VALIDATION.md for current checks.

# RidgeLab: problem, enhancement, and evaluation

## Problem statement

Fingerprint impressions captured as digital images may contain noise, low contrast, and uneven illumination. These conditions make the ridges and valleys difficult to distinguish and inspect. This project develops a local web application that applies digital signal-processing techniques to improve the visibility of existing fingerprint structures and evaluate the resulting images.

This is an image-quality problem. The current app does not identify people, authenticate users, or search fingerprint databases.

## What is being enhanced?

Ridges are the lines forming the fingerprint pattern; valleys are the gaps between them. In an ink impression, ridges are usually dark and valleys lighter. Useful enhancement makes these structures easier to distinguish while preserving their shape and continuity.

Enhancement is not simply increasing sharpness. An image can look sharper while gaining false joins, losing ridge endings, or developing new breaks. Missing or saturated image detail cannot be reliably reconstructed by these filters.

## Causes and treatment

| Problem | Effect on the image | Treatment in this app | Limitation |
| --- | --- | --- | --- |
| Random noise | Speckles obscure ridge detail | Strength-controlled bilateral filtering | Excessive smoothing removes fine detail |
| Faint contrast | Ridges and valleys have similar intensity | CLAHE local contrast adjustment | Can amplify residual noise |
| Uneven lighting | Some areas are difficult to distinguish | Local contrast adjustment | Clipped highlights and shadows have lost information |
| Weak ridge visibility | Patterns are difficult to follow | Orientation/frequency-adapted Gabor filtering | Poor parameter estimates may introduce false structure |
| Background content | Distracts from the fingerprint | Candidate mask and manual crop | Striped textures can trigger the mask |
| Heavy blur or smudging | Adjacent ridges merge | User inspection and clearer source recommended | This version has no deblurring or reliable reconstruction |

## Processing sequence

1. Validate the input, correct orientation, crop, convert to grayscale, and resize if needed.
2. Estimate a candidate region from local contrast and directional consistency.
3. Reduce noise with a strength-controlled bilateral filter.
4. Adjust local contrast with CLAHE.
5. Estimate ridge orientation using gradients and a structure tensor.
6. Estimate local ridge spacing using windowed block FFTs.
7. Select Gabor filters by orientation and approximate spacing, then blend their responses with the contrast image inside the candidate region.
8. Show the result, diagnostic stages, and optional binary visualization.

The user can also select denoising only or local contrast only. These simpler alternatives allow meaningful comparisons. The large FFT image is a diagnostic display; the local block FFTs are used in frequency estimation.

## Why this is DSP

A grayscale image is a two-dimensional discrete signal I[x,y]. Each pixel stores an intensity sample at a spatial location. Filters operate on these samples. Spatial frequency describes how rapidly brightness alternates across the image, such as the repeated light/dark transitions between valleys and ridges. Gabor filters select particular orientations and spatial frequencies.

## Relevance to computer security

Fingerprint image processing can be a preprocessing stage in a larger biometric system. The relevance of this prototype is improving image inspectability and demonstrating DSP before any downstream feature extraction or matching. The prototype does not measure authentication accuracy or establish security suitability.

## How to verify results

### Controlled reference test

Treat a clean uploaded image as a reference. Add fixed-seed Gaussian noise, process that degraded image, and compare both the noisy input and the output with the same clean reference using PSNR and SSIM. Use the same dimensions and crop. Higher scores mean closer agreement under those metrics, not a probability that a fingerprint is correct.

The current verification mode tests added Gaussian noise or Gaussian blur. These controlled tests do not establish performance on real smudging, lighting problems, or arbitrary-scene detection.

### Structural inspection

At the same zoom and crop, check selected ridges for continuity, false joins, new breaks, vanished branches, and lost detail. A darker or higher-contrast result is not automatically a better result.

### Real-image evaluation

Use distinct real fingerprint impressions and negative examples, including blank images and striped textures. Keep evaluation images separate from images used to tune settings. Record failures and compare all four methods. Do not present the built-in synthetic pattern as a real fingerprint dataset.

## Initial measured example

On the synthetic test pattern with Gaussian noise sigma 20 and seed 17:

| Result | PSNR | SSIM |
| --- | ---: | ---: |
| Noisy input | 22.902 dB | 0.6711 |
| Denoising | 27.954 dB | 0.8626 |
| Adaptive ridge enhancement | 19.363 dB | 0.6996 |

Denoising improved both measures in this example. Ridge enhancement improved SSIM slightly but reduced PSNR. This demonstrates why enhancement settings must be evaluated rather than assumed to improve every image. These results are synthetic engineering checks, not biometric validation.

## Suggested objectives

1. Develop a local web application for uploading and enhancing single fingerprint impressions.
2. Apply noise reduction, local contrast enhancement, and adaptive ridge filtering using DSP techniques.
3. Display intermediate processing results and allow before/after inspection.
4. Evaluate controlled restoration using PSNR, SSIM, and visual ridge-preservation checks.

## Short presentation explanation

Our project addresses fingerprint images that are difficult to inspect because of noise and faint contrast. RidgeLab applies digital signal-processing techniques to reduce noise and make existing ridge patterns more visible. Users can compare processing methods and inspect each stage. We evaluate controlled noise restoration using a clean reference, PSNR, and SSIM, together with visual checks for false ridge connections or breaks. The current application enhances images; it does not identify the person or authenticate a user.
