"""Add server-side STT endpoint to views.py."""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'accounts', 'views.py')

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add import for os
old_import = 'import requests'
if old_import in content:
    content = content.replace(old_import, 'import os\nimport tempfile\nimport requests\nimport speech_recognition as sr')

# Add endpoint before Translation section
marker = "# ── Translation ──────────────────────────────────────────────────────────────"
stt_code = '''# ── Audio Transcription ──────────────────────────────────────────────────────

def transcribe_audio(request, post_id):
    """Server-side STT: accept audio file, return transcribed text."""
    post = get_object_or_404(Post, pk=post_id)  # noqa: F841
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    audio_file = request.FILES.get('audio')
    if not audio_file:
        return JsonResponse({'error': 'No audio file provided'}, status=400)

    tmp_path = None
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
                pass


'''

content = content.replace(marker, stt_code + marker)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('views.py patched with STT endpoint')
