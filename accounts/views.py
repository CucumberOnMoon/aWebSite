import json
import urllib.request
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
import os
import tempfile
import requests
import speech_recognition as sr
from .models import UserProfile, Post, Comment, BodyMeasurement


def admin_required(view_func):
    """Decorator: user must be logged in AND have admin role."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = UserProfile.objects.get_or_create(user=request.user)[0]
        if not profile.is_admin:
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def _geo_request(url, timeout=5):
    """Make a geo-IP API request with retry logic."""
    last_error = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'MySite/1.0'})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except Exception as e:
            last_error = e
            if attempt < 2:
                import time
                time.sleep(0.5)  # Brief delay before retry
    raise last_error


def get_geo_location(ip):
    """Resolve IP address to a human-readable location string.

    Uses ip-api.com as primary, ipinfo.io as fallback.
    When the client IP is localhost, queries for this machine's public IP
    to determine the actual geographic location.
    """
    is_local = ip in ('127.0.0.1', 'localhost', '::1', '')

    if is_local:
        # Query for public IP + location in one request
        urls = [
            'http://ip-api.com/json/?fields=query,city,regionName,country',
            'https://ipinfo.io/json',
        ]
    else:
        urls = [
            f'http://ip-api.com/json/{ip}?fields=city,regionName,country',
            f'https://ipinfo.io/{ip}/json',
        ]

    for url in urls:
        try:
            data = _geo_request(url)

            if 'ipinfo.io' in url:
                # ipinfo.io response format: {"ip": "...", "city": "...", "region": "...", "country": "..."}
                resolved_ip = data.get('ip', ip) if is_local else ip
                parts = [data.get('city', ''), data.get('region', ''), data.get('country', '')]
            else:
                # ip-api.com format
                resolved_ip = data.get('query', ip) if is_local else ip
                parts = [data.get('city', ''), data.get('regionName', ''), data.get('country', '')]

            parts = [p for p in parts if p]
            location = ', '.join(parts) if parts else 'Unknown'
            return resolved_ip, location
        except Exception:
            continue  # Try next URL

    # All APIs failed
    return ip, 'Unknown'


def update_login_info(request, user):
    """Capture IP and geo-location after login, save to UserProfile."""
    ip = get_client_ip(request)
    resolved_ip, location = get_geo_location(ip)
    profile, created = UserProfile.objects.get_or_create(user=user)

    # First user to register automatically becomes admin
    if created and not UserProfile.objects.filter(role=UserProfile.Role.ADMIN).exists():
        profile.role = UserProfile.Role.ADMIN

    profile.last_login_ip = resolved_ip or ip
    profile.last_login_location = location
    profile.save()


def home(request):
    """Landing page with links to login and register."""
    return render(request, 'accounts/home.html')


def weight_data(request):
    """Display all body measurement records in a table, newest first."""
    measurements = BodyMeasurement.objects.all()
    return render(request, 'accounts/weight_data.html', {
        'measurements': measurements,
    })


@login_required
def weight_delete(request, pk):
    """Delete a single body measurement record."""
    record = get_object_or_404(BodyMeasurement, pk=pk)
    record.delete()
    return JsonResponse({'success': True})


@csrf_exempt
def weight_upload(request):
    """Upload a body measurement screenshot, extract data via local OCR (primary) or vision API (fallback)."""
    if request.method != 'POST' or not request.FILES.get('image'):
        return JsonResponse({'error': '请上传图片'}, status=400)
    
    image = request.FILES['image']
    
    # Save image temporarily
    suffix = os.path.splitext(image.name)[1] or '.jpg'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        for chunk in image.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name
    
    from datetime import datetime
    from django.utils import timezone
    
    try:
        # ========== STEP 1: Try local Windows OCR (free, unlimited) ==========
        from .scale_ocr import ocr_scale_image
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            ocr_result = ocr_scale_image(tmp_path)
            logger.info(f"Local OCR result: {ocr_result}")
        except ImportError:
            logger.info("winrt not available, skipping local OCR")
            ocr_result = {}
        
        dt = datetime.now().replace(tzinfo=timezone.get_current_timezone())
        
        # Use OCR-extracted date if available
        ocr_date = ocr_result.get('date')
        ocr_time = ocr_result.get('time')
        if ocr_date:
            try:
                if ocr_time:
                    dt = datetime.strptime(f'{ocr_date} {ocr_time}', '%Y-%m-%d %H:%M')
                else:
                    dt = datetime.strptime(ocr_date, '%Y-%m-%d')
                dt = dt.replace(tzinfo=timezone.get_current_timezone())
            except (ValueError, TypeError):
                pass
        
        record = BodyMeasurement(measured_at=dt)
        
        # Map OCR fields to Django model fields (OCR returns values in 斤 already)
        field_map = {
            'weight_jin': ('weight_jin', float),
            'bmi': ('bmi', float),
            'body_fat_pct': ('body_fat_pct', float),
            'body_fat_score': ('body_fat_score', lambda v: int(float(v))),
            'skeletal_muscle_jin': ('skeletal_muscle_jin', float),
            'visceral_fat_level': ('visceral_fat_level', float),
            'arms_legs_muscle_index': ('arms_legs_muscle_index', float),
            'waist_hip_ratio': ('waist_hip_ratio', float),
            'body_water_pct': ('body_water_pct', float),
            'protein_pct': ('protein_pct', float),
            'fat_free_mass_jin': ('fat_free_mass_jin', float),
            'basal_metabolism_kcal': ('basal_metabolism_kcal', lambda v: int(float(v))),
            'body_age': ('body_age', lambda v: int(float(v))),
            'heart_rate': ('heart_rate', lambda v: int(float(v))),
        }
        for ocr_key, (model_field, conv) in field_map.items():
            val = ocr_result.get(ocr_key)
            if val is not None:
                try:
                    setattr(record, model_field, conv(val))
                except (ValueError, TypeError):
                    pass
        
        # Check if we have at least weight data
        has_weight = bool(ocr_result.get('weight_jin'))
        
        if has_weight:
            record.save()
            # Build response with all available fields
            resp = {
                'success': True,
                'source': 'local_ocr',
                'id': record.id,
                'date': dt.strftime('%Y-%m-%d %H:%M'),
            }
            for f in ['weight_jin', 'bmi', 'body_fat_pct', 'body_fat_score',
                       'skeletal_muscle_jin', 'visceral_fat_level',
                       'arms_legs_muscle_index', 'waist_hip_ratio',
                       'body_water_pct', 'protein_pct', 'fat_free_mass_jin',
                       'basal_metabolism_kcal', 'body_age', 'heart_rate']:
                v = getattr(record, f, None)
                if v is not None:
                    resp[f] = str(v)
            return JsonResponse(resp)
        
        # ========== STEP 2: Fallback to DeepSeek Vision API ==========
        import base64
        with open(tmp_path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Get API key from env or settings
        api_key = os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPENROUTER_API_KEY')
        if not api_key:
            return JsonResponse({'error': '未配置API密钥'}, status=500)
        
        # Call DeepSeek vision API (V4 Flash supports images)
        resp = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'nvidia/nemotron-nano-12b-v2-vl:free',
                'messages': [{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': (
                            '从这张体脂秤截图中提取所有健康数据，返回纯JSON格式（不要markdown、不要注释）：\n'
                            '{\n'
                            '  "date": "YYYY-MM-DD",\n'
                            '  "time": "HH:MM",\n'
                            '  "weight_jin": 0.0,\n'
                            '  "bmi": 0.0,\n'
                            '  "body_fat_pct": 0.0,\n'
                            '  "body_fat_score": 0,\n'
                            '  "skeletal_muscle_jin": 0.0,\n'
                            '  "visceral_fat_level": 0.0,\n'
                            '  "arms_legs_muscle_index": 0.0,\n'
                            '  "waist_hip_ratio": 0.00,\n'
                            '  "body_water_pct": 0.0,\n'
                            '  "protein_pct": 0.0,\n'
                            '  "bone_mineral_jin": 0.00,\n'
                            '  "fat_free_mass_jin": 0.0,\n'
                            '  "basal_metabolism_kcal": 0,\n'
                            '  "body_age": 0,\n'
                            '  "heart_rate": 0,\n'
                            '  "body_type": "",\n'
                            '  "body_shape": ""\n'
                            '}\n'
                            '如果某个数据不存在，设为null。日期时间从图片左上角读取。'
                        )},
                        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
                    ],
                }],
                'max_tokens': 1024,
            },
            timeout=60,
        )
        
        if resp.status_code != 200:
            return JsonResponse({'error': f'API请求失败: {resp.status_code}'}, status=500)
        
        result = resp.json()
        content = result['choices'][0]['message']['content']
        
        # Parse JSON from response (handle markdown-wrapped JSON)
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            return JsonResponse({'error': '无法解析返回数据'}, status=500)
        
        data = json.loads(json_match.group())
        
        # Parse date/time
        from datetime import datetime
        from django.utils import timezone
        
        date_str = data.get('date', '')
        time_str = data.get('time', '')
        if date_str and time_str:
            dt = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %H:%M')
        elif date_str:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            dt = datetime.now()
        dt = dt.replace(tzinfo=timezone.get_current_timezone())
        
        # Create record (only save fields that have values)
        record = BodyMeasurement(measured_at=dt)
        field_map = {
            'weight_jin': float, 'bmi': float, 'body_fat_pct': float,
            'body_fat_score': lambda v: int(float(v)) if v is not None else None,
            'skeletal_muscle_jin': float, 'visceral_fat_level': float,
            'arms_legs_muscle_index': float, 'waist_hip_ratio': float,
            'body_water_pct': float, 'protein_pct': float, 'bone_mineral_jin': float,
            'fat_free_mass_jin': float, 'basal_metabolism_kcal': lambda v: int(float(v)) if v is not None else None,
            'body_age': lambda v: int(float(v)) if v is not None else None,
            'heart_rate': lambda v: int(float(v)) if v is not None else None,
            'body_type': str, 'body_shape': str,
        }
        for field, conv in field_map.items():
            val = data.get(field)
            if val is not None:
                try:
                    setattr(record, field, conv(val))
                except (ValueError, TypeError):
                    pass
        
        record.save()
        
        return JsonResponse({
            'success': True,
            'id': record.id,
            'date': dt.strftime('%Y-%m-%d %H:%M'),
            'weight': str(record.weight_jin),
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass


def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('post_list')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            update_login_info(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account has been created.')
            return redirect('post_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('post_list')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            update_login_info(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('post_list')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """User logout view."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def success_view(request):
    """Success page shown after login."""
    all_users = User.objects.select_related('profile').all().order_by('-last_login')
    return render(request, 'accounts/success.html', {'all_users': all_users})


