"""Fix Sphinx empty-string bug in transcribe_audio."""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'accounts', 'views.py')

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = """        # Try Google first, then offline Sphinx
        text = None
        try:
            text = recognizer.recognize_google(audio_data)
        except Exception:
            try:
                text = recognizer.recognize_sphinx(audio_data)
            except Exception:
                pass

        if text:
            return JsonResponse({'text': text, 'lang': 'auto'})
        else:
            return JsonResponse({
                'error': 'All recognition engines failed.',
            }, status=503)"""

new = """        # Try Google first, then offline Sphinx
        text = None
        try:
            text = recognizer.recognize_google(audio_data)
        except Exception:
            pass

        if not text:
            try:
                text = recognizer.recognize_sphinx(audio_data)
            except sr.UnknownValueError:
                text = None
            except Exception:
                text = None

        if text:
            return JsonResponse({'text': text, 'lang': 'auto'})
        else:
            return JsonResponse({
                'error': 'No speech detected or recognition failed.',
            }, status=503)"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched: fixed Sphinx empty-string handling')
else:
    print('ERROR: string not found')
