"""Step definitions for navigation and internationalization features."""

from pytest_bdd import step, parsers


@step(parsers.parse('I switch the language to "{language}"'), type_=None)
def switch_language(page, language):
    lang_map = {
        'Chinese': 'zh-hans',
        'English': 'en',
        '简体中文': 'zh-hans',
    }
    lang_code = lang_map.get(language, language)
    page.select_option('.lang-switcher select', lang_code)
    page.wait_for_load_state('networkidle')


@step('I click the language switcher', type_=None)
def click_lang_switcher(page):
    page.click('.lang-switcher select')


@step(parsers.parse('the page should display text in {language}'), type_=None)
def page_in_language(page, language):
    checks = {
        'Chinese': ['首页', '帖子', '登录', '注册'],
        'English': ['Home', 'Posts', 'Login', 'Register'],
    }
    for phrase in checks.get(language, checks['English']):
        if page.locator(f'text={phrase}').is_visible():
            return
    all_text = page.text_content('body')
    raise AssertionError(
        f'No {language} text found. Body text (first 300): {all_text[:300]}'
    )


@step(parsers.parse('the nav bar should display "{text}"'), type_=None)
def nav_bar_displays(page, text):
    assert page.locator(f'nav a:has-text("{text}")').is_visible(), \
        f'Nav bar does not display "{text}"'


@step('the language switcher should be present', type_=None)
def lang_switcher_present(page):
    assert page.locator('.lang-switcher').is_visible(), \
        'Language switcher not visible'


@step(parsers.parse('every page should have a working nav bar with "{link}"'), type_=None)
def every_page_nav(page, link):
    urls = ['/', '/login/', '/register/', '/posts/']
    for url in urls:
        page.goto(page._base_url + url)
        page.wait_for_load_state('networkidle')
        assert page.locator(f'nav a:has-text("{link}")').is_visible(), \
            f'Nav link "{link}" missing on {url}'


@step(parsers.parse('the current page URL should contain "{fragment}"'), type_=None)
def url_contains(page, fragment):
    assert fragment in page.url, f'URL {page.url} does not contain "{fragment}"'
