#!/usr/bin/env python3
"""
Ultimate JSBSim Reference PDF Generator.

Produces an exhaustive technical document describing the JSBSim Flight
Dynamics Model (FDM): its architecture, math, XML configuration language,
aerodynamics calculations, and a practical workflow for building a new
aircraft model from CFD-derived data.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, PageBreak, Preformatted, KeepTogether,
    Table, TableStyle, NextPageTemplate, Image,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re
import os
import datetime


OUT_PATH = "/home/user/jsbsim/docs_output/JSBSim_Ultimate_Reference_UK.pdf"


# Register DejaVu fonts. The Ukrainian edition renders body text in DejaVu
# (the built-in base-14 fonts have no Cyrillic glyphs); DejaVuSans covers the
# full Ukrainian alphabet incl. і, ї, ґ, plus the macrons/dots used in maths.
DEJAVU_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DejaVu",        f"{DEJAVU_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold",   f"{DEJAVU_DIR}/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Oblique",
                               f"{DEJAVU_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Mono",
                               f"{DEJAVU_DIR}/DejaVuSansMono.ttf"))
# Register a font family so inline <b>/<i> markup resolves to the DejaVu
# bold/oblique faces rather than silently dropping to a glyph-less DejaVu.
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                              italic="DejaVu-Oblique", boldItalic="DejaVu-Bold")


# -----------------------------------------------------------------------------
# Page template with header/footer
# -----------------------------------------------------------------------------

PAGE_W, PAGE_H = A4


class HeaderFooterCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_pages = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self.draw_header_footer(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count):
        page_num = self._pageNumber
        if page_num == 1:
            return  # Don't draw on the cover page
        self.saveState()
        # Header bar
        self.setFillColor(colors.HexColor("#0d3b66"))
        self.rect(0, PAGE_H - 12 * mm, PAGE_W, 8 * mm, fill=1, stroke=0)
        self.setFillColor(colors.white)
        self.setFont("DejaVu-Bold", 9)
        self.drawString(15 * mm, PAGE_H - 8 * mm,
                        "Вичерпний довідник JSBSim")
        self.drawRightString(PAGE_W - 15 * mm, PAGE_H - 8 * mm,
                             "Модель динаміки польоту")
        # Footer
        self.setFillColor(colors.HexColor("#0d3b66"))
        self.rect(0, 8 * mm, PAGE_W, 0.4 * mm, fill=1, stroke=0)
        self.setFillColor(colors.HexColor("#333333"))
        self.setFont("DejaVu", 8)
        self.drawString(15 * mm, 5 * mm,
                        "JSBSim — відкрита 6-DoF модель динаміки польоту")
        self.drawRightString(PAGE_W - 15 * mm, 5 * mm,
                             f"Стор. {page_num} з {page_count}")
        self.restoreState()


# -----------------------------------------------------------------------------
# Styles
# -----------------------------------------------------------------------------

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "BigTitle", parent=styles["Title"],
    fontName="DejaVu-Bold", fontSize=30, leading=36,
    textColor=colors.HexColor("#0d3b66"), spaceAfter=10, alignment=TA_CENTER,
)
SUBTITLE_STYLE = ParagraphStyle(
    "Subtitle", parent=styles["Title"],
    fontName="DejaVu", fontSize=16, leading=20,
    textColor=colors.HexColor("#333333"), spaceAfter=24, alignment=TA_CENTER,
)
COVER_DESCR_STYLE = ParagraphStyle(
    "CoverDescr", parent=styles["Normal"],
    fontName="DejaVu-Oblique", fontSize=11, leading=15,
    textColor=colors.HexColor("#444444"), alignment=TA_CENTER,
)

CHAPTER_STYLE = ParagraphStyle(
    "Chapter", parent=styles["Heading1"],
    fontName="DejaVu-Bold", fontSize=22, leading=26,
    textColor=colors.HexColor("#0d3b66"),
    spaceBefore=12, spaceAfter=14, keepWithNext=True,
)
SECTION_STYLE = ParagraphStyle(
    "Section", parent=styles["Heading2"],
    fontName="DejaVu-Bold", fontSize=15, leading=19,
    textColor=colors.HexColor("#1d5d9b"),
    spaceBefore=14, spaceAfter=8, keepWithNext=True,
)
SUBSECTION_STYLE = ParagraphStyle(
    "SubSection", parent=styles["Heading3"],
    fontName="DejaVu-Bold", fontSize=12, leading=16,
    textColor=colors.HexColor("#222222"),
    spaceBefore=10, spaceAfter=5, keepWithNext=True,
)
SUBSUB_STYLE = ParagraphStyle(
    "SubSub", parent=styles["Heading4"],
    fontName="DejaVu-Bold", fontSize=10.5, leading=14,
    textColor=colors.HexColor("#444444"),
    spaceBefore=8, spaceAfter=3, keepWithNext=True,
)
BODY_STYLE = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontName="DejaVu", fontSize=10, leading=14,
    spaceAfter=6, alignment=TA_JUSTIFY,
)
BULLET_STYLE = ParagraphStyle(
    "Bullet", parent=BODY_STYLE,
    leftIndent=14, bulletIndent=2, spaceAfter=3, alignment=TA_LEFT,
)
QUOTE_STYLE = ParagraphStyle(
    "Quote", parent=BODY_STYLE,
    leftIndent=14, rightIndent=14, textColor=colors.HexColor("#555555"),
    fontName="DejaVu-Oblique",
    backColor=colors.HexColor("#f4f4f4"),
    borderColor=colors.HexColor("#cccccc"),
    borderWidth=0.5, borderPadding=6, spaceAfter=8, spaceBefore=4,
)
CODE_STYLE = ParagraphStyle(
    "Code", parent=styles["Code"],
    fontName="DejaVu-Mono", fontSize=8.0, leading=10.5,
    leftIndent=6, rightIndent=6,
    backColor=colors.HexColor("#f5f7fa"),
    borderColor=colors.HexColor("#cdd5e0"),
    borderWidth=0.6, borderPadding=6,
    spaceBefore=4, spaceAfter=8, textColor=colors.HexColor("#111122"),
)
MATH_STYLE = ParagraphStyle(
    "Math", parent=BODY_STYLE,
    alignment=TA_CENTER, fontName="DejaVu",
    fontSize=10.5, leading=14,
    textColor=colors.HexColor("#222222"),
    backColor=colors.HexColor("#fdf6e3"),
    borderColor=colors.HexColor("#e6d39a"),
    borderWidth=0.5, borderPadding=5,
    spaceBefore=4, spaceAfter=8,
)
CELL_STYLE_HEADER = ParagraphStyle(
    "CellHeader", fontName="DejaVu-Bold", fontSize=8.5, leading=11,
    textColor=colors.white, alignment=TA_LEFT,
)
CELL_STYLE_BODY = ParagraphStyle(
    "CellBody", fontName="DejaVu", fontSize=8.5, leading=11,
    textColor=colors.HexColor("#222222"), alignment=TA_LEFT,
)
TOC_HEADING_STYLE = ParagraphStyle(
    "TOCHeading", parent=styles["Heading1"],
    fontSize=20, textColor=colors.HexColor("#0d3b66"),
    alignment=TA_LEFT, spaceAfter=18,
)


# -----------------------------------------------------------------------------
# Custom paragraph that registers itself with the TOC
# -----------------------------------------------------------------------------

_HEADING_COUNTER = {"chapter": 0, "section": 0, "subsection": 0}


def heading(text, level, story):
    """Add a heading that will appear in the auto-generated TOC."""
    if level == 0:
        _HEADING_COUNTER["chapter"] += 1
        _HEADING_COUNTER["section"] = 0
        _HEADING_COUNTER["subsection"] = 0
        numbered = f"Розділ {_HEADING_COUNTER['chapter']}: {text}"
        style = CHAPTER_STYLE
    elif level == 1:
        _HEADING_COUNTER["section"] += 1
        _HEADING_COUNTER["subsection"] = 0
        numbered = (f"{_HEADING_COUNTER['chapter']}."
                    f"{_HEADING_COUNTER['section']}  {text}")
        style = SECTION_STYLE
    elif level == 2:
        _HEADING_COUNTER["subsection"] += 1
        numbered = (f"{_HEADING_COUNTER['chapter']}."
                    f"{_HEADING_COUNTER['section']}."
                    f"{_HEADING_COUNTER['subsection']}  {text}")
        style = SUBSECTION_STYLE
    else:
        numbered = text
        style = SUBSUB_STYLE

    # Use a "registration" hack: a paragraph whose afterFlowable triggers TOC
    bookmark = f"hdg_{id(numbered)}_{_HEADING_COUNTER['chapter']}"
    p = Paragraph(
        f'<a name="{bookmark}"/>{numbered}', style
    )
    p._toc_entry = (level, numbered, bookmark)
    story.append(p)


# -----------------------------------------------------------------------------
# Helper paragraph builders
# -----------------------------------------------------------------------------


_CURRENT_STORY = []


def use_story(story):
    """Set the current story so bare code()/math() calls append to it."""
    _CURRENT_STORY.clear()
    _CURRENT_STORY.append(story)


def _story():
    return _CURRENT_STORY[0]


def p(text, style=BODY_STYLE):
    """Body paragraph. Returns flowable (caller wraps in story.append)."""
    return Paragraph(text, style)


def bullet(text):
    return Paragraph(f"• {text}", BULLET_STYLE)


def code(text):
    """Preformatted code block — auto-appends to current story.
    Preformatted in ReportLab keeps newlines but does NOT decode HTML
    entities — so feed it raw < and > directly."""
    flow = Preformatted(text, CODE_STYLE)
    _story().append(flow)
    return flow


def math(text):
    """Math line — auto-appends to current story."""
    flow = Paragraph(text, MATH_STYLE)
    _story().append(flow)
    return flow


def quote(text):
    """Quote — returns flowable (caller wraps in story.append)."""
    return Paragraph(text, QUOTE_STYLE)


def wrap_table(table_data):
    """Wrap every string cell in a Paragraph so HTML markup is interpreted
    and long cells word-wrap inside their column."""
    out = []
    for i, row in enumerate(table_data):
        style = CELL_STYLE_HEADER if i == 0 else CELL_STYLE_BODY
        out.append([
            Paragraph(c, style) if isinstance(c, str) else c
            for c in row
        ])
    return out


# -----------------------------------------------------------------------------
# TOC-collecting document template
# -----------------------------------------------------------------------------


class TOCDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        BaseDocTemplate.__init__(self, filename, **kwargs)
        cover_frame = Frame(
            0, 0, PAGE_W, PAGE_H,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        )
        body_frame = Frame(
            18 * mm, 16 * mm, PAGE_W - 36 * mm, PAGE_H - 32 * mm,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
            id="body",
        )
        self.addPageTemplates([
            PageTemplate(id="Cover", frames=cover_frame),
            PageTemplate(id="Body", frames=body_frame),
        ])

    def afterFlowable(self, flowable):
        if hasattr(flowable, "_toc_entry"):
            level, text, bookmark = flowable._toc_entry
            self.notify("TOCEntry", (level, text, self.page, bookmark))


# -----------------------------------------------------------------------------
# Document content
# -----------------------------------------------------------------------------


def build_story():
    story = []
    use_story(story)

    # ------------------------------------------------------------------ COVER
    story.append(Spacer(1, 60 * mm))
    story.append(Paragraph("Вичерпний", TITLE_STYLE))
    story.append(Paragraph("довідник із JSBSim", TITLE_STYLE))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Архітектура, аеродинаміка та моделювання літальних апаратів — зсередини",
        SUBTITLE_STYLE))
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph(
        "Практичний інженерний посібник, що охоплює мову конфігурування XML "
        "у JSBSim, рівняння руху, методи інтегрування, функційно-табличну "
        "аеродинамічну систему, підсистему силової установки, компоненти "
        "системи керування польотом і робочий процес створення аеродинамічних "
        "таблиць даних, отриманих з CFD, для власної моделі літального апарата.",
        COVER_DESCR_STYLE))
    story.append(Spacer(1, 50 * mm))
    today = datetime.date.today().isoformat()
    story.append(Paragraph(
        f"Згенеровано {today} &nbsp;·&nbsp; "
        "Реконструйовано на основі вихідного коду JSBSim v2.0",
        ParagraphStyle("CoverFooter", parent=COVER_DESCR_STYLE,
                       fontSize=9, textColor=colors.HexColor("#666666"))))
    story.append(NextPageTemplate("Body"))
    story.append(PageBreak())

    # ------------------------------------------------------------------ TOC
    story.append(Paragraph("Зміст", TOC_HEADING_STYLE))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC0", fontName="DejaVu-Bold", fontSize=11,
                       textColor=colors.HexColor("#0d3b66"),
                       leftIndent=0, leading=16, spaceAfter=3),
        ParagraphStyle("TOC1", fontName="DejaVu", fontSize=10,
                       leftIndent=14, leading=13, spaceAfter=1),
        ParagraphStyle("TOC2", fontName="DejaVu", fontSize=9,
                       leftIndent=28, leading=12, spaceAfter=0,
                       textColor=colors.HexColor("#555555")),
    ]
    story.append(toc)
    story.append(PageBreak())

    # ================================================================
    # CHAPTER 1 - Introduction
    # ================================================================
    heading("Вступ до JSBSim", 0, story)
    story.append(p(
        "JSBSim — це багатоплатформна об’єктно-орієнтована модель динаміки "
        "польоту (FDM) з відкритим кодом, написана мовою C++, що слугує "
        "фізичним ядром для широкого спектра аерокосмічних застосунків: "
        "FlightGear, проєкту Antoinette на Unreal Engine, симуляцій "
        "Software-in-the-Loop для ArduPilot та PX4, середовищ навчання з "
        "підкріпленням на кшталт <i>gym-jsbsim</i>, а також академічних "
        "досліджень, на які посилаються тисячі разів. Вона реалізує "
        "нелінійну симуляцію твердого тіла з шістьма ступенями свободи з "
        "точною моделлю Землі (еліпсоїд WGS-84, обертання, ефект Коріоліса), "
        "стандартною атмосферою ISA 1976, налаштовуваним вітром і "
        "турбулентністю, силовою установкою (поршневою, турбінною, "
        "турбогвинтовою, ракетною, електричною, гвинтокрилою), реакціями "
        "опори та повністю скриптованою системою керування польотом на "
        "основі XML."))

    heading("Що охоплює цей документ", 1, story)
    story.append(p(
        "Цей довідник побудований як занурення в JSBSim згори донизу. Ми "
        "починаємо з архітектури та циклу виконання, потім проходимо кожен "
        "розділ XML літального апарата, далі поглиблено розглядаємо "
        "аеродинаміку (математичний апарат, таблиці та домовленості) і "
        "завершуємо практичним робочим процесом CFD-to-JSBSim для побудови "
        "власної моделі літального апарата. Кожне твердження підкріплене "
        "посиланнями на вихідний код у форматі "
        "<font face='Courier'>file:line</font>."))

    heading("Чим JSBSim відрізняється від типового рушія симуляції", 1, story)
    for b in [
        "<b>Моделювання лише через XML:</b> літальні апарати описуються "
        "декларативним XML — для додавання нового планера перекомпіляція не "
        "потрібна.",
        "<b>Функційно-таблична аеродинаміка:</b> аеродинамічні коефіцієнти "
        "виражаються як <i>функції</i>, що поєднують таблиці, властивості та "
        "арифметичні оператори. Завдяки цьому модель повністю керується "
        "даними і її легко наповнювати з CFD чи даних аеродинамічної труби.",
        "<b>Дерево властивостей:</b> кожна змінна стану, керувальний вхід, "
        "вихід FCS і аеродинамічний коефіцієнт доступні за ієрархічним "
        "рядковим шляхом (<font face='Courier'>aero/qbar-psf</font>, "
        "<font face='Courier'>velocities/p-aero-rad_sec</font> тощо). Усе "
        "піддається спостереженню, а більшість значень — запису.",
        "<b>Фізика круглої Землі:</b> рівняння руху інтегруються у системі "
        "відліку ECI з урахуванням коріолісового та відцентрового "
        "прискорень від обертання Землі. Опціональне моделювання "
        "гравітаційного моменту підтримує космічні апарати.",
        "<b>Алгоритм балансування:</b> надійний розв’язувач кореня методом "
        "обмеження інтервалу балансує апарат у режим усталеного польоту "
        "(поздовжній, повний, у віражі, з виходом із пікірування, наземний, "
        "користувацький).",
    ]:
        story.append(bullet(b))

    heading("Домовленості, прийняті в цьому документі", 1, story)
    story.append(p(
        "Відстані та інерція за замовчуванням подаються в американських "
        "звичаєвих одиницях (фути, дюйми, slug·ft²) — це типове налаштування "
        "JSBSim — однак усі елементи допускають явний атрибут "
        "<font face='Courier'>unit</font>. Математичні позначення "
        "відповідають домовленості Etkin/Stevens-Lewis: <i>α</i> — кут атаки "
        "(angle of attack), <i>β</i> — кут ковзання (sideslip), "
        "<i>p,q,r</i> — кутові швидкості у зв’язаній системі, "
        "<i><font name='DejaVu'>q̄</font></i> = ½ρV² — швидкісний напір "
        "(dynamic pressure), <i>S, b, <font name='DejaVu'>c̄</font></i> — "
        "площа крила, розмах, середня аеродинамічна хорда."))

    heading("Українсько-англійський словник ключових термінів", 1, story)
    story.append(p(
        "Це переклад зберігає всі назви, ідентифікатори, шляхи властивостей, "
        "елементи XML, цитати джерел (<font face='Courier'>файл:рядок</font>) "
        "та одиниці виміру в оригіналі. Щоб полегшити звірку з англомовною "
        "документацією, вихідним кодом і самим деревом властивостей JSBSim, "
        "важливі терміни в тексті при першій згадці супроводжуються "
        "оригіналом у дужках, напр. «кут атаки (angle of attack)». Повний "
        "перелік ключових відповідників зібрано в таблиці нижче."))
    _terms = [
        ("модель динаміки польоту", "flight dynamics model (FDM)"),
        ("рівняння руху", "equations of motion"),
        ("дерево властивостей", "property tree"),
        ("система керування польотом", "flight control system (FCS)"),
        ("планер", "airframe"),
        ("кут атаки", "angle of attack"),
        ("кут ковзання", "sideslip"),
        ("піднімальна сила", "lift"),
        ("сила опору (лобовий опір)", "drag"),
        ("бічна сила", "side force"),
        ("тангаж", "pitch"),
        ("крен", "roll"),
        ("рискання", "yaw"),
        ("момент тангажа", "pitching moment"),
        ("момент крену", "rolling moment"),
        ("момент рискання", "yawing moment"),
        ("коефіцієнт", "coefficient"),
        ("похідна стійкості", "stability derivative"),
        ("похідна демпфування", "damping derivative"),
        ("похідна керованості", "control derivative"),
        ("аеродинаміка", "aerodynamics"),
        ("аеродинамічний профіль", "airfoil"),
        ("крило", "wing"),
        ("видовження", "aspect ratio"),
        ("середня аеродинамічна хорда", "mean aerodynamic chord (MAC)"),
        ("швидкісний напір", "dynamic pressure"),
        ("число Маха", "Mach number"),
        ("число Рейнольдса", "Reynolds number"),
        ("пограничний шар", "boundary layer"),
        ("звалювання", "stall"),
        ("штопор", "spin"),
        ("гістерезис", "hysteresis"),
        ("центр мас", "centre of gravity (CG)"),
        ("тензор інерції", "inertia tensor"),
        ("запас поздовжньої стійкості", "static margin"),
        ("нейтральна точка", "neutral point"),
        ("балансування", "trim"),
        ("силова установка", "propulsion"),
        ("тяга", "thrust"),
        ("поршневий двигун", "piston engine"),
        ("турбіна", "turbine"),
        ("турбореактивний двигун", "turbojet"),
        ("турбовентиляторний двигун", "turbofan"),
        ("турбогвинтовий двигун", "turboprop"),
        ("тиск у впускному колекторі", "manifold pressure"),
        ("повітряний гвинт", "propeller"),
        ("регулятор постійних обертів", "constant-speed governor"),
        ("відносна хода", "advance ratio"),
        ("паливо", "fuel"),
        ("паливний бак", "fuel tank"),
        ("шасі", "landing gear"),
        ("реакції опори", "ground reactions"),
        ("амортизаційна стійка", "strut"),
        ("тертя", "friction"),
        ("гальмо", "brake"),
        ("коефіцієнт підсилення", "gain"),
        ("фільтр", "filter"),
        ("привод (виконавчий механізм)", "actuator"),
        ("датчик", "sensor"),
        ("автопілот", "autopilot"),
        ("система покращення стійкості", "stability augmentation"),
        ("демпфер рискання", "yaw damper"),
        ("кермова поверхня", "control surface"),
        ("відхилення", "deflection"),
        ("атмосфера", "atmosphere"),
        ("вітер", "wind"),
        ("турбулентність", "turbulence"),
        ("порив вітру", "gust"),
        ("розрахункова сітка", "mesh"),
        ("розв’язувач", "solver"),
        ("обчислювальна гідрогазодинаміка", "CFD"),
        ("вимушені коливання", "forced oscillation"),
        ("зведена частота", "reduced frequency"),
        ("аеродинамічна труба", "wind tunnel"),
        ("льотні випробування", "flight test"),
        ("пілотажні характеристики", "handling qualities"),
        ("короткоперіодичний рух", "short period"),
        ("фугоїд", "phugoid"),
        ("голландський крок", "Dutch roll"),
        ("спіральний рух", "spiral mode"),
        ("крен-мода", "roll mode"),
        ("власний рух (форма)", "eigenmode"),
        ("кватерніон", "quaternion"),
        ("верифікація", "verification"),
        ("валідація", "validation"),
    ]
    _gloss_rows = [["Українською", "English", "Українською", "English"]]
    for _i in range(0, len(_terms), 2):
        _pair = _terms[_i:_i + 2]
        _row = [_pair[0][0], _pair[0][1]]
        _row += [_pair[1][0], _pair[1][1]] if len(_pair) > 1 else ["", ""]
        _gloss_rows.append(_row)
    story.append(_oftab(_gloss_rows,
                        [4.0 * cm, 4.2 * cm, 4.0 * cm, 4.2 * cm]))

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 2 - Architecture & Execution Flow
    # ================================================================
    heading("Архітектура та хід виконання", 0, story)
    story.append(p(
        "JSBSim побудований навколо центрального керувального класу "
        "(<font face='Courier'>FGFDMExec</font>), який володіє списком "
        "<i>моделей</i> із фіксованим порядком і керує ними через цикл із "
        "дискретним часом. Кожна модель зчитує свої вхідні дані з дерева "
        "властивостей (заповненого попередніми моделями на тому самому "
        "такті) і записує туди свої вихідні дані. Інтегрування рівнянь руху "
        "саме є однією з таких моделей."))

    heading("Порядок виконання моделей", 1, story)
    story.append(p(
        "Моделі перелічено в <font face='Courier'>FGFDMExec.h:225-241"
        "</font> і виконуються в такому порядку на кожному такті:"))
    code(
        "enum eModels {\n"
        "  ePropagate=0,        // Integrate state from previous tick's accels\n"
        "  eInput,              // Telnet/socket inputs\n"
        "  eInertial,           // Gravity and Earth rotation vector\n"
        "  eAtmosphere,         // T, p, rho, speed of sound at h\n"
        "  eWinds,              // Steady wind + gusts + turbulence\n"
        "  eSystems,            // FCS, autopilot, custom systems\n"
        "  eMassBalance,        // CG, inertia tensor, total mass\n"
        "  eAuxiliary,          // alpha, beta, qbar, Vt, Mach, ...\n"
        "  ePropulsion,         // Engine thrust and torque\n"
        "  eAerodynamics,       // Aero forces and moments\n"
        "  eGroundReactions,    // Gear forces and friction\n"
        "  eExternalReactions,  // User-defined external forces\n"
        "  eBuoyantForces,      // Lighter-than-air models\n"
        "  eAircraft,           // Sum forces and moments at CG\n"
        "  eAccelerations,      // Solve F = m a, tau = I omega-dot\n"
        "  eOutput              // CSV, sockets, FlightGear, ...\n"
        "};")
    story.append(p(
        "<b>Чому цей порядок важливий.</b> <i>Propagate</i> виконується "
        "першим, бо просуває стан, використовуючи прискорення, обчислені "
        "наприкінці <i>попереднього</i> такту. Далі атмосфера й вітри дають "
        "тиск, густину та швидкість відносно повітряної маси, що потрібні "
        "<i>Auxiliary</i> для обчислення <i>α, β, <font name='DejaVu'>q̄</font>, M</i> — які споживають "
        "аеродинамічні функції. Баланс мас виконується після FCS, щоб закон "
        "керування міг запросити зсув точкової маси (приклади: перекачування "
        "палива, скидання вантажу). Accelerations виконується останньою; її "
        "вихідні дані стають вхідними для Propagate на наступному такті."))

    heading("Цикл Run у псевдокоді", 1, story)
    code(
        "FGFDMExec::Run() {                                    // FGFDMExec.cpp:404\n"
        "    for child in childFDMs: child->Run()\n"
        "    sim_time += dt; Frame++\n"
        "    if (script) script->RunScript()\n"
        "    for i in eModels:\n"
        "        LoadInputs(i)        // copy upstream outputs to this model's inputs\n"
        "        Models[i]->Run(holding)\n"
        "}")
    story.append(p(
        "Типовий крок інтегрування — "
        "<font face='Courier'>1.0 / 120.0</font> с "
        "(див. <font face='Courier'>FGFDMExec.cpp:99</font>). На частоті "
        "120 Гц JSBSim працює швидше за реальний час на одному ядрі CPU "
        "навіть для складних літальних апаратів. Крок задається через "
        "<font face='Courier'>SetDeltaT()</font> або через скрипт симуляції."))

    heading("Модулі побіжно", 1, story)
    table_data = [
        ["Модуль", "Вихідний код", "Відповідальність"],
        ["FGPropagate", "models/FGPropagate.*",
            "Інтегрує положення, швидкість, кватерніон"],
        ["FGAccelerations", "models/FGAccelerations.*",
            "Рівняння Ньютона-Ейлера; наземне тертя через LCP"],
        ["FGAerodynamics", "models/FGAerodynamics.*",
            "Підсумовує аеродинамічні сили/моменти на основі функцій"],
        ["FGPropulsion", "models/FGPropulsion.*",
            "Двигуни (поршневий/турбінний/ракетний/електричний)"],
        ["FGGroundReactions", "models/FGGroundReactions.*",
            "Шини, амортизаційні стійки, гальма, керування поворотом"],
        ["FGAtmosphere", "models/FGAtmosphere.*",
            "ISA 1976 (T, p, ρ, a)"],
        ["FGWinds", "models/atmosphere/FGWinds.*",
            "Усталений вітер, зсув, турбулентність Драйдена/Кармана"],
        ["FGInertial", "models/FGInertial.*",
            "Гравітація (сферична або WGS-84), обертання планети"],
        ["FGMassBalance", "models/FGMassBalance.*",
            "Маса, CG, тензор інерції, точкові маси"],
        ["FGAuxiliary", "models/FGAuxiliary.*",
            "α, β, <font name='DejaVu'>q̄</font>, Vt, число Маха, gamma, перевантаження"],
        ["FGFCS", "models/FGFCS.*",
            "Система керування польотом; граф каналів/компонентів"],
        ["FGOutput", "models/FGOutput.*",
            "CSV, двійковий формат FlightGear, TCP, telnet"],
        ["FGTrim", "initialization/FGTrim.*",
            "Розв’язувач кореня з обмеженням інтервалу для балансування"],
        ["FGPropertyManager", "input_output/FGPropertyManager.*",
            "Ієрархічне дерево властивостей, увесь ввід/вивід через шляхи"],
    ]
    t = Table(wrap_table(table_data), colWidths=[3.1 * cm, 4.0 * cm, 9.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 3 - Coordinate frames and units
    # ================================================================
    heading("Системи координат, осі та одиниці", 0, story)
    story.append(p(
        "Правильне поводження із системами відліку — найпоширеніше джерело "
        "помилок під час побудови нового літального апарата. JSBSim "
        "використовує одразу кілька систем, і кожен розділ XML неявно обирає "
        "одну з них."))

    heading("Конструктивна система (геометрія в XML)", 1, story)
    story.append(p(
        "Усі елементи <font face='Courier'>&lt;location&gt;</font> — шасі, "
        "CG, AERORP, точкові маси, розташування рушія двигуна — задаються у "
        "<i>конструктивній</i> (structural) системі відліку. Це зв’язана з "
        "літаком система, у якій вісь X зазвичай напрямлена назад уздовж "
        "фюзеляжу, Y — праворуч, Z — угору. Початок координат (0,0,0) за "
        "домовленістю розміщують поблизу протипожежної перегородки або "
        "носового базового перерізу. Типовою одиницею є дюйми."))
    story.append(p(
        "Усередині FDM ці положення перетворюються у зв’язану із тілом "
        "(body-fixed) систему, яку використовують рівняння руху (X — уперед, "
        "Y — праворуч, Z — донизу), але самого перетворення в XML ви "
        "<b>не</b> бачите."))

    heading("Зв’язана із тілом (зв’язана) система", 1, story)
    story.append(p(
        "Усі кутові швидкості, прискорення, швидкості у зв’язаній системі та "
        "компоненти інерції подаються у зв’язаній системі:"))
    for b in [
        "<b>X</b> — уперед, крізь ніс.",
        "<b>Y</b> — назовні крізь праве крило.",
        "<b>Z</b> — донизу, доповнюючи правобічну трійку.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Поступальна швидкість у зв’язаній системі — це трійка властивостей "
        "<font face='Courier'>velocities/u-fps, v-fps, w-fps</font>. Кутові "
        "швидкості — <font face='Courier'>velocities/p-rad_sec, "
        "q-rad_sec, r-rad_sec</font>. Тензор інерції в XML задається у "
        "конструктивній системі, але під час завантаження повертається у "
        "зв’язану систему."))

    heading("Швидкісна (аеродинамічна) та зв’язана зі стійкістю системи", 1, story)
    story.append(p(
        "<i>Швидкісна</i> (wind) система повернута відносно зв’язаної на кут "
        "ковзання <i>β</i> та кут атаки <i>α</i>: її вісь X напрямлена "
        "уздовж відносного вітру, сила опору діє вздовж −X, піднімальна сила "
        "діє вздовж −Z (угору відносно потоку). Коли ви пишете "
        "<font face='Courier'>&lt;axis name=\"LIFT\"&gt;</font> у розділі "
        "аеродинаміки, JSBSim вважає, що ви працюєте у швидкісних осях. "
        "<i>Зв’язана зі стійкістю</i> (stability) система — це проміжна "
        "система, повернута відносно зв’язаної лише на α (без β); деякі "
        "класичні похідні стійкості табулюють саме в ній, і ви можете "
        "увімкнути її через <font face='Courier'>frame=\"STABILITY\"</font>."))
    story.append(p(
        "JSBSim виконує перетворення автоматично: сили, обчислені у "
        "<i>LIFT/DRAG/SIDE</i>, повертаються матрицею <i>T<sub>w2b</sub></i> "
        "у зв’язану систему, моменти додаються в точці AERORP, а потім "
        "переносяться в CG за формулою <i>r × F</i>."))

    heading("Локальна NED та ECI системи", 1, story)
    story.append(p(
        "<b>Локальна NED</b> (North-East-Down, північ-схід-вниз) — це "
        "локально-дотична система з центром у літаку. JSBSim використовує її "
        "для вітрів, наземної траєкторії (γ, ψ<sub>gt</sub>) та локальних "
        "кутів Ейлера <i>φ, θ, ψ</i>. <b>ECI</b> (Earth-Centred Inertial, "
        "геоцентрична інерціальна) — це необертова система, у якій рівняння "
        "руху фактично інтегруються; "
        "<font face='Courier'>FGPropagate</font> підтримує "
        "<i>v<sub>inertial</sub></i> та <i>r<sub>inertial</sub></i> "
        "внутрішньо і перетворює їх у зв’язану/локальну для виведення."))

    heading("Домовленості про знаки", 1, story)
    for b in [
        "<b>Відхилення руля висоти</b>: додатне — задньою кромкою донизу "
        "(створює від’ємний момент тангажа), виводиться до "
        "<font face='Courier'>fcs/elevator-pos-rad</font>.",
        "<b>Відхилення елеронів</b>: диференціальне — C-172 використовує "
        "<font face='Courier'>left-aileron-pos-rad</font>, де додатне = "
        "донизу (кренить праворуч).",
        "<b>Відхилення руля напряму</b>: додатне — задньою кромкою ліворуч "
        "(відхиляє ніс ліворуч).",
        "<b>Відцентрові добутки інерції</b>: класична домовленість трактує "
        "<i>I<sub>xz</sub></i> як інтеграл <i>+xz dm</i>. Деякі джерела "
        "використовують від’ємну домовленість; щоб перемкнути, встановіть "
        "<font face='Courier'>negated_crossproduct_inertia=\"true\"</font> "
        "на елементі <i>&lt;mass_balance&gt;</i>.",
        "<b>Угору чи вниз</b>: <i>Z<sub>body</sub></i> додатне донизу. "
        "Конструктивне Z, задане в XML, зазвичай додатне вгору — JSBSim "
        "виконує обернення внутрішньо.",
    ]:
        story.append(bullet(b))

    heading("Одиниці", 1, story)
    code(
        "Length             FT (default), IN (default for <location>), M, KM, CM\n"
        "Area               FT2 (default), M2, IN2, CM2\n"
        "Mass               LBS (default), KG, SLUG  (1 slug = 14.594 kg)\n"
        "Inertia            SLUG*FT2 (default), KG*M2\n"
        "Force              LBS, N\n"
        "Pressure           PSF (default), PSI, INHG, ATM, PA, N/M2\n"
        "Velocity (output)  FPS, KTS, M/S  (per-property)\n"
        "Angle              RAD (aero default), DEG (FCS default)\n"
        "Spring             LBS/FT, N/M\n"
        "Damping            LBS/FT/SEC, N/M/SEC")
    story.append(p(
        "<b>Завжди оголошуйте одиниці явно</b> на кожному елементі, що "
        "приймає атрибут <font face='Courier'>unit</font> — приховані "
        "розбіжності типових значень спричиняють більшість звітів про "
        "помилки на кшталт «мій літак сам злітає боком»."))

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 4 - The Aircraft XML
    # ================================================================
    heading("XML літального апарата, розділ за розділом", 0, story)
    story.append(p(
        "Літальний апарат — це єдиний XML-файл із кореневим елементом "
        "<font face='Courier'>&lt;fdm_config&gt;</font>. Порядок розділів "
        "примусово задається XSD; канонічну послідовність показано нижче. За "
        "вступним матеріалом ідуть приблизно 10 підрозділів, по одному на "
        "кожен головний розділ."))

    heading("Корінь: fdm_config", 1, story)
    code(
        '<?xml version="1.0"?>\n'
        '<fdm_config name="MyAircraft" version="2.0" release="PRODUCTION"\n'
        '    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        '    xsi:noNamespaceSchemaLocation="http://jsbsim.sourceforge.net/JSBSim.xsd">\n'
        '\n'
        '    <fileheader>          ...  </fileheader>\n'
        '    <planet>              ...  </planet>      <!-- optional -->\n'
        '    <metrics>             ...  </metrics>\n'
        '    <mass_balance>        ...  </mass_balance>\n'
        '    <ground_reactions>    ...  </ground_reactions>\n'
        '    <external_reactions>  ...  </external_reactions>\n'
        '    <buoyant_forces>      ...  </buoyant_forces>\n'
        '    <propulsion>          ...  </propulsion>\n'
        '    <system  .../>                            <!-- 0..N -->\n'
        '    <autopilot ...>       ...  </autopilot>   <!-- 0..1 -->\n'
        '    <flight_control ...>  ...  </flight_control>\n'
        '    <aerodynamics>        ...  </aerodynamics>\n'
        '    <input ...>           ...  </input>       <!-- 0..N -->\n'
        '    <output ...>          ...  </output>      <!-- 0..N -->\n'
        '</fdm_config>')
    story.append(p(
        "<b>Атрибути:</b> "
        "<font face='Courier'>name</font> (обов’язковий) — відображувана "
        "назва; <font face='Courier'>version</font> (обов’язковий, наразі "
        "2.0); <font face='Courier'>release</font> = PRODUCTION | ALPHA | "
        "BETA (ALPHA/BETA виводять попередження під час завантаження)."))

    heading("fileheader: авторство та походження", 1, story)
    story.append(p(
        "Суто метадані. JSBSim ігнорує весь вміст усередині, проте його "
        "зчитують інструменти, що сканують парк моделей. Використовуйте "
        "його."))
    code(
        '<fileheader>\n'
        '    <author>Ada Lovelace</author>\n'
        '    <email>ada@example.com</email>\n'
        '    <organization>Acme Aircraft</organization>\n'
        '    <license licenseName="GPL"\n'
        '             licenseURL="http://www.gnu.org/licenses/gpl.html"/>\n'
        '    <filecreationdate>2026-05-24</filecreationdate>\n'
        '    <version>$Revision: 1.0 $</version>\n'
        '    <description>Acme A-1 light sport aircraft.</description>\n'
        '    <note>Stall hysteresis modelled per NACA TN-3909.</note>\n'
        '    <limitation>Gear aero drag not modelled.</limitation>\n'
        '    <reference title="AGARD-AR-265"\n'
        '               author="ESDU"\n'
        '               date="1988"\n'
        '               URL="https://example.org/AR265.pdf"/>\n'
        '</fileheader>')

    heading("metrics: геометрія літального апарата", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;metrics&gt;</font> задає величини для "
        "знерозмірнення: <i>S</i> (площа крила), <i>b</i> (розмах крила), "
        "<i><font name='DejaVu'>c̄</font></i> (середня аеродинамічна хорда), "
        "площі/плечі оперення та три <i>базові точки</i> AERORP, EYEPOINT і "
        "VRP."))
    code(
        '<metrics>\n'
        '    <wingarea  unit="FT2"> 174.0  </wingarea>\n'
        '    <wingspan  unit="FT" >  35.8  </wingspan>\n'
        '    <chord     unit="FT" >   4.9  </chord>\n'
        '    <htailarea unit="FT2">  21.9  </htailarea>\n'
        '    <htailarm  unit="FT" >  15.7  </htailarm>\n'
        '    <vtailarea unit="FT2">  16.5  </vtailarea>\n'
        '    <vtailarm  unit="FT" >   0    </vtailarm>\n'
        '    <wing_incidence unit="DEG"> 1.5 </wing_incidence>  <!-- optional -->\n'
        '\n'
        '    <location name="AERORP" unit="IN">  <!-- 25% MAC -->\n'
        '        <x>43.2</x> <y>0</y> <z>59.4</z>\n'
        '    </location>\n'
        '    <location name="EYEPOINT" unit="IN">\n'
        '        <x>37</x> <y>0</y> <z>48</z>\n'
        '    </location>\n'
        '    <location name="VRP" unit="IN">\n'
        '        <x>42.6</x> <y>0</y> <z>38.5</z>\n'
        '    </location>\n'
        '</metrics>')
    story.append(p(
        "Три базові точки мають конкретне значення:"))
    for b in [
        "<b>AERORP</b> — аеродинамічна базова точка (aerodynamic reference "
        "point). Усі аеродинамічні моменти спочатку підсумовуються відносно "
        "цієї точки, а потім переносяться в CG за формулою "
        "<i>M<sub>cg</sub> = M<sub>arp</sub> + r<sub>arp→cg</sub> × F"
        "</i>. За домовленістю розміщується на 25% середньої аеродинамічної "
        "хорди крила.",
        "<b>EYEPOINT</b> — положення очей пілота. Використовується "
        "FlightGear та візуальними системами; впливає на перевантаження на "
        "рівні голови пілота "
        "(<font face='Courier'>accelerations/n-pilot-{x,y,z}-norm</font>).",
        "<b>VRP</b> — візуальна базова точка (visual reference point), "
        "початок координат для зовнішніх засобів перегляду.",
    ]:
        story.append(bullet(b))

    heading("mass_balance: вага, CG, інерція", 1, story)
    story.append(p(
        "Споряджена вага плюс список <i>точкових мас</i> — це те, на основі "
        "чого JSBSim обчислює повну масу, положення CG і тензор інерції в "
        "CG. Точкові маси охоплюють екіпаж, пасажирів, вантаж та "
        "користувацькі елементи, які можуть переміщуватися під час "
        "виконання (підвісні вантажі, перекачуване паливо). Маса баків "
        "додається автоматично підсистемою силової установки і витрачається "
        "впродовж польоту."))
    code(
        '<mass_balance negated_crossproduct_inertia="false">\n'
        '    <ixx unit="SLUG*FT2">  948 </ixx>\n'
        '    <iyy unit="SLUG*FT2"> 1346 </iyy>\n'
        '    <izz unit="SLUG*FT2"> 1967 </izz>\n'
        '    <ixy unit="SLUG*FT2">   0  </ixy>\n'
        '    <ixz unit="SLUG*FT2">   0  </ixz>\n'
        '    <iyz unit="SLUG*FT2">   0  </iyz>\n'
        '    <emptywt unit="LBS"> 1500 </emptywt>\n'
        '    <location name="CG" unit="IN">\n'
        '        <x>41</x> <y>0</y> <z>36.5</z>\n'
        '    </location>\n'
        '    <pointmass name="Pilot">\n'
        '        <weight unit="LBS"> 180 </weight>\n'
        '        <location unit="IN"> <x>36</x><y>-14</y><z>24</z> </location>\n'
        '    </pointmass>\n'
        '    <pointmass name="Baggage">\n'
        '        <weight unit="LBS">  0  </weight>\n'
        '        <location unit="IN"> <x>95</x><y>0</y><z>24</z> </location>\n'
        '        <form shape="cylinder">  <!-- optional inertia shape -->\n'
        '            <radius unit="IN">  6 </radius>\n'
        '            <length unit="IN"> 24 </length>\n'
        '        </form>\n'
        '    </pointmass>\n'
        '</mass_balance>')
    story.append(p(
        "<b>Інерція відносно CG</b>: значення, які ви задаєте в "
        "<font face='Courier'>ixx, iyy, izz, ixy, ixz, iyz</font>, — це "
        "інерція спорядженої конструкції відносно CG у "
        "<i>конструктивній</i> системі. JSBSim повертає їх у зв’язану "
        "систему, а потім додає внески кожної точкової маси за теоремою про "
        "паралельні осі. Атрибут "
        "<font face='Courier'>negated_crossproduct_inertia</font> існує "
        "тому, що половина підручників використовує протилежну домовленість "
        "про знак для добутків інерції."))

    heading("ground_reactions: шасі, лижі та контакти", 1, story)
    story.append(p(
        "Елементи <font face='Courier'>&lt;contact&gt;</font> описують усе, "
        "що може торкатися землі. Є два типи:"))
    for b in [
        "<b>BOGEY</b> — колесо. Має амортизаційну стійку (пружність + "
        "демпфування), тертя шини (статичне, динамічне, кочення), "
        "опціональне керування поворотом, опціональні гальма та "
        "опціональне прибирання.",
        "<b>STRUCTURE</b> — контакт без кочення, як-от законцівка крила, "
        "лижа, фюзеляж чи хвостова опора. Зазвичай дуже жорсткий з низьким "
        "тертям.",
    ]:
        story.append(bullet(b))
    code(
        '<ground_reactions>\n'
        '    <contact type="BOGEY" name="NOSE">\n'
        '        <location unit="IN">\n'
        '            <x>-6.8</x> <y>0</y> <z>-19.5</z>\n'
        '        </location>\n'
        '        <static_friction>  0.80 </static_friction>\n'
        '        <dynamic_friction> 0.50 </dynamic_friction>\n'
        '        <rolling_friction> 0.02 </rolling_friction>\n'
        '        <spring_coeff  unit="LBS/FT">     1800 </spring_coeff>\n'
        '        <damping_coeff unit="LBS/FT/SEC"> 600  </damping_coeff>\n'
        '        <damping_coeff_rebound unit="LBS/FT/SEC"> 1200 </damping_coeff_rebound>\n'
        '        <max_steer unit="DEG"> 10 </max_steer>\n'
        '        <brake_group> NONE </brake_group>\n'
        '        <retractable>0</retractable>\n'
        '    </contact>\n'
        '    <contact type="BOGEY" name="LEFT_MAIN">\n'
        '        <location unit="IN"> <x>58.2</x><y>-43</y><z>-15.5</z> </location>\n'
        '        <static_friction>0.8</static_friction>\n'
        '        <dynamic_friction>0.5</dynamic_friction>\n'
        '        <rolling_friction>0.02</rolling_friction>\n'
        '        <spring_coeff  unit="LBS/FT">     5400 </spring_coeff>\n'
        '        <damping_coeff unit="LBS/FT/SEC"> 1600 </damping_coeff>\n'
        '        <brake_group> LEFT </brake_group>\n'
        '    </contact>\n'
        '    <contact type="STRUCTURE" name="LEFT_WINGTIP">\n'
        '        <location unit="IN"> <x>43.2</x><y>-214.8</y><z>59.4</z> </location>\n'
        '        <static_friction>0.2</static_friction>\n'
        '        <dynamic_friction>0.2</dynamic_friction>\n'
        '        <spring_coeff  unit="LBS/FT">     20000 </spring_coeff>\n'
        '        <damping_coeff unit="LBS/FT/SEC">  2000 </damping_coeff>\n'
        '    </contact>\n'
        '</ground_reactions>')
    story.append(p(
        "Сили тертя обчислюються ітеративним розв’язувачем множників "
        "Лагранжа методом проєктованого Гаусса-Зейделя (Catto 2005) "
        "усередині "
        "<font face='Courier'>FGAccelerations::CalculateFrictionForces()"
        "</font>, тож багатоколісні контакти одночасно задовольняють "
        "обмеження невзаємопроникнення та кулонівського тертя."))

    heading("external_reactions: додаткові сили", 1, story)
    story.append(p(
        "Сюди потрапляє все, що прикладає силу чи момент, які не є ні "
        "аеродинамічними, ні від силової установки, ні наземним контактом: "
        "парашути, буксирні троси, прискорювачі JATO, магнітні катапульти."))
    code(
        '<external_reactions>\n'
        '    <property>fcs/parachute_reef_pos_norm</property>  <!-- declare -->\n'
        '\n'
        '    <force name="parachute" frame="WIND">\n'
        '        <function>\n'
        '            <product>\n'
        '                <property>aero/qbar-psf</property>\n'
        '                <property>fcs/parachute_reef_pos_norm</property>\n'
        '                <value>1.0</value>\n'
        '                <value>10000.0</value>     <!-- chute area in sq-ft -->\n'
        '            </product>\n'
        '        </function>\n'
        '        <location unit="FT"> <x>1</x><y>0</y><z>0</z> </location>\n'
        '        <direction> <x>-1</x><y>0</y><z>0</z> </direction>\n'
        '    </force>\n'
        '</external_reactions>')

    heading("propulsion: двигуни, баки, рушії", 1, story)
    story.append(p(
        "Силова установка дворівнева: XML-файл <i>двигуна</i> (завантажується "
        "з <font face='Courier'>$JSBSIM_ROOT/engine/</font>) описує двигун; "
        "XML літального апарата посилається на нього й додає "
        "<i>рушій</i> (тіло, що прикладає власне саму силу) та один чи "
        "кілька <i>баків</i>. Типи двигунів такі:"))
    for b in [
        "<b>piston_engine</b> — поршневий двигун внутрішнього згоряння з "
        "таблицями потужності залежно від обертів, дросельної заслінки, "
        "паливо-повітряної суміші, тиску у впускному колекторі (MAP) та "
        "висоти.",
        "<b>turbine_engine</b> — турбореактивний/турбовентиляторний двигун "
        "із таблицями режимів малого газу / максимального безфорсажного / "
        "форсажного (AB).",
        "<b>turboprop_engine</b> — турбогвинтовий двигун із таблицями "
        "потужності на валу.",
        "<b>rocket_engine</b> — твердопаливний або рідкопаливний ракетний "
        "двигун із характеристиками тяги/Isp.",
        "<b>electric_engine</b> — двигун постійного струму, потужність × "
        "дросель.",
        "<b>brushless_dc_motor</b> — крива моменту залежно від обертів.",
        "<b>rotor</b> — гвинт гелікоптера (індуктивний потік + махові "
        "рухи).",
    ]:
        story.append(bullet(b))
    code(
        '<propulsion>\n'
        '    <engine file="eng_io320">\n'
        '        <feed>0</feed>          <!-- consume from tank 0 -->\n'
        '        <feed>1</feed>\n'
        '        <thruster file="prop_75in2f">\n'
        '            <location unit="IN"> <x>-37.7</x><y>0</y><z>26.6</z> </location>\n'
        '            <orient   unit="DEG">\n'
        '                <pitch>0</pitch><roll>0</roll><yaw>0</yaw>\n'
        '            </orient>\n'
        '            <sense>1</sense>      <!-- 1 = right-hand prop -->\n'
        '            <p_factor>5</p_factor> <!-- effective offset for P-factor -->\n'
        '        </thruster>\n'
        '    </engine>\n'
        '\n'
        '    <tank type="FUEL" number="0">\n'
        '        <location unit="IN"> <x>56</x><y>-112</y><z>59.4</z> </location>\n'
        '        <type>AVGAS</type>\n'
        '        <capacity unit="LBS"> 185 </capacity>\n'
        '        <contents unit="LBS"> 100 </contents>\n'
        '        <priority>1</priority>\n'
        '    </tank>\n'
        '    <tank type="FUEL" number="1">\n'
        '        <location unit="IN"> <x>56</x><y> 112</y><z>59.4</z> </location>\n'
        '        <capacity unit="LBS"> 185 </capacity>\n'
        '        <contents unit="LBS"> 100 </contents>\n'
        '    </tank>\n'
        '</propulsion>')
    story.append(p(
        "Приклад файлу двигуна (<font face='Courier'>engine/eng_io320.xml"
        "</font>):"))
    code(
        '<piston_engine name="IO320">\n'
        '    <minmp     unit="INHG">  10.0 </minmp>\n'
        '    <maxmp     unit="INHG">  28.5 </maxmp>\n'
        '    <displacement unit="IN3"> 320.0 </displacement>\n'
        '    <maxhp>                 160.0 </maxhp>\n'
        '    <bsfc>                    0.32 </bsfc>\n'
        '    <cycles>                  4.0  </cycles>\n'
        '    <idlerpm>               550.0  </idlerpm>\n'
        '    <maxrpm>               2700.0  </maxrpm>\n'
        '    <maxthrottle>             1.0  </maxthrottle>\n'
        '    <minthrottle>             0.1  </minthrottle>\n'
        '    <sparkfaildrop>           0.1  </sparkfaildrop>\n'
        '</piston_engine>')

    heading("flight_control: формування команд", 1, story)
    story.append(p(
        "FCS — це орієнтований граф компонентів, упорядкованих у іменовані "
        "<i>канали</i>. Входи надходять із команд пілота "
        "(<font face='Courier'>fcs/elevator-cmd-norm</font> тощо, задаються "
        "пристроєм вводу чи скриптом), а виходи надходять у властивості "
        "аеродинамічного відхилення (<font face='Courier'>fcs/elevator-pos-rad"
        "</font> тощо), які зчитують аеродинамічні функції."))
    code(
        '<flight_control name="FCS: c172">\n'
        '\n'
        '    <channel name="Pitch">\n'
        '        <summer name="Pitch Trim Sum">\n'
        '            <input>fcs/elevator-cmd-norm</input>\n'
        '            <input>fcs/pitch-trim-cmd-norm</input>\n'
        '            <clipto> <min>-1</min><max>1</max> </clipto>\n'
        '        </summer>\n'
        '\n'
        '        <aerosurface_scale name="Elevator Control">\n'
        '            <input>fcs/pitch-trim-sum</input>\n'
        '            <gain>0.01745</gain>           <!-- deg -> rad -->\n'
        '            <range> <min>-28</min><max>23</max> </range>\n'
        '            <output>fcs/elevator-pos-rad</output>\n'
        '        </aerosurface_scale>\n'
        '    </channel>\n'
        '\n'
        '    <channel name="Flaps">\n'
        '        <kinematic name="Flaps Control">\n'
        '            <input>fcs/flap-cmd-norm</input>\n'
        '            <traverse>\n'
        '                <setting><position>0</position> <time>0</time></setting>\n'
        '                <setting><position>10</position><time>2</time></setting>\n'
        '                <setting><position>20</position><time>2</time></setting>\n'
        '                <setting><position>30</position><time>2</time></setting>\n'
        '            </traverse>\n'
        '            <output>fcs/flap-pos-deg</output>\n'
        '        </kinematic>\n'
        '    </channel>\n'
        '</flight_control>')
    story.append(p(
        "Доступні компоненти FCS включають "
        "<font face='Courier'>summer, pure_gain, scheduled_gain, "
        "aerosurface_scale, kinematic, deadband, switch, fcs_function, "
        "pid, lag_filter, lead_lag_filter, washout_filter, "
        "second_order_filter, integrator, sensor, actuator</font>, а також "
        "узагальнений <font face='Courier'>fcs_function</font>, який "
        "дозволяє вбудувати будь-який вираз мовою функцій як блок. "
        "PID-регулятори та фільтри дискретизують свою неперервно-часову "
        "форму за допомогою кроку симуляції <i>dt</i>."))

    heading("autopilot та system: той самий набір, інша область", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;autopilot&gt;</font> та "
        "<font face='Courier'>&lt;system&gt;</font> використовують ті самі "
        "компоненти FCS та структуру каналів. Їх виокремлено, бо вони "
        "виконуються як окремі підгрупи: типова практика — розміщувати "
        "базове формування команд ручки/педалей у <i>flight_control</i>, "
        "класичні контури автопілота (утримання висоти, утримання курсу, "
        "автомат тяги) — в <i>autopilot</i>, а логіку авіоніки чи "
        "електросистеми — в <i>system</i> (яка може завантажуватися із "
        "зовнішніх файлів у <font face='Courier'>$AC/Systems/</font>)."))

    heading("aerodynamics: ядро моделі", 1, story)
    story.append(p(
        "Аеродинаміка достатньо обширна, щоб заслуговувати на власний "
        "розділ — див. розділ 5. Її каркас такий:"))
    code(
        '<aerodynamics>\n'
        '\n'
        '    <alphalimits unit="RAD">           <!-- physical alpha clamp -->\n'
        '        <min>-0.087</min>\n'
        '        <max> 0.280</max>\n'
        '    </alphalimits>\n'
        '\n'
        '    <hysteresis_limits unit="RAD">     <!-- stall hysteresis -->\n'
        '        <min>0.09</min>\n'
        '        <max>0.36</max>\n'
        '    </hysteresis_limits>\n'
        '\n'
        '    <!-- Helper functions (often ground effect, induced velocity) -->\n'
        '    <function name="aero/function/kCLge"> ... </function>\n'
        '\n'
        '    <!-- Six axes: three forces and three moments -->\n'
        '    <axis name="DRAG">  ...  </axis>\n'
        '    <axis name="SIDE">  ...  </axis>\n'
        '    <axis name="LIFT">  ...  </axis>\n'
        '    <axis name="ROLL">  ...  </axis>\n'
        '    <axis name="PITCH"> ...  </axis>\n'
        '    <axis name="YAW">   ...  </axis>\n'
        '</aerodynamics>')

    heading("input та output", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;input&gt;</font> вмикає зовнішній "
        "інтерфейс, зазвичай сокет TCP/UDP для взаємодії команда/запит у "
        "стилі telnet. <font face='Courier'>&lt;output&gt;</font> "
        "трапляється значно частіше: це конфігурація журналювання для "
        "CSV-файлів, двійкового формату FlightGear, сокетів тощо."))
    code(
        '<output name="flight.csv" type="CSV" rate="60">\n'
        '    <property> aero/qbar-psf </property>\n'
        '    <property> velocities/vt-fps </property>\n'
        '    <rates>     ON </rates>\n'
        '    <velocities>ON </velocities>\n'
        '    <forces>    ON </forces>\n'
        '    <moments>   ON </moments>\n'
        '    <position>  ON </position>\n'
        '    <fcs>       OFF</fcs>\n'
        '    <aerosurfaces>OFF</aerosurfaces>\n'
        '</output>\n'
        '\n'
        '<output type="FLIGHTGEAR" rate="60" protocol="UDP" port="5500"/>\n'
        '\n'
        '<input port="1138"/>     <!-- telnet on TCP 1138 -->')

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 5 - Aerodynamics deep dive
    # ================================================================
    heading("Аеродинаміка — поглиблений розгляд", 0, story)

    heading("Шість осей та функційно-таблична модель", 1, story)
    story.append(p(
        "Усередині <font face='Courier'>&lt;aerodynamics&gt;</font> серцем "
        "моделі є довільна кількість елементів "
        "<font face='Courier'>&lt;function&gt;</font>, згрупованих у блоки "
        "<font face='Courier'>&lt;axis&gt;</font>. JSBSim підсумовує кожну "
        "функцію всередині осі, щоб отримати повну силу чи момент цієї осі "
        "<i>у фізичних одиницях</i> (lbf, ft·lbf). Жодного додаткового "
        "знерозмірнення вона <b>не</b> виконує — множник "
        "<i><font name='DejaVu'>q̄</font>·S</i> ви за домовленістю "
        "вбудовуєте самі."))
    story.append(p(
        "Назви осей відповідають індексам (FGAerodynamics.cpp:57-69):"))
    code(
        "Forces (axis index 0..2)   Moments (axis index 3..5)\n"
        "  0  DRAG                     3  ROLL  (l)\n"
        "  1  SIDE                     4  PITCH (m)\n"
        "  2  LIFT                     5  YAW   (n)\n"
        "\n"
        "Alternative force axes:        Alternative moment frames:\n"
        "  X, Y, Z       (body)         frame=\"WIND\"\n"
        "  AXIAL, NORMAL (axial/norm)   frame=\"STABILITY\"")

    heading("Як обчислюється окрема функція", 1, story)
    story.append(p(
        "Кожна функція щотакту повертає скаляр. Канонічний доданок сили "
        "опору має такий вигляд:"))
    code(
        '<function name="aero/coefficient/CDo">\n'
        '    <description>Drag at zero lift</description>\n'
        '    <product>\n'
        '        <property>aero/qbar-psf</property>     <!-- q-bar -->\n'
        '        <property>metrics/Sw-sqft</property>   <!-- S -->\n'
        '        <value>0.027</value>                   <!-- CD0 -->\n'
        '    </product>\n'
        '</function>')
    math("F<sub>D,0</sub> &nbsp;=&nbsp; C<sub>D0</sub> · <font name='DejaVu'>q̄</font> · S")
    story.append(p(
        "Усередині <font face='Courier'>FGAerodynamics::Run()</font> "
        "значення, повернуті всіма нащадками "
        "<font face='Courier'>&lt;axis name=\"DRAG\"&gt;"
        "</font>, підсумовуються у комірку DRAG масиву "
        "<font face='Courier'>vFnative</font>; комірки LIFT та SIDE "
        "заповнюються так само; потім поворот матрицею "
        "<i>T<sub>w2b</sub></i> переводить сили у швидкісних осях у зв’язану "
        "систему, моменти, обчислені ROLL/PITCH/YAW, додаються в точці "
        "AERORP, і нарешті моменти переносяться в CG за формулою "
        "<i>M<sub>cg</sub> = M<sub>arp</sub> + r<sub>arp→cg</sub> × F"
        "</i>."))

    heading("Мова функцій", 1, story)
    story.append(p(
        "Мова функцій JSBSim — це невелике XML-дерево виразів у стилі Lisp. "
        "Листками є <font face='Courier'>&lt;value&gt;</font> "
        "(константа) та <font face='Courier'>&lt;property&gt;</font> "
        "(посилання на дерево властивостей); внутрішні вузли — це "
        "оператори."))
    code(
        "Arithmetic      sum, difference, product, quotient, pow, sqrt,\n"
        "                abs, min, max, avg\n"
        "Trigonometric   sin, cos, tan, asin, acos, atan, atan2\n"
        "Exponential     exp, ln, log2, log10\n"
        "Logical         lt, le, gt, ge, eq, nq, and, or, not,\n"
        "                ifthen, switch\n"
        "Modular         mod, floor, ceil, fmod, roundmultiple\n"
        "Unit            toradians, todegrees\n"
        "Random          random      (Gaussian),  urandom (uniform)\n"
        "Constants       pi, value/v, integer\n"
        "Table           table   (1-D, 2-D, 3-D, n-D)\n"
        "Property        property/p")
    story.append(p(
        "Цікавіший приклад — індуктивний опір, "
        "<i>C<sub>Di</sub> = C<sub>L</sub>² / (π·AR·e)</i> — перетворений на "
        "функцію JSBSim:"))
    code(
        '<function name="aero/coefficient/CDi">\n'
        '    <description>Induced drag</description>\n'
        '    <product>\n'
        '        <property>aero/qbar-psf</property>\n'
        '        <property>metrics/Sw-sqft</property>\n'
        '        <quotient>\n'
        '            <pow>\n'
        '                <property>aero/cl-squared</property>     <!-- CL^2 -->\n'
        '                <value>0.5</value>                       <!-- *not* powed -->\n'
        '            </pow>\n'
        '            <product>\n'
        '                <pi/>\n'
        '                <property>metrics/aspectratio</property>\n'
        '                <value>0.85</value>                       <!-- e -->\n'
        '            </product>\n'
        '        </quotient>\n'
        '    </product>\n'
        '</function>')

    heading("Таблиці: 1-вимірні, 2-вимірні, 3-вимірні та вищих розмірностей", 1, story)
    story.append(p(
        "Таблиці — це робоча конячка будь-якої нетривіальної моделі: вони "
        "дають змогу закодувати отриманий з CFD пошук будь-якого "
        "коефіцієнта за будь-якою комбінацією змінних стану. JSBSim "
        "використовує <b>лінійну інтерполяцію</b> за кожним виміром; поза "
        "табульованим діапазоном граничне значення фіксується (без "
        "екстраполяції), тож покрити робочу область — ваше завдання."))

    story.append(p(
        "<b>1-вимірна таблиця</b> (векторний пошук за однією змінною):"))
    code(
        '<table>\n'
        '    <independentVar lookup="row">aero/alpha-rad</independentVar>\n'
        '    <tableData>\n'
        '        -0.0900  -0.2200\n'
        '         0.0000   0.2500\n'
        '         0.0900   0.7300\n'
        '         0.1500   1.0000\n'
        '         0.2800   1.1500\n'
        '    </tableData>\n'
        '</table>')

    story.append(p(
        "<b>2-вимірна таблиця</b> (наприклад, сила опору залежно від alpha "
        "та кута відхилення закрилків):"))
    code(
        '<table>\n'
        '    <independentVar lookup="row">aero/alpha-rad</independentVar>\n'
        '    <independentVar lookup="column">fcs/flap-pos-deg</independentVar>\n'
        '    <tableData>\n'
        '                 0.0     10.0    20.0    30.0\n'
        '        -0.0873  0.0041  0.0000  0.0005  0.0014\n'
        '        -0.0349  0.0003  0.0057  0.0108  0.0141\n'
        '         0.0000  0.0052  0.0168  0.0251  0.0299\n'
        '         0.0524  0.0240  0.0452  0.0583  0.0655\n'
        '         0.1571  0.0962  0.1353  0.1573  0.1690\n'
        '    </tableData>\n'
        '</table>')

    story.append(p(
        "<b>3-вимірна таблиця</b> (наприклад, момент тангажа залежно від "
        "alpha, руля висоти, числа Маха). Ви укладаєте 2-вимірні таблиці "
        "стосом, кожна з атрибутом <font face='Courier'>breakPoint"
        "</font> для третього виміру:"))
    code(
        '<table>\n'
        '    <independentVar lookup="row">aero/alpha-rad</independentVar>\n'
        '    <independentVar lookup="column">fcs/elevator-pos-rad</independentVar>\n'
        '    <independentVar lookup="table">velocities/mach</independentVar>\n'
        '\n'
        '    <tableData breakPoint="0.30">           <!-- Mach = 0.30 -->\n'
        '             -0.4  -0.2   0.0   0.2   0.4\n'
        '       -0.1   0.20  0.11  0.04 -0.06 -0.16\n'
        '        0.0   0.15  0.07  0.00 -0.07 -0.15\n'
        '        0.1   0.11  0.04 -0.04 -0.12 -0.21\n'
        '    </tableData>\n'
        '\n'
        '    <tableData breakPoint="0.80">           <!-- Mach = 0.80 -->\n'
        '             -0.4  -0.2   0.0   0.2   0.4\n'
        '       -0.1   0.18  0.10  0.03 -0.05 -0.14\n'
        '        0.0   0.13  0.06  0.00 -0.06 -0.13\n'
        '        0.1   0.10  0.03 -0.03 -0.10 -0.19\n'
        '    </tableData>\n'
        '</table>')
    story.append(p(
        "Вищі розмірності підтримуються рекурсивно. На практиці 3-вимірні "
        "таблиці — це межа того, що варто будувати вручну; для 4-вимірних і "
        "вище використовуйте скрипт для генерації XML із бази даних CFD."))

    heading("Властивості, що часто використовуються в аеродинаміці", 1, story)
    code(
        "aero/qbar-psf                 q-bar = 0.5 * rho * Vt^2  (psf)\n"
        "aero/alpha-rad                angle of attack (radians)\n"
        "aero/beta-rad                 sideslip angle (radians)\n"
        "aero/alphadot-rad_sec         alpha-dot\n"
        "aero/betadot-rad_sec          beta-dot\n"
        "aero/mag-beta-rad             |beta|  (useful in drag terms)\n"
        "aero/bi2vel                   b / (2 V)   --- roll-rate non-dim factor\n"
        "aero/ci2vel                   cbar / (2 V)--- pitch-rate non-dim factor\n"
        "aero/h_b-mac-ft               height above ground / chord, for ground effect\n"
        "aero/cl-squared               CL^2 (computed from previous tick's lift)\n"
        "velocities/p-aero-rad_sec     roll rate in aero frame  (rad/s)\n"
        "velocities/q-aero-rad_sec     pitch rate in aero frame\n"
        "velocities/r-aero-rad_sec     yaw rate in aero frame\n"
        "velocities/mach               Mach number\n"
        "velocities/vt-fps             true airspeed (ft/s)\n"
        "metrics/Sw-sqft               wing area\n"
        "metrics/bw-ft                 wing span\n"
        "metrics/cbarw-ft              mean aerodynamic chord\n"
        "fcs/elevator-pos-rad          elevator deflection from FCS output\n"
        "fcs/aileron-pos-rad           aileron\n"
        "fcs/rudder-pos-rad            rudder\n"
        "fcs/flap-pos-deg              flap (commonly in degrees)\n"
        "gear/gear-pos-norm            gear position (0..1)\n"
        "fcs/speedbrake-pos-rad        speedbrake")
    story.append(p(
        "Кутові швидкості в аеродинамічній системі "
        "<font face='Courier'>p-aero, q-aero, "
        "r-aero</font> — це швидкості у зв’язаній системі, повернуті у "
        "швидкісну систему (повернуту лише на α — зв’язану зі стійкістю "
        "систему). Для похідних демпфування завжди використовуйте саме їх, а "
        "не «сирі» <font face='Courier'>p-rad_sec</font>."))

    heading("Знерозмірнення вручну", 1, story)
    story.append(p(
        "Оскільки JSBSim не знерозмірнює за вас, на вас лягає "
        "відповідальність правильно записати розмірну формулу. Це підручникові "
        "формули, які ви вбудовуєте в <font face='Courier'>"
        "&lt;product&gt;</font>:"))
    math("Lift &nbsp;=&nbsp; C<sub>L</sub> · <font name='DejaVu'>q̄</font> · S")
    math("Drag &nbsp;=&nbsp; C<sub>D</sub> · <font name='DejaVu'>q̄</font> · S")
    math("Side &nbsp;=&nbsp; C<sub>Y</sub> · <font name='DejaVu'>q̄</font> · S")
    math("Roll moment &nbsp;=&nbsp; C<sub>l</sub> · <font name='DejaVu'>q̄</font> · S · b")
    math("Pitch moment &nbsp;=&nbsp; C<sub>m</sub> · <font name='DejaVu'>q̄</font> · S · <font name='DejaVu'>c̄</font>")
    math("Yaw moment &nbsp;=&nbsp; C<sub>n</sub> · <font name='DejaVu'>q̄</font> · S · b")
    story.append(p(
        "Для похідних демпфування помножте на відповідний множник "
        "<i>b/(2V)</i> або <i><font name='DejaVu'>c̄</font>/(2V)</i>:"))
    math("Roll-rate moment &nbsp;=&nbsp; "
         "C<sub>lp</sub> · <font name='DejaVu'>q̄</font> · S · b · [b/(2V)] · p")
    math("Pitch-rate moment &nbsp;=&nbsp; "
         "C<sub>mq</sub> · <font name='DejaVu'>q̄</font> · S · <font name='DejaVu'>c̄</font> · [<font name='DejaVu'>c̄</font>/(2V)] · q")
    math("Yaw-rate moment &nbsp;=&nbsp; "
         "C<sub>nr</sub> · <font name='DejaVu'>q̄</font> · S · b · [b/(2V)] · r")
    math("<font name='DejaVu'>α̇</font> moment &nbsp;=&nbsp; "
         "C<sub>m_<font name='DejaVu'>α̇</font></sub> · <font name='DejaVu'>q̄</font> · S · <font name='DejaVu'>c̄</font> · [<font name='DejaVu'>c̄</font>/(2V)] · <font name='DejaVu'>α̇</font>")

    heading("Розв’язаний приклад: момент крену від кутової швидкості крену", 1, story)
    story.append(p(
        "З <font face='Courier'>aircraft/c172p/c172p.xml:733</font>:"))
    code(
        '<function name="aero/coefficient/Clp">\n'
        '    <description>Roll moment due to roll rate (roll damping)</description>\n'
        '    <product>\n'
        '        <property>aero/qbar-psf</property>           <!-- q-bar -->\n'
        '        <property>metrics/Sw-sqft</property>         <!-- S    -->\n'
        '        <property>metrics/bw-ft</property>           <!-- b    -->\n'
        '        <property>aero/bi2vel</property>             <!-- b/(2V) -->\n'
        '        <property>velocities/p-aero-rad_sec</property> <!-- p   -->\n'
        '        <value>-0.4840</value>                         <!-- Clp  -->\n'
        '    </product>\n'
        '</function>')
    story.append(p(
        "Cl<sub>p</sub> для C-172 є сталим і дорівнює −0,484 — це "
        "демпфування крену крилом. Перемноження дає момент крену у зв’язаній "
        "системі в ft·lbf, чого й очікує вісь ROLL."))

    heading("Статичні похідні — отримання їх із CFD", 1, story)
    story.append(p(
        "Статичні похідні (∂C/∂α, ∂C/∂β, ∂C/∂δ) характеризують "
        "<i>усталений</i> аеродинамічний відгук літального апарата на зміни "
        "α, β та відхилень органів керування. Їх отримують із CFD, "
        "обраховуючи літак як тверде тіло в усталеному стані на сітці точок "
        "(α, β, δ, M) і зчитуючи отримані сили та моменти. Наведений нижче "
        "перелік — це типовий мінімальний набір розгорток для дозвукового "
        "класичного літального апарата:"))
    table_data = [
        ["Похідна", "Незалежні змінні", "Розгортка CFD"],
        ["C<sub>L</sub>(α, M, flap)",        "α, M, flap",
            "усталений крейсер за α ∈ [−6°, 18°], звалювання = фіксація"],
        ["C<sub>D</sub>(α, M, flap, gear)",  "α, M, flap, gear",
            "Та сама матриця; CD = сила опору/<font name='DejaVu'>q̄</font>S"],
        ["C<sub>m</sub>(α, M, δ<sub>e</sub>)", "α, M, δ<sub>e</sub>",
            "α-розгортка за кожного δ<sub>e</sub> та числа Маха"],
        ["C<sub>Y</sub>(β, δ<sub>r</sub>)",  "β, δ<sub>r</sub>",
            "β-розгортка ∈ [−15°, 15°]"],
        ["C<sub>l</sub>(β, α, δ<sub>a</sub>)", "β, α, δ<sub>a</sub>",
            "β-розгортка + прирости δ<sub>a</sub>"],
        ["C<sub>n</sub>(β, α, δ<sub>r</sub>)", "β, α, δ<sub>r</sub>",
            "β-розгортка + прирости δ<sub>r</sub>"],
        ["C<sub>L</sub><sub>α</sub>", "α", "нахил кривої CL-α"],
        ["C<sub>m</sub><sub>α</sub>", "α", "нахил кривої Cm-α (від’ємний → стійкий)"],
        ["C<sub>n</sub><sub>β</sub>", "β", "нахил кривої Cn-β (додатний → стійкий)"],
        ["C<sub>l</sub><sub>β</sub>", "β", "ефект поперечного V"],
    ]
    t = Table(wrap_table(table_data), colWidths=[4.0 * cm, 4.5 * cm, 8.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    heading("Динамічні похідні (демпфування) — CFD з рухом", 1, story)
    story.append(p(
        "Динамічні похідні описують момент, створений кутовою швидкістю "
        "(p, q, r, <font name='DejaVu'>α̇</font>). Їх не можна отримати зі "
        "статичного знімка геометрії в усталеному стані; потрібен "
        "<i>рухомий</i> CFD або класичні інженерні аналоги."))
    for b in [
        "<b>Вимушені коливання</b>: в URANS чи LES змусьте літак "
        "коливатися синусоїдально навколо відповідної осі із заданими "
        "амплітудою та зведеною частотою. Виокремте синфазну та "
        "квадратурну складові моменту — вони дають відповідно статичні та "
        "похідні демпфування. Стандартні промислові інструменти: ANSYS "
        "Fluent, OpenFOAM з overset, STAR-CCM+, NASA OVERFLOW.",
        "<b>Квазістатичний метод</b>: обрахуйте кілька усталених випадків "
        "CFD зі сталою кутовою швидкістю <i>p</i>, накладеною на "
        "інерціальну систему; виокремте момент крену з кожного. Нахил "
        "ΔC<sub>l</sub>/Δ(pb/2V) і є C<sub>lp</sub>. Швидко, але обмежено "
        "малими кутами.",
        "<b>Метод смуг / несної лінії</b>: дешевий інженерний запасний "
        "варіант. Для початкового запуску моделі візьміть довідникові "
        "оцінки (Roskam, Etkin, USAF DATCOM) — для класичних літальних "
        "апаратів вони лежать у межах ±30% від високоточних даних.",
        "<b>Ідентифікація системи</b>: якщо у вас уже є дані льотних "
        "випробувань, підберіть похідні демпфування, мінімізуючи нев’язку "
        "симуляції на маневрі-дублеті. Саме це насправді й роблять статті "
        "AIAA SciTech про «модель, валідовану в польоті».",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Похідні демпфування, які слід отримати щонайменше:"))
    table_data = [
        ["Символ",  "Значення", "Типовий знак", "Метод"],
        ["C<sub>lp</sub>", "Демпфування крену",         "від’ємний",
            "вимушені коливання навколо X"],
        ["C<sub>lr</sub>", "Крен від швидкості рискання", "додатний",
            "вимушені коливання навколо Z"],
        ["C<sub>mq</sub>", "Демпфування тангажа",        "від’ємний",
            "вимушені коливання навколо Y"],
        ["C<sub>m_<font name='DejaVu'>α̇</font></sub>", "Тангаж від <font name='DejaVu'>α̇</font>",    "від’ємний",
            "вимушені коливання занурення"],
        ["C<sub>nr</sub>", "Демпфування рискання",          "від’ємний",
            "вимушені коливання навколо Z"],
        ["C<sub>np</sub>", "Рискання від крену",      "малий, зі знаком",
            "вимушені коливання навколо X"],
        ["C<sub>Yp</sub>", "Бічна сила від крену", "малий",
            "з того самого прогону коливань навколо X"],
        ["C<sub>Yr</sub>", "Бічна сила від рискання",  "малий",
            "з того самого прогону коливань навколо Z"],
    ]
    t = Table(wrap_table(table_data), colWidths=[2.6 * cm, 4.3 * cm, 2.6 * cm, 7.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
    ]))
    story.append(t)

    heading("Похідні керованості", 1, story)
    story.append(p(
        "Похідні керованості (Cm<sub>δe</sub>, Cl<sub>δa</sub>, Cn<sub>δr"
        "</sub>, …) — це нахили моменту залежно від відхилення органа "
        "керування. Вони статичні, тож ви отримуєте їх у тому самому пакеті "
        "усталеного CFD, що й статичні похідні, просто включивши відхилення "
        "органа керування як вісь розгортки. Для нелінійної ефективності "
        "керування (дуже поширеної за великих α чи великих відхилень) "
        "віддавайте перевагу 2-вимірній таблиці "
        "<font face='Courier'>(α, δ)</font>, а не одному коефіцієнту."))
    code(
        '<function name="aero/coefficient/Cmde">\n'
        '    <description>Pitch moment due to elevator</description>\n'
        '    <product>\n'
        '        <property>aero/qbar-psf</property>\n'
        '        <property>metrics/Sw-sqft</property>\n'
        '        <property>metrics/cbarw-ft</property>\n'
        '        <table>\n'
        '            <independentVar lookup="row">aero/alpha-rad</independentVar>\n'
        '            <independentVar lookup="column">fcs/elevator-pos-rad</independentVar>\n'
        '            <tableData>\n'
        '                       -0.40  -0.20   0.00   0.20   0.40\n'
        '              -0.10    0.22   0.11   0.00  -0.11  -0.22\n'
        '               0.00    0.21   0.10   0.00  -0.10  -0.21\n'
        '               0.10    0.18   0.09   0.00  -0.09  -0.18\n'
        '               0.20    0.12   0.06   0.00  -0.06  -0.12\n'
        '            </tableData>\n'
        '        </table>\n'
        '    </product>\n'
        '</function>')

    heading("Вплив екрана та число Рейнольдса", 1, story)
    story.append(p(
        "Вплив екрана (екранний ефект) за домовленістю реалізують як "
        "<i>множник</i> до піднімальної сили та сили опору, обчислюваний як "
        "1-вимірна таблиця залежно від висоти над землею, нормованої на "
        "середню хорду (<font face='Courier'>aero/h_b-mac-ft</font>):"))
    code(
        '<function name="aero/function/kCLge">\n'
        '    <description>Lift multiplier due to ground effect</description>\n'
        '    <table>\n'
        '        <independentVar>aero/h_b-mac-ft</independentVar>\n'
        '        <tableData>\n'
        '            0.00  1.203\n'
        '            0.10  1.127\n'
        '            0.20  1.073\n'
        '            0.50  1.019\n'
        '            1.00  1.002\n'
        '            1.10  1.000\n'
        '        </tableData>\n'
        '    </table>\n'
        '</function>')
    story.append(p(
        "Використовуйте <font face='Courier'>aero/function/kCLge</font> як "
        "множник у функції піднімальної сили. Той самий підхід опрацьовує "
        "вплив числа Маха (таблиця залежно від "
        "<font face='Courier'>velocities/mach</font>) та число Рейнольдса "
        "(таблиця залежно від <font face='Courier'>velocities/reynolds</font>), "
        "якщо у вас є дані CFD для їхнього наповнення."))

    heading("Звалювання та гістерезис звалювання", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;alphalimits&gt;</font> обмежує "
        "<i>фізичний</i> α, що використовується в аеродинамічних "
        "обчисленнях. <font face='Courier'>&lt;hysteresis_limits&gt;</font> "
        "задає смугу перемикання — JSBSim надає "
        "<font face='Courier'>aero/stall-hyst-norm</font>, що дорівнює 0 "
        "нижче нижньої межі та 1 вище верхньої межі. Використовуйте її як "
        "другу вісь таблиці піднімальної сили, щоб закодувати різницю між "
        "кривими піднімальної сили до та після звалювання й отримати "
        "правильну поведінку під час виходу зі звалювання."))

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 6 - Core flight dynamics
    # ================================================================
    heading("Рівняння руху зсередини", 0, story)
    story.append(p(
        "Увесь XML і всі таблиці зрештою живлять невеликий набір звичайних "
        "диференціальних рівнянь. У цьому розділі розглянуто математику так, "
        "як її реалізує JSBSim."))

    heading("Вектор стану", 1, story)
    code(
        "VehicleState {                                      // FGPropagate.h:100\n"
        "  FGLocation     vLocation;          // ECEF position (ft)\n"
        "  FGColumnVector3 vUVW;              // body-frame velocity rel. ECEF\n"
        "  FGColumnVector3 vPQR;              // body-frame angular rate rel. ECEF\n"
        "  FGColumnVector3 vPQRi;             // body-frame angular rate rel. ECI\n"
        "  FGQuaternion   qAttitudeLocal;     // body w.r.t. local NED\n"
        "  FGQuaternion   qAttitudeECI;       // body w.r.t. ECI  <-- primary\n"
        "  FGColumnVector3 vInertialVelocity; // ECI frame velocity\n"
        "  FGColumnVector3 vInertialPosition; // ECI frame position\n"
        "  // ... history deques for multi-step integrators\n"
        "};")

    heading("Кінематика орієнтації через кватерніон", 1, story)
    story.append(p(
        "Орієнтація просувається як кватерніон <i>q<sub>i→b</sub></i> від "
        "інерціальної до зв’язаної системи. Похідна за часом — це "
        "кінематичне рівняння"))
    math("<font name='DejaVu'>q̇</font> &nbsp;=&nbsp; ½ · q ⊗ ω<sub>b/i</sub>")
    story.append(p(
        "де <i>ω<sub>b/i</sub></i> — кутова швидкість тіла відносно "
        "інерціальної системи, виражена у зв’язаній системі "
        "(<font face='Courier'>vPQRi</font>). "
        "<font face='Courier'>FGQuaternion::GetQDot()</font> у JSBSim "
        "обчислює саме це; <font face='Courier'>FGPropagate::CalculateQuatdot()"
        "</font> є обгорткою над ним. Доступно кілька інтеграторів:"))
    code(
        "0  eNone               freeze\n"
        "1  eRectEuler          q(n+1) = q(n) + dt * q-dot(n)\n"
        "2  eTrapezoidal        q(n+1) = q(n) + 0.5*dt*(q-dot(n)+q-dot(n-1))\n"
        "3  eAdamsBashforth2    q(n+1) = q(n) + dt*(1.5 q-dot(n) - 0.5 q-dot(n-1))\n"
        "4  eAdamsBashforth3    23/12, -16/12, +5/12 weights\n"
        "5  eAdamsBashforth4    55/24, -59/24, 37/24, -9/24\n"
        "6  eAdamsBashforth5    classical 5-step coefficients\n"
        "7  eBuss1              q(n+1) = q(n) * exp(0.5*dt*omega)\n"
        "8  eBuss2              augmented with omega-dot terms\n"
        "9  eLocalLinearization Barker et al. (NASA TN D-7347)")
    story.append(p(
        "Типові інтегратори — прямокутний метод Ейлера для орієнтації та "
        "кутової швидкості, Adams-Bashforth-2 для поступальної швидкості, "
        "Adams-Bashforth-3 для положення. Інтегратори Buss цікаві тим, що "
        "точно зберігають норму кватерніона (без потреби в "
        "перенормуванні, якого прямокутний метод Ейлера потребує "
        "щотакту)."))

    heading("Поступальна динаміка в інерціальній системі", 1, story)
    story.append(p(
        "JSBSim розв’язує другий закон Ньютона в інерціальній системі та "
        "перетворює назад у зв’язані координати для виведення:"))
    math("<font name='DejaVu'>v̇</font><sub>body</sub> &nbsp;=&nbsp; F/m &nbsp;−&nbsp; "
         "(p<sub>body</sub> + 2·T<sub>i2b</sub>·Ω<sub>planet</sub>) × v<sub>body</sub>"
         " &nbsp;−&nbsp; T<sub>i2b</sub>·Ω<sub>planet</sub> × (Ω<sub>planet</sub> × r<sub>i</sub>)")
    story.append(p(
        "Перший доданок — це звичайне <i>F = ma</i>. Другий — коріолісове "
        "прискорення, включно з внеском від обертання Землі "
        "(Ω<sub>planet</sub> ≈ 7.292·10⁻⁵ rad/s навколо осі Z системи "
        "ECI). Третій — відцентрове прискорення від обертання навколо "
        "центра Землі. Для польотів у межах атмосфери на масштабах "
        "транспортних літаків ці доданки малі, але помітні — саме завдяки "
        "їм симулятор узгоджується з контрольними прикладами NASA-2015."))

    heading("Обертальна динаміка", 1, story)
    math("J · <font name='DejaVu'>ω̇</font><sub>i</sub> &nbsp;=&nbsp; M &nbsp;−&nbsp; "
         "ω<sub>i</sub> × (J · ω<sub>i</sub>)")
    story.append(p(
        "Доданок <i>ω × (Jω)</i> — це ейлерів гіроскопічний момент "
        "(ненульовий завжди, коли тензор інерції не ізотропний). "
        "<font face='Courier'>FGAccelerations::CalculatePQRdot()</font> "
        "обчислює його безпосередньо. Тензор інерції J у зв’язаній системі "
        "підтримується <i>FGMassBalance</i> і оновлюється щотакту, щоб "
        "враховувати вигоряння палива та зсуви точкових мас. Опціональний "
        "момент від градієнта гравітації вмикається через властивість "
        "<font face='Courier'>simulation/gravitational-torque</font>; "
        "корисно для орбітальної механіки."))

    heading("Збирання повної сили та моменту", 1, story)
    story.append(p(
        "<font face='Courier'>FGAircraft</font> підсумовує сили та моменти "
        "з моделей <i>аеродинаміки, силової установки, опори, зовнішніх "
        "реакцій, плавучості</i> і подає їх як єдині F та M у зв’язаній "
        "системі моделі Accelerations. Гравітацію окремо опрацьовує "
        "<font face='Courier'>FGInertial</font> (сферична або "
        "WGS-84 з доданком J2) і додає її безпосередньо до вектора "
        "прискорення — виключення її з M означає, що момент гравітації "
        "відносно CG автоматично дорівнює нулю (гравітація за визначенням "
        "діє в CG)."))

    heading("Наземне тертя як задача з обмеженнями", 1, story)
    story.append(p(
        "Звичайне явне інтегрування жорстких пружинно-демпферних моделей "
        "шасі є нестійким. Натомість JSBSim формулює задачу тертя як "
        "<i>задачу лінійної доповняльності (LCP)</i>: кожна точка контакту "
        "накладає обмеження невзаємопроникнення за нормаллю до ЗПС і "
        "обмеження кулонівського тертя по дотичній до неї. Невідомими є "
        "множники Лагранжа λ. Система "
        "<i>A · λ = b</i> з <i>A = J · M<sup>−1</sup> · Jᵀ</i> "
        "розв’язується ітеративно (проєктований метод Гаусса-Зейделя, Catto "
        "2005) до 50 ітерацій на такт — див. "
        "<font face='Courier'>FGAccelerations::CalculateFrictionForces()"
        "</font>. Контактні сили тертя та момент "
        "<i>r × F</i> потім додаються до векторів F та M."))

    heading("Балансування", 1, story)
    story.append(p(
        "Балансування реалізовано в <font face='Courier'>FGTrim</font> "
        "розв’язувачем кореня з обмеженням інтервалу, що застосовується "
        "незалежно до кожної пари вісь-керування й ітерується у "
        "зовнішньому циклі, доки всі осі не збіжаться. Це <b>не</b> метод "
        "Ньютона-Рафсона — JSBSim використовує варіант методу січних із "
        "лінійною інтерполяцією та коефіцієнтом релаксації 0,9 для "
        "придушення коливань. Режими такі:"))
    table_data = [
        ["Режим", "Обмеження", "Органи керування"],
        ["tLongitudinal", "<font name='DejaVu'>w̄</font>˙=0, <font name='DejaVu'>ū</font>˙=0, <font name='DejaVu'>q̄</font>˙=0", "α, дросель, руль висоти"],
        ["tFull",  "поздовжній + <font name='DejaVu'>v̇</font>=0, ṗ=0, ṙ=0 + утримання ψ",
            "+ φ, елерони, руль напряму, β"],
        ["tGround", "<font name='DejaVu'>w̄</font>˙=0, <font name='DejaVu'>q̄</font>˙=0, ṗ=0", "висота, θ, φ"],
        ["tPullup", "поздовжній за цільового перевантаження", "α, дросель, руль висоти"],
        ["tTurn",   "координований віраж за цільового кута крену",
            "дросель, руль висоти, руль напряму"],
        ["tCustom", "користувацькі пари (стан, керування)", "будь-які"],
    ]
    t = Table(wrap_table(table_data), colWidths=[3.0 * cm, 7.5 * cm, 6.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
    ]))
    story.append(t)

    heading("Модель атмосфери", 1, story)
    story.append(p(
        "<font face='Courier'>FGStandardAtmosphere</font> реалізує "
        "Стандартну атмосферу США 1976 року через кусково-лінійні "
        "вертикальні градієнти температури від 0 до 86 км. Властивості "
        "надаються в розділі <font face='Courier'>atmosphere/</font>: "
        "<font face='Courier'>T-R</font>, "
        "<font face='Courier'>P-psf</font>, "
        "<font face='Courier'>rho-slugs_ft3</font>, "
        "<font face='Courier'>a-fps</font>. Можна створити власний підклас "
        "атмосфери; модель C-172 зсуває температуру, щоб змоделювати ефекти "
        "висоти за щільністю."))

    heading("Вітри та турбулентність", 1, story)
    story.append(p(
        "<font face='Courier'>FGWinds</font> підтримує:"))
    for b in [
        "Усталений вітер у NED (задається через "
        "<font face='Courier'>atmosphere/wind-north-fps</font>, "
        "<font face='Courier'>wind-east-fps</font>, "
        "<font face='Courier'>wind-down-fps</font>).",
        "Лінійний зсув вітру з висотою.",
        "Пориви вітру (модель «дискретного пориву» 1-cosine, що "
        "використовується в MIL-F-8785C).",
        "Неперервну турбулентність за Драйденом або фон Карманом із "
        "налаштовуваними інтенсивністю та масштабами.",
        "Модель мікропориву (microburst) з трьома складовими та вихровим "
        "кільцем.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "<font face='Courier'>FGAuxiliary</font> споживає вектор вітру для "
        "обчислення швидкості відносно повітряної маси, яку використовує "
        "аеродинаміка."))

    heading("Дерево властивостей", 1, story)
    story.append(p(
        "<font face='Courier'>FGPropertyManager</font> є обгорткою над "
        "деревом властивостей SimGear. Кожна змінна стану, керувальний вхід, "
        "сигнал FCS, аеродинамічний коефіцієнт та атмосферна величина "
        "доступні за рядковим шляхом; значення курсують між моделями "
        "цілком через нього. Елементи "
        "<font face='Courier'>&lt;property&gt;</font> в XML літального "
        "апарата можуть <i>оголошувати</i> нову властивість (створюючи її за "
        "потреби); компоненти FCS, аеродинамічні функції та зовнішні "
        "інтерфейси всі прив’язуються до цього дерева."))
    code(
        "# Inspect a property in the JSBSim Python module\n"
        "import jsbsim\n"
        "fdm = jsbsim.FGFDMExec(None)\n"
        "fdm.load_model(\"c172p\")\n"
        "fdm.run_ic()\n"
        "print(fdm[\"velocities/vt-fps\"], fdm[\"aero/alpha-deg\"])")

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 7 - Building your own aircraft
    # ================================================================
    heading("Побудова власного літального апарата, крок за кроком", 0, story)
    story.append(p(
        "Це практичний посібник до дії. Ми припускаємо, що у вас є доступ до "
        "<b>геометрії</b> (CAD або принаймні три проєкції), <b>масових "
        "характеристик</b> (вага, CG, в ідеалі оцінка інерції), <b>даних "
        "двигуна</b> (криві потужності чи тяги) та <b>аеродинамічних "
        "даних</b> (CFD або аеродинамічна труба). Наведений нижче робочий "
        "процес поєднує їх у робочу модель JSBSim за пару тижнів неповної "
        "зайнятості."))

    heading("Крок 1: Структура каталогу", 1, story)
    code(
        "$JSBSIM_ROOT/aircraft/MyAcft/\n"
        "    MyAcft.xml          # the main XML (this is what JSBSim loads)\n"
        "    reset00.xml         # initial conditions for default launch\n"
        "    Systems/            # (optional) external <system> files\n"
        "    Engines/            # (optional) aircraft-specific engine files\n"
        "$JSBSIM_ROOT/scripts/\n"
        "    MyAcft_takeoff.xml  # a script that loads MyAcft + reset00")
    story.append(p(
        "Двигуни та повітряні гвинти можуть розміщуватися у спільному для "
        "проєкту каталозі <font face='Courier'>$JSBSIM_ROOT/engine/</font>, "
        "якщо ви хочете повторно використовувати їх для кількох планерів."))

    heading("Крок 2: Каркас XML", 1, story)
    code(
        '<?xml version="1.0"?>\n'
        '<fdm_config name="MyAcft" version="2.0" release="ALPHA"\n'
        '    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
        '    xsi:noNamespaceSchemaLocation="http://jsbsim.sourceforge.net/JSBSim.xsd">\n'
        '\n'
        '    <fileheader>\n'
        '        <author>You</author>\n'
        '        <filecreationdate>2026-05-24</filecreationdate>\n'
        '        <description>My new aircraft.</description>\n'
        '    </fileheader>\n'
        '\n'
        '    <metrics>            ... </metrics>\n'
        '    <mass_balance>       ... </mass_balance>\n'
        '    <ground_reactions>   ... </ground_reactions>\n'
        '    <propulsion>         ... </propulsion>\n'
        '    <flight_control name="FCS: MyAcft">\n'
        '        <channel name="Pitch"> ... </channel>\n'
        '        <channel name="Roll">  ... </channel>\n'
        '        <channel name="Yaw">   ... </channel>\n'
        '    </flight_control>\n'
        '    <aerodynamics>       ... </aerodynamics>\n'
        '    <output type="CSV" rate="60" name="MyAcft.csv">\n'
        '        <rates>ON</rates>\n'
        '        <velocities>ON</velocities>\n'
        '        <position>ON</position>\n'
        '    </output>\n'
        '</fdm_config>')

    heading("Крок 3: Геометрія, маса та шасі", 1, story)
    story.append(p(
        "<b>Геометрія</b>: з вашого CAD витягніть площу крила "
        "<i>S</i>, розмах крила <i>b</i>, середню аеродинамічну хорду "
        "<i><font name='DejaVu'>c̄</font></i>, площі та плечі оперення. "
        "Виберіть AERORP на 25% MAC і розмістіть його у своїй конструктивній "
        "системі. Визначте розташування CG (будь-яка прийнятна точка з "
        "діапазону центрування — пізніше ви зможете зсунути його точковими "
        "масами)."))
    story.append(p(
        "<b>Маса</b>: споряджена вага + екіпаж/пасажири/вантаж як точкові "
        "маси. Щодо інерції: якщо у вас є CAD-модель, найпростіше "
        "експортувати її в інструмент кінематики (SolidWorks, Onshape, "
        "Fusion 360), який видає вам I<sub>xx,yy,zz,xy,xz,yz</sub> відносно "
        "CG безпосередньо. Інакше оцініть за радіусами інерції "
        "(Roskam т. V, таблиці 9.1-9.4)."))
    story.append(p(
        "<b>Шасі</b>: розмістіть кожну точку контакту в конструктивній "
        "системі. Вибір пружності/демпфування — частково мистецтво, "
        "частково розрахунок: орієнтуйтеся на статичне обтиснення 2-4 дюйми "
        "під вагою на колесах і коефіцієнт демпфування близько 0,3-0,5. "
        "Швидка оцінка:"))
    math("k &nbsp;=&nbsp; W<sub>gear</sub> / Δ<sub>static</sub>"
         " &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
         "c &nbsp;=&nbsp; 2 ζ √(k · W<sub>gear</sub> / g)")

    heading("Крок 4: Силова установка", 1, story)
    story.append(p(
        "Виберіть файл двигуна, що відповідає вашому типу. Стандартна "
        "бібліотека двигунів JSBSim має гарні відправні точки: "
        "<font face='Courier'>eng_io320</font> (160 к.с., 4-циліндровий), "
        "<font face='Courier'>CFM56</font> (турбовентиляторний), "
        "<font face='Courier'>F100-PW-229</font> (турбовентиляторний із "
        "форсажем), "
        "<font face='Courier'>Estes_E9</font> (модельна ракета), "
        "<font face='Courier'>DJI_E305</font> (електричний для дрона). Для "
        "нового двигуна скопіюйте наявний файл і відредагуйте робочий "
        "об’єм / максимальну потужність / BSFC / діапазон обертів. "
        "Поєднайте двигун із рушієм — "
        "<font face='Courier'>direct</font> для реактивних "
        "двигунів/ракет, <font face='Courier'>prop_*</font> для повітряних "
        "гвинтів."))
    code(
        '<propulsion>\n'
        '    <engine file="eng_io360">              <!-- 180 hp -->\n'
        '        <feed>0</feed>\n'
        '        <feed>1</feed>\n'
        '        <thruster file="prop_77in">\n'
        '            <location unit="IN"> <x>-30</x><y>0</y><z>2</z> </location>\n'
        '            <orient unit="DEG"><pitch>2</pitch></orient>  <!-- thrust line up 2° -->\n'
        '        </thruster>\n'
        '    </engine>\n'
        '    <tank type="FUEL" number="0">\n'
        '        <location unit="IN"><x>0</x><y>-80</y><z>30</z></location>\n'
        '        <capacity unit="LBS">300</capacity>\n'
        '        <contents unit="LBS">280</contents>\n'
        '    </tank>\n'
        '    <tank type="FUEL" number="1">\n'
        '        <location unit="IN"><x>0</x><y>80</y><z>30</z></location>\n'
        '        <capacity unit="LBS">300</capacity>\n'
        '        <contents unit="LBS">280</contents>\n'
        '    </tank>\n'
        '</propulsion>')

    heading("Крок 5: Система керування польотом", 1, story)
    story.append(p(
        "Найпростіша можлива FCS просто відображає "
        "<font face='Courier'>fcs/elevator-cmd-norm</font> (−1..+1) на "
        "<font face='Courier'>fcs/elevator-pos-rad</font> через "
        "<font face='Courier'>aerosurface_scale</font>. Реальні літаки "
        "додають суматори балансування, обмеження швидкості, зони "
        "нечутливості, фільтри поривів, автопілоти — але починайте з "
        "мінімуму, доб’йтеся, щоб літак летів у розімкненому контурі, а "
        "потім нарощуйте складність."))

    heading("Крок 6: Аеродинаміка з CFD", 1, story)
    story.append(p(
        "Це найбільш трудомісткий крок. Загальна процедура:"))
    story.append(bullet(
        "<b>1. Визначте сітку розгортки.</b> Розумна дозвукова сітка — це "
        "α ∈ {−6, −4, −2, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18} deg, "
        "β ∈ {−15, −10, −5, 0, 5, 10, 15} deg, "
        "число Маха ∈ {0.15, 0.30, 0.50, 0.70}, "
        "відхилення органів керування по 5-7 точок кожне. Це приблизно "
        "3000 випадків CFD для повної пошукової матриці; на практиці ви "
        "розв’язуєте їх роздільно."))
    story.append(bullet(
        "<b>2. Обрахуйте усталені випадки RANS</b> у вашому інструменті CFD "
        "на вибір (OpenFOAM, Fluent, STAR-CCM+, SU2). Для кожного випадку "
        "витягніть <i>F<sub>x</sub>, F<sub>y</sub>, F<sub>z</sub>, "
        "M<sub>x</sub>, M<sub>y</sub>, M<sub>z</sub></i> у зв’язаній "
        "системі відносно AERORP і перетворіть на коефіцієнти, поділивши на "
        "<i><font name='DejaVu'>q̄</font>·S</i>, "
        "<i><font name='DejaVu'>q̄</font>·S·b</i>, "
        "<i><font name='DejaVu'>q̄</font>·S·<font name='DejaVu'>c̄</font></i>."))
    story.append(bullet(
        "<b>3. Розв’язуйте роздільно, де можливо.</b> Зазвичай беріть "
        "C<sub>L</sub>, C<sub>D</sub>, C<sub>m</sub> з α-розгортки за "
        "β=0; беріть C<sub>Y</sub>, C<sub>l</sub>, C<sub>n</sub> з "
        "β-розгорток за α=0; беріть похідні керованості як нахил моменту "
        "залежно від відхилення в умовах балансування. Для моделей із "
        "великими α чи трансзвукових зв’язаність реальна, і повна "
        "2-вимірна чи 3-вимірна таблиця вам справді потрібна."))
    story.append(bullet(
        "<b>4. Обрахуйте випадки похідних демпфування</b> — або вимушені "
        "коливання, або квазістатичні крен/рискання/тангаж зі сталою "
        "швидкістю. Витягніть C<sub>lp</sub>, C<sub>mq</sub>, "
        "C<sub>nr</sub>, C<sub>lr</sub>, C<sub>np</sub>, "
        "C<sub>m_<font name='DejaVu'>α̇</font></sub>."))
    story.append(bullet(
        "<b>5. Табулюйте та валідуйте.</b> Побудуйте графік кожного "
        "коефіцієнта як функції кожної незалежної змінної. Шукайте "
        "немонотонну поведінку, якої ви не очікували — зазвичай це ознака "
        "проблем із сіткою чи збіжністю."))
    story.append(bullet(
        "<b>6. Перетворіть на XML JSBSim.</b> Формат — це проста матриця "
        "чисел у <font face='Courier'>&lt;tableData&gt;</font>. Скрипт "
        "Python у наступному розділі автоматизує це."))

    heading("Крок 7: Початкові умови та скрипт димового тесту", 1, story)
    code(
        '<!-- reset00.xml -->\n'
        '<?xml version="1.0"?>\n'
        '<initialize name="reset00">\n'
        '    <ubody unit="FT/SEC">  150 </ubody>     <!-- ~100 KT -->\n'
        '    <vbody unit="FT/SEC">   0  </vbody>\n'
        '    <wbody unit="FT/SEC">   0  </wbody>\n'
        '    <latitude unit="DEG">  37.6 </latitude>\n'
        '    <longitude unit="DEG">-122.4</longitude>\n'
        '    <altitude  unit="FT">  5000 </altitude>\n'
        '    <phi unit="DEG">  0 </phi>\n'
        '    <theta unit="DEG">2 </theta>\n'
        '    <psi unit="DEG"> 90 </psi>               <!-- heading east -->\n'
        '</initialize>')
    code(
        '<!-- scripts/MyAcft_smoke.xml -->\n'
        '<?xml version="1.0"?>\n'
        '<runscript name="MyAcft smoke">\n'
        '    <use aircraft="MyAcft" initialize="reset00"/>\n'
        '    <run start="0" end="120" dt="0.00833333">\n'
        '        <event name="Trim">\n'
        '            <condition>simulation/sim-time-sec ge 0</condition>\n'
        '            <set name="simulation/do_simple_trim" value="1"/>\n'
        '            <notify/>\n'
        '        </event>\n'
        '        <event name="Pitch doublet">\n'
        '            <condition>simulation/sim-time-sec ge 30</condition>\n'
        '            <set name="fcs/elevator-cmd-norm" value="0.2" type="FG_VALUE"/>\n'
        '            <notify/>\n'
        '        </event>\n'
        '        <event name="Pitch return">\n'
        '            <condition>simulation/sim-time-sec ge 32</condition>\n'
        '            <set name="fcs/elevator-cmd-norm" value="0"/>\n'
        '            <notify/>\n'
        '        </event>\n'
        '    </run>\n'
        '</runscript>')
    story.append(p(
        "Запустіть це командою:"))
    code("JSBSim --script=scripts/MyAcft_smoke.xml --logdirectivefile=...")

    heading("Крок 8: Цикл ітерацій", 1, story)
    for b in [
        "<b>Чи балансується?</b> Якщо "
        "<font face='Courier'>do_simple_trim</font> "
        "не вдається, перевірте домовленості про знаки (руль висоти "
        "створює правильний напрям моменту тангажа), перевірте, що "
        "Cm<sub>α</sub> &lt; 0 (статична стійкість за тангажем), і "
        "перевірте, що діапазон α ваших таблиць покриває α балансування.",
        "<b>Чи летить прямо?</b> Статична бічно-курсова стійкість потребує "
        "Cn<sub>β</sub> &gt; 0 та Cl<sub>β</sub> &lt; 0. Якщо літак "
        "звалюється в крен, перевірте ефект поперечного V.",
        "<b>Чи реагує як справжній літак?</b> Порівняйте власні значення "
        "фугоїда, короткоперіодичного руху, голландського кроку, режиму "
        "крену та спірального руху з опублікованими даними чи льотними "
        "випробуваннями.",
        "<b>Чи приземляється?</b> Налаштовуйте пружність/демпфування шасі, "
        "доки відскок не виглядатиме правильно. Якщо літак провалюється "
        "крізь ЗПС, ваша пружина заслабка або точка контакту зависока (Z "
        "надто додатне в конструктивній системі).",
    ]:
        story.append(bullet(b))

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 8 - CFD workflow in depth
    # ================================================================
    heading("Робочий процес CFD-to-JSBSim", 0, story)
    story.append(p(
        "У цьому розділі описано рекомендований робочий процес генерування "
        "аеродинамічних таблиць JSBSim із даних CFD, включно з конкретними "
        "випадками для обрахунку, формулами до застосування та еталонним "
        "скриптом Python для перетворення результатів на XML JSBSim."))

    heading("Вибір розв’язувача CFD", 1, story)
    for b in [
        "<b>OpenFOAM</b> (відкритий код) — <i>simpleFoam</i> для усталеного "
        "RANS; <i>pimpleFoam</i> з overset для рухомих сіток. Безкоштовний, "
        "але якість сітки та вибір моделі турбулентності — на вас.",
        "<b>SU2</b> (відкритий код) — сучасний, із підтримкою спряжених "
        "методів, добрий як для оптимізації форми, так і для аналізу.",
        "<b>ANSYS Fluent / STAR-CCM+</b> — комерційні, дуже зрілі. Варті "
        "ліцензії, якщо вона у вас є.",
        "<b>NASA OVERFLOW / FUN3D</b> — структурований/неструктурований "
        "RANS дослідницького рівня, доступний університетам США.",
        "<b>XFLR5 / AVL</b> (вихрова ґратка) — швидкі, на диво точні для "
        "дозвукових оцінок на ранніх етапах проєктування. Використовуйте "
        "їх для початкового наближення, перш ніж витрачати бюджет на CFD.",
    ]:
        story.append(bullet(b))

    heading("Рекомендована матриця випадків", 1, story)
    story.append(p(
        "Для класичного дозвукового літального апарата повна модель "
        "потребує наведених нижче випадків. Кожен — це окремий прогін CFD."))
    table_data = [
        ["Група", "Розгортка", "α (deg)", "β (deg)", "Результат"],
        ["Поздовжня статика",
            "α у чистій конфігурації, β=0",
            "від −6 до +18 крок 2",
            "0",
            "C<sub>L</sub>(α), C<sub>D</sub>(α), C<sub>m</sub>(α)"],
        ["Поздовжня із закрилками",
            "α × flap",
            "від −4 до +14 крок 2",
            "0",
            "ΔC<sub>L</sub>, ΔC<sub>D</sub>, ΔC<sub>m</sub> залежно від flap"],
        ["Поздовжня з рулем висоти",
            "α × δ<sub>e</sub>",
            "від −4 до +14 крок 2",
            "0",
            "C<sub>m_δe</sub>(α, δ<sub>e</sub>)"],
        ["Бічна статика",
            "β за α<sub>cruise</sub>",
            "α<sub>cr</sub>",
            "від −15 до +15 крок 3",
            "C<sub>Y</sub>(β), C<sub>l</sub>(β), C<sub>n</sub>(β)"],
        ["Елерони",
            "β × δ<sub>a</sub>",
            "α<sub>cr</sub>",
            "від −10 до +10",
            "C<sub>l_δa</sub>, C<sub>n_δa</sub>"],
        ["Руль напряму",
            "β × δ<sub>r</sub>",
            "α<sub>cr</sub>",
            "від −10 до +10",
            "C<sub>Y_δr</sub>, C<sub>n_δr</sub>"],
        ["Стисливість",
            "число Маха",
            "0",
            "0",
            "ΔC<sub>D</sub>(M), ΔC<sub>m</sub>(M)"],
        ["Вплив екрана",
            "h/<font name='DejaVu'>c̄</font>",
            "α<sub>cr</sub>",
            "0",
            "k<sub>CL,ge</sub>(h/<font name='DejaVu'>c̄</font>), k<sub>CD,ge</sub>(h/<font name='DejaVu'>c̄</font>)"],
        ["Демпфування тангажа",
            "вимуш. кол. навколо Y",
            "α<sub>cr</sub>",
            "0",
            "C<sub>mq</sub>, C<sub>m_<font name='DejaVu'>α̇</font></sub>"],
        ["Демпфування крену",
            "вимуш. кол. навколо X",
            "α<sub>cr</sub>",
            "0",
            "C<sub>lp</sub>, C<sub>Yp</sub>, C<sub>np</sub>"],
        ["Демпфування рискання",
            "вимуш. кол. навколо Z",
            "α<sub>cr</sub>",
            "0",
            "C<sub>nr</sub>, C<sub>Yr</sub>, C<sub>lr</sub>"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[3.2 * cm, 3.6 * cm, 2.0 * cm, 2.0 * cm, 5.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(p(
        "Якщо у вас є трансзвукові чи надзвукові режими, додайте число Маха "
        "як третю вісь до всіх поздовжніх випадків. Для винищувача чи "
        "ударного БПЛА (UCAV), що працює на великих α, подвоюйте діапазон "
        "α та крок."))

    heading("Метод вимушених коливань для похідних демпфування", 1, story)
    story.append(p(
        "Найчистіший спосіб отримати C<sub>mq</sub> тощо з CFD — змусити "
        "геометрію коливатися синусоїдально навколо відповідної осі з малою "
        "амплітудою та відомою зведеною частотою, а потім підібрати синфазну "
        "та квадратурну складові моменту. Для демпфування тангажа:"))
    math("θ(t) &nbsp;=&nbsp; θ<sub>0</sub> + Δθ · sin(ω t)")
    math("q(t) &nbsp;=&nbsp; Δθ · ω · cos(ω t)")
    math("C<sub>m</sub>(t) &nbsp;=&nbsp; C<sub>m,0</sub> &nbsp;+&nbsp; "
         "C<sub>m_α</sub> · Δα · sin(ωt) &nbsp;+&nbsp; "
         "[C<sub>mq</sub> + C<sub>m_<font name='DejaVu'>α̇</font></sub>] · (<font name='DejaVu'>c̄</font>/2V) · Δθ · ω · cos(ωt)")
    story.append(p(
        "Підбирайте методом найменших квадратів: коефіцієнт при cos дорівнює "
        "(C<sub>mq</sub> + C<sub>m_<font name='DejaVu'>α̇</font></sub>)·(<font name='DejaVu'>c̄</font>/2V)·Δθ·ω, коефіцієнт при sin "
        "дорівнює C<sub>m_α</sub>·Δα. Відокремлення C<sub>mq</sub> від "
        "C<sub>m_<font name='DejaVu'>α̇</font></sub> потребує додаткових коливань <i>занурення</i> "
        "(α змінюється без зміни q). На практиці багато довідників просто "
        "публікують суму (C<sub>mq</sub> + C<sub>m_<font name='DejaVu'>α̇</font></sub>) і розбивають "
        "її приблизно як 70/30."))
    story.append(p(
        "Рекомендовані амплітуди та зведені частоти для транспортного "
        "літака: Δθ = 1°, k = ω<font name='DejaVu'>c̄</font>/(2V) ∈ [0.01, 0.1]. П’ять чи десять циклів "
        "у CFD перед виокремленням підгонки."))

    heading("Квазістатичний метод (швидший)", 1, story)
    story.append(p(
        "Обрахуйте кілька усталених випадків CFD зі <i>сталою</i> кутовою "
        "швидкістю у зв’язаній системі, прикладеною як обертова система "
        "відліку. Побудуйте графік отриманого моменту залежно від pb/(2V) "
        "(або q<font name='DejaVu'>c̄</font>/(2V), чи rb/(2V)); нахил — це похідна "
        "демпфування. Це значно дешевше за URANS, але справедливо лише для "
        "малих швидкостей та нестисливого потоку. Достатньо для моделі "
        "першого наближення."))

    heading("Виокремлення та табулювання", 1, story)
    story.append(p(
        "Кожен випадок CFD дає вам F та M у зв’язаній системі відносно "
        "відомої точки. Перетворіть на коефіцієнти у зв’язаній системі "
        "відносно AERORP, а потім поверніть коефіцієнти сил у швидкісну "
        "вісь, якщо ваша модель JSBSim використовує LIFT/DRAG/SIDE:"))
    math("C<sub>L</sub> &nbsp;=&nbsp; C<sub>Z</sub> cos α &nbsp;−&nbsp; "
         "C<sub>X</sub> sin α")
    math("C<sub>D</sub> &nbsp;=&nbsp; −C<sub>X</sub> cos α &nbsp;−&nbsp; "
         "C<sub>Z</sub> sin α")
    math("C<sub>Y</sub> &nbsp;(unchanged from body)")

    heading("Допоміжний скрипт Python: CSV із CFD → XML JSBSim", 1, story)
    story.append(p(
        "Мінімальний генератор, що перетворює CSV зі стовпцями "
        "<font face='Courier'>alpha_deg, flap_deg, CL, CD, Cm</font> "
        "на блок функцій LIFT/DRAG/PITCH у JSBSim:"))
    code(
        "import pandas as pd\n"
        "\n"
        "df = pd.read_csv('cfd_results.csv')\n"
        "alphas = sorted(df.alpha_deg.unique())\n"
        "flaps  = sorted(df.flap_deg.unique())\n"
        "\n"
        "def emit_table(name, indvar_row, indvar_col, rows, cols, values):\n"
        "    out = ['<table>',\n"
        "           f'  <independentVar lookup=\"row\">{indvar_row}</independentVar>',\n"
        "           f'  <independentVar lookup=\"column\">{indvar_col}</independentVar>',\n"
        "           '  <tableData>']\n"
        "    header = '          ' + '  '.join(f'{c:8.3f}' for c in cols)\n"
        "    out.append(header)\n"
        "    for r in rows:\n"
        "        row = [f'{r:8.4f}'] + [f'{values[(r,c)]:8.4f}' for c in cols]\n"
        "        out.append('  ' + '  '.join(row))\n"
        "    out += ['  </tableData>', '</table>']\n"
        "    return '\\n'.join(out)\n"
        "\n"
        "CL = {(r,c): df[(df.alpha_deg==r)&(df.flap_deg==c)].CL.iloc[0]\n"
        "      for r in alphas for c in flaps}\n"
        "\n"
        "print('<function name=\"aero/coefficient/CL\">')\n"
        "print('  <product>')\n"
        "print('    <property>aero/qbar-psf</property>')\n"
        "print('    <property>metrics/Sw-sqft</property>')\n"
        "alpha_rad = sorted([a*3.14159/180 for a in alphas])\n"
        "print(emit_table('CL', 'aero/alpha-rad', 'fcs/flap-pos-deg',\n"
        "                 alpha_rad, flaps, CL))\n"
        "print('  </product>')\n"
        "print('</function>')")

    heading("Валідація: від чисел CFD до відчуття польоту", 1, story)
    story.append(p(
        "Три класи валідації, у порядку зростання складності:"))
    for b in [
        "<b>Графіки коефіцієнтів</b> — накладіть коефіцієнти JSBSim на "
        "вихідні дані CFD. Вони мають збігатися за побудовою; якщо ні, у вас "
        "помилка в одиницях.",
        "<b>Аналіз власних значень</b> — лінеаризуйте модель JSBSim на "
        "крейсерському режимі за допомогою вбудованого інструмента "
        "<font face='Courier'>python/JSBSim/utils/linearize</font>. "
        "Порівняйте корені фугоїда, короткоперіодичного руху, голландського "
        "кроку, крену та спірального руху з підручниковими оцінками "
        "(Stevens-Lewis, розд. 5) чи опублікованими даними для подібних "
        "літаків.",
        "<b>Зіставлення маневрів</b> — виконайте дублети тангажа, бочки "
        "елеронами, удари рулем напряму. Побудуйте графіки p, q, r, α, β. "
        "Порівняйте з льотними випробуваннями чи задокументованими "
        "пілотажними характеристиками (Cooper-Harper, MIL-F-8785C).",
    ]:
        story.append(bullet(b))

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 9 - Reference appendices
    # ================================================================
    heading("Довідкові додатки", 0, story)

    heading("Шпаргалка з дерева властивостей", 1, story)
    code(
        "# Pilot inputs (writable from any external program / script)\n"
        "fcs/elevator-cmd-norm        -1..+1, positive = nose-up command\n"
        "fcs/aileron-cmd-norm         -1..+1, positive = roll right\n"
        "fcs/rudder-cmd-norm          -1..+1, positive = yaw right\n"
        "fcs/throttle-cmd-norm[n]     0..1 per engine\n"
        "fcs/mixture-cmd-norm[n]      0..1 per piston engine\n"
        "gear/gear-cmd-norm           0 or 1\n"
        "fcs/flap-cmd-norm            0..1\n"
        "fcs/speedbrake-cmd-norm      0..1\n"
        "\n"
        "# Aero state\n"
        "aero/alpha-rad / alpha-deg\n"
        "aero/beta-rad  / beta-deg\n"
        "aero/qbar-psf\n"
        "velocities/vt-fps           true airspeed\n"
        "velocities/vc-kts           calibrated airspeed\n"
        "velocities/mach\n"
        "velocities/p-rad_sec        body-frame angular rates\n"
        "velocities/p-aero-rad_sec   aero-frame angular rates\n"
        "\n"
        "# Position and attitude\n"
        "position/lat-geod-deg, position/long-gc-deg\n"
        "position/h-sl-ft            altitude above MSL\n"
        "position/h-agl-ft           altitude above ground\n"
        "attitude/phi-rad, theta-rad, psi-rad\n"
        "\n"
        "# Forces and moments (body frame, lbf, ft-lbf)\n"
        "forces/fbx-aero, fby-aero, fbz-aero\n"
        "forces/fbx-prop, fby-prop, fbz-prop\n"
        "moments/l-aero, m-aero, n-aero\n"
        "moments/l-total, m-total, n-total")

    heading("Поширені компоненти FCS", 1, story)
    table_data = [
        ["Компонент", "Призначення"],
        ["summer", "Підсумовує входи з опціональним зсувом та обмеженням."],
        ["pure_gain", "y = k * x (k може бути властивістю)"],
        ["scheduled_gain", "k = table(independent_var); y = k * x"],
        ["aerosurface_scale",
            "Відображає нормований вхід на фізичний діапазон відхилення."],
        ["kinematic",
            "Дискретні положення з часами переходу — закрилки, шасі."],
        ["lag_filter", "Запізнення першого порядку: ẏ = (x − y) / τ"],
        ["lead_lag_filter", "Неперервний (a₀+a₁s)/(b₀+b₁s)"],
        ["washout_filter", "Верхньочастотний: τs/(τs+1)"],
        ["second_order_filter",
            "Режекторний/низькочастотний з 4 коефіцієнтами чисельника + 4 знаменника"],
        ["integrator", "y = ∫ x dt, з опціональним тригером скидання"],
        ["deadband", "Видає нуль у межах смуги навколо входу"],
        ["switch", "Умовна логіка з випадками test/default"],
        ["fcs_function",
            "Вбудовує довільний вираз-функцію як блок FCS"],
        ["pid", "PID(Kp,Ki,Kd) з тригером, опціональним clipto"],
        ["sensor", "Додає шум, зсув, дрейф, запізнення, затримку"],
        ["actuator",
            "Обмеження швидкості, запізнення, гістерезис, зона нечутливості, режими відмов"],
    ]
    t = Table(wrap_table(table_data), colWidths=[4.0 * cm, 12.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    heading("Перехресний довідник типів двигунів", 1, story)
    table_data = [
        ["Клас двигуна", "Кореневий тег XML", "Типовий рушій",
            "Ключові входи"],
        ["Поршневий",      "<piston_engine>", "<propeller>",
            "дросель, суміш, магнето"],
        ["Турбореактивний/Турбовентиляторний",
            "<turbine_engine>", "<direct> або <nozzle>",
            "дросель, форсаж вкл/викл"],
        ["Турбогвинтовий",   "<turboprop_engine>", "<propeller>",
            "дросель, крок гвинта"],
        ["Ракетний",      "<rocket_engine>",  "<nozzle>",
            "дросель (часто 0/1)"],
        ["Електричний пост. струму", "<electric_engine>", "<propeller>",
            "дросель (PWM)"],
        ["Безколекторний пост. струму", "<brushless_dc_motor>", "<propeller>",
            "дросель, обмеження струму"],
        ["Гвинт", "<rotor>", "(інтегрований)",
            "загальний крок, циклічний крок, дросель"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[3.6 * cm, 3.4 * cm, 3.0 * cm, 6.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
    ]))
    story.append(t)

    heading("Карта вихідного коду", 1, story)
    code(
        "src/FGFDMExec.cpp / .h           main executive, model orchestration\n"
        "src/initialization/FGInitialCondition.cpp\n"
        "                                 IC parsing and application\n"
        "src/initialization/FGTrim.cpp    trim algorithm\n"
        "src/input_output/FGPropertyManager.cpp\n"
        "                                 property tree bindings\n"
        "src/input_output/FGInputType*.cpp\n"
        "                                 telnet/socket/QtJSBSim input drivers\n"
        "src/input_output/FGOutputType*.cpp\n"
        "                                 CSV, FlightGear, socket output drivers\n"
        "src/math/FGFunction.cpp          function-language evaluator\n"
        "src/math/FGTable.cpp             N-D table interpolation\n"
        "src/math/FGPropertyValue.cpp     property-bound value node\n"
        "src/math/FGQuaternion.cpp        quaternion arithmetic\n"
        "src/math/FGMatrix33.cpp          3x3 matrix\n"
        "src/math/FGColumnVector3.cpp     3-vector\n"
        "src/models/FGPropagate.cpp       state integration\n"
        "src/models/FGAccelerations.cpp   Newton-Euler, ground LCP\n"
        "src/models/FGAerodynamics.cpp    aero force/moment assembly\n"
        "src/models/FGAuxiliary.cpp       alpha, beta, qbar, Mach\n"
        "src/models/FGAtmosphere.cpp      standard atmosphere\n"
        "src/models/atmosphere/FGWinds.cpp  winds, gusts, turbulence\n"
        "src/models/FGInertial.cpp        gravity, WGS-84, planet rotation\n"
        "src/models/FGMassBalance.cpp     mass/CG/inertia composition\n"
        "src/models/FGPropulsion.cpp      engine container\n"
        "src/models/propulsion/FGPiston.cpp        piston engine\n"
        "src/models/propulsion/FGTurbine.cpp       turbojet/turbofan\n"
        "src/models/propulsion/FGTurboProp.cpp     turboprop\n"
        "src/models/propulsion/FGRocket.cpp        rocket\n"
        "src/models/propulsion/FGElectric.cpp      electric\n"
        "src/models/propulsion/FGBrushLessDCMotor.cpp\n"
        "src/models/propulsion/FGPropeller.cpp     propeller\n"
        "src/models/propulsion/FGNozzle.cpp        rocket nozzle\n"
        "src/models/propulsion/FGRotor.cpp         helicopter rotor\n"
        "src/models/propulsion/FGTank.cpp          fuel tank\n"
        "src/models/FGGroundReactions.cpp ground reactions container\n"
        "src/models/FGLGear.cpp           landing gear / contact point\n"
        "src/models/flight_control/...    FCS components (summer, pid, ...)\n"
        "src/models/FGFCS.cpp             flight control system orchestrator")

    heading("Бібліографія та джерела", 1, story)
    for b in [
        "Berndt, J. S. <i>JSBSim Reference Manual</i> (онлайн та PDF). "
        "https://jsbsim.sourceforge.net/documentation.html",
        "Stevens B. L., Lewis F. L. <i>Aircraft Control and Simulation</i>, "
        "2nd ed., Wiley, 2003. — визначальне джерело щодо рівнянь руху, які "
        "реалізує JSBSim.",
        "Etkin B., Reid L. D. <i>Dynamics of Flight: Stability and "
        "Control</i>, 3rd ed., Wiley, 1996. — класичні визначення похідних "
        "стійкості.",
        "Roskam, J. <i>Airplane Design, Vols. I-VIII</i>, DARcorp. — "
        "інженерні оцінки інерції, шасі, геометрії органів керування.",
        "USAF DATCOM, <i>USAF Stability and Control DATCOM</i>, USAF "
        "AFFDL-TR-79-3032. — довідникові оцінки похідних стійкості та "
        "демпфування; корисна перевірка адекватності CFD.",
        "Cooke J., Zyda M., Pratt D., McGhee R. <i>NPSNET: Flight "
        "Simulation Dynamic Modeling Using Quaternions</i>, 1994.",
        "Buss S. <i>Accurate and Efficient Simulation of Rigid Body "
        "Rotations</i>, UCSD, 1999.",
        "Catto E. <i>Iterative Dynamics with Temporal Coherence</i>, "
        "Crystal Dynamics, 2005.",
        "U.S. Standard Atmosphere, 1976, NASA-TM-X-74335.",
        "NASA-NESC. <i>2015 Flight Simulation Check Cases</i>. "
        "https://nescacademy.nasa.gov/flightsim/2015",
        "MIL-F-8785C, <i>Military Specification, Flying Qualities of "
        "Piloted Airplanes</i>.",
        "MIL-HDBK-516B, <i>Department of Defense Handbook: Airworthiness "
        "Certification Criteria</i>.",
    ]:
        story.append(bullet(b))

    heading("Підсумкові міркування", 1, story)
    story.append(p(
        "Дизайн JSBSim винагороджує інженерів, які вже мислять у термінах "
        "похідних стійкості, систем відліку та рівнянь руху: прихованої магії "
        "тут дуже мало. Більшість того, що в XML здається механічним "
        "налаштуванням, насправді є прямим вираженням фізики — функція, що "
        "множить коефіцієнт на <i><font name='DejaVu'>q̄</font>·S·<font name='DejaVu'>c̄</font>·…</i>, "
        "є підручниковою формулою, а не домовленістю JSBSim. Наслідок "
        "полягає в тому, що коли щось іде не так, помилка майже завжди в "
        "даних, одиницях чи знаках — а не в симуляторі. Довіряйте "
        "фреймворку, інструментуйте його (дерево властивостей робить "
        "інструментування тривіальним) та ітеруйте."))
    story.append(quote(
        "Модель хибна, але симулятор має рацію. — фольклор"))

    add_chapter_diagrams(story)
    add_chapter_propulsion_deep(story)
    add_chapter_fcs_deep(story)
    add_chapter_atmosphere(story)
    add_chapter_quaternions(story)
    add_chapter_worked_example(story)
    add_chapter_scripts_ic(story)
    add_chapter_validation(story)
    add_chapter_troubleshooting(story)
    add_chapter_python_api(story)
    add_chapter_extended_properties(story)
    # ------------------------------------------------------------------
    # PART II — Extended theory: from first principles to the cutting edge.
    # Each chapter brings a self-contained, citation-rich treatment of the
    # mathematics, physics, aerodynamics, geodesy, propulsion, and JSBSim-
    # specific machinery that the earlier chapters depend on.
    # ------------------------------------------------------------------
    add_part_separator(story, "Частина II", "Розширена теорія та підґрунтя")
    add_ext_math_fundamentals(story)
    add_ext_quaternions_deep(story)
    add_ext_numerical_integration(story)
    add_ext_newton_euler(story)
    add_ext_fluid_mechanics(story)
    add_ext_lift_theory(story)
    add_ext_drag_breakdown(story)
    add_ext_stability_control(story)
    add_ext_eigenmodes(story)
    add_ext_airfoil_aerodynamics(story)
    add_ext_cfd_methods(story)
    add_ext_forced_oscillation(story)
    add_ext_geodesy_wgs84(story)
    add_ext_coord_transforms(story)
    add_ext_earth_gravity(story)
    add_ext_magnetic_navigation(story)
    add_ext_time_systems(story)
    add_ext_atmosphere_deep(story)
    add_ext_wind_turbulence(story)
    add_ext_propulsion_theory(story)
    add_ext_propeller_rotor(story)
    add_ext_signal_processing(story)
    add_ext_lcp_friction(story)
    add_ext_trim_algorithm(story)
    add_ext_nesc_check_cases(story)
    add_ext_property_tree_complete(story)
    add_ext_function_language_complete(story)
    add_ext_verification_validation(story)
    # ------------------------------------------------------------------
    # PART III — A complete, reproducible workflow for generating an
    # aircraft's aerodynamic dataset with OpenFOAM and importing it into
    # a JSBSim model: meshing, static coefficients, dynamic derivatives,
    # the XML mapping, automation, and verification.
    # ------------------------------------------------------------------
    add_part_iii_separator(story)
    add_of_pipeline_overview(story)
    add_of_geometry_meshing(story)
    add_of_static_coeffs(story)
    add_of_dynamic_derivatives(story)
    add_of_xml_mapping(story)
    add_of_automation(story)
    add_of_verification(story)
    # ------------------------------------------------------------------
    # PART IV — The practitioner's half: where aerodynamic data comes
    # from and how to blend it, how every subsystem (mass, propulsion,
    # gear, FCS, autopilot, sensors) is built and tuned, how stall/spin
    # are captured, how to script tests, and how to match performance
    # and handling qualities. Distilled from the source, the reference
    # manual, the FlightGear wiki and the developer forums.
    # ------------------------------------------------------------------
    add_part_iv_separator(story)
    add_fdm_data_sources(story)
    add_fdm_aeromatic(story)
    add_fdm_mass_balance(story)
    add_fdm_propulsion_practice(story)
    add_fdm_propellers(story)
    add_fdm_gear(story)
    add_fdm_fcs(story)
    add_fdm_autopilot(story)
    add_fdm_sensors_systems(story)
    add_fdm_high_alpha(story)
    add_fdm_scripting(story)
    add_fdm_performance_hq(story)
    add_fdm_integration(story)
    add_fdm_checklist(story)
    add_ext_further_reading(story)
    add_chapter_glossary(story)

    return story


# ============================================================================
# Extended chapters
# ============================================================================


def add_chapter_diagrams(story):
    story.append(PageBreak())
    heading("Візуальні діаграми циклу FDM", 0, story)
    story.append(p(
        "JSBSim не має вбудованої графічної документації. ASCII-"
        "діаграми в цьому розділі реконструйовано з вихідного коду й "
        "вони достовірно відображають потік даних станом на v2.0."))

    heading("Цикл симуляції верхнього рівня", 1, story)
    code(
        "  +----------------------------+\n"
        "  |       FGFDMExec::Run()     |  <-- called every tick (default 1/120 s)\n"
        "  +--------------+-------------+\n"
        "                 |\n"
        "                 v\n"
        "       +---------+---------+\n"
        "       | Child FDMs (if any)|     handle gear-detached subvehicles\n"
        "       +---------+---------+\n"
        "                 |\n"
        "                 v\n"
        "    +--------------------------+\n"
        "    | sim_time += dt; Frame++  |\n"
        "    +-------------+------------+\n"
        "                  |\n"
        "                  v\n"
        "    +--------------------------+\n"
        "    | Script::RunScript()      |  (events, set-property, conditionals)\n"
        "    +-------------+------------+\n"
        "                  |\n"
        "                  v\n"
        "    +============== Model loop ====================+\n"
        "    | for i in eModels:                            |\n"
        "    |     LoadInputs(i)        // wire properties  |\n"
        "    |     Models[i]->Run()     // evaluate model   |\n"
        "    +==============================================+\n"
        "                  |\n"
        "                  v\n"
        "       (outputs flushed by FGOutput at end of tick)\n"
        "\n"
        "                              propagated state ----.\n"
        "                                                   |\n"
        "                                                   v\n"
        " next tick: Propagate uses Accelerations' result from this tick\n")

    heading("Потік даних між моделями за один такт", 1, story)
    code(
        "  Propagate   --> (x, v, q)                                     ---+\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  Inertial   --> g, Omega_planet                                  |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  Atmosphere --> T, p, rho, a                                     |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  Winds      --> Vw_local, Tw2b                                   |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  Systems(FCS) --> delta_e, delta_a, delta_r, throttle, etc.      |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  MassBalance --> m, J, r_cg                                      |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  Auxiliary  --> alpha, beta, qbar, Vt, Mach, n_load              |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  Propulsion --> F_thrust, M_thrust                               |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  Aerodynamics --> F_aero, M_aero                                 |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  GroundReactions --> F_gear, M_gear (LCP)                        |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  ExternalReactions / BuoyantForces --> F_ext, M_ext              |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  Aircraft   --> F_total, M_total                                 |\n"
        "      |                                                           |\n"
        "      v                                                           |\n"
        "  Accelerations --> v_dot, omega_dot   --(next tick)-------------+\n"
        "      |\n"
        "      v\n"
        "  Output     --> CSV/socket/FlightGear\n")

    heading("Схема зв’язаної, вітрової та конструктивної систем координат", 1, story)
    code(
        "         WIND/STABILITY frame                BODY frame\n"
        "         (rotated from body by                (X-fwd, Y-right,\n"
        "          alpha and beta)                       Z-down)\n"
        "                                                                \n"
        "                          ^ Z_body (down)                       \n"
        "                          |                                      \n"
        "                          |                                      \n"
        "       relative           |                                      \n"
        "         wind            X_body                                  \n"
        "          --->     +-----+-----+---> X_body (forward)            \n"
        "                  /              \\                              \n"
        "                 / aircraft       \\                             \n"
        "                /                  \\                            \n"
        "               +----------+---------+                            \n"
        "                          |                                      \n"
        "                          v Y_body (out the right wing)          \n"
        "\n"
        "  alpha = angle between V_rel and the body X axis in the X-Z plane\n"
        "  beta  = angle between V_rel and the body X-Z plane             \n"
        "\n"
        "  STRUCTURAL frame (used in <location> elements of the XML):\n"
        "      X_struct = aft (typically),\n"
        "      Y_struct = right,\n"
        "      Z_struct = up.\n"
        "  JSBSim flips X and Z internally when converting to body frame.\n")

    heading("Потік від аеродинамічних осей до сил", 1, story)
    code(
        "  +---------------+         +----------------+\n"
        "  | aerodynamics  |         |  metrics S,b,c |\n"
        "  | functions     |         +-------+--------+\n"
        "  | <axis name=\"\">|                 |\n"
        "  +-------+-------+                 v\n"
        "          |                  +---------------+\n"
        "          v                  | qbar from Aux |\n"
        "  6 axis slots:              +-------+-------+\n"
        "    DRAG  SIDE  LIFT                 |\n"
        "    ROLL  PITCH YAW                  |\n"
        "          |                         |  embedded in each function's\n"
        "          v                         |  <product> ... </product>\n"
        "  +---------------+                 |\n"
        "  | sum functions |<----------------+\n"
        "  +-------+-------+\n"
        "          |\n"
        "          v\n"
        "  +---------------+\n"
        "  | rotate W->B   |  using Tw2b from Auxiliary\n"
        "  +-------+-------+\n"
        "          |\n"
        "          v\n"
        "  +---------------------+\n"
        "  | accumulate moments  |\n"
        "  | at AERORP, then     |\n"
        "  | shift to CG via r x F|\n"
        "  +-------+-------------+\n"
        "          |\n"
        "          v\n"
        "  F_aero_body, M_aero_cg --> FGAircraft\n")


def add_chapter_propulsion_deep(story):
    story.append(PageBreak())
    heading("Силова установка — довідник за типами двигунів", 0, story)

    heading("Поршневі двигуни", 1, story)
    story.append(p(
        "<font face='Courier'>FGPiston</font> моделює чотиритактний "
        "поршневий двигун (piston engine) з динамікою абсолютного тиску у "
        "впускному колекторі, керуванням сумішшю та дроселем, відмовами "
        "магнето й зниженням потужності з висотою. Параметри конфігурації:"))
    code(
        "<piston_engine name=\"NewEngine\">\n"
        "    <minmp     unit=\"INHG\">  10.0 </minmp>      <!-- idle MAP -->\n"
        "    <maxmp     unit=\"INHG\">  28.5 </maxmp>      <!-- max MAP (SL) -->\n"
        "    <displacement unit=\"IN3\"> 320 </displacement>\n"
        "    <maxhp>                   160 </maxhp>       <!-- SL max power -->\n"
        "    <bsfc>                    0.45 </bsfc>       <!-- brake-spec fuel csmp -->\n"
        "    <cycles>                  4    </cycles>     <!-- 4 or 2-stroke -->\n"
        "    <idlerpm>                 600  </idlerpm>\n"
        "    <maxrpm>                 2700  </maxrpm>\n"
        "    <maxthrottle>             1.0  </maxthrottle>\n"
        "    <minthrottle>             0.05 </minthrottle>\n"
        "    <sparkfaildrop>           0.1  </sparkfaildrop>\n"
        "    <numboostspeeds>          1    </numboostspeeds>\n"
        "    <boostoverride>           0    </boostoverride>\n"
        "    <ratedpower>            160    </ratedpower>\n"
        "    <ratedrpm>              2700   </ratedrpm>\n"
        "    <ratedaltitude unit=\"FT\"> 0  </ratedaltitude>\n"
        "</piston_engine>")
    story.append(p(
        "Вихідна потужність моделюється як параболічна залежність від MAP "
        "і лінійне масштабування за дроселем/RPM. Суміш впливає на висоту "
        "за щільністю — збіднення відносно піка зменшує потужність, "
        "збагачення відносно піка збільшує витрату палива. Модель враховує "
        "відновлення тиску набігаючого потоку на високих швидкостях."))

    heading("Турбіна (турбореактивний/турбовентиляторний двигун)", 1, story)
    story.append(p(
        "<font face='Courier'>FGTurbine</font> реалізує двовальний "
        "двигун із режимами малого газу/максимальної безфорсажної тяги/"
        "форсажу та тягою за таблицями пошуку:"))
    code(
        "<turbine_engine name=\"F100\">\n"
        "    <milthrust unit=\"LBS\">    17800 </milthrust>\n"
        "    <maxthrust unit=\"LBS\">    29100 </maxthrust>  <!-- AB rating -->\n"
        "    <bypassratio>             0.35  </bypassratio>\n"
        "    <tsfc>                    0.74  </tsfc>        <!-- cruise SFC -->\n"
        "    <atsfc>                   2.05  </atsfc>       <!-- AB SFC -->\n"
        "    <bleed>                   0.03  </bleed>\n"
        "    <idlen1>                  30.0  </idlen1>\n"
        "    <idlen2>                  60.0  </idlen2>\n"
        "    <maxn1>                  100.0  </maxn1>\n"
        "    <maxn2>                  100.0  </maxn2>\n"
        "    <augmented>               1     </augmented>   <!-- has AB -->\n"
        "    <augmethod>               1     </augmethod>\n"
        "    <injected>                0     </injected>\n"
        "\n"
        "    <function name=\"IdleThrust\">\n"
        "        <table>\n"
        "            <independentVar lookup=\"row\">velocities/mach</independentVar>\n"
        "            <independentVar lookup=\"column\">atmosphere/density-altitude</independentVar>\n"
        "            <tableData>\n"
        "                          0        20000     40000     60000\n"
        "                 0.0      0.0430   0.0488    0.0533    0.0593\n"
        "                 0.4      0.0356   0.0418    0.0466    0.0524\n"
        "                 0.8      0.0235   0.0312    0.0376    0.0445\n"
        "                 1.2      0.0070   0.0185    0.0272    0.0364\n"
        "                 1.6     -0.0094   0.0040    0.0156    0.0276\n"
        "            </tableData>\n"
        "        </table>\n"
        "    </function>\n"
        "\n"
        "    <function name=\"MilThrust\">\n"
        "        <table>...</table>      <!-- normalised thrust 0..1 -->\n"
        "    </function>\n"
        "\n"
        "    <function name=\"AugThrust\">\n"
        "        <table>...</table>      <!-- AB normalised thrust -->\n"
        "    </function>\n"
        "</turbine_engine>")
    story.append(p(
        "Кожна таблиця тяги нормована на 1.0 для статичних умов на рівні "
        "моря (SL); модель множить її на відповідне номінальне значення "
        "(milthrust або maxthrust). Розкрутка моделюється запізненнями "
        "першого порядку; властивість "
        "<font face='Courier'>propulsion/engine[n]/n2-norm</font> можна "
        "подати до FCS, щоб керувати випуском закрилків або логікою "
        "реверсора тяги."))

    heading("Турбогвинтовий двигун", 1, story)
    story.append(p(
        "<font face='Courier'>FGTurboProp</font> поєднує турбінне ядро з "
        "повітряним гвинтом. XML додає "
        "<font face='Courier'>maxpower</font> у потужності на валу (к. с.) "
        "та <font face='Courier'>betarangeend</font>:"))
    code(
        "<turboprop_engine name=\"PW100\">\n"
        "    <milthrust unit=\"LBS\"> 0 </milthrust>\n"
        "    <maxpower unit=\"HP\">  1200 </maxpower>\n"
        "    <idlen1>  50 </idlen1>\n"
        "    <maxn1>  100 </maxn1>\n"
        "    <betarangeend> 0.20 </betarangeend>  <!-- pitch override below this -->\n"
        "    <reversemaxpower> 0.50 </reversemaxpower>\n"
        "    <function name=\"EnginePowerVC\">\n"
        "        <table>...</table>\n"
        "    </function>\n"
        "    <function name=\"EnginePowerAltitude\">\n"
        "        <table>...</table>\n"
        "    </function>\n"
        "</turboprop_engine>")
    story.append(p(
        "Рушій має бути <font face='Courier'>&lt;propeller&gt;"
        "</font> (окремий файл XML), а крок гвинта керується або "
        "регулятором (постійних обертів), або безпосередньо командами "
        "FCS."))

    heading("Ракетні двигуни", 1, story)
    story.append(p(
        "<font face='Courier'>FGRocket</font> моделює ракету з "
        "фіксованим Isp. Змінна тяга підтримується через дросель і "
        "таблицю «тяга-час»; векторування тяги підтримується через "
        "<font face='Courier'>&lt;nozzle&gt;</font> з керованими кутами "
        "PYR. Придатний для прискорювачів, метеорологічних ракет і "
        "моделей ракет."))
    code(
        "<rocket_engine name=\"SolidBooster\">\n"
        "    <isp>      265.0 </isp>             <!-- specific impulse, sec -->\n"
        "    <builduptime> 0.2 </builduptime>     <!-- ignition transient -->\n"
        "    <thrust_table>\n"
        "        <table>                          <!-- F vs t in sec -->\n"
        "            <independentVar>propulsion/engine[0]/thrust-time</independentVar>\n"
        "            <tableData>\n"
        "                0.0   1500\n"
        "                0.5   3200\n"
        "                3.0   3200\n"
        "                4.0   1000\n"
        "                4.5      0\n"
        "            </tableData>\n"
        "        </table>\n"
        "    </thrust_table>\n"
        "</rocket_engine>")

    heading("Електричні та безколекторні двигуни постійного струму", 1, story)
    code(
        "<electric_engine name=\"E305\">\n"
        "    <power unit=\"WATTS\"> 1000 </power>   <!-- max shaft power -->\n"
        "</electric_engine>\n"
        "\n"
        "<brushless_dc_motor name=\"OutrunnerBLDC\">\n"
        "    <maxvolts>     22.2  </maxvolts>     <!-- 6S LiPo -->\n"
        "    <velocityconstant> 920 </velocityconstant>   <!-- Kv, rpm/V -->\n"
        "    <coilresistance>   0.02 </coilresistance>    <!-- ohms -->\n"
        "    <noloadcurrent>   1.0 </noloadcurrent>       <!-- A -->\n"
        "</brushless_dc_motor>")
    story.append(p(
        "Обидві моделі обчислюють момент на валу з дроселя (PWM) та "
        "кривої проти-ЕРС. <font face='Courier'>FGBrushLessDCMotor</font> "
        "явно відстежує споживаний струм, що корисно для "
        "моделювання ресурсу акумулятора — помножте струм на напругу на "
        "клемах, щоб отримати миттєву потужність, а потім інтегруйте її "
        "відносно ємності бака, щоб змоделювати рівень заряду "
        "акумулятора."))

    heading("Несучий гвинт вертольота", 1, story)
    story.append(p(
        "<font face='Courier'>FGRotor</font> моделює несучий або "
        "хвостовий гвинт вертольота за допомогою аналітичного підходу "
        "елемента лопаті з моделюванням індуктивного потоку, динаміки "
        "махових рухів і впливу екрана. Він складний — для першого "
        "наближення починайте з прикладів J3Cub piston або X15 у "
        "<font face='Courier'>aircraft/</font>, а не з нуля."))

    heading("Повітряні гвинти", 1, story)
    story.append(p(
        "Повітряні гвинти розміщуються в <font face='Courier'>engine/prop_*.xml"
        "</font> і посилаються на таблиці C<sub>T</sub> та C<sub>P</sub> "
        "залежно від відносної ходи J:"))
    code(
        "<propeller name=\"prop_75in2f\">\n"
        "    <ixx>         1.67 </ixx>\n"
        "    <diameter unit=\"IN\"> 75.0 </diameter>\n"
        "    <numblades>      2 </numblades>\n"
        "    <gearratio>    1.0 </gearratio>\n"
        "    <cp_factor>    1.0 </cp_factor>\n"
        "    <ct_factor>    1.0 </ct_factor>\n"
        "    <minpitch>    10.0 </minpitch>   <!-- variable-pitch range -->\n"
        "    <maxpitch>    35.0 </maxpitch>\n"
        "    <minrpm>      640  </minrpm>     <!-- governor range -->\n"
        "    <maxrpm>     2700  </maxrpm>\n"
        "    <constspeed>   1   </constspeed> <!-- 1 = constant-speed prop -->\n"
        "    <table name=\"C_THRUST\" type=\"internal\">\n"
        "        <tableData>\n"
        "             0.00  0.0863\n"
        "             0.10  0.0837\n"
        "             0.20  0.0792\n"
        "             0.30  0.0727\n"
        "             0.40  0.0643\n"
        "             0.50  0.0540\n"
        "        </tableData>\n"
        "    </table>\n"
        "    <table name=\"C_POWER\" type=\"internal\">\n"
        "        <tableData> ... </tableData>\n"
        "    </table>\n"
        "</propeller>")
    story.append(p(
        "Використовуйте <font face='Courier'>p_factor</font> на рушії, "
        "щоб змоделювати незначний момент рискання вліво від "
        "асиметрії диска гвинта на великих α. <font face='Courier'>sense"
        "</font> дорівнює +1 для обертання за годинниковою стрілкою (якщо "
        "дивитися з кабіни) і −1 — проти годинникової стрілки; це важливо "
        "для напрямку реактивного моменту та ефектів «критичного "
        "двигуна» на двомоторних літаках."))

    heading("Паливні баки", 1, story)
    code(
        "<tank type=\"FUEL\" number=\"0\" name=\"LeftWingTank\">\n"
        "    <location unit=\"IN\">  <x>56</x><y>-112</y><z>59.4</z> </location>\n"
        "    <drain_location unit=\"IN\">\n"
        "        <x>56</x><y>-112</y><z>50</z>           <!-- pickup point -->\n"
        "    </drain_location>\n"
        "    <type>AVGAS</type>                          <!-- or JET-A, RP-1, ... -->\n"
        "    <capacity unit=\"LBS\"> 185 </capacity>\n"
        "    <contents unit=\"LBS\"> 100 </contents>      <!-- initial fuel -->\n"
        "    <density unit=\"LBS/GAL\"> 6.0 </density>\n"
        "    <temperature> 50 </temperature>             <!-- degF -->\n"
        "    <standpipe unit=\"LBS\"> 5 </standpipe>      <!-- unusable bottom -->\n"
        "    <unusable-volume unit=\"GAL\"> 0.5 </unusable-volume>\n"
        "    <priority> 1 </priority>                    <!-- 1 = consume first -->\n"
        "</tank>")
    story.append(p(
        "Баки додають масу та інерцію (перенесену за теоремою про "
        "паралельні осі з розташування бака до CG), які зменшуються в "
        "міру споживання палива. Кілька баків із різними пріоритетами "
        "дають змогу змоделювати реальний розклад роботи паливної "
        "системи (наприклад, «спочатку перекачувати з допоміжного бака до "
        "основного»)."))


def add_chapter_fcs_deep(story):
    story.append(PageBreak())
    heading("Компоненти системи керування польотом — довідник", 0, story)
    story.append(p(
        "Кожен компонент FCS має однакову структуру: ім’я, одну або "
        "кілька властивостей <font face='Courier'>&lt;input&gt;</font>, "
        "специфічну для компонента конфігурацію, необов’язковий "
        "<font face='Courier'>&lt;clipto&gt;</font> та властивість "
        "<font face='Courier'>&lt;output&gt;</font>, яку можуть читати "
        "інші компоненти, розташовані нижче за потоком. Вихід "
        "обчислюється в тому <i>порядку</i>, у якому компоненти йдуть у "
        "каналі."))

    heading("Суматор / Чистий коефіцієнт підсилення / Масштабування аероповерхні", 1, story)
    code(
        "<summer name=\"trim_sum\">                <!-- y = sum(inputs) + bias -->\n"
        "    <input>fcs/elevator-cmd-norm</input>\n"
        "    <input>fcs/pitch-trim-cmd-norm</input>\n"
        "    <bias>0.0</bias>\n"
        "    <clipto> <min>-1</min><max>1</max> </clipto>\n"
        "</summer>\n"
        "\n"
        "<pure_gain name=\"elev_gain\">             <!-- y = k * x -->\n"
        "    <input>fcs/trim_sum</input>\n"
        "    <gain>2.5</gain>                      <!-- can be a property -->\n"
        "</pure_gain>\n"
        "\n"
        "<scheduled_gain name=\"yaw_damper_gain\">  <!-- k = table(prop) -->\n"
        "    <input>velocities/r-aero-rad_sec</input>\n"
        "    <table>\n"
        "        <independentVar>velocities/mach</independentVar>\n"
        "        <tableData>\n"
        "            0.0   0.0\n"
        "            0.3   1.0\n"
        "            0.9   1.2\n"
        "        </tableData>\n"
        "    </table>\n"
        "    <output>fcs/yaw-damper-cmd</output>\n"
        "</scheduled_gain>\n"
        "\n"
        "<aerosurface_scale name=\"elev_to_rad\">\n"
        "    <input>fcs/trim_sum</input>\n"
        "    <gain>0.01745</gain>          <!-- multiply input first -->\n"
        "    <domain> <min>-1</min><max>1</max> </domain>      <!-- input range -->\n"
        "    <range>  <min>-28</min><max>23</max> </range>     <!-- output range -->\n"
        "    <output>fcs/elevator-pos-rad</output>\n"
        "</aerosurface_scale>")

    heading("Фільтри", 1, story)
    story.append(p(
        "Фільтри використовують дискретизацію за Тастіном (білінійну). "
        "Кожен має характеристичну сталу <font face='Courier'>c1..c5"
        "</font>, яка відповідає підручниковим коефіцієнтам."))
    code(
        "<lag_filter name=\"y\">                    <!-- H = c1/(s+c1) -->\n"
        "    <input>fcs/x</input>\n"
        "    <c1>500</c1>                          <!-- time constant 1/500 s -->\n"
        "</lag_filter>\n"
        "\n"
        "<lead_lag_filter name=\"y\">               <!-- H = (c1 s + c2)/(c3 s + c4) -->\n"
        "    <input>fcs/x</input>\n"
        "    <c1>0.5</c1> <c2>1</c2> <c3>0.05</c3> <c4>1</c4>\n"
        "</lead_lag_filter>\n"
        "\n"
        "<washout_filter name=\"y\">                <!-- H = s/(s+c1) -->\n"
        "    <input>velocities/q-rad_sec</input>\n"
        "    <c1>1.0</c1>\n"
        "</washout_filter>\n"
        "\n"
        "<second_order_filter name=\"y\">           <!-- H = (c1 s2 + c2 s + c3)/(c4 s2 + c5 s + c6) -->\n"
        "    <input>fcs/x</input>\n"
        "    <c1>0</c1><c2>0</c2><c3>4</c3>\n"
        "    <c4>1</c4><c5>2.0</c5><c6>4</c6>      <!-- 2 Hz, zeta=0.5 -->\n"
        "</second_order_filter>")

    heading("Інтегратор", 1, story)
    code(
        "<integrator name=\"alpha_int\">\n"
        "    <input>aero/alpha-rad</input>\n"
        "    <c1>1.0</c1>                              <!-- integration gain -->\n"
        "    <trigger>fcs/integrator-trigger</trigger> <!-- 0=run, 1=hold, -1=reset -->\n"
        "</integrator>")
    story.append(p(
        "Властивість trigger дає змогу реалізувати захист від "
        "інтегрального насичення звичайною логікою: утримувати під час "
        "насичення, скидати при вимкненні."))

    heading("ПІД-регулятор", 1, story)
    code(
        "<pid name=\"AltitudeHold\">\n"
        "    <input>fcs/altitude-error-ft</input>\n"
        "    <kp>0.05</kp>\n"
        "    <ki type=\"ab3\">0.001</ki>            <!-- ab2/ab3 = Adams-Bashforth -->\n"
        "    <kd>0.10</kd>\n"
        "    <trigger>ap/altitude-hold-engaged</trigger>\n"
        "    <clipto> <min>-0.5</min><max>0.5</max> </clipto>\n"
        "</pid>")

    heading("Кінематичний компонент, зона нечутливості, перемикач", 1, story)
    code(
        "<kinematic name=\"flaps\">                  <!-- discrete positions w/ traverse times -->\n"
        "    <input>fcs/flap-cmd-norm</input>\n"
        "    <traverse>\n"
        "        <setting><position> 0</position><time>0</time></setting>\n"
        "        <setting><position>10</position><time>2</time></setting>\n"
        "        <setting><position>30</position><time>4</time></setting>\n"
        "    </traverse>\n"
        "    <output>fcs/flap-pos-deg</output>\n"
        "</kinematic>\n"
        "\n"
        "<deadband name=\"stick_db\">                <!-- zero out small inputs -->\n"
        "    <input>fcs/elevator-cmd-norm</input>\n"
        "    <width>0.02</width>\n"
        "</deadband>\n"
        "\n"
        "<switch name=\"gear_switch\">               <!-- conditional output -->\n"
        "    <default value=\"0\"/>\n"
        "    <test logic=\"AND\" value=\"1\">\n"
        "        gear/gear-cmd-norm ge 0.5\n"
        "        velocities/vc-kts le 250\n"
        "    </test>\n"
        "    <output>fcs/gear-extend</output>\n"
        "</switch>")

    heading("Огортання датчика та привода", 1, story)
    story.append(p(
        "Використовуйте <font face='Courier'>&lt;sensor&gt;</font> для "
        "імітації недосконалих вимірювань (запізнення, зміщення, шум) і "
        "<font face='Courier'>&lt;actuator&gt;</font> для імітації "
        "недосконалого приведення поверхні (обмеження швидкості, "
        "гістерезис, зона нечутливості, режими відмов). Обидва корисні "
        "для досліджень із внесенням несправностей."))
    code(
        "<sensor name=\"ias_sensor\">\n"
        "    <input>velocities/vc-kts</input>\n"
        "    <lag>0.5</lag>                <!-- first-order lag tau -->\n"
        "    <bias>2</bias>                <!-- additive offset -->\n"
        "    <drift_rate>0.01</drift_rate> <!-- units/sec -->\n"
        "    <gain>1.005</gain>\n"
        "    <noise variation=\"PERCENT\">0.5</noise>\n"
        "    <quantization name=\"adc12bit\">\n"
        "        <bits>12</bits><min>0</min><max>500</max>\n"
        "    </quantization>\n"
        "    <delay>0.1</delay>            <!-- pure time delay -->\n"
        "    <output>instr/ias-indicated</output>\n"
        "</sensor>\n"
        "\n"
        "<actuator name=\"elev_act\">\n"
        "    <input>fcs/elevator-cmd-rad</input>\n"
        "    <lag>0.05</lag>\n"
        "    <rate_limit sense=\"incr\">0.6</rate_limit>\n"
        "    <rate_limit sense=\"decr\">0.6</rate_limit>\n"
        "    <bias>0</bias>\n"
        "    <deadband_width>0.0017</deadband_width>\n"
        "    <hysteresis_width>0.0035</hysteresis_width>\n"
        "    <fail_zero> fcs/elev-act-fail-zero </fail_zero>\n"
        "    <fail_hardover> fcs/elev-act-fail-hard </fail_hardover>\n"
        "    <fail_stuck> fcs/elev-act-fail-stuck </fail_stuck>\n"
        "    <output>fcs/elevator-pos-rad</output>\n"
        "</actuator>")


def add_chapter_atmosphere(story):
    story.append(PageBreak())
    heading("Атмосфера, вітри та Земля", 0, story)

    heading("Стандартна атмосфера ISA 1976", 1, story)
    story.append(p(
        "<font face='Courier'>FGStandardAtmosphere</font> обчислює "
        "US Standard Atmosphere 1976 — вісім кусково-сталих сегментів "
        "градієнта температури від рівня моря до геометричної висоти "
        "86 км. Модель надає:"))
    code(
        "atmosphere/T-R              static temperature, Rankine\n"
        "atmosphere/T-sl-R           sea-level reference temperature\n"
        "atmosphere/T-dev-R          local deviation from standard\n"
        "atmosphere/P-psf            static pressure, lb/ft^2\n"
        "atmosphere/P-sl-psf\n"
        "atmosphere/rho-slugs_ft3    density\n"
        "atmosphere/a-fps            speed of sound\n"
        "atmosphere/density-altitude\n"
        "atmosphere/pressure-altitude")
    story.append(p(
        "<b>Власна атмосфера.</b> Успадкуйте від "
        "<font face='Courier'>FGAtmosphere</font> у C++ і перевизначте "
        "<font face='Courier'>Calculate(double altitudeASL)</font>. Для "
        "більшості потреб достатньо стандартної моделі плюс зсуву "
        "температури (<font face='Courier'>atmosphere/delta-T</font>) — "
        "зсув T за сталого P дає зсув висоти за щільністю, у такий спосіб "
        "зазвичай моделюють ефекти висоти за щільністю (спекотно й "
        "високо)."))

    heading("Вітри та зсув вітру", 1, story)
    code(
        "atmosphere/wind-north-fps          steady wind from FGWinds\n"
        "atmosphere/wind-east-fps           (NED frame, points TO direction wind blows toward)\n"
        "atmosphere/wind-down-fps\n"
        "atmosphere/wind-mag-fps            magnitude\n"
        "atmosphere/psiw-rad                wind heading\n"
        "atmosphere/total-wind-north-fps    steady + turbulence + gust + shear\n"
        "atmosphere/turb-rate-rad_sec       Dryden/Karman turbulence angular component")
    story.append(p(
        "<b>Моделі турбулентності</b>: вибираються через "
        "<font face='Courier'>atmosphere/turb-type</font>:"))
    code(
        "0 ttNone            no turbulence\n"
        "1 ttStandard        legacy white-noise model\n"
        "2 ttCulp            John Culp's model (used in FlightGear)\n"
        "3 ttMilspec         MIL-F-8785C Dryden\n"
        "4 ttTustin          MIL-F-8785C Tustin discrete-Dryden")
    story.append(p(
        "Для моделей за MIL-spec ви задаєте "
        "<font face='Courier'>atmosphere/turbulence/milspec/severity"
        "</font> за шкалою 0-7; модель автоматично добирає масштабні "
        "довжини та інтенсивності відповідно до специфікації."))

    heading("Пориви (дискретні)", 1, story)
    story.append(p(
        "Дискретний порив «1-cosine» можна ввімкнути, задавши:"))
    code(
        "atmosphere/cosine-gust-start  -> set to 1 to start\n"
        "atmosphere/cosine-gust-frame  -> 1 BODY, 2 WIND, 3 LOCAL\n"
        "atmosphere/cosine-gust-duration\n"
        "atmosphere/cosine-gust-magnitude-ft_sec\n"
        "atmosphere/cosine-gust-startup-duration\n"
        "atmosphere/cosine-gust-steady-duration\n"
        "atmosphere/cosine-gust-end-duration\n"
        "atmosphere/cosine-gust-X-velocity   (and Y, Z in chosen frame)")

    heading("Мікропорив", 1, story)
    story.append(p(
        "Тривимірна модель мікропориву (Vicroy + Mulgund) доступна через "
        "<font face='Courier'>atmosphere/turbulence-cosine-set</font>. "
        "Використовується для тренувальних сценаріїв повторного заходу на "
        "посадку та виходу зі зсуву вітру."))

    heading("Інерціальна модель: гравітація та обертання Землі", 1, story)
    story.append(p(
        "<font face='Courier'>FGInertial</font> публікує вектор "
        "гравітації та швидкість обертання планети. Доступні дві моделі "
        "гравітації, вибираються через "
        "<font face='Courier'>simulation/gravity-model</font>:"))
    code(
        "0  Spherical inverse-square gravity (uniform mass distribution)\n"
        "1  WGS-84 ellipsoid with J2 term (default)\n"
        "\n"
        "simulation/gravitational-torque  -> 0/1 (default 0)\n"
        "    Adds tidal torque on extended bodies; relevant for spacecraft.\n"
        "\n"
        "Planet rotation: 7.2921151467e-5 rad/s about ECI Z (sidereal day).\n"
        "\n"
        "WGS-84 ellipsoid:\n"
        "    semi-major axis a   = 6378137.0 m\n"
        "    semi-minor axis b   = 6356752.3142 m\n"
        "    flattening f        = 1/298.257223563\n"
        "    GM                  = 3.986004418e14 m^3/s^2\n"
        "    J2                  = 1.08263e-3")
    story.append(p(
        "<b>Чому це важливо навіть для польоту на малих висотах.</b> "
        "Прискорення Коріоліса на крейсерському режимі при Mach 0.8 має "
        "порядок 0.003 m/s² — мале, але ненульове. JSBSim коректно його "
        "враховує, що частково пояснює, чому він проходить контрольні "
        "приклади NASA 2015. Якщо порівнювати із симуляторами, що "
        "використовують наближення плоскої Землі, очікуйте невеликих "
        "усталених відхилень курсу під час тривалих польотів у напрямку "
        "схід-захід."))


def add_chapter_quaternions(story):
    story.append(PageBreak())
    heading("Орієнтація через кватерніони — вступ до коду", 0, story)
    story.append(p(
        "Читати <font face='Courier'>FGPropagate</font> і "
        "<font face='Courier'>FGQuaternion</font> значно простіше, якщо "
        "ви вже володієте кватерніонами. Цей розділ — стислий повторний "
        "огляд із позначеннями, специфічними для JSBSim."))

    heading("Означення та домовленості", 1, story)
    story.append(p(
        "Одиничний кватерніон — це четвірка <i>q = (q<sub>0</sub>, q<sub>1</sub>"
        ", q<sub>2</sub>, q<sub>3</sub>)</i> з нормою 1. JSBSim "
        "дотримується домовленості Гамільтона (i² = j² = k² = ijk = −1); "
        "<font face='Courier'>FGQuaternion</font> зберігає їх у "
        "порядку (w, x, y, z) — тобто скалярна компонента йде першою."))
    math("q &nbsp;=&nbsp; cos(θ/2) &nbsp;+&nbsp; <b><font name='DejaVu'>n̂</font></b> · sin(θ/2)")
    story.append(p(
        "де <b><font name='DejaVu'>n̂</font></b> — вісь обертання, а θ — кут обертання. "
        "Кватерніон, який обертає вектор з інерціальної системи координат "
        "у зв’язану, — це <i>q<sub>i→b</sub></i>, а еквівалентне "
        "пасивне обертання має вигляд"))
    math("v<sub>body</sub> &nbsp;=&nbsp; q* · v<sub>inertial</sub> · q")
    story.append(p(
        "(де вектори піднято до чистих кватерніонів, а · позначає добуток "
        "Гамільтона). Саме це й попередньо обчислює "
        "<font face='Courier'>FGQuaternion::GetTransformationMatrix()"
        "</font> як матрицю обертання 3×3 для швидких перетворень між "
        "системами координат."))

    heading("Кінематичне рівняння", 1, story)
    math("<font name='DejaVu'>q̇</font> &nbsp;=&nbsp; ½ · q · ω<sub>b/i</sub>")
    story.append(p(
        "Тут <i>ω<sub>b/i</sub></i> — інерціальна кутова швидкість, "
        "виражена як чистий кватерніон <i>(0, p<sub>i</sub>, q<sub>i</sub>"
        ", r<sub>i</sub>)</i>. <font face='Courier'>FGQuaternion::GetQDot()"
        "</font> реалізує це за 12 операцій із рухомою комою."))
    code(
        "FGQuaternion FGQuaternion::GetQDot(const FGColumnVector3& PQR) const {\n"
        "    return FGQuaternion(\n"
        "        -0.5*( data[1]*PQR(eP) + data[2]*PQR(eQ) + data[3]*PQR(eR)),\n"
        "         0.5*( data[0]*PQR(eP) - data[3]*PQR(eQ) + data[2]*PQR(eR)),\n"
        "         0.5*( data[3]*PQR(eP) + data[0]*PQR(eQ) - data[1]*PQR(eR)),\n"
        "         0.5*(-data[2]*PQR(eP) + data[1]*PQR(eQ) + data[0]*PQR(eR))\n"
        "    );\n"
        "}")

    heading("Перенормування", 1, story)
    story.append(p(
        "Числове інтегрування <i><font name='DejaVu'>q̇</font></i> за схемами Ейлера чи Адамса-Башфорта "
        "не зберігає одиничну норму — з часом кватерніон зсувається з "
        "одиничної 3-сфери, що рівносильно появі паразитного "
        "розтягнення. JSBSim перенормовує його кожного "
        "такту, ділячи на модуль (<font face='Courier'>"
        "FGQuaternion::Normalize()</font>). Інтегратори Buss уникають "
        "цього, інтегруючи безпосередньо за допомогою експоненційного "
        "відображення:"))
    math("q(t+Δt) &nbsp;=&nbsp; q(t) · exp(½ · Δt · ω)")
    story.append(p(
        "що є точним для сталого ω і зберігає одиничну норму з точністю "
        "до рухомої коми."))

    heading("Видобування кутів Ейлера", 1, story)
    story.append(p(
        "<font face='Courier'>FGQuaternion::GetEulerDeg()</font> повертає "
        "звичайні кути Ейлера літака (φ, θ, ψ) у градусах за "
        "послідовністю 3-2-1 (Z-Y-X, внутрішня). Особлива точка при "
        "θ = ±90° неминуча — кватерніони існують саме для того, щоб "
        "<i>уникнути</i> особливості під час інтегрування, але вони все "
        "одно мусять проєктуватися крізь неї, коли ви зчитуєте кути "
        "Ейлера. Для високопілотажних літаків виконуйте всі "
        "обчислення у просторі кватерніонів або у просторі DCM і "
        "видобувайте кути Ейлера лише наприкінці."))


def add_chapter_worked_example(story):
    story.append(PageBreak())
    heading("Повний розібраний приклад: простий літак", 0, story)
    story.append(p(
        "Цей розділ проходить кожну секцію мінімального, але придатного "
        "до польоту літака — легкого одномоторного Acme A-1 — беручи "
        "значення з геометрії за першими принципами, поршневого двигуна, "
        "повторно використаного з бібліотеки, та аеродинамічних "
        "коефіцієнтів, отриманих за CFD. Повний XML наведено частинами з "
        "коментарями."))

    heading("Заголовок та довідкові дані", 1, story)
    code(
        "<?xml version=\"1.0\"?>\n"
        "<fdm_config name=\"AcmeA1\" version=\"2.0\" release=\"ALPHA\">\n"
        "\n"
        "<fileheader>\n"
        "    <author>Engineering Team</author>\n"
        "    <filecreationdate>2026-05-24</filecreationdate>\n"
        "    <description>Acme A-1, single-engine 2-seat sport aircraft.</description>\n"
        "</fileheader>\n"
        "\n"
        "<metrics>\n"
        "    <wingarea unit=\"FT2\">  140 </wingarea>      <!-- S -->\n"
        "    <wingspan unit=\"FT\">    32 </wingspan>      <!-- b -->\n"
        "    <chord    unit=\"FT\">   4.4 </chord>         <!-- cbar -->\n"
        "    <htailarea unit=\"FT2\">  18 </htailarea>\n"
        "    <htailarm  unit=\"FT\">   14 </htailarm>\n"
        "    <vtailarea unit=\"FT2\">  15 </vtailarea>\n"
        "    <vtailarm  unit=\"FT\">   14 </vtailarm>\n"
        "    <location name=\"AERORP\" unit=\"IN\">\n"
        "        <x>40</x><y>0</y><z>30</z>             <!-- 25% MAC -->\n"
        "    </location>\n"
        "    <location name=\"EYEPOINT\" unit=\"IN\">\n"
        "        <x>30</x><y>-10</y><z>50</z>\n"
        "    </location>\n"
        "    <location name=\"VRP\" unit=\"IN\">\n"
        "        <x>0</x><y>0</y><z>0</z>\n"
        "    </location>\n"
        "</metrics>")

    heading("Маса, центрування та інерція", 1, story)
    code(
        "<mass_balance>\n"
        "    <!-- Inertias from CAD about the empty-weight CG, structural frame -->\n"
        "    <ixx unit=\"SLUG*FT2\">  800 </ixx>\n"
        "    <iyy unit=\"SLUG*FT2\"> 1100 </iyy>\n"
        "    <izz unit=\"SLUG*FT2\"> 1700 </izz>\n"
        "    <ixz unit=\"SLUG*FT2\">   0  </ixz>\n"
        "    <emptywt unit=\"LBS\"> 1250 </emptywt>\n"
        "    <location name=\"CG\" unit=\"IN\">\n"
        "        <x>39</x><y>0</y><z>30</z>             <!-- ~24% MAC -->\n"
        "    </location>\n"
        "    <pointmass name=\"Pilot\">\n"
        "        <weight unit=\"LBS\">175</weight>\n"
        "        <location unit=\"IN\"><x>34</x><y>-12</y><z>32</z></location>\n"
        "    </pointmass>\n"
        "    <pointmass name=\"Passenger\">\n"
        "        <weight unit=\"LBS\">175</weight>\n"
        "        <location unit=\"IN\"><x>34</x><y> 12</y><z>32</z></location>\n"
        "    </pointmass>\n"
        "    <pointmass name=\"Baggage\">\n"
        "        <weight unit=\"LBS\"> 60</weight>\n"
        "        <location unit=\"IN\"><x>70</x><y>0</y><z>30</z></location>\n"
        "    </pointmass>\n"
        "</mass_balance>")

    heading("Шасі", 1, story)
    code(
        "<ground_reactions>\n"
        "    <contact type=\"BOGEY\" name=\"NOSE\">\n"
        "        <location unit=\"IN\"><x>-10</x><y>0</y><z>-20</z></location>\n"
        "        <static_friction>0.8</static_friction>\n"
        "        <dynamic_friction>0.5</dynamic_friction>\n"
        "        <rolling_friction>0.02</rolling_friction>\n"
        "        <spring_coeff  unit=\"LBS/FT\">    1500 </spring_coeff>\n"
        "        <damping_coeff unit=\"LBS/FT/SEC\"> 500 </damping_coeff>\n"
        "        <max_steer unit=\"DEG\">15</max_steer>\n"
        "        <brake_group>NONE</brake_group>\n"
        "    </contact>\n"
        "    <contact type=\"BOGEY\" name=\"LEFT_MAIN\">\n"
        "        <location unit=\"IN\"><x>55</x><y>-40</y><z>-18</z></location>\n"
        "        <static_friction>0.8</static_friction>\n"
        "        <dynamic_friction>0.5</dynamic_friction>\n"
        "        <rolling_friction>0.02</rolling_friction>\n"
        "        <spring_coeff  unit=\"LBS/FT\">    4500 </spring_coeff>\n"
        "        <damping_coeff unit=\"LBS/FT/SEC\">1300 </damping_coeff>\n"
        "        <brake_group>LEFT</brake_group>\n"
        "    </contact>\n"
        "    <contact type=\"BOGEY\" name=\"RIGHT_MAIN\">\n"
        "        <location unit=\"IN\"><x>55</x><y> 40</y><z>-18</z></location>\n"
        "        <static_friction>0.8</static_friction>\n"
        "        <dynamic_friction>0.5</dynamic_friction>\n"
        "        <rolling_friction>0.02</rolling_friction>\n"
        "        <spring_coeff  unit=\"LBS/FT\">    4500 </spring_coeff>\n"
        "        <damping_coeff unit=\"LBS/FT/SEC\">1300 </damping_coeff>\n"
        "        <brake_group>RIGHT</brake_group>\n"
        "    </contact>\n"
        "    <contact type=\"STRUCTURE\" name=\"LEFT_TIP\">\n"
        "        <location unit=\"IN\"><x>40</x><y>-192</y><z>30</z></location>\n"
        "        <static_friction>0.2</static_friction>\n"
        "        <dynamic_friction>0.2</dynamic_friction>\n"
        "        <spring_coeff  unit=\"LBS/FT\">    20000 </spring_coeff>\n"
        "        <damping_coeff unit=\"LBS/FT/SEC\"> 2000 </damping_coeff>\n"
        "    </contact>\n"
        "    <contact type=\"STRUCTURE\" name=\"RIGHT_TIP\">\n"
        "        <location unit=\"IN\"><x>40</x><y> 192</y><z>30</z></location>\n"
        "        <static_friction>0.2</static_friction>\n"
        "        <dynamic_friction>0.2</dynamic_friction>\n"
        "        <spring_coeff  unit=\"LBS/FT\">    20000 </spring_coeff>\n"
        "        <damping_coeff unit=\"LBS/FT/SEC\"> 2000 </damping_coeff>\n"
        "    </contact>\n"
        "</ground_reactions>")

    heading("Силова установка", 1, story)
    code(
        "<propulsion>\n"
        "    <engine file=\"eng_io360\">          <!-- 180 hp 4-cyl -->\n"
        "        <feed>0</feed>\n"
        "        <feed>1</feed>\n"
        "        <thruster file=\"prop_77in\">\n"
        "            <location unit=\"IN\"><x>-30</x><y>0</y><z>30</z></location>\n"
        "            <orient unit=\"DEG\"><pitch>2</pitch></orient>\n"
        "            <sense>1</sense>\n"
        "            <p_factor>5</p_factor>\n"
        "        </thruster>\n"
        "    </engine>\n"
        "    <tank type=\"FUEL\" number=\"0\">\n"
        "        <location unit=\"IN\"><x>40</x><y>-80</y><z>32</z></location>\n"
        "        <capacity unit=\"LBS\">160</capacity>\n"
        "        <contents unit=\"LBS\">120</contents>\n"
        "        <type>AVGAS</type>\n"
        "    </tank>\n"
        "    <tank type=\"FUEL\" number=\"1\">\n"
        "        <location unit=\"IN\"><x>40</x><y> 80</y><z>32</z></location>\n"
        "        <capacity unit=\"LBS\">160</capacity>\n"
        "        <contents unit=\"LBS\">120</contents>\n"
        "        <type>AVGAS</type>\n"
        "    </tank>\n"
        "</propulsion>")

    heading("Система керування польотом", 1, story)
    code(
        "<flight_control name=\"FCS: AcmeA1\">\n"
        "    <channel name=\"Pitch\">\n"
        "        <summer name=\"pitch_sum\">\n"
        "            <input>fcs/elevator-cmd-norm</input>\n"
        "            <input>fcs/pitch-trim-cmd-norm</input>\n"
        "            <clipto><min>-1</min><max>1</max></clipto>\n"
        "        </summer>\n"
        "        <aerosurface_scale name=\"elevator\">\n"
        "            <input>fcs/pitch_sum</input>\n"
        "            <range><min>-25</min><max>20</max></range>\n"
        "            <gain>0.01745</gain>\n"
        "            <output>fcs/elevator-pos-rad</output>\n"
        "        </aerosurface_scale>\n"
        "    </channel>\n"
        "\n"
        "    <channel name=\"Roll\">\n"
        "        <summer name=\"roll_sum\">\n"
        "            <input>fcs/aileron-cmd-norm</input>\n"
        "            <input>fcs/roll-trim-cmd-norm</input>\n"
        "            <clipto><min>-1</min><max>1</max></clipto>\n"
        "        </summer>\n"
        "        <aerosurface_scale name=\"left_aileron\">\n"
        "            <input>fcs/roll_sum</input>\n"
        "            <range><min>-20</min><max>15</max></range>\n"
        "            <gain>0.01745</gain>\n"
        "            <output>fcs/left-aileron-pos-rad</output>\n"
        "        </aerosurface_scale>\n"
        "        <aerosurface_scale name=\"right_aileron\">\n"
        "            <input>fcs/roll_sum</input>\n"
        "            <range><min>-15</min><max>20</max></range>\n"
        "            <gain>-0.01745</gain>\n"
        "            <output>fcs/right-aileron-pos-rad</output>\n"
        "        </aerosurface_scale>\n"
        "    </channel>\n"
        "\n"
        "    <channel name=\"Yaw\">\n"
        "        <summer name=\"yaw_sum\">\n"
        "            <input>fcs/rudder-cmd-norm</input>\n"
        "            <input>fcs/yaw-trim-cmd-norm</input>\n"
        "            <clipto><min>-1</min><max>1</max></clipto>\n"
        "        </summer>\n"
        "        <aerosurface_scale name=\"rudder\">\n"
        "            <input>fcs/yaw_sum</input>\n"
        "            <range><min>-20</min><max>20</max></range>\n"
        "            <gain>0.01745</gain>\n"
        "            <output>fcs/rudder-pos-rad</output>\n"
        "        </aerosurface_scale>\n"
        "    </channel>\n"
        "\n"
        "    <channel name=\"Flaps\">\n"
        "        <kinematic name=\"flaps\">\n"
        "            <input>fcs/flap-cmd-norm</input>\n"
        "            <traverse>\n"
        "                <setting><position> 0</position><time>0</time></setting>\n"
        "                <setting><position>10</position><time>3</time></setting>\n"
        "                <setting><position>20</position><time>2</time></setting>\n"
        "                <setting><position>30</position><time>2</time></setting>\n"
        "            </traverse>\n"
        "            <output>fcs/flap-pos-deg</output>\n"
        "        </kinematic>\n"
        "    </channel>\n"
        "</flight_control>")

    heading("Аеродинаміка (репрезентативні значення з CFD)", 1, story)
    code(
        "<aerodynamics>\n"
        "    <alphalimits unit=\"RAD\">\n"
        "        <min>-0.087</min><max>0.30</max>\n"
        "    </alphalimits>\n"
        "    <hysteresis_limits unit=\"RAD\">\n"
        "        <min>0.20</min><max>0.30</max>\n"
        "    </hysteresis_limits>\n"
        "\n"
        "    <!-- ============================ LIFT ============================ -->\n"
        "    <axis name=\"LIFT\">\n"
        "        <function name=\"aero/coefficient/CLwbh\">\n"
        "            <description>Wing-body-tail lift vs alpha (clean)</description>\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <table>\n"
        "                    <independentVar>aero/alpha-rad</independentVar>\n"
        "                    <tableData>\n"
        "                       -0.087  -0.250\n"
        "                       -0.044   0.100\n"
        "                        0.000   0.300\n"
        "                        0.087   0.760\n"
        "                        0.175   1.230\n"
        "                        0.262   1.500\n"
        "                        0.300   1.200    <!-- post-stall -->\n"
        "                    </tableData>\n"
        "                </table>\n"
        "            </product>\n"
        "        </function>\n"
        "\n"
        "        <function name=\"aero/coefficient/CLDf\">\n"
        "            <description>Lift increment due to flap</description>\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <table>\n"
        "                    <independentVar>fcs/flap-pos-deg</independentVar>\n"
        "                    <tableData>\n"
        "                         0   0.00\n"
        "                        10   0.20\n"
        "                        20   0.35\n"
        "                        30   0.45\n"
        "                    </tableData>\n"
        "                </table>\n"
        "            </product>\n"
        "        </function>\n"
        "\n"
        "        <function name=\"aero/coefficient/CLde\">\n"
        "            <description>Lift due to elevator</description>\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>fcs/elevator-pos-rad</property>\n"
        "                <value>0.43</value>\n"
        "            </product>\n"
        "        </function>\n"
        "    </axis>\n"
        "\n"
        "    <!-- ============================ DRAG ============================ -->\n"
        "    <axis name=\"DRAG\">\n"
        "        <function name=\"aero/coefficient/CD0\">\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <value>0.025</value>\n"
        "            </product>\n"
        "        </function>\n"
        "        <function name=\"aero/coefficient/CDi\">\n"
        "            <description>Induced drag, CL^2 / (pi * AR * e)</description>\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <quotient>\n"
        "                    <property>aero/cl-squared</property>\n"
        "                    <value>20.4</value>           <!-- pi * AR * e ~ 20 -->\n"
        "                </quotient>\n"
        "            </product>\n"
        "        </function>\n"
        "    </axis>\n"
        "\n"
        "    <!-- =========================== PITCH ============================ -->\n"
        "    <axis name=\"PITCH\">\n"
        "        <function name=\"aero/coefficient/Cm0\">\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>metrics/cbarw-ft</property>\n"
        "                <value>-0.04</value>\n"
        "            </product>\n"
        "        </function>\n"
        "        <function name=\"aero/coefficient/Cma\">\n"
        "            <description>Pitch moment slope (must be negative)</description>\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>metrics/cbarw-ft</property>\n"
        "                <property>aero/alpha-rad</property>\n"
        "                <value>-0.5</value>\n"
        "            </product>\n"
        "        </function>\n"
        "        <function name=\"aero/coefficient/Cmde\">\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>metrics/cbarw-ft</property>\n"
        "                <property>fcs/elevator-pos-rad</property>\n"
        "                <value>-1.10</value>\n"
        "            </product>\n"
        "        </function>\n"
        "        <function name=\"aero/coefficient/Cmq\">\n"
        "            <description>Pitch damping</description>\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>metrics/cbarw-ft</property>\n"
        "                <property>aero/ci2vel</property>\n"
        "                <property>velocities/q-aero-rad_sec</property>\n"
        "                <value>-12.0</value>\n"
        "            </product>\n"
        "        </function>\n"
        "    </axis>\n"
        "\n"
        "    <!-- ============================ SIDE ============================ -->\n"
        "    <axis name=\"SIDE\">\n"
        "        <function name=\"aero/coefficient/CYb\">\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>aero/beta-rad</property>\n"
        "                <value>-0.7</value>\n"
        "            </product>\n"
        "        </function>\n"
        "    </axis>\n"
        "\n"
        "    <!-- ============================ ROLL ============================ -->\n"
        "    <axis name=\"ROLL\">\n"
        "        <function name=\"aero/coefficient/Clb\">\n"
        "            <description>Dihedral effect (must be negative)</description>\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>metrics/bw-ft</property>\n"
        "                <property>aero/beta-rad</property>\n"
        "                <value>-0.08</value>\n"
        "            </product>\n"
        "        </function>\n"
        "        <function name=\"aero/coefficient/Clp\">\n"
        "            <description>Roll damping</description>\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>metrics/bw-ft</property>\n"
        "                <property>aero/bi2vel</property>\n"
        "                <property>velocities/p-aero-rad_sec</property>\n"
        "                <value>-0.46</value>\n"
        "            </product>\n"
        "        </function>\n"
        "        <function name=\"aero/coefficient/Clda\">\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>metrics/bw-ft</property>\n"
        "                <property>fcs/left-aileron-pos-rad</property>\n"
        "                <value>0.22</value>\n"
        "            </product>\n"
        "        </function>\n"
        "    </axis>\n"
        "\n"
        "    <!-- ============================ YAW ============================= -->\n"
        "    <axis name=\"YAW\">\n"
        "        <function name=\"aero/coefficient/Cnb\">\n"
        "            <description>Weathercock stability (must be positive)</description>\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>metrics/bw-ft</property>\n"
        "                <property>aero/beta-rad</property>\n"
        "                <value>0.06</value>\n"
        "            </product>\n"
        "        </function>\n"
        "        <function name=\"aero/coefficient/Cnr\">\n"
        "            <description>Yaw damping</description>\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>metrics/bw-ft</property>\n"
        "                <property>aero/bi2vel</property>\n"
        "                <property>velocities/r-aero-rad_sec</property>\n"
        "                <value>-0.10</value>\n"
        "            </product>\n"
        "        </function>\n"
        "        <function name=\"aero/coefficient/Cndr\">\n"
        "            <product>\n"
        "                <property>aero/qbar-psf</property>\n"
        "                <property>metrics/Sw-sqft</property>\n"
        "                <property>metrics/bw-ft</property>\n"
        "                <property>fcs/rudder-pos-rad</property>\n"
        "                <value>-0.05</value>\n"
        "            </product>\n"
        "        </function>\n"
        "    </axis>\n"
        "</aerodynamics>\n"
        "\n"
        "</fdm_config>")
    story.append(p(
        "<b>Перевірки правдоподібності для цієї моделі</b>:"))
    for b in [
        "C<sub>Lα</sub> ≈ 5.4/rad (нахил таблиці піднімальної сили "
        "поблизу α=0). Типове значення для прямокутного крила при "
        "AR ≈ 7.3 становить близько 4.7/rad — наше число достатньо "
        "близьке.",
        "C<sub>Lmax</sub> ≈ 1.5. Прийнятно для чистого крила.",
        "C<sub>D0</sub> = 0.025. Приблизно правильне значення для "
        "одномоторного літака з неприбиральним шасі.",
        "Статично стійкий: C<sub>mα</sub> = −0.5 &lt; 0, "
        "C<sub>nβ</sub> = +0.06 &gt; 0, C<sub>lβ</sub> = −0.08 &lt; 0.",
        "Знак похідної за кермом висоти: C<sub>mδe</sub> = −1.1. "
        "Відхилення задньої кромки вниз (додатне δ<sub>e</sub>) "
        "створює тангаж на пікірування — це відповідає нашій "
        "домовленості про знаки.",
    ]:
        story.append(bullet(b))


def add_chapter_scripts_ic(story):
    story.append(PageBreak())
    heading("Початкові умови, сценарії та скидання", 0, story)

    heading("Початкові умови (файли скидання)", 1, story)
    story.append(p(
        "Файл початкових умов (IC) задає кожну змінну стану до "
        "самоузгодженої вихідної точки для симуляції. Мінімальний набір — "
        "це положення (3), орієнтація (3), швидкість (3) — далі JSBSim "
        "обчислює α, β, <font name='DejaVu'>q̄</font>, число Маха внутрішньо. Можна задати надлишково й "
        "дати JSBSim усе узгодити, але краще задавати явно."))
    code(
        "<?xml version=\"1.0\"?>\n"
        "<initialize name=\"cruise_5000\">\n"
        "    <!-- Position -->\n"
        "    <latitude  unit=\"DEG\">  37.6 </latitude>\n"
        "    <longitude unit=\"DEG\">-122.4 </longitude>\n"
        "    <altitude  unit=\"FT\">   5000 </altitude>          <!-- above MSL -->\n"
        "\n"
        "    <!-- Attitude (Euler 3-2-1) -->\n"
        "    <phi   unit=\"DEG\"> 0 </phi>                       <!-- bank -->\n"
        "    <theta unit=\"DEG\"> 2 </theta>                     <!-- pitch -->\n"
        "    <psi   unit=\"DEG\"> 90 </psi>                      <!-- heading -->\n"
        "\n"
        "    <!-- Pick ONE velocity spec: -->\n"
        "    <ubody unit=\"FT/SEC\"> 150 </ubody>\n"
        "    <vbody unit=\"FT/SEC\">   0 </vbody>\n"
        "    <wbody unit=\"FT/SEC\">   5 </wbody>\n"
        "    <!--  or: <vt unit=\"KTS\">100</vt> with <alpha unit=\"DEG\">2</alpha> -->\n"
        "    <!--  or: <vc unit=\"KTS\">95</vc> (calibrated airspeed) -->\n"
        "    <!--  or: <mach>0.55</mach> -->\n"
        "</initialize>")
    story.append(p(
        "Інші корисні елементи IC:"))
    code(
        "<gamma unit=\"DEG\"> 0 </gamma>          flight path angle\n"
        "<vnorth>0</vnorth><veast>0</veast><vdown>0</vdown>   NED wind-rel velocity\n"
        "<roc   unit=\"FT/MIN\"> 0 </roc>          rate of climb\n"
        "<altitudeAGL unit=\"FT\"> 0 </altitudeAGL> above ground level\n"
        "<targetNlf> 1 </targetNlf>               target load factor for trim-pullup")

    heading("Сценарії (подієво-орієнтовані випробування)", 1, story)
    story.append(p(
        "Сценарій (script) — це замкнений опис випробувального польотного "
        "сценарію: послідовність подій з умовами та діями над "
        "властивостями. Цикл Run крокує модель із заданим "
        "<font face='Courier'>dt</font>, доки не досягне "
        "<font face='Courier'>end</font>."))
    code(
        "<?xml version=\"1.0\"?>\n"
        "<runscript name=\"Cruise climb\">\n"
        "    <description>5000 ft cruise -> trim -> climb to 8000</description>\n"
        "    <use aircraft=\"AcmeA1\" initialize=\"cruise_5000\"/>\n"
        "\n"
        "    <run start=\"0\" end=\"300\" dt=\"0.00833333\">\n"
        "        <event name=\"Trim\">\n"
        "            <condition>simulation/sim-time-sec ge 0</condition>\n"
        "            <set name=\"simulation/do_simple_trim\" value=\"1\"/>\n"
        "            <notify/>\n"
        "        </event>\n"
        "\n"
        "        <event name=\"Throttle up\">\n"
        "            <condition>simulation/sim-time-sec ge 30</condition>\n"
        "            <set name=\"fcs/throttle-cmd-norm\"\n"
        "                 action=\"FG_EXP\" tc=\"5.0\" value=\"1.0\"/>\n"
        "            <notify/>\n"
        "        </event>\n"
        "\n"
        "        <event name=\"Climb to 8000\">\n"
        "            <condition>simulation/sim-time-sec ge 60</condition>\n"
        "            <set name=\"fcs/elevator-cmd-norm\"\n"
        "                 action=\"FG_RAMP\" tc=\"3.0\" value=\"-0.1\"/>\n"
        "            <notify/>\n"
        "        </event>\n"
        "\n"
        "        <event name=\"Level off\">\n"
        "            <condition>position/h-sl-ft ge 8000</condition>\n"
        "            <set name=\"fcs/elevator-cmd-norm\" value=\"0\"/>\n"
        "            <notify>\n"
        "                <property>position/h-sl-ft</property>\n"
        "                <property>velocities/vc-kts</property>\n"
        "            </notify>\n"
        "        </event>\n"
        "    </run>\n"
        "</runscript>")
    story.append(p(
        "<b>Типи дій</b> для <font face='Courier'>&lt;set&gt;</font>:"))
    code(
        "FG_VALUE   set property to value immediately (default)\n"
        "FG_DELTA   add value to current property\n"
        "FG_RAMP    linear ramp over tc seconds\n"
        "FG_EXP     first-order exponential approach with tc seconds")
    story.append(p(
        "<b>Умови</b>: будь-який булів вираз над властивостями з "
        "використанням <font face='Courier'>ge le gt lt eq nq and or not</font>. "
        "Умови можна вкладати через "
        "<font face='Courier'>&lt;condition logic=\"AND|OR\"&gt;"
        "</font>."))


def add_chapter_validation(story):
    story.append(PageBreak())
    heading("Процес валідації", 0, story)
    story.append(p(
        "Модель, яка компілюється й балансується, — це лише перший крок. "
        "Наведені нижче стандартні для галузі кроки валідації виявляють "
        "переважну більшість помилок моделювання ще до того, як вони "
        "потраплять до замовника."))

    heading("Крок 1: діагностика балансування", 1, story)
    story.append(p(
        "Запустіть <font face='Courier'>simulation/do_simple_trim</font> = 1 "
        "(поздовжнє) і перевірте, що отримані положення керма висоти та "
        "сектора газу лежать у межах реального діапазону керування. Якщо "
        "балансувальний α близький до верхньої межі за кутом атаки, то "
        "балансування не зірвалося лише завдяки везінню; зменшіть "
        "крейсерську швидкість або перевірте свою криву "
        "C<sub>L</sub>(α)."))

    heading("Крок 2: розімкнені перехідні характеристики", 1, story)
    story.append(p(
        "Виконайте подвійні відхилення керма висоти, імпульси елеронів і "
        "поштовхи кермом напряму з балансувального стану. Побудуйте графіки "
        "p, q, r, α, β, φ, θ, ψ:"))
    for b in [
        "<b>Фугоїд</b>: коливання з періодом ~30-60 с, слабко демпфований "
        "(ζ ≈ 0.05). Проявляється як довгоперіодні коливання висоти й "
        "повітряної швидкості після збурення за тангажем.",
        "<b>Коротко-періодичний рух</b>: період ~2-5 с, добре демпфований "
        "(ζ ≈ 0.5). Проявляється як швидке коливання кутової швидкості "
        "тангажа після подвійного відхилення.",
        "<b>Крен-мода</b>: першого порядку, стала часу ~0.5-1.5 с. "
        "Проявляється як експоненційне згасання p після поштовху елеронами.",
        "<b>Голландський крок</b>: період ~3-6 с, ζ ≈ 0.05-0.3. Зв’язане "
        "рискання-крен після поштовху кермом напряму.",
        "<b>Спіральна мода</b>: дуже повільна (стала часу ~30-300 с), часто "
        "трохи нестійка для звичайних літаків.",
    ]:
        story.append(bullet(b))

    heading("Крок 3: вилучення лінійної моделі", 1, story)
    story.append(p(
        "JSBSim постачає утиліту мовою Python "
        "(<font face='Courier'>python/JSBSim/utils/linearize.py</font>), "
        "яка будує лінійну модель A, B, C, D в балансувальній точці. "
        "Обчисліть власні значення матриці A і порівняйте полюси з "
        "аналітичними оцінками Etkin або Stevens-Lewis. Порядок величини "
        "має збігатися; якщо полюс опиняється не в тій півплощині, у вас "
        "помилка знака в аеродинамічних коефіцієнтах."))

    heading("Крок 4: перевірка експлуатаційного діапазону", 1, story)
    table_data = [
        ["Величина", "Як отримати в JSBSim", "Порівнювати з"],
        ["V<sub>S0</sub> швидкість звалювання (чиста)",
            "Збалансувати на мін. α, утримуючи висоту, зменшити сектор газу",
            "POH або проєктна ціль"],
        ["V<sub>S1</sub> швидкість звалювання (закрилки)",
            "Те саме, але з положенням закрилків = макс.",
            "POH"],
        ["V<sub>max</sub>",
            "Горизонтальний політ на повному газі, записати швидкість",
            "POH"],
        ["Найбільша скоропідіймальність (V<sub>y</sub>)",
            "Набір висоти на різних швидкостях, знайти макс. ROC",
            "Графік з POH"],
        ["Практична стеля",
            "Балансування з кроком за висотою, знайти h за ROC = 100 fpm",
            "POH"],
        ["Дальність",
            "Крейсерський режим найбільшої економічності, інтегрувати "
            "витрату пального",
            "POH"],
    ]
    t = Table(wrap_table(table_data), colWidths=[5.0 * cm, 6.0 * cm, 5.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    heading("Крок 5: перевірка пілотажних властивостей", 1, story)
    story.append(p(
        "Якщо вас цікавить відчуття від пілотування, оцініть модель за "
        "специфікаціями пілотажних властивостей MIL-F-8785C / "
        "MIL-HDBK-1797. Найцінніший окремий показник — це <i>параметр C*</i> "
        "(коефіцієнт перевантаження, зважений за кутовою швидкістю тангажа), "
        "нанесений на граничну діаграму Cooper-Harper для крейсерського "
        "режиму. JSBSim видає всі необхідні властивості, щоб обчислити його "
        "офлайн."))

    heading("Крок 6: порівняння з льотними випробуваннями", 1, story)
    story.append(p(
        "Там, де є дані льотних випробувань, виконайте той самий маневр у "
        "JSBSim з тими самими вхідними даними й накладіть графіки. "
        "Розбіжності, які ви побачите, — це рецепт для наступної ітерації "
        "CFD або підстроювання коефіцієнтів. Стережіться «гонитви за "
        "польотом»: підстроювання JSBSim під один маневр часто погіршує "
        "інші. Завжди перевіряйте модель на відкладеному наборі маневрів."))


def add_chapter_troubleshooting(story):
    story.append(PageBreak())
    heading("Поширені помилки та способи їх діагностики", 0, story)
    story.append(p(
        "Це режими відмов, з якими найчастіше стикаються новачки, "
        "приблизно за порядком частоти. Стовпець розв’язку вказує на те, "
        "що слід перевірити насамперед."))
    table_data = [
        ["Симптом", "Імовірна причина", "Що перевірити першим"],
        ["Літак «провалюється» крізь злітну смугу за IC",
            "Координата Z шасі має неправильний знак або одиницю",
            "<font face='Courier'>&lt;contact&gt;</font> Z має бути "
            "від’ємним, якщо шасі нижче за початок структурної системи"],
        ["Літак догори дриґом або обертається на 180° під час запуску",
            "Розбіжність угод щодо ψ та курсу або "
            "невідповідність negated_crossproduct_inertia",
            "Поміняйте атрибут знака інерції"],
        ["Балансування одразу провалюється",
            "Діапазон α в таблицях CFD не охоплює балансувальний α",
            "Задайте <font face='Courier'>&lt;output&gt;</font> для α і "
            "запустіть нерозважливо — подивіться, який α він запитує"],
        ["Балансування збігається, але літак опускає ніс і пікірує",
            "Помилка знака C<sub>mα</sub> (модель статично нестійка)",
            "Побудуйте Cm від α; нахил має бути від’ємним"],
        ["Літак некеровано рискає вбік",
            "Помилка знака C<sub>nβ</sub>",
            "Нахил має бути додатним"],
        ["Повільне, але стале кренення",
            "Несиметрична точкова маса або елерон не відцентрований",
            "Перевірте, що Y-координати точкових мас у сумі дають нуль"],
        ["Тангаж коливається на 0.5-2 Гц",
            "Недостатній C<sub>mq</sub> або неправильний знак",
            "Має бути від’ємним; величина 5-15 для авіації загального "
            "призначення"],
        ["Відхилення елеронів не дає реакції за креном",
            "Неправильний знак C<sub>lδa</sub> або властивість положення "
            "елерона не відповідає властивості аеродинамічного коефіцієнта",
            "Простежте fcs/left-aileron-pos-rad аж до функції"],
        ["Величезна сила опору на балансуванні",
            "Забули відняти опорну силу опору, або "
            "коефіцієнти CFD у зв’язаній системі подано на осі LIFT/DRAG",
            "Обчисліть D = C<sub>D</sub>·<font name='DejaVu'>q̄</font>·S вручну; "
            "порівняйте з F<sub>x,aero,body</sub>"],
        ["Двигун не створює тяги",
            "Місткість бака = 0 або неправильні індекси подачі",
            "Перевірте <font face='Courier'>propulsion/tank[n]/contents-lbs"
            "</font>"],
        ["Симуляція аварійно завершується з NaN",
            "Ділення на нуль у функції (часто /Vt за нульової повітряної "
            "швидкості) або кватерніон став неодиничним",
            "Додайте <font face='Courier'>&lt;clipto&gt;</font> або захистіть "
            "за допомогою <font face='Courier'>&lt;ifthen&gt;</font>"],
        ["Літак «занурюється» крізь землю після приземлення",
            "Стала пружини занадто м’яка для цієї ваги",
            "k ≥ W / 0.5 ft для нормальних коефіцієнтів демпфування"],
        ["Сильно стрибає під час посадки",
            "Коефіцієнт демпфування занадто низький",
            "Прагніть до ζ ≈ 0.4-0.6 (c = 2ζ√(km))"],
        ["Вихід FCS застряг на clipto",
            "Насичення; інтегратор «розкрутився»",
            "Додайте тригер антинасичення (anti-windup) до ПІД-регулятора"],
        ["FlightGear показує тремтіння літака",
            "Розбіжність частоти виводу або розходження кроку часу FG/FDM",
            "Задайте частоту виводу 60 Гц і FG теж на 60 Гц"],
    ]
    t = Table(wrap_table(table_data), colWidths=[4.8 * cm, 5.4 * cm, 6.3 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)


def add_chapter_python_api(story):
    story.append(PageBreak())
    heading("API мовою Python", 0, story)
    story.append(p(
        "JSBSim постачає модуль мовою Python (<font face='Courier'>jsbsim"
        "</font>) у PyPI та conda-forge, який обгортає бібліотеку C++. "
        "Це рекомендований спосіб керувати JSBSim із коду машинного "
        "навчання, пакетних параметричних досліджень або модульних тестів."))

    heading("Швидкий старт", 1, story)
    code(
        "import jsbsim\n"
        "\n"
        "fdm = jsbsim.FGFDMExec(root_dir=None)  # auto-detect aircraft path\n"
        "fdm.set_debug_level(0)\n"
        "fdm.load_model('c172p')\n"
        "fdm.load_ic('reset00', useStoredPath=True)\n"
        "fdm.run_ic()                            # apply initial conditions\n"
        "\n"
        "# Trim longitudinally\n"
        "fdm['simulation/do_simple_trim'] = 1\n"
        "\n"
        "# Step the model 10 seconds at 120 Hz\n"
        "for _ in range(1200):\n"
        "    fdm.run()\n"
        "\n"
        "print(\"alt:\", fdm['position/h-sl-ft'])\n"
        "print(\"V :\", fdm['velocities/vt-fps'])")

    heading("Читання та запис властивостей", 1, story)
    code(
        "# All properties accessible by string path\n"
        "fdm['fcs/elevator-cmd-norm'] = -0.1     # nose-up command\n"
        "fdm['fcs/throttle-cmd-norm'] = 0.8\n"
        "alpha = fdm['aero/alpha-deg']\n"
        "p, q, r = (fdm[f'velocities/{ax}-rad_sec'] for ax in 'pqr')\n"
        "\n"
        "# Snapshot the full property tree (slow)\n"
        "snapshot = fdm.query_property_catalog('')")

    heading("Балансування та лінеаризація", 1, story)
    code(
        "from jsbsim.utils.linearize import linearize\n"
        "\n"
        "fdm.load_model('c172p')\n"
        "fdm.load_ic('cruise', useStoredPath=True)\n"
        "fdm.run_ic()\n"
        "fdm['simulation/do_simple_trim'] = 1\n"
        "\n"
        "A, B, C, D, x_trim, u_trim = linearize(fdm)\n"
        "import numpy as np\n"
        "eigvals = np.linalg.eigvals(A)\n"
        "print(sorted(eigvals, key=lambda e: e.real))")

    heading("Пакетні параметричні дослідження", 1, story)
    code(
        "def sweep_alpha(cg_x_in):\n"
        "    fdm = jsbsim.FGFDMExec(None)\n"
        "    fdm.load_model('AcmeA1')\n"
        "    fdm.load_ic('cruise_5000', useStoredPath=True)\n"
        "    fdm['inertia/pointmass-location-X-inches[0]'] = cg_x_in\n"
        "    fdm.run_ic()\n"
        "    fdm['simulation/do_simple_trim'] = 1\n"
        "    return fdm['aero/alpha-deg'], fdm['fcs/elevator-pos-deg']\n"
        "\n"
        "for cg in range(30, 50, 2):\n"
        "    a, e = sweep_alpha(cg)\n"
        "    print(f'CG={cg} in   alpha={a:.2f}  elev={e:.2f}')")


def add_chapter_extended_properties(story):
    story.append(PageBreak())
    heading("Розширений довідник властивостей", 0, story)
    story.append(p(
        "Повне дерево властивостей публікує сам JSBSim за допомогою "
        "<font face='Courier'>fdm.query_property_catalog('')</font>. "
        "Тут згруповано найкорисніші властивості для зчитування показників "
        "та машинного навчання."))

    heading("Час", 1, story)
    code(
        "simulation/sim-time-sec                 simulation time since reset\n"
        "simulation/frame                        tick counter\n"
        "simulation/dt                           timestep size (s)\n"
        "simulation/integrator/rate/rotational\n"
        "simulation/integrator/rate/translational\n"
        "simulation/integrator/position/rotational\n"
        "simulation/integrator/position/translational")

    heading("Атмосфера та вітри", 1, story)
    code(
        "atmosphere/T-R, T-sl-R, delta-T\n"
        "atmosphere/P-psf, P-sl-psf\n"
        "atmosphere/rho-slugs_ft3\n"
        "atmosphere/a-fps                       speed of sound\n"
        "atmosphere/density-altitude\n"
        "atmosphere/pressure-altitude\n"
        "atmosphere/wind-{north,east,down}-fps  steady wind in NED\n"
        "atmosphere/total-wind-{north,east,down}-fps wind+gust+turb\n"
        "atmosphere/turb-type                   turbulence model (0..4)\n"
        "atmosphere/turb-rate-rad_sec           current angular turbulence")

    heading("Положення", 1, story)
    code(
        "position/lat-geod-deg, lat-gc-rad      geodetic and geocentric lat\n"
        "position/long-gc-deg\n"
        "position/h-sl-ft, h-sl-meters          altitude above MSL\n"
        "position/h-agl-ft                      altitude above ground\n"
        "position/geod-alt-ft\n"
        "position/distance-from-start-mag-mt    great-circle distance\n"
        "position/terrain-elevation-asl-ft")

    heading("Орієнтація", 1, story)
    code(
        "attitude/phi-rad, theta-rad, psi-rad   Euler\n"
        "attitude/phi-deg, theta-deg, psi-deg   degrees\n"
        "attitude/heading-true-rad\n"
        "attitude/pitch-rad, roll-rad\n"
        "/sim/attitude/q[0..3]                  quaternion components (if exposed)")

    heading("Швидкості", 1, story)
    code(
        "velocities/vt-fps                      true airspeed\n"
        "velocities/vc-kts                      calibrated airspeed\n"
        "velocities/ve-kts                      equivalent airspeed\n"
        "velocities/vg-fps                      ground speed\n"
        "velocities/mach\n"
        "velocities/u-fps, v-fps, w-fps         body-frame velocity\n"
        "velocities/u-aero-fps                  body-frame airmass-relative\n"
        "velocities/p-rad_sec, q-rad_sec, r-rad_sec   body angular rates\n"
        "velocities/p-aero-rad_sec              aero-frame angular rates\n"
        "velocities/vdown-fps                   NED down velocity (=climb rate)")

    heading("Аеродинамічний стан", 1, story)
    code(
        "aero/alpha-rad, alpha-deg\n"
        "aero/beta-rad, beta-deg\n"
        "aero/alphadot-rad_sec, betadot-rad_sec\n"
        "aero/mag-alpha-rad, mag-beta-rad       |alpha|, |beta|\n"
        "aero/qbar-psf, qbarUW-psf, qbarUV-psf\n"
        "aero/h_b-mac-ft                        h/c for ground effect\n"
        "aero/bi2vel, ci2vel\n"
        "aero/cl-squared                        CL^2 from previous tick\n"
        "aero/stall-hyst-norm                   stall hysteresis switch (0 or 1)")

    heading("Сили та моменти (зв’язана система)", 1, story)
    code(
        "forces/fbx-aero, fby-aero, fbz-aero    aerodynamic\n"
        "forces/fbx-prop, fby-prop, fbz-prop    propulsion\n"
        "forces/fbx-gear, fby-gear, fbz-gear    ground reactions\n"
        "forces/fbx-external, fby-external, fbz-external\n"
        "forces/fbx-buoyant, fby-buoyant, fbz-buoyant\n"
        "forces/fbx-total, fby-total, fbz-total sum (used by Accelerations)\n"
        "moments/l-aero, m-aero, n-aero\n"
        "moments/l-prop, m-prop, n-prop\n"
        "moments/l-gear, m-gear, n-gear\n"
        "moments/l-total, m-total, n-total")

    heading("Прискорення", 1, story)
    code(
        "accelerations/udot-ft_sec2, vdot-ft_sec2, wdot-ft_sec2\n"
        "accelerations/pdot-rad_sec2, qdot-rad_sec2, rdot-rad_sec2\n"
        "accelerations/a-pilot-x-ft_sec2        at the EYEPOINT\n"
        "accelerations/n-pilot-x-norm           load factor at EYEPOINT, g\n"
        "accelerations/Nz                       normal load factor")

    heading("Команди та положення FCS", 1, story)
    code(
        "fcs/elevator-cmd-norm                  -1..+1 from pilot/script\n"
        "fcs/aileron-cmd-norm\n"
        "fcs/rudder-cmd-norm\n"
        "fcs/pitch-trim-cmd-norm\n"
        "fcs/roll-trim-cmd-norm\n"
        "fcs/yaw-trim-cmd-norm\n"
        "fcs/flap-cmd-norm\n"
        "fcs/throttle-cmd-norm[n]\n"
        "fcs/mixture-cmd-norm[n]\n"
        "fcs/elevator-pos-rad, fcs/elevator-pos-deg, fcs/elevator-pos-norm\n"
        "fcs/left-aileron-pos-rad, ...\n"
        "fcs/rudder-pos-rad, ...\n"
        "fcs/flap-pos-deg, fcs/flap-pos-norm\n"
        "fcs/speedbrake-pos-rad\n"
        "fcs/left-brake-cmd-norm, right-brake, center-brake\n"
        "fcs/steer-cmd-norm")

    heading("Силова установка", 1, story)
    code(
        "propulsion/engine[n]/thrust-lbs\n"
        "propulsion/engine[n]/fuel-flow-rate-pps        per-second\n"
        "propulsion/engine[n]/fuel-flow-rate-gph\n"
        "propulsion/engine[n]/n1, n2                    turbine spool speeds\n"
        "propulsion/engine[n]/rpm                       prop or piston rpm\n"
        "propulsion/engine[n]/torque-lbsft\n"
        "propulsion/engine[n]/power-hp                  piston\n"
        "propulsion/engine[n]/map-inhg                  manifold pressure\n"
        "propulsion/engine[n]/egt-degf                  exhaust temp\n"
        "propulsion/engine[n]/cht-degf                  cylinder head\n"
        "propulsion/engine[n]/oil-pressure-psi\n"
        "propulsion/engine[n]/oil-temp-degf\n"
        "propulsion/tank[n]/contents-lbs, capacity-lbs\n"
        "propulsion/total-fuel-lbs")

    heading("Керування симуляцією", 1, story)
    code(
        "simulation/do_simple_trim     1 = longitudinal trim, 2 = ground, ...\n"
        "simulation/do_trim            full trim mode\n"
        "simulation/reset              reset to initial conditions\n"
        "simulation/terminate          stop the script\n"
        "simulation/pause              freeze the model\n"
        "simulation/gravity-model      0 spherical, 1 WGS-84\n"
        "simulation/gravitational-torque   spacecraft tidal torque on/off\n"
        "simulation/notify-time-trigger\n"
        "simulation/randomseed")


def add_chapter_glossary(story):
    story.append(PageBreak())
    heading("Глосарій та покажчик позначень", 0, story)

    table_data = [
        ["Позначення", "Значення"],
        ["α (alpha)",      "Кут атаки — кут між зв’язаною віссю X та проєкцією відносного вітру на зв’язану площину X-Z."],
        ["β (beta)",       "Кут ковзання — кут між відносним вітром та зв’язаною площиною X-Z."],
        ["<font name='DejaVu'>α̇</font> (alphadot)",   "Швидкість зміни α в часі."],
        ["<font name='DejaVu'>q̄</font> (qbar)",       "Швидкісний напір, ½ρV²."],
        ["ρ (rho)",        "Густина атмосфери."],
        ["V<sub>t</sub>",   "Істинна повітряна швидкість (модуль швидкості відносно повітряної маси)."],
        ["V<sub>c</sub>",   "Приладова виправлена повітряна швидкість (приладова швидкість з поправкою на стисливість)."],
        ["V<sub>e</sub>",   "Еквівалентна повітряна швидкість (приладова швидкість з поправкою на густину)."],
        ["M",              "Число Маха, V<sub>t</sub>/a."],
        ["a",              "Швидкість звуку."],
        ["p, q, r",        "Кутові швидкості крену, тангажа, рискання в зв’язаній системі."],
        ["u, v, w",        "Складові поступальної швидкості в зв’язаній системі."],
        ["φ, θ, ψ",        "Кути Ейлера крену, тангажа, курсу (послідовність 3-2-1)."],
        ["γ (gamma)",       "Кут траєкторії польоту (додатний — набір висоти)."],
        ["S",              "Опорна площа крила."],
        ["b",              "Розмах крила."],
        ["<font name='DejaVu'>c̄</font> (cbar)",       "Середня аеродинамічна хорда."],
        ["AR",             "Видовження, b²/S."],
        ["e",              "Коефіцієнт ефективності Освальда (зазвичай 0.7-0.95)."],
        ["AERORP",          "Аеродинамічна опорна точка — початок відліку для аеродинамічних моментів."],
        ["VRP",            "Візуальна опорна точка — початок відліку, який використовують зовнішні переглядачі."],
        ["EYEPOINT",        "Положення очей пілота."],
        ["AGL",             "Над рівнем землі."],
        ["MSL",             "Середній рівень моря."],
        ["WGS-84",          "Всесвітня геодезична система 1984 — модель земного еліпсоїда, яку використовують GPS і JSBSim."],
        ["ECEF",            "Геоцентрична, пов’язана із Землею (обертається разом із планетою)."],
        ["ECI",             "Геоцентрична інерціальна (необертова)."],
        ["NED",             "Місцева дотична площина «північ-схід-вниз»."],
        ["LCP",             "Задача лінійної доповнюваності — формулювання тертя в контакті."],
        ["FDM",             "Модель динаміки польоту."],
        ["FCS",             "Система керування польотом."],
        ["IC",              "Початкові умови."],
        ["BSFC",            "Питома витрата пального на гальмівній потужності."],
        ["MAP",             "Абсолютний тиск у впускному колекторі (поршневі двигуни)."],
        ["N1, N2",          "Частоти обертання роторів низького та високого тиску (турбінні двигуни)."],
        ["TSFC",            "Питома витрата пального на одиницю тяги (турбіни)."],
        ["CFD",             "Обчислювальна гідрогазодинаміка."],
        ["RANS",            "Осереднені за Рейнольдсом рівняння Нав’є-Стокса."],
        ["URANS",           "Нестаціонарні RANS."],
        ["LES",             "Моделювання великих вихорів."],
        ["AVL",             "Athena Vortex Lattice (Drela)."],
        ["DATCOM",          "Довідник USAF з стійкості та керованості DATCOM."],
        ["POH",             "Посібник з льотної експлуатації."],
        ["TAS",             "Істинна повітряна швидкість (=V<sub>t</sub>)."],
        ["IAS",             "Приладова повітряна швидкість."],
        ["CAS",             "Приладова виправлена повітряна швидкість (=V<sub>c</sub>)."],
        ["EAS",             "Еквівалентна повітряна швидкість (=V<sub>e</sub>)."],
        ["KCAS / KTAS / KIAS",
            "Приладова виправлена/істинна/приладова повітряна швидкість у вузлах."],
    ]
    t = Table(wrap_table(table_data), colWidths=[3.0 * cm, 13.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    story.append(Spacer(1, 12))
    story.append(p(
        "<i>Кінець вичерпного довідника JSBSim.</i> Повідомлення про "
        "помилки та вдосконалення вітаються за адресою "
        "https://github.com/JSBSim-Team/jsbsim."))


# ============================================================================
# PART II — Extended theory chapters
# ============================================================================


def add_part_separator(story, label, title):
    """A title page introducing a part of the book."""
    story.append(PageBreak())
    story.append(Spacer(1, 60 * mm))
    story.append(Paragraph(label, ParagraphStyle(
        "PartLabel", fontName="DejaVu-Bold", fontSize=18,
        textColor=colors.HexColor("#1d5d9b"), alignment=TA_CENTER,
        spaceAfter=12)))
    story.append(Paragraph(title, ParagraphStyle(
        "PartTitle", fontName="DejaVu-Bold", fontSize=28,
        textColor=colors.HexColor("#0d3b66"), alignment=TA_CENTER,
        leading=34)))
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "Решта цього посібника переходить від практичних "
        "&quot;настанов&quot; Частини I до глибшого, підкріпленого "
        "посиланнями викладу математики, фізики, аеродинаміки, геодезії, "
        "силової установки та механізмів верифікації, які реалізує JSBSim. "
        "Читайте її послідовно, щоб побудувати повне уявлення, або "
        "користуйтеся нею як довідником, коли натрапите в Частині I на тему, "
        "яку хочете зрозуміти глибше.",
        ParagraphStyle("PartIntro", parent=BODY_STYLE,
                       alignment=TA_CENTER, fontSize=11, leading=15,
                       leftIndent=24 * mm, rightIndent=24 * mm)))


# ----------------------------------------------------------------------------
def add_ext_math_fundamentals(story):
    story.append(PageBreak())
    heading("Математика для динаміки польоту", 0, story)
    story.append(p(
        "Кожен рядок JSBSim — це по суті дії над тривимірними векторами, "
        "матрицями обертання, кватерніонами та тензором, що пов’язує їх "
        "усі разом, — тензором інерції. Цей розділ є стислим довідником "
        "із цих об’єктів. Ми передбачаємо знання математичного аналізу та "
        "основ лінійної алгебри; усе, що понад це, побудовано з нуля."))

    heading("Вектори у тривимірному просторі", 1, story)
    story.append(p(
        "Тривимірний вектор — це впорядкована трійка <b>v</b> = (v<sub>x</sub>, "
        "v<sub>y</sub>, v<sub>z</sub>). Центральними є дві операції:"))
    math("Dot product: &nbsp; <b>a</b>·<b>b</b> = a<sub>x</sub>b<sub>x</sub>"
         " + a<sub>y</sub>b<sub>y</sub> + a<sub>z</sub>b<sub>z</sub> = "
         "|<b>a</b>||<b>b</b>| cos θ")
    math("Cross product: &nbsp; (<b>a</b>×<b>b</b>)<sub>i</sub> = "
         "ε<sub>ijk</sub> a<sub>j</sub> b<sub>k</sub>; &nbsp;"
         "|<b>a</b>×<b>b</b>| = |<b>a</b>||<b>b</b>| sin θ")
    story.append(p(
        "Скалярний добуток є скаляром; векторний добуток є вектором, "
        "перпендикулярним до обох операндів. Обидва реалізовано у "
        "вихідному коді JSBSim як перевантаження "
        "<font face='Courier'>FGColumnVector3</font>."))
    story.append(p(
        "<b>Мішаний добуток.</b> Мішаний (скалярно-векторний) добуток "
        "<b>a</b> · (<b>b</b> × <b>c</b>) дорівнює орієнтованому об’ємові "
        "паралелепіпеда, побудованого на трьох векторах. Подвійний "
        "векторний добуток задовольняє тотожність "
        "<b>a</b> × (<b>b</b> × <b>c</b>) = (<b>a</b>·<b>c</b>)<b>b</b> − "
        "(<b>a</b>·<b>b</b>)<b>c</b> — тотожність «BAC-CAB», що "
        "використовується в кінематиці твердого тіла."))
    story.append(p(
        "<b>Проєкція.</b> Складова вектора <b>a</b> вздовж одиничного "
        "вектора <b><font name='DejaVu'>n̂</font></b> дорівнює <b>a</b>·<b><font name='DejaVu'>n̂</font></b>; векторна проєкція дорівнює "
        "(<b>a</b>·<b><font name='DejaVu'>n̂</font></b>)<b><font name='DejaVu'>n̂</font></b>. Це використовується для виділення складових "
        "сили опору вздовж напрямку відносного вітру, нормальних сил "
        "уздовж нормалі до еліпсоїда тощо."))

    heading("Матриці обертання в SO(3)", 1, story)
    story.append(p(
        "Матриця обертання <b>R</b> ∈ SO(3) — це дійсна матриця 3×3 із "
        "<b>R</b><sup>T</sup><b>R</b> = <b>I</b> (ортогональна) та "
        "det(<b>R</b>) = +1 (власна, без віддзеркалення). Звідси два "
        "наслідки:"))
    for b in [
        "Обернення тривіальне: <b>R</b><sup>−1</sup> = <b>R</b><sup>T</sup>. "
        "JSBSim ніколи не обчислює чисельне обернення матриці обертання.",
        "Композиція — це множення матриць: обертання на <b>R<sub>1</sub></b> "
        "з наступним <b>R<sub>2</sub></b> дорівнює <b>R<sub>2</sub></b><b>R<sub>1</sub></b>. "
        "Композиція є некомутативною.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Три елементарні обертання навколо зв’язаних осей є будівельними "
        "блоками будь-якої аерокосмічної угоди про кути Ейлера:"))
    code(
        "         | 1   0     0   |          |  cθ   0   sθ |          | cψ -sψ  0 |\n"
        "R_x(φ) = | 0  cφ    sφ   |  R_y(θ)= |   0   1    0 |  R_z(ψ)= | sψ  cψ  0 |\n"
        "         | 0 -sφ    cφ   |          | -sθ   0   cθ |          |  0   0  1 |")
    story.append(p(
        "Зверніть увагу на угоду про знаки: ці матриці обертають "
        "<i>вектори</i> в активному сенсі (або, що еквівалентно, "
        "перетворюють <i>системи координат</i> у пасивному сенсі — JSBSim "
        "використовує пасивну угоду)."))

    heading("Аерокосмічна послідовність Ейлера 3-2-1", 1, story)
    story.append(p(
        "Кутове положення повітряного судна традиційно задається рисканням ψ, "
        "потім тангажем θ, потім креном φ, які застосовуються як власні "
        "обертання навколо Z, потім Y', потім X''. Об’єднана матриця, що "
        "перетворює вектор із місцевої системи NED у зв’язану систему, має "
        "вигляд"))
    math("R<sup>b</sup><sub>n</sub> = R<sub>x</sub>(φ) R<sub>y</sub>(θ) "
         "R<sub>z</sub>(ψ)")
    story.append(p(
        "Перемножена поелементно, вона дає класичну матрицю напрямних "
        "косинусів із дев’яти елементів, наведену в кожному аерокосмічному "
        "підручнику (Stevens &amp; Lewis, рівн. 1.4-7). Послідовність 3-2-1 "
        "має особливість при θ = ±90°, де ψ та φ уже не визначаються окремо, "
        "— це добре відомий ефект &quot;складання рамок&quot; (gimbal lock)."))

    heading("Тензор інерції", 1, story)
    story.append(p(
        "Для твердого тіла з неперервним розподілом маси ρ(<b>r</b>) тензор "
        "інерції відносно точки дорівнює"))
    math("<b>I</b> = ∫∫∫ ρ(<b>r</b>) (|<b>r</b>|²<b>1</b> − "
         "<b>r</b>⊗<b>r</b>) dV")
    story.append(p(
        "де <b>1</b> — одинична матриця 3×3, а ⊗ — зовнішній добуток. "
        "Поелементно діагональні члени (моменти інерції)"))
    math("I<sub>xx</sub> = ∫(y²+z²) dm; &nbsp; I<sub>yy</sub> = ∫(x²+z²) dm;"
         " &nbsp; I<sub>zz</sub> = ∫(x²+y²) dm")
    story.append(p(
        "та позадіагональні члени (відцентрові моменти інерції)"))
    math("I<sub>xy</sub> = ∫xy dm; &nbsp; I<sub>xz</sub> = ∫xz dm; &nbsp; "
         "I<sub>yz</sub> = ∫yz dm")
    story.append(p(
        "<b>Теорема Гюйгенса-Штейнера (про паралельні осі).</b> Якщо "
        "<b>I</b><sub>cg</sub> — тензор інерції відносно центра мас, то "
        "тензор інерції відносно точки, зміщеної на <b>d</b> від центра "
        "мас, дорівнює"))
    math("<b>I</b><sub>P</sub> = <b>I</b><sub>cg</sub> + m (|<b>d</b>|² "
         "<b>1</b> − <b>d</b>⊗<b>d</b>)")
    story.append(p(
        "<font face='Courier'>FGMassBalance</font> застосовує її на кожному "
        "кроці, щоб додати внесок інерції кожної точкової маси до тензора "
        "порожнього спорядженого судна."))
    story.append(p(
        "<b>Головні осі.</b> Діагоналізація <b>I</b> (яка є дійсною "
        "симетричною, а отже, ортогонально діагоналізовною) дає три "
        "<i>головні моменти інерції</i> вздовж трьох <i>головних осей</i>. "
        "Для повітряних суден із симетрією відносно площини x-z "
        "I<sub>xy</sub> = I<sub>yz</sub> = 0 за побудовою; I<sub>xz</sub> "
        "є ненульовим щоразу, коли верхня та нижня половини фюзеляжу "
        "масово незбалансовані (тобто завжди)."))

    heading("Перетворення тензора при обертанні", 1, story)
    story.append(p(
        "Вектори перетворюються як v' = <b>R</b>v. Тензор другого порядку, "
        "як-от матриця інерції, перетворюється як"))
    math("<b>I</b>' = <b>R</b> <b>I</b> <b>R</b><sup>T</sup>")
    story.append(p(
        "Саме так інерція в конструктивній системі, наведена в XML, "
        "повертається у зв’язану систему під час завантаження, а інерція у "
        "зв’язаній системі повертається у швидкісну (стійкісну) чи вітрову "
        "систему, коли це потрібно для аналізу похідних стійкості."))


# ----------------------------------------------------------------------------
def add_ext_quaternions_deep(story):
    story.append(PageBreak())
    heading("Кватерніони — теорія і практика", 0, story)
    story.append(p(
        "Кватерніони є основним робочим представленням обертань усередині "
        "<font face='Courier'>FGPropagate</font>. Читати цикл інтегрування "
        "JSBSim значно легше, якщо ви впевнено володієте відповідною "
        "алгеброю."))

    heading("Означення: H, алгебра кватерніонів", 1, story)
    story.append(p(
        "Кватерніони Гамільтона — це чотиривимірна дійсна алгебра, "
        "натягнута на 1, i, j, k з правилами множення"))
    math("i² = j² = k² = ijk = −1, &nbsp; ij = k, &nbsp; jk = i, &nbsp; "
         "ki = j")
    story.append(p(
        "Кватерніон — це q = q<sub>0</sub> + q<sub>1</sub>i + q<sub>2</sub>j"
        " + q<sub>3</sub>k, що часто записують як (q<sub>0</sub>, <b>q</b>), "
        "де q<sub>0</sub> — скалярна частина, а <b>q</b> = "
        "(q<sub>1</sub>,q<sub>2</sub>,q<sub>3</sub>) — векторна частина."))

    heading("Добуток Гамільтона", 1, story)
    math("p · q = (p<sub>0</sub>q<sub>0</sub> − <b>p</b>·<b>q</b>, &nbsp; "
         "p<sub>0</sub><b>q</b> + q<sub>0</sub><b>p</b> + <b>p</b>×<b>q</b>)")
    story.append(p(
        "Цей некомутативний добуток є серцем арифметики кватерніонів. Його "
        "реалізовано у <font face='Courier'>FGQuaternion::operator*</font>. "
        "<b>Застереження:</b> аерокосмічне програмне забезпечення поділене "
        "між угодою Гамільтона (яку використовують JSBSim, ROS, MATLAB "
        "Aerospace Toolbox) та угодою JPL (яку використовує космічне ПЗ JPL "
        "та NASA Goddard, із протилежним знаком члена з векторним добутком). "
        "Їх змішування міняє місцями ліво- та правобічні обертання — часте "
        "джерело помилок."))

    heading("Одиничні кватерніони та обертання", 1, story)
    story.append(p(
        "Одиничний кватерніон (|q| = 1) параметризує обертання. Відповідність "
        "«вісь-кут» має вигляд"))
    math("q = (cos(θ/2), <b><font name='DejaVu'>n̂</font></b> sin(θ/2))")
    story.append(p(
        "для обертання на кут θ навколо одиничної осі <b><font name='DejaVu'>n̂</font></b>. Вектор "
        "<b>v</b> обертається як уявна частина виразу"))
    math("v' = q v q*")
    story.append(p(
        "де v — чистий кватерніон (0, <b>v</b>), а q* = "
        "(q<sub>0</sub>, −<b>q</b>) — спряжений кватерніон. Еквівалентно, "
        "матриця напрямних косинусів (DCM), що відповідає q, дорівнює"))
    code(
        "       | q0²+q1²-q2²-q3²    2(q1q2 - q0q3)     2(q1q3 + q0q2) |\n"
        "R(q) = | 2(q1q2 + q0q3)    q0²-q1²+q2²-q3²    2(q2q3 - q0q1) |\n"
        "       | 2(q1q3 - q0q2)    2(q2q3 + q0q1)    q0²-q1²-q2²+q3² |")
    story.append(p(
        "Усередині метод <font face='Courier'>FGQuaternion::"
        "GetTransformationMatrix()</font> кешує цю DCM із дев’яти елементів, "
        "тож подальші перетворення систем зводяться до множення матриці на "
        "вектор."))

    heading("Кінематичне рівняння: <font name='DejaVu'>q̇</font> = ½ q ⊗ ω", 1, story)
    story.append(p(
        "Якщо кутова швидкість тіла (у зв’язаній системі) дорівнює ω, то "
        "кінематичне звичайне диференціальне рівняння для обертання з "
        "інерціальної системи у зв’язану має вигляд"))
    math("<font name='DejaVu'>q̇</font> = ½ q ⊗ (0, ω<sub>body</sub>)")
    story.append(p(
        "Геометрично: у кожну мить кватерніон рухається перпендикулярно до "
        "самого себе в чотиривимірному просторі, тож |q| є інваріантом при "
        "<i>точному</i> інтегруванні. Чисельні схеми втрачають цей "
        "інваріант і потребують або періодичної перенормалізації, або "
        "інтегратора, що зберігає структуру."))
    story.append(p(
        "<b>Інтегратори Бусса (Buss)</b> реалізують дискретні відображення, "
        "що зберігають структуру. Для сталого ω на проміжку [t, t+Δt] вираз"))
    math("q(t+Δt) = q(t) · exp(½ Δt ω) = q(t) · "
         "(cos(|ω|Δt/2), <b><font name='DejaVu'>ω̂</font></b> sin(|ω|Δt/2))")
    story.append(p(
        "є точним і зберігає одиничну норму з точністю до похибки чисел із "
        "рухомою комою. Buss-2 доповнює його коригувальним членом від <font name='DejaVu'>ω̇</font>, "
        "забезпечуючи другий порядок точності для несталого ω."))

    heading("Кватерніони проти кутів Ейлера проти DCM", 1, story)
    table_data = [
        ["Представлення", "Параметри", "Особливість", "Вартість", "Коли"],
        ["Ейлер 3-2-1", "3 (φ, θ, ψ)",
         "θ = ±90° (gimbal lock)",
         "Дешеве для відображення",
         "Індикація в кабіні, вивід"],
        ["Кватерніон",  "4 (q<sub>0</sub>..q<sub>3</sub>)",
         "Немає",
         "Компактний, швидкий",
         "Інтегрування, зберігання"],
        ["DCM",
         "9 (ортогональність марнує 6)",
         "Немає",
         "Дрейф; потрібна перенормалізація",
         "Перетворення систем"],
        ["Вектор обертання",
         "3 (θ <b><font name='DejaVu'>n̂</font></b>)",
         "Особлива при θ=2π",
         "Мінімальна",
         "Лінеаризовані збурення"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[3.4 * cm, 3.4 * cm, 3.6 * cm, 2.4 * cm, 3.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(p(
        "Архітектура JSBSim несе кватерніон як основний стан кутового "
        "положення (без особливості, чотири ступені вільності), кешує "
        "похідну від нього DCM (дешеві повторні перетворення систем) і надає "
        "вивід у кутах Ейлера лише на межі дерева властивостей."))


# ----------------------------------------------------------------------------
def add_ext_numerical_integration(story):
    story.append(PageBreak())
    heading("Чисельне інтегрування — теорія", 0, story)
    story.append(p(
        "Властивості <font face='Courier'>simulation/integrator/rate/"
        "rotational</font>, <font face='Courier'>position/rotational</font>, "
        "<font face='Courier'>rate/translational</font> та "
        "<font face='Courier'>position/translational</font> незалежно "
        "обирають чотири схеми. Знання базової чисельної теорії — це різниця "
        "між стійкою моделлю за <i>dt</i> = 1/120 с і моделлю, що "
        "розходиться, коли ви змінюєте <i>dt</i>."))

    heading("Однокрокові методи", 1, story)
    story.append(p(
        "Для задачі Коші ẏ = f(t, y), y(t<sub>0</sub>) = y<sub>0</sub>:"))
    math("Forward Euler: &nbsp; y<sub>n+1</sub> = y<sub>n</sub> + h f(t<sub>n</sub>, y<sub>n</sub>)")
    story.append(p(
        "Локальна похибка апроксимації O(h²), глобальна похибка O(h). "
        "Умовно стійкий: для тестового рівняння ẏ = λy потрібно "
        "|1 + hλ| &lt; 1, що для дійсного від’ємного λ означає h &lt; 2/|λ|."))
    math("Backward Euler: &nbsp; y<sub>n+1</sub> = y<sub>n</sub> + h f(t<sub>n+1</sub>, y<sub>n+1</sub>)")
    story.append(p(
        "Неявний, безумовно A-стійкий. Потребує розв’язання нелінійного "
        "рівняння на кожному кроці. Рідко використовується в моделюванні "
        "повітряних суден у реальному часі через обчислювальну вартість."))
    math("Trapezoidal (Heun, AM2): y<sub>n+1</sub> = y<sub>n</sub> + (h/2)"
         "[f(t<sub>n</sub>, y<sub>n</sub>) + f(t<sub>n+1</sub>, y<sub>n+1</sub>)]")
    story.append(p(
        "Неявний метод другого порядку; звичайною явною версією є форма "
        "«прогноз-корекція». Метод <font face='Courier'>eTrapezoidal</font> "
        "у JSBSim використовує «прогноз-корекцію» з попередньою похідною як "
        "прогнозом — фактично трапецієподібний на попередній похідній."))
    math("RK4: &nbsp; k<sub>1</sub> = f(t<sub>n</sub>, y<sub>n</sub>), &nbsp; "
         "k<sub>2</sub> = f(t<sub>n</sub>+h/2, y<sub>n</sub>+h k<sub>1</sub>/2), "
         "...&nbsp; y<sub>n+1</sub> = y<sub>n</sub> + h(k<sub>1</sub>+2k<sub>2</sub>+2k<sub>3</sub>+k<sub>4</sub>)/6")
    story.append(p(
        "Класичний метод Runge-Kutta 4 є золотим стандартом для роботи "
        "симуляторів, де віддають перевагу однокроковим методам. Має "
        "четвертий порядок точності, але потребує чотирьох обчислень функції "
        "на крок — це не те, що JSBSim використовує за замовчуванням."))

    heading("Багатокрокові методи: Adams-Bashforth", 1, story)
    story.append(p(
        "JSBSim реалізує явний метод Adams-Bashforth до 5-го порядку "
        "включно. Вони використовують одне обчислення функції на крок, але "
        "потребують початкових значень (які заповнюються методами нижчого "
        "порядку або повторними кроками Ейлера)."))
    code(
        "AB2:  y_{n+1} = y_n + h*(  3/2 f_n  -  1/2 f_{n-1} )\n"
        "AB3:  y_{n+1} = y_n + h*( 23/12 f_n - 16/12 f_{n-1} + 5/12 f_{n-2} )\n"
        "AB4:  y_{n+1} = y_n + h*( 55/24 f_n - 59/24 f_{n-1} + 37/24 f_{n-2}\n"
        "                          - 9/24 f_{n-3} )\n"
        "AB5:  y_{n+1} = y_n + h*( 1901/720 f_n - 2774/720 f_{n-1}\n"
        "                          + 2616/720 f_{n-2} - 1274/720 f_{n-3}\n"
        "                          + 251/720 f_{n-4} )")
    story.append(p(
        "Стандартні налаштування JSBSim — AB2 для поступальної швидкості, "
        "AB3 для поступального положення та прямокутний метод Ейлера для "
        "кватерніона (з подальшою перенормалізацією). Для плавної траєкторії "
        "повітряного судна це забезпечує збереження енергії та моменту "
        "імпульсу з точністю до ~10⁻⁶ упродовж прогонів тривалістю в тисячі "
        "секунд за <i>dt</i> = 1/120 с."))

    heading("Області стійкості та вибір кроку", 1, story)
    story.append(p(
        "Кожен інтегратор має <i>область абсолютної стійкості</i> в "
        "комплексній площині λh. Для рухів повітряного судна із власними "
        "значеннями λ порядку від −2 до +0,05 рад/с (короткоперіодичний рух, "
        "фугоїд, голландський крок) умови h &lt; 2/|λ<sub>max</sub>| ≈ 0,6 с "
        "достатньо для стійкості. Однак аеродинамічне збурення вносить "
        "швидкі рухи (смуга пропускання фільтрів запізнення СКУ, власні "
        "частоти стійок шасі 20-50 Гц), що на практиці підвищує вимогу до "
        "h ≲ 1/120 с."))
    story.append(p(
        "<b>Жорсткість.</b> Коли система має власні значення, що "
        "охоплюють багато порядків величини (повільні рухи польоту плюс "
        "швидкі рухи шасі/приводів), явні методи стають неефективними — вони "
        "змушені використовувати найменшу сталу часу. Неявні методи "
        "допомогли б; натомість JSBSim розв’язує жорсткі частини окремо (LCP "
        "для шасі, попередні фільтри для приводів), щоб явне інтегрування "
        "повільних рухів польоту залишалося стійким."))


# ----------------------------------------------------------------------------
def add_ext_newton_euler(story):
    story.append(PageBreak())
    heading("Динаміка твердого тіла Ньютона-Ейлера", 0, story)
    story.append(p(
        "Рівняння руху повітряного судна є окремим випадком механіки "
        "твердого тіла. Цей розділ виводить їх з нуля та показує, як JSBSim "
        "реалізує кожен член."))

    heading("Інерціальна форма (закони Ньютона)", 1, story)
    math("m <b>a</b><sub>i</sub> = <b>F</b>, &nbsp;&nbsp;&nbsp; "
         "d<b>H</b>/dt = <b>M</b>")
    story.append(p(
        "Кількість руху p = m<b>v</b><sub>i</sub> підпорядковується "
        "ṗ = <b>F</b>. Момент імпульсу відносно центра мас дорівнює "
        "<b>H</b> = <b>I</b><b>ω</b>; його похідна за часом в інерціальній "
        "системі дорівнює прикладеному моменту."))

    heading("Форма у зв’язаній системі через теорему про перенесення", 1, story)
    story.append(p(
        "Якщо вектор <b>q</b> виражено в системі, що обертається з кутовою "
        "швидкістю <b>ω</b>, то зв’язок між його похідними в інерціальній та "
        "відносно системи координат має вигляд"))
    math("(d<b>q</b>/dt)<sub>inertial</sub> = "
         "(d<b>q</b>/dt)<sub>body</sub> + <b>ω</b> × <b>q</b>")
    story.append(p(
        "Застосуймо до v<sub>body</sub> та до <b>H</b>:"))
    math("m(<b><font name='DejaVu'>v̇</font></b><sub>body</sub> + <b>ω</b> × <b>v</b><sub>body</sub>) = "
         "<b>F</b><sub>body</sub>")
    math("<b>I</b><b><font name='DejaVu'>ω̇</font></b> + <b>ω</b> × (<b>I</b><b>ω</b>) = <b>M</b><sub>body</sub>")
    story.append(p(
        "Це <font face='Courier'>FGAccelerations::CalculateUVWdot()"
        "</font> та <font face='Courier'>CalculatePQRdot()</font>, кожен по "
        "12 рядків арифметики. Член перехресного зв’язку "
        "<b>ω</b> × (<b>I</b><b>ω</b>) є джерелом гіроскопічних ефектів, "
        "зокрема знаменитої теореми про тенісну ракетку."))

    heading("Урахування обертання планети", 1, story)
    story.append(p(
        "Зв’язана система на Землі, що обертається, не є строго "
        "інерціальною. Записавши інерціальне прискорення через внески у "
        "зв’язаній та дотичній до ECEF системах і застосувавши теорему про "
        "перенесення двічі, отримуємо"))
    math("<b><font name='DejaVu'>v̇</font></b><sub>body</sub> + (<b>ω</b><sub>b/i</sub>) × <b>v</b><sub>body</sub>"
         " = <b>F</b>/m &minus; T<sub>i→b</sub>(<b>Ω</b><sub>p</sub> × <b>r</b><sub>i</sub>)·…")
    story.append(p(
        "Повна інерціальна форма, що включає коріолісові та відцентрові "
        "члени, інтегрується в інерціальній системі; "
        "<font face='Courier'>FGPropagate</font> зберігає "
        "<font face='Courier'>vInertialPosition</font> та "
        "<font face='Courier'>vInertialVelocity</font> і перетворює їх у "
        "зв’язану систему для виводу."))

    heading("Спрощення, специфічні для повітряних суден", 1, story)
    for b in [
        "Симетрія відносно площини x-z: I<sub>xy</sub> = I<sub>yz</sub> = 0.",
        "Зв’язані осі координат збігаються з головними осями лише "
        "наближено; I<sub>xz</sub> ≠ 0, бо верхня та нижня половини "
        "фюзеляжу масово асиметричні.",
        "Усталений політ: <b><font name='DejaVu'>v̇</font></b><sub>body</sub> = 0, <b><font name='DejaVu'>ω̇</font></b> = 0; "
        "F та M зводяться до нуля (умова балансування).",
        "Лінеаризація навколо точки балансування дає поздовжню "
        "(u, w, q, θ) та бічно-курсову (v, p, r, φ, ψ) розв’язані "
        "у просторі станів системи, які використовуються для аналізу "
        "стійкості.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_ext_fluid_mechanics(story):
    story.append(PageBreak())
    heading("Основи механіки рідин і газів", 0, story)
    story.append(p(
        "Усі аеродинамічні коефіцієнти, які споживає JSBSim, походять із "
        "фізики, що зрештою ґрунтується на рівняннях Нав’є-Стокса. Цей "
        "розділ є містком від рівнянь суцільного середовища до інженерних "
        "величин."))

    heading("Закони збереження", 1, story)
    math("Continuity: &nbsp; ∂ρ/∂t + ∇·(ρ<b>V</b>) = 0")
    math("Momentum: &nbsp; ρ(∂<b>V</b>/∂t + <b>V</b>·∇<b>V</b>) = "
         "−∇p + ∇·τ + ρ<b>g</b>")
    math("Energy: &nbsp; ρ(∂e/∂t + <b>V</b>·∇e) = "
         "−p ∇·<b>V</b> + Φ + ∇·(k∇T) + Q̇")
    story.append(p(
        "із ньютонівським в’язким напруженням "
        "τ<sub>ij</sub> = μ(∂u<sub>i</sub>/∂x<sub>j</sub> + "
        "∂u<sub>j</sub>/∂x<sub>i</sub>) − (2/3)μδ<sub>ij</sub>∇·<b>V</b>. "
        "Система замикається рівнянням стану p = ρRT (калорично досконалий "
        "газ)."))

    heading("Безрозмірні числа", 1, story)
    table_data = [
        ["Число", "Означення", "Фізичний зміст"],
        ["Рейнольдса Re",  "ρVL/μ = VL/ν",
         "Інерційні / в’язкі сили; визначає пограничний шар"],
        ["Маха M",
         "V/a, &nbsp; a = √(γRT)",
         "Стисливість; M&lt;0,3 нестислива течія"],
        ["Кнудсена Kn",
         "λ/L",
         "Застосовність суцільного середовища; Kn&lt;0,01 прийнятно"],
        ["Прандтля Pr",
         "μc<sub>p</sub>/k",
         "Товщина імпульсного проти теплового пограничного шару"],
        ["Струхаля St",
         "fL/V",
         "Відношення нестаціонарного до конвективного масштабу часу"],
        ["Фруда Fr",
         "V/√(gL)",
         "Інерційні / гравітаційні сили (вільна поверхня)"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[3.0 * cm, 4.0 * cm, 9.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(p(
        "Типові аерокосмічні діапазони: Re для БпЛА на малій висоті "
        "становить 10⁵-10⁶, для літака авіації загального призначення "
        "10⁶-10⁷, для транспортного 10⁷-10⁸. Число Маха коливається від "
        "0,05 (малий БпЛА) до 2,5+ (винищувач); навколозвуковий діапазон "
        "(0,8-1,2) є найскладнішим чисельно."))

    heading("Пограничні шари", 1, story)
    story.append(p(
        "Prandtl (1904) помітив, що за великих Re в’язкість має значення "
        "лише в тонкому шарі товщиною δ біля поверхні. Рівняння "
        "пограничного шару є спрощеною формою рівнянь Нав’є-Стокса:"))
    math("∂u/∂x + ∂v/∂y = 0, &nbsp; "
         "u ∂u/∂x + v ∂u/∂y = −(1/ρ)dp/dx + ν ∂²u/∂y², &nbsp; "
         "∂p/∂y ≈ 0")
    story.append(p(
        "Тиск задається ззовні із зовнішньої незв’язкої течії. Розв’язок "
        "Блазіуса (Blasius) для плоскої пластини за нульового градієнта "
        "тиску дає закон ламінарного зростання δ ≈ 5.0 x/√Re<sub>x</sub> та "
        "місцеве поверхневе тертя C<sub>f</sub> ≈ 0.664/√Re<sub>x</sub>."))
    story.append(p(
        "<b>Турбулентний перехід</b> на гладкій плоскій пластині за "
        "нульового градієнта настає поблизу Re<sub>x</sub> ≈ 5×10⁵, але "
        "вкрай чутливий до турбулентності набігаючого потоку, шорсткості та "
        "градієнта тиску. Аеродинамічні профілі масштабу БпЛА за Re &lt; "
        "5×10⁵ часто мають бульбашки ламінарного відриву, що домінують у "
        "полярі."))
    story.append(p(
        "<b>Турбулентний профіль</b>: u<sup>+</sup> = (1/κ) ln y<sup>+</sup>"
        " + B у логарифмічному шарі, де κ ≈ 0,41 та B ≈ 5,0. RANS-розрахунок "
        "CFD має розв’язувати y<sup>+</sup> &lt; 1 у першій комірці для "
        "аналізу з роздільною здатністю біля стінки."))

    heading("Відрив, зрив і закритичні режими", 1, story)
    story.append(p(
        "Потік відривається, коли дотичне напруження на стінці зникає під "
        "дією несприятливого градієнта тиску. На аеродинамічному профілі це "
        "відбувається при куті зриву α<sub>stall</sub>, за яким піднімальна "
        "сила падає, а сила опору зростає. Три механізми зриву (залежно від "
        "товщини профілю):"))
    for b in [
        "<b>Зрив із задньої кромки</b> (товсті профілі &gt;15% t/c): "
        "відрив повзе вгору за потоком від задньої кромки; плавний злам "
        "піднімальної сили.",
        "<b>Зрив із передньої кромки</b> (середні 9-15% t/c): "
        "коротка бульбашка ламінарного відриву лопає; різкий злам "
        "піднімальної сили.",
        "<b>Зрив тонкого профілю</b> (&lt;8% t/c): довга бульбашка "
        "росте та знову прилягає далі за потоком; крива піднімальної сили "
        "сплощується перед зламом.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Елемент <font face='Courier'>&lt;hysteresis_limits&gt;</font> у "
        "<font face='Courier'>&lt;aerodynamics&gt;</font> у JSBSim явно "
        "реалізує гістерезис повторного прилягання потоку після зриву."))


# ----------------------------------------------------------------------------
def add_ext_lift_theory(story):
    story.append(PageBreak())
    heading("Теорія виникнення піднімальної сили", 0, story)

    heading("Бернуллі — не відповідь (а рівний час проходження хибний)", 1, story)
    story.append(p(
        "Рівняння Бернуллі вздовж лінії течії нестисливого незв’язкого "
        "усталеного потоку має вигляд"))
    math("p + ½ρV² + ρgz = const")
    story.append(p(
        "Воно є <b>наслідком</b> збереження кількості руху, а не причиною "
        "піднімальної сили. Популярне пояснення про &quot;рівний час "
        "проходження&quot; — нібито повітря над верхньою поверхнею має "
        "пройти її за той самий час, що й повітря знизу, — емпірично хибне; "
        "досліди з димовими лініями показують, що повітря над верхньою "
        "поверхнею досягає задньої кромки значно раніше. Справжньою причиною "
        "асиметрії тиску є <i>циркуляція</i>, встановлена умовою Кутта."))

    heading("Кутта-Жуковський: правильна відповідь", 1, story)
    math("L' = ρ<sub>∞</sub> V<sub>∞</sub> Γ")
    story.append(p(
        "Для двовимірної незв’язкої нестисливої течії навколо будь-якого "
        "замкненого тіла піднімальна сила на одиницю розмаху дорівнює "
        "добутку густини, швидкості набігаючого потоку та циркуляції "
        "Γ = ∮<b>V</b>·d<b>s</b>. Сила опору в цій моделі дорівнює нулю "
        "(парадокс Д’Аламбера); в’язкість повертає опір і однозначно "
        "визначає Γ через умову Кутта (плавний схід потоку з гострої "
        "задньої кромки)."))

    heading("Теорія тонкого профілю", 1, story)
    story.append(p(
        "Для тонкого профілю похила кривої піднімальної сили дає відомий "
        "результат"))
    math("dC<sub>l</sub>/dα = 2π &nbsp;(per radian) &nbsp;≈ 0.110 /deg")
    story.append(p(
        "а аеродинамічний фокус (точка нульового моменту тангажа за α) "
        "розташований на чверті хорди. Кривина зміщує кут нульової "
        "піднімальної сили α<sub>L=0</sub>, але не змінює похилу."))

    heading("Крила скінченного розмаху: несна лінія Прандтля", 1, story)
    story.append(p(
        "Крило скінченного розмаху скидає за собою завихреність, що "
        "наводить скіс потоку, нахиляючи місцевий вектор піднімальної сили "
        "назад (індуктивний опір) і зменшуючи ефективний кут атаки. Теорія "
        "несної лінії Прандтля замінює крило приєднаним вихором з "
        "інтенсивністю Γ(y) та пеленою вільних вихорів. Класичні "
        "результати:"))
    math("C<sub>L</sub> = π · AR · A<sub>1</sub>, &nbsp; "
         "C<sub>D,i</sub> = C<sub>L</sub>² / (π · AR · e)")
    story.append(p(
        "з коефіцієнтом ефективності розмаху e ≤ 1 (e = 1 для еліптичного "
        "розподілу навантаження — розподілу з мінімальним індуктивним "
        "опором). Сучасні повітряні судна використовують вінглети та "
        "оптимізацію розподілу навантаження за розмахом, щоб наблизитися до "
        "e ≈ 0,9-0,95."))
    story.append(p(
        "Похила кривої піднімальної сили крила скінченного розмаху:"))
    math("dC<sub>L</sub>/dα = a<sub>0</sub> / (1 + a<sub>0</sub>/(π·AR·e))")
    story.append(p(
        "де a<sub>0</sub> ≈ 2π — похила профілю у двовимірному перерізі. "
        "Для AR=8, e=0,85 це дає dC<sub>L</sub>/dα ≈ 4,9/рад — приблизно на "
        "20% менше за значення 2π, яке мало б крило нескінченного розмаху."))

    heading("Поправка на стисливість", 1, story)
    math("C<sub>L,M</sub> = C<sub>L,inc</sub> / √(1 − M<sub>∞</sub>²) &nbsp;"
         "(Prandtl-Glauert)")
    story.append(p(
        "Дійсна до M ≈ 0,7. За цим значенням домінують утворення стрибка "
        "ущільнення та місцева навколозвукова задача; M<sub>crit</sub> "
        "(де місцеве число Маха вперше досягає 1) для транспортних профілів "
        "зазвичай настає при M<sub>∞</sub> ≈ 0,7-0,8."))


# ----------------------------------------------------------------------------
def add_ext_drag_breakdown(story):
    story.append(PageBreak())
    heading("Сила опору — повний розклад", 0, story)
    math("C<sub>D</sub> = C<sub>D,f</sub> + C<sub>D,p</sub> + "
         "C<sub>D,i</sub> + C<sub>D,int</sub> + C<sub>D,w</sub>")
    story.append(p(
        "П’ять адитивних джерел на дозвукових швидкостях. Кожне задається "
        "окремою XML-функцією в JSBSim і кожне походить від іншого фізичного "
        "механізму."))

    heading("Поверхневе тертя (шкідливий опір)", 1, story)
    story.append(p(
        "Турбулентне поверхневе тертя на плоскій пластині (ESDU/Schlichting):"))
    math("C<sub>f</sub> ≈ 0.455 / (log<sub>10</sub> Re<sub>L</sub>)<sup>2.58</sup>")
    story.append(p(
        "Модифікується коефіцієнтом форми FF для кривини та коефіцієнтом "
        "інтерференції Q для з’єднань компонентів. У сумі по змочуваній "
        "площі D<sub>f</sub> = q ∑ C<sub>f,i</sub> FF<sub>i</sub> "
        "Q<sub>i</sub> S<sub>wet,i</sub>."))

    heading("Опір форми (тиску)", 1, story)
    story.append(p(
        "Результат потовщення пограничного шару та помірного відриву, що "
        "перешкоджає повному відновленню тиску в задній частині тіла до "
        "значення в точці гальмування. Разом із поверхневим тертям це "
        "становить <i>профільний опір</i>. C<sub>D,f</sub> + C<sub>D,p</sub> "
        "об’єднуються в C<sub>D0</sub> для поляри."))

    heading("Індуктивний опір (зумовлений піднімальною силою)", 1, story)
    math("C<sub>D,i</sub> = C<sub>L</sub>² / (π · AR · e)")
    story.append(p(
        "Зростає квадратично з C<sub>L</sub>. Коефіцієнт ефективності "
        "розмаху e становить від 0,7 до 0,95 для звичайних крил; "
        "коефіцієнт ефективності Освальда e<sub>0</sub> (який поглинає інші "
        "ефекти, пропорційні C<sub>L</sub>²) використовується в стандартній "
        "параболічній полярі."))

    heading("Опір інтерференції", 1, story)
    story.append(p(
        "З’єднання між компонентами (крило-фюзеляж, пілон-крило) "
        "створюють додатковий вихровий та зумовлений тиском опір. ESDU та "
        "Hoerner наводять емпіричні коефіцієнти Q, зазвичай 1,0-1,3."))

    heading("Хвильовий опір", 1, story)
    story.append(p(
        "Понад критичним числом Маха M<sub>crit</sub> потік місцево "
        "прискорюється до M=1 і утворюється стрибок ущільнення. Взаємодія "
        "стрибка з пограничним шаром дає хвильовий опір, що швидко зростає "
        "після числа Маха дивергенції опору M<sub>DD</sub>:"))
    math("ΔC<sub>D,wave</sub> ≈ 20(M − M<sub>DD</sub>)<sup>4</sup>")
    story.append(p(
        "(правило четвертого степеня Лока). Надзвуковий мінімальний "
        "хвильовий опір досягається тілом обертання Сірса-Хаака (Sears-Haack) "
        "(правило площ, Whitcomb)."))

    heading("Параболічна поляра опору та максимальна аеродинамічна якість L/D", 1, story)
    math("C<sub>D</sub> = C<sub>D0</sub> + k C<sub>L</sub>², &nbsp; "
         "k = 1/(π·AR·e)")
    story.append(p(
        "Максимальна якість L/D досягається при "
        "C<sub>L</sub><sup>*</sup> = √(C<sub>D0</sub>/k), "
        "C<sub>D</sub><sup>*</sup> = 2 C<sub>D0</sub>:"))
    math("(L/D)<sub>max</sub> = 1 / (2 √(k · C<sub>D0</sub>))")
    story.append(p(
        "Типові значення: планер 40-60, реактивний транспортний літак "
        "17-22, малий БпЛА 8-14, Wright Flyer 1903 ≈ 8,3 (Anderson)."))


# ----------------------------------------------------------------------------
def add_ext_stability_control(story):
    story.append(PageBreak())
    heading("Стійкість і керованість — повна таблиця похідних", 0, story)

    heading("Угоди про знаки та означення", 1, story)
    for b in [
        "<b>Поздовжня статична стійкість</b>: dC<sub>m</sub>/dα &lt; 0. "
        "Еквівалентно розташуванню центра мас попереду нейтральної точки.",
        "<b>Курсова (флюгерна) стійкість</b>: "
        "dC<sub>n</sub>/dβ &gt; 0. Праве ковзання дає момент на ніс "
        "праворуч, повертаючи ніс до вітру.",
        "<b>Бічна стійкість (ефект поперечного V)</b>: "
        "dC<sub>l</sub>/dβ &lt; 0. Праве ковзання дає лівий момент крену, "
        "піднімаючи навітряне крило.",
    ]:
        story.append(bullet(b))

    heading("Повна таблиця похідних", 1, story)
    table_data = [
        ["Сила/Момент", "α / <font name='DejaVu'>α̇</font>", "Кутова швидкість", "Керування"],
        ["C<sub>L</sub>",   "C<sub>Lα</sub>, C<sub>L<font name='DejaVu'>α̇</font></sub>",
         "C<sub>Lq</sub>",  "C<sub>Lδe</sub>, C<sub>Lδf</sub>"],
        ["C<sub>D</sub>",   "C<sub>Dα</sub> (≈2k·C<sub>L</sub>·C<sub>Lα</sub>)",
         "—", "C<sub>Dδe</sub>, C<sub>Dδf</sub>, C<sub>Dgear</sub>"],
        ["C<sub>Y</sub>",   "C<sub>Yβ</sub>",
         "C<sub>Yp</sub>, C<sub>Yr</sub>", "C<sub>Yδa</sub>, C<sub>Yδr</sub>"],
        ["C<sub>l</sub> (крен)", "C<sub>lβ</sub>",
         "C<sub>lp</sub>, C<sub>lr</sub>",
         "C<sub>lδa</sub>, C<sub>lδr</sub>"],
        ["C<sub>m</sub> (тангаж)", "C<sub>mα</sub>, C<sub>m<font name='DejaVu'>α̇</font></sub>",
         "C<sub>mq</sub>", "C<sub>mδe</sub>"],
        ["C<sub>n</sub> (рискання)",  "C<sub>nβ</sub>",
         "C<sub>np</sub>, C<sub>nr</sub>",
         "C<sub>nδr</sub>, C<sub>nδa</sub>"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[3.6 * cm, 4.0 * cm, 4.0 * cm, 4.8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(p(
        "Похідні демпфування зведено до безрозмірного вигляду через "
        "b/(2V) (бічні) або <font name='DejaVu'>c̄</font>/(2V) (поздовжні). Похідна за <font name='DejaVu'>α̇</font> "
        "враховує запізнення скосу потоку між крилом і хвостовим оперенням. "
        "C<sub>nδa</sub> — це &quot;зворотне рискання&quot;: позитивна "
        "команда на елерони викликає рискання у бік, протилежний до "
        "наміченого напрямку повороту, через диференціальний опір на "
        "відхилених елеронах."))

    heading("Нейтральна точка та запас статичної стійкості", 1, story)
    math("x<sub>NP</sub> = x<sub>AC,wing</sub> − (<font name='DejaVu'>q̄</font>·S<sub>h</sub>/<font name='DejaVu'>q̄</font>·S) · "
         "(C<sub>Lα,h</sub>/C<sub>Lα</sub>) · l<sub>h</sub> / <font name='DejaVu'>c̄</font>")
    story.append(p(
        "Запас статичної стійкості: SM = (x<sub>NP</sub> − x<sub>CG</sub>) / "
        "<font name='DejaVu'>c̄</font>. У цивільних транспортних літаків SM ≈ 5-15%; "
        "винищувачі можуть мати від’ємний SM з активним законом керування "
        "(ослаблена статична стійкість)."))

    heading("Маневрена точка", 1, story)
    story.append(p(
        "Положення центра мас, за якого dC<sub>m</sub>/dn<sub>z</sub> = 0 "
        "в усталеному виході з пікірування. Розташована позаду x<sub>NP</sub> "
        "приблизно на ρ S <font name='DejaVu'>c̄</font> C<sub>mq</sub> / (4 m), що зміщує "
        "x<sub>MP</sub> на кілька відсотків <font name='DejaVu'>c̄</font> позаду x<sub>NP</sub> "
        "для типових транспортних літаків."))


# ----------------------------------------------------------------------------
def add_ext_eigenmodes(story):
    story.append(PageBreak())
    heading("Власні рухи повітряного судна та лінеаризація", 0, story)

    heading("Лінеаризація навколо балансування", 1, story)
    story.append(p(
        "Збурення Δu, Δw, Δq, Δθ навколо балансування з U<sub>0</sub>, Θ<sub>0</sub>:"))
    code(
        "m Δu̇  = X_u Δu + X_w Δw - m g cosΘ_0 Δθ + ΔX_ctrl\n"
        "m Δẇ  = Z_u Δu + Z_w Δw + (m U_0 + Z_q) Δq - m g sinΘ_0 Δθ + ΔZ_ctrl\n"
        "I_y Δq̇ = M_u Δu + M_w Δw + M_w_dot Δẇ + M_q Δq + ΔM_ctrl\n"
        "Δθ̇   = Δq")
    story.append(p(
        "Бічно-курсова підсистема — це [Δv, Δp, Δr, Δφ], керована "
        "Y<sub>v</sub>, Y<sub>p</sub>, Y<sub>r</sub>, L<sub>v</sub>, "
        "L<sub>p</sub>, L<sub>r</sub>, N<sub>v</sub>, N<sub>p</sub>, "
        "N<sub>r</sub>. У першому наближенні за симетричного балансування "
        "ці дві підсистеми розв’язуються."))

    heading("Форма у просторі станів", 1, story)
    math("ẋ = Ax + Bu, &nbsp; y = Cx + Du")
    story.append(p(
        "Власні значення A дають рухи; власні вектори дають форму руху "
        "(які стани беруть участь у кожному русі). Властивість "
        "<font face='Courier'>simulation/do_linearization</font> у JSBSim "
        "виділяє A, B, C, D у точці балансування та записує їх у вивід "
        "log4cpp. Модуль Python надає те саме через "
        "<font face='Courier'>jsbsim.utils.linearize</font>."))

    heading("Поздовжні рухи", 1, story)
    story.append(p(
        "<b>Короткоперіодичний рух</b> — швидке коливання тангажа, "
        "переважно рух Δw та Δq, слабко залежний від Δu. Сильно "
        "задемпфований (ζ ≈ 0,3-0,7), ω<sub>n</sub> зазвичай 1-5 рад/с для "
        "транспортних літаків, 5-15 рад/с для винищувачів."))
    math("ω<sub>n,sp</sub>² ≈ Z<sub>α</sub>M<sub>q</sub>/V<sub>0</sub> − M<sub>α</sub>")
    math("2ζ<sub>sp</sub>ω<sub>n,sp</sub> ≈ −(M<sub>q</sub> + M<sub><font name='DejaVu'>α̇</font></sub> + Z<sub>α</sub>/V<sub>0</sub>)")
    story.append(p(
        "<b>Фугоїд</b> — повільний обмін кінетичної та потенціальної "
        "енергії: Δu та Δθ коливаються, Δw та Δq майже нульові. Слабко "
        "задемпфований (ζ ≈ 0,05) та повільний."))
    math("ω<sub>n,ph</sub> ≈ √2 · g / V<sub>0</sub> &nbsp;(Lanchester)")
    math("ζ<sub>ph</sub> ≈ (1/√2) · (C<sub>D</sub>/C<sub>L</sub>)")
    story.append(p(
        "Для пасажирського літака за V<sub>0</sub> = 250 м/с ω<sub>ph</sub> "
        "≈ 0,055 рад/с — період ≈ 115 с. L/D = 17 дає ζ<sub>ph</sub> ≈ "
        "0,041."))

    heading("Бічно-курсові рухи", 1, story)
    story.append(p(
        "<b>Рух крену</b> — першого порядку, сильно задемпфоване "
        "експоненційне згасання кутової швидкості крену:"))
    math("τ<sub>roll</sub> ≈ −I<sub>x</sub> / (<font name='DejaVu'>q̄</font>·S·b·C<sub>lp</sub>·b/(2V))")
    story.append(p(
        "Типове τ<sub>roll</sub> = 0,3-1,5 с. Сприймається пілотом як "
        "&quot;реакція за кутовою швидкістю&quot;."))
    story.append(p(
        "<b>Спіральний рух</b> — першого порядку, дуже повільний, часто "
        "трохи нестійкий. Власне значення близьке до нуля. Визначається "
        "відношенням ефекту поперечного V до флюгерної стійкості; стійкість "
        "вимагає"))
    math("C<sub>lβ</sub> · C<sub>nr</sub> &gt; C<sub>nβ</sub> · C<sub>lr</sub>")
    story.append(p(
        "<b>Голландський крок</b> — зв’язане коливання рискання-крену; "
        "повітряне судно &quot;виляє хвостом&quot;, водночас погойдуючи "
        "крилами зі зсувом фази 90°. Помірно задемпфований (ζ ≈ 0,05-0,3), "
        "ω<sub>n</sub> ≈ 0,5-3 рад/с для транспортних літаків."))
    math("ω<sub>n,DR</sub>² ≈ (<font name='DejaVu'>q̄</font>·S·b/I<sub>z</sub>) C<sub>nβ</sub>")
    math("2 ζ<sub>DR</sub> ω<sub>n,DR</sub> ≈ −(<font name='DejaVu'>q̄</font>·S·b²/(2V·I<sub>z</sub>)) "
         "C<sub>nr</sub>")
    story.append(p(
        "Голландський крок потребує демпфера рискання на транспортних "
        "повітряних суднах; власний рух зазвичай задемпфований надто слабко "
        "для комфорту пілота. СКУ в JSBSim керує цим за допомогою демпфера "
        "рискання з програмованим коефіцієнтом підсилення."))


# ----------------------------------------------------------------------------
def add_ext_airfoil_aerodynamics(story):
    story.append(PageBreak())
    heading("Аеродинаміка профілю", 0, story)

    heading("Сімейство профілів NACA", 1, story)
    story.append(p(
        "<b>4-значні</b> (NACA 2412): максимальна кривина 2% хорди, "
        "положення максимальної кривини 0,4c, максимальна товщина 12%."))
    story.append(p(
        "<b>5-значні</b> (NACA 23012): розрахунковий C<sub>L</sub> = 0,3, "
        "положення максимальної кривини 0,15c, максимальна товщина 12%."))
    story.append(p(
        "<b>6-значні</b> (NACA 64<sub>2</sub>-415, &quot;ламінарний&quot;): "
        "положення мінімального тиску на 0,4c, напівширина «ковша» малого "
        "опору за CL = 0,2, розрахунковий C<sub>L</sub> = 0,4, товщина 15%."))

    heading("Типові характеристики", 1, story)
    table_data = [
        ["Профіль",  "C<sub>L,max</sub>", "α<sub>stall</sub>",
         "C<sub>d,min</sub>", "C<sub>m,ac</sub>"],
        ["NACA 0012",   "1.45 (Re 3×10⁶)", "14°", "0.0060", "0.000"],
        ["NACA 2412",   "1.55",             "15°", "0.0065", "−0.045"],
        ["NACA 23012",  "1.70",             "18°", "0.0070", "−0.014"],
        ["NACA 65-415", "1.50",             "16°", "0.0045", "−0.075"],
        ["Selig S1223 (малі Re)", "2.20 (Re 2×10⁵)", "10°",
            "0.0150", "−0.27"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[4.0 * cm, 3.4 * cm, 2.3 * cm, 3.0 * cm, 3.7 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    heading("Вплив числа Рейнольдса на БпЛА", 1, story)
    story.append(p(
        "Нижче за Re ≈ 5×10⁵ домінують бульбашки ламінарного відриву, "
        "підвищуючи C<sub>d,min</sub> та знижуючи C<sub>L,max</sub>. БпЛА за "
        "Re ≈ 10⁵-3×10⁵ потребують спеціалізованих профілів для малих Re: "
        "Eppler 387, SD7037, Selig S1223. Аеродинамічні таблиці JSBSim для "
        "БпЛА мають відповідати експлуатаційному Re — не екстраполюйте від "
        "Re 10⁶ в аеродинамічній трубі до польотного Re 10⁵."))

    heading("Критичне число Маха", 1, story)
    math("C<sub>p</sub><sup>*</sup> = (2/γM<sub>∞</sub>²)[((1 + (γ−1)/2·M<sub>∞</sub>²)/(1 + (γ−1)/2))<sup>γ/(γ−1)</sup> − 1]")
    story.append(p(
        "M<sub>crit</sub> розв’язується одночасно з поправкою "
        "Prandtl-Glauert Cp = Cp,min,inc / √(1 − M<sub>crit</sub>²). Число "
        "Маха дивергенції опору M<sub>DD</sub> &gt; M<sub>crit</sub>, "
        "визначається там, де dC<sub>D</sub>/dM = 0,1."))
    story.append(p(
        "<b>Надкритичні профілі</b> (серія NASA SC(2) Віткомба) "
        "підвищують M<sub>DD</sub> на 0,05-0,10 за тієї самої товщини або "
        "дозволяють на 30-60% більшу товщину за того самого M<sub>DD</sub> "
        "— що дає змогу робити конструктивно легші крила."))


# ----------------------------------------------------------------------------
def add_ext_cfd_methods(story):
    story.append(PageBreak())
    heading("Методи CFD — теорія і практика", 0, story)

    heading("Панельні методи", 1, story)
    story.append(p(
        "Для незв’язкої нестисливої течії (або з поправкою P-G) навколо "
        "довільних форм метод Хесса-Сміта (Hess-Smith) розподіляє джерела "
        "та диполі по панелях тіла і забезпечує умову непротікання. "
        "Складність O(N²) за кількістю панелей. Метод дипольної решітки "
        "(Albano-Rodden 1969) поширюється на нестаціонарну коливальну течію "
        "і є основним інструментом аналізу флатера."))

    heading("Вихрова решітка", 1, story)
    story.append(p(
        "Крила представлено підковоподібними вихорами на плоскій серединній "
        "поверхні, з вільними нитками, орієнтованими вздовж набігаючого "
        "потоку. Обчислює C<sub>L</sub>, індуктивний опір, розподіл "
        "навантаження за розмахом. AVL Марка Дрели (Mark Drela) є "
        "канонічним інструментом з відкритим кодом для попереднього "
        "проєктування та оцінювання похідних стійкості. Обмеження: без "
        "товщини, без в’язких ефектів, без стисливості понад P-G, без "
        "відриву."))

    heading("Моделі турбулентності RANS", 1, story)
    for b in [
        "<b>Spalart-Allmaras (1992)</b>: одне рівняння перенесення для "
        "модифікованої турбулентної в’язкості ν̃. Широко вживається у "
        "зовнішній аеродинаміці. Допускає вищі y<sup>+</sup> завдяки "
        "пристінній лінеаризації.",
        "<b>k-ε</b>: два рівняння. Погано працює за несприятливих градієнтів "
        "тиску та відриву; зазвичай потребує пристінних функцій.",
        "<b>k-ω SST (Menter, 1994)</b>: поєднує k-ω біля стінок з k-ε "
        "у віддаленому полі через зрощувальну функцію F1. Найкраща "
        "універсальна модель RANS для течій з відривом / несприятливим "
        "градієнтом тиску. Промисловий стандарт для механізації крила, "
        "крил, гвинтокрилих апаратів.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Роздільна здатність біля стінки: y<sup>+</sup> &lt; 1 у першій "
        "комірці, 30-40 комірок упоперек пограничного шару, коефіцієнт "
        "зростання за нормаллю до стінки &lt; 1,2."))

    heading("LES, DES, гібридні методи", 1, story)
    story.append(p(
        "<b>LES</b> розв’язує вихори аж до масштабу сітки; y<sup>+</sup> ≈ "
        "1 у всіх трьох напрямках, Δx<sup>+</sup>, Δz<sup>+</sup> ~ 50. "
        "Вартість ~ Re<sup>2.5</sup> для LES з роздільною здатністю біля "
        "стінки — неприйнятна за польотних Re."))
    story.append(p(
        "<b>DES/DDES/IDDES</b> (Spalart 1997): RANS у приєднаних "
        "пограничних шарах, LES у зонах відриву. Доступний за вартістю для "
        "течій з масштабним відривом (великі α, закритичні режими, відділення "
        "вантажу)."))

    heading("Валідаційні задачі", 1, story)
    story.append(p(
        "AGARD AR-303 та AR-138, NASA Turbulence Modeling Resource "
        "(turbmodels.larc.nasa.gov), механізація крила DLR-F6/F11, NASA "
        "Common Research Model (CRM), семінари HiLiftPW, семінари AIAA Drag "
        "Prediction Workshops 1-7. CFL3D, FUN3D та OVERFLOW є еталонними "
        "кодами."))


# ----------------------------------------------------------------------------
def add_ext_forced_oscillation(story):
    story.append(PageBreak())
    heading("Вимушені коливання та похідні демпфування", 0, story)

    heading("Постановка задачі", 1, story)
    story.append(p(
        "Накладаємо синусоїдальний рух із частотою ω. Для тангажа:"))
    math("α(t) = α<sub>0</sub> + Δα sin(ωt), &nbsp; q(t) = ωΔα cos(ωt)")
    story.append(p(
        "Часозалежний (time-accurate) CFD-розрахунок проходить ~5 циклів, "
        "щоб розсіяти початкові перехідні процеси; дані беруть із циклів 3-5. "
        "Найкраща практика: ≥100 кроків за часом на цикл, подвійне крокування "
        "за часом (dual time-stepping) із 30-50 внутрішніми ітераціями."))

    heading("Зведена частота", 1, story)
    math("k = ω L<sub>ref</sub> / (2 V<sub>∞</sub>)")
    story.append(p(
        "Відношення нестаціонарного й конвективного часових масштабів. "
        "k → 0 відповідає квазістаціонарному режиму (лише статичні похідні); "
        "k &gt; 0.05 враховує запізнення циркуляції та ефекти приєднаної маси. "
        "Типові вимушені коливання в CFD: k = 0.02-0.10."))

    heading("Виділення похідних", 1, story)
    math("C<sub>m</sub>(t) ≈ C<sub>m0</sub> + C<sub>mα</sub>Δα + "
         "(C<sub>mq</sub> + C<sub>m<font name='DejaVu'>α̇</font></sub>)(<font name='DejaVu'>c̄</font>/(2V))Δα·ω·cos(ωt)/sin(ωt)·... ")
    story.append(p(
        "Інтегрування за Фур’є на одному циклі:"))
    code(
        "C_mα   ≈ (1/(π Δα)) ∫₀^(2π/ω) C_m(t) sin(ωt) dt\n"
        "C_mq + C_mα̇ ≈ (1/(π k Δα)) ∫₀^(2π/ω) C_m(t) cos(ωt) dt")
    story.append(p(
        "Чисте демпфування C<sub>mq</sub> та запізнення за <font name='DejaVu'>α̇</font> "
        "C<sub>m<font name='DejaVu'>α̇</font></sub> неможливо розділити з одного коливання "
        "лише за тангажем; для цього потрібен вертикальний рух (plunge — зміна α "
        "за сталого q) або комбінований графік. Багато довідників публікують суму "
        "(C<sub>mq</sub> + C<sub>m<font name='DejaVu'>α̇</font></sub>) і розбивають "
        "її приблизно у співвідношенні 70/30."))


# ----------------------------------------------------------------------------
def add_ext_geodesy_wgs84(story):
    story.append(PageBreak())
    heading("Геодезія та еліпсоїд WGS-84", 0, story)
    story.append(p(
        "JSBSim інтегрує свої рівняння руху в інерціальній системі координат "
        "і перетворює результати до еліпсоїда WGS-84 для виведення. Цей розділ "
        "є довідником щодо геодезичних сталих і домовленостей."))

    heading("Визначальні сталі WGS-84", 1, story)
    table_data = [
        ["Символ", "Значення", "Опис"],
        ["a", "6 378 137.0 м (точно)", "Велика піввісь"],
        ["1/f", "298.257 223 563 (точно)", "Обернене стиснення"],
        ["GM",  "3.986 004 418 × 10¹⁴ м³/с²", "Гравітаційний параметр Землі"],
        ["ω",   "7.292 115 × 10⁻⁵ рад/с", "Кутова швидкість обертання Землі"],
        ["b",   "6 356 752.3142 м", "Мала піввісь, b = a(1−f)"],
        ["e²",  "6.694 379 990 14 × 10⁻³",
         "Перший ексцентриситет² = 2f − f²"],
        ["e'²", "6.739 496 742 28 × 10⁻³",
         "Другий ексцентриситет² = e²/(1−e²)"],
        ["J2",  "1.082 626 7 × 10⁻³",
         "Друга зональна гармоніка (ненормована)"],
        ["R<sub>V</sub>", "6 371 000.79 м", "Середній (об’ємний) радіус"],
        ["γ<sub>e</sub>", "9.780 325 м/с²", "Нормальна сила тяжіння на екваторі"],
        ["γ<sub>p</sub>", "9.832 185 м/с²", "Нормальна сила тяжіння на полюсі"],
        ["g<sub>0</sub>", "9.806 65 м/с²", "Стандартна сила тяжіння (за визначенням)"],
        ["Зоряна доба", "86 164.0905 с", "Тривалість зоряної доби"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[2.6 * cm, 4.8 * cm, 9.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    heading("Геодезична та геоцентрична широта", 1, story)
    math("tan(φ<sub>c</sub>) = (1 − e²) tan(φ<sub>g</sub>)")
    story.append(p(
        "Вони відрізняються до 11.55 кутової хвилини ≈ 0.19° поблизу φ = 45° — "
        "що відповідає 21.4 км відстані в напрямку північ-південь по поверхні Землі. "
        "В авіації завжди використовують геодезичну широту (GPS, карти, автопілоти). "
        "Внутрішні обчислення JSBSim іноді послуговуються геоцентричною; на виведенні "
        "присутні обидві."))

    heading("Означення висоти", 1, story)
    for b in [
        "<b>Еліпсоїдальна (геодезична) висота h</b> — знакова відстань до "
        "еліпсоїда WGS-84 уздовж нормалі до еліпсоїда. Власне виведення GPS.",
        "<b>Ортометрична висота H</b> — висота над геоїдом (еквіпотенціаль "
        "середнього рівня моря). Вода тече від високих H до низьких. Її "
        "використовують на картах.",
        "<b>Хвиля геоїда N</b> — h = H + N. У глобальному масштабі N ∈ [−105 м, "
        "+85 м] відносно WGS-84. EGM96/EGM2008 дають глобальні моделі геоїда.",
        "<b>Барометрична висота (pressure altitude)</b> — висота в ISA, на якій "
        "виникає виміряний тиск. Висотомір із налаштуванням 29.92 inHg.",
        "<b>Висота за густиною (density altitude)</b> — те саме поняття для густини. "
        "Прогнозує характеристики літака та двигуна.",
        "<b>Геопотенціальна висота</b> — H<sub>geopot</sub> = R·H<sub>geom</sub>/(R + H<sub>geom</sub>). "
        "Використовується моделлю стандартної атмосфери, щоб гідростатичне "
        "рівняння мало сталу g.",
    ]:
        story.append(bullet(b))

    heading("Радіуси кривини", 1, story)
    math("M(φ) = a(1−e²) / (1 − e² sin²φ)<sup>3/2</sup> &nbsp;(меридіан)")
    math("N(φ) = a / √(1 − e² sin²φ) &nbsp;(перший вертикал)")
    story.append(p(
        "На екваторі M = a(1−e²), N = a; на полюсі M = N = a/√(1−e²) "
        "≈ 6 399 593.6 м. Відстань на радіан: північ-південь M; схід-захід "
        "N cos φ. Одна кутова хвилина широти на екваторі дорівнює "
        "1843 м; одна морська миля становить точно 1852 м за визначенням."))


# ----------------------------------------------------------------------------
def add_ext_coord_transforms(story):
    story.append(PageBreak())
    heading("Перетворення координат докладно", 0, story)

    heading("Геодезичні → ECEF (замкнена форма)", 1, story)
    code(
        "x = (N + h) cos(φ) cos(λ)\n"
        "y = (N + h) cos(φ) sin(λ)\n"
        "z = (N (1 - e²) + h) sin(φ)\n"
        "where N(φ) = a / sqrt(1 - e² sin²φ)")
    story.append(p(
        "Три множення та один квадратний корінь. JSBSim застосовує це на кожному "
        "такті, щоб відобразити проінтегроване інерціальне положення в геодезичну "
        "трійку (широта, довгота, висота) для виведення."))

    heading("ECEF → геодезичні (ітерація Боврінга)", 1, story)
    code(
        "p = sqrt(x² + y²)\n"
        "φ_0 = atan2(z, p (1 - e²))\n"
        "repeat:\n"
        "    N_i = a / sqrt(1 - e² sin² φ_i)\n"
        "    h_i = p / cos(φ_i) - N_i\n"
        "    φ_{i+1} = atan2(z, p (1 - e² N_i / (N_i + h_i)))\n"
        "until |φ_{i+1} - φ_i| < 1e-12\n"
        "λ = atan2(y, x)")
    story.append(p(
        "Збіжність за 3 ітерації до 10⁻¹¹ рад ≈ 0.06 мм будь-де на "
        "Землі. Гейккінен (Heikkinen, 1982) та Олсон (Olson, 1996) дають "
        "беззітераційні замкнені альтернативи; метод Вермея (Vermeille, 2011) "
        "точний до нанометрів у межах 5000 км від еліпсоїда."))

    heading("Поворот ECEF → ECI", 1, story)
    code(
        "| x_ECI |   |  cos(θ)  -sin(θ)  0 |   | x_ECEF |\n"
        "| y_ECI | = |  sin(θ)   cos(θ)  0 | * | y_ECEF |\n"
        "| z_ECI |   |    0        0     1 |   | z_ECEF |")
    story.append(p(
        "θ — це середній зоряний час за Гринвічем (GMST). Для прецизійних задач "
        "його доповнюють прецесією P, нутацією N, рухом полюсів W: "
        "GCRF = P<sup>T</sup>N<sup>T</sup>R<sup>T</sup>W<sup>T</sup> · "
        "ITRF. Для авіасимуляції достатньо чистого повороту."))

    heading("ECEF → NED у точці (φ₀, λ₀)", 1, story)
    code(
        "                | -sin(φ₀)cos(λ₀)  -sin(φ₀)sin(λ₀)   cos(φ₀) |\n"
        "R_NED^ECEF =    | -sin(λ₀)           cos(λ₀)            0     |\n"
        "                | -cos(φ₀)cos(λ₀)  -cos(φ₀)sin(λ₀)  -sin(φ₀) |")
    story.append(p(
        "ENU отримують перестановкою перших двох рядків та зміною знаку "
        "третього. JSBSim кешує обидві матриці — NED-із-ECEF та ECEF-із-NED — "
        "на кожному такті."))

    heading("NED → зв’язана (3-2-1 Тейта-Брайана)", 1, story)
    math("R<sup>b</sup><sub>n</sub> = R<sub>x</sub>(φ) R<sub>y</sub>(θ) R<sub>z</sub>(ψ)")
    story.append(p(
        "У розгорнутому вигляді:"))
    code(
        "          | cθcψ                    cθsψ                   -sθ    |\n"
        "R_b_n =   | sφsθcψ - cφsψ           sφsθsψ + cφcψ          sφcθ  |\n"
        "          | cφsθcψ + sφsψ           cφsθsψ - sφcψ          cφcθ  |")
    story.append(p(
        "Сингулярність при θ = ±90° — це канонічне складання рамок (gimbal lock); "
        "саме тому JSBSim інтегрує кватерніонну форму і лише експортує "
        "кути Ейлера."))


# ----------------------------------------------------------------------------
def add_ext_earth_gravity(story):
    story.append(PageBreak())
    heading("Обертання Землі та сила тяжіння", 0, story)

    heading("Кутова швидкість обертання Землі та фіктивні сили", 1, story)
    story.append(p(
        "Обертова система ECEF є неінерціальною. Закон Ньютона набуває "
        "коріолісового та відцентрового доданків:"))
    math("<b>a</b><sub>inertial</sub> = <b>a</b><sub>ECEF</sub> + 2 <b>Ω</b> × <b>v</b> + <b>Ω</b> × (<b>Ω</b> × <b>r</b>)")
    story.append(p(
        "На крейсерському режимі M 0.8 (~250 м/с) на середніх широтах коріолісове "
        "прискорення становить ~0.036 м/с² (0.0037 g) — мале, але за нехтування "
        "ним воно накопичується у значні похибки курсу й траєкторії на масштабах "
        "годин польоту. Відцентровий доданок на екваторі становить ~0.034 м/с² "
        "назовні, що саме й пояснює, чому виміряна поверхнева сила тяжіння на "
        "екваторі (9.780 м/с²) менша за чисте гравітаційне притягання "
        "(9.814 м/с²). Відцентрову складову традиційно включають у модель "
        "сили тяжіння, тож у рівняннях руху явно лишається тільки коріолісова."))

    heading("Сферична сила тяжіння (проста)", 1, story)
    math("g(r) = GM / r² &nbsp;(радіальний напрямок назовні)")
    story.append(p(
        "На рівні моря r = 6 378 км, g ≈ 9.798 м/с². Достатня для багатьох "
        "авіасимуляцій; усталений варіант JSBSim."))

    heading("Нормальна сила тяжіння за Сомільяною (поверхня WGS-84)", 1, story)
    math("γ(φ) = γ<sub>e</sub> (1 + k sin²φ) / √(1 − e² sin²φ)")
    story.append(p(
        "де γ<sub>e</sub> = 9.7803254 м/с² та "
        "k = (b γ<sub>p</sub> − a γ<sub>e</sub>)/(a γ<sub>e</sub>) "
        "≈ 0.001932. Поправка вільного повітря (free-air) на висоту:"))
    math("γ(φ, h) ≈ γ(φ)[1 − (2/a)(1 + f + m − 2f sin²φ) h + (3/a²) h²]")
    story.append(p(
        "де m = ω<sub>E</sub>² a² b / GM ≈ 3.45 × 10⁻³."))

    heading("Збурення сили тяжіння J2", 1, story)
    story.append(p(
        "Відхилення поля сили тяжіння Землі від сферичної маси у головному "
        "порядку:"))
    math("a<sub>J2</sub> = −(3 J2 GM a²)/(2 r⁴) × [(1−5sin²φ<sub>c</sub>)x̂, "
         "(1−5sin²φ<sub>c</sub>)ŷ, (3−5sin²φ<sub>c</sub>)ẑ]")
    story.append(p(
        "Для літаків на висоті нижче 20 км у польотах тривалістю до 24 годин "
        "достатньо моделі Сомільяни з поправкою на висоту. Для ракет-носіїв, "
        "ракет і орбітального входу в атмосферу потрібні J2 (а часто й J3, J4)."))


# ----------------------------------------------------------------------------
def add_ext_magnetic_navigation(story):
    story.append(PageBreak())
    heading("Магнітне поле та навігація", 0, story)

    heading("Світова магнітна модель (WMM 2025)", 1, story)
    story.append(p(
        "WMM — це спільний стандарт NCEI / British Geological Survey / NGA "
        "для головного геомагнітного поля. Поточна модель — "
        "WMM2025, чинна до 31 грудня 2029 року. Поле подається рядом "
        "сферичних гармонік (стандартний степінь/порядок 12, 133 для "
        "високороздільної WMMHR2025), де кожен коефіцієнт Гаусса змінюється "
        "лінійно в часі протягом епохи моделі."))
    story.append(p(
        "У заданій точці (φ, λ, h, t) модель видає три геоцентричні "
        "компоненти (X на північ, Y на схід, Z униз), з яких:"))
    for b in [
        "Повна напруженість F = √(X² + Y² + Z²)",
        "Горизонтальна напруженість H = √(X² + Y²)",
        "Магнітне схилення D = atan2(Y, X) — кут від справжньої півночі до "
        "магнітної півночі, додатний на схід",
        "Магнітне нахилення I = atan2(Z, H) — кут від горизонталі",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Перетворення справжнього курсу на магнітний: ψ<sub>mag</sub> = ψ<sub>true</sub> − D. "
        "Магнітні компаси також потребують картки девіації (специфічної для "
        "планера) і мають похибки повороту на північ через нахилення."))

    heading("GPS у WGS-84", 1, story)
    story.append(p(
        "Сузір’я GPS передає ефемериди в ECEF WGS-84 та супутниковий час "
        "у GPST. Приймач розв’язує систему з чотирма невідомими "
        "(3 координати ECEF + зсув годинника) з рівнянь псевдодальності"))
    math("ρ<sub>i</sub> = |<b>r</b><sub>sat,i</sub> − <b>r</b><sub>rx</sub>| + c·Δt<sub>rx</sub> + ε<sub>i</sub>")
    story.append(p(
        "методом зважених найменших квадратів або розширеним фільтром Калмана. "
        "Розв’язок у ECEF потім перетворюється на (φ, λ, h) замкненими "
        "або ітераційними алгоритмами з попереднього розділу. Сучасні "
        "системи GNSS із підтримкою ІНС досягають субметрової точності в "
        "динамічних режимах."))

    heading("Відстань по великому колу за гаверсинусом", 1, story)
    code(
        "a = sin²((φ₂-φ₁)/2) + cos(φ₁) cos(φ₂) sin²((λ₂-λ₁)/2)\n"
        "c = 2 atan2(√a, √(1-a))\n"
        "d = R_E · c")
    story.append(p(
        "де R<sub>E</sub> ≈ 6 371 км. Початковий пеленг:"))
    code(
        "θ_i = atan2(sin(Δλ) cos(φ₂), cos(φ₁) sin(φ₂) - sin(φ₁) cos(φ₂) cos(Δλ))")
    story.append(p(
        "Похибки нижче 0.3% порівняно зі сплюснутою Землею. Ітераційний "
        "метод Вінсенті (Vincenty) (або варіант Карні, Karney) дає геодезичні "
        "відстані з субміліметровою точністю на WGS-84."))


# ----------------------------------------------------------------------------
def add_ext_time_systems(story):
    story.append(PageBreak())
    heading("Системи відліку часу в аерокосмічній галузі", 0, story)
    story.append(p(
        "Мають значення п’ять годинників. Чітке розуміння їх відрізняє "
        "симуляцію, що бездоганно узгоджується з GPS, ефемеридами та "
        "моделями магнітного поля, від тієї, що ні."))

    table_data = [
        ["Шкала", "Означення", "Застосування"],
        ["TAI", "Міжнародний атомний час. Рівномірні секунди SI.",
            "Основа; без розривів."],
        ["UTC", "= TAI − N високосних секунд; |UT1−UTC|&lt;0.9 с.",
            "Цивільний час. UTC = TAI − 37 с (2026)."],
        ["UT1", "Час обертання Землі (середнє Сонце на меридіані → полудень).",
            "Дрейфує; передається як DUT1 = UT1−UTC."],
        ["GPST", "Атомний; розпочався від UTC 1980-01-06.",
            "Супутниковий час GPS; = TAI − 19 с."],
        ["TT",   "= TAI + 32.184 с (за визначенням).",
            "Ефемериди Сонячної системи."],
        ["GMST", "Середній зоряний час за Гринвічем.",
            "Поворот ECEF↔ECI; +3хв 56.6 с/добу відносно UTC."],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[2.5 * cm, 7.5 * cm, 6.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(p(
        "Формула GMST (наближена, у градусах):"))
    code(
        "GMST = 280.46061837 + 360.98564736629·d + 0.000387933·T² − T³/38710000\n"
        "with d = days from J2000.0, T = centuries from J2000.0.")


# ----------------------------------------------------------------------------
def add_ext_atmosphere_deep(story):
    story.append(PageBreak())
    heading("Стандартна атмосфера докладно", 0, story)
    story.append(p(
        "Клас <font face='Courier'>FGStandardAtmosphere</font> у JSBSim "
        "реалізує стандартну атмосферу США 1976 року (NASA-TM-X-74335). "
        "Стандартна атмосфера ICAO ідентична до висоти 32 км."))

    heading("Опорні значення на рівні моря", 1, story)
    table_data = [
        ["Величина", "Символ", "Значення"],
        ["Температура",      "T<sub>0</sub>",   "288.15 K (15°C)"],
        ["Тиск",             "p<sub>0</sub>",   "101 325 Pa"],
        ["Густина",          "ρ<sub>0</sub>",   "1.225 kg/m³"],
        ["Швидкість звуку",  "a<sub>0</sub>",   "340.294 m/s"],
        ["Динамічна в’язкість","μ<sub>0</sub>",  "1.7894 × 10⁻⁵ Pa·s"],
        ["Питома газова стала","R",              "287.058 J/(kg·K)"],
        ["Показник адіабати","γ",                "1.40"],
        ["g₀",               "g<sub>0</sub>",   "9.806 65 m/s²"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[5.0 * cm, 3.0 * cm, 8.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    heading("Структура шарів (від 0 до 86 км)", 1, story)
    table_data = [
        ["Шар", "Нижня висота (км)", "Верхня висота (км)", "Вертикальний градієнт L (K/км)"],
        ["Тропосфера",    "0",  "11",  "−6.5"],
        ["Тропопауза",    "11", "20",  "0"],
        ["Стратосфера 1", "20", "32",  "+1.0"],
        ["Стратосфера 2", "32", "47",  "+2.8"],
        ["Стратопауза",   "47", "51",  "0"],
        ["Мезосфера 1",   "51", "71",  "−2.8"],
        ["Мезосфера 2",   "71", "84.852", "−2.0"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[3.6 * cm, 3.0 * cm, 3.0 * cm, 6.8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(p(
        "У межах кожного неізотермічного шару гідростатичне рівняння"))
    math("dp/dh = −ρ g, &nbsp; p = ρRT, &nbsp; T(h) = T<sub>b</sub> + L(h − h<sub>b</sub>)")
    story.append(p("інтегрується до"))
    math("p(h) = p<sub>b</sub> · [T<sub>b</sub>/(T<sub>b</sub> + L(h−h<sub>b</sub>))]"
         "<sup>g<sub>0</sub>/(R·L)</sup>")
    story.append(p(
        "Для ізотермічних шарів (L = 0) розв’язок є експоненційним:"))
    math("p(h) = p<sub>b</sub> · exp[ −g<sub>0</sub>(h − h<sub>b</sub>)/(R T<sub>b</sub>) ]")

    heading("Похідні величини", 1, story)
    math("a = √(γRT) &nbsp;(швидкість звуку)")
    math("M = V/a &nbsp;(число Маха)")
    math("μ(T) = μ<sub>ref</sub>(T/T<sub>ref</sub>)<sup>1.5</sup>(T<sub>ref</sub> + S)/(T + S)")
    story.append(p(
        "(закон Сазерленда, із S = 110.4 K для повітря). Число Рейнольдса "
        "Re = ρVL/μ. Повний тиск/тиск гальмування та температура:"))
    math("p<sub>t</sub> = p(1 + (γ−1)/2 · M²)<sup>γ/(γ−1)</sup>")
    math("T<sub>t</sub> = T(1 + (γ−1)/2 · M²)")


# ----------------------------------------------------------------------------
def add_ext_wind_turbulence(story):
    story.append(PageBreak())
    heading("Вітер, турбулентність і пориви", 0, story)

    heading("Профіль вітру поблизу поверхні", 1, story)
    math("u(z) = (u<sub>*</sub>/κ) ln(z/z<sub>0</sub>) &nbsp;(логарифмічний закон, κ ≈ 0.41)")
    math("u(h) = u<sub>ref</sub> (h/h<sub>ref</sub>)<sup>α</sup> &nbsp;(степеневий закон, α ≈ 1/7 над відкритою місцевістю)")

    heading("Дискретні пориви (MIL-F-8785C, 1-косинус)", 1, story)
    math("V<sub>gust</sub>(t) = (V<sub>m</sub>/2) (1 − cos(πt/T<sub>m</sub>))")
    story.append(p(
        "Використовується для сертифікації пілотажних характеристик. T<sub>m</sub> "
        "лежить у діапазоні від 0.5 с (малий БПЛА) до кількох секунд (транспортні "
        "літаки); V<sub>m</sub> типово 5-15 м/с."))

    heading("Неперервна турбулентність — СЩП за Драйденом", 1, story)
    math("Φ<sub>u</sub>(ω) = σ<sub>u</sub>² · (2L<sub>u</sub>/V) / (1 + (L<sub>u</sub>ω/V)²)")
    math("Φ<sub>v</sub>(ω) = σ<sub>v</sub>² · (L<sub>v</sub>/V) · "
         "(1 + 3(L<sub>v</sub>ω/V)²) / (1 + (L<sub>v</sub>ω/V)²)²")
    math("Φ<sub>w</sub>(ω) = σ<sub>w</sub>² · (L<sub>w</sub>/V) · "
         "(1 + 3(L<sub>w</sub>ω/V)²) / (1 + (L<sub>w</sub>ω/V)²)²")
    story.append(p(
        "Масштаби довжини L<sub>u,v,w</sub> та інтенсивності σ<sub>u,v,w</sub> "
        "задаються за смугами висот у MIL-F-8785C / MIL-HDBK-1797. "
        "Імовірності слабкої/помірної/сильної інтенсивності зменшуються з "
        "висотою; турбулентність вище тропопаузи трапляється рідко."))
    story.append(p(
        "<b>СЩП за фон Карманом</b> — це альтернатива (точніша на високих "
        "частотах), яку часто застосовують в аналізі флатера."))

    heading("Мікропорив (Вікрой, Vicroy)", 1, story)
    story.append(p(
        "Мікропорив (microburst) моделюється як трикомпонентне поле течії: "
        "горизонтальний відтік + спадний потік + вихрове кільце. Аналітична "
        "модель Вікроя параметризує профіль радіального відтоку радіусом ядра, "
        "висотою вихрового кільця та піковою швидкістю відтоку. Використовується "
        "для тренувальних сценаріїв виходу зі зсуву вітру."))


# ----------------------------------------------------------------------------
def add_ext_propulsion_theory(story):
    story.append(PageBreak())
    heading("Теорія силової установки", 0, story)

    heading("Поршневі двигуни — цикл Отто", 1, story)
    story.append(p(
        "Чотиритактний двигун: впуск, стиснення (адіабатичне), згоряння "
        "(за сталого об’єму), розширення (адіабатичне), випуск. Ідеальний ККД "
        "циклу Отто η = 1 − (1/r)<sup>γ−1</sup> зі ступенем стиснення r. "
        "Питома витрата палива (BSFC) типово 0.4-0.5 lb/(hp·hr) для безнаддувних "
        "двигунів на авіаційному бензині."))
    story.append(p(
        "Характеристики масштабуються з абсолютним тиском у впускному "
        "колекторі (MAP), частотою обертання (RPM) та сумішшю. Клас "
        "<font face='Courier'>FGPiston</font> використовує параболічну "
        "залежність потужності від MAP і лінійне масштабування за дроселем/RPM. "
        "Зниження характеристик з висотою (derating) враховує зменшення густини "
        "довкілля (якщо немає нагнітача чи турбонаддуву)."))

    heading("Турбіна — цикл Брайтона", 1, story)
    story.append(p(
        "Цикл із неперервним потоком: стиснення, згоряння (≈за сталого "
        "тиску), розширення. Ідеальний ККД циклу Брайтона η = 1 − (1/π)"
        "<sup>(γ−1)/γ</sup> зі ступенем підвищення тиску π. У сучасних "
        "турбовентиляторних двигунах π ≈ 30-50, TSFC 0.30-0.50 lb/(lbf·hr) на "
        "крейсерському режимі, 1.5-2.5 з увімкненим форсажем (AB)."))
    story.append(p(
        "<b>Ступінь двоконтурності</b>: чистий турбореактивний ≈ 0; військовий "
        "із низькою двоконтурністю ≈ 0.3; комерційний із високою ≈ 10-12 "
        "(GE9X, Trent XWB). Висока двоконтурність = більша масова витрата на "
        "нижчій швидкості = тихіше й ефективніше на дозвукових швидкостях."))
    story.append(p(
        "<b>Двовальна архітектура</b>: N1 (ротор низького тиску, вентилятор) та "
        "N2 (ротор високого тиску, компресор + турбіна). N1 — це основний "
        "параметр режиму тяги на більшості комерційних двигунів."))

    heading("Ракета — F = ṁ V<sub>e</sub> + (p<sub>e</sub> − p<sub>a</sub>)A<sub>e</sub>", 1, story)
    math("I<sub>sp</sub> = F / (ṁ · g<sub>0</sub>) &nbsp;(секунди)")
    story.append(p(
        "Питомий імпульс вимірює паливну ефективність. Типові значення: "
        "тверде паливо 250 с, RP-1/LOX 350 с, LH2/LOX 450 с, іонний "
        "&gt;3000 с. Рівняння Ціолковського:"))
    math("Δv = I<sub>sp</sub> g<sub>0</sub> ln(m<sub>0</sub>/m<sub>f</sub>)")
    story.append(p(
        "Виведення на орбіту вимагає Δv ≈ 9-10 км/с з урахуванням втрат на "
        "силу тяжіння та опір. Багатоступеневість необхідна, бо m<sub>0</sub>/m<sub>f</sub> "
        "експоненційно залежить від Δv."))

    heading("Електродвигуни — BLDC", 1, story)
    story.append(p(
        "Безщітковий двигун постійного струму описується (на фазу):"))
    math("V = K<sub>e</sub>·ω + I·R, &nbsp; τ = K<sub>t</sub>·I, &nbsp; "
         "K<sub>t</sub> = 1/K<sub>v</sub> in SI units")
    story.append(p(
        "де K<sub>v</sub> в rpm/V (хобі-домовленість). Потужність "
        "P = V·I = ω·τ + I²·R; другий доданок — резистивні втрати. "
        "ККД η = ω·τ / (V·I) досягає максимуму за проміжних навантажень "
        "(~50-70% номінального струму)."))
    story.append(p(
        "Акумулятор: елементи LiPo номінально 3.7 V (4.2 V макс., 3.0 V мін.); "
        "C-рейтинг обмежує піковий розряд (напр., 25 C × 5000 mAh = 125 A "
        "макс.). Рівень заряду інтегрує струм за часом: "
        "SoC(t) = SoC(0) − ∫I/Q · dt."))


# ----------------------------------------------------------------------------
def add_ext_propeller_rotor(story):
    story.append(PageBreak())
    heading("Теорія повітряного та несного гвинта", 0, story)

    heading("Повітряний гвинт — імпульсна теорія + елемент лопаті", 1, story)
    story.append(p(
        "Імпульсна теорія (Фруда): ідеальний диск прискорює потік "
        "від V до V+2v<sub>i</sub>, створюючи тягу"))
    math("T = 2 ρ A (V + v<sub>i</sub>) v<sub>i</sub>")
    story.append(p(
        "де v<sub>i</sub> — індуктивна швидкість на диску. Потужність "
        "P = T (V + v<sub>i</sub>); ККД η = TV/P → 1 лише за нульового "
        "v<sub>i</sub> (нескінченна площа диска, межа активного диска)."))
    story.append(p(
        "Теорія елемента лопаті аналізує кожен елемент лопаті як 2-D профіль "
        "із локальними α та V<sub>resultant</sub>. Клас "
        "<font face='Courier'>FGPropeller</font> у JSBSim використовує табличні "
        "криві C<sub>T</sub>(J) та C<sub>P</sub>(J), де відносна хода "
        "(advance ratio)"))
    math("J = V / (n·D), &nbsp; n in rev/s, D = diameter")
    math("Thrust = C<sub>T</sub>(J) · ρ · n² · D⁴")
    math("Power = C<sub>P</sub>(J) · ρ · n³ · D⁵")
    math("Efficiency η<sub>p</sub> = J · C<sub>T</sub> / C<sub>P</sub>")

    heading("P-фактор та ефекти, спричинені гвинтом", 1, story)
    for b in [
        "<b>P-фактор</b>: за ненульового α спадна лопать має вищий "
        "локальний кут атаки, ніж висхідна, що створює "
        "бічний зсув тяги, який спричиняє рискання літака.",
        "<b>Обертання струменя гвинта</b>: струмінь гвинта закручується "
        "по спіралі, асиметрично потрапляючи на вертикальне оперення і "
        "створюючи момент рискання.",
        "<b>Гіроскопічна прецесія</b>: літак на режимі тангажа прикладає "
        "вхідний момент відносно поперечної осі; обертовий гвинт реагує "
        "прецесійним рисканням, і навпаки.",
        "<b>Реактивний момент</b>: третій закон Ньютона — двигун, що крутить "
        "гвинт в один бік, крутить літак в інший. Напрямок "
        "(за/проти годинникової стрілки з кабіни) визначає, у який саме.",
    ]:
        story.append(bullet(b))

    heading("Гвинти зі сталою частотою обертання", 1, story)
    story.append(p(
        "Регулятор частоти обертання змінює крок лопаті, щоб утримувати задану "
        "RPM незалежно від положення дроселя. Це вмикається через "
        "<font face='Courier'>&lt;constspeed&gt;1"
        "&lt;/constspeed&gt;</font> у XML гвинта в JSBSim. "
        "Нижче діапазону регулятора гвинт повертається до фіксованого кроку на "
        "<font face='Courier'>&lt;minpitch&gt;</font>. Бета-діапазон (нижче "
        "польотного малого газу) та реверс (від’ємний крок) підтримуються на "
        "турбогвинтових двигунах."))

    heading("Несний гвинт вертольота", 1, story)
    story.append(p(
        "Несний гвинт — це повітряний гвинт, що також створює піднімальну "
        "силу. Тяга на висінні (імпульсна теорія):"))
    math("T = 2 ρ A v<sub>i</sub>², &nbsp; v<sub>i</sub> = √(T/(2ρA))")
    story.append(p(
        "<b>Поступальна піднімальна сила</b>: у горизонтальному польоті приплив "
        "стає асиметричним; наступаюча лопать бачить V + ω·r, відступаюча — ω·r − V. "
        "Відступаюча лопать наближається до зриву на високій поступальній "
        "швидкості — це межа V<sub>NE</sub> вертольота."))
    story.append(p(
        "<b>Циклічний крок</b>: крок лопаті змінюється раз за оберт, щоб "
        "нахилити диск несного гвинта, створюючи сили в будь-якому напрямку. "
        "<b>Загальний крок</b>: усі лопаті змінюють крок разом, "
        "керуючи величиною тяги. Клас "
        "<font face='Courier'>FGRotor</font> у JSBSim реалізує елемент лопаті + "
        "імпульсну теорію з динамікою махання; приклади X-15 та Pterosaur "
        "є гарною відправною точкою."))


# ----------------------------------------------------------------------------
def add_ext_signal_processing(story):
    story.append(PageBreak())
    heading("Обробка сигналів для САК", 0, story)

    heading("Фільтри в неперервному часі", 1, story)
    math("Аперіодична ланка: &nbsp; H(s) = c<sub>1</sub>/(s + c<sub>1</sub>)")
    math("Ланка випередження-запізнення: &nbsp; H(s) = (c<sub>1</sub>s + c<sub>2</sub>)/(c<sub>3</sub>s + c<sub>4</sub>)")
    math("Розмивна (washout) ланка: &nbsp; H(s) = s/(s + c<sub>1</sub>)")
    math("Другого порядку: &nbsp; H(s) = (c<sub>1</sub>s² + c<sub>2</sub>s + c<sub>3</sub>)/"
         "(c<sub>4</sub>s² + c<sub>5</sub>s + c<sub>6</sub>)")
    story.append(p(
        "Усі чотири — це компоненти-фільтри JSBSim із розділу 12. "
        "Коефіцієнти c<sub>1..6</sub> беруться безпосередньо з проєкту "
        "в неперервній s-площині."))

    heading("Дискретизація: білінійне (Тастіна) перетворення", 1, story)
    math("s ← (2/T) · (z − 1)/(z + 1)")
    story.append(p(
        "Перетворення Тастіна відображає всю ліву півплощину (стійкий "
        "неперервний випадок) в одиничний круг (стійкий дискретний), тож "
        "стійкість зберігається. Частоти спотворюються: "
        "ω<sub>d</sub> = (2/T) tan(ω<sub>a</sub>T/2). "
        "Для критичних частот полюсів/нулів «передспотворення» (prewarping) "
        "(заміна 2/T на ω<sub>0</sub>/tan(ω<sub>0</sub>T/2)) "
        "зберігає їхнє розташування точно."))

    heading("Дискретизація ПІД-регулятора", 1, story)
    code(
        "u(z) = K_p · e(z)\n"
        "     + K_i · T/2 · (1 + z⁻¹)/(1 − z⁻¹) · e(z)   (trapezoidal)\n"
        "     + K_d · (1 − z⁻¹)/T · e(z)                  (backward Euler)")
    story.append(p(
        "Елемент <font face='Courier'>&lt;pid&gt;</font> у JSBSim пропонує "
        "чотири методи інтегрування (rect = зворотний метод Ейлера, "
        "trap = трапецій, ab2/ab3 = Адамса-Бешфорта). Елемент "
        "<font face='Courier'>&lt;trigger&gt;</font> забезпечує "
        "захист від насичення інтегратора (anti-windup): за ненульового "
        "значення інтеграл заморожується, за від’ємного — скидається."))

    heading("Правила налаштування ПІД-регулятора", 1, story)
    table_data = [
        ["Метод", "Kp", "Ki", "Kd"],
        ["Циглера-Нікольса (за коливаннями)",
            "0.6·K<sub>u</sub>", "1.2·K<sub>u</sub>/T<sub>u</sub>", "0.075·K<sub>u</sub>·T<sub>u</sub>"],
        ["Лямбда-налаштування (FOPDT, λ = τ замкненого контуру)",
            "τ/(K(λ+θ))", "Kp/τ", "0 (без D)"],
        ["IMC PI",
            "(2τ+θ)/(2K(λ+θ))", "Kp/(τ+θ/2)", "—"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[5.5 * cm, 3.6 * cm, 3.6 * cm, 3.8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)


# ----------------------------------------------------------------------------
def add_ext_lcp_friction(story):
    story.append(PageBreak())
    heading("Лінійна задача доповнюваності та контактне тертя", 0, story)

    heading("Формулювання LCP", 1, story)
    story.append(p(
        "Лінійна задача доповнюваності (LCP) шукає <b>z</b> ∈ ℝⁿ такий, що"))
    math("<b>w</b> = M<b>z</b> + <b>q</b>, &nbsp; <b>w</b> ≥ 0, &nbsp; <b>z</b> ≥ 0, &nbsp; <b>w</b><sup>T</sup><b>z</b> = 0")
    story.append(p(
        "тобто для кожного i або w<sub>i</sub> = 0, або z<sub>i</sub> = 0. "
        "Контакт із тертям природно є LCP: z<sub>i</sub> — це "
        "контактний імпульс на i-му контакті, w<sub>i</sub> — відносна "
        "швидкість за нормаллю до поверхні; або контакт є (z &gt; 0, "
        "w = 0), або його немає (z = 0, w &gt; 0)."))

    heading("LCP шасі в JSBSim", 1, story)
    story.append(p(
        "Кожен контакт шасі додає:"))
    for b in [
        "Обмеження непроникнення за нормаллю до злітно-посадкової смуги.",
        "Обмеження кулонівського тертя по дотичній до смуги (поздовжній / "
        "бічний / опір коченню).",
        "Гальмівний момент від САК як додаткове обмеження конуса тертя.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Метод <font face='Courier'>FGAccelerations::"
        "CalculateFrictionForces()</font> у JSBSim розв’язує отриману LCP "
        "проєкційною ітерацією Гаусса-Зейделя (Catto 2005), до 50 внутрішніх "
        "ітерацій на такт. Це той самий алгоритм, що застосовується в сучасних "
        "ігрових фізичних рушіях (Bullet, ODE, Box2D)."))
    story.append(p(
        "<b>Чому LCP, а не просто явне обчислення сил?</b> "
        "Бо жорстка система пружина-демпфер-тертя є "
        "безумовно нестійкою за явного інтегрування, якщо допускати "
        "взаємопроникнення. Формулювання LCP проєктує контакт на "
        "допустимий многовид обмежень на кожному такті, що є "
        "неявно стійким незалежно від жорсткості."))


# ----------------------------------------------------------------------------
def add_ext_trim_algorithm(story):
    story.append(PageBreak())
    heading("Алгоритм балансування зсередини", 0, story)
    story.append(p(
        "Клас <font face='Courier'>FGTrim</font> знаходить стан літака та "
        "положення органів керування, що задовольняють умову усталеного "
        "польоту. Його реалізовано як композицію одновимірних секансних "
        "пошуковців коренів, координованих зовнішнім циклом."))

    heading("FGTrimAxis: елементарна комірка", 1, story)
    story.append(p(
        "Кожен <font face='Courier'>FGTrimAxis</font> поєднує змінну стану, "
        "яку треба обнулити (напр. <i>ẇ</i>), зі змінною керування, "
        "яку треба варіювати (напр. α). За двома пробними значеннями керування "
        "з відповідними значеннями стану секансне оновлення таке:"))
    math("x<sub>n+1</sub> = x<sub>n</sub> − f(x<sub>n</sub>) · (x<sub>n</sub> − x<sub>n−1</sub>) / (f(x<sub>n</sub>) − f(x<sub>n−1</sub>))")
    story.append(p(
        "JSBSim застосовує релаксацію 0.9, щоб гасити коливання:"))
    math("x<sub>n+1</sub> = x<sub>n</sub> − 0.9 f(x<sub>n</sub>) (Δx/Δf)")
    story.append(p(
        "Якщо секансний крок виходить за межі інтервалу, JSBSim повертається "
        "до бісекції на цій осі. Кожна вісь збігається до допуску: "
        "1e-3 для поступального ẍ, 1e-4 (у 10× жорсткіше) для кутового <font name='DejaVu'>ω̇</font>."))

    heading("Режими балансування", 1, story)
    table_data = [
        ["Режим (TrimMode)", "Обнулювані стани", "Варійовані органи керування"],
        ["tLongitudinal",
         "<i>u̇</i>=0, <i>ẇ</i>=0, <i><font name='DejaVu'>q̇</font></i>=0",
         "дросель, α, кермо висоти"],
        ["tFull",
         "+ <i><font name='DejaVu'>v̇</font></i>=0, <i>ṗ</i>=0, <i>ṙ</i>=0, утримання ψ",
         "+ φ, елерон, кермо напряму, β"],
        ["tFullWingsLevel", "tFull, але φ=0; β розв’язує <i><font name='DejaVu'>v̇</font></i>=0",
         "дросель, α, кермо висоти, елерон, кермо напряму, β"],
        ["tGround",
         "<i>ẇ</i>=0, <i><font name='DejaVu'>q̇</font></i>=0, <i>ṗ</i>=0",
         "висота (AGL), θ, φ"],
        ["tPullup",
         "поздовжній, n<sub>z</sub> = ціль",
         "α, дросель, кермо висоти"],
        ["tTurn",
         "координований віраж із заданим креном",
         "дросель, кермо висоти, кермо напряму"],
        ["tTurnFull",
         "координований віраж + кутові швидкості крену/рискання",
         "повний набір"],
        ["tCustom",
         "побудований користувачем через AddState/RemoveState",
         "обраний користувачем"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[3.6 * cm, 6.0 * cm, 6.8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    heading("Зовнішній цикл та збіжність", 1, story)
    story.append(p(
        "Усталені значення: <font face='Courier'>SetMaxCycles(60)</font> "
        "проходів по списку осей, <font face='Courier'>SetMaxCyclesPerAxis(100)"
        "</font> ітерацій на внутрішню вісь. У межах кожного циклу осі "
        "балансуються у фіксованому порядку. Якщо всі осі одночасно досягають "
        "своїх допусків після повного циклу, балансування оголошується збіжним, "
        "а <font face='Courier'>simulation/trim-completed</font> встановлюється "
        "в 1; інакше часова історія відновлюється і виникає "
        "помилка."))


# ----------------------------------------------------------------------------
def add_ext_nesc_check_cases(story):
    story.append(PageBreak())
    heading("Контрольні приклади верифікації NASA NESC 2015", 0, story)
    story.append(p(
        "JSBSim був єдиним учасником із відкритим кодом у програмі верифікації "
        "руху з 6 ступенями вільності Інженерно-безпекового центру NASA "
        "(NASA/TM-2015-218675). Шістьма іншими інструментами були внутрішні "
        "симулятори NASA (LaSRS++, SES, Marvin, POST-II, OSIRIS, MAVERIC). "
        "NESC дійшов висновку, що всі сім симуляторів узгоджувалися до "
        "придатного для публікації ступеня на більшості прикладів, а решта "
        "відмінностей була пояснена й могла бути зменшена."))

    heading("Приклади атмосферного польоту", 1, story)
    table_data = [
        ["#", "Приклад", "Що перевіряє"],
        ["1", "Скинута куля, без опору",
         "Вільне падіння в однорідному полі сили тяжіння"],
        ["2", "Цеглина, що перекидається, без опору",
         "Рівняння Ньютона-Ейлера, тензор інерції"],
        ["3", "Цеглина, що перекидається + аеродинамічне демпфування",
         "Додає демпфувальні моменти до твердотільного прикладу 2"],
        ["4", "Скинута куля, плоска Земля",
         "Перевіряє вибір моделі сили тяжіння"],
        ["5", "Скинута куля, обертова сферична Земля",
         "Додає коріолісову складову"],
        ["6", "Скинута куля, обертова еліпсоїдальна Земля",
         "Додає геодезію WGS-84"],
        ["7-8", "Скинута куля, сталий / змінний вітер",
         "Профілі зсуву вітру та поривів"],
        ["9-10", "Балістика на схід / на північ",
         "Коріолісові компоненти"],
        ["11", "Дозвукове балансування F-16",
         "Алгоритм балансування, власна структура короткоперіодичного руху"],
        ["12", "Надзвукове балансування F-16",
         "Трансзвукова / надзвукова аеродинаміка, балансування на M&gt;1"],
        ["13.1-13.4", "Збурювальні маневри F-16",
         "Дублет за висотою, ступінчаста зміна швидкості, ступінчаста зміна курсу"],
        ["15-16", "Глобальні польоти F-16",
         "Над Північним полюсом, навколо екватора"],
        ["17", "Двоступенева ракета від рівня моря до орбіти",
         "Перехід атмосферний → орбітальний"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[2.0 * cm, 6.0 * cm, 8.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(p(
        "Реалізації тестових прикладів NASA для JSBSim розташовані за адресою "
        "<font face='Courier'>github.com/open-aerospace/jsbsim-nasa-test-cases</font>; "
        "їх запуск — рекомендований спосіб верифікувати збірку JSBSim "
        "проти опублікованих еталонних траєкторій. Власні значення "
        "короткоперіодичного руху та руху голландського кроку F-16 збігаються "
        "між симуляторами до третьої значущої цифри; нев’язки балансування "
        "нижчі за допуски на вісь 1e-3 ft/s² та 1e-4 rad/s², усталені в JSBSim."))


# ----------------------------------------------------------------------------
def add_ext_property_tree_complete(story):
    story.append(PageBreak())
    heading("Повне дерево властивостей", 0, story)
    story.append(p(
        "Далі наведено майже повний перелік простору імен властивостей "
        "JSBSim, узагальнений з довідника API Doxygen, "
        "онлайн-посібника та викликів <font face='Courier'>"
        "PropertyManager-&gt;Tie()</font> у вихідному коді кожної моделі."))

    heading("simulation/", 1, story)
    code(
        "simulation/sim-time-sec        cumulative simulation time\n"
        "simulation/dt                  integration step\n"
        "simulation/frame               tick counter\n"
        "simulation/do_simple_trim      0=long, 1=full, 2=ground, 3=pullup,\n"
        "                                4=custom, 5=turn, 6=none\n"
        "simulation/do_linearization    write nonzero to dump A,B,C,D\n"
        "simulation/trim-completed      1 after successful trim\n"
        "simulation/reset               reset to IC\n"
        "simulation/pause               freeze model\n"
        "simulation/terminate           stop script\n"
        "simulation/integrator/rate/rotational\n"
        "simulation/integrator/rate/translational\n"
        "simulation/integrator/position/rotational\n"
        "simulation/integrator/position/translational\n"
        "simulation/gravity-model       0=spherical, 1=WGS-84\n"
        "simulation/gravitational-torque  0/1 spacecraft tidal\n"
        "simulation/randomseed          seeds random/urandom functions\n"
        "simulation/disperse            Monte-Carlo enable\n"
        "forces/hold-down               hold aircraft fixed at IC")

    heading("ic/", 1, story)
    code(
        "ic/u-fps, ic/v-fps, ic/w-fps         body-axis velocity\n"
        "ic/vn-fps, ic/ve-fps, ic/vd-fps      NED velocity\n"
        "ic/vt-fps, ic/vt-kts                 true airspeed\n"
        "ic/vc-kts                            calibrated airspeed\n"
        "ic/ve-kts                            equivalent airspeed\n"
        "ic/vg-kts                            ground speed\n"
        "ic/mach\n"
        "ic/phi-deg, ic/theta-deg, ic/psi-true-deg\n"
        "ic/alpha-deg, ic/beta-deg, ic/gamma-deg\n"
        "ic/lat-gc-deg, ic/lat-geod-deg\n"
        "ic/long-gc-deg\n"
        "ic/h-sl-ft, ic/h-agl-ft, ic/terrain-elevation-ft\n"
        "ic/vw-dir-deg, ic/vw-mag-fps\n"
        "ic/vw-north-fps, ic/vw-east-fps, ic/vw-down-fps\n"
        "ic/p-rad_sec, ic/q-rad_sec, ic/r-rad_sec\n"
        "ic/roc-fpm, ic/roc-fps\n"
        "ic/targetNlf                          load factor target")

    heading("position/, attitude/", 1, story)
    code(
        "position/h-sl-ft, h-sl-meters\n"
        "position/h-agl-ft\n"
        "position/lat-gc-deg, lat-gc-rad, lat-geod-deg\n"
        "position/long-gc-deg, long-gc-rad\n"
        "position/radius-to-vehicle-ft\n"
        "position/distance-from-start-lat-mt\n"
        "position/distance-from-start-lon-mt\n"
        "position/distance-from-start-mag-mt\n"
        "position/terrain-elevation-asl-ft\n"
        "position/epa-rad                       Earth position angle\n"
        "position/eci-x-ft, eci-y-ft, eci-z-ft\n"
        "position/ecef-x-ft, ecef-y-ft, ecef-z-ft\n"
        "attitude/phi-rad, theta-rad, psi-rad\n"
        "attitude/phi-deg, theta-deg, psi-deg\n"
        "attitude/heading-true-rad\n"
        "attitude/roll-rad, pitch-rad")

    heading("velocities/", 1, story)
    code(
        "velocities/u-fps, v-fps, w-fps              body\n"
        "velocities/u-aero-fps, v-aero-fps, w-aero-fps    body, airmass-rel\n"
        "velocities/p-rad_sec, q-rad_sec, r-rad_sec       body rates\n"
        "velocities/p-aero-rad_sec, q-aero-rad_sec, r-aero-rad_sec\n"
        "velocities/pi-rad_sec, qi-rad_sec, ri-rad_sec    inertial rates\n"
        "velocities/vt-fps, vt-kts\n"
        "velocities/vc-fps, vc-kts                  calibrated\n"
        "velocities/ve-fps, ve-kts                  equivalent\n"
        "velocities/vg-fps                          ground\n"
        "velocities/mach, machU\n"
        "velocities/h-dot-fps                       climb rate\n"
        "velocities/v-north-fps, v-east-fps, v-down-fps\n"
        "velocities/eci-velocity-mag-fps")

    heading("aero/, atmosphere/", 1, story)
    code(
        "aero/qbar-psf, qbarUW-psf, qbarUV-psf\n"
        "aero/alpha-rad, alpha-deg, beta-rad, beta-deg\n"
        "aero/alphadot-rad_sec, betadot-rad_sec\n"
        "aero/mag-beta-rad, mag-alpha-rad\n"
        "aero/Re                                  Reynolds number\n"
        "aero/bi2vel, ci2vel                      b/(2V), cbar/(2V)\n"
        "aero/alpha-wing-rad                      incidence adjusted\n"
        "aero/h_b-cg-ft, h_b-mac-ft               ground-effect ratios\n"
        "aero/stall-hyst-norm                     stall hysteresis\n"
        "aero/cl-squared\n"
        "aero/coefficient/<axis>/<name>           every defined coefficient\n"
        "\n"
        "atmosphere/T-R, T-sl-R, delta-T\n"
        "atmosphere/rho-slugs_ft3, rho-sl-slugs_ft3\n"
        "atmosphere/P-psf, P-sl-psf\n"
        "atmosphere/a-fps, a-sl-fps\n"
        "atmosphere/delta, theta, sigma\n"
        "atmosphere/density-altitude, pressure-altitude\n"
        "atmosphere/wind-north-fps, wind-east-fps, wind-down-fps\n"
        "atmosphere/total-wind-fps, psiw-rad\n"
        "atmosphere/turbulence/milspec/severity   0..7")

    heading("forces/, moments/, accelerations/", 1, story)
    code(
        "forces/fbx-aero-lbs, fby-aero-lbs, fbz-aero-lbs\n"
        "forces/fwx-aero-lbs, fwy-aero-lbs, fwz-aero-lbs   wind-axis\n"
        "forces/fbx-prop-lbs, fby-prop-lbs, fbz-prop-lbs\n"
        "forces/fbx-gear-lbs, fby-gear-lbs, fbz-gear-lbs\n"
        "forces/fbx-total-lbs, fby-total-lbs, fbz-total-lbs\n"
        "forces/hold-down\n"
        "moments/l-aero-lbsft, m-aero-lbsft, n-aero-lbsft\n"
        "moments/l-prop-lbsft, m-prop-lbsft, n-prop-lbsft\n"
        "moments/l-gear-lbsft, m-gear-lbsft, n-gear-lbsft\n"
        "moments/l-total-lbsft, m-total-lbsft, n-total-lbsft\n"
        "accelerations/pdot-rad_sec2, qdot-rad_sec2, rdot-rad_sec2\n"
        "accelerations/udot-ft_sec2, vdot-ft_sec2, wdot-ft_sec2\n"
        "accelerations/Nx, Ny, Nz                load factors (g)\n"
        "accelerations/n-pilot-x-norm, n-pilot-y-norm, n-pilot-z-norm\n"
        "accelerations/a-pilot-x-ft_sec2, a-pilot-y, a-pilot-z\n"
        "accelerations/gravity-ft_sec2")

    heading("fcs/, gear/", 1, story)
    code(
        "fcs/elevator-cmd-norm, aileron-cmd-norm, rudder-cmd-norm\n"
        "fcs/flap-cmd-norm, speedbrake-cmd-norm, spoiler-cmd-norm\n"
        "fcs/pitch-trim-cmd-norm, roll-trim-cmd-norm, yaw-trim-cmd-norm\n"
        "fcs/steer-cmd-norm\n"
        "fcs/throttle-cmd-norm[n], mixture-cmd-norm[n]\n"
        "fcs/throttle-pos-norm[n], mixture-pos-norm[n]\n"
        "fcs/advance-cmd-norm[n], feather-cmd-norm[n]\n"
        "fcs/magneto-cmd[n], starter-cmd[n]\n"
        "fcs/elevator-pos-rad, -deg, -norm\n"
        "fcs/left-aileron-pos-..., right-aileron-pos-...\n"
        "fcs/rudder-pos-...\n"
        "fcs/flap-pos-deg, flap-pos-norm\n"
        "fcs/speedbrake-pos-rad, spoiler-pos-rad\n"
        "fcs/wing-fold-pos-norm\n"
        "fcs/left-brake-cmd-norm, right-brake-cmd-norm, center-brake-cmd-norm\n"
        "gear/gear-cmd-norm, gear-pos-norm, tailhook-pos-norm\n"
        "gear/unit[i]/compression-ft, WOW, wheel-speed-fps,\n"
        "             static-friction-coeff, pos-x, pos-y, pos-z")

    heading("propulsion/, inertia/, metrics/", 1, story)
    code(
        "propulsion/engine[i]/thrust-lbs, power-hp, rpm\n"
        "propulsion/engine[i]/fuel-flow-rate-pps, fuel-flow-rate-gph\n"
        "propulsion/engine[i]/n1, n2\n"
        "propulsion/engine[i]/egt-degF, oil-pressure-psi, oil-temperature-degF\n"
        "propulsion/engine[i]/bsfc-lbs_hphr\n"
        "propulsion/engine[i]/mp-osi, volumetric-efficiency\n"
        "propulsion/engine[i]/set-running                  start flag\n"
        "propulsion/tank[i]/contents-lbs, capacity-gal_us\n"
        "propulsion/total-fuel-lbs, refuel\n"
        "inertia/empty-weight-lbs, weight-lbs, mass-slugs\n"
        "inertia/cg-x-in, cg-y-in, cg-z-in\n"
        "inertia/ixx-slugs_ft2, iyy-, izz-, ixy-, ixz-, iyz-\n"
        "metrics/Sw-sqft, bw-ft, cbarw-ft\n"
        "metrics/Sh-sqft, lh-ft, Sv-sqft, lv-ft\n"
        "metrics/aero-rp-x-in, aero-rp-y-in, aero-rp-z-in")


# ----------------------------------------------------------------------------
def add_ext_function_language_complete(story):
    story.append(PageBreak())
    heading("Мова функцій — повний довідник операторів", 0, story)
    story.append(p(
        "Кожен оператор, придатний для використання всередині блоку "
        "<font face='Courier'>&lt;function&gt;</font> у "
        "<font face='Courier'>&lt;aerodynamics&gt;</font>, <font face='Courier'>"
        "&lt;flight_control&gt;</font>, <font face='Courier'>&lt;system&gt;"
        "</font> чи <font face='Courier'>&lt;external_reactions&gt;</font>, "
        "узагальнений з довідника Doxygen <font face='Courier'>FGFunction</font>. "
        "Скорочення: <font face='Courier'>&lt;v&gt;</font> = "
        "<font face='Courier'>&lt;value&gt;</font>, "
        "<font face='Courier'>&lt;p&gt;</font> = "
        "<font face='Courier'>&lt;property&gt;</font>, "
        "<font face='Courier'>&lt;t&gt;</font> = "
        "<font face='Courier'>&lt;table&gt;</font>."))

    table_data = [
        ["Оператор", "Опис"],
        ["sum",         "Додає всі безпосередні дочірні елементи."],
        ["difference",  "Перший дочірній елемент мінус сума решти дочірніх."],
        ["product",     "Перемножує всі дочірні елементи."],
        ["quotient",    "Перший дочірній елемент, поділений на другий."],
        ["pow",         "Перший дочірній елемент, піднесений до другого."],
        ["sqrt",        "Квадратний корінь."],
        ["exp",         "e в степені дочірнього елемента."],
        ["ln, log2, log10", "Натуральний логарифм, за основою 2, за основою 10."],
        ["abs, sign",   "Абсолютне значення, знак."],
        ["sin, cos, tan", "Тригонометричні (аргумент у радіанах)."],
        ["asin, acos, atan", "Обернені тригонометричні; результат у радіанах."],
        ["atan2",       "atan2(Y, X); діапазон −π..π."],
        ["toradians, todegrees", "Перетворення кутових одиниць."],
        ["pi",          "Стала π. Вживається як <pi/>."],
        ["lt, le, gt, ge, eq, nq",
            "Повертає 1, якщо відношення виконується, інакше 0."],
        ["and, or, not", "Булеві. and/or приймають n дочірніх елементів."],
        ["ifthen",      "ifthen(умова, true, false). Усталене false = 0."],
        ["switch",      "switch(індекс, v0, v1, …); індекс від нуля."],
        ["min, max, avg", "Агрегування за дочірніми елементами."],
        ["floor, ceil, integer, fraction",
            "Операції округлення."],
        ["mod, fmod, roundmultiple",
            "Остача, остача з рухомою комою, округлення до кратного."],
        ["random",      "Гаусів; атрибути seed, mean, stddev."],
        ["urandom",     "Рівномірний; атрибути seed, lower, upper."],
        ["value, v",    "Числовий літерал."],
        ["property, p", "Читання властивості (рядкове тіло)."],
        ["table, t",    "1-D, 2-D або 3-D таблиця."],
        ["interpolate1d", "1-D вбудована інтерполяція."],
        ["rotation_alpha_local, rotation_beta_local, rotation_gamma_local",
            "Спеціальні повороти (6 аргументів)."],
        ["rotation_bf_to_wf, rotation_wf_to_bf",
            "Повороти зв’язана↔вітрова (7 аргументів)."],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[4.4 * cm, 12.1 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)


# ----------------------------------------------------------------------------
def add_ext_verification_validation(story):
    story.append(PageBreak())
    heading("Процедури верифікації та валідації", 0, story)

    heading("Ієрархія V&amp;V", 1, story)
    for b in [
        "<b>Верифікація</b> (verification): чи правильно ми розв’язуємо "
        "рівняння? Перевірка проти аналітичних розв’язків, проти "
        "опублікованих еталонних траєкторій (NESC), проти власних "
        "попередніх результатів симулятора після зміни коду.",
        "<b>Валідація</b> (validation): чи розв’язуємо ми правильні "
        "рівняння? Порівняння з льотними випробуваннями, аеродинамічною "
        "трубою, паспортними числами реального літака. Валідація завжди "
        "проводиться проти зовнішнього еталона.",
        "<b>Аналіз чутливості</b>: збурити кожен параметр (центр мас, "
        "I<sub>yy</sub>, C<sub>mα</sub> тощо) і кількісно оцінити зсув "
        "відгуку. Виявляє параметри, у які найбільше варто вкладатися.",
    ]:
        story.append(bullet(b))

    heading("Контрольний список верифікації (на кожен реліз)", 1, story)
    code(
        "1.  Build and run unit tests (CMake/CTest).\n"
        "2.  Run NESC atmospheric cases 1-17. Compare against\n"
        "    open-aerospace/jsbsim-nasa-test-cases reference CSVs.\n"
        "    Acceptable error: <1e-4 in normalised state.\n"
        "3.  Run all aircraft in aircraft/ through their reset00 IC and\n"
        "    do_simple_trim=0. Every aircraft must trim within 60 cycles.\n"
        "4.  For each trimmed aircraft, run a pitch doublet and check\n"
        "    short-period damping ratio is in [0.2, 0.9]; phugoid in\n"
        "    [0.005, 0.1].\n"
        "5.  Run forced-oscillation about Y at +/-1 deg, k=0.05, on the\n"
        "    F-16 cruise condition; extract C_mq + C_m_alphadot;\n"
        "    compare to NASA-2015 reference -22.0 +/- 1.0 1/rad.")

    heading("Валідація за льотними даними", 1, story)
    story.append(p(
        "Коли наявні дані льотних випробувань (ступінчасті відгуки з оцінкою "
        "за шкалою Купера-Гарпера, відпускання штурвала, дублети), процедура "
        "така:"))
    for b in [
        "Точно відтворити умови балансування: вагу, центр мас, висоту, число "
        "Маха, стан палива. Задокументувати конфігурацію літака (шасі, "
        "закрилки, підвіски).",
        "Подати на симулятор записані команди пілота (цифрові траси "
        "штурвала/важеля газу).",
        "Побудувати графіки p, q, r, α, β, n<sub>z</sub>, висоти, IAS у "
        "накладенні із сигналами льотних випробувань. Обчислити "
        "середньоквадратичну (RMS) похибку для кожного каналу.",
        "Уточнювати аеродинамічні коефіцієнти для мінімізації похибки "
        "методом найменших квадратів (least-squares system ID) — але завжди "
        "проти <i>відкладеного</i> валідаційного маневру, щоб уникнути "
        "перенавчання.",
    ]:
        story.append(bullet(b))

    heading("Пілотажні характеристики (MIL-F-8785C / MIL-HDBK-1797)", 1, story)
    story.append(p(
        "Сучасна оцінка пілотажних характеристик прогнозує пілотну оцінку за "
        "шкалою Купера-Гарпера з розімкнених і замкнених параметрів. Ключові "
        "межі:"))
    for b in [
        "Короткоперіодична <i>ω<sub>n</sub></i> відносно n/α (межі Категорії "
        "A/B/C, Рівня 1/2/3).",
        "Коефіцієнт демпфування фугоїда (Рівень 1: ζ &gt; 0.04).",
        "Стала часу режиму крену τ<sub>roll</sub> (Рівень 1: &lt; 1 с).",
        "Голландський крок ζ·ω<sub>n</sub> &gt; 0.15 (Рівень 1).",
        "Смуга пропускання та закид (dropback) (сучасні критерії; доповнюють "
        "MIL-F-8785C).",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_ext_further_reading(story):
    story.append(PageBreak())
    heading("Додаткова література та авторитетні джерела", 0, story)
    story.append(p(
        "Наведений нижче перелік — це впорядкований набір джерел, на які "
        "найчастіше посилаються цей посібник і сам вихідний код JSBSim."))

    heading("Аеродинаміка та теорія профілю", 1, story)
    for b in [
        "Anderson, J. D. Jr. <i>Fundamentals of Aerodynamics</i>, 6th ed., "
        "McGraw-Hill, 2017.",
        "Houghton, E. L., Carpenter, P. W. <i>Aerodynamics for Engineering "
        "Students</i>, 7th ed., Butterworth-Heinemann, 2017.",
        "Drela, M. <i>Flight Vehicle Aerodynamics</i>, MIT Press, 2014.",
        "McCormick, B. W. <i>Aerodynamics, Aeronautics and Flight "
        "Mechanics</i>, 2nd ed., Wiley, 1994.",
        "Schlichting, H. and Gersten, K. <i>Boundary-Layer Theory</i>, 9th "
        "ed., Springer, 2017.",
        "Abbott, I. H., von Doenhoff, A. E. <i>Theory of Wing Sections</i>, "
        "Dover, 1959. — довідник з профілів NACA.",
    ]:
        story.append(bullet(b))

    heading("Динаміка польоту та керування", 1, story)
    for b in [
        "Stevens, B. L., Lewis, F. L., Johnson, E. N. <i>Aircraft Control "
        "and Simulation</i>, 3rd ed., Wiley, 2015.",
        "Etkin, B., Reid, L. D. <i>Dynamics of Flight: Stability and "
        "Control</i>, 3rd ed., Wiley, 1996.",
        "Nelson, R. C. <i>Flight Stability and Automatic Control</i>, 2nd "
        "ed., McGraw-Hill, 1998.",
        "Cook, M. V. <i>Flight Dynamics Principles</i>, 3rd ed., "
        "Butterworth-Heinemann, 2012.",
        "Roskam, J. <i>Airplane Flight Dynamics and Automatic Flight "
        "Controls</i>, DARcorp, 2003. Восьмитомний комплект <i>Airplane "
        "Design</i> Роскама — інженерна біблія.",
        "USAF Stability and Control DATCOM, AFFDL-TR-79-3032 (1978). "
        "Напівемпіричні методи оцінювання для кожної похідної.",
    ]:
        story.append(bullet(b))

    heading("CFD та моделювання турбулентності", 1, story)
    for b in [
        "Wilcox, D. C. <i>Turbulence Modeling for CFD</i>, 3rd ed., "
        "DCW Industries, 2006.",
        "Pope, S. B. <i>Turbulent Flows</i>, Cambridge, 2000.",
        "Hirsch, C. <i>Numerical Computation of Internal and External "
        "Flows</i>, 2nd ed., Butterworth-Heinemann, 2007.",
        "Spalart, P. R., Allmaras, S. R. \"A One-Equation Turbulence "
        "Model for Aerodynamic Flows.\" AIAA 92-0439.",
        "Menter, F. R. \"Two-Equation Eddy-Viscosity Turbulence Models "
        "for Engineering Applications.\" AIAA Journal 32, 1994.",
        "NASA Turbulence Modeling Resource — "
        "turbmodels.larc.nasa.gov.",
    ]:
        story.append(bullet(b))

    heading("Атмосфера та геодезія", 1, story)
    for b in [
        "NASA-TM-X-74335 / NOAA-S/T 76-1562. <i>U.S. Standard "
        "Atmosphere, 1976.</i>",
        "NIMA / NGA TR 8350.2. <i>Department of Defense World Geodetic "
        "System 1984.</i>",
        "Torge, W., Müller, J. <i>Geodesy</i>, 4th ed., de Gruyter, 2012.",
        "Hofmann-Wellenhof, B., Lichtenegger, H., Wasle, E. <i>GNSS — "
        "Global Navigation Satellite Systems</i>, Springer, 2008.",
        "Vallado, D. A. <i>Fundamentals of Astrodynamics and "
        "Applications</i>, 4th ed., Microcosm Press, 2013.",
        "NCEI, BGS, NGA. <i>World Magnetic Model 2025 Technical "
        "Report</i>, 2025.",
    ]:
        story.append(bullet(b))

    heading("Силові установки", 1, story)
    for b in [
        "Mattingly, J. D. <i>Aircraft Engine Design</i>, 2nd ed., "
        "AIAA, 2002.",
        "Hill, P. G., Peterson, C. R. <i>Mechanics and Thermodynamics of "
        "Propulsion</i>, 2nd ed., Addison-Wesley, 1992.",
        "Sutton, G. P., Biblarz, O. <i>Rocket Propulsion Elements</i>, "
        "9th ed., Wiley, 2017.",
        "Leishman, J. G. <i>Principles of Helicopter Aerodynamics</i>, "
        "2nd ed., Cambridge, 2006.",
    ]:
        story.append(bullet(b))

    heading("Чисельні методи", 1, story)
    for b in [
        "Hairer, E., Nørsett, S. P., Wanner, G. <i>Solving Ordinary "
        "Differential Equations I</i> (нежорсткі), 2nd ed., Springer, 1993.",
        "Diebel, J. \"Representing Attitude.\" Stanford Univ. report, 2006.",
        "Shoemake, K. \"Animating Rotation with Quaternion Curves.\" "
        "SIGGRAPH 1985.",
        "Buss, S. \"Accurate and Efficient Simulation of Rigid Body "
        "Rotations.\" UCSD, 1999.",
        "Catto, E. \"Iterative Dynamics with Temporal Coherence.\" "
        "Crystal Dynamics tech. report, 2005.",
    ]:
        story.append(bullet(b))

    heading("Ресурси щодо JSBSim", 1, story)
    for b in [
        "Berndt, J. S. \"JSBSim: An Open Source Flight Dynamics Model in "
        "C++.\" AIAA-2004-4923. PDF на jsbsim.sourceforge.net.",
        "Онлайн-посібник: jsbsim-team.github.io/jsbsim-reference-manual.",
        "API Doxygen: jsbsim-team.github.io/jsbsim.",
        "Контрольні приклади NASA NESC з 6 ступенями свободи: "
        "nescacademy.nasa.gov/flightsim/2015.",
        "Реалізації тестових прикладів NASA для JSBSim: github.com/"
        "open-aerospace/jsbsim-nasa-test-cases.",
        "Огляд на DeepWiki: deepwiki.com/JSBSim-Team/jsbsim.",
        "Вікі FlightGear (багато практичних нотаток щодо JSBSim): "
        "wiki.flightgear.org/JSBSim.",
    ]:
        story.append(bullet(b))

    heading("OpenFOAM та робочий процес CFD→FDM", 1, story)
    for b in [
        "OpenFOAM User Guide &mdash; функціональні об’єкти <i>forces</i> та "
        "<i>forceCoeffs</i>: openfoam.com/documentation/guides "
        "(ESI) та cpp.openfoam.org (Foundation).",
        "Greenshields, C. <i>OpenFOAM User Guide</i>, OpenCFD/CFD Direct. "
        "Підручники (tutorials) "
        "<font face='Courier'>snappyHexMesh</font>, "
        "<font face='Courier'>simpleFoam</font> та "
        "<font face='Courier'>pimpleFoam</font> (зокрема "
        "<font face='Courier'>RAS/wingMotion</font>) — це канонічні "
        "відправні точки.",
        "Menter, F. R. \"Two-Equation Eddy-Viscosity Turbulence Models for "
        "Engineering Applications.\" AIAA Journal 32(8), 1994 &mdash; модель "
        "k-&omega; SST, що використовується для зовнішньої аеродинаміки.",
        "Da Ronch, A., et al. \"Estimation of Dynamic Stability Derivatives "
        "Using Computational Fluid Dynamics.\" &mdash; методи обертальної "
        "системи відліку та вимушених коливань.",
        "Mi, B., et al. \"Estimation and Separation of Longitudinal Dynamic "
        "Stability Derivatives with the Forced Oscillation Method Using CFD.\" "
        "<i>Aerospace</i> 8(11):354, 2021 &mdash; розділення C<sub>mq</sub> та "
        "C<sub>m" + _g("α̇") + "</sub> через вертикальний (plunge) і "
        "тангажний рухи.",
        "Tobak, M., Schiff, L. B. \"Aerodynamic Mathematical Modeling &mdash; "
        "Basic Concepts.\" AGARD LS-114, 1981 &mdash; теорія індикіальних "
        "відгуків (indicial-response), що лежить в основі динамічних похідних.",
        "NASA Turbulence Modeling Resource (turbmodels.larc.nasa.gov) та "
        "семінари AIAA Drag Prediction / High-Lift Prediction Workshops "
        "&mdash; валідаційні приклади для CFD літаків.",
        "Roache, P. J. \"Quantification of Uncertainty in Computational Fluid "
        "Dynamics.\" <i>Annu. Rev. Fluid Mech.</i> 29, 1997 &mdash; індекс "
        "збіжності сітки (Grid Convergence Index) для перевірки незалежності "
        "від сітки.",
        "PyFoam, foamlib і Python-модуль JSBSim &mdash; скриптування "
        "параметричного перебору та верифікація згенерованої моделі.",
    ]:
        story.append(bullet(b))

    heading("Побудова FDM, джерела даних і валідація", 1, story)
    for b in [
        "Berndt, J. S. \"JSBSim: An Open Source Flight Dynamics Model in "
        "C++.\" AIAA 2004-4923 &mdash; канонічна стаття про це ядро.",
        "Berndt, J. S., De Marco, A. \"Progress on and Usage of the Open "
        "Source Flight Dynamics Model Software Library, JSBSim.\" "
        "AIAA 2009-5699.",
        "<i>JSBSim Reference Manual</i> (jsbsim.sourceforge.net/"
        "JSBSimReferenceManual.pdf) та онлайн-посібник на "
        "jsbsim-team.github.io/jsbsim-reference-manual.",
        "Вікі FlightGear: <i>JSBSim</i>, <i>JSBSim Aerodynamics</i>, "
        "<i>JSBSim Engines</i>, <i>JSBSim Thrusters</i>, "
        "<i>JSBSim GroundReactions</i> &mdash; практична база знань "
        "спільноти.",
        "&quot;A Journal for the Creation and Refinement of a JSBSim Aircraft "
        "Flight Model&quot; &mdash; детальний коментований щоденник побудови "
        "моделі.",
        "Aeromatic / aeromatic++ (jsbsim.sourceforge.net/aeromatic2.html; "
        "вихідний код у <font face='Courier'>utils/aeromatic++/</font>).",
        "USAF Stability and Control DATCOM, AFFDL-TR-79-3032; Digital DATCOM "
        "(holycows.net/datcom) з експортом у XML для JSBSim.",
        "Drela, M., Youngren, H. <i>AVL</i> (метод вихрової решітки); "
        "<i>XFLR5</i>; OpenVSP / <i>VSPAero</i> &mdash; попередня "
        "аеродинаміка та похідні.",
        "Roskam, J. <i>Airplane Design</i> (Part V: ваги компонентів і "
        "моменти інерції) &mdash; радіуси інерції за класами.",
        "Cooper, G. E., Harper, R. P. \"The Use of Pilot Rating in the "
        "Evaluation of Aircraft Handling Qualities.\" NASA TN D-5153, 1969.",
        "MIL-STD-1797 / MIL-F-8785C &mdash; вимоги до пілотажних "
        "характеристик і модальні критерії, яким має відповідати реалістична "
        "модель.",
        "Klein, V., Morelli, E. A. <i>Aircraft System Identification: Theory "
        "and Practice</i>, AIAA, 2006 &mdash; виділення похідних із даних "
        "льотних (та JSBSim) випробувань.",
    ]:
        story.append(bullet(b))


# ============================================================================
# Part III — The OpenFOAM -> JSBSim CFD workflow
# ============================================================================


def _g(s):
    """Wrap a string in the DejaVu font so non-Latin-1 glyphs (Greek, dots,
    arrows, mathematical operators) render reliably inside DejaVu prose."""
    return f"<font name='DejaVu'>{s}</font>"


def _oftab(data, colWidths):
    """Build a table in the house style used throughout this manual."""
    t = Table(wrap_table(data), colWidths=colWidths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "DejaVu"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def add_part_iii_separator(story):
    story.append(PageBreak())
    story.append(Spacer(1, 55 * mm))
    story.append(Paragraph("Частина III", ParagraphStyle(
        "PartLabel3", fontName="DejaVu-Bold", fontSize=18,
        textColor=colors.HexColor("#1d5d9b"), alignment=TA_CENTER,
        spaceAfter=12)))
    story.append(Paragraph(
        "Від CFD до літаючої моделі:<br/>робочий процес від OpenFOAM до JSBSim",
        ParagraphStyle(
            "PartTitle3", fontName="DejaVu-Bold", fontSize=26,
            textColor=colors.HexColor("#0d3b66"), alignment=TA_CENTER,
            leading=32)))
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "Найвибагливіша частина створення нового літального апарата — це "
        "наповнення блоку <font face='Courier'>&lt;aerodynamics&gt;</font> "
        "числами, які насправді відповідають вашому планеру. Частина III — це "
        "наскрізний, відтворюваний рецепт генерування цих чисел за допомогою "
        "відкритого пакета обчислювальної гідрогазодинаміки (CFD) OpenFOAM та "
        "їх перенесення в JSBSim. Ми розглядаємо підготовку геометрії та "
        "побудову сітки, стаціонарне отримання статичних коефіцієнтів сил і "
        "моментів, три взаємодоповнювальні методики для динамічних похідних "
        "(за кутовими швидкостями), точне відображення кожного коефіцієнта "
        "мовою функцій/таблиць JSBSim, скриптований конвеєр, що автоматизує "
        "всю розгортку, та цикл верифікації, який зводить CFD із "
        "балансуванням, власними модами, даними з аеродинамічної труби та "
        "льотними даними. Усе тут спирається на механізми аеродинаміки, "
        "функцій/таблиць та балансування, описані в Частинах I і II.",
        ParagraphStyle("PartIntro3", parent=BODY_STYLE,
                       alignment=TA_CENTER, fontSize=11, leading=15,
                       leftIndent=22 * mm, rightIndent=22 * mm)))


# ----------------------------------------------------------------------------
def add_of_pipeline_overview(story):
    A = _g("α"); B = _g("β")
    story.append(PageBreak())
    heading("Конвеєр від CFD до FDM: від OpenFOAM до моделі JSBSim", 0,
            story)
    story.append(p(
        "Аеродинамічна модель JSBSim — це, по суті, таблиця безрозмірних "
        "коефіцієнтів як функцій стану потоку (кута атаки, кута ковзання, "
        "числа Маха, відхилень керм) плюс кілька динамічних похідних, які "
        "відображають нестаціонарну реакцію на кутові швидкості. Дані з "
        "аеродинамічної труби — це золотий стандарт, але для нового чи "
        "модифікованого планера кампанія CFD на основі осереднених за "
        "Рейнольдсом рівнянь Нав’є-Стокса (RANS) в OpenFOAM — це "
        "найдоступніший спосіб отримати повний, узгоджений набір даних ще до "
        "того, як з’явиться будь-яке залізо. Цей розділ окреслює всю "
        "кампанію: що потрібно JSBSim, як модель розкладається на складові та "
        "яка матриця розрахунків CFD її породжує."))

    heading("Навіщо будувати аеродинамічну модель з CFD", 1, story)
    for b in [
        "<b>Не потрібне залізо.</b> Ви можете охарактеризувати планер за "
        "CAD-моделлю за місяці до того, як отримаєте час в аеродинамічній "
        "трубі чи виконаєте перший політ.",
        "<b>Повна спостережуваність.</b> CFD повертає повне поле тиску та "
        "дотичних напружень, тож ви можете розкласти сили за компонентами "
        "(крило, хвостове оперення, фюзеляж, гондоли) саме так, як того "
        "потребує складова модель JSBSim.",
        "<b>Довільні умови.</b> Великий кут атаки, кут ковзання, відхилення "
        "керм, вплив землі та польотні числа Рейнольдса/Маха, які важко чи "
        "дорого відтворити в трубі.",
        "<b>Відкритість і відтворюваність.</b> OpenFOAM поширюється за GPL, "
        "піддається скриптуванню та запускається на ноутбуці чи на "
        "HPC-кластері з ідентичними словниками — природна пара для відкритої, "
        "керованої даними філософії JSBSim.",
    ]:
        story.append(bullet(b))
    story.append(quote(
        "CFD не замінює аеродинамічну трубу чи льотні випробування; вона "
        "наповнює модель наперед, тож дорогі дані, які ви все ж збираєте, "
        "витрачаються на коригування моделі, а не на створення її з нуля."))

    heading("Що потрібно JSBSim: перелік необхідних коефіцієнтів", 1, story)
    story.append(p(
        "Кожна величина нижче — це <i>безрозмірний</i> коефіцієнт. У JSBSim "
        "кожен із них стає одним чи кількома елементами "
        "<font face='Courier'>&lt;function&gt;</font>, що сумуються в "
        "<font face='Courier'>&lt;axis&gt;</font> (див. розділ про "
        "аеродинаміку та <font face='Courier'>FGAerodynamics.cpp:57-69</font> "
        "щодо відображення назви осі в індекс). Правий стовпець називає "
        "експеримент CFD, який його дає."))
    data = [
        ["Коефіцієнт", "Фізичний зміст", "Вісь JSBSim", "Експеримент CFD"],
        ["C<sub>L</sub>", "Піднімальна сила за " + A + ", закрилком, Махом",
         "LIFT (вітрова)",
         "Стаціонарна RANS-розгортка за " + A],
        ["C<sub>D</sub>", "Поляра опору за " + A + ", Махом", "DRAG (вітрова)",
         "Стаціонарна RANS-розгортка за " + A],
        ["C<sub>Y</sub>", "Бічна сила за " + B, "SIDE (вітрова)",
         "Стаціонарна RANS-розгортка за " + B],
        ["C<sub>l</sub>", "Момент крену за " + B + ", " + _g("δ") + "a, " +
         _g("δ") + "r", "ROLL (зв’язана)", "Розгортка за " + B + " + розрахунки керм"],
        ["C<sub>m</sub>", "Момент тангажа за " + A + ", " + _g("δ") + "e, Махом",
         "PITCH (зв’язана)", "Розгортка за " + A + " + розрахунки руля висоти"],
        ["C<sub>n</sub>", "Момент рискання за " + B + ", " + _g("δ") + "a, " +
         _g("δ") + "r", "YAW (зв’язана)", "Розгортка за " + B + " + розрахунки керм"],
        ["C<sub>Lq</sub>, C<sub>mq</sub>",
         "Піднімальна сила/тангаж від швидкості тангажа q",
         "LIFT, PITCH", "Вимушені коливання тангажа / обертання"],
        ["C<sub>lp</sub>, C<sub>np</sub>",
         "Крен/рискання від швидкості крену p",
         "ROLL, YAW", "Вимушені коливання крену / стаціонарний крен"],
        ["C<sub>lr</sub>, C<sub>nr</sub>",
         "Крен/рискання від швидкості рискання r",
         "ROLL, YAW", "Вимушені коливання рискання / стаціонарне рискання"],
        ["C<sub>L" + _g("α̇") + "</sub>, C<sub>m" + _g("α̇") + "</sub>",
         "Піднімальна сила/тангаж від " + _g("α̇") +
         " (запізнення скосу потоку)", "LIFT, PITCH",
         "Коливання вертикального переміщення (плунжерні)"],
        ["&Delta;C<sub>(...)</sub>/" + _g("δ"),
         "Прирости від ефективності керм", "відповідні осі",
         "Розрахунки з відхиленою геометрією"],
    ]
    story.append(_oftab(data, [2.6 * cm, 5.0 * cm, 2.7 * cm, 6.0 * cm]))

    heading("Складова (покомпонентна) модель і квазістаціонарне "
            "припущення", 1, story)
    story.append(p(
        "JSBSim сумує незалежні внески "
        "<font face='Courier'>&lt;function&gt;</font> у кожну вісь, тож "
        "природна модель — це <i>складова</i>: базова крива плюс адитивні "
        "прирости. Наприклад, для моменту тангажа:"))
    math("C<sub>m</sub> = C<sub>m0</sub> + C<sub>m</sub>(" + _g("α") +
         ") + C<sub>m" + _g("δ") + "e</sub>·" + _g("δ") +
         "e + C<sub>mq</sub>·(c&#x0304;/2V)·q + C<sub>m" + _g("α̇") +
         "</sub>·(c&#x0304;/2V)·" + _g("α̇"))
    story.append(p(
        "Ця лінійна суперпозиція точна лише тоді, коли внески незалежні. На "
        "практиці базові криві табулюються нелінійно (щоб охопити зрив потоку "
        "та стисливість), члени керм та кутових швидкостей трактуються як "
        "прирости навколо локальної робочої точки, а сильні зв’язки (напр. "
        "залежність ефективності керм від " + A + ") переносяться як двовимірні "
        "таблиці. <i>Квазістаціонарне</i> припущення — що миттєва сила "
        "залежить лише від миттєвого стану плюс члени кутових швидкостей "
        "першого порядку — це те, що робить достатньою скінченну таблицю. Воно "
        "справджується для зведених частот звичайного польоту; воно "
        "порушується для швидких маневрів, динамічного зриву та аеропружного "
        "флатера, які потребують нестаціонарних моделей поза межами табличного "
        "каркаса JSBSim."))

    heading("Матриця плану експерименту", 1, story)
    story.append(p(
        "Плануйте кампанію як структуровану розгортку, щоб кожен розрахунок "
        "CFD відповідав відомому вузлу таблиці. Практична базова матриця для "
        "звичайного літака:"))
    for b in [
        "<b>Розгортка за " + A + "</b> при " + B + "=0: напр. від -8&deg; до "
        "+20&deg; із кроком 2&deg;, дрібнішим поблизу зриву. Дає "
        "C<sub>L</sub>(" + A + "), C<sub>D</sub>(" + A + "), C<sub>m</sub>(" +
        A + ").",
        "<b>Розгортка за " + B + "</b> при кількох репрезентативних " + A +
        ": від 0&deg; до &plusmn;15&deg;. Дає C<sub>Y</sub>(" + B + "), "
        "C<sub>l</sub>(" + B + "), C<sub>n</sub>(" + B + ") — статичну "
        "бічно-колійну стійкість.",
        "<b>Розрахунки керм</b>: перебудуйте сітку з кожною відхиленою "
        "поверхнею (руль висоти, елерон, кермо напряму, закрилок) на 2-3 "
        "кутах, щоб отримати лінійні та насичувані прирости.",
        "<b>Розгортка за Махом</b> (якщо потік стисливий/трансзвуковий): "
        "повторіть розгортку за " + A + " на кількох числах Маха, щоб "
        "наповнити вимір таблиці за стисливістю.",
        "<b>Динамічні розрахунки</b>: випадки вимушених коливань чи обертання "
        "в одній чи кількох робочих точках, щоб отримати похідні за кутовими "
        "швидкостями (наступні розділи).",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Мінімальний набір даних для звичайного літака — порядку 20-40 "
        "статичних розрахунків плюс кілька динамічних; трансзвуковий, "
        "багатомаховий набір із повним набором керм може сягати кількох "
        "сотень. Скриптуйте це (див. розділ про автоматизацію)."))

    heading("Знерозмірювання: міст між CFD і JSBSim", 1,
            story)
    story.append(p(
        "Обидва світи говорять коефіцієнтами, але ви маєте узгодити "
        "характерні величини, інакше числа не перенесуться. CFD повідомляє "
        "C<sub>F</sub> = F / (&frac12;" + _g("ρ") + "V&sup2; S<sub>ref</sub>) "
        "та C<sub>M</sub> = M / (&frac12;" + _g("ρ") +
        "V&sup2; S<sub>ref</sub> l<sub>ref</sub>). JSBSim відновлює силу як "
        "<i>коефіцієнт</i> &times; <font face='Courier'>"
        "aero/qbar-area</font> (= " + _g("q̄") + "&middot;S), а момент — із "
        "додатковим множником розмаху чи хорди, де " + _g("q̄") + " = &frac12;"
        + _g("ρ") + "V&sup2; (<font face='Courier'>FGAerodynamics.cpp:163"
        "</font>)."))
    story.append(p(
        "Ключові правила узгодження — помиліться в них, і вашу модель буде "
        "непомітно неправильно змасштабовано:"))
    for b in [
        "<b>S<sub>ref</sub> = </b> площа крила, яку ви задаєте в "
        "<font face='Courier'>&lt;metrics&gt;&lt;wingarea&gt;</font> "
        "(властивість <font face='Courier'>metrics/Sw-sqft</font>). "
        "Використовуйте той самий <font face='Courier'>Aref</font> у "
        "<font face='Courier'>forceCoeffs</font> в OpenFOAM.",
        "<b>l<sub>ref</sub> = </b> середня аеродинамічна хорда c&#x0304; для "
        "тангажа, розмах b для крену/рискання. JSBSim множить тангаж на "
        "<font face='Courier'>metrics/cbarw-ft</font>, а крен/рискання на "
        "<font face='Courier'>metrics/bw-ft</font>.",
        "<b>Точка зведення моментів = </b> <font face='Courier'>CofR"
        "</font> в OpenFOAM має дорівнювати <font face='Courier'>&lt;location "
        "name=\"AERORP\"&gt;</font> в JSBSim, інакше ви маєте перенести "
        "моменти (див. розділ про відображення в XML).",
        "<b>Знерозмірювачі кутових швидкостей.</b> JSBSim формує b/(2V) як "
        "<font face='Courier'>aero/bi2vel</font>, а c&#x0304;/(2V) як "
        "<font face='Courier'>aero/ci2vel</font> "
        "(<font face='Courier'>FGAerodynamics.cpp:159-160, 618-619</font>); "
        "ваші похідні за кутовими швидкостями з CFD мають використовувати "
        "<i>ту саму</i> умову половини хорди/половини розмаху.",
    ]:
        story.append(bullet(b))

    heading("Дорожня карта Частини III", 1, story)
    for b in [
        "<b>Геометрія та побудова сітки</b> — герметичний STL, область, "
        "snappyHexMesh, y<sup>+</sup>, кермові поверхні.",
        "<b>Статичні коефіцієнти</b> — simpleFoam/rhoSimpleFoam, функційний "
        "об’єкт <font face='Courier'>forceCoeffs</font>, "
        "розгортки за " + A + "/" + B + ".",
        "<b>Динамічні похідні</b> — обертова система, вимушені коливання, "
        "вертикальне переміщення, індикальний метод; отримання C<sub>mq</sub>, "
        "C<sub>lp</sub>, C<sub>nr</sub>, &hellip;",
        "<b>Відображення в XML</b> — перетворення набору даних на повний блок "
        "<font face='Courier'>&lt;aerodynamics&gt;</font>.",
        "<b>Автоматизація</b> — драйвер на Python, що виконує розгортку та "
        "видає таблиці JSBSim.",
        "<b>Верифікація</b> — балансування, власні моди та порівняння з "
        "трубою/польотом.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_of_geometry_meshing(story):
    story.append(PageBreak())
    heading("Геометрія та побудова сітки для літаків в OpenFOAM", 0, story)
    story.append(p(
        "Розрахункова сітка визначає, чи будуть ваші коефіцієнти фізикою, чи "
        "числовим шумом. Цей розділ охоплює підготовку герметичної геометрії, "
        "визначення розмірів області, генерацію тілоконформної сітки за "
        "допомогою <font face='Courier'>blockMesh</font> + "
        "<font face='Courier'>snappyHexMesh</font>, досягнення правильного "
        "пристінкового розрізнення для вашої моделі турбулентності та особливу "
        "проблему відхилених кермових поверхонь."))

    heading("Герметична геометрія та виділення особливостей", 1, story)
    story.append(p(
        "Експортуйте планер як тріангульовану поверхню (STL/OBJ) у вигляді "
        "єдиної, замкненої оболонки без самоперетинів, з іменованими "
        "областями (<font face='Courier'>wing</font>, "
        "<font face='Courier'>fuselage</font>, "
        "<font face='Courier'>elevator</font>, &hellip;), щоб патчі можна було "
        "інтегрувати за силами окремо для покомпонентної складової моделі. "
        "Помістіть файл у <font face='Courier'>constant/triSurface/</font>. "
        "Виділіть гострі кромки (задні кромки, щілини кермових поверхонь), щоб "
        "побудовник сітки прив’язувався до них:"))
    code("""\
# constant/triSurface/ contains aircraft.stl (named solids)
surfaceFeatureExtract       # reads system/surfaceFeatureExtractDict
                            # -> writes aircraft.eMesh (feature edges)
surfaceCheck aircraft.stl   # verify closed & non-degenerate""")
    story.append(p(
        "Тримайте геометрію в метрах та узгодженою з характерною площею, яку "
        "ви оголосите; OpenFOAM не залежить від одиниць, але ваші "
        "<font face='Courier'>Aref</font>/<font face='Courier'>lRef</font> та "
        "метрики JSBSim мають відповідати тим самим фізичним розмірам."))

    heading("Розрахункова область", 1, story)
    story.append(p(
        "Області зовнішньої аеродинаміки мають бути достатньо великими, щоб "
        "межа набігного поля не впливала на розв’язок. Емпіричні правила, "
        "відмірювані від літака:"))
    for b in [
        "Вхід вище за потоком: 10-20 середніх хорд (або &gt;5 довжин тіла).",
        "Вихід нижче за потоком: 20-30 хорд, щоб дати слідові розвинутися.",
        "Бічне/вертикальне набігне поле: 10-20 хорд (або 5-10 розмахів).",
        "Для симетричного випадку (" + _g("β") + "=0, без асиметрії крену/"
        "рискання) розітніть область по центральній площині патчем "
        "<font face='Courier'>symmetry</font> і будуйте сітку лише для "
        "половини літака — удвічі менше комірок за того самого розрізнення.",
    ]:
        story.append(bullet(b))

    heading("Фонова сітка: blockMesh", 1, story)
    story.append(p(
        "<font face='Courier'>blockMesh</font> будує прямокутну фонову "
        "гексаедричну сітку та називає патчі набігного поля. "
        "<font face='Courier'>snappyHexMesh</font> потім вирізає з неї літак. "
        "Скелетний <font face='Courier'>blockMeshDict</font>:"))
    code("""\
scale 1;                       // STL already in metres
vertices ( (-60 -40 -40) (90 -40 -40) (90 40 -40) (-60 40 -40)
           (-60 -40  40) (90 -40  40) (90 40  40) (-60 40  40) );
blocks ( hex (0 1 2 3 4 5 6 7) (150 80 80) simpleGrading (1 1 1) );
boundary
(
    inlet    { type patch;    faces ((0 4 7 3)); }
    outlet   { type patch;    faces ((1 2 6 5)); }
    farfield { type patch;    faces ((0 1 5 4)(3 7 6 2)(4 5 6 7)); }
    symmetry { type symmetryPlane; faces ((0 3 2 1)); }   // y = 0 plane
);""")

    heading("Тілоконформна сітка: snappyHexMesh", 1, story)
    story.append(p(
        "<font face='Courier'>snappyHexMesh</font> працює у три фази: "
        "<i>зубчасте різання</i> (подрібнення та вилучення комірок усередині "
        "тіла), <i>прив’язка</i> (зсув граничних вузлів на STL та особливі "
        "кромки) та <i>додавання шарів</i> (вставлення призматичних комірок "
        "пограничного шару). Основні параметри словника:"))
    code("""\
castellatedMeshControls
{
    maxLocalCells 2000000; maxGlobalCells 50000000;
    refinementSurfaces
    {
        aircraft { level (5 6);      // min/max surface refinement
                   patchInfo { type wall; } }
    }
    features ( { file "aircraft.eMesh"; level 6; } );  // snap to edges
    refinementRegions
    {
        wakeBox { mode inside; levels ((1e15 3)); }    // refine the wake
    }
    locationInMesh (50 5 5);          // a point in the FLUID, not the body
}
snapControls { nSmoothPatch 3; tolerance 2.0; nSolveIter 50; }
addLayersControls
{
    relativeSizes true;
    layers { aircraft { nSurfaceLayers 12; } }
    expansionRatio 1.2;
    finalLayerThickness 0.4;          // fraction of adjacent cell
    minThickness 0.1;
}""")
    story.append(p(
        "Запустіть <font face='Courier'>snappyHexMesh -overwrite</font>, потім "
        "<font face='Courier'>checkMesh</font>. Вимагайте неортогональності "
        "нижче ~65&deg;, скошеності нижче ~4 і щоб запитані шари справді "
        "наросли (читайте журнал <font face='Courier'>snappyHexMesh</font>: "
        "покриття «Layer addition» близько 100% на несучих поверхнях)."))

    heading("Пристінкове розрізнення та y<sup>+</sup>", 1, story)
    story.append(p(
        "Висота першої комірки задає пристінкову координату y<sup>+</sup> = "
        "u<sub>" + _g("τ") + "</sub> y / " + _g("ν") + ", а ваш підхід до "
        "турбулентності диктує цільове значення:"))
    for b in [
        "<b>Пристінково-розрізнена (низькорейнольдсова) k-" + _g("ω") +
        " SST</b>: y<sup>+</sup> &lt; 1 на несучих поверхнях, з 30-40 "
        "комірками поперек пограничного шару та коефіцієнтом зростання "
        "&lt; 1.2. Потрібна для надійних опору, відриву та зриву.",
        "<b>Пристінкові функції</b> (високорейнольдсові): 30 &lt; "
        "y<sup>+</sup> &lt; 300. Дешевше, прийнятно для піднімальної сили при "
        "безвідривному обтіканні та моменту тангажа, але ненадійно поблизу "
        "зриву та для розкладу опору.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Оцініть висоту першої комірки за кореляцією поверхневого тертя "
        "плоскої пластини: C<sub>f</sub> &asymp; 0.026/Re<sub>x</sub><sup>1/7"
        "</sup>, дотичне напруження на стінці " + _g("τ") + "<sub>w</sub> = "
        "&frac12;C<sub>f</sub>" + _g("ρ") + "U&sup2;, динамічна швидкість "
        "u<sub>" + _g("τ") + "</sub> = &radic;(" + _g("τ") + "<sub>w</sub>/" +
        _g("ρ") + "), потім &Delta;y<sub>1</sub> = y<sup>+</sup>" + _g("ν") +
        "/u<sub>" + _g("τ") + "</sub>. Завжди підтверджуйте досягнуте "
        "y<sup>+</sup> за розв’язком "
        "(<font face='Courier'>postProcess -func yPlus</font>) і "
        "перебудовуйте сітку, якщо воно завелике."))

    heading("Незалежність від сітки", 1, story)
    story.append(p(
        "Запустіть щонайменше три систематично подрібнені сітки (напр. з "
        "кількостями комірок у співвідношенні близько 2) за фіксованої умови "
        "та підтвердьте, що C<sub>L</sub>, C<sub>D</sub>, C<sub>m</sub> "
        "збігаються. Кількісно оцініть це за допомогою індексу збіжності "
        "сітки (Roache) та екстраполяції Річардсона; повідомляйте асимптотичне "
        "значення, а не значення на найдрібнішій сітці. Опір значно "
        "чутливіший до сітки, ніж піднімальна сила, тож домагайтеся збіжності "
        "за опором."))

    heading("Кермові поверхні та рухома геометрія", 1, story)
    story.append(p(
        "Розрахунки ефективності керм та динамічних похідних потребують "
        "геометрії у відхиленому чи рухомому стані. Три підходи, у порядку "
        "зростання вартості:"))
    for b in [
        "<b>Окремі статичні сітки</b> — моделюйте кожне відхилення як власний "
        "STL та сітку. Найпростіший і найнадійніший спосіб для приростів від "
        "керм; просто перезапустіть розгортку з відхиленою геометрією та "
        "візьміть різницю коефіцієнтів.",
        "<b>Деформування сітки</b> (<font face='Courier'>displacementLaplacian"
        "</font> / RBF) — деформуйте єдину сітку для малих відхилень чи "
        "коливань; уникає перебудови, але погіршує якість комірок при великому "
        "русі.",
        "<b>Накладені (overset) або ковзні сітки AMI</b> — тілоконформна "
        "сітка компонента рухається крізь фонову сітку. Потрібна для великих "
        "обертань (відхилення поверхні на повний хід, гвинти) та для "
        "динамічних розрахунків з вимушеними коливаннями.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_of_static_coeffs(story):
    A = _g("α"); B = _g("β")
    story.append(PageBreak())
    heading("Статичні аеродинамічні коефіцієнти з OpenFOAM", 0, story)
    story.append(p(
        "Зі збіжною сіткою статичні коефіцієнти отримують із серії "
        "стаціонарних RANS-розв’язків, по одному на кожну умову потоку, кожен "
        "з яких постоброблюється функційним об’єктом "
        "<font face='Courier'>forceCoeffs</font>. Цей розділ уточнює вибір "
        "розв’язувача, граничні умови, спосіб задання кута атаки та кута "
        "ковзання, точний словник <font face='Courier'>forceCoeffs</font> та "
        "спосіб зчитування розгортки."))

    heading("Вибір розв’язувача", 1, story)
    data = [
        ["Режим", "Розв’язувач", "Примітки"],
        ["M &lt; 0.3 (нестисливий)", "simpleFoam",
         "Стаціонарний SIMPLE; стала густина; найшвидший. Більшість робіт для "
         "АЗП/БПЛА."],
        ["0.3 &le; M &lt; 0.7", "rhoSimpleFoam",
         "Стаціонарний стисливий; враховує зміну густини."],
        ["Трансзвуковий (M ~ 0.7-1.2)", "rhoSimpleFoam",
         "Стисливий із вловлюванням стрибків; потребує дрібнішої сітки, "
         "обережної релаксації."],
        ["Потрібна часова точність", "pimpleFoam / rhoPimpleFoam",
         "Нестаціонарний; використовується для розрахунків динамічних "
         "похідних."],
    ]
    story.append(_oftab(data, [4.0 * cm, 3.4 * cm, 8.8 * cm]))
    story.append(p(
        "Щодо моделі турбулентності, <b>k-" + _g("ω") + " SST</b> (Menter) — "
        "це робоча конячка зовнішньої аеродинаміки: вона добре поводиться при "
        "несприятливих градієнтах тиску та відриві й інтегрується до стінки, "
        "коли y<sup>+</sup>&lt;1. Spalart-Allmaras — надійна однорівнянна "
        "альтернатива для безвідривного обтікання."))

    heading("Граничні умови", 1, story)
    story.append(p(
        "Типове нестисливе налаштування (поля в <font face='Courier'>0/"
        "</font>):"))
    data = [
        ["Патч", "U", "p", "k / " + _g("ω")],
        ["inlet", "freestreamVelocity", "freestreamPressure /<br/>zeroGradient",
         "fixedValue (турб. притік)"],
        ["outlet", "freestream / inletOutlet", "freestreamPressure",
         "inletOutlet"],
        ["farfield", "freestream", "freestreamPressure", "inletOutlet"],
        ["aircraft", "noSlip", "zeroGradient",
         "kqRWallFunction / omegaWallFunction"],
        ["symmetry", "symmetryPlane", "symmetryPlane", "symmetryPlane"],
    ]
    story.append(_oftab(data, [2.4 * cm, 4.2 * cm, 4.6 * cm, 5.0 * cm]))
    story.append(p(
        "Умови <font face='Courier'>freestream</font>/"
        "<font face='Courier'>freestreamVelocity</font> перемикаються між "
        "поведінкою входу та виходу на основі локального потоку, тож те саме "
        "набігне поле працює для будь-якого напрямку потоку — зручно для "
        "розгорток за " + A + "/" + B + "."))

    heading("Задання кута атаки та кута ковзання", 1, story)
    story.append(p(
        "Чистий підхід — тримати сітку нерухомою та <b>повертати вектор "
        "швидкості набігного потоку</b>. У зв’язаних осях, де x спрямована "
        "назад уздовж фюзеляжу, y — на правий борт, z — угору, набігний потік "
        "зі швидкістю V при куті атаки " + A + " та куті ковзання " + B +
        " дорівнює:"))
    math("U = V&middot;( cos" + _g("α") + "&middot;cos" + _g("β") + ",  &minus;sin"
         + _g("β") + ",  sin" + _g("α") + "&middot;cos" + _g("β") + " )")
    code("""\
// 0/include/freestreamConditions  (use #include in 0/U, controlDict)
Uinf            68.0;            // m/s
alphaDeg        5.0;
betaDeg         0.0;
// 0/U
internalField   uniform (67.74 0 5.93);   // = Uinf*(cosA, 0, sinA), beta=0
boundaryField { inlet { type freestreamVelocity;
                        freestreamValue $internalField; } ... }""")
    story.append(p(
        "Принципово важливо, щоб <font face='Courier'>liftDir</font> та "
        "<font face='Courier'>dragDir</font> у "
        "<font face='Courier'>forceCoeffs</font> були задані для <i>тих "
        "самих</i> " + A + "/" + B + ", щоб піднімальна сила повідомлялася "
        "перпендикулярно до відносного вітру, а опір — уздовж нього. Для "
        "розгорток у площині тангажа: dragDir = (cos" + _g("α") + ", 0, sin" +
        _g("α") + "), liftDir = (&minus;sin" + _g("α") + ", 0, cos" + _g("α") +
        ")."))

    heading("Функційний об’єкт forceCoeffs", 1, story)
    story.append(p(
        "Додайте це до <font face='Courier'>system/controlDict</font> в "
        "розділ <font face='Courier'>functions { }</font> (синтаксис ESI / "
        "openfoam.com; форк openfoam.org майже ідентичний). Він інтегрує сили "
        "тиску та в’язкісні сили по іменованих патчах і нормує їх."))
    code("""\
functions
{
    forceCoeffs1
    {
        type            forceCoeffs;
        libs            ("libforces.so");
        writeControl    timeStep;  writeInterval 1;
        patches         (aircraft);          // or (wing fuselage tail ...)
        rho             rhoInf;               // incompressible: name + value
        rhoInf          1.225;                // kg/m^3
        magUInf         68.0;                 // m/s  (freestream speed)
        lRef            1.40;                 // mean aerodynamic chord  [m]
        Aref            16.17;                // reference (wing) area    [m^2]
        // wind axes for alpha = 5 deg, beta = 0:
        liftDir         (-0.0872 0 0.9962);
        dragDir         ( 0.9962 0 0.0872);
        pitchAxis       (0 1 0);
        CofR            (1.07 0 0);           // == JSBSim AERORP, in metres
        // optional (newer versions): which coefficients to write
        coefficients    (Cd Cl CmPitch Cs CmRoll CmYaw);
    }
}""")
    story.append(p(
        "Результати потрапляють у "
        "<font face='Courier'>postProcessing/forceCoeffs1/&lt;startTime&gt;/"
        "</font> як <font face='Courier'>coefficient.dat</font> (новіше) чи "
        "<font face='Courier'>forceCoeffs.dat</font> (старіше), по одному рядку "
        "на кожен запис, зі стовпцями, що включають "
        "<font face='Courier'>Cd</font> (опір), "
        "<font face='Courier'>Cl</font> (піднімальна сила), "
        "<font face='Courier'>Cs</font> (бічна сила), та коефіцієнти моментів "
        "<font face='Courier'>CmRoll</font>, "
        "<font face='Courier'>CmPitch</font>, "
        "<font face='Courier'>CmYaw</font>. Усі вони нормуються на &frac12;"
        + _g("ρ") + "&middot;magUInf&sup2;&middot;Aref (моменти &times; lRef)."))
    story.append(p(
        "<b>Зауваження щодо знаку та осей.</b> Коефіцієнти моментів OpenFOAM "
        "беруться відносно <font face='Courier'>CofR</font> у системі сітки; "
        "ROLL/PITCH/YAW у JSBSim — це моменти у зв’язаних осях відносно "
        "AERORP. Задайте <font face='Courier'>CofR=AERORP</font> та перевірте "
        "знак кожного коефіцієнта на відомому випадку, перш ніж довіряти йому "
        "— перевернута вісь чи зсув точки зведення моментів — це найпоширеніша "
        "помилка в усьому конвеєрі (детально розглянуто в розділі про "
        "відображення в XML)."))

    heading("Збіжність та осереднення", 1, story)
    for b in [
        "Запускайте до стагнації нев’язок (зазвичай від 1e-4 до 1e-6) <i>та</i> "
        "виходу коефіцієнтів на плато — стежте за "
        "<font face='Courier'>coefficient.dat</font> наживо, а не лише за "
        "нев’язками.",
        "Поблизу зриву чи для погано обтічних тіл стаціонарний розв’язувач "
        "може виходити на граничний цикл; перейдіть на нестаціонарний "
        "розв’язувач та осередніть за часом, або осередніть останні кілька "
        "сотень ітерацій SIMPLE.",
        "Використовуйте узгоджену нижню релаксацію та кілька тисяч ітерацій; "
        "трансзвукові випадки потребують поступового нарощування числа "
        "Куранта / релаксації.",
    ]:
        story.append(bullet(b))

    heading("Виконання розгорток", 1, story)
    story.append(p(
        "Клонуйте збіжний базовий випадок для кожної умови, відредагуйте "
        "набігний потік та <font face='Courier'>liftDir</font>/"
        "<font face='Courier'>dragDir</font>, запустіть і зберіть фінальний "
        "рядок коефіцієнтів. Результат — це сировина для таблиць JSBSim:"))
    for b in [
        "<b>Розгортка за " + A + "</b> &rarr; C<sub>L</sub>(" + A + "), "
        "C<sub>D</sub>(" + A + "), C<sub>m</sub>(" + A + "). Нахил C<sub>L</sub>"
        " за " + A + " має бути близько 2" + _g("π") + "&middot;AR/(AR+2) на "
        "радіан; нахил C<sub>m</sub> за " + A + " має бути від’ємним для "
        "статичної стійкості.",
        "<b>Розгортка за " + B + "</b> &rarr; C<sub>Y</sub>(" + B + "), "
        "C<sub>l</sub>(" + B + ") (ефект поперечного V, бажано &lt;0), "
        "C<sub>n</sub>(" + B + ") (флюгерна стійкість, бажано &gt;0).",
        "<b>Розрахунки керм</b> &rarr; &Delta;C на градус "
        "руля висоти/елерона/керма напряму/закрилка.",
        "<b>Перевірка поляри опору</b> &rarr; підженіть C<sub>D</sub> = "
        "C<sub>D0</sub> + C<sub>L</sub>&sup2;/(" + _g("π") + " e AR), щоб "
        "перевірити осмисленість опору при нульовій піднімальній силі та "
        "коефіцієнта Освальда.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_of_dynamic_derivatives(story):
    A = _g("α"); B = _g("β")
    adot = _g("α̇")
    story.append(PageBreak())
    heading("Динамічні похідні стійкості з OpenFOAM", 0, story)
    story.append(p(
        "Статичні розгортки не охоплюють реакцію планера на <i>кутові "
        "швидкості</i> та на <i>швидкість зміни</i> кута набігання. Ці "
        "динамічні похідні (похідні демпфування) — C<sub>mq</sub>, "
        "C<sub>lp</sub>, C<sub>nr</sub>, C<sub>lr</sub>, C<sub>np</sub>, "
        "C<sub>m" + adot + "</sub>, &hellip; — задають короткоперіодичну, "
        "голландського кроку, кренову та спіральну поведінку. Їх важче "
        "отримати з CFD, бо вони потребують або обертової системи відліку, або "
        "справді часо-точного руху. У широкому вжитку три методи."))

    heading("Похідні та їхній зміст", 1, story)
    data = [
        ["Похідна", "Зв’язує", "Знак для стійкого звичайного літака"],
        ["C<sub>mq</sub>", "момент тангажа &larr; швидкість тангажа q",
         "&lt; 0 (демпфування тангажа)"],
        ["C<sub>m" + adot + "</sub>", "момент тангажа &larr; " + adot +
         " (запізнення скосу потоку)", "&lt; 0"],
        ["C<sub>Lq</sub>", "піднімальна сила &larr; швидкість тангажа q",
         "&gt; 0"],
        ["C<sub>lp</sub>", "момент крену &larr; швидкість крену p",
         "&lt; 0 (демпфування крену)"],
        ["C<sub>nr</sub>", "момент рискання &larr; швидкість рискання r",
         "&lt; 0 (демпфування рискання)"],
        ["C<sub>lr</sub>", "момент крену &larr; швидкість рискання r", "&gt; 0"],
        ["C<sub>np</sub>", "момент рискання &larr; швидкість крену p",
         "&lt; 0 (несприятлива)"],
    ]
    story.append(_oftab(data, [2.6 * cm, 6.4 * cm, 7.2 * cm]))

    heading("Безрозмірна кутова швидкість та зведена частота", 1, story)
    story.append(p(
        "Похідні за кутовими швидкостями визначаються відносно безрозмірних "
        "кутових швидкостей: q&#x0302; = q&middot;c&#x0304;/(2V) для тангажа, "
        "та p&#x0302;, r&#x0302; = p,r&middot;b/(2V) для крену/рискання — це "
        "точно <font face='Courier'>ci2vel</font> та "
        "<font face='Courier'>bi2vel</font> у JSBSim. Для коливальних "
        "випробувань ключовий параметр подібності — <i>зведена частота</i>:"))
    math("k = " + _g("ω") + "&middot;c&#x0304; / (2V)")
    story.append(p(
        "Обирайте k малим (~0.01-0.1) та амплітуду малою (1-2&deg;), щоб "
        "отримані похідні були квазістаціонарними значеннями, яких очікують "
        "таблиці JSBSim; більше k зондує справді нестаціонарну аеродинаміку."))

    heading("Метод 1: стаціонарне обертання в неінерціальній системі", 1,
            story)
    story.append(p(
        "Чисті обертові похідні (C<sub>mq</sub> без частини " + adot +
        ", C<sub>lp</sub>, C<sub>nr</sub>) можна отримати зі "
        "<i>стаціонарного</i> розв’язку в обертовій системі відліку, "
        "уникаючи будь-якого руху сітки. Літак перебуває в системі, що "
        "обертається зі сталою кутовою швидкістю " + _g("Ω") + "; для випадку "
        "швидкості тангажа потік слідує по дузі кола, а стаціонарний момент "
        "дає C<sub>mq</sub> безпосередньо. В OpenFOAM це налаштовується через "
        "MRF-зону або джерело обертання "
        "<font face='Courier'>fvOptions</font>:"))
    code("""\
// constant/fvOptions  (impose a body rate omega about the CofR)
rotationSource
{
    type            rotorDiskSource;   // or a coded/MRF source
    // For derivative work an SRF (single rotating frame) solver
    // (SRFSimpleFoam) with SRFProperties is the classic route:
}
// constant/SRFProperties
SRFModel   rpm;
axis       (0 1 0);          // pitch about y
rpm        rpm_value;        // omega = q (rad/s) -> rpm""")
    story.append(p(
        "Запустіть дві-три кутові швидкості, що охоплюють нуль, побудуйте "
        "графік коефіцієнта моменту відносно безрозмірної кутової швидкості та "
        "візьміть нахил:"))
    math("C<sub>mq</sub> = &part;C<sub>m</sub> / &part;q&#x0302;,   "
         "q&#x0302; = q&middot;c&#x0304;/(2V)")
    story.append(p(
        "Це дешево (стаціонарно) та чисто для обертової частини, але <i>не</i> "
        "охоплює внесок " + adot + " (запізнення скосу потоку), який потребує "
        "руху."))

    heading("Метод 2: вимушені коливання", 1, story)
    story.append(p(
        "Коливайте літак синусоїдально навколо CofR за допомогою "
        "нестаціонарного розв’язувача "
        "(<font face='Courier'>pimpleFoam</font> + динамічна сітка) і "
        "вилучайте похідні з фази відгуку моменту. Канонічний примітив "
        "OpenFOAM — це "
        "<font face='Courier'>oscillatingRotatingMotion</font> (див. навчальний "
        "приклад <font face='Courier'>pimpleFoam/RAS/wingMotion</font>):"))
    code("""\
// constant/dynamicMeshDict
dynamicFvMesh   dynamicMotionSolverFvMesh;
motionSolver    solidBody;
solidBodyMotionFunction oscillatingRotatingMotion;
oscillatingRotatingMotionCoeffs
{
    origin      (1.07 0 0);     // CofR == AERORP
    axis        (0 1 0);        // pitch
    omega       6.2832;         // angular FREQUENCY of oscillation [rad/s]
    amplitude   (0 2 0);        // degrees about each axis (here 2 deg pitch)
}""")
    story.append(p(
        "Для чистого коливання тангажа навколо CG за нерухомого набігного "
        "потоку кут атаки та швидкість тангажа жорстко зчеплені (q = " +
        adot + "), тож квазістаціонарний момент дорівнює:"))
    math("C<sub>m</sub>(t) = C<sub>m0</sub> + C<sub>m" + _g("α") +
         "</sub>&middot;" + _g("α") + "(t) + (C<sub>mq</sub> + C<sub>m" + adot +
         "</sub>)&middot;(c&#x0304;/2V)&middot;" + adot + "(t)")
    story.append(p(
        "При " + _g("α") + "(t) = " + _g("α") + "<sub>0</sub> + &Delta;" +
        _g("α") + "&middot;sin(" + _g("ω") + "t) синфазна (синусна) "
        "компонента C<sub>m</sub> дає статичний нахил C<sub>m" + _g("α") +
        "</sub>, а протифазна (косинусна) компонента дає сумарне демпфування. "
        "Вилучаючи їх як перші коефіцієнти Фур’є за один період T:"))
    math("C<sub>m" + _g("α") + "</sub> = (2/(&Delta;" + _g("α") +
         "T)) &#x222B; C<sub>m</sub>(t) sin(" + _g("ω") + "t) dt")
    math("C<sub>mq</sub> + C<sub>m" + adot + "</sub> = (2V/(c&#x0304;&middot;"
         + _g("ω") + "&middot;&Delta;" + _g("α") + "T)) &#x222B; C<sub>m</sub>"
         "(t) cos(" + _g("ω") + "t) dt")
    story.append(p(
        "Рівнозначно, побудуйте графік C<sub>m</sub> відносно " + _g("α") +
        " за цикл: площа та напрямок обходу петлі кодують демпфування. Петля, "
        "що обходиться за годинниковою стрілкою (енергія відбирається), "
        "означає додатне демпфування (C<sub>mq</sub>+C<sub>m" + adot +
        "</sub> &lt; 0). Відкиньте перші 1-2 цикли як пусковий перехідний "
        "процес і осередніть за кількома чистими циклами."))

    heading("Метод 3: вертикальне переміщення та індикальний відгук", 1, story)
    story.append(p(
        "Вимушений тангаж дає лише <i>суму</i> C<sub>mq</sub> + C<sub>m" +
        adot + "</sub>. Щоб їх розділити, запустіть <b>коливання "
        "вертикального переміщення (плунжерні)</b>: переміщуйте літак "
        "вертикально так, щоб змінювався кут атаки (даючи " + adot + ") за "
        "<i>нульової</i> швидкості тангажа (q = 0). Це виокремлює "
        "C<sub>m" + adot + "</sub>; відніміть її від суми вимушеного тангажа, "
        "щоб відновити C<sub>mq</sub>:"))
    math("C<sub>mq</sub> = (C<sub>mq</sub> + C<sub>m" + adot +
         "</sub>)<sub>pitch</sub> &minus; (C<sub>m" + adot +
         "</sub>)<sub>plunge</sub>")
    story.append(p(
        "<b>Індикальний (ступінчастий) метод</b> — це третій шлях: задайте "
        "стрибок " + _g("α") + " чи q та запишіть перехідне наростання "
        "моменту; похідні випливають з індикальних функцій відгуку (теорія "
        "Тобака/Вагнера). Він найзагальніший, але найвибагливіший до "
        "постобробки."))

    heading("Бічно-колійні похідні", 1, story)
    story.append(p(
        "Той самий механізм застосовується до крену та рискання. Вимушені "
        "коливання крену навколо зв’язаної осі x дають C<sub>lp</sub> (та "
        "C<sub>np</sub>); вимушені коливання рискання навколо z дають "
        "C<sub>nr</sub> (та C<sub>lr</sub>). Знерозмірювач перемикається з "
        "c&#x0304;/(2V) на b/(2V) (<font face='Courier'>bi2vel</font> у "
        "JSBSim). Стаціонарне обертання в неінерціальній системі знову є "
        "дешевим шляхом для чистих частин за кутовими швидкостями."))

    heading("Порівняння методів", 1, story)
    data = [
        ["Метод", "Дає", "Вартість", "Застереження"],
        ["Стаціонарна обертова система", "чисті C<sub>mq</sub>, C<sub>lp</sub>, "
         "C<sub>nr</sub>", "низька (стаціонарна)", "пропускає запізнення " +
         adot],
        ["Вимушені коливання", "C<sub>mq</sub>+C<sub>m" + adot + "</sub> тощо",
         "висока (нестаціонарна + рухома сітка)", "потребує розділення Фур’є"],
        ["Вертикальне переміщення", "лише C<sub>m" + adot + "</sub>",
         "висока", "у парі з вимушеним тангажем"],
        ["Індикальний / ступінчастий", "усі, найзагальніший",
         "висока", "складна постобробка"],
    ]
    story.append(_oftab(data, [3.6 * cm, 5.0 * cm, 4.0 * cm, 3.6 * cm]))
    story.append(quote(
        "Прагматичний рецепт: використовуйте стаціонарну обертову систему для "
        "основної маси обертових похідних, додайте один випадок вимушеного "
        "тангажа + один випадок вертикального переміщення, щоб розрізнити "
        "C<sub>mq</sub> та C<sub>m" + adot + "</sub>, та вдавайтеся до оцінок "
        "DATCOM/AVL для будь-якої похідної, яку бюджет не може охопити."))


# ----------------------------------------------------------------------------
def add_of_xml_mapping(story):
    A = _g("α"); B = _g("β")
    story.append(PageBreak())
    heading("Зведення даних CFD у XML літака JSBSim", 0, story)
    story.append(p(
        "Саме тут кампанія окупається: перетворення набору даних CFD на "
        "повний блок <font face='Courier'>&lt;aerodynamics&gt;</font>. Добра "
        "новина в тому, що каркас JSBSim відображається майже один-до-одного "
        "на безрозмірні коефіцієнти — значення похідної потрапляє прямо в "
        "<font face='Courier'>&lt;value&gt;</font>, а крива коефіцієнта "
        "потрапляє прямо в <font face='Courier'>&lt;table&gt;</font>."))

    heading("Вибір системи осей та точки зведення", 1, story)
    story.append(p(
        "Узгодьте осі JSBSim з тим, що природно повідомляє CFD. Сили з "
        "<font face='Courier'>forceCoeffs</font> — це піднімальна/опір/бічна "
        "(вітрові осі); моменти — це крен/тангаж/рискання у зв’язаних осях. "
        "Отже:"))
    for b in [
        "Сили &rarr; <font face='Courier'>&lt;axis name=\"LIFT\"&gt;</font>, "
        "<font face='Courier'>\"DRAG\"</font>, <font face='Courier'>\"SIDE\""
        "</font> (вітрова система — стандартна, коли використовуються "
        "LIFT/DRAG; <font face='Courier'>FGAerodynamics.cpp:453-460</font>).",
        "Моменти &rarr; <font face='Courier'>&lt;axis name=\"ROLL\"&gt;</font>,"
        " <font face='Courier'>\"PITCH\"</font>, <font face='Courier'>\"YAW\""
        "</font> (зв’язана система за замовчуванням; "
        "<font face='Courier'>FGAerodynamics.cpp:450-452</font>).",
        "Задайте <font face='Courier'>CofR</font> в OpenFOAM рівним "
        "<font face='Courier'>&lt;metrics&gt;&lt;location name=\"AERORP\"&gt;"
        "</font>, щоб точка зведення моментів збігалася; інакше перенесіть "
        "моменти (нижче).",
    ]:
        story.append(bullet(b))

    heading("Головна таблиця відображення", 1, story)
    story.append(p(
        "Кожен коефіцієнт CFD стає "
        "<font face='Courier'>&lt;function&gt;</font> = (знерозмірювачі) "
        "&times; (коефіцієнт). Знерозмірювачі — це властивості JSBSim; "
        "коефіцієнт — це ваша <font face='Courier'>&lt;table&gt;</font> чи "
        "<font face='Courier'>&lt;value&gt;</font> з CFD."))
    qa = "<font face='Courier'>aero/qbar-area</font>"
    data = [
        ["Коефіцієнт", "Вісь", "Функція JSBSim = добуток"],
        ["C<sub>L</sub>(" + A + ")", "LIFT",
         qa + " &times; таблиця C<sub>L</sub>(" + A + ")"],
        ["C<sub>D</sub>(" + A + ")", "DRAG",
         qa + " &times; таблиця C<sub>D</sub>(" + A + ")"],
        ["C<sub>Y</sub>(" + B + ")", "SIDE",
         qa + " &times; таблиця C<sub>Y</sub>(" + B + ")"],
        ["C<sub>l</sub>(" + B + ")", "ROLL",
         qa + " &times; <font face='Courier'>bw-ft</font> &times; таблиця"],
        ["C<sub>m</sub>(" + A + ")", "PITCH",
         qa + " &times; <font face='Courier'>cbarw-ft</font> &times; таблиця"],
        ["C<sub>n</sub>(" + B + ")", "YAW",
         qa + " &times; <font face='Courier'>bw-ft</font> &times; таблиця"],
        ["C<sub>mq</sub>", "PITCH",
         qa + " &times; <font face='Courier'>cbarw-ft</font> &times; "
         "<font face='Courier'>ci2vel</font> &times; "
         "<font face='Courier'>q-aero-rad_sec</font> &times; значення"],
        ["C<sub>lp</sub>", "ROLL",
         qa + " &times; <font face='Courier'>bw-ft</font> &times; "
         "<font face='Courier'>bi2vel</font> &times; "
         "<font face='Courier'>p-aero-rad_sec</font> &times; значення"],
        ["C<sub>nr</sub>", "YAW",
         qa + " &times; <font face='Courier'>bw-ft</font> &times; "
         "<font face='Courier'>bi2vel</font> &times; "
         "<font face='Courier'>r-aero-rad_sec</font> &times; значення"],
    ]
    story.append(_oftab(data, [2.4 * cm, 1.8 * cm, 12.0 * cm]))

    heading("Ключове розуміння: значення І Є похідною", 1, story)
    story.append(p(
        "Оскільки JSBSim будує безрозмірну кутову швидкість внутрішньо (b/2V "
        "та c&#x0304;/2V через <font face='Courier'>bi2vel</font>/"
        "<font face='Courier'>ci2vel</font>, "
        "<font face='Courier'>FGAerodynamics.cpp:159-160</font>) і повертає "
        "розмірність через " + _g("q̄") + "&middot;S та розмах/хорду, стала, "
        "яку ви розміщуєте в <font face='Courier'>&lt;value&gt;</font> "
        "похідної за кутовою швидкістю, — це точно підручникова безрозмірна "
        "похідна. Модель c172 робить це наочним — її функція демпфування "
        "крену — це буквально " + _g("q̄") + "S&middot;b&middot;(b/2V)"
        "&middot;p&middot;C<sub>lp</sub> з C<sub>lp</sub> = &minus;0.47 "
        "(<font face='Courier'>aircraft/c172x/c172x.xml:1025-1034</font>):"))
    code("""\
<function name="aero/coefficient/Clp">
  <description>Roll moment due to roll rate (roll damping)</description>
  <product>
    <property>aero/qbar-area</property>       <!-- qbar * Sw          -->
    <property>metrics/bw-ft</property>         <!-- span b             -->
    <property>aero/bi2vel</property>           <!-- b/(2V)             -->
    <property>velocities/p-aero-rad_sec</property> <!-- roll rate p    -->
    <value>-0.47</value>                       <!-- Clp from CFD       -->
  </product>
</function>""")
    story.append(p(
        "Тож ваші отримані з OpenFOAM C<sub>lp</sub>, C<sub>mq</sub>, "
        "C<sub>nr</sub>, &hellip; йдуть прямо в гніздо "
        "<font face='Courier'>&lt;value&gt;</font>. Жодного додаткового "
        "масштабування."))

    heading("Статичні криві як таблиці", 1, story)
    story.append(p(
        "Табулюйте кожен базовий коефіцієнт відносно його первинної змінної, "
        "додаючи виміри стовпця/таблиці для зв’язків (напр. " + B + ", Махом, "
        "закрилком). Крива піднімальної сили з розгортки за " + A + ", "
        "помножена до сили:"))
    code("""\
<axis name="LIFT">
  <function name="aero/coefficient/CL_basic">
    <description>Lift from CFD alpha-sweep</description>
    <product>
      <property>aero/qbar-area</property>
      <table>
        <independentVar lookup="row">aero/alpha-rad</independentVar>
        <tableData>
          -0.140  -0.62
          -0.087  -0.18
           0.000   0.27
           0.087   0.95
           0.175   1.42
           0.262   1.61   <!-- approaching stall -->
           0.300   1.45   <!-- post-stall drop  -->
        </tableData>
      </table>
    </product>
  </function>
</axis>""")
    story.append(p(
        "Для набору даних із залежністю від Маха додайте "
        "<font face='Courier'>&lt;independentVar lookup=\"column\"&gt;"
        "velocities/mach&lt;/independentVar&gt;</font> та надайте матрицю; "
        "для " + A + "/" + B + "/Маха додайте третій вимір "
        "<font face='Courier'>lookup=\"table\"</font> з блоками "
        "<font face='Courier'>&lt;tableData breakPoint=\"&hellip;\"&gt;"
        "</font>."))

    heading("Прирости від керм", 1, story)
    story.append(p(
        "Взяття різниці між розрахунком із відхиленою геометрією та чистим "
        "базовим розрахунком дає &Delta;C на кожну поверхню; табулюйте "
        "відносно відхилення, щоб охопити нелінійність/насичення:"))
    code("""\
<function name="aero/coefficient/Cm_de">
  <description>Pitch moment due to elevator (CFD increments)</description>
  <product>
    <property>aero/qbar-area</property>
    <property>metrics/cbarw-ft</property>
    <table>
      <independentVar lookup="row">fcs/elevator-pos-rad</independentVar>
      <tableData>
        -0.35  0.38
         0.00  0.00
         0.35 -0.41
      </tableData>
    </table>
  </product>
</function>""")

    heading("Умови знаків та осей: підводні камені", 1, story)
    story.append(p(
        "Більшість невдач тут — це облік, а не фізика. Узгодьте ці моменти, "
        "перш ніж довіряти моделі:"))
    for b in [
        "<b>Знак опору.</b> C<sub>D</sub> з CFD додатний (сила, що протидіє "
        "вітру). Вісь DRAG у JSBSim уже спрямована вздовж відносного вітру, "
        "тож додатне значення — це правильний опір — не змінюйте знак.",
        "<b>Напрямки зв’язаних осей.</b> Підтвердьте, що ваша зв’язана система "
        "CFD (напрямки x, y, z) відповідає умові структурної-до-зв’язаної "
        "JSBSim; перевернута y чи z непомітно інвертує крен/рискання чи "
        "тангаж.",
        "<b>Перенесення точки зведення моментів.</b> Якщо "
        "<font face='Courier'>CofR &ne; AERORP</font>, зсуньте момент тангажа. "
        "За нормальної сили C<sub>N</sub>, осьової сили C<sub>A</sub> та "
        "AERORP на відстані &Delta;x назад і &Delta;z вище за CofR:",
    ]:
        story.append(bullet(b))
    math("C<sub>m,AERORP</sub> = C<sub>m,CofR</sub> + "
         "(C<sub>N</sub>&middot;&Delta;x &minus; C<sub>A</sub>&middot;&Delta;z)"
         " / c&#x0304;")
    for b in [
        "<b>Радіани проти градусів.</b> Незалежні змінні таблиць "
        "використовують власну одиницю властивості — "
        "<font face='Courier'>aero/alpha-rad</font> у радіанах, "
        "<font face='Courier'>aero/alpha-deg</font> у градусах, "
        "<font face='Courier'>fcs/elevator-pos-rad</font> у радіанах. "
        "Узгодьте вузли ваших CFD-таблиць із властивістю, на яку ви "
        "посилаєтеся.",
        "<b>Узгодженість характерних площі/довжини.</b> S, b, c&#x0304; в "
        "<font face='Courier'>&lt;metrics&gt;</font> мають дорівнювати "
        "<font face='Courier'>Aref</font>/<font face='Courier'>lRef</font>, "
        "що використовуються в <font face='Courier'>forceCoeffs</font>.",
    ]:
        story.append(bullet(b))

    heading("Розв’язаний приклад: повний набір осей, отриманий з CFD", 1,
            story)
    story.append(p(
        "Збираючи все докупи — компактний, але повний скелет "
        "<font face='Courier'>&lt;aerodynamics&gt;</font>, наповнений "
        "цілковито з CFD (базові криві скорочено):"))
    code("""\
<aerodynamics>
  <axis name="DRAG">
    <function name="aero/coefficient/CD0">          <!-- CD vs alpha -->
      <product><property>aero/qbar-area</property>
        <table><independentVar lookup="row">aero/alpha-rad</independentVar>
          <tableData> -0.09 0.025
                       0.00 0.022
                       0.17 0.060
                       0.26 0.140 </tableData></table>
      </product>
    </function>
  </axis>
  <axis name="LIFT">
    <function name="aero/coefficient/CLa">          <!-- CL vs alpha -->
      <product><property>aero/qbar-area</property>
        <table><independentVar lookup="row">aero/alpha-rad</independentVar>
          <tableData> -0.09 -0.18
                       0.00  0.27
                       0.17  1.42
                       0.26  1.61 </tableData></table>
      </product>
    </function>
    <function name="aero/coefficient/CLq">          <!-- lift due to q -->
      <product><property>aero/qbar-area</property>
        <property>aero/ci2vel</property>
        <property>velocities/q-aero-rad_sec</property>
        <value>3.9</value></product>
    </function>
  </axis>
  <axis name="SIDE">
    <function name="aero/coefficient/CYb">          <!-- side force vs beta -->
      <product><property>aero/qbar-area</property>
        <property>aero/beta-rad</property><value>-0.31</value></product>
    </function>
  </axis>
  <axis name="ROLL">
    <function name="aero/coefficient/Clb">          <!-- dihedral effect -->
      <product><property>aero/qbar-area</property><property>metrics/bw-ft</property>
        <property>aero/beta-rad</property><value>-0.089</value></product>
    </function>
    <function name="aero/coefficient/Clp">          <!-- roll damping -->
      <product><property>aero/qbar-area</property><property>metrics/bw-ft</property>
        <property>aero/bi2vel</property>
        <property>velocities/p-aero-rad_sec</property>
        <value>-0.47</value></product>
    </function>
  </axis>
  <axis name="PITCH">
    <function name="aero/coefficient/Cma">          <!-- pitch stiffness -->
      <product><property>aero/qbar-area</property><property>metrics/cbarw-ft</property>
        <property>aero/alpha-rad</property><value>-1.8</value></product>
    </function>
    <function name="aero/coefficient/Cmq">          <!-- pitch damping -->
      <product><property>aero/qbar-area</property><property>metrics/cbarw-ft</property>
        <property>aero/ci2vel</property>
        <property>velocities/q-aero-rad_sec</property>
        <value>-12.4</value></product>
    </function>
  </axis>
  <axis name="YAW">
    <function name="aero/coefficient/Cnb">          <!-- weathercock -->
      <product><property>aero/qbar-area</property><property>metrics/bw-ft</property>
        <property>aero/beta-rad</property><value>0.065</value></product>
    </function>
    <function name="aero/coefficient/Cnr">          <!-- yaw damping -->
      <product><property>aero/qbar-area</property><property>metrics/bw-ft</property>
        <property>aero/bi2vel</property>
        <property>velocities/r-aero-rad_sec</property>
        <value>-0.15</value></product>
    </function>
  </axis>
</aerodynamics>""")
    story.append(p(
        "Кожне <font face='Courier'>&lt;value&gt;</font> вище — це безрозмірна "
        "похідна стійкості прямо з CFD; кожна "
        "<font face='Courier'>&lt;table&gt;</font> — це розгортка CFD. "
        "Додавайте прирости від керм, вплив землі та виміри за Махом, як того "
        "вимагають дані."))


# ----------------------------------------------------------------------------
def add_of_automation(story):
    story.append(PageBreak())
    heading("Автоматизація конвеєра від OpenFOAM до JSBSim", 0, story)
    story.append(p(
        "Реальна кампанія — це десятки-сотні розрахунків; робити це вручну — "
        "загрожує помилками та невідтворювано. Цей розділ накидає скриптований "
        "конвеєр: створіть шаблон базового випадку за матрицею умов, запустіть "
        "розв’язувач, розберіть "
        "<font face='Courier'>coefficient.dat</font> та видайте XML "
        "<font face='Courier'>&lt;function&gt;</font>/"
        "<font face='Courier'>&lt;table&gt;</font> для JSBSim."))

    heading("Шаблонування випадків за матрицею умов", 1, story)
    story.append(p(
        "Тримайте один збіжний <font face='Courier'>baseCase/</font> та "
        "клонуйте його для кожної умови, переписуючи лише набігний потік та "
        "<font face='Courier'>liftDir</font>/<font face='Courier'>dragDir"
        "</font>. Мінімальний драйвер на Python:"))
    code('''\
import math, shutil, subprocess, pathlib, re

def wind_dirs(alpha_deg, beta_deg=0.0):
    a, b = math.radians(alpha_deg), math.radians(beta_deg)
    drag = (math.cos(a)*math.cos(b), -math.sin(b), math.sin(a)*math.cos(b))
    lift = (-math.sin(a), 0.0, math.cos(a))
    return drag, lift

def make_case(alpha, Uinf=68.0, base="baseCase"):
    case = pathlib.Path(f"run_a{alpha:+05.1f}")
    if case.exists(): shutil.rmtree(case)
    shutil.copytree(base, case)
    drag, lift = wind_dirs(alpha)
    U = (Uinf*math.cos(math.radians(alpha)), 0.0,
         Uinf*math.sin(math.radians(alpha)))
    # patch 0/U internalField and forceCoeffs liftDir/dragDir
    sub(case/"0"/"U", r"internalField\\s+uniform \\([^)]*\\)",
        f"internalField   uniform ({U[0]:.4f} {U[1]:.4f} {U[2]:.4f})")
    fc = case/"system"/"controlDict"
    sub(fc, r"liftDir\\s+\\([^)]*\\)", f"liftDir ({lift[0]:.4f} {lift[1]:.4f} {lift[2]:.4f})")
    sub(fc, r"dragDir\\s+\\([^)]*\\)", f"dragDir ({drag[0]:.4f} {drag[1]:.4f} {drag[2]:.4f})")
    return case

def sub(path, pattern, repl):
    t = path.read_text()
    path.write_text(re.sub(pattern, repl, t))

for alpha in range(-8, 22, 2):
    case = make_case(alpha)
    subprocess.run(["simpleFoam", "-case", str(case)], check=True)''')

    heading("Розбір коефіцієнтів", 1, story)
    story.append(p(
        "Зчитуйте останній рядок "
        "<font face='Courier'>coefficient.dat</font> (пропускаючи заголовок "
        "<font face='Courier'>#</font>) для кожного випадку:"))
    code('''\
import numpy as np, glob, os

def last_coeffs(case):
    f = sorted(glob.glob(f"{case}/postProcessing/forceCoeffs1/*/coefficient.dat"))[-1]
    rows = [l for l in open(f) if not l.startswith("#")]
    cols = np.array(rows[-1].split(), dtype=float)
    # column order (ESI): time Cd Cs Cl CmRoll CmPitch CmYaw ...
    return dict(Cd=cols[1], Cs=cols[2], Cl=cols[3],
                Cl_roll=cols[4], Cm=cols[5], Cn=cols[6])

data = {}
for case in sorted(glob.glob("run_a*")):
    alpha = float(case.split("_a")[1])
    data[alpha] = last_coeffs(case)''')

    heading("Видача таблиць JSBSim", 1, story)
    story.append(p(
        "Нарешті, відформатуйте розібрану розгортку як "
        "<font face='Courier'>&lt;function&gt;</font> JSBSim з "
        "<font face='Courier'>&lt;table&gt;</font>. Зверніть увагу на "
        "перетворення вузлів за " + _g("α") + " у радіани, щоб відповідати "
        "<font face='Courier'>aero/alpha-rad</font>:"))
    code('''\
def emit_lift(data):
    rows = "\\n".join(f"      {math.radians(a):8.4f} {data[a]['Cl']:8.4f}"
                      for a in sorted(data))
    return f"""<function name="aero/coefficient/CL_cfd">
  <description>Lift from OpenFOAM alpha-sweep</description>
  <product>
    <property>aero/qbar-area</property>
    <table>
      <independentVar lookup="row">aero/alpha-rad</independentVar>
      <tableData>
{rows}
      </tableData>
    </table>
  </product>
</function>"""

print(emit_lift(data))   # paste into <axis name="LIFT"> ... </axis>''')

    heading("Інструментарій та відтворюваність", 1, story)
    for b in [
        "<b>PyFoam</b>, <b>foamlib</b> та <b>openfoamparser</b> надійно "
        "читають/записують словники OpenFOAM та файли постобробки — "
        "віддавайте перевагу їм перед регулярними виразами для робочих "
        "конвеєрів.",
        "<b>pandas</b>/<b>numpy</b> для зберігання розгортки, підгонки поляри "
        "(C<sub>D0</sub>, число Освальда e) та оцінки нахилів "
        "(C<sub>L" + _g("α") + "</sub>, C<sub>m" + _g("α") + "</sub>).",
        "<b>Модуль JSBSim для Python</b> (<font face='Courier'>import jsbsim"
        "</font>) дозволяє тому самому скрипту збалансувати та випробувати "
        "згенеровану модель для негайної верифікації.",
        "Тримайте <font face='Courier'>Allrun</font>/<font face='Courier'>"
        "Allclean</font>, зафіксуйте версію OpenFOAM та архівуйте журнали і "
        "вивід <font face='Courier'>checkMesh</font>, щоб набір даних можна "
        "було перевірити та перезапустити.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_of_verification(story):
    story.append(PageBreak())
    heading("Верифікація: замикання циклу CFD-JSBSim-політ", 0, story)
    story.append(p(
        "Модель, що завантажується без помилок, — це не валідована модель. "
        "Останній крок — підтвердити, що літак JSBSim відтворює фізику CFD, "
        "осмислено поводиться при балансуванні та у своїх динамічних модах і "
        "— там, де дані існують, — узгоджується з аеродинамічною трубою та "
        "польотом. Сприймайте це як цикл: кожна розбіжність вказує назад на "
        "конкретну таблицю, знак чи точку зведення."))

    heading("Статичні перевірки: чи балансується там, де каже CFD", 1, story)
    for b in [
        "Збалансуйте модель (<font face='Courier'>FGTrim</font>, поздовжній "
        "режим) та підтвердьте, що балансувальні " + _g("α") + " і руль висоти "
        "є фізичними та відповідають робочій точці CFD.",
        "Відновіть C<sub>m</sub>(" + _g("α") + ") з JSBSim, розгортаючи " +
        _g("α") + " за фіксованих керм та зчитуючи "
        "<font face='Courier'>aero/coefficient/*</font> чи "
        "<font face='Courier'>moments/m-aero-lbsft</font>; нахил має "
        "відповідати C<sub>m" + _g("α") + "</sub> з CFD.",
        "Знайдіть <b>нейтральну точку</b> (де dC<sub>m</sub>/dC<sub>L</sub> "
        "= 0) та підтвердьте, що <b>статичний запас</b> (НТ мінус CG, у % MAC) "
        "є додатним і узгодженим зі значенням, отриманим із CFD.",
    ]:
        story.append(bullet(b))

    heading("Динамічні перевірки: лінеаризуйте та порівняйте моди", 1, story)
    story.append(p(
        "Збалансуйте, застосуйте малі збурення (чи скористайтеся утилітою "
        "лінеаризації) та вилучіть власні значення, потім порівняйте з "
        "аналітичними модами, які прогнозують похідні (див. розділ про "
        "власні моди):"))
    for b in [
        "<b>Короткоперіодична</b> частота/демпфування, зумовлені C<sub>m" +
        _g("α") + "</sub> та C<sub>mq</sub>+C<sub>m" + _g("α̇") + "</sub> — "
        "пряма перевірка похідної демпфування тангажа, яку ви вилучили.",
        "<b>Фугоїдна</b> — низька частота, слабко демпфована; чутлива до опору "
        "та піднімальної сили, отже, до статичної поляри.",
        "<b>Голландський крок</b> від C<sub>n" + _g("β") + "</sub>, "
        "C<sub>nr</sub>, C<sub>l" + _g("β") + "</sub>; <b>аперіодичний крен</b> "
        "від C<sub>lp</sub>; <b>спіраль</b> від C<sub>l" + _g("β") + "</sub>, "
        "C<sub>nr</sub>, C<sub>lr</sub>, C<sub>n" + _g("β") + "</sub>.",
        "Мода, що є нестійкою, коли не мала б бути, або частота, хибна на "
        "порядок, майже завжди простежується до хибного знаку чи відсутньої "
        "похідної за кутовою швидкістю.",
    ]:
        story.append(bullet(b))

    heading("Порівняння з незалежними даними", 1, story)
    story.append(p(
        "Ранжуйте свою впевненість: льотні випробування &gt; аеродинамічна "
        "труба &gt; високоточна CFD &gt; панельні методи/VLM (AVL, XFLR5) "
        "&gt; емпіричні (DATCOM). Використовуйте дешевші методи, щоб "
        "обмежити CFD, та дорогі дані, щоб її скоригувати:"))
    for b in [
        "Перехресно перевірте C<sub>L" + _g("α") + "</sub>, C<sub>m" +
        _g("α") + "</sub>, C<sub>l" + _g("β") + "</sub>, C<sub>nr</sub>, "
        "&hellip; з оцінками AVL (вихорова решітка) та USAF DATCOM — вони "
        "мають збігатися за знаком та грубою величиною.",
        "Там, де існують дані з аеродинамічної труби чи польоту, "
        "налаштовуйте отримані з CFD таблиці так, щоб вони збігалися "
        "(спершу поправки за Рейнольдсом та станом балансування).",
        "Поєднуйте джерела явно: напр. CFD для нелінійної піднімальної сили "
        "на великих " + _g("α") + ", AVL для лінійних похідних, DATCOM для "
        "похідної, яку не охопив жоден розрахунок. Документуйте походження "
        "кожного числа.",
    ]:
        story.append(bullet(b))

    heading("Застереження щодо екстраполяції", 1, story)
    for b in [
        "<b>Число Рейнольдса.</b> Запускайте CFD при польотному Re; "
        "піддослідне (зменшене) Re зсуває C<sub>D0</sub>, максимальну "
        "піднімальну силу та зривний " + _g("α") + ".",
        "<b>Мах.</b> Нестисливі коефіцієнти недійсні за M~0.3-0.5; додайте "
        "вимір таблиці за Махом для швидких літаків.",
        "<b>За межами даних.</b> JSBSim продовжує таблиці, утримуючи кінцеве "
        "значення сталим (без екстраполяції); забезпечте, щоб ваші таблиці "
        "охоплювали всю передбачену область, особливо зазривний режим та "
        "великий кут ковзання.",
        "<b>Лише абсолютно тверде тіло.</b> CFD на CAD ігнорує аеропружну "
        "деформацію та нестаціонарні/відривні ефекти поза межами "
        "квазістаціонарної моделі.",
    ]:
        story.append(bullet(b))

    heading("Цикл ітерацій", 1, story)
    story.append(p(
        "Верифікація рідко буває за один прохід. Здоровий робочий процес "
        "такий: побудувати таблиці з CFD &rarr; збалансувати &rarr; перевірити "
        "моди &rarr; порівняти з еталонними даними &rarr; виявити найгіршу "
        "розбіжність &rarr; додати чи скоригувати відповідальний розрахунок "
        "CFD чи таблицю &rarr; повторити. Оскільки кожен коефіцієнт — це "
        "ізольована, спостережувана "
        "<font face='Courier'>&lt;function&gt;</font> у дереві властивостей, "
        "JSBSim робить цей цикл швидким: ви можете спостерігати за кожним "
        "внеском наживо та точно вказати, який саме член хибний."))
    story.append(quote(
        "Польотна модель ніколи не буває завершеною — лише поступово менш "
        "хибною. CFD дає вам правдоподібну першу модель; балансування, власні "
        "моди та реальні дані підказують, куди витратити наступний "
        "розрахунок."))


# ============================================================================
# Part IV — Building a highly realistic FDM: data, subsystems, and tuning
# ============================================================================


def add_part_iv_separator(story):
    story.append(PageBreak())
    story.append(Spacer(1, 52 * mm))
    story.append(Paragraph("Частина IV", ParagraphStyle(
        "PartLabel4", fontName="DejaVu-Bold", fontSize=18,
        textColor=colors.HexColor("#1d5d9b"), alignment=TA_CENTER,
        spaceAfter=12)))
    story.append(Paragraph(
        "Побудова високодостовірної моделі динаміки польоту (FDM):<br/>дані, підсистеми та налаштування",
        ParagraphStyle(
            "PartTitle4", fontName="DejaVu-Bold", fontSize=25,
            textColor=colors.HexColor("#0d3b66"), alignment=TA_CENTER,
            leading=31)))
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "Частини I-III дають вам рушій, математику та спосіб генерувати "
        "аеродинамічні дані. Однак достовірність криється в деталях: звідки "
        "беруться дані та як ви їх поєднуєте, як будуються й налаштовуються "
        "підсистеми маси, силової установки, шасі, керування польотом і "
        "датчиків, як відтворюються звалювання та штопор, як ви пишете "
        "сценарії випробувань і звіряєте результат із опублікованими льотними "
        "та пілотажними характеристиками. Частина IV — це практична половина "
        "посібника, дистиляція вихідного коду JSBSim, довідкового керівництва, "
        "вікі FlightGear та форумів розробників у конкретний рецепт планера, "
        "який упізнав би льотчик-випробувач. Кожен розділ про підсистему "
        "прив’язаний до вихідного коду, тож ви точно знаєте, який елемент XML "
        "керує яким рядком коду.",
        ParagraphStyle("PartIntro4", parent=BODY_STYLE,
                       alignment=TA_CENTER, fontSize=11, leading=15,
                       leftIndent=22 * mm, rightIndent=22 * mm)))


# ----------------------------------------------------------------------------
def add_fdm_data_sources(story):
    story.append(PageBreak())
    heading("Джерела аеродинамічних даних і сходинки достовірності", 0, story)
    story.append(p(
        "Модель JSBSim настільки реалістична, наскільки реалістичні числа в її "
        "таблицях. Перш ніж щось налаштовувати, ви маєте вирішити, звідки "
        "беруться коефіцієнти, бо саме це задає стелю достовірності (fidelity). "
        "Методи утворюють сходи: кожна сходинка коштує більше і повертає більше "
        "правди. Хороша модель зазвичай <i>поєднує</i> сходинки — дешеві методи "
        "для більшої частини діапазону, дорогі — там, де дешеві методи не "
        "працюють."))

    heading("Сходинки достовірності", 1, story)
    data = [
        ["Метод", "Достовірність", "Зусилля", "Найкраще підходить для"],
        ["Aeromatic / Aeromatic++", "низька", "хвилини",
         "перша літаюча модель зі специфікацій рівня POH"],
        ["USAF Digital DATCOM", "низька-середня", "години",
         "напівемпіричні похідні для звичайних компонувань; експорт XML"],
        ["Вихрова решітка (AVL, XFLR5)", "середня", "години",
         "лінійні похідні, ефективність керування, нейтральна точка (приєднана течія)"],
        ["Панельний + в’язкий (VSPAero)", "середня", "години-дні",
         "поляри та похідні на основі геометрії з моделі OpenVSP"],
        ["RANS CFD (OpenFOAM)", "середня-висока", "дні-тижні",
         "нелінійні великі " + _g("α") + ", стисливість, опір (див. Частину III)"],
        ["Аеродинамічна труба", "висока", "тижні+",
         "надійні статичні дані + дані вимушених коливань на реальній моделі"],
        ["Льотні випробування (system ID)", "найвища", "програма",
         "істина; використовується для корекції всього вищезазначеного"],
    ]
    story.append(_oftab(data, [3.7 * cm, 2.0 * cm, 2.0 * cm, 8.0 * cm]))

    heading("Зчитування даних із POH або сертифіката типу", 1, story)
    story.append(p(
        "Керівництво з льотної експлуатації (POH), документ даних сертифіката "
        "типу та виробничий тривид — це найдешевші реальні дані, які ви "
        "будь-коли отримаєте. Вони фіксують геометрію (розмах, площу, хорду, "
        "довжини), маси та діапазон CG, а також опорні точки характеристик, до "
        "яких можна налаштовуватися: швидкості звалювання (чиста конфігурація "
        "та з закрилками), V<sub>x</sub>/V<sub>y</sub> і швидкопідйомність, "
        "крейсерську TAS і витрату палива, практичну стелю, граничну "
        "швидкість і дистанції зльоту/посадки. Кожна з них — це обмеження, яке "
        "має відтворювати готова FDM."))

    heading("Digital DATCOM", 1, story)
    story.append(p(
        "USAF Stability and Control Digital DATCOM — це напівемпіричний код: з "
        "геометричного опису він повертає поздовжні коефіцієнти "
        "C<sub>D</sub>, C<sub>L</sub>, C<sub>m</sub>, "
        "C<sub>N</sub>, C<sub>A</sub> та ключові похідні "
        "dC<sub>L</sub>/d" + _g("α") + ", dC<sub>m</sub>/d" + _g("α") + ", "
        "dC<sub>Y</sub>/d" + _g("β") + ", dC<sub>n</sub>/d" + _g("β") + ", "
        "dC<sub>l</sub>/d" + _g("β") + ". Сучасні збірки експортують таблицю "
        "даних XML, яку безпосередньо споживають JSBSim і FlightGear, а "
        "Aerospace Toolbox у MATLAB може імпортувати її вивід. Він швидкий та "
        "ідеальний для звичайних компонувань, але це інтерполяція по базі даних "
        "результатів з аеродинамічної труби, тож він найслабший саме там, де "
        "планери стають цікавими: великі " + _g("α") + ", незвичні форми в "
        "плані, сильна інтерференція."))

    heading("Методи вихрової решітки та панельні методи", 1, story)
    story.append(p(
        "<b>AVL</b> Марка Дрели та керований графічним інтерфейсом <b>XFLR5</b> "
        "розв’язують задачу вихрової решітки за секунди й дають чудові лінійні "
        "похідні, ефективність керування та нейтральну точку для приєднаної "
        "течії — ідеально для більшої частини крейсерського діапазону та для "
        "перехресної перевірки CFD. <b>VSPAero</b>, прив’язаний до геометрії "
        "OpenVSP, додає активний диск і нарощування в’язкого опору й має "
        "задокументований спільнотою робочий процес для створення "
        "аеродинамічних таблиць JSBSim. Їхня спільна сліпа зона — це "
        "відривання течії: жоден з них не моделює звалювання чи зазвалювальний "
        "режим, тож вище лінійного діапазону їх необхідно доповнювати даними "
        "CFD, труби чи емпіричними даними."))

    heading("Аеродинамічна труба та льотні випробування", 1, story)
    story.append(p(
        "Дані з аеродинамічної труби — статичні розгортки плюс запуски "
        "вимушених коливань для похідних демпфування — це класичне джерело "
        "високої достовірності. Льотні випробування — це найвищий авторитет: "
        "через <i>ідентифікацію параметрів</i> (підгонку похідних до виміряних "
        "відгуків на здвоєний імпульс/розгортку) ви видобуваєте реальні похідні "
        "стійкості й керованості та використовуєте їх для корекції моделі. "
        "Невизначеність цих похідних можна обмежити розгортками Монте-Карло, "
        "щоб показати, що модель залишається коректною в усьому правдоподібному "
        "діапазоні."))

    heading("Поєднання джерел і подібні літаки", 1, story)
    story.append(p(
        "Реальні моделі гібридні: лінійне ядро з AVL/DATCOM, нелінійні "
        "піднімальна сила і опір на великих " + _g("α") + " із CFD чи даних "
        "труби, похідні демпфування з вимушених коливань і фінальне "
        "калібрування за льотними випробуваннями. Коли для вашого літака немає "
        "даних, запозичте їх у <i>подібного</i> — зі схожою конфігурацією, "
        "видовженням і призначенням — і масштабуйте за геометрією; це набагато "
        "краще за здогад і є стандартною практикою спільноти JSBSim. Хоч би "
        "якою була суміш, фіксуйте походження кожного числа; саме цей слід "
        "аудиту дозволяє пізніше налагодити модель, що поводиться неправильно."))
    story.append(quote(
        "Колективна мудрість спільноти зафіксована в документах на кшталт "
        "&quot;A Journal for the Creation and Refinement of a JSBSim Aircraft "
        "Flight Model&quot; — прочитайте один із них, перш ніж братися за свій "
        "перший планер."))


# ----------------------------------------------------------------------------
def add_fdm_aeromatic(story):
    story.append(PageBreak())
    heading("Aeromatic: первинне створення літаючої моделі", 0, story)
    story.append(p(
        "Aeromatic — це найшвидший шлях від чистого аркуша до літака, який "
        "літає. Він запитує мінімальний набір специфікацій і генерує "
        "правдоподібні файли конфігурації JSBSim, використовуючи спрощувальні "
        "припущення. Існує два різновиди: оригінальний вебінструмент (PHP) на "
        "jsbsim.sourceforge.net та потужніша програма командного рядка на C++ "
        "<font face='Courier'>aeromatic++</font>, що постачається в "
        "<font face='Courier'>utils/aeromatic++/</font>. Для будь-чого "
        "серйознішого за іграшку використовуйте версію на C++."))

    heading("Що ви йому подаєте", 1, story)
    story.append(p(
        "Що кращі ваші вхідні дані, то менше Aeromatic здогадується. Надайте "
        "якомога більше з POH:"))
    for b in [
        "Клас літака (планер, легкий одномоторний, транспортний, винищувач, "
        "&hellip;) та повну масу.",
        "Геометрію: розмах крила, площу крила, довжину; наявність керівних "
        "поверхонь.",
        "Тип двигуна та потужність/тягу; кількість двигунів; гвинт чи реактивний.",
        "Опорні точки характеристик там, де інструмент їх приймає (крейсерська, "
        "V<sub>stall</sub>).",
    ]:
        story.append(bullet(b))

    heading("Що він створює", 1, story)
    story.append(p(
        "Повний стартовий набір: <b>файл літака</b> (метрики, маса і "
        "центрування, параметричний блок аеродинаміки, реакції опори та базова "
        "система керування польотом), <b>файл двигуна</b> і — для гвинтових "
        "літаків — <b>файл рушія/гвинта</b>. Аеродинаміка будується з "
        "підручникових співвідношень (наближено еліптична крива піднімальної "
        "сили, параболічна поляра опору, оцінки похідних за видовженням і "
        "об’ємом хвостового оперення), і саме тому результат літає, але ще не "
        "відповідає жодному конкретному планеру."))

    heading("Припущення та обмеження", 1, story)
    for b in [
        "<b>Один тип двигуна на модель.</b> Змішану силову установку (напр. "
        "поршневий + реактивний) доводиться додавати вручну згодом.",
        "<b>Узагальнені похідні.</b> Похідні демпфування й керування — це "
        "емпіричні правила; заради достовірності замініть їх значеннями з "
        "DATCOM/CFD/льотних випробувань.",
        "<b>Лінійна, симетрична аеродинаміка.</b> Стандартна вісь рискання не "
        "залежить від кута атаки, тож щойно створена модель Aeromatic не буде "
        "реалістично штопорити, доки ви не додасте члени C<sub>n</sub>(" +
        _g("α") + ", " + _g("β") + ") (див. розділ про звалювання/штопор).",
    ]:
        story.append(bullet(b))

    heading("Робочий процес уточнення та поширені пастки", 1, story)
    story.append(p(
        "Ставтеся до виводу Aeromatic як до риштування: домогтеся, щоб модель "
        "балансувалася й літала, а потім замінюйте таблиці й похідні джерело за "
        "джерелом, повторно перевіряючи після кожної зміни. Вікі FlightGear "
        "застерігає, що &quot;легко зробити зміни, які призведуть до нелітаючої "
        "FDM&quot; — двома класичними помилками є:"))
    for b in [
        "<b>Порушення лівої/правої симетрії</b> при переміщенні розташувань — "
        "зміщене шасі, бак чи точкова маса вносять фантомний нахил крену/рискання.",
        "<b>Зміщення CG надто далеко від AERORP</b> — велике зміщення CG "
        "відносно аеродинамічного орієнтира псує нарощування моменту тангажа й "
        "запас поздовжньої стійкості, часто породжуючи незбалансовуваний чи "
        "розбіжний літак.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_fdm_mass_balance(story):
    story.append(PageBreak())
    heading("Достовірність маси, центрування, інерції та палива", 0, story)
    story.append(p(
        "Ніщо не впливає на те, як літає літак, більше, ніж розташування його "
        "маси. CG задає запас поздовжньої стійкості й балансування; тензор "
        "інерції задає обертальний відгук і частоти власних рухів; вигоряння "
        "палива переміщує CG у польоті. Зробіть цей розділ неправильно — і "
        "жодне аеродинамічне налаштування не зробить модель правильною на "
        "відчуття."))

    heading("Блок mass_balance", 1, story)
    story.append(p(
        "Порожні інерції задаються відносно CG порожнього літака у "
        "конструктивній системі координат; JSBSim додає точкові маси та паливо "
        "автоматично. Зверніть увагу на знакову угоду для "
        "<font face='Courier'>ixz</font>: JSBSim очікує <i>фактичний</i> "
        "відцентровий момент інерції (для більшості літаків додатний зв’язок "
        "«на кабрування» — це від’ємний ixz)."))
    code("""\
<mass_balance>
  <ixx unit="SLUG*FT2">  948 </ixx>
  <iyy unit="SLUG*FT2"> 1346 </iyy>
  <izz unit="SLUG*FT2"> 1967 </izz>
  <ixz unit="SLUG*FT2">    0 </ixz>          <!-- XZ product of inertia -->
  <emptywt unit="LBS"> 1500 </emptywt>
  <location name="CG" unit="IN"> <x>41.0</x><y>0</y><z>36.5</z> </location>
  <pointmass name="pilot">
    <weight unit="LBS">180</weight>
    <location unit="IN"> <x>36</x><y>-14</y><z>40</z> </location>
  </pointmass>
</mass_balance>""")

    heading("Оцінювання тензора інерції", 1, story)
    story.append(p(
        "Якщо у вас є CAD, беріть інерції прямо з нього відносно CG. Інакше "
        "оцініть за радіусами інерції: I = m&middot;k&sup2;, де k — частка "
        "розмаху (крен), довжини (тангаж) та їх поєднання (рискання). Roskam "
        "та USAF DATCOM наводять у таблицях безрозмірні радіуси інерції за "
        "класом літака — це набагато краща відправна точка, ніж здогад. "
        "Правило перевірки для звичайних літаків: I<sub>zz</sub> &gt; "
        "I<sub>yy</sub> &gt; I<sub>xx</sub> і I<sub>zz</sub> &asymp; "
        "I<sub>xx</sub> + I<sub>yy</sub>."))

    heading("Точкові маси та компонування завантаження", 1, story)
    story.append(p(
        "Екіпаж, пасажири, корисне навантаження та підвіски — це елементи "
        "<font face='Courier'>&lt;pointmass&gt;</font>; JSBSim підсумовує їхню "
        "масу, зміщує CG та доповнює тензор інерції їхніми внесками за теоремою "
        "про паралельні осі. Моделюйте випадки завантаження, які вас цікавлять "
        "(передній CG, задній CG, максимальна повна маса) — керованість помітно "
        "різниться між ними, а саме у випадку заднього CG запаси стійкості "
        "стають тонкими."))

    heading("Паливні баки та зміщення CG у польоті", 1, story)
    story.append(p(
        "Кожен <font face='Courier'>&lt;tank&gt;</font> має розташування, "
        "ємність і вміст; модель силової установки накопичує "
        "&Sigma;(положення бака &times; вміст бака) у бюджет маси "
        "(<font face='Courier'>FGPropulsion.cpp:579-586</font>), тож вигоряння "
        "палива переміщує CG у реальному часі. Важелі достовірності баків:"))
    for b in [
        "<font face='Courier'>&lt;capacity&gt;</font> / "
        "<font face='Courier'>&lt;contents&gt;</font> у LBS або KG; "
        "<font face='Courier'>&lt;density&gt;</font> або іменований "
        "<font face='Courier'>&lt;type&gt;</font> (AVGAS, JET-A).",
        "<font face='Courier'>&lt;priority&gt;</font> та список "
        "<font face='Courier'>&lt;feed&gt;</font> двигуна задають, які баки "
        "спорожнюються першими — моделюйте реальне керування паливом, щоб "
        "відтворити міграцію CG.",
        "<font face='Courier'>&lt;unusable&gt;</font> та "
        "<font face='Courier'>&lt;standpipe&gt;</font> резервують паливо, яке "
        "не можна спалити чи злити — важливо для достовірності дальності та "
        "тривалості польоту (<font face='Courier'>FGTank.h:113-142</font>).",
    ]:
        story.append(bullet(b))
    story.append(quote(
        "Модель, яка чудово балансується з повним паливом і стає "
        "незбалансовуваною майже порожньою, майже завжди має бак не на тому "
        "місці: звірте спричинений паливом хід CG з діапазоном POH."))


# ----------------------------------------------------------------------------
def add_fdm_propulsion_practice(story):
    story.append(PageBreak())
    heading("Достовірність силової установки на практиці", 0, story)
    story.append(p(
        "JSBSim відокремлює <i>двигун</i> (виробляє потужність/тягу) від "
        "<i>рушія</i> (перетворює її на силу: гвинт, сопло, ротор чи прямо) та "
        "<i>баків</i> (тримають паливо). Блок "
        "<font face='Courier'>&lt;propulsion&gt;</font> з’єднує їх докупи; "
        "означення двигуна й рушія містяться в окремих файлах, що "
        "завантажуються з теки літака <font face='Courier'>Engines/</font> або "
        "з глобальної бібліотеки <font face='Courier'>engine/</font> "
        "(<font face='Courier'>FGPropulsion.cpp:389-489</font>)."))
    code("""\
<propulsion>
  <engine file="Continental A-65-8">
    <feed>0</feed>                       <!-- tank index this engine draws -->
    <thruster file="CM7445_MCCauley">
      <location unit="IN"> <x>-5</x><y>0</y><z>0</z> </location>
      <orient   unit="DEG"> <roll>0</roll><pitch>0</pitch><yaw>0</yaw> </orient>
    </thruster>
  </engine>
  <tank type="FUEL" number="0">
    <location unit="IN"> <x>45</x><y>0</y><z>30</z> </location>
    <capacity unit="LBS">  108 </capacity>
    <contents unit="LBS">   90 </contents>
  </tank>
</propulsion>""")

    heading("Поршневі двигуни", 1, story)
    story.append(p(
        "Поршнева модель (<font face='Courier'>FGPiston</font>) формує тиск у "
        "впускному колекторі з мережі впускного імпедансу й обчислює потужність "
        "і витрату палива з робочого об’єму, обертів, об’ємної ефективності та "
        "BSFC. Практичний порядок налаштування, згідно з вікі FlightGear, "
        "такий:"))
    for b in [
        "<b><font face='Courier'>ram-air-factor</font></b> спочатку, щоб "
        "влучити в правильний крейсерський тиск у впускному колекторі.",
        "<b><font face='Courier'>volumetric-efficiency</font></b> далі — "
        "основний регулятор витрати палива за заданих MAP/RPM (наддувні двигуни "
        "можуть перевищувати 1.0).",
        "<b><font face='Courier'>bsfc</font></b> останнім, щоб узгодити "
        "потужність (означення <font face='Courier'>&lt;bsfc&gt;</font> "
        "перекриває вбудований розрахунок кінських сил).",
    ]:
        story.append(bullet(b))
    story.append(p(
        "<font face='Courier'>&lt;minmp&gt;</font>/"
        "<font face='Courier'>&lt;idlerpm&gt;</font> задають нахил відгуку на "
        "холостому ходу / газі; <font face='Courier'>&lt;maxmp&gt;</font>/"
        "<font face='Courier'>&lt;maxrpm&gt;</font> задають впускний опір; "
        "елементи <font face='Courier'>&lt;numboostspeeds&gt;</font> та "
        "<font face='Courier'>ratedboost/ratedpower/ratedaltitude</font> "
        "моделюють нагнітачі "
        "(<font face='Courier'>FGPiston.h:66-112</font>). Реальний, повний "
        "приклад (згенерований Aeromatic, потім перевірений вручну):"))
    code("""\
<piston_engine name="Continental A-65-8">
  <minmp unit="INHG">         10.0 </minmp>
  <maxmp unit="INHG">         28.5 </maxmp>
  <displacement unit="IN3">  171.0 </displacement>
  <maxhp>                       65 </maxhp>
  <cycles>                     4.0 </cycles>
  <idlerpm>                  700.0 </idlerpm>
  <maxrpm>                  2800.0 </maxrpm>
  <volumetric-efficiency>     0.85 </volumetric-efficiency>
  <stroke unit="IN">         3.625 </stroke>
  <bore   unit="IN">         3.875 </bore>
  <cylinders>                    4 </cylinders>
  <compression-ratio>          6.3 </compression-ratio>
</piston_engine>""")

    heading("Турбіни: турбореактивні та турбовентиляторні двигуни", 1, story)
    story.append(p(
        "<font face='Courier'>FGTurbine</font> моделює два каскади (N1 — "
        "вентилятор, N2 — газогенератор) із запізнено-фільтрованим "
        "розкручуванням/гальмуванням, тягою за пошуком у таблиці за числом Маха "
        "та висотою й опціональним форсуванням. Ключові регулятори "
        "(<font face='Courier'>FGTurbine.h:84-109</font>): "
        "<font face='Courier'>&lt;milthrust&gt;</font>/"
        "<font face='Courier'>&lt;maxthrust&gt;</font> (без форсажу / з "
        "форсажем), <font face='Courier'>&lt;bypassratio&gt;</font>, "
        "<font face='Courier'>&lt;tsfc&gt;</font>/"
        "<font face='Courier'>&lt;atsfc&gt;</font> (витрата палива), "
        "<font face='Courier'>&lt;idlen1/2&gt;</font>, "
        "<font face='Courier'>&lt;maxn1/2&gt;</font>, часи розкручування "
        "<font face='Courier'>&lt;n1spinup&gt;</font>/"
        "<font face='Courier'>&lt;n2spinup&gt;</font> та "
        "<font face='Courier'>&lt;augmented&gt;</font>/"
        "<font face='Courier'>&lt;augmethod&gt;</font> для форсажної камери. "
        "Таблиці тяги — це серце достовірності; беріть їх з характеристик "
        "двигуна (engine deck), якщо можете. Заголовок J79 (F-4):"))
    code("""\
<turbine_engine name="J79">
  <milthrust>  10000.0 </milthrust>
  <maxthrust>  15800.0 </maxthrust>     <!-- with afterburner -->
  <bypassratio>    0.0 </bypassratio>
  <tsfc>          0.98 </tsfc>
  <atsfc>         1.96 </atsfc>          <!-- afterburning TSFC -->
  <idlen2>        53.0 </idlen2>
  <maxn1>        100.0 </maxn1> <maxn2> 100.0 </maxn2>
  <augmented>        1 </augmented> <augmethod> 1 </augmethod>
  <!-- IdleThrust / MilThrust / MaxThrust tables vs mach, altitude ... -->
</turbine_engine>""")

    heading("Турбогвинтові, електричні та ракетні двигуни", 1, story)
    for b in [
        "<b>Турбогвинтовий</b> (<font face='Courier'>FGTurboProp</font>): один "
        "каскад, бета-діапазон нижче <font face='Courier'>&lt;betarangeend&gt;"
        "</font>, моделювання ITT, обмежувач крутного моменту IELU та "
        "потужність (<font face='Courier'>&lt;maxpower&gt;</font>, "
        "<font face='Courier'>&lt;psfc&gt;</font>), що приводить гвинт "
        "постійних обертів.",
        "<b>Електричний</b> (<font face='Courier'>FGElectric</font>): єдина "
        "<font face='Courier'>&lt;power&gt;</font> у ватах, лінійна за газом, "
        "нульове вигоряння палива — природний вибір для eVTOL та електричних "
        "БПЛА.",
        "<b>Ракетний</b> (<font face='Courier'>FGRocket</font>): питомий "
        "імпульс <font face='Courier'>&lt;isp&gt;</font> та опціональна "
        "таблиця тяги від часу; споживає баки і палива, і окисника.",
    ]:
        story.append(bullet(b))

    heading("Паливна система та узгодження характеристик", 1, story)
    story.append(p(
        "Паливо споживається за пріоритетом: баки з найменшим числом "
        "<font face='Courier'>&lt;priority&gt;</font> спорожнюються першими, а "
        "двигун живиться лише з баків у своєму списку "
        "<font face='Courier'>&lt;feed&gt;</font> "
        "(<font face='Courier'>FGPropulsion.cpp:169-263</font>). Перевіряйте "
        "силову установку за трьома опорними точками з POH / характеристик "
        "двигуна: статична тяга на рівні моря чи злітна потужність, крейсерська "
        "витрата палива на відомій висоті та режимі потужності й найкраща "
        "швидкопідйомність. Налаштовуйте "
        "<font face='Courier'>volumetric-efficiency</font>/"
        "<font face='Courier'>tsfc</font> за витратою палива, а коефіцієнти "
        "тяги/потужності — за швидкопідйомністю та максимальною швидкістю."))


# ----------------------------------------------------------------------------
def add_fdm_propellers(story):
    story.append(PageBreak())
    heading("Повітряні гвинти, рушії та регулятор постійних обертів", 0,
            story)
    story.append(p(
        "Для гвинтових літаків рушій — це місце, де потужність двигуна стає "
        "тягою, і він є поширеним джерелом нереалістичної поведінки. "
        "<font face='Courier'>FGPropeller</font> працює в коефіцієнтній формі, "
        "точно як аеродинаміка: безрозмірні коефіцієнти тяги й потужності "
        "наводяться в таблицях залежно від відносної ходи та кута установки "
        "лопаті."))

    heading("Файл повітряного гвинта", 1, story)
    story.append(p(
        "Геометрія та обмеження "
        "(<font face='Courier'>FGPropeller.h:59-101</font>): "
        "<font face='Courier'>&lt;diameter&gt;</font>, "
        "<font face='Courier'>&lt;numblades&gt;</font>, полярний момент "
        "<font face='Courier'>&lt;ixx&gt;</font> (задає інерцію розкручування "
        "та гіроскопічний момент), <font face='Courier'>&lt;gearratio&gt;</font>, "
        "діапазон кута установки <font face='Courier'>&lt;minpitch&gt;</font>/"
        "<font face='Courier'>&lt;maxpitch&gt;</font> та регульований діапазон "
        "обертів <font face='Courier'>&lt;minrpm&gt;</font>/"
        "<font face='Courier'>&lt;maxrpm&gt;</font>, плюс множники "
        "налаштування <font face='Courier'>&lt;ct_factor&gt;</font>/"
        "<font face='Courier'>&lt;cp_factor&gt;</font>."))
    code("""\
<propeller name="CM7445" version="1.0">
  <ixx>        1.67 </ixx>
  <diameter unit="IN"> 74.0 </diameter>
  <numblades>     2 </numblades>
  <gearratio>   1.0 </gearratio>
  <minpitch>     10 </minpitch>
  <maxpitch>     25 </maxpitch>           <!-- fixed-pitch: omit governor -->
  <table name="C_THRUST" type="internal">
    <independentVar lookup="row">advance-ratio</independentVar>
    <tableData> 0.0  0.0653
                0.4  0.0524
                0.8  0.0241
                1.2 -0.0140 </tableData>
  </table>
  <table name="C_POWER" type="internal">
    <independentVar lookup="row">advance-ratio</independentVar>
    <tableData> 0.0  0.0383
                0.4  0.0378
                0.8  0.0291
                1.2  0.0097 </tableData>
  </table>
</propeller>""")

    heading("Коефіцієнти, відносна хода та число Маха", 1, story)
    story.append(p(
        "Відносна хода J = V/(n&middot;D) (n у об/с) — це &quot;кут атаки&quot; "
        "гвинта. Тяга й потужність випливають із:"))
    math("T = C<sub>T</sub>(J)&middot;" + _g("ρ") + "&middot;n&sup2;"
         "&middot;D&#x2074;        P = C<sub>P</sub>(J)&middot;" + _g("ρ") +
         "&middot;n&sup3;&middot;D&#x2075;")
    story.append(p(
        "Опціональні таблиці <font face='Courier'>CT_MACH</font>/"
        "<font face='Courier'>CP_MACH</font> (індексовані за гвинтовим числом "
        "Маха на кінці лопаті) відображають втрати на стисливість, коли кінці "
        "лопатей наближаються до швидкості звуку "
        "(<font face='Courier'>FGPropeller.h:333-334</font>). Індукована "
        "швидкість розв’язується з імпульсної теорії "
        "(<font face='Courier'>FGPropeller.cpp:256-261</font>)."))

    heading("Регулятор постійних обертів", 1, story)
    story.append(p(
        "Блок постійних обертів утримує цільові оберти, змінюючи кут установки "
        "лопаті між <font face='Courier'>minpitch</font> та "
        "<font face='Courier'>maxpitch</font>. Розподіл органів керування "
        "пілота такий самий, як на реальному літаку: <b>газ</b> задає тиск у "
        "впускному колекторі (потужність), <b>важіль гвинта</b> задає "
        "регульовані оберти, а <b>якість суміші</b> задає співвідношення "
        "паливо/повітря. Установіть <font face='Courier'>&lt;constspeed&gt;1&lt;/"
        "constspeed&gt;</font> та розумну смугу обертів; регулятор тоді змінює "
        "кут установки, щоб утримувати оберти зі зміною повітряної швидкості та "
        "потужності."))

    heading("P-фактор, напрям, авторотація гвинта та реверс", 1, story)
    for b in [
        "<b><font face='Courier'>&lt;sense&gt;</font></b> (&plusmn;1) задає "
        "напрям обертання; він керує закруткою струменя за гвинтом та реакцією "
        "крутного моменту двигуна, проти якої літак має балансуватися.",
        "<b><font face='Courier'>&lt;p_factor&gt;</font></b> зміщує точку "
        "прикладання тяги залежно від кута атаки, породжуючи характерне "
        "рискання на великих " + _g("α") + "/великій потужності "
        "(<font face='Courier'>FGPropeller.cpp:266-278</font>).",
        "<b>Авторотація гвинта (windmilling)</b> (від’ємна тяга, великий опір) "
        "виникає природно, коли J робить C<sub>T</sub> від’ємним; "
        "<b>флюгування</b> (<font face='Courier'>maxpitch</font> вирівняно з "
        "потоком) знижує цей опір заради достовірності при відмові двигуна.",
        "<b>Реверс / бета</b>-діапазон дає гальмування на землі; поєднайте його "
        "з турбогвинтовим <font face='Courier'>&lt;betarangeend&gt;</font> чи "
        "<font face='Courier'>&lt;reversepitch&gt;</font>.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_fdm_gear(story):
    story.append(PageBreak())
    heading("Шасі та керування рухом по землі", 0, story)
    story.append(p(
        "Керування рухом по землі — це місце, де розвалюються багато інакше "
        "хороших моделей: літак підстрибує, ковзає, входить у некерований "
        "розворот (ground-loop) чи провалюється крізь злітно-посадкову смугу. "
        "Шасі JSBSim — це амортизаційна стійка з пружиною й демпфером із "
        "моделлю тертя, означена як елементи "
        "<font face='Courier'>&lt;contact&gt;</font> всередині "
        "<font face='Courier'>&lt;ground_reactions&gt;</font> "
        "(<font face='Courier'>FGLGear.cpp</font>, "
        "<font face='Courier'>FGGroundReactions.cpp:135-156</font>)."))

    heading("Закон сили стійки", 1, story)
    story.append(p(
        "Кожна стійка обчислює нормальну силу зі стиснення та швидкості "
        "стиснення (<font face='Courier'>FGLGear.cpp:624-653</font>). Сила — це "
        "пружний член плюс демпфувальний член, обмежений так, щоб стійка могла "
        "лише штовхати:"))
    math("F<sub>strut</sub> = &minus;( k&middot;x + c&middot;v ),   "
         "clamped to F &le; 0")
    story.append(p(
        "з окремими коефіцієнтами для стиснення ("
        "<font face='Courier'>&lt;damping_coeff&gt;</font>) та віддачі "
        "(<font face='Courier'>&lt;damping_coeff_rebound&gt;</font>) і "
        "опціональним <font face='Courier'>type=\"SQUARE\"</font>, який робить "
        "демпфування пропорційним v&sup2; заради сильнішого контролю над "
        "екстремальними стисненнями. Типовий контакт BOGEY:"))
    code("""\
<contact type="BOGEY" name="LEFT_MAIN">
  <location unit="IN"> <x>58</x><y>-50</y><z>-18</z> </location>
  <static_friction>  0.80 </static_friction>
  <dynamic_friction> 0.50 </dynamic_friction>
  <rolling_friction> 0.02 </rolling_friction>
  <spring_coeff         unit="LBS/FT">     5400 </spring_coeff>
  <damping_coeff        unit="LBS/FT/SEC">  160 </damping_coeff>
  <damping_coeff_rebound unit="LBS/FT/SEC"> 320 </damping_coeff_rebound>
  <max_steer unit="DEG">  0 </max_steer>       <!-- 0 = fixed, 360 = caster -->
  <brake_group> LEFT </brake_group>
  <retractable> 1 </retractable>
</contact>""")

    heading("Тертя, керування поворотом і гальма", 1, story)
    for b in [
        "<b>Тертя</b> використовує статичний, динамічний коефіцієнти та "
        "коефіцієнт тертя кочення; гальмування додає частку (static &minus; "
        "rolling), масштабовану положенням гальма "
        "(<font face='Courier'>FGLGear.cpp:588-594</font>). Бічна сила (у "
        "повороті) використовує «магічну формулу» Pacejka із вбудованими "
        "коефіцієнтами (жорсткість 0.06, форма 2.8, пік = статичний коефіцієнт, "
        "кривина 1.03), які можна перекрити таблицею "
        "<font face='Courier'>CORNERING_COEFF</font> "
        "(<font face='Courier'>FGLGear.cpp:596-615</font>).",
        "<b>Керування поворотом</b> задається через "
        "<font face='Courier'>&lt;max_steer&gt;</font>: 0&deg; = фіксоване, "
        "360&deg; (або <font face='Courier'>&lt;castered&gt;1</font>) = вільно "
        "орієнтоване, будь-що між = кероване за командою через "
        "<font face='Courier'>fcs/steer-cmd-norm</font> "
        "(<font face='Courier'>FGLGear.cpp:151-165</font>).",
        "<b>Групи гальм</b> LEFT/RIGHT/CENTER (NOSE/TAIL відображаються на "
        "CENTER) прив’язують шасі до "
        "<font face='Courier'>fcs/&hellip;-brake-cmd-norm</font> "
        "(<font face='Courier'>FGLGear.cpp:204-217</font>); диференціальне "
        "гальмування — це те, як літаки з хвостовим колесом і багато реактивних "
        "літаків керують поворотом на малій швидкості.",
        "<b>Контакти STRUCTURE</b> (законцівки крила, хвостовий костиль, "
        "мотогондоли) — це неколісні точки удару/тертя об землю; "
        "<b><font face='Courier'>&lt;retractable&gt;</font></b> прив’язує стійку "
        "до <font face='Courier'>gear/unit[i]/pos-norm</font>.",
    ]:
        story.append(bullet(b))

    heading("Поверхня землі", 1, story)
    story.append(p(
        "<font face='Courier'>FGSurface</font> надає "
        "<font face='Courier'>ground/solid</font> (вода чи суша — нетверда "
        "поверхня не дає ваги на колесах), "
        "<font face='Courier'>ground/bumpiness</font> (процедурну "
        "нерівність злітно-посадкової смуги) та множники коефіцієнта тертя й "
        "максимальної сили, усі з яких можна встановлювати окремо для кожної "
        "поверхні, щоб моделювати мокрі, обледенілі чи нерівні аеродроми "
        "(<font face='Courier'>FGSurface.cpp</font>)."))

    heading("Налаштування стабільної, реалістичної поведінки на землі", 1, story)
    for b in [
        "<b>Жорсткість пружини</b> &asymp; вага на стійку / статичне "
        "стиснення. Починайте з реального ходу стійки та статичного розподілу "
        "навантаження.",
        "<b>Використовуйте найм’якшу пружину, з якою можете змиритися.</b> "
        "Надто жорстке шасі з сильним демпфуванням вносить енергію на кожному "
        "часовому кроці й змушує літак підстрибувати — частий збій, про який "
        "повідомляють у списку розробників JSBSim.",
        "<b>Демпфування віддачі &ge; демпфування стиснення</b>, щоб поглинути "
        "посадку, не виштовхуючи літак назад у повітря; розгляньте "
        "<font face='Courier'>type=\"SQUARE\"</font>, щоб приборкати "
        "екстремальні приземлення.",
        "<b>Стежте за часовим кроком.</b> Жорстке шасі потребує малого "
        "<font face='Courier'>dt</font>; якщо стійка може стиснутися більше, "
        "ніж це фізично можливо за один крок, сили вибухають. JSBSim обмежує "
        "швидкість стиснення за крок, але м’яке шасі + малий dt — це надійне "
        "поєднання.",
        "<b>Інструментуйте це.</b> Записуйте "
        "<font face='Courier'>gear/unit[i]/compression-ft</font>, "
        "<font face='Courier'>&hellip;/WOW</font> та "
        "<font face='Courier'>&hellip;/compression-velocity-fps</font> під час "
        "приземлення, щоб точно бачити, що робить стійка.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_fdm_fcs(story):
    story.append(PageBreak())
    heading("Системи керування польотом на практиці", 0, story)
    story.append(p(
        "Система керування польотом відображає команди пілота на відхилення "
        "поверхонь. У JSBSim це набір <font face='Courier'>&lt;channel&gt;"
        "</font> із компонентів, що виконуються по порядку, кожен з яких читає "
        "й записує дерево властивостей, тож канал — це буквально діаграма "
        "проходження сигналу в XML (<font face='Courier'>FGFCS.cpp</font>, "
        "<font face='Courier'>FGFCSChannel.h</font>). Той самий механізм "
        "обслуговує три секції — "
        "<font face='Courier'>&lt;flight_control&gt;</font>, "
        "<font face='Courier'>&lt;system&gt;</font> та "
        "<font face='Courier'>&lt;autopilot&gt;</font>."))

    heading("Каталог компонентів", 1, story)
    data = [
        ["Компонент", "Елемент", "Ключові параметри / передавальна функція"],
        ["Чистий коефіцієнт підсилення", "pure_gain", "gain (константа чи властивість)"],
        ["Планований коефіцієнт", "scheduled_gain", "gain &times; table(schedule)"],
        ["Масштаб керівної поверхні", "aerosurface_scale",
         "відображення domain&rarr;range; cmd-norm &harr; surface-rad"],
        ["Суматор", "summer", "&Sigma; входів + bias, clipto"],
        ["Фільтр запізнення", "lag_filter", "C1/(s+C1)"],
        ["Випередження-запізнення / washout", "lead_lag_filter / washout_filter",
         "(C1 s+C2)/(C3 s+C4); s/(s+C1)"],
        ["Фільтр 2-го порядку", "second_order_filter", "повний біквад C1..C6"],
        ["Інтегратор", "integrator", "rect/trap/ab2/ab3, з тригером"],
        ["ПІД-регулятор", "pid", "kp, ki, kd; trigger (захист від насичення)"],
        ["Зона нечутливості", "deadband", "width, gain"],
        ["Перемикач", "switch", "перевірки з умовами AND/OR, default"],
        ["Кінематичний", "kinematic", "обмежений за швидкістю перехід між налаштуваннями"],
        ["Привод", "actuator", "lag, rate_limit, hysteresis, bias, fail"],
        ["Функція FCS", "fcs_function", "довільна &lt;function&gt;"],
    ]
    story.append(_oftab(data, [3.0 * cm, 4.6 * cm, 8.1 * cm]))
    story.append(p(
        "Кожен компонент підтримує <font face='Courier'>&lt;input&gt;</font> "
        "(додайте до властивості префікс <font face='Courier'>-</font>, щоб "
        "інвертувати), опціональний <font face='Courier'>&lt;output&gt;</font> "
        "для копіювання його результату в іншу властивість і "
        "<font face='Courier'>&lt;clipto&gt;</font> для його насичення."))

    heading("Шлях керування, від початку до кінця", 1, story)
    story.append(p(
        "Мінімальний механічний (reversible) канал тангажа: підсумовуємо "
        "команди пілота й балансування, обмежуємо до нормованого діапазону, "
        "масштабуємо до кута поверхні, потім публікуємо нормоване положення для "
        "анімації. З моделі OV-10 "
        "(<font face='Courier'>aircraft/OV10/OV10.xml:241-272</font>):"))
    code("""\
<channel name="Pitch">
  <summer name="Pitch Trim Sum">
    <input> fcs/elevator-cmd-norm </input>
    <input> fcs/pitch-trim-cmd-norm </input>
    <clipto> <min>-1</min> <max>1</max> </clipto>
  </summer>
  <aerosurface_scale name="Elevator Control">
    <input> fcs/pitch-trim-sum </input>
    <range> <min>-0.35</min> <max>0.35</max> </range>   <!-- radians -->
    <output> fcs/elevator-pos-rad </output>
  </aerosurface_scale>
  <aerosurface_scale name="Elevator Normalized">
    <input> fcs/elevator-pos-rad </input>
    <domain> <min>-0.35</min> <max>0.35</max> </domain>
    <range>  <min>-1</min>    <max>1</max>    </range>
    <output> fcs/elevator-pos-norm </output>
  </aerosurface_scale>
</channel>""")
    story.append(p(
        "Аеродинаміка потім читає <font face='Courier'>fcs/elevator-pos-rad"
        "</font> (або <font face='Courier'>-norm</font>) у своїх керівних "
        "приростах — FCS та аеродинаміка зустрічаються в дереві властивостей."))

    heading("Механічне, бустерне керування та fly-by-wire", 1, story)
    story.append(p(
        "Ті самі будівельні блоки масштабуються від легкого літака з тросами й "
        "блоками (команда прямо на поверхню, з передаточним відношенням і "
        "нелінійним <font face='Courier'>kinematic</font> для закрилків) до "
        "бустерної системи (додайте динаміку приводів) і до fly-by-wire "
        "(вставте фільтри, коефіцієнти підсилення та зворотний зв’язок, щоб "
        "сформувати відгук і додати систему покращення стійкості — наступний "
        "розділ). Моделюйте <i>передаточне відношення</i> та <i>змішування</i> "
        "керування явно: змішування спойлеронів, комбінації "
        "елевонів/рудеваторів і взаємозв’язки елерон-руль напряму — це лише "
        "суматори й коефіцієнти підсилення."))

    heading("Достовірність приводів", 1, story)
    story.append(p(
        "Реальні поверхні не миттєві. Компонент "
        "<font face='Courier'>&lt;actuator&gt;</font> "
        "(<font face='Courier'>FGActuator.h:54-122</font>) застосовує, по "
        "порядку, <font face='Courier'>&lt;lag&gt;</font>, "
        "<font face='Courier'>&lt;rate_limit&gt;</font> (опціонально різні для "
        "збільшення/зменшення), <font face='Courier'>&lt;deadband_width&gt;"
        "</font>, <font face='Courier'>&lt;hysteresis_width&gt;</font> "
        "(люфт) та <font face='Courier'>&lt;bias&gt;</font>. Обмеження "
        "швидкості важливі для пілотажних характеристик: недостатньо швидкий "
        "привод спричиняє розкачку, викликану пілотом (pilot-induced "
        "oscillation). Компонент також підтримує введення відмов "
        "(<font face='Courier'>fail_zero</font>, "
        "<font face='Courier'>fail_hardover</font>, "
        "<font face='Courier'>fail_stuck</font>) для випробувань систем."))


# ----------------------------------------------------------------------------
def add_fdm_autopilot(story):
    story.append(PageBreak())
    heading("Покращення стійкості, автопілоти та наведення", 0, story)
    story.append(p(
        "Щойно «голий» планер починає літати, автоматичне керування додає "
        "достовірності й корисності: демпфери, що гасять небажані рухи, "
        "автопілоти, що утримують стани, і наведення, що проводить маршрути. "
        "Усе це будується з тих самих компонентів FCS, розміщується в секції "
        "<font face='Courier'>&lt;autopilot&gt;</font> і за угодою керується "
        "властивостями <font face='Courier'>ap/</font>."))

    heading("Покращення стійкості", 1, story)
    story.append(p(
        "Демпфер рискання — канонічний приклад: подайте кутову швидкість "
        "рискання тіла через <font face='Courier'>washout_filter</font> (щоб "
        "він боровся з коливаннями, але не зі сталими, командними розворотами) "
        "та коефіцієнт підсилення на руль напряму. Відгук washout-фільтра "
        "s/(s+C1) пропускає перехідну кутову швидкість і блокує сталу складову "
        "— саме те, що приборкує слабко задемпфований голландський крок. "
        "Демпфери тангажа й крену подають q та p аналогічно. Оскільки "
        "покращення підсумовується в той самий канал поверхні, що й у пілота, "
        "будуйте його як додатковий вхід <font face='Courier'>summer</font>."))

    heading("Канали автопілота з ПІД-регуляторами", 1, story)
    story.append(p(
        "Режими утримання — це ПІД-контури, замкнені на похибці стану. "
        "Вирівнювач крил автопілота C-172 показує цей прийом — реалістичний "
        "<font face='Courier'>sensor</font> на куті крену, "
        "<font face='Courier'>switch</font>, що вмикає режим, та "
        "<font face='Courier'>pid</font>, чий <font face='Courier'>"
        "&lt;trigger&gt;</font> забезпечує захист від насичення інтегратора "
        "(<font face='Courier'>aircraft/c172x/c172ap.xml</font>):"))
    code("""\
<channel name="Roll wing leveler">
  <sensor name="fcs/attitude/sensor/phi-rad">
    <input> attitude/phi-rad </input>
    <lag> 0.50 </lag>
    <noise variation="PERCENT" distribution="GAUSSIAN"> 0.05 </noise>
    <bias> 0.001 </bias>
  </sensor>
  <switch name="fcs/wing-leveler-ap-on-off">
    <default value="-1"/>
    <test value="0"> ap/attitude_hold == 1 </test>
  </switch>
  <pid name="fcs/roll-ap-error-pid">
    <input> attitude/phi-rad </input>
    <kp> ap/roll-pid-kp </kp>
    <ki> ap/roll-pid-ki </ki>
    <kd> ap/roll-pid-kd </kd>
    <trigger> fcs/wing-leveler-ap-on-off </trigger>   <!-- anti-windup -->
  </pid>
</channel>""")
    story.append(p(
        "Виведення коефіцієнтів підсилення як властивостей "
        "(<font face='Courier'>ap/roll-pid-kp</font>, &hellip;) дозволяє "
        "налаштовувати їх наживо зі сценарію чи консолі без перезбирання. "
        "Типові режими утримання: просторове положення, висота, вертикальна "
        "швидкість, курс і повітряна швидкість (часто замикається на газ)."))

    heading("Налаштування контурів", 1, story)
    for b in [
        "Замикайте спочатку внутрішні контури (кутова швидкість/просторове "
        "положення), потім зовнішні (висота, курс) — внутрішній контур є "
        "об’єктом, який бачить зовнішній контур.",
        "Починайте лише з P, додайте D, щоб задемпфувати перерегулювання, "
        "додайте рівно стільки I, скільки треба, щоб усунути сталу похибку; "
        "використовуйте <font face='Courier'>&lt;trigger&gt;</font>, щоб "
        "зупинити насичення інтегратора при насиченні.",
        "Плануйте коефіцієнти підсилення за швидкісним напором "
        "(<font face='Courier'>scheduled_gain</font> на "
        "<font face='Courier'>aero/qbar-psf</font> чи повітряній швидкості), "
        "щоб контур поводився коректно в усьому діапазоні.",
    ]:
        story.append(bullet(b))

    heading("Наведення та навігація", 1, story)
    story.append(p(
        "Компоненти <font face='Courier'>waypoint_heading</font> та "
        "<font face='Courier'>waypoint_distance</font> обчислюють "
        "ортодромічний пеленг і відстань до цільових широти/довготи; подайте "
        "пеленг в утримання курсу — і ви маєте базовий LNAV. Компонент "
        "<font face='Courier'>angle</font> повертає найменший заданий кут "
        "(зручно для похибки курсу через перехід &plusmn;180&deg;). Для повних "
        "місій керуйте заданими значеннями зі сценарію (див. розділ про "
        "сценарії)."))


# ----------------------------------------------------------------------------
def add_fdm_sensors_systems(story):
    story.append(PageBreak())
    heading("Датчики, системи та моделювання відмов", 0, story)
    story.append(p(
        "Робота високої достовірності — апаратура в контурі (hardware-in-the-"
        "loop), розробка оцінювача стану й автопілота, аналіз відмов — потребує "
        "більшого, ніж ідеальні стани. JSBSim моделює недосконалі датчики, "
        "довільні підсистеми та відмови, що вводяться, — усе це через "
        "фреймворк компонентів FCS і дерево властивостей."))

    heading("Недосконалі датчики", 1, story)
    story.append(p(
        "Компонент <font face='Courier'>&lt;sensor&gt;</font> "
        "(<font face='Courier'>FGSensor.h:56-127</font>) погіршує чистий сигнал "
        "так само, як це робить реальна апаратура:"))
    for b in [
        "<b><font face='Courier'>&lt;lag&gt;</font></b> — стала часу першого "
        "порядку (смуга пропускання датчика).",
        "<b><font face='Courier'>&lt;noise&gt;</font></b> — PERCENT або "
        "ABSOLUTE, з розподілом UNIFORM чи GAUSSIAN.",
        "<b><font face='Courier'>&lt;quantization&gt;</font></b> — біти на "
        "діапазоні min/max (роздільність АЦП).",
        "<b><font face='Courier'>&lt;drift_rate&gt;</font></b>, "
        "<b><font face='Courier'>&lt;bias&gt;</font></b>, "
        "<b><font face='Courier'>&lt;gain&gt;</font></b> — повільний дрейф, "
        "зміщення та похибки масштабу.",
        "<b><font face='Courier'>&lt;delay&gt;</font></b> — транспортна "
        "затримка в часі чи кадрах.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Спеціалізовані датчики будуються на цьому: "
        "<font face='Courier'>&lt;accelerometer&gt;</font> та "
        "<font face='Courier'>&lt;gyro&gt;</font> беруть "
        "<font face='Courier'>&lt;location&gt;</font>/"
        "<font face='Courier'>&lt;orientation&gt;</font> та "
        "<font face='Courier'>&lt;axis&gt;</font> і повідомляють виміряну "
        "питому силу / кутову швидкість у тій точці (тож акселерометр на носі "
        "відчуває кутове прискорення тангажа), а "
        "<font face='Courier'>&lt;magnetometer&gt;</font> зчитує поле. Подавання "
        "саме цих сигналів — а не істинних станів — у ваші закони керування і є "
        "різницею між демонстрацією та стендом для розробки."))

    heading("Довільні підсистеми", 1, story)
    story.append(p(
        "Секція <font face='Courier'>&lt;system&gt;</font> — це вільний набір "
        "каналів FCS, який можна використати для моделювання будь-чого: "
        "електричних шин, гідравлічного тиску, логіки керування паливом, "
        "виявлення пожежі/перегріву, систем балансування чи логіки "
        "озброєння/вантажу. Оскільки кожен компонент читає й записує "
        "властивості, дерево властивостей є системною шиною — "
        "<font face='Courier'>switch</font> може вмикати насос за властивістю "
        "напруги, <font face='Courier'>lag_filter</font> може моделювати "
        "наростання тиску, а <font face='Courier'>fcs_function</font> може "
        "обчислити будь-яке алгебраїчне співвідношення. JSBSim постачає придатні "
        "для повторного використання системи (напр. "
        "<font face='Courier'>systems/catapult.xml</font>), які можна "
        "підключити."))

    heading("Зовнішні реакції та плавучість", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;external_reactions&gt;</font> додають "
        "іменовані сили/моменти в системах BODY, LOCAL чи WIND, величина яких "
        "керується властивістю чи <font face='Courier'>&lt;function&gt;</font> "
        "— катапульти, гальмівні гаки, буксирні троси, скидання кінцевих баків, "
        "лебідковий старт. Катапульта — це лише "
        "<font face='Courier'>switch</font>, який записує "
        "<font face='Courier'>external_reactions/catapult/magnitude</font>, "
        "коли вона зведена. <font face='Courier'>&lt;buoyant_forces&gt;</font> з "
        "<font face='Courier'>&lt;gas_cell&gt;</font> (HYDROGEN/HELIUM/AIR) та "
        "балонетами моделюють аеростати й дирижаблі "
        "(<font face='Courier'>FGBuoyantForces</font>, "
        "<font face='Courier'>FGGasCell</font>)."))

    heading("Введення відмов", 1, story)
    story.append(p(
        "Достовірність включає й те, що йде не так. Приводи надають "
        "<font face='Courier'>fail_zero</font>/"
        "<font face='Courier'>fail_hardover</font>/"
        "<font face='Courier'>fail_stuck</font>; датчики можна зміщувати, "
        "заморожувати чи зашумлювати через їхні властивості; двигуни можна "
        "позбавити палива, спорожнивши бак, чи зупинити через "
        "<font face='Courier'>propulsion/engine[i]/set-running</font>; керівні "
        "поверхні можна заклинити за допомогою "
        "<font face='Courier'>switch</font>. Керуйте всім цим зі сценарію, щоб "
        "побудувати відтворюваний набір тестів сценаріїв відмов."))


# ----------------------------------------------------------------------------
def add_fdm_high_alpha(story):
    story.append(PageBreak())
    heading("Моделювання великих кутів атаки, звалювання та штопора", 0, story)
    story.append(p(
        "Лінійні коефіцієнти описують крейсерський діапазон; достовірність на "
        "межах — звалювання, зрив у некерований режим, штопор — потребує "
        "нелінійної, асиметричної, залежної від передісторії аеродинаміки. Це "
        "найважча частина FDM для правильної реалізації й та частина, яка "
        "найбільше вирізняє серйозну модель."))

    heading("Моделювання звалювання", 1, story)
    story.append(p(
        "Звалювання — це відривання течії: піднімальна сила переламується й "
        "падає, тоді як опір круто зростає. Відтворіть його, табулюючи "
        "C<sub>L</sub> та C<sub>D</sub> в усьому діапазоні " + _g("α") + " — "
        "далеко за C<sub>Lmax</sub>, крізь зазвалювальний спад, в ідеалі до "
        "&plusmn;90&deg; для роботи зі штопором та виведенням зі складних "
        "положень. Найбільша аеродинамічна ознака звалювання — це зростання "
        "опору, тож не нехтуйте кінцем таблиці опору на великих " + _g("α") +
        "."))

    heading("Гістерезис звалювання", 1, story)
    story.append(p(
        "Відривання та повторне приєднання течії відбуваються за різних кутів, "
        "тож звалювання має пам’ять. JSBSim моделює це за допомогою "
        "<font face='Courier'>&lt;alphalimits&gt;</font> та смуги "
        "<font face='Courier'>&lt;hysteresis_limits&gt;</font>, надаючи "
        "<font face='Courier'>aero/stall-hyst-norm</font> (0&rarr;1 уздовж "
        "смуги, <font face='Courier'>FGAerodynamics.cpp</font>). Використовуйте "
        "це як другий вимір таблиці, щоб крива піднімальної сили йшла різним "
        "шляхом при звалюванні та при виведенні — модель c172 робить саме це "
        "(<font face='Courier'>aircraft/c172x/c172x.xml</font>)."))
    code("""\
<alphalimits unit="DEG"> <min>-12</min> <max>22</max> </alphalimits>
<hysteresis_limits unit="DEG"> <min>12</min> <max>18</max> </hysteresis_limits>
...
<table>
  <independentVar lookup="row">aero/alpha-rad</independentVar>
  <independentVar lookup="column">aero/stall-hyst-norm</independentVar>
  <tableData>
            0.0    1.0          <!-- attached   stalled -->
    0.21    1.25   0.86
    0.28    1.47   0.92
    0.35    1.20   1.05         <!-- post-stall, different recovery path -->
  </tableData>
</table>""")

    heading("Штопор та зрив у некерований режим", 1, story)
    story.append(p(
        "Штопор — це нестійкість по осі рискання у поєднанні зі звалюванням. "
        "Вирішальний момент моделювання — і задокументоване обмеження "
        "стандартного виводу Aeromatic — полягає в тому, що момент рискання має "
        "залежати від кута атаки: плаский C<sub>n</sub>(" + _g("β") + ") ніколи "
        "не дасть авторотації. Для правдоподібних штопорів вам потрібні:"))
    for b in [
        "C<sub>n</sub> та C<sub>l</sub> як функції <i>і</i> " + _g("α") + ", "
        "<i>і</i> " + _g("β") + " (2-D таблиці), щоб зазвалювальна асиметрія "
        "рискання/крену могла спричиняти авторотацію.",
        "Демпфування крену й рискання (C<sub>lp</sub>, C<sub>nr</sub>), яке "
        "змінює знак чи величину за звалюванням — саме втрата демпфування крену "
        "дозволяє штопору розвинутися.",
        "Асиметричне звалювання крила та здорове зростання опору на великих " +
        _g("α") + ", щоб задати швидкість обертання штопора й зниження.",
        "Погіршену ефективність керування на великих " + _g("α") + " "
        "(затінені руль висоти/руль напряму), щоб виведення вимагало "
        "правильної техніки.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Високодостовірні моделі зазвалювального режиму/штопора будуються з "
        "даних аеродинамічної труби, отриманих на ротаційному балансі та у "
        "вимушених коливаннях (NASA має обширні набори) або, дедалі частіше, з "
        "DES/гібридного CFD; дослідники використовують біфуркаційний аналіз для "
        "характеризації відповідних режимів зриву, зазвалювальної гірації та "
        "штопора."))

    heading("Інші крайові ефекти", 1, story)
    story.append(p(
        "Вплив екрана землі (таблиця множників піднімальної сили й опору від "
        "висоти/розмаху, <font face='Courier'>aero/h_b-mac-ft</font>), "
        "стисливість (вимір таблиці за числом Маха), ефекти числа Рейнольдса "
        "(запускайте CFD за льотного Re) та бафтинг (збурення, подібне до "
        "турбулентності, за звалюванням) — усе це додає достовірності на "
        "межах. Пам’ятайте, що JSBSim тримає кінці таблиць плаcкими — ваші "
        "таблиці за " + _g("α") + ", " + _g("β") + " та числом Маха мають "
        "насправді охоплювати той діапазон, у якому ви маєте намір літати."))


# ----------------------------------------------------------------------------
def add_fdm_scripting(story):
    story.append(PageBreak())
    heading("Сценарії для автоматизованих випробувань, налаштування та system ID", 0, story)
    story.append(p(
        "Налаштування ручним пілотуванням повільне й невідтворюване. Мова "
        "сценаріїв JSBSim прокручує модель без візуалізації за прописаною "
        "часовою лінією, вводячи вхідні дані й записуючи виходи — це основа "
        "регресійних випробувань, ідентифікації параметрів та досліджень "
        "збурень (<font face='Courier'>FGScript.cpp</font>)."))

    heading("Анатомія сценарію запуску", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;runscript&gt;</font> називає літак і файл "
        "ініціалізації (скидання), задає часове вікно та крок і містить "
        "<font face='Courier'>&lt;event&gt;</font> та директиви "
        "<font face='Courier'>&lt;output&gt;</font>:"))
    code("""\
<?xml version="1.0"?>
<runscript name="elevator doublet">
  <use aircraft="c172x" initialize="reset01"/>
  <run start="0.0" end="60.0" dt="0.0083333">
    <event name="Trim">
      <condition> simulation/sim-time-sec ge 0.0 </condition>
      <set name="simulation/do_simple_trim" value="1"/>
    </event>
    <event name="Doublet up">
      <condition> simulation/sim-time-sec ge 5.0 </condition>
      <set name="fcs/elevator-cmd-norm" value="0.3"
           action="FG_STEP"/>
    </event>
    <event name="Doublet down">
      <condition> simulation/sim-time-sec ge 6.0 </condition>
      <set name="fcs/elevator-cmd-norm" value="-0.3" action="FG_STEP"/>
    </event>
    <event name="Center">
      <condition> simulation/sim-time-sec ge 7.0 </condition>
      <set name="fcs/elevator-cmd-norm" value="0.0" action="FG_RAMP" tc="0.2"/>
    </event>
    <output name="doublet.csv" type="CSV" rate="50">
      <rates> ON </rates> <velocities> ON </velocities>
      <position> ON </position> <fcs> ON </fcs>
    </output>
  </run>
</runscript>""")
    story.append(p(
        "Запустіть без візуалізації: <font face='Courier'>JSBSim "
        "--script=scripts/doublet.xml</font>. Умови використовують трійки "
        "властивість-оператор-значення (<font face='Courier'>ge le eq ne</font> "
        "чи символьні форми) й вкладаються через "
        "<font face='Courier'>logic=\"AND|OR\"</font> "
        "(<font face='Courier'>FGCondition.cpp:109-128</font>)."))

    heading("Дії set: крок, лінійна зміна, експонента", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;set&gt;</font> змінює властивість як "
        "<font face='Courier'>FG_STEP</font>, лінійну "
        "<font face='Courier'>FG_RAMP</font> за сталу часу "
        "<font face='Courier'>tc</font> або як експоненційне наближення "
        "першого порядку <font face='Courier'>FG_EXP</font>; "
        "<font face='Courier'>type=\"FG_DELTA\"</font> робить значення "
        "приростом (<font face='Courier'>FGScript.cpp:472-495</font>). Це все, "
        "що потрібно для синтезу класичних вхідних впливів system ID:"))
    for b in [
        "<b>Здвоєний імпульс (doublet)</b> (показаний вище) — збуджує "
        "короткоперіодичний рух / голландський крок для ідентифікації "
        "демпфування та частоти.",
        "<b>3-2-1-1</b> — багатокроковий вхідний вплив, багатий у смузі "
        "частот, стандарт для ідентифікації параметрів.",
        "<b>Розгортка за частотою</b> — змінюйте частоту синусоїди через "
        "<font face='Courier'>fcs_function</font>, щоб відобразити частотну "
        "характеристику.",
        "<b>Кроки газу/керування</b> — для точок характеристик (набір висоти, "
        "розгін) та перевірки балансування.",
    ]:
        story.append(bullet(b))

    heading("Вивід, notify та пакетні робочі процеси", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;output type=\"CSV\"&gt;</font> обирає цілі "
        "підсистеми (<font face='Courier'>rates</font>, "
        "<font face='Courier'>velocities</font>, "
        "<font face='Courier'>forces</font>, "
        "<font face='Courier'>moments</font>, "
        "<font face='Courier'>aerosurfaces</font>, "
        "<font face='Courier'>propulsion</font>, &hellip;) та/або окремі "
        "<font face='Courier'>&lt;property&gt;</font>, опціонально "
        "перетворюючи одиниці функцією <font face='Courier'>apply</font> "
        "(<font face='Courier'>FGOutputType.cpp:100-128</font>). "
        "<font face='Courier'>&lt;notify&gt;</font> друкує обрані властивості, "
        "коли спрацьовує подія. Обгорніть запуски сценаріїв у модулі Python "
        "(<font face='Courier'>import jsbsim</font>), щоб розгортати параметри, "
        "автоматично балансувати в усьому діапазоні й перевіряти результати "
        "твердженнями — перетворюючи ваше налаштування на автоматизований "
        "набір регресійних тестів."))

    heading("Випробування збуреннями та турбулентністю", 1, story)
    story.append(p(
        "Робастність виникає з польоту моделі в погоді. Атмосфера JSBSim "
        "забезпечує сталі шари вітру, дискретні пориви та неперервну "
        "турбулентність (спектри типу Dryden із обиральною інтенсивністю); "
        "задайте їх із файлу IC чи сценарію й переконайтеся, що літак із "
        "покращенням стійкості все ще утримує свої власні рухи. Поєднайте це з "
        "розгортками похідних за методом Монте-Карло з розділу про дані, щоб "
        "обмежити пілотажні характеристики з урахуванням як атмосферної, так і "
        "модельної невизначеності."))


# ----------------------------------------------------------------------------
def add_fdm_performance_hq(story):
    story.append(PageBreak())
    heading("Узгодження льотних і пілотажних характеристик", 0, story)
    story.append(p(
        "Остаточна перевірка достовірності кількісна: чи відтворює модель "
        "опубліковані льотні характеристики літака й чи виявляє правильні "
        "пілотажні характеристики? Це фаза приймання — цикл, у якому ви "
        "порівнюєте з даними й коригуєте відповідальні числа."))

    heading("Балансування та точки характеристик", 1, story)
    story.append(p(
        "Починайте з балансування (розділ про алгоритм балансування): "
        "переконайтеся, що літак балансується за розумних просторових положень "
        "і положень органів керування для різних мас і висот. Потім "
        "пропишіть у сценарії опорні точки характеристик і порівняйте з POH:"))
    data = [
        ["Цільова характеристика", "Як виміряти в JSBSim"],
        ["Швидкість звалювання (чиста / з закрилками)",
         "балансувати за зростання " + _g("α") + " до C<sub>Lmax</sub>; зчитати V"],
        ["Найкраща швидкопідйомність / V<sub>y</sub>",
         "збалансована розгортка набору висоти на повному газі за швидкістю"],
        ["Крейсерська TAS &amp; витрата палива",
         "балансувати на крейсерських потужності/висоті; зчитати velocities/propulsion"],
        ["Практична стеля",
         "набирати висоту, доки швидкопідйомність не впаде до 100 ft/min"],
        ["Дистанція зльоту / посадки",
         "прописаний у сценарії пробіг із шасі + гальмами"],
        ["Дальність / тривалість польоту",
         "інтегрувати вигоряння палива на крейсерському режимі до порожнього"],
    ]
    story.append(_oftab(data, [6.0 * cm, 9.8 * cm]))

    heading("Цільові пілотажні характеристики", 1, story)
    story.append(p(
        "Лінеаризуйте відносно балансування (або підженіть відгуки на здвоєний "
        "імпульс) і звірте характеристики власних рухів із критеріями "
        "MIL-STD-1797 / старішого MIL-F-8785C та оцінюваної пілотами шкали "
        "Cooper-Harper:"))
    for b in [
        "<b>Короткоперіодичний рух</b> — частота й демпфування у зоні Level-1 "
        "на діаграмі CAP (Control Anticipation Parameter); це рух, який "
        "пілоти відчувають найдужче.",
        "<b>Фугоїд</b> — довгоперіодичний, слабко задемпфований, але не "
        "розбіжний (демпфування &gt; 0).",
        "<b>Голландський крок</b> — достатні частота й демпфування; демпфер "
        "рискання існує саме для того, щоб цього досягти.",
        "<b>Крен-мода</b> — стала часу достатньо мала для чіткого відгуку по "
        "крену; <b>спіральний рух</b> — у найгіршому разі повільно розбіжний.",
    ]:
        story.append(bullet(b))

    heading("Енергетичні методи та цикл ітерацій", 1, story)
    story.append(p(
        "Питома надлишкова потужність P<sub>s</sub> = V(T&minus;D)/W пов’язує "
        "тягу, опір і вагу з набором висоти та розгоном; узгодження "
        "P<sub>s</sub> в усьому діапазоні одночасно перевіряє поляру опору та "
        "модель тяги. Коли щось не так, розбіжність указує на винуватця: "
        "неправильна крейсерська швидкість &rarr; поляра опору чи тяга; "
        "неправильний набір висоти &rarr; надлишкова потужність; неправильна "
        "швидкість звалювання &rarr; C<sub>Lmax</sub>; неправильний "
        "короткоперіодичний рух &rarr; C<sub>m" + _g("α") + "</sub>/C<sub>mq"
        "</sub> або інерція/CG. Виправте це число, перезапустіть сценарій, "
        "повторіть. Обмежте залишкову невизначеність розгортками похідних за "
        "методом Монте-Карло, щоб знати, що модель робастна, а не лише "
        "налаштована під одну точку."))
    story.append(quote(
        "Спершу перевіряйте розімкнений контур: із зафіксованими органами "
        "керування вільний відгук хорошої моделі (власні рухи, відхід "
        "балансування, планування) має вже відповідати льотним даним ще до "
        "ввімкнення будь-якого автопілота."))


# ----------------------------------------------------------------------------
def add_fdm_integration(story):
    story.append(PageBreak())
    heading("Інтеграція з FlightGear та зовнішніми симуляторами", 0, story)
    story.append(p(
        "JSBSim — це бібліотека; достовірність, яку сприймає користувач, також "
        "залежить від того, як її під’єднано до візуального симулятора чи "
        "стека керування. Контрактом завжди є дерево властивостей: хост "
        "записує команди й середовище, JSBSim інтегрує фізику, а хост зчитує "
        "стани назад для візуалізації та приладів."))

    heading("FlightGear", 1, story)
    story.append(p(
        "FlightGear вбудовує JSBSim як рідну FDM. Точки інтеграції:"))
    for b in [
        "<b>Входи</b>: хост записує <font face='Courier'>fcs/aileron-cmd-norm"
        "</font>, <font face='Courier'>elevator-cmd-norm</font>, "
        "<font face='Courier'>rudder-cmd-norm</font>, "
        "<font face='Courier'>throttle-cmd-norm</font>, команди "
        "шасі/закрилків/гальм тощо.",
        "<b>Виходи</b>: він зчитує положення для анімацій 3-D моделі — "
        "<font face='Courier'>fcs/&hellip;-pos-norm</font> для поверхонь і "
        "шасі, оберти двигуна / N1 та стан тіла для виду.",
        "<b>Середовище</b>: FlightGear надає вітри, температуру та висоту "
        "землі/рельєфу, з якими контактує шасі.",
        "<b>Зв’язний шар</b>: тримайте імена властивостей на стандартних "
        "шляхах, щоб штатні прив’язки FlightGear і код приладів їх знаходили; "
        "документуйте будь-які власні властивості "
        "<font face='Courier'>ap/</font> чи "
        "<font face='Courier'>systems/</font>, які ви додаєте.",
    ]:
        story.append(bullet(b))

    heading("Сокети, рідні протоколи та інші рушії", 1, story)
    story.append(p(
        "Для зовнішніх стеків <font face='Courier'>&lt;output type=\"SOCKET\""
        "&gt;</font> та <font face='Courier'>type=\"FLIGHTGEAR\"</font> "
        "транслюють стан через TCP/UDP, а API Python/C++ вбудовують рушій "
        "безпосередньо. JSBSim — це фізичне ядро за FlightGear, проєктом "
        "Antoinette на Unreal Engine, ArduPilot і PX4 software-in-the-loop та "
        "середовищами навчання з підкріпленням на кшталт gym-jsbsim; у кожному "
        "випадку хост крокує модель і обмінюється тим самим набором "
        "властивостей. Узгодьте частоту кадрів хоста з розумним "
        "<font face='Courier'>dt</font> JSBSim (часто 120 Hz) та "
        "інтерполюйте візуалізацію, а не сповільнюйте фізику."))

    heading("Поширені пастки інтеграції", 1, story)
    for b in [
        "Подвійні шляхи керування — і хост, і внутрішній автопілот керують тією "
        "самою поверхнею; вирішіть, кому належить кожна команда.",
        "Неузгодженість частоти кадрів / <font face='Courier'>dt</font>, що "
        "спричиняє тремтіння чи нестійкість, особливо з жорстким шасі.",
        "Розбіжності опорних значень рельєфу/висоти (AGL чи MSL, геоїд чи "
        "еліпсоїд), через які шасі ширяє чи провалюється.",
        "Неузгодженість одиниць на межі — команди JSBSim нормовані, але виходи "
        "стану — у футах, fps, радіанах, якщо не перетворено.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_fdm_checklist(story):
    story.append(PageBreak())
    heading("Зведений контрольний список достовірності та поширені пастки", 0, story)
    story.append(p(
        "Цей розділ зводить Частину IV у контрольний список, який ви можете "
        "прогнати по будь-якій моделі. Жоден із цих пунктів не екзотичний; "
        "кожен — це реальний збій, помічений на форумах і в списку розробників, "
        "і більшості тривіально уникнути, щойно ви знаєте, де шукати."))

    heading("Геометрія, маса та центрування", 1, story)
    for b in [
        "Ліва/права симетрія кожного розташування (шасі, баки, точкові маси, "
        "рушії), якщо асиметрія не передбачена навмисно.",
        "CG тримається біля AERORP та всередині діапазону POH за всіх "
        "завантажень і станів палива; перевірте хід CG від вигоряння палива.",
        "Тензор інерції фізичний: I<sub>zz</sub> &gt; I<sub>yy</sub> &gt; "
        "I<sub>xx</sub>, I<sub>zz</sub> &asymp; I<sub>xx</sub>+I<sub>yy</sub>, "
        "розумний знак <font face='Courier'>ixz</font>.",
        "Опорні S, b, c&#x0304; у <font face='Courier'>&lt;metrics&gt;</font> "
        "відповідають значенням, використаним для знерозмірнення аеродинамічних "
        "даних.",
    ]:
        story.append(bullet(b))

    heading("Аеродинаміка", 1, story)
    for b in [
        "Таблиці охоплюють увесь передбачений діапазон за " + _g("α") + ", " +
        _g("β") + " та числом Маха (кінці тримаються плаcкими, не "
        "екстраполюються).",
        "C<sub>m" + _g("α") + "</sub> &lt; 0 (статично стійкий) з розумним "
        "запасом поздовжньої стійкості; C<sub>n" + _g("β") + "</sub> &gt; 0, "
        "C<sub>l" + _g("β") + "</sub> &lt; 0.",
        "Похідні демпфування присутні й мають правильний знак (C<sub>mq</sub>, "
        "C<sub>lp</sub>, C<sub>nr</sub> &lt; 0); одиниці відповідають угоді "
        "<font face='Courier'>bi2vel</font>/<font face='Courier'>ci2vel"
        "</font>.",
        "Рискання/крен залежать від " + _g("α") + ", якщо ви хочете "
        "звалювання/штопор; присутнє зростання опору на великих " + _g("α") +
        ".",
        "Знаки керування перевірені: додатний elevator-cmd робить із тангажем "
        "те, що ви очікуєте.",
    ]:
        story.append(bullet(b))

    heading("Силова установка, шасі та керування", 1, story)
    for b in [
        "Силова установка узгоджена зі статичною тягою/потужністю, "
        "крейсерською витратою палива та набором висоти; напрям/крутний момент "
        "гвинта збалансовано.",
        "Жорсткість пружини шасі &asymp; навантаження/стиснення, достатньо "
        "м’яка, щоб уникнути приросту енергії; демпфування віддачі &ge; "
        "стиснення; приземлення записане й стабільне.",
        "Групи гальм і керування поворотом під’єднані; літаки з хвостовим "
        "колесом керуються поворотом і не входять у некерований розворот.",
        "Обмеження швидкості приводів реалістичні (немає розкачки, викликаної "
        "пілотом); передаточне відношення/змішування керування правильні.",
    ]:
        story.append(bullet(b))

    heading("Перевірка та інтеграція", 1, story)
    for b in [
        "Балансується в усьому діапазоні без розбіжності; вільний відгук у "
        "розімкненому контурі відповідає очікуванням ще до автопілота.",
        "Цільові льотні характеристики й характеристики власних рухів досягнуто "
        "відносно POH та MIL-STD-1797 / Cooper-Harper.",
        "Поводиться коректно в турбулентності та в розкиді похідних за методом "
        "Монте-Карло.",
        "Імена властивостей на стандартних шляхах; єдиний власник на кожну "
        "команду керування; узгоджений <font face='Courier'>dt</font> з хостом.",
        "Походження кожного коефіцієнта зафіксоване, тож майбутню розбіжність "
        "можна простежити до її джерела.",
    ]:
        story.append(bullet(b))
    story.append(quote(
        "Достовірність — це не один великий секрет; це сотня маленьких "
        "правильностей. Дерево властивостей робить кожну з них спостережною — "
        "інструментуйте, порівнюйте, коригуйте, повторюйте."))


# ============================================================================
# Main
# ============================================================================


def main():
    print("[1/3] Building story...")
    story = build_story()
    print(f"[2/3] Story has {len(story)} flowables. Rendering PDF...")
    doc = TOCDocTemplate(
        OUT_PATH,
        pagesize=A4,
        title="Вичерпний довідник JSBSim (українське видання)",
        author="Проєкт JSBSim — конспект створено Claude",
        subject="Внутрішня будова FDM JSBSim, схема XML, аеродинаміка та робочий процес CFD",
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
    )
    doc.multiBuild(story, canvasmaker=HeaderFooterCanvas)
    size = os.path.getsize(OUT_PATH)
    print(f"[3/3] Wrote {OUT_PATH} ({size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
