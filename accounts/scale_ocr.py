"""
Scale OCR — v5: clean regex, handle 9→9.9 case in specific fields.
Windows-only OCR via winrt; falls through on other platforms.
"""

import asyncio, re, json, io, os

# winrt is Windows-only — import lazily inside the function
_winrt_available = False
try:
    import winrt.windows.foundation.collections  # noqa: F401
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage.streams import InMemoryRandomAccessStream, DataWriter
    _winrt_available = True
except ImportError:
    _winrt_available = False

from PIL import Image

_ocr_engine = None

def _get_ocr():
    global _ocr_engine
    if not _winrt_available:
        raise ImportError("winrt not available (Windows-only OCR)")
    if _ocr_engine is None:
        ocr = OcrEngine.try_create_from_language(Language("zh-CN"))
        ocr = ocr or OcrEngine()
        _ocr_engine = ocr
    return _ocr_engine

async def _ocr_image(image_bytes):
    ocr = _get_ocr()
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode != 'RGB': img = img.convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    png_bytes = buf.getvalue()
    stream = InMemoryRandomAccessStream()
    writer = DataWriter(stream)
    writer.write_bytes(png_bytes)
    await writer.store_async()
    stream.seek(0)
    decoder = await BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    result = await ocr.recognize_async(bitmap)
    return [line.text for line in result.lines]

def clean(t):
    """Just replace punctuation and remove spaces. No digit-regex joining."""
    t = t.replace('．', '.').replace('，', '.').replace('％', '%')
    t = t.replace('·', '.').replace('：', ':').replace('／', '/')
    t = t.replace(' ', '').replace('l', '1').replace('O', '0').replace('o', '0')
    return t.strip()

def num_in(text, lo, hi):
    m = re.search(r'(\d+\.?\d*)', text)
    if m:
        v = float(m[1])
        return v if lo <= v <= hi else None
    return None

