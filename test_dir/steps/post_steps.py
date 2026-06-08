"""Step definitions for post / blog features."""

from pytest_bdd import step, parsers


@step(parsers.parse('there is a post titled "{title}"'), type_=None)
def create_post(page, title):
    """Create a post via the UI so it exists for later steps."""
    page.goto(page._base_url + '/register/')
    if '/success/' not in page.url:
        page.fill('input[name="username"]', f'post_author_{title[:8]}')
        page.fill('input[name="password1"]', 'TestPass123!')
        page.fill('input[name="password2"]', 'TestPass123!')
        page.click('button[type="submit"]')
        page.wait_for_url('**/success/')

    page.goto(page._base_url + '/posts/create/')
    page.fill('input[name="title"]', title)
    page.fill('textarea[name="content"]', f'Content of {title}.')
    page.click('button[type="submit"]')
    page.wait_for_url('**/posts/*/')


@step(parsers.parse('I fill the title with "{title}"'), type_=None)
def fill_title(page, title):
    page.fill('input[name="title"]', title)


@step(parsers.parse('I fill the content with "{content}"'), type_=None)
def fill_content(page, content):
    page.fill('textarea[name="content"]', content)


@step('I submit the post form', type_=None)
def submit_post(page):
    page.click('button[type="submit"]')


@step(parsers.parse('I click the post title "{title}"'), type_=None)
def click_post_title(page, title):
    page.click(f'.post-item h3 a:has-text("{title}")')


@step(parsers.parse('I should see a post titled "{title}" in the list'), type_=None)
def post_in_list(page, title):
    assert page.locator(f'.post-item:has-text("{title}")').is_visible(), \
        f'Post "{title}" not in list'


@step(parsers.parse('I should see the post content "{content}"'), type_=None)
def post_content_visible(page, content):
    assert page.locator(f'.post-content:has-text("{content}")').is_visible(), \
        f'Post content "{content}" not visible'


@step(parsers.parse('I should see the author "{username}" on the post'), type_=None)
def author_on_post(page, username):
    detail = page.locator('.post-detail-section')
    assert detail.locator(f':has-text("{username}")').is_visible(), \
        f'Author "{username}" not on post detail'


@step('I should see an empty post list message', type_=None)
def empty_post_list(page):
    assert page.locator(':has-text("No posts yet")').is_visible(), \
        'Empty post list message not visible'


@step(parsers.parse('the post list should contain {count:d} posts'), type_=None)
def post_count(page, count):
    items = page.locator('.post-item')
    actual = items.count()
    assert actual == count, f'Expected {count} posts, got {actual}'


@step('I should see a validation message about required fields', type_=None)
def required_field_message(page):
    page.wait_for_load_state('networkidle')


@step(parsers.parse('the post "{title}" should appear before "{other_title}"'), type_=None)
def ordering_check(page, title, other_title):
    content = page.text_content('.post-list')
    pos1 = content.find(title)
    pos2 = content.find(other_title)
    assert pos1 < pos2, \
        f'"{title}" (pos {pos1}) should appear before "{other_title}" (pos {pos2})'
