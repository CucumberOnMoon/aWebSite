#!/usr/bin/env python3
"""Generate test_documentation.pdf for the aWebSite Django project."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem, HRFlowable
)
from reportlab.lib import colors
import os

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_documentation.pdf')

# ── Styles ──────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=26, leading=32,
                              spaceAfter=6, textColor=HexColor('#1a1a2e'))
subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=13, leading=18,
                                 spaceAfter=20, textColor=HexColor('#555555'))
h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=18, leading=24,
                     spaceBefore=20, spaceAfter=10, textColor=HexColor('#1a1a2e'))
h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, leading=18,
                     spaceBefore=14, spaceAfter=6, textColor=HexColor('#2d3436'))
h3 = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=12, leading=16,
                     spaceBefore=10, spaceAfter=4, textColor=HexColor('#444444'))
body = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=15,
                       spaceAfter=6, spaceBefore=2)
code = ParagraphStyle('Code', parent=styles['Code'], fontSize=8, leading=11,
                       leftIndent=10, spaceAfter=4, spaceBefore=4,
                       backColor=HexColor('#f4f4f4'))
bullet = ParagraphStyle('Bullet', parent=body, leftIndent=20, spaceAfter=2,
                         bulletIndent=10)
note = ParagraphStyle('Note', parent=body, leftIndent=10, spaceBefore=6, spaceAfter=6,
                       backColor=HexColor('#fff3cd'), borderPadding=6)

# ── Helpers ─────────────────────────────────────────────────────────────────

def hr():
    return HRFlowable(width="100%", thickness=1, color=HexColor('#dddddd'),
                      spaceBefore=8, spaceAfter=8)

def bullet_list(items):
    return ListFlowable(
        [ListItem(Paragraph(t, bullet), bulletColor=HexColor('#2d3436')) for t in items],
        bulletType='bullet',
        start=None,
        bulletFontSize=8,
    )

def make_table(data, col_widths=None):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f8f9fa'), colors.white]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t


# ── Build PDF ───────────────────────────────────────────────────────────────

doc = SimpleDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=20*mm, bottomMargin=20*mm,
)

elements = []

# ── Cover ───────────────────────────────────────────────────────────────────
elements.append(Spacer(1, 80))
elements.append(Paragraph('aWebSite', title_style))
elements.append(Paragraph('Test Documentation & Deployment Guide', subtitle_style))
elements.append(hr())
elements.append(Spacer(1, 20))
elements.append(Paragraph('Project: D:\\gitSpace\\aWebSite', body))
elements.append(Paragraph('Framework: Django 5.2 + pytest-bdd 8.x + Playwright', body))
elements.append(Paragraph('Language: Python 3.11 (VPS) / 3.13 (Dev)', body))
elements.append(Spacer(1, 30))
elements.append(Paragraph(f'Generated: June 2026', body))

elements.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 1. Project Overview
# ══════════════════════════════════════════════════════════════════════════════
elements.append(Paragraph('1. Project Overview', h1))
elements.append(hr())

elements.append(Paragraph(
    'aWebSite is a Django-based personal website with user authentication, '
    'blog posts, body weight tracking (with screenshot OCR), user management, '
    'and internationalization (English/Chinese).', body))

elements.append(Paragraph('Core Features', h2))
elements.append(bullet_list([
    'User registration, login, logout, password management',
    'Blog post CRUD with pagination and i18n translation support',
    'Body weight tracking: upload scale screenshots, OCR extracts measurement data',
    'User management dashboard with IP/location tracking',
    'Django admin interface for content moderation',
    'Language switching (English / Simplified Chinese)',
    'Responsive UI with CSS styling',
]))

elements.append(Paragraph('Architecture', h2))
elements.append(make_table([
    ('Component', 'Technology', 'Notes'),
    ('Backend', 'Django 5.2', 'SQLite database'),
    ('Frontend', 'HTML + CSS + Django Templates', 'No JavaScript framework'),
    ('OCR', 'winrt (Win) / Tesseract (Linux)', 'Free, local OCR'),
    ('Vision Fallback', 'OpenRouter API', 'When local OCR fails'),
    ('Tests', 'pytest-bdd + Playwright', 'BDD + browser automation'),
    ('Production', 'VPS CentOS 7 (23.224.152.81:8000)', 'Python 3.11, no Docker'),
]))

elements.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 2. Deployment
# ══════════════════════════════════════════════════════════════════════════════
elements.append(Paragraph('2. Deployment', h1))
elements.append(hr())

elements.append(Paragraph('2.1 VPS Info', h2))
elements.append(make_table([
    ('Item', 'Value'),
    ('IP', '23.224.152.81'),
    ('OS', 'CentOS 7.9 (1 CPU, 351MB RAM)'),
    ('Python', '/usr/local/python311/bin/python3 (3.11.11)'),
    ('Django', '5.2.15'),
    ('Port', '8000 (iptables opened)'),
    ('DB', 'SQLite (db.sqlite3, SQLite 3.49.1)'),
], col_widths=[120, 320]))

elements.append(Paragraph('2.2 Quick Deploy', h2))
elements.append(Paragraph(
    'From the local Windows machine (D:\\gitSpace\\aWebSite):', body))
elements.append(Paragraph(
    '<b>Step 1:</b> Package the project', body))
elements.append(Paragraph(
    'cd "D:/gitSpace/aWebSite" && tar czf /tmp/aweb.tar.gz '
    '--exclude=website --exclude=__pycache__ --exclude=.claude '
    '--exclude=*.pyc --exclude=.git .', code))
elements.append(Spacer(1, 4))
elements.append(Paragraph(
    '<b>Step 2:</b> Transfer via SCP (password auth via SSH_ASKPASS)', body))
elements.append(Paragraph(
    'scp -o StrictHostKeyChecking=no /tmp/aweb.tar.gz root@23.224.152.81:/root/', code))
elements.append(Spacer(1, 4))
elements.append(Paragraph(
    '<b>Step 3:</b> Extract & migrate on VPS', body))
elements.append(Paragraph(
    'export PATH=/usr/local/python311/bin:$PATH\\n'
    'export LD_LIBRARY_PATH="/usr/local/lib:/usr/lib64/openssl11:$LD_LIBRARY_PATH"\\n'
    'cd /root && tar xzf aweb.tar.gz\\n'
    'python3 manage.py makemigrations\\n'
    'python3 manage.py migrate\\n'
    'python3 manage.py collectstatic --noinput', code))
elements.append(Spacer(1, 4))
elements.append(Paragraph(
    '<b>Step 4:</b> Start the server', body))
elements.append(Paragraph(
    'pkill -f "manage.py" 2>/dev/null; sleep 1\\n'
    'nohup python3 manage.py runserver 0.0.0.0:8000 > /tmp/django.log 2>&1 &', code))

elements.append(Paragraph('2.3 Dependencies', h2))
elements.append(Paragraph(
    'VPS Python packages: django, python-dotenv, requests, SpeechRecognition, '
    'Pillow, pytesseract. System packages: tesseract + chi_sim language data, '
    'openssl11, sqlite 3.49.1 (compiled from source).', body))

elements.append(Spacer(1, 10))
note_text = Paragraph(
    '<b>⚠ Note:</b> The VPS has limited resources (351MB RAM, 1 CPU). '
    'The dev server (manage.py runserver) is sufficient for personal use. '
    'For production, consider gunicorn + nginx.', note)
elements.append(note_text)

elements.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 3. Test Design Methodology
# ══════════════════════════════════════════════════════════════════════════════
elements.append(Paragraph('3. Test Design Methodology', h1))
elements.append(hr())

elements.append(Paragraph('3.1 Approach: BDD + Playwright', h2))
elements.append(Paragraph(
    'Tests use <b>pytest-bdd</b> (Gherkin language) for human-readable scenario '
    'specifications combined with <b>Playwright</b> for browser automation. '
    'This gives us:', body))
elements.append(bullet_list([
    'Executable specifications — feature files are both documentation and tests',
    'Real browser rendering — tests run against Chromium via Playwright',
    'Isolation — each scenario gets a fresh browser context',
    'Live Django server — conftest.py auto-starts a dev server per session',
    'Django ORM access — test data creation via ORM (not UI) for speed',
]))

elements.append(Paragraph('3.2 Architecture', h2))
elements.append(Paragraph(
    'test_dir/', body))
elements.append(Paragraph(
    '├── conftest.py              # All fixtures + ALL step definitions\\n'
    '│   (Django setup, live server, Playwright browser, page, screenshots)\\n'
    '├── test_scenarios.py         # Loads all .feature files\\n'
    '├── pytest.ini                # Markers for test categorization\\n'
    '├── features/                 # Gherkin feature files (.feature)\\n'
    '│   ├── authentication.feature (6 scenarios)\\n'
    '│   ├── posts.feature         (6 scenarios)\\n'
    '│   ├── navigation.feature    (7 scenarios)\\n'
    '│   ├── dashboard.feature     (6 scenarios)\\n'
    '│   ├── weight-data.feature   (5 scenarios)\\n'
    '│   └── admin.feature         (5 scenarios)\\n'
    '└── steps/                    # (deprecated, steps moved to conftest)\\n'
    '    ├── conftest.py\\n'
    '    └── ... (old step files kept for reference)', code))

elements.append(Paragraph('3.3 Why Steps in conftest.py', h2))
elements.append(Paragraph(
    'In pytest-bdd 8.x, <b>@given/@when/@then decorators create pytest fixtures</b> '
    'which must be registered in conftest.py for proper discovery. '
    'Step definitions in external modules are not found by pytest-bdd\'s fixture '
    'scanning. All ~60 step definitions are therefore in test_dir/conftest.py.', body))

elements.append(Paragraph('3.4 Key Design Decisions', h2))
elements.append(make_table([
    ('Decision', 'Rationale'),
    ('ORM for test data', 'Speed: create users/posts via DB, not browser UI'),
    ('Fresh context per test', 'Isolation: no state leakage between scenarios'),
    ('Session-scoped server', 'Performance: start Django once per test session'),
    ('Screenshot on failure', 'Debug: auto-capture page state when test fails'),
    ('@given/@when/@then', 'Clarity: explicit step types match Gherkin grammar'),
], col_widths=[160, 280]))

elements.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 4. Test Coverage
# ══════════════════════════════════════════════════════════════════════════════
elements.append(Paragraph('4. Test Coverage', h1))
elements.append(hr())

elements.append(Paragraph('4.1 Feature Coverage Matrix', h2))
elements.append(make_table([
    ('Feature', 'Scenarios', 'Covers', 'Status'),
    ('Authentication', '6',
     'Register, duplicate user, login, invalid login, logout, unauthed redirect',
     '⚠ 1/6 pass'),
    ('Blog Posts', '6',
     'Empty list, create post, detail view, ordering, guest restrictions, pagination',
     '⚠ 1/6 pass'),
    ('Navigation/i18n', '7',
     'Guest/authed nav, lang switcher presence, Chinese/English toggle, persistence',
     '⚠ 1/7 pass'),
    ('Dashboard', '6',
     'Info cards, user table, row highlight, multi-user, IP/location columns, i18n',
     '❌ 0/6 pass'),
    ('Weight Data', '5',
     'Upload form, image upload, records list, guest redirect, column display',
     '❌ 0/5 pass'),
    ('Admin', '5',
     'Admin login, authed access, user CRUD, edit form, guest restriction',
     '❌ 0/5 pass'),
], col_widths=[90, 36, 240, 70]))

elements.append(Paragraph('4.2 Total Stats', h2))
elements.append(make_table([
    ('Metric', 'Value'),
    ('Feature files', '6'),
    ('Total scenarios', '35'),
    ('Passing', '3 (9%)'),
    ('Failing', '32 (91%) — mainly assertion mismatches vs actual site'),
    ('Step definitions', '~60 (all in conftest.py)'),
    ('Framework status', '✅ All steps discovered, server starts, browser runs'),
], col_widths=[160, 280]))

elements.append(Spacer(1, 10))
note_text2 = Paragraph(
    '<b>⚠ Note:</b> The 32 failing tests fail because the Gherkin assertions '
    'expect specific text/elements that differ from the actual live site. '
    'The test infrastructure (Django server, Playwright, step discovery) is '
    'fully operational. Each failure identifies a discrepancy between the '
    'specification and the actual UI — these are valuable for test-driven '
    'refinement.', note)
elements.append(note_text2)

elements.append(Paragraph('4.3 Coverage Gaps', h2))
elements.append(bullet_list([
    'No post translation/transcription tests',
    'No comment tests (list, receive)',
    'No password reset / email notification tests',
    'No responsive/mobile viewport tests',
    'No performance or load tests',
    'No API-level tests (all tests are through the browser)',
]))

elements.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 5. Running Tests
# ══════════════════════════════════════════════════════════════════════════════
elements.append(Paragraph('5. Running Tests', h1))
elements.append(hr())

elements.append(Paragraph('5.1 Prerequisites', h2))
elements.append(bullet_list([
    'Python 3.10+ with project venv activated',
    'Playwright browsers installed: playwright install chromium',
    'Django project files in place (D:\\gitSpace\\aWebSite)',
    'Python packages: pytest, pytest-bdd, playwright, Pillow',
]))

elements.append(Paragraph('5.2 Run All Tests', h2))
elements.append(Paragraph(
    'cd D:\\gitSpace\\aWebSite\\n'
    'website\\Scripts\\python.exe -m pytest test_dir/test_scenarios.py -v', code))

elements.append(Paragraph('5.3 Run Specific Features', h2))
elements.append(Paragraph(
    '# Run only authentication tests\\n'
    'website\\Scripts\\python.exe -m pytest test_dir/test_scenarios.py '
    '-k "register or login or logout" -v', code))
elements.append(Spacer(1, 4))
elements.append(Paragraph(
    '# Run only smoke tests (with marker)\\n'
    'website\\Scripts\\python.exe -m pytest -m smoke -v', code))

elements.append(Paragraph('5.4 Run a Single Scenario', h2))
elements.append(Paragraph(
    'website\\Scripts\\python.exe -m pytest '
    'test_dir/test_scenarios.py::test_register_a_new_account_successfully -v --tb=short',
    code))

elements.append(Paragraph('5.5 Command-Line Options', h2))
elements.append(make_table([
    ('Flag', 'Effect'),
    ('-v', 'Verbose output (show each test name)'),
    ('--tb=short', 'Short traceback (focus on failure message)'),
    ('--tb=long', 'Full traceback with all context'),
    ('-k "keyword"', 'Filter tests by name keyword'),
    ('-m "smoke"', 'Run only tests with @pytest.mark.smoke'),
    ('-x', 'Stop after first failure'),
    ('--headed', 'Run browser in headed mode (watch the test)'),
    ('--slowmo 500', 'Slow down Playwright by 500ms between actions'),
    ('-s', 'Print stdout from tests (no capture)'),
], col_widths=[140, 300]))

elements.append(Paragraph('5.6 Debugging Failing Tests', h2))
elements.append(Paragraph(
    'When a test fails:',
    body))
elements.append(bullet_list([
    'A screenshot is saved to test_dir/screenshots/ automatically',
    'Use --tb=long to see the full error traceback',
    'Add --headed to watch the browser during test execution',
    'Check /tmp/django.log on VPS (or local server log) for Django errors',
    'Run interactively in Python: from test_dir.conftest import *; then call steps',
]))

elements.append(Spacer(1, 10))
elements.append(Paragraph(
    '5.7 Quick Verification', h2))
elements.append(Paragraph(
    '# Quick check: framework works (1 test, ~3 seconds)\\n'
    'website\\Scripts\\python.exe -m pytest '
    'test_dir/test_scenarios.py::test_dashboard_requires_authentication -v',
    code))

# ── Generate ────────────────────────────────────────────────────────────────
doc.build(elements)
print(f'PDF generated: {OUTPUT}')
print(f'Size: {os.path.getsize(OUTPUT) / 1024:.0f} KB')