def parse(raw_lines):
    data = {k: None for k in [
        'weight_jin','bmi','body_fat_pct','body_fat_score',
        'skeletal_muscle_jin','visceral_fat_level','arms_legs_muscle_index',
        'waist_hip_ratio','body_water_pct','protein_pct','bone_mineral_jin',
        'fat_free_mass_jin','basal_metabolism_kcal','body_age','heart_rate',
        'body_type','body_shape','date','time'
    ]}
    data['raw_lines'] = raw_lines

    # Join value lines with their unit/qualifier lines
    joined = []
    skip = False
    for i in range(len(raw_lines)):
        if skip: skip = False; continue
        r = raw_lines[i]
        if i+1 < len(raw_lines):
            nr = raw_lines[i+1]
            # Only join: (a) value line + unit line, or (b) short value line + short qualifier
            if (re.match(r'^[\s·]*[斤％分级岁次/卡kg]', nr) or  # next line is unit
                (len(r.strip(' ·')) <= 12 and re.search(r'\d', r) and 
                 not re.search(r'\d', nr) and len(nr.strip(' ·')) <= 5 and  # qualifier short
                 not any(u in r for u in '斤％分级岁次/卡kg'))):  # current line NOT already has unit
                joined.append(r + ' ' + nr); skip = True; continue
        joined.append(r)

    pairs = [(clean(r), r) for r in joined]

    # === Helper: find value after keyword ===
    def after_kw(kw, lo, hi, fmt=float):
        for i, (c, r) in enumerate(pairs):
            if kw in c:
                for j in range(i, min(i+2, len(pairs))):
                    v = num_in(pairs[j][0], lo, hi)
                    if v: return fmt(v)
        return None

    # === DATE/TIME ===
    for c, r in pairs:
        norm = r.replace('：',':').replace('／','/')
        m = re.search(r'(\d{4})\s*[/\-]\s*(\d{1,2})\s*[/\-]\s*(\d{1,2})\s+(\d{1,2})\s*:\s*(\d{2})', norm)
        if m:
            data['date'] = f"{m[1]}-{m[2].zfill(2)}-{m[3].zfill(2)}"
            data['time'] = f"{m[4].zfill(2)}:{m[5]}"
            break

    # === WEIGHT (斤): find the largest 2-3 digit decimal ===
    for c, r in pairs:
        m = re.search(r'(\d{2,3}\.\d{1,2})', c)
        if m and 80 <= float(m[1]) <= 300:
            data['weight_jin'] = float(m[1])
            break

    # === BMI ===
    for i, (c, r) in enumerate(pairs):
        if 'bmi' in c.lower():
            for j in range(i, min(i+2, len(pairs))):
                v = num_in(pairs[j][0], 10, 50)
                if v: data['bmi'] = v; break
            break

    # === BODY FAT ===
    data['body_fat_pct'] = after_kw('脂肪率', 5, 60)
    if data['body_fat_pct'] is None:
        data['body_fat_pct'] = after_kw('脂', 5, 60)

    # === BODY FAT SCORE ===
    for i, (c, r) in enumerate(pairs):
        if '得分' in c or ('身体' in c and '分' in c):
            v = num_in(c, 0, 100)
            if v: data['body_fat_score'] = int(v); break
        # Also check next line
        if i+1 < len(pairs) and ('得分' in c or '身体' in c):
            v = num_in(pairs[i+1][0], 0, 100)
            if v: data['body_fat_score'] = int(v); break

    # === General label+value fields ===
    label_map = [
        ('骨骼肌量', 'skeletal_muscle_jin', 40, 150),  # 更精确的关键词
        ('内脏脂肪', 'visceral_fat_level', 1, 30),
        ('四肢', 'arms_legs_muscle_index', 3, 20),
        ('腰臀比', 'waist_hip_ratio', 0.5, 1.5),
        ('水分', 'body_water_pct', 30, 80),
        ('蛋白质', 'protein_pct', 5, 30),
        ('去脂', 'fat_free_mass_jin', 60, 250),
        ('代谢', 'basal_metabolism_kcal', 800, 5000),
        ('年龄', 'body_age', 10, 99),
        ('心率', 'heart_rate', 30, 220),
    ]
    for kw, key, lo, hi in label_map:
        if data[key] is not None: continue
        data[key] = after_kw(kw, lo, hi)
    # Convert int fields
    if data['basal_metabolism_kcal']: data['basal_metabolism_kcal'] = int(data['basal_metabolism_kcal'])
    if data['body_age']: data['body_age'] = int(data['body_age'])
    if data['heart_rate']: data['heart_rate'] = int(data['heart_rate'])

    # Special: limbs muscle index — handle "99" → 9.9
    if data['arms_legs_muscle_index'] is None:
        for i, (c, r) in enumerate(pairs):
            if '四肢' in c or '指数' in c:
                for j in range(i, min(i+2, len(pairs))):
                    m = re.search(r'(\d{2,3})', pairs[j][0])
                    if m:
                        v = int(m[1])
                        if 3 <= v <= 20:
                            data['arms_legs_muscle_index'] = float(v)
                            break
                        elif 30 <= v <= 200:
                            data['arms_legs_muscle_index'] = v / 10.0
                            break
                break

    # === BASAL METABOLISM ===
    for c, r in pairs:
        if '代谢' in c:
            m = re.search(r'(\d{3,4})', c)
            if m and 800 <= int(m[1]) <= 5000:
                data['basal_metabolism_kcal'] = int(m[1]); break
        # Also try raw line for "千卡"
        if '代谢' in c:
            m = re.search(r'(\d{3,4})', c.replace('.', ''))
            if m and 800 <= int(m[1]) <= 5000:
                data['basal_metabolism_kcal'] = int(m[1]); break

    # === BODY AGE ===
    for c, r in pairs:
        if '年龄' in c:
            m = re.search(r'(\d{2})', c)
            if m and 10 <= int(m[1]) <= 99:
                data['body_age'] = int(m[1]); break

    # === HEART RATE ===
    for c, r in pairs:
        if '心率' in c:
            m = re.search(r'(\d{2,3})', c)
            if m and 30 <= int(m[1]) <= 220:
                data['heart_rate'] = int(m[1]); break

    # === BODY TYPE ===
    for i, (c, r) in enumerate(pairs):
        if '身体类型' in c or '体型' in c:
            check_lines = [c]
            if i+1 < len(pairs): check_lines.append(pairs[i+1][0])
            for cl in check_lines:
                for t in ['标准肌肉型','肌肉型','偏胖型','肥胖型','标准型','消瘦型']:
                    if t in cl: data['body_type'] = t; break
                if data['body_type']: break
            if data['body_type']: break

    # === BODY SHAPE ===
    for i, (c, r) in enumerate(pairs):
        if '身体形态' in c or '形态' in c:
            check_lines = [c]
            if i+1 < len(pairs): check_lines.append(pairs[i+1][0])
            for cl in check_lines:
                for s in ['苹果型','梨型','标准型','沙漏型','直筒型']:
                    if s in cl: data['body_shape'] = s; break
                if data['body_shape']: break
            if data['body_shape']: break

    return data

def ocr_scale_image(path):
    with open(path, 'rb') as f: img_bytes = f.read()
    lines = asyncio.run(_ocr_image(img_bytes))
    return {**parse(lines), 'image_path': path}

def ocr_scale_bytes(img_bytes, source='unknown'):
    lines = asyncio.run(_ocr_image(img_bytes))
    return {**parse(lines), 'source': source}

if __name__ == '__main__':
    r = ocr_scale_image(r'C:\Users\howar\real_scale.jpg')
    found = {k:v for k,v in r.items() if k != 'raw_lines' and v is not None}
    missing = {k:v for k,v in r.items() if v is None and k != 'raw_lines'}
    print(json.dumps(found, indent=2, ensure_ascii=False))
    print(f"\n✅ Found: {len(found)}  ❌ Missing: {len(missing)}")
    if missing:
        print(f"   Missing: {list(missing.keys())}")
