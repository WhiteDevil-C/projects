# Face Award System (v2 - API ready)

## 1) Install dependencies
```bash
pip install -r requirements.txt
```

## 2) Run the server
From the project folder (where `app.py` is):
```bash
python app.py
```

Open in browser:
- http://127.0.0.1:5000/

## 3) Use the app (recommended flow)
1. Register (captures 25 face samples using your webcam)
2. Train (creates `models/lbph_model.xml` + `models/label_map.json`)
3. Verify (recognizes face)
4. Award (creates a certificate PNG you can download)

## Notes / Troubleshooting
- If camera doesn't open: close Zoom/Meet/browser tabs using camera, then retry.
- On Windows, DirectShow is used automatically for more stable camera open.
- Certificates are saved in `certificates/`.
- Face images are saved in `data/faces/<name>/`.