# ── Post views ──────────────────────────────────────────────────────────────

PER_PAGE_OPTIONS = [10, 20, 50, 100]
DEFAULT_PER_PAGE = 10


def _paginate_posts(request):
    """Return page_obj for post queryset, with configurable per_page."""
    qs = Post.objects.select_related('author').all()

    per_page = request.GET.get('per_page', str(DEFAULT_PER_PAGE))
    try:
        per_page = int(per_page)
        if per_page not in PER_PAGE_OPTIONS:
            per_page = DEFAULT_PER_PAGE
    except (ValueError, TypeError):
        per_page = DEFAULT_PER_PAGE

    paginator = Paginator(qs, per_page)
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)
    return page_obj


def post_list(request):
    """Public list of all posts, paginated."""
    page_obj = _paginate_posts(request)
    return render(request, 'accounts/post_list.html', {
        'posts': page_obj.object_list, 'page_obj': page_obj,
        'per_page_options': PER_PAGE_OPTIONS,
    })


def post_detail(request, post_id):
    """Public detail view for a single post, with paginated sidebar and comments."""
    post = get_object_or_404(Post.objects.select_related('author'), pk=post_id)

    # Handle comment / reply submission
    if request.method == 'POST' and request.user.is_authenticated:
        comment_text = request.POST.get('comment', '').strip()
        parent_id = request.POST.get('parent_id', '')
        audio_file = request.FILES.get('audio')

        # Require at least text or audio
        if not comment_text and not audio_file:
            messages.error(request, 'Comment cannot be empty.')
        elif comment_text and len(comment_text) > 2000:
            messages.error(request, 'Comment too long (max 2000 characters).')
        else:
            parent = None
            if parent_id:
                parent = get_object_or_404(Comment, pk=parent_id, post=post)
            Comment.objects.create(
                post=post, author=request.user, content=comment_text,
                parent=parent, audio=audio_file
            )
            messages.success(request, 'Comment added.')
        redirect_url = request.path
        if request.GET:
            redirect_url += '?' + request.GET.urlencode()
        return HttpResponseRedirect(redirect_url)

    page_obj = _paginate_posts(request)
    source_lang = _detect_language(post.content)
    comments = post.comments.select_related('author').all()
    return render(request, 'accounts/post_detail.html', {
        'post': post, 'page_obj': page_obj,
        'per_page_options': PER_PAGE_OPTIONS,
        'source_lang': source_lang,
        'comments': comments,
    })


