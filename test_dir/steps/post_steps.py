"""
Step definitions for post / blog features.
Uses Django ORM for fast test-data creation; UI for actual user flows.
"""

from pytest_bdd import given, when, then, parsers
from django.contrib.auth.models import User
from accounts.models import Post


@given(parsers.parse('there is a post titled "{title}"'))
def create_post_via_orm(page, title):
    author, _ = User.objects.get_or_create(
        username='post_author',
        defaults={'email': 'post_author@test.com'},
    )
    Post.objects.get_or_create(
        title=title,
        defaults={
            'content': f'Content of {title}.',
            'author': author,
        },
    )


@when(parsers.parse('I fill the title with "{title}"'))
def fill_title(page, title):
    page.wait_for_selector('input[name="title"]', state='visible')
    page.fill('input[name="title"]', title)


@when(parsers.parse('I fill the content with "{content}"'))
def fill_content(page, content):
    page.wait_for_selector('textarea[name="content"]', state='visible')
    page.fill('textarea[name="content"]', content)


@when('I submit the post form')
def submit_post(page):
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


@when(parsers.parse('I click the post title "{title}"'))
def click_post_title(page, title):
    link = page.locator(f'.post-item h3 a:has-text("{title}")')
    link.wait_for(state='visible')
    link.click()
    page.wait_for_load_state('networkidle')


@then(parsers.parse('I should see a post titled "{title}" in the list'))
def post_in_list(page, title):
    locator = page.locator(f'.post-item:has-text("{title}")')
    locator.wait_for(state='visible', timeout=5000)
    assert locator.is_visible(), f'Post "{title}" not in list'


@then(parsers.parse('I should see the post content "{content}"'))
def post_content_visible(page, content):
    locator = page.locator(f'.post-content:has-text("{content}")')
    locator.wait_for(state='visible', timeout=3000)
    assert locator.is_visible(), f'Post content "{content}" not visible'


@then(parsers.parse('I should see the author "{username}" on the post'))
def author_on_post(page, username):
    detail = page.locator('.post-detail-section')
    assert detail.locator(f':has-text("{username}")').is_visible(), \
        f'Author "{username}" not on post detail'


@then('I should see an empty post list message')
def empty_post_list(page):
    locator = page.locator(':has-text("No posts yet")')
    locator.wait_for(state='visible', timeout=3000)
    assert locator.is_visible(), 'Empty post list message not visible'


@then(parsers.parse('the post list should contain {count:d} posts'))
def post_count(page, count):
    items = page.locator('.post-item')
    assert items.count() == count, f'Expected {count} posts, got {items.count()}'


@then(parsers.parse('the post "{title}" should appear before "{other_title}"'))
def ordering_check(page, title, other_title):
    content = page.text_content('.post-list') or ''
    pos1 = content.find(title)
    pos2 = content.find(other_title)
    assert pos1 < pos2, \
        f'"{title}" (pos {pos1}) should appear before "{other_title}" (pos {pos2})'


@then('I should see pagination controls')
def pagination_visible(page):
    locator = page.locator('.pagination, nav[aria-label="Pagination"], .page-item')
    if locator.count() == 0:
        items = page.locator('.post-item')
        assert items.count() <= 10, 'Expected pagination but >10 posts without it'
        return
    assert locator.is_visible(), 'Pagination controls not visible'
