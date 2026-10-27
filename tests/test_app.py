import base64
import unittest
import cv2
import numpy as np
from fastapi.testclient import TestClient
from app import app
from processing import sample, degrade, metrics

client = TestClient(app)

def upload(image, **settings):
    raw = cv2.imencode('.png', image)[1].tobytes()
    return client.post('/api/process', files={'file': ('test.png', raw, 'image/png')}, data=settings)

class AppTests(unittest.TestCase):
    def test_tiff_preview_and_processing(self):
        from io import BytesIO
        from PIL import Image
        for extension in ('tif', 'tiff'):
            for compression in ('raw', 'tiff_lzw'):
                buf = BytesIO()
                Image.fromarray(sample()).save(buf, format='TIFF', compression=compression)
                files = {'file': ('print.'+extension, buf.getvalue(), 'application/octet-stream')}
                preview = client.post('/api/preview', files=files)
                self.assertEqual(preview.status_code, 200, preview.text[:200])
                self.assertTrue(preview.json()['image'].startswith('data:image/png;base64,'))
                self.assertEqual(preview.json()['width'], 384)
                self.assertEqual(client.post('/api/process', files=files).status_code, 200)
        buf = BytesIO()
        Image.fromarray(sample()).save(buf, format='TIFF', save_all=True, append_images=[Image.fromarray(sample())])
        r = client.post('/api/preview', files={'file': ('pages.tif', buf.getvalue())})
        self.assertEqual(r.json()['pages'], 2)
        self.assertEqual(client.post('/api/preview', files={'file': ('bad.tif', b'bad')}).status_code, 400)

    def test_home(self):
        self.assertEqual(client.get('/').status_code, 200)
        self.assertEqual(client.get('/static/app.js').status_code, 200)

    def test_pipeline_and_serialization(self):
        for method in ('ridge', 'contrast', 'denoise', 'sharpen'):
            response = upload(sample(), method=method)
            self.assertEqual(response.status_code, 200, response.text[:200])
            data = response.json()
            out = cv2.imdecode(np.frombuffer(base64.b64decode(data['output'].split(',')[1]), np.uint8), 0)
            self.assertEqual(out.shape, (384, 384))
            self.assertTrue(data['report']['candidate_found'])
            self.assertEqual(len(data['stages']), 7)
            self.assertGreater(np.std(out), 10)

    def test_reference_metrics_and_reproducibility(self):
        a = upload(sample(), method='denoise', verify='true', noise=20).json()
        b = upload(sample(), method='denoise', verify='true', noise=20).json()
        self.assertEqual(a['input'], b['input'])
        self.assertEqual(a['report']['baseline'], metrics(sample(), degrade(sample(), 20)))
        self.assertGreater(a['report']['delta_ssim'], 0)

    def test_strength_and_blur(self):
        from processing import enhance
        ref = sample()
        for method in ('ridge', 'contrast', 'denoise', 'sharpen'):
            out, _, _ = enhance(ref, 0, method)
            np.testing.assert_array_equal(out, ref)
        noisy = degrade(ref, 20)
        gentle = enhance(noisy, .03, 'denoise')[0]
        strong = enhance(noisy, 1, 'denoise')[0]
        self.assertLess(np.mean(abs(gentle.astype(float)-noisy)), np.mean(abs(strong.astype(float)-noisy)))
        r = upload(ref, method='sharpen', verify='true', degradation='blur', blur_sigma=1).json()
        self.assertEqual(r['report']['degradation'], 'blur')
        self.assertIsNone(r['report']['noise_sigma'])
        self.assertEqual(r['report']['baseline'], metrics(ref, degrade(ref, 20, kind='blur', blur_sigma=1)))
        self.assertGreater(r['report']['delta_ssim'], 0)
        self.assertEqual(upload(ref, degradation='invalid').status_code, 422)

    def test_blank_has_no_candidate(self):
        data = upload(np.full((128, 128), 255, np.uint8)).json()
        self.assertFalse(data['report']['candidate_found'])

    def test_invalid_image_and_settings(self):
        r = client.post('/api/process', files={'file': ('bad.png', b'not an image', 'image/png')})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(upload(sample(), method='unknown').status_code, 422)
        self.assertEqual(upload(sample(), strength='nan').status_code, 422)
        self.assertEqual(upload(sample(), crop_x=.8, crop_w=.5).status_code, 422)
        self.assertEqual(upload(sample(), crop_w=.01).status_code, 400)

    def test_crop_and_size_limit(self):
        r = upload(sample(), crop_x=.25, crop_y=.25, crop_w=.5, crop_h=.5).json()
        self.assertEqual((r['report']['width'], r['report']['height']), (192, 192))
        big = np.full((1200, 1600), 200, np.uint8)
        r = upload(big).json()
        self.assertEqual((r['report']['width'], r['report']['height']), (1000, 750))

if __name__ == '__main__':
    unittest.main(verbosity=2)