# ── Received Comments ────────────────────────────────────────────────────────

@login_required
def received_comments(request):
    """Show all comments received on the current user's posts."""
    comments = Comment.objects.filter(
        post__author=request.user
    ).exclude(
        author=request.user  # exclude own comments
    ).select_related('author', 'post', 'parent').order_by('post_id', '-created_at')

    # Build list of (comment, show_title) — title only shown for first comment per post
    comment_rows = []
    seen_posts = set()
    for c in comments:
        show_title = c.post_id not in seen_posts
        if show_title:
            seen_posts.add(c.post_id)
        comment_rows.append((c, show_title))

    # If a post_id is provided, show that post's detail on the right
    selected_post = None
    selected_comments = []
    post_id = request.GET.get('post_id')
    if post_id:
        selected_post = get_object_or_404(
            Post.objects.select_related('author').filter(author=request.user),
            pk=post_id
        )
        selected_comments = selected_post.comments.select_related('author').all()

    return render(request, 'accounts/received_comments.html', {
        'comment_rows': comment_rows,
        'selected_post': selected_post,
        'selected_comments': selected_comments,
    })


@login_required
def post_create(request):
    """Create a new post (login required)."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        if title and content:
            post = Post.objects.create(title=title, content=content, author=request.user)
            messages.success(request, 'Post published!')
            return redirect('post_detail', post_id=post.id)
        else:
            messages.error(request, 'Title and content are required.')
    return render(request, 'accounts/post_create.html')


# ── Admin: User Management ───────────────────────────────────────────────────

@admin_required
def user_manage(request):
    """List all users — admin only."""
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    return render(request, 'accounts/user_manage.html', {'all_users': users})


@admin_required
def user_create(request):
    """Admin creates a new user."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        role = request.POST.get('role', 'user')

        errors = []
        if not username:
            errors.append('Username is required.')
        if User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        if not password1:
            errors.append('Password is required.')
        elif password1 != password2:
            errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
            messages.success(request, f'User "{username}" created.')
            return redirect('user_manage')

    return render(request, 'accounts/user_edit.html', {
        'edit_user': None, 'edit_profile': None
    })


