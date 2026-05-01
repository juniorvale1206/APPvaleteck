# Image Testing Playbook

## TEST AGENT PROMPT – IMAGE INTEGRATION RULES

### Image Handling Rules
- Always use base64-encoded images for all tests and requests.
- Accepted formats: JPEG, PNG, WEBP only.
- Do not use SVG, BMP, HEIC, or other formats.
- Do not upload blank, solid-color, or uniform-variance images.
- Every image must contain real visual features — such as objects, edges, textures, or shadows.
- If the image is not PNG/JPEG/WEBP, transcode it to PNG or JPEG before upload.
- If the image is animated (e.g., GIF, APNG, WEBP animation), extract the first frame only.
- Resize large images to reasonable bounds (avoid oversized payloads).

### For OCR endpoint `/api/ocr/plate`
- Provide a real image that plausibly contains a Brazilian vehicle license plate (ABC1234 or ABC1D23).
- The response should contain `{ plate: string|null, confidence: float, raw: string }`.
- If plate not detected, `plate` may be null with lower confidence.
