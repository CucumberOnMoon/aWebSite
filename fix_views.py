"""Patch views.py for comment reply support."""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(BASE, 'accounts', 'views.py')

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update comment text
old = 'Handle comment submission'
content = content.replace(old, 'Handle comment / reply submission')

# 2. Add parent_id extraction
old2 = """comment_text = request.POST.get('comment', '').strip()
        if comment_text and len(comment_text) <= 2000:"""
new2 = """comment_text = request.POST.get('comment', '').strip()
        parent_id = request.POST.get('parent_id', '')

        if comment_text and len(comment_text) <= 2000:"""
content = content.replace(old2, new2)

# 3. Update Comment.objects.create
old3 = """Comment.objects.create(
                post=post, author=request.user, content=comment_text
            )"""
new3 = """parent = None
            if parent_id:
                parent = get_object_or_404(Comment, pk=parent_id, post=post)
            Comment.objects.create(
                post=post, author=request.user, content=comment_text, parent=parent
            )"""
content = content.replace(old3, new3)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('views.py patched successfully')