@admin_required
def user_edit(request, user_id):
    """Admin edits an existing user."""
    edit_user = get_object_or_404(User, pk=user_id)
    edit_profile, _ = UserProfile.objects.get_or_create(user=edit_user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        role = request.POST.get('role', edit_profile.role)

        errors = []
        if not username:
            errors.append('Username is required.')
        if User.objects.filter(username=username).exclude(pk=user_id).exists():
            errors.append('Username already taken.')
        if password1:
            if password1 != password2:
                errors.append('Passwords do not match.')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            edit_user.username = username
            edit_user.email = email
            if password1:
                edit_user.set_password(password1)
            edit_user.save()
            edit_profile.role = role
            edit_profile.save()
            messages.success(request, f'User "{username}" updated.')
            return redirect('user_manage')

    return render(request, 'accounts/user_edit.html', {
        'edit_user': edit_user, 'edit_profile': edit_profile
    })


@admin_required
def user_delete(request, user_id):
    """Admin deletes a user."""
    target = get_object_or_404(User, pk=user_id)
    if target == request.user:
        messages.error(request, 'You cannot delete yourself.')
    else:
        username = target.username
        target.delete()
        messages.success(request, f'User "{username}" has been deleted.')
    return redirect('user_manage')


# ── Audio Transcription ──────────────────────────────────────────────────────

@csrf_exempt
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
                pass


# ── Translation ──────────────────────────────────────────────────────────────

SUPPORTED_LANGS = {
    'zh': 'Chinese', 'en': 'English',
    'ja': 'Japanese', 'ko': 'Korean',
}

# Language codes for translation APIs
LANG_CODES = {
    'zh': 'zh-CN',
    'en': 'en-US',
    'ja': 'ja',
    'ko': 'ko',
}

MYMEMORY_URL = 'https://api.mymemory.translated.net/get'


def _detect_language(text):
    """Detect language from character ranges. Returns 'zh', 'en', 'ja', or 'ko'."""
    if not text:
        return 'en'
    # Count characters in each script
    cjk_unified = sum(1 for c in text if '一' <= c <= '鿿')
    hiragana = sum(1 for c in text if '぀' <= c <= 'ゟ')
    katakana = sum(1 for c in text if '゠' <= c <= 'ヿ')
    hangul = sum(1 for c in text if '가' <= c <= '힯' or 'ᄀ' <= c <= 'ᇿ')
    ascii_chars = sum(1 for c in text if ord(c) < 128)

    total = max(len(text), 1)

    # Japanese: significant hiragana/katakana
    if (hiragana + katakana) / total > 0.05:
        return 'ja'
    # Korean: significant Hangul
    if hangul / total > 0.05:
        return 'ko'
    # Chinese: significant CJK unified ideographs
    if cjk_unified / total > 0.1:
        return 'zh'
    # Default: English
    return 'en'


def _translate_text(text, source, target):
    """Translate text via MyMemory API with strict timeout."""
    src_code = LANG_CODES.get(source, 'en-US')
    tgt_code = LANG_CODES.get(target, 'zh-CN')

    # Split into manageable chunks (MyMemory limit ~500 chars)
    chunks = _split_for_translation(text, 450)

    translated_chunks = []
    for chunk in chunks:
        try:
            resp = requests.get(
                MYMEMORY_URL,
                params={'q': chunk, 'langpair': f'{src_code}|{tgt_code}'},
                timeout=3,
            )
            if resp.status_code == 200:
                data = resp.json()
                translated = data.get('responseData', {}).get('translatedText', chunk)
                translated_chunks.append(translated)
            else:
                translated_chunks.append(chunk)  # keep original on error
        except requests.exceptions.Timeout:
            translated_chunks.append(chunk)
        except Exception:
            translated_chunks.append(chunk)

    return '\n\n'.join(translated_chunks)


def _split_for_translation(text, max_len):
    """Split text into chunks under max_len, preserving sentence boundaries."""
    if len(text) <= max_len:
        return [text]

    # Split by double newlines (paragraphs) first
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks = []
    current = ''
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_len:
            current = (current + '\n\n' + para).strip() if current else para
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)

    # Second pass: split any chunk that's still too long into sentences
    result = []
    for chunk in chunks:
        if len(chunk) <= max_len:
            result.append(chunk)
            continue

        # Split by sentences using both English and Chinese punctuation
        import re
        sentences = re.split(r'(?<=[.!?！？。])\s+', chunk)
        sentences = [s.strip() for s in sentences if s.strip()]

        sub = ''
        for sent in sentences:
            if len(sent) > max_len:
                # Force-split long sentences at word boundaries
                if sub:
                    result.append(sub.strip())
                    sub = ''
                # Split this long sentence into max_len pieces
                words = sent.split(' ')
                piece = ''
                for w in words:
                    if len(piece) + len(w) + 1 <= max_len:
                        piece = (piece + ' ' + w).strip() if piece else w
                    else:
                        if piece:
                            result.append(piece)
                        piece = w
                if piece:
                    result.append(piece)
            elif len(sub) + len(sent) + 1 <= max_len:
                sub = (sub + ' ' + sent).strip() if sub else sent
            else:
                if sub:
                    result.append(sub.strip())
                sub = sent
        if sub:
            result.append(sub.strip())

    return result or [text]


def translate_post(request, post_id):
    """Return translated post content as JSON. Supports EN<->ZH."""
    post = get_object_or_404(Post, pk=post_id)
    target = request.GET.get('lang', 'en')

    if target not in SUPPORTED_LANGS:
        return JsonResponse({'error': 'Unsupported language'}, status=400)

    # Detect source language from content character ranges
    source = _detect_language(post.content)

    # If target matches source, return original
    if target == source:
        return JsonResponse({'title': post.title, 'content': post.content, 'lang': target})

    try:
        translated_content = _translate_text(post.content, source, target)
        translated_title = _translate_text(post.title, source, target)
    except Exception:
        return JsonResponse({
            'error': 'Translation service unavailable. Please try again later.',
        }, status=503)

    return JsonResponse({
        'title': translated_title,
        'content': translated_content,
        'lang': target,
    })
