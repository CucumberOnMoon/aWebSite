"""Update transcribe_audio to use Sphinx offline fallback."""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'accounts', 'views.py')

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the try block in transcribe_audio
old = """    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_path) as source:
            audio_data = recognizer.record(source)

        text = recognizer.recognize_google(audio_data)
        return JsonResponse({'text': text, 'lang': 'auto'})
    except Exception as e:
        return JsonResponse({
            'error': f'Transcription failed: {str(e)[:100]}',
        }, status=503)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass"""

new = """    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_path) as source:
            audio_data = recognizer.record(source)

        # Try Google first, then offline Sphinx
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
            }, status=503)
    except Exception as e:
        return JsonResponse({
            'error': f'Transcription failed: {str(e)[:100]}',
        }, status=503)
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched: Google + Sphinx fallback')
else:
    print('ERROR: old string not found')
    # Try to find it
    idx = content.find('tempfile.NamedTemporaryFile')
    if idx >= 0:
        snippet = content[idx-30:idx+150]
        print(f'Found at {idx}: {repr(snippet[:100])}...')
