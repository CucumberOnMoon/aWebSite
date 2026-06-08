"""Patch views.py for audio comment support."""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'accounts', 'views.py')

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the comment submission block
old = """    # Handle comment / reply submission
    if request.method == 'POST' and request.user.is_authenticated:
        comment_text = request.POST.get('comment', '').strip()
        parent_id = request.POST.get('parent_id', '')

        if comment_text and len(comment_text) <= 2000:
            parent = None
            if parent_id:
                parent = get_object_or_404(Comment, pk=parent_id, post=post)
            Comment.objects.create(
                post=post, author=request.user, content=comment_text, parent=parent
            )
            messages.success(request, 'Comment added.')
        elif not comment_text:
            messages.error(request, 'Comment cannot be empty.')
        else:
            messages.error(request, 'Comment too long (max 2000 characters).')
        redirect_url = request.path
        if request.GET:
            redirect_url += '?' + request.GET.urlencode()
        return HttpResponseRedirect(redirect_url)"""

new = """    # Handle comment / reply submission
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
        return HttpResponseRedirect(redirect_url)"""

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('views.py patched for audio support')
else:
    print('ERROR: old string not found')
    # Debug: find the comment text
    idx = content.find('Handle comment')
    if idx >= 0:
        print('Found at index', idx)
        print(repr(content[idx:idx+200]))
