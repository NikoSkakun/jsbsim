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


OUT_PATH = "/home/user/jsbsim/docs_output/JSBSim_Ultimate_Reference.pdf"


# Register DejaVu fonts so we can render unicode glyphs (macrons, dots, etc.)
DEJAVU_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DejaVu",        f"{DEJAVU_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold",   f"{DEJAVU_DIR}/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Oblique",
                               f"{DEJAVU_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Mono",
                               f"{DEJAVU_DIR}/DejaVuSansMono.ttf"))


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
        self.setFont("Helvetica-Bold", 9)
        self.drawString(15 * mm, PAGE_H - 8 * mm,
                        "The Ultimate JSBSim Reference")
        self.drawRightString(PAGE_W - 15 * mm, PAGE_H - 8 * mm,
                             "Flight Dynamics Model")
        # Footer
        self.setFillColor(colors.HexColor("#0d3b66"))
        self.rect(0, 8 * mm, PAGE_W, 0.4 * mm, fill=1, stroke=0)
        self.setFillColor(colors.HexColor("#333333"))
        self.setFont("Helvetica", 8)
        self.drawString(15 * mm, 5 * mm,
                        "JSBSim - Open-source 6-DoF flight dynamics engine")
        self.drawRightString(PAGE_W - 15 * mm, 5 * mm,
                             f"Page {page_num} of {page_count}")
        self.restoreState()


# -----------------------------------------------------------------------------
# Styles
# -----------------------------------------------------------------------------

styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "BigTitle", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=30, leading=36,
    textColor=colors.HexColor("#0d3b66"), spaceAfter=10, alignment=TA_CENTER,
)
SUBTITLE_STYLE = ParagraphStyle(
    "Subtitle", parent=styles["Title"],
    fontName="Helvetica", fontSize=16, leading=20,
    textColor=colors.HexColor("#333333"), spaceAfter=24, alignment=TA_CENTER,
)
COVER_DESCR_STYLE = ParagraphStyle(
    "CoverDescr", parent=styles["Normal"],
    fontName="Helvetica-Oblique", fontSize=11, leading=15,
    textColor=colors.HexColor("#444444"), alignment=TA_CENTER,
)

CHAPTER_STYLE = ParagraphStyle(
    "Chapter", parent=styles["Heading1"],
    fontName="Helvetica-Bold", fontSize=22, leading=26,
    textColor=colors.HexColor("#0d3b66"),
    spaceBefore=12, spaceAfter=14, keepWithNext=True,
)
SECTION_STYLE = ParagraphStyle(
    "Section", parent=styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=15, leading=19,
    textColor=colors.HexColor("#1d5d9b"),
    spaceBefore=14, spaceAfter=8, keepWithNext=True,
)
SUBSECTION_STYLE = ParagraphStyle(
    "SubSection", parent=styles["Heading3"],
    fontName="Helvetica-Bold", fontSize=12, leading=16,
    textColor=colors.HexColor("#222222"),
    spaceBefore=10, spaceAfter=5, keepWithNext=True,
)
SUBSUB_STYLE = ParagraphStyle(
    "SubSub", parent=styles["Heading4"],
    fontName="Helvetica-BoldOblique", fontSize=10.5, leading=14,
    textColor=colors.HexColor("#444444"),
    spaceBefore=8, spaceAfter=3, keepWithNext=True,
)
BODY_STYLE = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontName="Helvetica", fontSize=10, leading=14,
    spaceAfter=6, alignment=TA_JUSTIFY,
)
BULLET_STYLE = ParagraphStyle(
    "Bullet", parent=BODY_STYLE,
    leftIndent=14, bulletIndent=2, spaceAfter=3, alignment=TA_LEFT,
)
QUOTE_STYLE = ParagraphStyle(
    "Quote", parent=BODY_STYLE,
    leftIndent=14, rightIndent=14, textColor=colors.HexColor("#555555"),
    fontName="Helvetica-Oblique",
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
    "CellHeader", fontName="Helvetica-Bold", fontSize=8.5, leading=11,
    textColor=colors.white, alignment=TA_LEFT,
)
CELL_STYLE_BODY = ParagraphStyle(
    "CellBody", fontName="Helvetica", fontSize=8.5, leading=11,
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
        numbered = f"Chapter {_HEADING_COUNTER['chapter']}: {text}"
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
    story.append(Paragraph("The Ultimate", TITLE_STYLE))
    story.append(Paragraph("JSBSim Reference", TITLE_STYLE))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Architecture, Aerodynamics, and Aircraft Modelling — Under the Hood",
        SUBTITLE_STYLE))
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph(
        "A practical engineering manual covering JSBSim's XML configuration "
        "language, equations of motion, integration methods, aerodynamic "
        "function/table framework, propulsion subsystem, flight control "
        "components, and the workflow for generating CFD-derived aerodynamic "
        "data tables for a custom aircraft model.",
        COVER_DESCR_STYLE))
    story.append(Spacer(1, 50 * mm))
    today = datetime.date.today().isoformat()
    story.append(Paragraph(
        f"Generated {today} &nbsp;·&nbsp; "
        "Reverse-engineered from JSBSim v2.0 source",
        ParagraphStyle("CoverFooter", parent=COVER_DESCR_STYLE,
                       fontSize=9, textColor=colors.HexColor("#666666"))))
    story.append(NextPageTemplate("Body"))
    story.append(PageBreak())

    # ------------------------------------------------------------------ TOC
    story.append(Paragraph("Table of Contents", TOC_HEADING_STYLE))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("TOC0", fontName="Helvetica-Bold", fontSize=11,
                       textColor=colors.HexColor("#0d3b66"),
                       leftIndent=0, leading=16, spaceAfter=3),
        ParagraphStyle("TOC1", fontName="Helvetica", fontSize=10,
                       leftIndent=14, leading=13, spaceAfter=1),
        ParagraphStyle("TOC2", fontName="Helvetica", fontSize=9,
                       leftIndent=28, leading=12, spaceAfter=0,
                       textColor=colors.HexColor("#555555")),
    ]
    story.append(toc)
    story.append(PageBreak())

    # ================================================================
    # CHAPTER 1 - Introduction
    # ================================================================
    heading("Introduction to JSBSim", 0, story)
    story.append(p(
        "JSBSim is an open-source, multi-platform, object-oriented C++ "
        "Flight Dynamics Model (FDM) used as the physics core behind a wide "
        "spectrum of aerospace applications: FlightGear, Unreal Engine's "
        "Antoinette Project, ArduPilot and PX4 Software-in-the-Loop, "
        "reinforcement-learning gyms such as <i>gym-jsbsim</i>, and academic "
        "research running into thousands of citations. It implements a "
        "nonlinear, six-degree-of-freedom rigid-body simulation with an "
        "accurate Earth model (WGS-84 ellipsoid, rotation, Coriolis), the "
        "ISA 1976 standard atmosphere, configurable wind and turbulence, "
        "propulsion (piston, turbine, turboprop, rocket, electric, rotor), "
        "ground reactions and a fully scriptable XML-based flight control "
        "system."))

    heading("What this document covers", 1, story)
    story.append(p(
        "This reference is organised as a top-down dive into JSBSim. We start "
        "with the architecture and execution loop, then walk every section "
        "of the aircraft XML, then go deep on aerodynamics (the math "
        "framework, tables, and conventions), and finish with a practical "
        "CFD-to-JSBSim workflow for building your own aircraft model. Every "
        "claim is rooted in source-code citations of the form "
        "<font face='Courier'>file:line</font>."))

    heading("How JSBSim differs from a typical sim engine", 1, story)
    for b in [
        "<b>XML-only modelling:</b> aircraft are described in declarative "
        "XML — no recompilation is needed to add a new airframe.",
        "<b>Function/table aerodynamics:</b> aerodynamic coefficients are "
        "expressed as <i>functions</i> that compose tables, properties and "
        "arithmetic operators. This makes the model fully data-driven and "
        "easy to populate from CFD or wind-tunnel data.",
        "<b>Property tree:</b> every state variable, control input, FCS "
        "output and aero coefficient is exposed under a hierarchical "
        "string path (<font face='Courier'>aero/qbar-psf</font>, "
        "<font face='Courier'>velocities/p-aero-rad_sec</font>, etc.). "
        "Everything is observable and most things are writable.",
        "<b>Round-Earth physics:</b> equations of motion are integrated in "
        "the ECI frame, including the Coriolis and centrifugal accelerations "
        "from Earth's rotation. Optional gravitational-torque modelling "
        "supports spacecraft.",
        "<b>Trim algorithm:</b> a robust bracketed root-finder trims the "
        "vehicle into steady flight (longitudinal, full, turn, pull-up, "
        "ground, custom).",
    ]:
        story.append(bullet(b))

    heading("Conventions used in this document", 1, story)
    story.append(p(
        "Distances and inertia use US customary units by default (feet, "
        "inches, slug·ft²) — JSBSim's default — but all elements accept an "
        "explicit <font face='Courier'>unit</font> attribute. Math symbols "
        "follow Etkin/Stevens-Lewis convention: <i>α</i> = angle of attack, "
        "<i>β</i> = sideslip, <i>p,q,r</i> = body angular rates, "
        "<i><font name='DejaVu'>q̄</font></i> = ½ρV² = dynamic pressure, <i>S, b, <font name='DejaVu'>c̄</font></i> = wing area, "
        "span, mean aerodynamic chord."))

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 2 - Architecture & Execution Flow
    # ================================================================
    heading("Architecture and Execution Flow", 0, story)
    story.append(p(
        "JSBSim is structured around a central executive class "
        "(<font face='Courier'>FGFDMExec</font>) that owns a fixed-order "
        "list of <i>models</i> and drives them through a discrete-time loop. "
        "Each model reads its inputs from the property tree (filled by "
        "upstream models in the same tick) and writes its outputs back. "
        "Integrating the equations of motion is itself one of those models."))

    heading("The model execution order", 1, story)
    story.append(p(
        "Models are enumerated in <font face='Courier'>FGFDMExec.h:225-241"
        "</font> and executed in this order every tick:"))
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
        "<b>Why this order matters.</b> <i>Propagate</i> runs first because "
        "it advances the state using the accelerations computed at the end "
        "of the <i>previous</i> tick. Then atmosphere and winds give "
        "pressure, density and the airmass-relative velocity that "
        "<i>Auxiliary</i> needs to compute <i>α, β, <font name='DejaVu'>q̄</font>, M</i> — which the "
        "aerodynamics functions consume. Mass balance runs after FCS so a "
        "control law can request a pointmass shift (think: fuel transfer, "
        "stores release). Accelerations runs last; its outputs become the "
        "inputs to Propagate on the next tick."))

    heading("The Run loop in pseudocode", 1, story)
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
        "Default integration step is "
        "<font face='Courier'>1.0 / 120.0</font> s "
        "(see <font face='Courier'>FGFDMExec.cpp:99</font>). At 120 Hz JSBSim "
        "runs faster than real time on a single CPU core even for complex "
        "aircraft. The step is set with "
        "<font face='Courier'>SetDeltaT()</font> or via the simulation script."))

    heading("Modules at a glance", 1, story)
    table_data = [
        ["Module", "Source", "Responsibility"],
        ["FGPropagate", "models/FGPropagate.*",
            "Integrate position, velocity, quaternion"],
        ["FGAccelerations", "models/FGAccelerations.*",
            "Newton-Euler equations; ground friction LCP"],
        ["FGAerodynamics", "models/FGAerodynamics.*",
            "Sum function-driven aero forces/moments"],
        ["FGPropulsion", "models/FGPropulsion.*",
            "Engines (piston/turbine/rocket/electric)"],
        ["FGGroundReactions", "models/FGGroundReactions.*",
            "Tires, struts, brakes, steering"],
        ["FGAtmosphere", "models/FGAtmosphere.*",
            "ISA 1976 (T, p, ρ, a)"],
        ["FGWinds", "models/atmosphere/FGWinds.*",
            "Steady wind, shear, Dryden/Karman turbulence"],
        ["FGInertial", "models/FGInertial.*",
            "Gravity (spherical or WGS-84), planet rotation"],
        ["FGMassBalance", "models/FGMassBalance.*",
            "Mass, CG, inertia tensor, pointmasses"],
        ["FGAuxiliary", "models/FGAuxiliary.*",
            "α, β, <font name='DejaVu'>q̄</font>, Vt, Mach, gamma, load factors"],
        ["FGFCS", "models/FGFCS.*",
            "Flight control system; channel/component graph"],
        ["FGOutput", "models/FGOutput.*",
            "CSV, FlightGear binary, TCP, telnet"],
        ["FGTrim", "initialization/FGTrim.*",
            "Bracketed root-finder for trim"],
        ["FGPropertyManager", "input_output/FGPropertyManager.*",
            "Hierarchical property tree, all I/O via paths"],
    ]
    t = Table(wrap_table(table_data), colWidths=[3.1 * cm, 4.0 * cm, 9.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
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
    heading("Coordinate Frames, Axes, and Units", 0, story)
    story.append(p(
        "Getting the frames right is the single most common source of bugs "
        "when building a new aircraft. JSBSim uses several frames at once "
        "and each section of the XML implicitly chooses one of them."))

    heading("The structural frame (XML geometry)", 1, story)
    story.append(p(
        "All <font face='Courier'>&lt;location&gt;</font> elements — landing "
        "gear, CG, AERORP, pointmasses, engine thruster location — are "
        "expressed in the <i>structural</i> reference frame. This is an "
        "aircraft-fixed frame with the X axis usually pointing aft along the "
        "fuselage, Y to the right, Z up. The origin (0,0,0) is conventionally "
        "near the firewall or the nose datum. Inches are the default unit."))
    story.append(p(
        "Inside the FDM these positions are converted to the body-fixed "
        "frame used by the equations of motion (X forward, Y right, "
        "Z down) — but you do <b>not</b> see that conversion in the XML."))

    heading("The body-fixed (body) frame", 1, story)
    story.append(p(
        "All angular rates, accelerations, body-frame velocities and inertia "
        "components are in the body frame:"))
    for b in [
        "<b>X</b> — forward, out through the nose.",
        "<b>Y</b> — out through the right wing.",
        "<b>Z</b> — downward, completing the right-handed triad.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Body-frame translational velocity is the property triple "
        "<font face='Courier'>velocities/u-fps, v-fps, w-fps</font>. "
        "Angular rates are <font face='Courier'>velocities/p-rad_sec, "
        "q-rad_sec, r-rad_sec</font>. The inertia tensor is given in the "
        "structural frame in the XML but is rotated to the body frame at "
        "load."))

    heading("Wind (aerodynamic) and stability frames", 1, story)
    story.append(p(
        "The <i>wind</i> frame is rotated from the body frame by sideslip "
        "<i>β</i> and angle of attack <i>α</i>: its X axis points along the "
        "relative wind, drag acts in −X, lift acts in −Z (up relative to "
        "airflow). When you write "
        "<font face='Courier'>&lt;axis name=\"LIFT\"&gt;</font> in the "
        "aerodynamics section JSBSim assumes you are in wind axes. The "
        "<i>stability</i> frame is an intermediate frame rotated from body "
        "only by α (no β); some classical stability derivatives are "
        "tabulated in that frame and you can opt into it with "
        "<font face='Courier'>frame=\"STABILITY\"</font>."))
    story.append(p(
        "JSBSim handles the conversion automatically: forces computed in "
        "<i>LIFT/DRAG/SIDE</i> are rotated by <i>T<sub>w2b</sub></i> into "
        "the body frame and moments are added at the AERORP, then "
        "transferred to the CG by <i>r × F</i>."))

    heading("Local NED and ECI frames", 1, story)
    story.append(p(
        "<b>Local NED</b> (North-East-Down) is the local-tangent frame "
        "centered at the aircraft. JSBSim uses it for winds, ground track "
        "(γ, ψ<sub>gt</sub>), and the local Euler angles <i>φ, θ, ψ</i>. "
        "<b>ECI</b> (Earth-Centred Inertial) is the non-rotating frame in "
        "which the equations of motion are actually integrated; "
        "<font face='Courier'>FGPropagate</font> maintains "
        "<i>v<sub>inertial</sub></i> and <i>r<sub>inertial</sub></i> "
        "internally and transforms them to body/local for output."))

    heading("Sign conventions", 1, story)
    for b in [
        "<b>Elevator deflection</b>: positive trailing-edge-down (creates "
        "negative pitching moment), output to "
        "<font face='Courier'>fcs/elevator-pos-rad</font>.",
        "<b>Aileron deflection</b>: differential — the C-172 uses "
        "<font face='Courier'>left-aileron-pos-rad</font> with positive = "
        "down (rolls right).",
        "<b>Rudder deflection</b>: positive trailing-edge-left (yaws nose "
        "left).",
        "<b>Inertia cross products</b>: classical convention is "
        "<i>I<sub>xz</sub></i> as the integral of <i>+xz dm</i>. Some "
        "references use the negated convention; set "
        "<font face='Courier'>negated_crossproduct_inertia=\"true\"</font> "
        "on the <i>&lt;mass_balance&gt;</i> element to switch.",
        "<b>Up vs. down</b>: <i>Z<sub>body</sub></i> is positive down. The "
        "structural Z given in the XML is usually positive up — JSBSim does "
        "the flip internally.",
    ]:
        story.append(bullet(b))

    heading("Units", 1, story)
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
        "<b>Always declare units explicitly</b> on every element that "
        "accepts a <font face='Courier'>unit</font> attribute — silent "
        "default mismatches are responsible for the majority of \"my "
        "aircraft launches itself sideways\" bug reports."))

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 4 - The Aircraft XML
    # ================================================================
    heading("The Aircraft XML, Section by Section", 0, story)
    story.append(p(
        "An aircraft is a single XML file with the root element "
        "<font face='Courier'>&lt;fdm_config&gt;</font>. The order of "
        "sections is enforced by the XSD; the canonical sequence is shown "
        "below. Below the cover material follow ~10 sub-chapters, one per "
        "major section."))

    heading("Root: fdm_config", 1, story)
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
        "<b>Attributes:</b> "
        "<font face='Courier'>name</font> (required) — display name; "
        "<font face='Courier'>version</font> (required, currently 2.0); "
        "<font face='Courier'>release</font> = PRODUCTION | ALPHA | BETA "
        "(ALPHA/BETA print a warning at load time)."))

    heading("fileheader: authorship and provenance", 1, story)
    story.append(p(
        "Pure metadata. JSBSim ignores everything inside but tools that "
        "scan a fleet of models read it. Use it."))
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

    heading("metrics: aircraft geometry", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;metrics&gt;</font> establishes the "
        "non-dimensionalisation: <i>S</i> (wing area), <i>b</i> (wing span), "
        "<i><font name='DejaVu'>c̄</font></i> (mean aerodynamic chord), tail areas/arms, and the three "
        "<i>reference points</i> AERORP, EYEPOINT and VRP."))
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
        "The three reference points have specific meaning:"))
    for b in [
        "<b>AERORP</b> — aerodynamic reference point. All aerodynamic "
        "moments are first summed about this point, then transferred to the "
        "CG by <i>M<sub>cg</sub> = M<sub>arp</sub> + r<sub>arp→cg</sub> × F"
        "</i>. Conventionally placed at the 25% mean aerodynamic chord on "
        "the wing.",
        "<b>EYEPOINT</b> — pilot eye position. Used by FlightGear and "
        "visual systems; affects the load factor at the pilot's head "
        "(<font face='Courier'>accelerations/n-pilot-{x,y,z}-norm</font>).",
        "<b>VRP</b> — visual reference point, origin used by external "
        "viewers.",
    ]:
        story.append(bullet(b))

    heading("mass_balance: weight, CG, inertia", 1, story)
    story.append(p(
        "The empty weight plus a list of <i>pointmasses</i> is what JSBSim "
        "uses to compute total mass, CG location, and the inertia tensor at "
        "the CG. Pointmasses include crew, passengers, cargo, and "
        "user-defined items that may move at runtime (slung loads, "
        "transferable fuel). Tank mass is added automatically by the "
        "propulsion subsystem and consumed during flight."))
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
        "<b>Inertia about the CG</b>: the values you put in "
        "<font face='Courier'>ixx, iyy, izz, ixy, ixz, iyz</font> are the "
        "inertia of the empty-weight structure about the CG, in the "
        "<i>structural</i> frame. JSBSim rotates them to the body frame, "
        "then adds the parallel-axis contributions of each pointmass. The "
        "<font face='Courier'>negated_crossproduct_inertia</font> attribute "
        "exists because half the textbooks use the opposite sign convention "
        "for products of inertia."))

    heading("ground_reactions: gear, skids and contacts", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;contact&gt;</font> elements describe "
        "anything that can touch the ground. There are two types:"))
    for b in [
        "<b>BOGEY</b> — a wheel. Has a strut (spring + damper), tire "
        "friction (static, dynamic, rolling), optional steering, optional "
        "brakes, and optional retraction.",
        "<b>STRUCTURE</b> — a non-rolling contact such as a wing tip, "
        "skid, fuselage or tail bumper. Typically very stiff with low "
        "friction.",
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
        "Friction forces are computed by a projected-Gauss-Seidel iterative "
        "Lagrange-multiplier solver (Catto 2005) inside "
        "<font face='Courier'>FGAccelerations::CalculateFrictionForces()"
        "</font>, so multi-wheel contacts respect the no-interpenetration "
        "and Coulomb-friction constraints simultaneously."))

    heading("external_reactions: bolt-on forces", 1, story)
    story.append(p(
        "Anything that applies a force or moment that is neither aero, nor "
        "propulsion, nor ground contact goes here: parachutes, towlines, "
        "JATO bottles, magnetic launchers."))
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

    heading("propulsion: engines, tanks, thrusters", 1, story)
    story.append(p(
        "Propulsion is two-tier: an <i>engine</i> XML file (loaded from "
        "<font face='Courier'>$JSBSIM_ROOT/engine/</font>) describes the "
        "engine; the aircraft XML references it and adds a "
        "<i>thruster</i> (the body that applies the actual force) and one "
        "or more <i>tanks</i>. Engine types are:"))
    for b in [
        "<b>piston_engine</b> — internal-combustion piston engine with "
        "power tables vs. RPM, throttle, mixture, MAP, altitude.",
        "<b>turbine_engine</b> — turbojet/turbofan with idle/military/AB "
        "tables.",
        "<b>turboprop_engine</b> — turboprop with shaft horsepower tables.",
        "<b>rocket_engine</b> — solid or liquid rocket with thrust/Isp.",
        "<b>electric_engine</b> — DC motor, power × throttle.",
        "<b>brushless_dc_motor</b> — torque vs. RPM curve.",
        "<b>rotor</b> — helicopter rotor (induced flow + flapping).",
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
        "An example engine file (<font face='Courier'>engine/eng_io320.xml"
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

    heading("flight_control: command shaping", 1, story)
    story.append(p(
        "The FCS is a directed graph of components arranged into named "
        "<i>channels</i>. Inputs come from pilot commands "
        "(<font face='Courier'>fcs/elevator-cmd-norm</font>, etc., set by "
        "the input device or script) and outputs flow into the aerodynamic "
        "deflection properties (<font face='Courier'>fcs/elevator-pos-rad"
        "</font>, etc.) that the aerodynamics functions read."))
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
        "Available FCS components include "
        "<font face='Courier'>summer, pure_gain, scheduled_gain, "
        "aerosurface_scale, kinematic, deadband, switch, fcs_function, "
        "pid, lag_filter, lead_lag_filter, washout_filter, "
        "second_order_filter, integrator, sensor, actuator</font> and "
        "the generic <font face='Courier'>fcs_function</font> which lets "
        "you embed any function-language expression as a block. PIDs and "
        "filters discretise their continuous-time form using the simulation "
        "<i>dt</i>."))

    heading("autopilot and system: same toolbox, different scope", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;autopilot&gt;</font> and "
        "<font face='Courier'>&lt;system&gt;</font> use the same FCS "
        "components and channel structure. They are split out because they "
        "execute as separate sub-groups: typical practice is to put basic "
        "stick/pedal shaping in <i>flight_control</i>, classical autopilot "
        "loops (altitude-hold, heading-hold, autothrottle) in "
        "<i>autopilot</i>, and avionics or electrical-system logic in "
        "<i>system</i> (which may be loaded from external files in "
        "<font face='Courier'>$AC/Systems/</font>)."))

    heading("aerodynamics: the core of the model", 1, story)
    story.append(p(
        "Aerodynamics is large enough to warrant its own chapter — see "
        "Chapter 5. The skeleton is:"))
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

    heading("input and output", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;input&gt;</font> enables an external "
        "interface, typically a TCP/UDP socket for telnet-style command/"
        "query interaction. <font face='Courier'>&lt;output&gt;</font> is "
        "much more common: a logging configuration for CSV files, "
        "FlightGear binary, sockets, etc."))
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
    heading("Aerodynamics — Deep Dive", 0, story)

    heading("The six axes and the function/table model", 1, story)
    story.append(p(
        "Inside <font face='Courier'>&lt;aerodynamics&gt;</font> the heart "
        "of the model is an arbitrary number of "
        "<font face='Courier'>&lt;function&gt;</font> elements grouped into "
        "<font face='Courier'>&lt;axis&gt;</font> blocks. JSBSim sums every "
        "function inside an axis to obtain that axis's total force or "
        "moment <i>in physical units</i> (lbf, ft·lbf). It does <b>not</b> "
        "do any additional non-dimensionalisation — you embed the "
        "<i><font name='DejaVu'>q̄</font>·S</i> factor yourself, by convention."))
    story.append(p(
        "Axis names map to indices (FGAerodynamics.cpp:57-69):"))
    code(
        "Forces (axis index 0..2)   Moments (axis index 3..5)\n"
        "  0  DRAG                     3  ROLL  (l)\n"
        "  1  SIDE                     4  PITCH (m)\n"
        "  2  LIFT                     5  YAW   (n)\n"
        "\n"
        "Alternative force axes:        Alternative moment frames:\n"
        "  X, Y, Z       (body)         frame=\"WIND\"\n"
        "  AXIAL, NORMAL (axial/norm)   frame=\"STABILITY\"")

    heading("How a single function evaluates", 1, story)
    story.append(p(
        "Every function returns a scalar each tick. A canonical drag "
        "term looks like:"))
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
        "Inside <font face='Courier'>FGAerodynamics::Run()</font> the "
        "values returned by all <font face='Courier'>&lt;axis name=\"DRAG\"&gt;"
        "</font> children are summed into the DRAG slot of "
        "<font face='Courier'>vFnative</font>; the LIFT and SIDE slots are "
        "filled the same way; then a rotation by <i>T<sub>w2b</sub></i> "
        "lifts wind-axis forces into the body frame, the moments computed "
        "by ROLL/PITCH/YAW are added at the AERORP, and the moments are "
        "finally transferred to the CG by "
        "<i>M<sub>cg</sub> = M<sub>arp</sub> + r<sub>arp→cg</sub> × F"
        "</i>."))

    heading("The function language", 1, story)
    story.append(p(
        "JSBSim's function language is a small Lisp-ish XML expression "
        "tree. The leaves are <font face='Courier'>&lt;value&gt;</font> "
        "(constant) and <font face='Courier'>&lt;property&gt;</font> "
        "(reference to the property tree); the internal nodes are operators."))
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
        "A more interesting example — induced drag, "
        "<i>C<sub>Di</sub> = C<sub>L</sub>² / (π·AR·e)</i> — turned into a "
        "JSBSim function:"))
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

    heading("Tables: 1-D, 2-D, 3-D, and higher", 1, story)
    story.append(p(
        "Tables are the workhorse of any non-trivial model — they let "
        "you encode the CFD-derived lookup of any coefficient against any "
        "combination of state variables. JSBSim uses <b>linear "
        "interpolation</b> in every dimension; outside the tabulated range "
        "the boundary value is clamped (no extrapolation), so it is your "
        "job to cover the operational envelope."))

    story.append(p(
        "<b>1-D table</b> (a vector lookup against one variable):"))
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
        "<b>2-D table</b> (e.g. drag vs alpha and flap angle):"))
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
        "<b>3-D table</b> (e.g. pitching moment vs alpha, elevator, Mach). "
        "You stack 2-D tables, each with a <font face='Courier'>breakPoint"
        "</font> attribute for the third dimension:"))
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
        "Higher dimensions are supported recursively. In practice 3-D is "
        "the limit of what you should build by hand; for 4-D and above use "
        "a script to generate the XML from a CFD database."))

    heading("Properties commonly used in aerodynamics", 1, story)
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
        "The aero-frame angular rates <font face='Courier'>p-aero, q-aero, "
        "r-aero</font> are the body-frame rates rotated into the wind frame "
        "(rotated by α only — the stability frame). Always use these for "
        "the damping derivatives, not the raw <font face='Courier'>p-rad_sec"
        "</font>."))

    heading("Non-dimensionalisation by hand", 1, story)
    story.append(p(
        "Because JSBSim does not non-dimensionalise for you, you wear the "
        "responsibility of writing the dimensional formula correctly. These "
        "are the textbook formulas you embed in <font face='Courier'>"
        "&lt;product&gt;</font>:"))
    math("Lift &nbsp;=&nbsp; C<sub>L</sub> · <font name='DejaVu'>q̄</font> · S")
    math("Drag &nbsp;=&nbsp; C<sub>D</sub> · <font name='DejaVu'>q̄</font> · S")
    math("Side &nbsp;=&nbsp; C<sub>Y</sub> · <font name='DejaVu'>q̄</font> · S")
    math("Roll moment &nbsp;=&nbsp; C<sub>l</sub> · <font name='DejaVu'>q̄</font> · S · b")
    math("Pitch moment &nbsp;=&nbsp; C<sub>m</sub> · <font name='DejaVu'>q̄</font> · S · <font name='DejaVu'>c̄</font>")
    math("Yaw moment &nbsp;=&nbsp; C<sub>n</sub> · <font name='DejaVu'>q̄</font> · S · b")
    story.append(p(
        "For damping derivatives multiply by the appropriate "
        "<i>b/(2V)</i> or <i><font name='DejaVu'>c̄</font>/(2V)</i> factor:"))
    math("Roll-rate moment &nbsp;=&nbsp; "
         "C<sub>lp</sub> · <font name='DejaVu'>q̄</font> · S · b · [b/(2V)] · p")
    math("Pitch-rate moment &nbsp;=&nbsp; "
         "C<sub>mq</sub> · <font name='DejaVu'>q̄</font> · S · <font name='DejaVu'>c̄</font> · [<font name='DejaVu'>c̄</font>/(2V)] · q")
    math("Yaw-rate moment &nbsp;=&nbsp; "
         "C<sub>nr</sub> · <font name='DejaVu'>q̄</font> · S · b · [b/(2V)] · r")
    math("<font name='DejaVu'>α̇</font> moment &nbsp;=&nbsp; "
         "C<sub>m_<font name='DejaVu'>α̇</font></sub> · <font name='DejaVu'>q̄</font> · S · <font name='DejaVu'>c̄</font> · [<font name='DejaVu'>c̄</font>/(2V)] · <font name='DejaVu'>α̇</font>")

    heading("Worked example: rolling moment due to roll rate", 1, story)
    story.append(p(
        "From <font face='Courier'>aircraft/c172p/c172p.xml:733</font>:"))
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
        "Cl<sub>p</sub> for the C-172 is constant at −0.484 — the wing's "
        "roll damping. Multiplying out gives a body-frame rolling moment "
        "in ft·lbf, which is what the ROLL axis expects."))

    heading("Static derivatives — getting them from CFD", 1, story)
    story.append(p(
        "Static derivatives (∂C/∂α, ∂C/∂β, ∂C/∂δ) characterise the "
        "<i>steady</i> aerodynamic response of the aircraft to changes in "
        "α, β and control deflections. They are obtained from CFD by "
        "running the aircraft as a rigid body in steady-state at a grid of "
        "(α, β, δ, M) points and reading off the resulting forces and "
        "moments. The list below is a typical minimum sweep for a "
        "subsonic conventional aircraft:"))
    table_data = [
        ["Derivative", "Independent vars", "CFD sweep"],
        ["C<sub>L</sub>(α, M, flap)",        "α, M, flap",
            "steady cruise over α ∈ [−6°, 18°], stalled = clip"],
        ["C<sub>D</sub>(α, M, flap, gear)",  "α, M, flap, gear",
            "Same matrix; CD = drag/<font name='DejaVu'>q̄</font>S"],
        ["C<sub>m</sub>(α, M, δ<sub>e</sub>)", "α, M, δ<sub>e</sub>",
            "α-sweep at each δ<sub>e</sub> and Mach"],
        ["C<sub>Y</sub>(β, δ<sub>r</sub>)",  "β, δ<sub>r</sub>",
            "β-sweep ∈ [−15°, 15°]"],
        ["C<sub>l</sub>(β, α, δ<sub>a</sub>)", "β, α, δ<sub>a</sub>",
            "β-sweep + δ<sub>a</sub> increments"],
        ["C<sub>n</sub>(β, α, δ<sub>r</sub>)", "β, α, δ<sub>r</sub>",
            "β-sweep + δ<sub>r</sub> increments"],
        ["C<sub>L</sub><sub>α</sub>", "α", "slope of CL-α curve"],
        ["C<sub>m</sub><sub>α</sub>", "α", "slope of Cm-α curve (negative → stable)"],
        ["C<sub>n</sub><sub>β</sub>", "β", "slope of Cn-β curve (positive → stable)"],
        ["C<sub>l</sub><sub>β</sub>", "β", "dihedral effect"],
    ]
    t = Table(wrap_table(table_data), colWidths=[4.0 * cm, 4.5 * cm, 8.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    heading("Dynamic (damping) derivatives — running CFD with motion", 1, story)
    story.append(p(
        "Dynamic derivatives describe the moment created by a rotation "
        "rate (p, q, r, <font name='DejaVu'>α̇</font>). They cannot be obtained from a steady-state "
        "snapshot of the geometry; you need <i>moving</i> CFD or the "
        "classical engineering analogues."))
    for b in [
        "<b>Forced oscillation</b>: in URANS or LES, run the aircraft "
        "oscillating sinusoidally about the relevant axis at a known "
        "amplitude and reduced frequency. Extract the in-phase and "
        "out-of-phase moment components — these give the static and "
        "damping derivatives respectively. Industry-standard tools: ANSYS "
        "Fluent, OpenFOAM with overset, STAR-CCM+, NASA OVERFLOW.",
        "<b>Quasi-steady method</b>: run several steady CFD cases with a "
        "constant rotation rate <i>p</i> imposed on the inertial frame; "
        "extract the rolling moment from each. The slope ΔC<sub>l</sub>/Δ"
        "(pb/2V) is C<sub>lp</sub>. Fast but limited to small angles.",
        "<b>Strip-theory / lifting-line</b>: a cheap engineering fallback. "
        "For early model bring-up, take handbook estimates "
        "(Roskam, Etkin, USAF DATCOM) — they are within ±30% of "
        "high-fidelity data for conventional aircraft.",
        "<b>System ID</b>: if you already have flight-test data, fit the "
        "damping derivatives by minimising the simulation residual on a "
        "doublet manoeuvre. This is what AIAA SciTech \"flight-validated "
        "model\" papers actually do.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Damping derivatives you should obtain at minimum:"))
    table_data = [
        ["Symbol",  "Meaning", "Typical sign", "Method"],
        ["C<sub>lp</sub>", "Roll damping",         "negative",
            "forced oscillation about X"],
        ["C<sub>lr</sub>", "Roll due to yaw rate", "positive",
            "forced oscillation about Z"],
        ["C<sub>mq</sub>", "Pitch damping",        "negative",
            "forced oscillation about Y"],
        ["C<sub>m_<font name='DejaVu'>α̇</font></sub>", "Pitch due to <font name='DejaVu'>α̇</font>",    "negative",
            "forced plunge oscillation"],
        ["C<sub>nr</sub>", "Yaw damping",          "negative",
            "forced oscillation about Z"],
        ["C<sub>np</sub>", "Yaw due to roll",      "small, signed",
            "forced oscillation about X"],
        ["C<sub>Yp</sub>", "Side force due to roll", "small",
            "from same X-oscillation run"],
        ["C<sub>Yr</sub>", "Side force due to yaw",  "small",
            "from same Z-oscillation run"],
    ]
    t = Table(wrap_table(table_data), colWidths=[2.6 * cm, 4.3 * cm, 2.6 * cm, 7.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
    ]))
    story.append(t)

    heading("Control derivatives", 1, story)
    story.append(p(
        "Control derivatives (Cm<sub>δe</sub>, Cl<sub>δa</sub>, Cn<sub>δr"
        "</sub>, …) are the slopes of moment vs. control deflection. They "
        "are static, so you obtain them in the same steady CFD batch as "
        "the static derivatives, simply by including control deflection as "
        "a sweep axis. For non-linear control authority (very common at "
        "high α or high deflection) prefer a 2-D table "
        "<font face='Courier'>(α, δ)</font> over a single coefficient."))
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

    heading("Ground effect and Reynolds effects", 1, story)
    story.append(p(
        "Ground effect is conventionally implemented as a "
        "<i>multiplier</i> on lift and drag, evaluated as a 1-D table "
        "against height-above-ground normalised by mean chord "
        "(<font face='Courier'>aero/h_b-mac-ft</font>):"))
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
        "Use <font face='Courier'>aero/function/kCLge</font> as a factor in "
        "the lift function. The same approach handles Mach effects (table "
        "vs. <font face='Courier'>velocities/mach</font>) and Reynolds "
        "(table vs. <font face='Courier'>velocities/reynolds</font>) if you "
        "have the CFD data to populate them."))

    heading("Stall and stall hysteresis", 1, story)
    story.append(p(
        "<font face='Courier'>&lt;alphalimits&gt;</font> clips the "
        "<i>physical</i> α used in aero calculations. "
        "<font face='Courier'>&lt;hysteresis_limits&gt;</font> defines a "
        "switching band — JSBSim exposes "
        "<font face='Courier'>aero/stall-hyst-norm</font> which is 0 below "
        "the low limit and 1 above the high limit. Use it as a second axis "
        "of a lift table to encode the difference between the un-stalled "
        "and stalled lift curves and get correct stall-recovery behaviour."))

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 6 - Core flight dynamics
    # ================================================================
    heading("The Equations of Motion Under the Hood", 0, story)
    story.append(p(
        "All the XML and tables eventually feed into a small set of "
        "ordinary differential equations. This chapter walks the math "
        "as JSBSim implements it."))

    heading("State vector", 1, story)
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

    heading("Quaternion attitude kinematics", 1, story)
    story.append(p(
        "Attitude is propagated as the quaternion <i>q<sub>i→b</sub></i> "
        "from inertial to body. The time derivative is the kinematic "
        "equation"))
    math("<font name='DejaVu'>q̇</font> &nbsp;=&nbsp; ½ · q ⊗ ω<sub>b/i</sub>")
    story.append(p(
        "where <i>ω<sub>b/i</sub></i> is the angular velocity of the body "
        "with respect to the inertial frame, expressed in the body frame "
        "(<font face='Courier'>vPQRi</font>). JSBSim's "
        "<font face='Courier'>FGQuaternion::GetQDot()</font> computes "
        "exactly this; <font face='Courier'>FGPropagate::CalculateQuatdot()"
        "</font> wraps it. Multiple integrators are available:"))
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
        "Default integrators are rectangular Euler for attitude and "
        "angular rate, Adams-Bashforth-2 for translational velocity, "
        "Adams-Bashforth-3 for position. The Buss integrators are "
        "interesting because they preserve quaternion norm exactly (no "
        "need for the renormalisation that rectangular Euler requires "
        "every tick)."))

    heading("Translational dynamics in the inertial frame", 1, story)
    story.append(p(
        "JSBSim solves Newton's second law in the inertial frame and "
        "transforms back to body coordinates for output:"))
    math("<font name='DejaVu'>v̇</font><sub>body</sub> &nbsp;=&nbsp; F/m &nbsp;−&nbsp; "
         "(p<sub>body</sub> + 2·T<sub>i2b</sub>·Ω<sub>planet</sub>) × v<sub>body</sub>"
         " &nbsp;−&nbsp; T<sub>i2b</sub>·Ω<sub>planet</sub> × (Ω<sub>planet</sub> × r<sub>i</sub>)")
    story.append(p(
        "The first term is the conventional <i>F = ma</i>. The second is "
        "the Coriolis acceleration, including the contribution from Earth's "
        "rotation (Ω<sub>planet</sub> ≈ 7.292·10⁻⁵ rad/s about the ECI Z "
        "axis). The third is the centrifugal acceleration from rotating "
        "about the Earth's centre. For terrestrial flight at "
        "transport-aircraft scales these are small but visible — they are "
        "what makes the simulator agree with the NASA-2015 check-cases."))

    heading("Rotational dynamics", 1, story)
    math("J · <font name='DejaVu'>ω̇</font><sub>i</sub> &nbsp;=&nbsp; M &nbsp;−&nbsp; "
         "ω<sub>i</sub> × (J · ω<sub>i</sub>)")
    story.append(p(
        "The term <i>ω × (Jω)</i> is the Euler gyroscopic torque "
        "(non-zero whenever the inertia tensor is not isotropic). "
        "<font face='Courier'>FGAccelerations::CalculatePQRdot()</font> "
        "computes this directly. The inertia tensor J in the body frame is "
        "maintained by <i>FGMassBalance</i> and is updated every tick to "
        "account for fuel burn and pointmass shifts. An optional "
        "gravity-gradient torque is enabled via the property "
        "<font face='Courier'>simulation/gravitational-torque</font>; "
        "useful for orbital mechanics."))

    heading("Total force and moment assembly", 1, story)
    story.append(p(
        "<font face='Courier'>FGAircraft</font> sums forces and moments "
        "from <i>aero, propulsion, ground, external, buoyant</i> models "
        "and exposes them as a single body-frame F and M to the "
        "Accelerations model. Gravity is treated separately by "
        "<font face='Courier'>FGInertial</font> (either spherical or "
        "WGS-84 with the J2 term) and added directly to the acceleration "
        "vector — keeping it out of M means the moment of gravity about "
        "the CG is automatically zero (gravity acts at the CG by "
        "definition)."))

    heading("Ground friction as a constrained problem", 1, story)
    story.append(p(
        "Standard explicit integration of stiff spring-damper landing-gear "
        "models is unstable. JSBSim instead poses the friction problem as a "
        "<i>linear-complementarity problem (LCP)</i>: each contact point "
        "imposes a non-penetration constraint normal to the runway and a "
        "Coulomb-friction constraint tangent to it. The unknowns are the "
        "Lagrange multipliers λ. The system "
        "<i>A · λ = b</i> with <i>A = J · M<sup>−1</sup> · Jᵀ</i> is solved "
        "iteratively (Projected Gauss-Seidel, Catto 2005) up to 50 "
        "iterations per tick — see "
        "<font face='Courier'>FGAccelerations::CalculateFrictionForces()"
        "</font>. The contact friction forces and the moment "
        "<i>r × F</i> are then added to the F and M vectors."))

    heading("Trim", 1, story)
    story.append(p(
        "Trim is implemented in <font face='Courier'>FGTrim</font> by a "
        "bracketed root-finder applied independently to each "
        "axis-control pair, iterated in an outer loop until all axes "
        "converge. It is <b>not</b> Newton-Raphson — JSBSim uses a "
        "linear-interpolation secant variant with a 0.9 relaxation factor "
        "to suppress oscillation. The modes are:"))
    table_data = [
        ["Mode", "Constraints", "Controls"],
        ["tLongitudinal", "<font name='DejaVu'>w̄</font>˙=0, <font name='DejaVu'>ū</font>˙=0, <font name='DejaVu'>q̄</font>˙=0", "α, throttle, elevator"],
        ["tFull",  "longitudinal + <font name='DejaVu'>v̇</font>=0, ṗ=0, ṙ=0 + ψ track",
            "+ φ, aileron, rudder, β"],
        ["tGround", "<font name='DejaVu'>w̄</font>˙=0, <font name='DejaVu'>q̄</font>˙=0, ṗ=0", "altitude, θ, φ"],
        ["tPullup", "longitudinal at target load factor", "α, throttle, elev"],
        ["tTurn",   "coordinated turn at target bank angle",
            "throttle, elevator, rudder"],
        ["tCustom", "user-defined (state, control) pairs", "any"],
    ]
    t = Table(wrap_table(table_data), colWidths=[3.0 * cm, 7.5 * cm, 6.0 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
    ]))
    story.append(t)

    heading("Atmospheric model", 1, story)
    story.append(p(
        "<font face='Courier'>FGStandardAtmosphere</font> implements the "
        "1976 U.S. Standard Atmosphere by piecewise linear lapse rates "
        "from 0 to 86 km. Properties are exposed under "
        "<font face='Courier'>atmosphere/</font>: "
        "<font face='Courier'>T-R</font>, "
        "<font face='Courier'>P-psf</font>, "
        "<font face='Courier'>rho-slugs_ft3</font>, "
        "<font face='Courier'>a-fps</font>. A custom atmosphere can be "
        "subclassed; the C-172 model offsets temperature to model density "
        "altitude effects."))

    heading("Winds and turbulence", 1, story)
    story.append(p(
        "<font face='Courier'>FGWinds</font> supports:"))
    for b in [
        "Steady wind in NED (set "
        "<font face='Courier'>atmosphere/wind-north-fps</font>, "
        "<font face='Courier'>wind-east-fps</font>, "
        "<font face='Courier'>wind-down-fps</font>).",
        "Linear wind shear with altitude.",
        "Gusts (1-cosine \"discrete gust\" model used in MIL-F-8785C).",
        "Dryden or von Kármán continuous turbulence with configurable "
        "intensity and scale lengths.",
        "Microburst model with three components and a vortex ring.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "<font face='Courier'>FGAuxiliary</font> consumes the wind vector "
        "to compute the airmass-relative velocity used by aerodynamics."))

    heading("Property tree", 1, story)
    story.append(p(
        "<font face='Courier'>FGPropertyManager</font> wraps SimGear's "
        "property tree. Every state variable, control input, FCS signal, "
        "aero coefficient and atmosphere quantity is exposed at a "
        "string path; values flow between models entirely through it. "
        "Aircraft XML <font face='Courier'>&lt;property&gt;</font> "
        "elements can <i>declare</i> a new property (creating it if "
        "needed); FCS components, aero functions and external interfaces "
        "all bind themselves to the tree."))
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
    heading("Building Your Own Aircraft, Step-by-Step", 0, story)
    story.append(p(
        "This is the practical playbook. We assume you have access to "
        "<b>geometry</b> (CAD or at least 3-view), <b>mass properties</b> "
        "(weight, CG, ideally an inertia estimate), <b>engine data</b> "
        "(power or thrust curves), and <b>aerodynamic data</b> (CFD or "
        "wind tunnel). The workflow below brings them together into a "
        "working JSBSim model in a couple of weeks of part-time effort."))

    heading("Step 1: Lay out the directory", 1, story)
    code(
        "$JSBSIM_ROOT/aircraft/MyAcft/\n"
        "    MyAcft.xml          # the main XML (this is what JSBSim loads)\n"
        "    reset00.xml         # initial conditions for default launch\n"
        "    Systems/            # (optional) external <system> files\n"
        "    Engines/            # (optional) aircraft-specific engine files\n"
        "$JSBSIM_ROOT/scripts/\n"
        "    MyAcft_takeoff.xml  # a script that loads MyAcft + reset00")
    story.append(p(
        "Engines and propellers can live in the project-wide "
        "<font face='Courier'>$JSBSIM_ROOT/engine/</font> directory if you "
        "want to reuse them across multiple airframes."))

    heading("Step 2: Skeleton XML", 1, story)
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

    heading("Step 3: Geometry, mass, and gear", 1, story)
    story.append(p(
        "<b>Geometry</b>: from your CAD, pull out the wing reference area "
        "<i>S</i>, wing span <i>b</i>, mean aerodynamic chord <i><font name='DejaVu'>c̄</font></i>, "
        "tail areas and arms. Pick the AERORP at 25% MAC and locate it in "
        "your structural frame. Locate the CG (any acceptable balance "
        "envelope point — you can shift it later with pointmasses)."))
    story.append(p(
        "<b>Mass</b>: empty weight + crew/passengers/cargo as pointmasses. "
        "For inertia, if you have a CAD model the easiest path is to "
        "export it to a kinematics tool (SolidWorks, Onshape, Fusion 360) "
        "that gives you I<sub>xx,yy,zz,xy,xz,yz</sub> about the CG "
        "directly. Otherwise estimate from radii of gyration "
        "(Roskam vol. V tables 9.1-9.4)."))
    story.append(p(
        "<b>Gear</b>: locate each contact point in the structural frame. "
        "Spring/damper choice is part craft, part calculation: aim for "
        "static deflection of 2-4 inches under weight on wheels, and a "
        "damping ratio of about 0.3-0.5. A quick estimator:"))
    math("k &nbsp;=&nbsp; W<sub>gear</sub> / Δ<sub>static</sub>"
         " &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
         "c &nbsp;=&nbsp; 2 ζ √(k · W<sub>gear</sub> / g)")

    heading("Step 4: Propulsion", 1, story)
    story.append(p(
        "Pick an engine file that matches your type. The standard "
        "JSBSim engine library has good starting points: "
        "<font face='Courier'>eng_io320</font> (160 hp 4-cyl), "
        "<font face='Courier'>CFM56</font> (turbofan), "
        "<font face='Courier'>F100-PW-229</font> (afterburning turbofan), "
        "<font face='Courier'>Estes_E9</font> (model rocket), "
        "<font face='Courier'>DJI_E305</font> (drone electric). For a new "
        "engine, copy an existing file and edit displacement / max power / "
        "BSFC / RPM range. Pair the engine with a thruster — "
        "<font face='Courier'>direct</font> for jets/rockets, "
        "<font face='Courier'>prop_*</font> for propellers."))
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

    heading("Step 5: Flight control system", 1, story)
    story.append(p(
        "The smallest possible FCS just maps "
        "<font face='Courier'>fcs/elevator-cmd-norm</font> (−1..+1) to "
        "<font face='Courier'>fcs/elevator-pos-rad</font> via an "
        "<font face='Courier'>aerosurface_scale</font>. Real aircraft add "
        "trim sums, rate limits, deadbands, gust filters, autopilots — "
        "but start minimal, get the aircraft flying open-loop, then add "
        "complexity."))

    heading("Step 6: Aerodynamics from CFD", 1, story)
    story.append(p(
        "This is the most labour-intensive step. The general procedure:"))
    story.append(bullet(
        "<b>1. Define your sweep grid.</b> A reasonable subsonic grid is "
        "α ∈ {−6, −4, −2, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18} deg, "
        "β ∈ {−15, −10, −5, 0, 5, 10, 15} deg, "
        "Mach ∈ {0.15, 0.30, 0.50, 0.70}, "
        "control deflections at 5-7 points each. That is ~3000 CFD cases "
        "for a full lookup matrix; in practice you decouple."))
    story.append(bullet(
        "<b>2. Run steady RANS cases</b> in your CFD tool of choice "
        "(OpenFOAM, Fluent, STAR-CCM+, SU2). For each case extract "
        "<i>F<sub>x</sub>, F<sub>y</sub>, F<sub>z</sub>, M<sub>x</sub>, "
        "M<sub>y</sub>, M<sub>z</sub></i> in the body frame about the "
        "AERORP and convert to coefficients by dividing by <i><font name='DejaVu'>q̄</font>·S</i>, "
        "<i><font name='DejaVu'>q̄</font>·S·b</i>, <i><font name='DejaVu'>q̄</font>·S·<font name='DejaVu'>c̄</font></i>."))
    story.append(bullet(
        "<b>3. Decouple where possible.</b> Generally take "
        "C<sub>L</sub>, C<sub>D</sub>, C<sub>m</sub> from the α-sweep at "
        "β=0; take C<sub>Y</sub>, C<sub>l</sub>, C<sub>n</sub> from "
        "β-sweeps at α=0; take control derivatives as the slope of moment "
        "vs. deflection at the trim condition. For high-α or transonic "
        "models the coupling is real and you do need a full 2-D or 3-D "
        "table."))
    story.append(bullet(
        "<b>4. Run damping derivative cases</b> — either forced oscillation "
        "or quasi-steady rolling/yawing/pitching with constant rate. "
        "Extract C<sub>lp</sub>, C<sub>mq</sub>, C<sub>nr</sub>, "
        "C<sub>lr</sub>, C<sub>np</sub>, C<sub>m_<font name='DejaVu'>α̇</font></sub>."))
    story.append(bullet(
        "<b>5. Tabulate and validate.</b> Plot every coefficient as a "
        "function of every independent variable. Look for non-monotonic "
        "behaviour you didn't expect — usually a sign of mesh or "
        "convergence problems."))
    story.append(bullet(
        "<b>6. Convert to JSBSim XML.</b> The format is a simple matrix of "
        "numbers in <font face='Courier'>&lt;tableData&gt;</font>. The "
        "Python script in the next chapter automates this."))

    heading("Step 7: Initial conditions and a smoke-test script", 1, story)
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
        "Run it with:"))
    code("JSBSim --script=scripts/MyAcft_smoke.xml --logdirectivefile=...")

    heading("Step 8: Iteration loop", 1, story)
    for b in [
        "<b>Does it trim?</b> If <font face='Courier'>do_simple_trim</font> "
        "fails, check sign conventions (elevator producing the right "
        "direction of pitching moment), check that "
        "Cm<sub>α</sub> &lt; 0 (statically stable in pitch), and check the "
        "α range of your tables covers the trim α.",
        "<b>Does it fly straight?</b> Static lateral-directional stability "
        "needs Cn<sub>β</sub> &gt; 0 and Cl<sub>β</sub> &lt; 0. If the "
        "aircraft rolls off, check the dihedral effect.",
        "<b>Does it respond like the real aircraft?</b> Compare phugoid, "
        "short-period, Dutch-roll, roll-mode and spiral-mode eigenvalues "
        "against published data or flight test.",
        "<b>Does it land?</b> Tune gear spring/damping until the bounce "
        "looks right. If the aircraft sinks through the runway, your "
        "spring is too soft or the contact point is too high (Z too "
        "positive in structural frame).",
    ]:
        story.append(bullet(b))

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 8 - CFD workflow in depth
    # ================================================================
    heading("CFD-to-JSBSim Workflow", 0, story)
    story.append(p(
        "This chapter describes the recommended workflow for generating "
        "JSBSim aerodynamic tables from CFD data, including the specific "
        "cases to run, the formulas to apply, and a reference Python "
        "script to convert results into JSBSim XML."))

    heading("Choosing a CFD solver", 1, story)
    for b in [
        "<b>OpenFOAM</b> (open source) — <i>simpleFoam</i> for steady "
        "RANS; <i>pimpleFoam</i> with overset for moving meshes. Free "
        "but mesh quality and turbulence model selection are on you.",
        "<b>SU2</b> (open source) — modern, adjoint capable, good for "
        "shape optimisation as well as analysis.",
        "<b>ANSYS Fluent / STAR-CCM+</b> — commercial, very mature. "
        "Worth the licence if you have it.",
        "<b>NASA OVERFLOW / FUN3D</b> — research-grade structured/"
        "unstructured RANS, available to U.S. universities.",
        "<b>XFLR5 / AVL</b> (vortex-lattice) — fast, surprisingly accurate "
        "for early-design subsonic estimates. Use it to bootstrap before "
        "spending CFD budget.",
    ]:
        story.append(bullet(b))

    heading("Recommended case matrix", 1, story)
    story.append(p(
        "For a conventional subsonic aircraft, a complete model needs the "
        "cases below. Each is a separate CFD run."))
    table_data = [
        ["Group", "Sweep", "α (deg)", "β (deg)", "Output"],
        ["Longitudinal static",
            "α at clean config, β=0",
            "−6 to +18 step 2",
            "0",
            "C<sub>L</sub>(α), C<sub>D</sub>(α), C<sub>m</sub>(α)"],
        ["Longitudinal w/ flap",
            "α × flap",
            "−4 to +14 step 2",
            "0",
            "ΔC<sub>L</sub>, ΔC<sub>D</sub>, ΔC<sub>m</sub> vs flap"],
        ["Longitudinal w/ elevator",
            "α × δ<sub>e</sub>",
            "−4 to +14 step 2",
            "0",
            "C<sub>m_δe</sub>(α, δ<sub>e</sub>)"],
        ["Lateral static",
            "β at α<sub>cruise</sub>",
            "α<sub>cr</sub>",
            "−15 to +15 step 3",
            "C<sub>Y</sub>(β), C<sub>l</sub>(β), C<sub>n</sub>(β)"],
        ["Aileron",
            "β × δ<sub>a</sub>",
            "α<sub>cr</sub>",
            "−10 to +10",
            "C<sub>l_δa</sub>, C<sub>n_δa</sub>"],
        ["Rudder",
            "β × δ<sub>r</sub>",
            "α<sub>cr</sub>",
            "−10 to +10",
            "C<sub>Y_δr</sub>, C<sub>n_δr</sub>"],
        ["Compressibility",
            "Mach",
            "0",
            "0",
            "ΔC<sub>D</sub>(M), ΔC<sub>m</sub>(M)"],
        ["Ground effect",
            "h/<font name='DejaVu'>c̄</font>",
            "α<sub>cr</sub>",
            "0",
            "k<sub>CL,ge</sub>(h/<font name='DejaVu'>c̄</font>), k<sub>CD,ge</sub>(h/<font name='DejaVu'>c̄</font>)"],
        ["Pitch damping",
            "forced osc. about Y",
            "α<sub>cr</sub>",
            "0",
            "C<sub>mq</sub>, C<sub>m_<font name='DejaVu'>α̇</font></sub>"],
        ["Roll damping",
            "forced osc. about X",
            "α<sub>cr</sub>",
            "0",
            "C<sub>lp</sub>, C<sub>Yp</sub>, C<sub>np</sub>"],
        ["Yaw damping",
            "forced osc. about Z",
            "α<sub>cr</sub>",
            "0",
            "C<sub>nr</sub>, C<sub>Yr</sub>, C<sub>lr</sub>"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[3.2 * cm, 3.6 * cm, 2.0 * cm, 2.0 * cm, 5.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(p(
        "If you have transonic or supersonic operations, add Mach as a "
        "third axis to all of the longitudinal cases. For a fighter aircraft "
        "or a UCAV operating to high α, double the α range and step size."))

    heading("Forced-oscillation method for damping derivatives", 1, story)
    story.append(p(
        "The cleanest way to get C<sub>mq</sub> et al. from CFD is to "
        "drive the geometry sinusoidally about the relevant axis with "
        "small amplitude and a known reduced frequency, then fit the "
        "in-phase and out-of-phase moment components. For pitch damping:"))
    math("θ(t) &nbsp;=&nbsp; θ<sub>0</sub> + Δθ · sin(ω t)")
    math("q(t) &nbsp;=&nbsp; Δθ · ω · cos(ω t)")
    math("C<sub>m</sub>(t) &nbsp;=&nbsp; C<sub>m,0</sub> &nbsp;+&nbsp; "
         "C<sub>m_α</sub> · Δα · sin(ωt) &nbsp;+&nbsp; "
         "[C<sub>mq</sub> + C<sub>m_<font name='DejaVu'>α̇</font></sub>] · (<font name='DejaVu'>c̄</font>/2V) · Δθ · ω · cos(ωt)")
    story.append(p(
        "Fit by least squares: the cos-coefficient is "
        "(C<sub>mq</sub> + C<sub>m_<font name='DejaVu'>α̇</font></sub>)·(<font name='DejaVu'>c̄</font>/2V)·Δθ·ω, the sin-coefficient "
        "is C<sub>m_α</sub>·Δα. Separating C<sub>mq</sub> from "
        "C<sub>m_<font name='DejaVu'>α̇</font></sub> requires an additional <i>plunge</i> oscillation "
        "(α changes without q changing). In practice many handbooks just "
        "publish the sum (C<sub>mq</sub> + C<sub>m_<font name='DejaVu'>α̇</font></sub>) and split it "
        "roughly 70/30."))
    story.append(p(
        "Recommended amplitudes and reduced frequencies for a transport: "
        "Δθ = 1°, k = ω<font name='DejaVu'>c̄</font>/(2V) ∈ [0.01, 0.1]. Five or ten cycles in CFD "
        "before extracting the fit."))

    heading("Quasi-steady method (faster)", 1, story)
    story.append(p(
        "Run several steady CFD cases with a <i>constant</i> body-fixed "
        "angular rate applied as a rotating reference frame. Plot the "
        "resulting moment against pb/(2V) (or q<font name='DejaVu'>c̄</font>/(2V), or rb/(2V)); the "
        "slope is the damping derivative. This is much cheaper than "
        "URANS but only valid for small rates and incompressible flow. "
        "Adequate for a first-cut model."))

    heading("Extracting and tabulating", 1, story)
    story.append(p(
        "Each CFD case gives you body-frame F and M about a known point. "
        "Convert to body-frame coefficients about the AERORP, then "
        "rotate force coefficients into wind-axis if your JSBSim model "
        "uses LIFT/DRAG/SIDE:"))
    math("C<sub>L</sub> &nbsp;=&nbsp; C<sub>Z</sub> cos α &nbsp;−&nbsp; "
         "C<sub>X</sub> sin α")
    math("C<sub>D</sub> &nbsp;=&nbsp; −C<sub>X</sub> cos α &nbsp;−&nbsp; "
         "C<sub>Z</sub> sin α")
    math("C<sub>Y</sub> &nbsp;(unchanged from body)")

    heading("Python helper: CFD CSV → JSBSim XML", 1, story)
    story.append(p(
        "A minimal generator that turns a CSV with columns "
        "<font face='Courier'>alpha_deg, flap_deg, CL, CD, Cm</font> "
        "into a JSBSim LIFT/DRAG/PITCH function block:"))
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

    heading("Validation: from CFD numbers to flight feel", 1, story)
    story.append(p(
        "Three classes of validation, in order of increasing difficulty:"))
    for b in [
        "<b>Coefficient plots</b> — overlay JSBSim coefficients against "
        "the CFD source data. Should match by construction; if not, you "
        "have a units bug.",
        "<b>Eigenvalue analysis</b> — linearise the JSBSim model at "
        "cruise with the bundled "
        "<font face='Courier'>python/JSBSim/utils/linearize</font> tool. "
        "Compare phugoid, short-period, Dutch-roll, roll, spiral roots "
        "against textbook estimates (Stevens-Lewis ch. 5) or published "
        "data for similar aircraft.",
        "<b>Manoeuvre matching</b> — run pitch doublets, aileron rolls, "
        "rudder kicks. Plot p, q, r, α, β. Compare against flight test or "
        "documented handling qualities (Cooper-Harper, MIL-F-8785C).",
    ]:
        story.append(bullet(b))

    story.append(PageBreak())

    # ================================================================
    # CHAPTER 9 - Reference appendices
    # ================================================================
    heading("Reference Appendices", 0, story)

    heading("Property tree cheat sheet", 1, story)
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

    heading("Common FCS components", 1, story)
    table_data = [
        ["Component", "Purpose"],
        ["summer", "Sum inputs with optional bias and clipping."],
        ["pure_gain", "y = k * x (k can be a property)"],
        ["scheduled_gain", "k = table(independent_var); y = k * x"],
        ["aerosurface_scale",
            "Map normalised input to physical deflection range."],
        ["kinematic",
            "Discrete positions with traverse times — flap, gear."],
        ["lag_filter", "First-order lag: ẏ = (x − y) / τ"],
        ["lead_lag_filter", "Continuous (a₀+a₁s)/(b₀+b₁s)"],
        ["washout_filter", "High-pass: τs/(τs+1)"],
        ["second_order_filter",
            "Notch/low-pass with 4 numerator + 4 denominator coefficients"],
        ["integrator", "y = ∫ x dt, with optional reset trigger"],
        ["deadband", "Output zero within a band around input"],
        ["switch", "Conditional logic with test/default cases"],
        ["fcs_function",
            "Embed an arbitrary function expression as an FCS block"],
        ["pid", "PID(Kp,Ki,Kd) with trigger, optional clipto"],
        ["sensor", "Adds noise, bias, drift, lag, delay"],
        ["actuator",
            "Rate limit, lag, hysteresis, deadband, fail modes"],
    ]
    t = Table(wrap_table(table_data), colWidths=[4.0 * cm, 12.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    heading("Engine type cross-reference", 1, story)
    table_data = [
        ["Engine class", "XML root tag", "Typical thruster",
            "Key inputs"],
        ["Piston",      "<piston_engine>", "<propeller>",
            "throttle, mixture, magnetos"],
        ["Turbojet/Turbofan",
            "<turbine_engine>", "<direct> or <nozzle>",
            "throttle, AB on/off"],
        ["Turboprop",   "<turboprop_engine>", "<propeller>",
            "throttle, propeller pitch"],
        ["Rocket",      "<rocket_engine>",  "<nozzle>",
            "throttle (often 0/1)"],
        ["Electric DC", "<electric_engine>", "<propeller>",
            "throttle (PWM)"],
        ["Brushless DC", "<brushless_dc_motor>", "<propeller>",
            "throttle, current limit"],
        ["Rotor",       "<rotor>", "(integrated)",
            "collective, cyclic, throttle"],
    ]
    t = Table(wrap_table(table_data),
              colWidths=[3.6 * cm, 3.4 * cm, 3.0 * cm, 6.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
    ]))
    story.append(t)

    heading("Source-code map", 1, story)
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

    heading("Bibliography and references", 1, story)
    for b in [
        "Berndt, J. S. <i>JSBSim Reference Manual</i> (online and PDF). "
        "https://jsbsim.sourceforge.net/documentation.html",
        "Stevens B. L., Lewis F. L. <i>Aircraft Control and Simulation</i>, "
        "2nd ed., Wiley, 2003. — definitive reference for the equations of "
        "motion JSBSim implements.",
        "Etkin B., Reid L. D. <i>Dynamics of Flight: Stability and "
        "Control</i>, 3rd ed., Wiley, 1996. — classical stability "
        "derivative definitions.",
        "Roskam, J. <i>Airplane Design, Vols. I-VIII</i>, DARcorp. — "
        "engineering estimates for inertia, gear, control-surface "
        "geometry.",
        "USAF DATCOM, <i>USAF Stability and Control DATCOM</i>, USAF "
        "AFFDL-TR-79-3032. — handbook estimates for stability and damping "
        "derivatives; useful sanity check on CFD.",
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

    heading("Closing thoughts", 1, story)
    story.append(p(
        "JSBSim's design rewards engineers who already think in terms of "
        "stability derivatives, frames and equations of motion: there is "
        "very little hidden magic. Most of what feels like rote "
        "configuration in the XML is actually a direct expression of the "
        "physics — a function multiplying a coefficient by <i><font name='DejaVu'>q̄</font>·S·<font name='DejaVu'>c̄</font>·…</i> "
        "is the textbook formula, not a JSBSim convention. The corollary "
        "is that when something goes wrong, the bug is almost always in "
        "the data, the units, or the signs — not in the simulator. Trust "
        "the framework, instrument it (the property tree makes "
        "instrumentation trivial), and iterate."))
    story.append(quote(
        "The model is wrong, but the simulator is right. — folklore"))

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
    add_part_separator(story, "Part II", "Extended Theory and Background")
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
    add_ext_further_reading(story)
    add_chapter_glossary(story)

    return story


# ============================================================================
# Extended chapters
# ============================================================================


def add_chapter_diagrams(story):
    story.append(PageBreak())
    heading("Visual Diagrams of the FDM Loop", 0, story)
    story.append(p(
        "JSBSim has no built-in graphical documentation. The ASCII "
        "diagrams in this chapter are reverse-engineered from the source "
        "and faithfully reflect data flow as of v2.0."))

    heading("Top-level simulation loop", 1, story)
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

    heading("Per-tick data flow between models", 1, story)
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

    heading("Body-frame, wind-frame and structural-frame sketch", 1, story)
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

    heading("Aerodynamic axis-to-force flow", 1, story)
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
    heading("Propulsion — Per-Engine-Type Reference", 0, story)

    heading("Piston engines", 1, story)
    story.append(p(
        "<font face='Courier'>FGPiston</font> models a four-stroke piston "
        "engine with manifold-absolute-pressure dynamics, mixture and "
        "throttle controls, magneto failures and altitude derating. "
        "Configuration parameters:"))
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
        "Power output is modelled as a parabolic relation in MAP and a "
        "linear-with-throttle/RPM scaling. Mixture affects density "
        "altitude — lean of peak penalises power, rich of peak penalises "
        "fuel flow. The model accounts for ram-air recovery at high speed."))

    heading("Turbine (turbojet/turbofan)", 1, story)
    story.append(p(
        "<font face='Courier'>FGTurbine</font> implements a two-spool "
        "engine with idle/military/afterburner regions and lookup-table "
        "thrust:"))
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
        "Each thrust table is normalised to 1.0 at the SL static "
        "condition; the model multiplies by the relevant rating "
        "(milthrust or maxthrust). Spool-up is modelled with first-order "
        "lags; the property "
        "<font face='Courier'>propulsion/engine[n]/n2-norm</font> can be "
        "fed to FCS to gate flap deployment or thrust-reverser logic."))

    heading("Turboprop", 1, story)
    story.append(p(
        "<font face='Courier'>FGTurboProp</font> couples a turbine "
        "core to a propeller. The XML adds a "
        "<font face='Courier'>maxpower</font> in shaft horsepower and a "
        "<font face='Courier'>betarangeend</font>:"))
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
        "The thruster must be a <font face='Courier'>&lt;propeller&gt;"
        "</font> (separate XML file) and the propeller's pitch is "
        "controlled either by a governor (constant speed) or directly "
        "by FCS commands."))

    heading("Rocket engines", 1, story)
    story.append(p(
        "<font face='Courier'>FGRocket</font> models a fixed-Isp "
        "rocket. Variable thrust is supported via throttle and a "
        "thrust-vs-time table; thrust vectoring is supported by a "
        "<font face='Courier'>&lt;nozzle&gt;</font> with steerable PYR "
        "angles. Suitable for boosters, sounding rockets, and missile "
        "models."))
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

    heading("Electric and brushless DC motors", 1, story)
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
        "Both models compute shaft torque from throttle (PWM) and a "
        "back-EMF curve. <font face='Courier'>FGBrushLessDCMotor</font> "
        "explicitly tracks current draw, which is useful for "
        "battery-life modelling — multiply current by terminal voltage "
        "for instantaneous power, then integrate against tank capacity to "
        "model battery state of charge."))

    heading("Helicopter rotor", 1, story)
    story.append(p(
        "<font face='Courier'>FGRotor</font> models a helicopter main "
        "or tail rotor using an analytical blade-element approach with "
        "inflow modelling, flapping dynamics and ground-effect. It is "
        "complex — for a first pass start from the J3Cub piston piston "
        "or the X15 examples in <font face='Courier'>aircraft/</font> "
        "rather than from scratch."))

    heading("Propellers", 1, story)
    story.append(p(
        "Propellers live in <font face='Courier'>engine/prop_*.xml"
        "</font> and reference C<sub>T</sub> and C<sub>P</sub> tables "
        "vs advance ratio J:"))
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
        "Use <font face='Courier'>p_factor</font> on the thruster to "
        "model the slight nose-left yawing moment from prop disc "
        "asymmetry at high α. <font face='Courier'>sense</font> is +1 "
        "for clockwise (viewed from cockpit) and −1 for counter-"
        "clockwise; this matters for torque reaction direction and "
        "twin-engine \"critical-engine\" effects."))

    heading("Fuel tanks", 1, story)
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
        "Tanks contribute mass and inertia (parallel-axis-shifted from "
        "tank location to CG) that decrease as fuel is consumed. "
        "Multiple tanks with different priorities let you model the "
        "real fuel system schedule (e.g. \"transfer from aux to main "
        "first\")."))


def add_chapter_fcs_deep(story):
    story.append(PageBreak())
    heading("Flight Control Components — Reference", 0, story)
    story.append(p(
        "Every FCS component has the same shape: a name, one or more "
        "<font face='Courier'>&lt;input&gt;</font> properties, "
        "component-specific configuration, optional "
        "<font face='Courier'>&lt;clipto&gt;</font>, and an "
        "<font face='Courier'>&lt;output&gt;</font> property that other "
        "components downstream can read. The output is computed in the "
        "<i>order</i> in which components appear in a channel."))

    heading("Summer / Pure gain / Aerosurface scale", 1, story)
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

    heading("Filters", 1, story)
    story.append(p(
        "Filters use Tustin (bilinear) discretisation. Each has a "
        "characteristic constant <font face='Courier'>c1..c5</font> that "
        "maps to the textbook coefficients."))
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

    heading("Integrator", 1, story)
    code(
        "<integrator name=\"alpha_int\">\n"
        "    <input>aero/alpha-rad</input>\n"
        "    <c1>1.0</c1>                              <!-- integration gain -->\n"
        "    <trigger>fcs/integrator-trigger</trigger> <!-- 0=run, 1=hold, -1=reset -->\n"
        "</integrator>")
    story.append(p(
        "The trigger property lets you anti-windup with conventional "
        "logic: hold while saturated, reset on disengage."))

    heading("PID controller", 1, story)
    code(
        "<pid name=\"AltitudeHold\">\n"
        "    <input>fcs/altitude-error-ft</input>\n"
        "    <kp>0.05</kp>\n"
        "    <ki type=\"ab3\">0.001</ki>            <!-- ab2/ab3 = Adams-Bashforth -->\n"
        "    <kd>0.10</kd>\n"
        "    <trigger>ap/altitude-hold-engaged</trigger>\n"
        "    <clipto> <min>-0.5</min><max>0.5</max> </clipto>\n"
        "</pid>")

    heading("Kinematic, deadband, switch", 1, story)
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

    heading("Sensor and actuator wrapping", 1, story)
    story.append(p(
        "Use <font face='Courier'>&lt;sensor&gt;</font> to simulate "
        "imperfect measurements (lag, bias, noise) and "
        "<font face='Courier'>&lt;actuator&gt;</font> to simulate "
        "imperfect surface actuation (rate limit, hysteresis, deadband, "
        "fail modes). Both are useful for fault-injection studies."))
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
    heading("Atmosphere, Winds, and Earth", 0, story)

    heading("ISA 1976 standard atmosphere", 1, story)
    story.append(p(
        "<font face='Courier'>FGStandardAtmosphere</font> evaluates the "
        "1976 US Standard Atmosphere — eight piecewise lapse-rate "
        "segments from sea level to 86 km geometric altitude. The "
        "model exposes:"))
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
        "<b>Custom atmosphere.</b> Inherit from "
        "<font face='Courier'>FGAtmosphere</font> in C++ and override "
        "<font face='Courier'>Calculate(double altitudeASL)</font>. For "
        "most needs the standard model plus a temperature offset "
        "(<font face='Courier'>atmosphere/delta-T</font>) is enough — "
        "shifting T while keeping P constant gives a density-altitude "
        "shift, which is how density-altitude effects (hot-and-high) are "
        "usually modelled."))

    heading("Winds and shear", 1, story)
    code(
        "atmosphere/wind-north-fps          steady wind from FGWinds\n"
        "atmosphere/wind-east-fps           (NED frame, points TO direction wind blows toward)\n"
        "atmosphere/wind-down-fps\n"
        "atmosphere/wind-mag-fps            magnitude\n"
        "atmosphere/psiw-rad                wind heading\n"
        "atmosphere/total-wind-north-fps    steady + turbulence + gust + shear\n"
        "atmosphere/turb-rate-rad_sec       Dryden/Karman turbulence angular component")
    story.append(p(
        "<b>Turbulence models</b>: select via "
        "<font face='Courier'>atmosphere/turb-type</font>:"))
    code(
        "0 ttNone            no turbulence\n"
        "1 ttStandard        legacy white-noise model\n"
        "2 ttCulp            John Culp's model (used in FlightGear)\n"
        "3 ttMilspec         MIL-F-8785C Dryden\n"
        "4 ttTustin          MIL-F-8785C Tustin discrete-Dryden")
    story.append(p(
        "For the MIL-spec models you set "
        "<font face='Courier'>atmosphere/turbulence/milspec/severity"
        "</font> on a 0-7 scale; the model auto-selects scale lengths "
        "and intensities according to the spec."))

    heading("Gusts (discrete)", 1, story)
    story.append(p(
        "A discrete \"1-cosine\" gust can be triggered by setting:"))
    code(
        "atmosphere/cosine-gust-start  -> set to 1 to start\n"
        "atmosphere/cosine-gust-frame  -> 1 BODY, 2 WIND, 3 LOCAL\n"
        "atmosphere/cosine-gust-duration\n"
        "atmosphere/cosine-gust-magnitude-ft_sec\n"
        "atmosphere/cosine-gust-startup-duration\n"
        "atmosphere/cosine-gust-steady-duration\n"
        "atmosphere/cosine-gust-end-duration\n"
        "atmosphere/cosine-gust-X-velocity   (and Y, Z in chosen frame)")

    heading("Microburst", 1, story)
    story.append(p(
        "A three-component microburst model (Vicroy + Mulgund) is "
        "available via "
        "<font face='Courier'>atmosphere/turbulence-cosine-set</font>. "
        "Used for go-around and wind-shear-recovery training scenarios."))

    heading("Inertial: gravity and Earth rotation", 1, story)
    story.append(p(
        "<font face='Courier'>FGInertial</font> publishes the gravity "
        "vector and the planet rotation rate. Two gravity models are "
        "available, selected via "
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
        "<b>Why this matters even for low-altitude flight.</b> The "
        "Coriolis acceleration at Mach 0.8 cruise is on the order of "
        "0.003 m/s² — small but non-zero. JSBSim correctly accounts for "
        "it, which is part of why it passes the NASA 2015 check cases. "
        "If you compare against simulators that use a flat-Earth "
        "approximation, expect small steady-state heading drifts when "
        "flying long distances east-west."))


def add_chapter_quaternions(story):
    story.append(PageBreak())
    heading("Quaternion Attitude — A Primer for the Code", 0, story)
    story.append(p(
        "Reading <font face='Courier'>FGPropagate</font> and "
        "<font face='Courier'>FGQuaternion</font> is much easier if you "
        "already speak quaternions. This chapter is a quick refresher "
        "with JSBSim-specific notation."))

    heading("Definition and conventions", 1, story)
    story.append(p(
        "A unit quaternion is a 4-tuple <i>q = (q<sub>0</sub>, q<sub>1</sub>"
        ", q<sub>2</sub>, q<sub>3</sub>)</i> with norm 1. JSBSim follows "
        "the Hamilton (i² = j² = k² = ijk = −1) convention; "
        "<font face='Courier'>FGQuaternion</font> stores them in the "
        "order (w, x, y, z) — i.e. the scalar component first."))
    math("q &nbsp;=&nbsp; cos(θ/2) &nbsp;+&nbsp; <b><font name='DejaVu'>n̂</font></b> · sin(θ/2)")
    story.append(p(
        "where <b><font name='DejaVu'>n̂</font></b> is the rotation axis and θ is the rotation angle. "
        "The quaternion that rotates a vector in the inertial frame into "
        "the body frame is <i>q<sub>i→b</sub></i> and the equivalent "
        "passive rotation is"))
    math("v<sub>body</sub> &nbsp;=&nbsp; q* · v<sub>inertial</sub> · q")
    story.append(p(
        "(with vectors lifted to pure quaternions, and · denoting "
        "Hamilton product). This is exactly what "
        "<font face='Courier'>FGQuaternion::GetTransformationMatrix()"
        "</font> precomputes as a 3×3 rotation matrix to use for fast "
        "frame transforms."))

    heading("Kinematic equation", 1, story)
    math("<font name='DejaVu'>q̇</font> &nbsp;=&nbsp; ½ · q · ω<sub>b/i</sub>")
    story.append(p(
        "Here <i>ω<sub>b/i</sub></i> is the inertial angular rate "
        "expressed as a pure quaternion <i>(0, p<sub>i</sub>, q<sub>i</sub>"
        ", r<sub>i</sub>)</i>. <font face='Courier'>FGQuaternion::GetQDot()"
        "</font> implements this in 12 floating-point operations."))
    code(
        "FGQuaternion FGQuaternion::GetQDot(const FGColumnVector3& PQR) const {\n"
        "    return FGQuaternion(\n"
        "        -0.5*( data[1]*PQR(eP) + data[2]*PQR(eQ) + data[3]*PQR(eR)),\n"
        "         0.5*( data[0]*PQR(eP) - data[3]*PQR(eQ) + data[2]*PQR(eR)),\n"
        "         0.5*( data[3]*PQR(eP) + data[0]*PQR(eQ) - data[1]*PQR(eR)),\n"
        "         0.5*(-data[2]*PQR(eP) + data[1]*PQR(eQ) + data[0]*PQR(eR))\n"
        "    );\n"
        "}")

    heading("Renormalisation", 1, story)
    story.append(p(
        "Numerical integration of <i><font name='DejaVu'>q̇</font></i> with Euler or Adams-Bashforth "
        "schemes does not preserve the unit norm — over time the "
        "quaternion drifts off the unit 3-sphere, equivalent to "
        "introducing a spurious dilation. JSBSim renormalises every "
        "tick by dividing by the magnitude (<font face='Courier'>"
        "FGQuaternion::Normalize()</font>). The Buss integrators avoid "
        "this by integrating with the exponential map directly:"))
    math("q(t+Δt) &nbsp;=&nbsp; q(t) · exp(½ · Δt · ω)")
    story.append(p(
        "which is exact for constant ω and stays unit-norm to "
        "floating-point precision."))

    heading("Euler angle extraction", 1, story)
    story.append(p(
        "<font face='Courier'>FGQuaternion::GetEulerDeg()</font> returns "
        "the conventional aircraft Euler angles (φ, θ, ψ) in degrees "
        "using a 3-2-1 (Z-Y-X intrinsic) sequence. The singularity at "
        "θ = ±90° is unavoidable — quaternions exist precisely to "
        "<i>avoid</i> the singularity in the integration, but they still "
        "have to project through it when you read out Euler angles. For "
        "highly aerobatic aircraft, do all your work in quaternion space "
        "or in DCM space and only extract Euler at the end."))


def add_chapter_worked_example(story):
    story.append(PageBreak())
    heading("Complete Worked Example: A Simple Aircraft", 0, story)
    story.append(p(
        "This chapter walks every section of a minimal but flyable "
        "aircraft — an Acme A-1 light single — pulling values from "
        "first-principles geometry, a piston engine reused from the "
        "library, and CFD-derived aerodynamic coefficients. The "
        "complete XML is reproduced in pieces with commentary."))

    heading("Header and reference data", 1, story)
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

    heading("Mass, balance and inertia", 1, story)
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

    heading("Landing gear", 1, story)
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

    heading("Propulsion", 1, story)
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

    heading("Flight control system", 1, story)
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

    heading("Aerodynamics (representative values from CFD)", 1, story)
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
        "<b>Sanity checks for this model</b>:"))
    for b in [
        "C<sub>Lα</sub> ≈ 5.4/rad (slope of the lift table near α=0). "
        "Typical for a Hershey-bar wing at AR ≈ 7.3 is around 4.7/rad — "
        "our number is close enough.",
        "C<sub>Lmax</sub> ≈ 1.5. Reasonable for a clean wing.",
        "C<sub>D0</sub> = 0.025. Around the right number for a "
        "fixed-gear single.",
        "Statically stable: C<sub>mα</sub> = −0.5 &lt; 0, "
        "C<sub>nβ</sub> = +0.06 &gt; 0, C<sub>lβ</sub> = −0.08 &lt; 0.",
        "Elevator-derivative sign: C<sub>mδe</sub> = −1.1. Trailing-edge "
        "down (positive δ<sub>e</sub>) produces nose-down pitch — that "
        "matches our sign convention.",
    ]:
        story.append(bullet(b))


def add_chapter_scripts_ic(story):
    story.append(PageBreak())
    heading("Initial Conditions, Scripts, and Resets", 0, story)

    heading("Initial conditions (reset files)", 1, story)
    story.append(p(
        "The IC file sets every state variable to a self-consistent "
        "starting point for the simulation. The minimal set is "
        "position (3), attitude (3), velocity (3) — JSBSim then computes "
        "α, β, <font name='DejaVu'>q̄</font>, Mach internally. You can over-specify and let JSBSim "
        "resolve, but explicit is better."))
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
        "Other useful IC elements:"))
    code(
        "<gamma unit=\"DEG\"> 0 </gamma>          flight path angle\n"
        "<vnorth>0</vnorth><veast>0</veast><vdown>0</vdown>   NED wind-rel velocity\n"
        "<roc   unit=\"FT/MIN\"> 0 </roc>          rate of climb\n"
        "<altitudeAGL unit=\"FT\"> 0 </altitudeAGL> above ground level\n"
        "<targetNlf> 1 </targetNlf>               target load factor for trim-pullup")

    heading("Scripts (event-based scenarios)", 1, story)
    story.append(p(
        "A script is the closed-form description of a flight test "
        "scenario: a sequence of events with conditions and property "
        "actions. The Run loop ticks the model at the specified "
        "<font face='Courier'>dt</font> until it reaches "
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
        "<b>Action types</b> on <font face='Courier'>&lt;set&gt;</font>:"))
    code(
        "FG_VALUE   set property to value immediately (default)\n"
        "FG_DELTA   add value to current property\n"
        "FG_RAMP    linear ramp over tc seconds\n"
        "FG_EXP     first-order exponential approach with tc seconds")
    story.append(p(
        "<b>Conditions</b>: any boolean expression over properties, "
        "using <font face='Courier'>ge le gt lt eq nq and or not</font>. "
        "Conditions can be nested via "
        "<font face='Courier'>&lt;condition logic=\"AND|OR\"&gt;"
        "</font>."))


def add_chapter_validation(story):
    story.append(PageBreak())
    heading("Validation Workflow", 0, story)
    story.append(p(
        "A model that compiles and trims is only the first step. The "
        "industry-standard validation steps below catch the vast "
        "majority of modelling bugs before they reach a customer."))

    heading("Step 1: trim diagnostics", 1, story)
    story.append(p(
        "Run <font face='Courier'>simulation/do_simple_trim</font> = 1 "
        "(longitudinal) and check the resulting elevator and throttle "
        "positions are inside the actual control envelope. If trim α is "
        "near the top of the alpha-limits, the trim is unstalled by "
        "luck only; lower the cruise speed or check your "
        "C<sub>L</sub>(α) curve."))

    heading("Step 2: open-loop step responses", 1, story)
    story.append(p(
        "Run pitch doublets, aileron pulses and rudder kicks from a "
        "trimmed condition. Plot p, q, r, α, β, φ, θ, ψ:"))
    for b in [
        "<b>Phugoid</b>: oscillatory at ~30-60 s period, lightly damped "
        "(ζ ≈ 0.05). Visible as long-period altitude and airspeed swings "
        "after a pitch perturbation.",
        "<b>Short period</b>: ~2-5 s period, well damped (ζ ≈ 0.5). "
        "Visible as a rapid pitch-rate oscillation after a doublet.",
        "<b>Roll mode</b>: first-order, time constant ~0.5-1.5 s. Visible "
        "as exponential decay of p after an aileron kick.",
        "<b>Dutch roll</b>: ~3-6 s period, ζ ≈ 0.05-0.3. Coupled yaw-roll "
        "after a rudder kick.",
        "<b>Spiral mode</b>: very slow (~30-300 s time constant), often "
        "slightly unstable for conventional aircraft.",
    ]:
        story.append(bullet(b))

    heading("Step 3: linear model extraction", 1, story)
    story.append(p(
        "JSBSim ships a Python utility "
        "(<font face='Courier'>python/JSBSim/utils/linearize.py</font>) "
        "that builds an A, B, C, D linear model at a trim point. Compute "
        "the eigenvalues of A and compare poles against the closed-form "
        "estimates of Etkin or Stevens-Lewis. The order of magnitude "
        "should agree; if a pole is in the wrong half-plane, you have "
        "a sign error in your aero coefficients."))

    heading("Step 4: performance envelope check", 1, story)
    table_data = [
        ["Quantity", "How to obtain in JSBSim", "Compare against"],
        ["V<sub>S0</sub> stall speed (clean)",
            "Trim at min α holding altitude, decrement throttle",
            "POH or design target"],
        ["V<sub>S1</sub> stall speed (flaps)",
            "Same but with flap pos = max",
            "POH"],
        ["V<sub>max</sub>",
            "Full throttle level flight, record speed",
            "POH"],
        ["Best rate of climb (V<sub>y</sub>)",
            "Climb at various speeds, find max ROC",
            "POH chart"],
        ["Service ceiling",
            "Step-altitude trims, find h at ROC = 100 fpm",
            "POH"],
        ["Range",
            "Cruise at best-economy, integrate fuel burn",
            "POH"],
    ]
    t = Table(wrap_table(table_data), colWidths=[5.0 * cm, 6.0 * cm, 5.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f4f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)

    heading("Step 5: handling-qualities check", 1, story)
    story.append(p(
        "If you care about pilot feel, evaluate against MIL-F-8785C / "
        "MIL-HDBK-1797 handling-qualities specifications. The most "
        "valuable single number is the <i>C* parameter</i> "
        "(pitch-rate weighted load factor) plotted on a Cooper-Harper "
        "boundary chart at the cruise condition. JSBSim outputs all "
        "the necessary properties to compute it offline."))

    heading("Step 6: flight-test comparison", 1, story)
    story.append(p(
        "Where flight-test data exists, run the same manoeuvre in "
        "JSBSim with the same inputs and overlay. The disagreements you "
        "see are a recipe for the next iteration of CFD or coefficient "
        "tuning. Beware of \"chasing the flight\": tuning JSBSim to "
        "match one manoeuvre often degrades others. Always validate "
        "against a held-out manoeuvre set."))


def add_chapter_troubleshooting(story):
    story.append(PageBreak())
    heading("Common Bugs and How to Diagnose Them", 0, story)
    story.append(p(
        "These are the failure modes most newcomers encounter, in "
        "rough order of frequency. The solution column points at the "
        "first thing to inspect."))
    table_data = [
        ["Symptom", "Likely cause", "First check"],
        ["Aircraft \"falls through\" the runway at IC",
            "Gear Z coordinate has wrong sign or wrong unit",
            "<font face='Courier'>&lt;contact&gt;</font> Z negative if "
            "gear is below the structural-frame origin"],
        ["Aircraft is upside down or rotates 180° on startup",
            "ψ vs heading conventions or "
            "negated_crossproduct_inertia mismatch",
            "Swap inertia sign attribute"],
        ["Trim fails immediately",
            "α range in CFD tables doesn't span trim α",
            "Set <font face='Courier'>&lt;output&gt;</font> for α and run "
            "unwise — see what α it asks for"],
        ["Trim converges but aircraft pitches down nose-first",
            "C<sub>mα</sub> sign error (model is statically unstable)",
            "Plot Cm vs α; slope must be negative"],
        ["Aircraft yaws sideways uncontrollably",
            "C<sub>nβ</sub> sign error",
            "Slope must be positive"],
        ["Slow but steady roll-off",
            "Asymmetric pointmass or aileron not centred",
            "Check pointmass Y locations sum to zero"],
        ["Pitch oscillates at 0.5-2 Hz",
            "Insufficient C<sub>mq</sub> or wrong sign",
            "Should be negative; magnitude 5-15 for GA"],
        ["Aileron input has no roll response",
            "C<sub>lδa</sub> wrong sign or aileron pos property not "
            "matching aero coefficient property",
            "Trace fcs/left-aileron-pos-rad through to the function"],
        ["Drag enormous at trim",
            "Forgot to subtract reference drag, or "
            "CFD coefficients in body frame fed to LIFT/DRAG axes",
            "Compute D = C<sub>D</sub>·<font name='DejaVu'>q̄</font>·S by hand; "
            "compare to F<sub>x,aero,body</sub>"],
        ["Engine produces no thrust",
            "Tank capacity = 0 or feed indices wrong",
            "Check <font face='Courier'>propulsion/tank[n]/contents-lbs"
            "</font>"],
        ["Simulation crashes with NaN",
            "Divide-by-zero in a function (often /Vt at zero airspeed) "
            "or quaternion gone non-unit",
            "Add <font face='Courier'>&lt;clipto&gt;</font> or guard "
            "with <font face='Courier'>&lt;ifthen&gt;</font>"],
        ["Aircraft \"sinks\" through ground after touch-down",
            "Spring constant too soft for the weight",
            "k ≥ W / 0.5 ft for normal damping rates"],
        ["Bounces violently on landing",
            "Damping coefficient too low",
            "Aim for ζ ≈ 0.4-0.6 (c = 2ζ√(km))"],
        ["FCS output stuck at clipto",
            "Saturated; integrator wound up",
            "Add an anti-windup trigger to the PID"],
        ["FlightGear shows the aircraft jittering",
            "Output rate mismatch or FG/FDM timestep diverge",
            "Set output rate to 60 Hz, FG to 60 Hz too"],
    ]
    t = Table(wrap_table(table_data), colWidths=[4.8 * cm, 5.4 * cm, 6.3 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d5d9b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
    heading("Python API", 0, story)
    story.append(p(
        "JSBSim ships a Python module (<font face='Courier'>jsbsim"
        "</font>) on PyPI and conda-forge that wraps the C++ library. "
        "It is the recommended way to drive JSBSim from machine-learning "
        "code, batch parameter studies, or unit tests."))

    heading("Quick start", 1, story)
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

    heading("Reading and writing properties", 1, story)
    code(
        "# All properties accessible by string path\n"
        "fdm['fcs/elevator-cmd-norm'] = -0.1     # nose-up command\n"
        "fdm['fcs/throttle-cmd-norm'] = 0.8\n"
        "alpha = fdm['aero/alpha-deg']\n"
        "p, q, r = (fdm[f'velocities/{ax}-rad_sec'] for ax in 'pqr')\n"
        "\n"
        "# Snapshot the full property tree (slow)\n"
        "snapshot = fdm.query_property_catalog('')")

    heading("Trim and linearisation", 1, story)
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

    heading("Batch parameter studies", 1, story)
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
    heading("Extended Property Reference", 0, story)
    story.append(p(
        "The complete property tree is published by JSBSim itself with "
        "<font face='Courier'>fdm.query_property_catalog('')</font>. "
        "The most useful properties for instrumentation and machine "
        "learning are grouped here."))

    heading("Time", 1, story)
    code(
        "simulation/sim-time-sec                 simulation time since reset\n"
        "simulation/frame                        tick counter\n"
        "simulation/dt                           timestep size (s)\n"
        "simulation/integrator/rate/rotational\n"
        "simulation/integrator/rate/translational\n"
        "simulation/integrator/position/rotational\n"
        "simulation/integrator/position/translational")

    heading("Atmosphere and winds", 1, story)
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

    heading("Position", 1, story)
    code(
        "position/lat-geod-deg, lat-gc-rad      geodetic and geocentric lat\n"
        "position/long-gc-deg\n"
        "position/h-sl-ft, h-sl-meters          altitude above MSL\n"
        "position/h-agl-ft                      altitude above ground\n"
        "position/geod-alt-ft\n"
        "position/distance-from-start-mag-mt    great-circle distance\n"
        "position/terrain-elevation-asl-ft")

    heading("Attitude", 1, story)
    code(
        "attitude/phi-rad, theta-rad, psi-rad   Euler\n"
        "attitude/phi-deg, theta-deg, psi-deg   degrees\n"
        "attitude/heading-true-rad\n"
        "attitude/pitch-rad, roll-rad\n"
        "/sim/attitude/q[0..3]                  quaternion components (if exposed)")

    heading("Velocities", 1, story)
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

    heading("Aerodynamic state", 1, story)
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

    heading("Forces and moments (body frame)", 1, story)
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

    heading("Accelerations", 1, story)
    code(
        "accelerations/udot-ft_sec2, vdot-ft_sec2, wdot-ft_sec2\n"
        "accelerations/pdot-rad_sec2, qdot-rad_sec2, rdot-rad_sec2\n"
        "accelerations/a-pilot-x-ft_sec2        at the EYEPOINT\n"
        "accelerations/n-pilot-x-norm           load factor at EYEPOINT, g\n"
        "accelerations/Nz                       normal load factor")

    heading("FCS commands and positions", 1, story)
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

    heading("Propulsion", 1, story)
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

    heading("Simulation control", 1, story)
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
    heading("Glossary and Symbol Index", 0, story)

    table_data = [
        ["Symbol", "Meaning"],
        ["α (alpha)",      "Angle of attack — angle between the body X axis and the projection of relative wind onto the body X-Z plane."],
        ["β (beta)",       "Sideslip angle — angle between relative wind and the body X-Z plane."],
        ["<font name='DejaVu'>α̇</font> (alphadot)",   "Time rate of change of α."],
        ["<font name='DejaVu'>q̄</font> (qbar)",       "Dynamic pressure, ½ρV²."],
        ["ρ (rho)",        "Atmospheric density."],
        ["V<sub>t</sub>",   "True airspeed (magnitude of velocity relative to the air mass)."],
        ["V<sub>c</sub>",   "Calibrated airspeed (compressibility-corrected indicated airspeed)."],
        ["V<sub>e</sub>",   "Equivalent airspeed (density-corrected indicated airspeed)."],
        ["M",              "Mach number, V<sub>t</sub>/a."],
        ["a",              "Speed of sound."],
        ["p, q, r",        "Body-frame roll, pitch, yaw angular rates."],
        ["u, v, w",        "Body-frame translational velocity components."],
        ["φ, θ, ψ",        "Bank, pitch, heading Euler angles (3-2-1 sequence)."],
        ["γ (gamma)",       "Flight path angle (positive climb)."],
        ["S",              "Wing reference area."],
        ["b",              "Wing span."],
        ["<font name='DejaVu'>c̄</font> (cbar)",       "Mean aerodynamic chord."],
        ["AR",             "Aspect ratio, b²/S."],
        ["e",              "Oswald efficiency factor (0.7-0.95 typical)."],
        ["AERORP",          "Aerodynamic reference point — origin for aerodynamic moments."],
        ["VRP",            "Visual reference point — origin used by external viewers."],
        ["EYEPOINT",        "Pilot eye position."],
        ["AGL",             "Above ground level."],
        ["MSL",             "Mean sea level."],
        ["WGS-84",          "World Geodetic System 1984 — Earth ellipsoid model used by GPS and JSBSim."],
        ["ECEF",            "Earth-centred, Earth-fixed (rotates with the planet)."],
        ["ECI",             "Earth-centred inertial (non-rotating)."],
        ["NED",             "North-East-Down local tangent plane."],
        ["LCP",             "Linear complementarity problem — formulation of contact friction."],
        ["FDM",             "Flight Dynamics Model."],
        ["FCS",             "Flight Control System."],
        ["IC",              "Initial conditions."],
        ["BSFC",            "Brake specific fuel consumption."],
        ["MAP",             "Manifold absolute pressure (piston engines)."],
        ["N1, N2",          "Low-pressure and high-pressure spool speeds (turbine engines)."],
        ["TSFC",            "Thrust specific fuel consumption (turbines)."],
        ["CFD",             "Computational Fluid Dynamics."],
        ["RANS",            "Reynolds-Averaged Navier-Stokes."],
        ["URANS",           "Unsteady RANS."],
        ["LES",             "Large-eddy simulation."],
        ["AVL",             "Athena Vortex Lattice (Drela)."],
        ["DATCOM",          "USAF Stability and Control DATCOM handbook."],
        ["POH",             "Pilot's Operating Handbook."],
        ["TAS",             "True airspeed (=V<sub>t</sub>)."],
        ["IAS",             "Indicated airspeed."],
        ["CAS",             "Calibrated airspeed (=V<sub>c</sub>)."],
        ["EAS",             "Equivalent airspeed (=V<sub>e</sub>)."],
        ["KCAS / KTAS / KIAS",
            "Knots calibrated/true/indicated airspeed."],
    ]
    t = Table(wrap_table(table_data), colWidths=[3.0 * cm, 13.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
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
        "<i>End of the Ultimate JSBSim Reference.</i> Bug reports and "
        "improvements welcome at https://github.com/JSBSim-Team/jsbsim."))


# ============================================================================
# PART II — Extended theory chapters
# ============================================================================


def add_part_separator(story, label, title):
    """A title page introducing a part of the book."""
    story.append(PageBreak())
    story.append(Spacer(1, 60 * mm))
    story.append(Paragraph(label, ParagraphStyle(
        "PartLabel", fontName="Helvetica-Bold", fontSize=18,
        textColor=colors.HexColor("#1d5d9b"), alignment=TA_CENTER,
        spaceAfter=12)))
    story.append(Paragraph(title, ParagraphStyle(
        "PartTitle", fontName="Helvetica-Bold", fontSize=28,
        textColor=colors.HexColor("#0d3b66"), alignment=TA_CENTER,
        leading=34)))
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "The remainder of this manual moves from the practical "
        "&quot;how-to&quot; of Part I into a deeper, citation-driven treatment "
        "of the mathematics, physics, aerodynamics, geodesy, propulsion "
        "and verification machinery JSBSim implements. Read it linearly to "
        "build a complete mental model, or use it as a reference once you "
        "hit a topic in Part I that you want to understand in depth.",
        ParagraphStyle("PartIntro", parent=BODY_STYLE,
                       alignment=TA_CENTER, fontSize=11, leading=15,
                       leftIndent=24 * mm, rightIndent=24 * mm)))


# ----------------------------------------------------------------------------
def add_ext_math_fundamentals(story):
    story.append(PageBreak())
    heading("Mathematics for Flight Dynamics", 0, story)
    story.append(p(
        "Every line of JSBSim is at root a manipulation of three-vectors, "
        "rotation matrices, quaternions, and the tensor that ties them all "
        "together — the inertia tensor. This chapter is the compact "
        "reference for those objects. We assume calculus and basic linear "
        "algebra; everything beyond is built up from scratch."))

    heading("Vectors in three dimensions", 1, story)
    story.append(p(
        "A 3-vector is an ordered triple <b>v</b> = (v<sub>x</sub>, "
        "v<sub>y</sub>, v<sub>z</sub>). Two operations are central:"))
    math("Dot product: &nbsp; <b>a</b>·<b>b</b> = a<sub>x</sub>b<sub>x</sub>"
         " + a<sub>y</sub>b<sub>y</sub> + a<sub>z</sub>b<sub>z</sub> = "
         "|<b>a</b>||<b>b</b>| cos θ")
    math("Cross product: &nbsp; (<b>a</b>×<b>b</b>)<sub>i</sub> = "
         "ε<sub>ijk</sub> a<sub>j</sub> b<sub>k</sub>; &nbsp;"
         "|<b>a</b>×<b>b</b>| = |<b>a</b>||<b>b</b>| sin θ")
    story.append(p(
        "The dot product is a scalar; the cross product is a vector "
        "perpendicular to both inputs. Both are written in JSBSim source "
        "as <font face='Courier'>FGColumnVector3</font> overloads."))
    story.append(p(
        "<b>Triple product.</b> The scalar triple product "
        "<b>a</b> · (<b>b</b> × <b>c</b>) equals the signed volume of the "
        "parallelepiped spanned by the three vectors. The vector triple "
        "product satisfies "
        "<b>a</b> × (<b>b</b> × <b>c</b>) = (<b>a</b>·<b>c</b>)<b>b</b> − "
        "(<b>a</b>·<b>b</b>)<b>c</b> — the 'BAC-CAB' identity used in "
        "rigid-body kinematics."))
    story.append(p(
        "<b>Projection.</b> The component of <b>a</b> along the unit "
        "vector <b><font name='DejaVu'>n̂</font></b> is <b>a</b>·<b><font name='DejaVu'>n̂</font></b>; the vector projection is "
        "(<b>a</b>·<b><font name='DejaVu'>n̂</font></b>)<b><font name='DejaVu'>n̂</font></b>. This is used to extract drag "
        "components along the relative-wind direction, normal forces "
        "along the ellipsoid normal, etc."))

    heading("Rotation matrices in SO(3)", 1, story)
    story.append(p(
        "A rotation matrix <b>R</b> ∈ SO(3) is a 3×3 real matrix with "
        "<b>R</b><sup>T</sup><b>R</b> = <b>I</b> (orthogonal) and "
        "det(<b>R</b>) = +1 (proper, no reflection). Two consequences:"))
    for b in [
        "Inversion is trivial: <b>R</b><sup>−1</sup> = <b>R</b><sup>T</sup>. "
        "JSBSim never computes a numerical inverse of a rotation matrix.",
        "Composition is matrix multiplication: a rotation by <b>R<sub>1</sub></b> "
        "followed by <b>R<sub>2</sub></b> is <b>R<sub>2</sub></b><b>R<sub>1</sub></b>. "
        "Composition is non-commutative.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "The three elementary rotations about the body axes are the "
        "building blocks of every aerospace Euler-angle convention:"))
    code(
        "         | 1   0     0   |          |  cθ   0   sθ |          | cψ -sψ  0 |\n"
        "R_x(φ) = | 0  cφ    sφ   |  R_y(θ)= |   0   1    0 |  R_z(ψ)= | sψ  cψ  0 |\n"
        "         | 0 -sφ    cφ   |          | -sθ   0   cθ |          |  0   0  1 |")
    story.append(p(
        "Note the sign convention: these matrices rotate <i>vectors</i> in "
        "the active sense (or equivalently transform <i>frames</i> in the "
        "passive sense — JSBSim uses the passive convention)."))

    heading("The 3-2-1 aerospace Euler sequence", 1, story)
    story.append(p(
        "Aircraft attitude is conventionally given by yaw ψ, then pitch θ, "
        "then roll φ, applied as intrinsic rotations about Z, then Y', then "
        "X''. The combined matrix transforming a vector from the local "
        "NED frame to the body frame is"))
    math("R<sup>b</sup><sub>n</sub> = R<sub>x</sub>(φ) R<sub>y</sub>(θ) "
         "R<sub>z</sub>(ψ)")
    story.append(p(
        "Multiplied out element by element this gives the classical 9-entry "
        "direction cosine matrix found in every aerospace textbook (Stevens "
        "&amp; Lewis Eq. 1.4-7). The 3-2-1 sequence has a singularity at "
        "θ = ±90° where ψ and φ are no longer separately determined — "
        "the well-known &quot;gimbal lock.&quot;"))

    heading("The inertia tensor", 1, story)
    story.append(p(
        "For a rigid body with continuous mass distribution ρ(<b>r</b>), "
        "the inertia tensor about a point is"))
    math("<b>I</b> = ∫∫∫ ρ(<b>r</b>) (|<b>r</b>|²<b>1</b> − "
         "<b>r</b>⊗<b>r</b>) dV")
    story.append(p(
        "where <b>1</b> is the 3×3 identity and ⊗ is the outer product. "
        "Element-wise, the diagonal terms (moments of inertia)"))
    math("I<sub>xx</sub> = ∫(y²+z²) dm; &nbsp; I<sub>yy</sub> = ∫(x²+z²) dm;"
         " &nbsp; I<sub>zz</sub> = ∫(x²+y²) dm")
    story.append(p(
        "and the off-diagonal terms (products of inertia)"))
    math("I<sub>xy</sub> = ∫xy dm; &nbsp; I<sub>xz</sub> = ∫xz dm; &nbsp; "
         "I<sub>yz</sub> = ∫yz dm")
    story.append(p(
        "<b>Parallel axis theorem.</b> If <b>I</b><sub>cg</sub> is the "
        "inertia about the centre of mass, the inertia about a point "
        "displaced by <b>d</b> from the CG is"))
    math("<b>I</b><sub>P</sub> = <b>I</b><sub>cg</sub> + m (|<b>d</b>|² "
         "<b>1</b> − <b>d</b>⊗<b>d</b>)")
    story.append(p(
        "<font face='Courier'>FGMassBalance</font> applies this every tick "
        "to add each pointmass's inertia contribution to the empty-weight "
        "tensor."))
    story.append(p(
        "<b>Principal axes.</b> Diagonalising <b>I</b> (which is real "
        "symmetric, hence orthogonally diagonalisable) gives three "
        "<i>principal moments of inertia</i> along three <i>principal "
        "axes</i>. For aircraft with x-z plane symmetry, "
        "I<sub>xy</sub> = I<sub>yz</sub> = 0 by construction; I<sub>xz</sub> "
        "is non-zero whenever the upper and lower halves of the fuselage "
        "are mass-imbalanced (always)."))

    heading("Tensor transformation under rotation", 1, story)
    story.append(p(
        "Vectors transform as v' = <b>R</b>v. A second-order tensor like the "
        "inertia matrix transforms as"))
    math("<b>I</b>' = <b>R</b> <b>I</b> <b>R</b><sup>T</sup>")
    story.append(p(
        "This is how the structural-frame inertia listed in the XML is "
        "rotated to the body frame at load time, and how the body-frame "
        "inertia is rotated to the stability or wind frames when needed "
        "for stability-derivative analysis."))


# ----------------------------------------------------------------------------
def add_ext_quaternions_deep(story):
    story.append(PageBreak())
    heading("Quaternions — Theory and Practice", 0, story)
    story.append(p(
        "Quaternions are the workhorse rotation representation inside "
        "<font face='Courier'>FGPropagate</font>. Reading JSBSim's "
        "integration loop is far easier if you have a working grip on "
        "the algebra."))

    heading("Definition: H, the quaternion algebra", 1, story)
    story.append(p(
        "Hamilton's quaternions are the four-dimensional real algebra "
        "spanned by 1, i, j, k with multiplication rules"))
    math("i² = j² = k² = ijk = −1, &nbsp; ij = k, &nbsp; jk = i, &nbsp; "
         "ki = j")
    story.append(p(
        "A quaternion is q = q<sub>0</sub> + q<sub>1</sub>i + q<sub>2</sub>j"
        " + q<sub>3</sub>k, often written (q<sub>0</sub>, <b>q</b>) with "
        "q<sub>0</sub> the scalar part and <b>q</b> = "
        "(q<sub>1</sub>,q<sub>2</sub>,q<sub>3</sub>) the vector part."))

    heading("The Hamilton product", 1, story)
    math("p · q = (p<sub>0</sub>q<sub>0</sub> − <b>p</b>·<b>q</b>, &nbsp; "
         "p<sub>0</sub><b>q</b> + q<sub>0</sub><b>p</b> + <b>p</b>×<b>q</b>)")
    story.append(p(
        "This non-commutative product is the heart of quaternion "
        "arithmetic. It is implemented in "
        "<font face='Courier'>FGQuaternion::operator*</font>. "
        "<b>Warning:</b> aerospace software is split between Hamilton "
        "convention (used by JSBSim, ROS, MATLAB Aerospace Toolbox) and "
        "JPL convention (used by JPL/NASA Goddard's spacecraft software, "
        "negating the sign of the cross-product term). Mixing them "
        "swaps left- and right-handed rotations — a frequent bug source."))

    heading("Unit quaternions and rotations", 1, story)
    story.append(p(
        "A unit quaternion (|q| = 1) parameterises a rotation. The "
        "axis-angle correspondence is"))
    math("q = (cos(θ/2), <b><font name='DejaVu'>n̂</font></b> sin(θ/2))")
    story.append(p(
        "for a rotation by angle θ about unit axis <b><font name='DejaVu'>n̂</font></b>. The vector "
        "<b>v</b> rotates as the imaginary part of"))
    math("v' = q v q*")
    story.append(p(
        "where v is the pure quaternion (0, <b>v</b>) and q* = "
        "(q<sub>0</sub>, −<b>q</b>) is the conjugate. Equivalently, the "
        "DCM corresponding to q is"))
    code(
        "       | q0²+q1²-q2²-q3²    2(q1q2 - q0q3)     2(q1q3 + q0q2) |\n"
        "R(q) = | 2(q1q2 + q0q3)    q0²-q1²+q2²-q3²    2(q2q3 - q0q1) |\n"
        "       | 2(q1q3 - q0q2)    2(q2q3 + q0q1)    q0²-q1²-q2²+q3² |")
    story.append(p(
        "Internally <font face='Courier'>FGQuaternion::"
        "GetTransformationMatrix()</font> caches this 9-entry DCM so that "
        "subsequent frame transforms reduce to a matrix-vector multiply."))

    heading("Kinematic equation: <font name='DejaVu'>q̇</font> = ½ q ⊗ ω", 1, story)
    story.append(p(
        "If the body's angular velocity (in body frame) is ω, the "
        "kinematic ODE for the rotation from inertial to body is"))
    math("<font name='DejaVu'>q̇</font> = ½ q ⊗ (0, ω<sub>body</sub>)")
    story.append(p(
        "Geometrically: at every instant the quaternion advances "
        "perpendicular to itself in 4-D, so |q| is invariant under "
        "<i>exact</i> integration. Numerical schemes lose this "
        "invariance and need either periodic renormalisation or a "
        "structure-preserving integrator."))
    story.append(p(
        "<b>The Buss integrators</b> implement structure-preserving "
        "discrete maps. For constant ω over [t, t+Δt],"))
    math("q(t+Δt) = q(t) · exp(½ Δt ω) = q(t) · "
         "(cos(|ω|Δt/2), <b><font name='DejaVu'>ω̂</font></b> sin(|ω|Δt/2))")
    story.append(p(
        "is exact and preserves unit norm to floating-point precision. "
        "Buss-2 augments this with a correction term from <font name='DejaVu'>ω̇</font>, giving "
        "second-order accuracy for non-constant ω."))

    heading("Quaternions vs. Euler angles vs. DCMs", 1, story)
    table_data = [
        ["Representation", "Parameters", "Singularity", "Cost", "When"],
        ["Euler 3-2-1", "3 (φ, θ, ψ)",
         "θ = ±90° (gimbal lock)",
         "Cheap to display",
         "Cockpit display, output"],
        ["Quaternion",  "4 (q<sub>0</sub>..q<sub>3</sub>)",
         "None",
         "Compact, fast",
         "Integration, storage"],
        ["DCM",
         "9 (orthogonality wastes 6)",
         "None",
         "Drift; need renorm",
         "Frame transforms"],
        ["Rotation vector",
         "3 (θ <b><font name='DejaVu'>n̂</font></b>)",
         "Singular at θ=2π",
         "Minimal",
         "Linearised perturbations"],
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
        "JSBSim's design carries the quaternion as the primary attitude "
        "state (no singularity, four DOF), caches a DCM derived from it "
        "(cheap repeated frame transforms), and offers Euler outputs only "
        "at the property-tree boundary."))


# ----------------------------------------------------------------------------
def add_ext_numerical_integration(story):
    story.append(PageBreak())
    heading("Numerical Integration — Theory", 0, story)
    story.append(p(
        "The properties <font face='Courier'>simulation/integrator/rate/"
        "rotational</font>, <font face='Courier'>position/rotational</font>, "
        "<font face='Courier'>rate/translational</font> and "
        "<font face='Courier'>position/translational</font> choose four "
        "schemes independently. Knowing the underlying numerical theory is "
        "the difference between a stable model at <i>dt</i> = 1/120 s and a "
        "model that blows up when you change <i>dt</i>."))

    heading("Single-step methods", 1, story)
    story.append(p(
        "For an initial-value problem ẏ = f(t, y), y(t<sub>0</sub>) = y<sub>0</sub>:"))
    math("Forward Euler: &nbsp; y<sub>n+1</sub> = y<sub>n</sub> + h f(t<sub>n</sub>, y<sub>n</sub>)")
    story.append(p(
        "Local truncation error O(h²), global error O(h). Conditionally "
        "stable: for the test equation ẏ = λy, |1 + hλ| &lt; 1 is required, "
        "which for real negative λ means h &lt; 2/|λ|."))
    math("Backward Euler: &nbsp; y<sub>n+1</sub> = y<sub>n</sub> + h f(t<sub>n+1</sub>, y<sub>n+1</sub>)")
    story.append(p(
        "Implicit, unconditionally A-stable. Requires a nonlinear solve "
        "each step. Rarely used in real-time aircraft sim because of cost."))
    math("Trapezoidal (Heun, AM2): y<sub>n+1</sub> = y<sub>n</sub> + (h/2)"
         "[f(t<sub>n</sub>, y<sub>n</sub>) + f(t<sub>n+1</sub>, y<sub>n+1</sub>)]")
    story.append(p(
        "Implicit second-order; predictor-corrector form is the usual "
        "explicit version. JSBSim's <font face='Courier'>eTrapezoidal</font> "
        "uses the predictor-corrector with the prior derivative as predictor "
        "— effectively trapezoidal on the previous derivative."))
    math("RK4: &nbsp; k<sub>1</sub> = f(t<sub>n</sub>, y<sub>n</sub>), &nbsp; "
         "k<sub>2</sub> = f(t<sub>n</sub>+h/2, y<sub>n</sub>+h k<sub>1</sub>/2), "
         "...&nbsp; y<sub>n+1</sub> = y<sub>n</sub> + h(k<sub>1</sub>+2k<sub>2</sub>+2k<sub>3</sub>+k<sub>4</sub>)/6")
    story.append(p(
        "Classical Runge-Kutta 4 is the gold standard for simulator work "
        "where 1-step methods are preferred. Fourth-order accurate but "
        "four function evaluations per step — not what JSBSim uses by "
        "default."))

    heading("Multi-step methods: Adams-Bashforth", 1, story)
    story.append(p(
        "JSBSim implements explicit Adams-Bashforth up to order 5. They "
        "use a single function evaluation per step but require startup "
        "values (filled in by lower-order methods or repeated Eulers)."))
    code(
        "AB2:  y_{n+1} = y_n + h*(  3/2 f_n  -  1/2 f_{n-1} )\n"
        "AB3:  y_{n+1} = y_n + h*( 23/12 f_n - 16/12 f_{n-1} + 5/12 f_{n-2} )\n"
        "AB4:  y_{n+1} = y_n + h*( 55/24 f_n - 59/24 f_{n-1} + 37/24 f_{n-2}\n"
        "                          - 9/24 f_{n-3} )\n"
        "AB5:  y_{n+1} = y_n + h*( 1901/720 f_n - 2774/720 f_{n-1}\n"
        "                          + 2616/720 f_{n-2} - 1274/720 f_{n-3}\n"
        "                          + 251/720 f_{n-4} )")
    story.append(p(
        "JSBSim's defaults are AB2 for translational rate, AB3 for "
        "translational position, and rectangular Euler for the quaternion "
        "(later renormalised). For a smooth aircraft trajectory this gives "
        "energy and angular-momentum conservation to within ~10⁻⁶ over "
        "thousand-second runs at <i>dt</i> = 1/120 s."))

    heading("Stability regions and step-size selection", 1, story)
    story.append(p(
        "Each integrator has a <i>region of absolute stability</i> in the "
        "complex λh plane. For aircraft modes with eigenvalues λ on the "
        "order of −2 to +0.05 rad/s (short period, phugoid, Dutch roll), "
        "h &lt; 2/|λ<sub>max</sub>| ≈ 0.6 s suffices for stability. But "
        "aerodynamic forcing introduces fast modes (the bandwidth of FCS "
        "lag filters, gear-strut natural frequencies of 20-50 Hz), pushing "
        "the requirement to h ≲ 1/120 s in practice."))
    story.append(p(
        "<b>Stiffness.</b> When the system has eigenvalues spanning many "
        "decades (slow flight modes plus fast gear/actuator modes), "
        "explicit methods become inefficient — they must use the smallest "
        "time constant. Implicit methods would help; JSBSim instead "
        "decouples the stiff parts (LCP for gear, prefilters for "
        "actuators) so the explicit integration of the slow flight modes "
        "stays stable."))


# ----------------------------------------------------------------------------
def add_ext_newton_euler(story):
    story.append(PageBreak())
    heading("Newton-Euler Rigid Body Dynamics", 0, story)
    story.append(p(
        "Aircraft EOMs are a special case of rigid-body mechanics. This "
        "chapter derives them from scratch and shows how JSBSim implements "
        "each term."))

    heading("Inertial form (Newton's laws)", 1, story)
    math("m <b>a</b><sub>i</sub> = <b>F</b>, &nbsp;&nbsp;&nbsp; "
         "d<b>H</b>/dt = <b>M</b>")
    story.append(p(
        "Linear momentum p = m<b>v</b><sub>i</sub> obeys "
        "ṗ = <b>F</b>. Angular momentum about the centre of mass is "
        "<b>H</b> = <b>I</b><b>ω</b>; its inertial-frame time derivative "
        "equals the applied moment."))

    heading("Body-frame form via the transport theorem", 1, story)
    story.append(p(
        "If a vector <b>q</b> is expressed in a frame rotating with "
        "angular velocity <b>ω</b>, the relation between its inertial "
        "and frame-relative derivatives is"))
    math("(d<b>q</b>/dt)<sub>inertial</sub> = "
         "(d<b>q</b>/dt)<sub>body</sub> + <b>ω</b> × <b>q</b>")
    story.append(p(
        "Apply to v<sub>body</sub> and to <b>H</b>:"))
    math("m(<b><font name='DejaVu'>v̇</font></b><sub>body</sub> + <b>ω</b> × <b>v</b><sub>body</sub>) = "
         "<b>F</b><sub>body</sub>")
    math("<b>I</b><b><font name='DejaVu'>ω̇</font></b> + <b>ω</b> × (<b>I</b><b>ω</b>) = <b>M</b><sub>body</sub>")
    story.append(p(
        "These are <font face='Courier'>FGAccelerations::CalculateUVWdot()"
        "</font> and <font face='Courier'>CalculatePQRdot()</font> in 12 "
        "lines of arithmetic each. The cross-coupling term "
        "<b>ω</b> × (<b>I</b><b>ω</b>) is the source of gyroscopic effects, "
        "including the celebrated tennis-racket theorem."))

    heading("Including planet rotation", 1, story)
    story.append(p(
        "The body frame on a rotating Earth is not strictly inertial. "
        "Writing the inertial acceleration in terms of body and "
        "ECEF-tangent contributions and applying the transport theorem "
        "twice yields"))
    math("<b><font name='DejaVu'>v̇</font></b><sub>body</sub> + (<b>ω</b><sub>b/i</sub>) × <b>v</b><sub>body</sub>"
         " = <b>F</b>/m &minus; T<sub>i→b</sub>(<b>Ω</b><sub>p</sub> × <b>r</b><sub>i</sub>)·…")
    story.append(p(
        "The full inertial form including Coriolis and centrifugal "
        "terms is integrated in the inertial frame; "
        "<font face='Courier'>FGPropagate</font> stores "
        "<font face='Courier'>vInertialPosition</font> and "
        "<font face='Courier'>vInertialVelocity</font> and transforms to "
        "body for output."))

    heading("Aircraft-specific simplifications", 1, story)
    for b in [
        "x-z plane symmetry: I<sub>xy</sub> = I<sub>yz</sub> = 0.",
        "Body-fixed coordinate axes coincide with principal axes only "
        "approximately; I<sub>xz</sub> ≠ 0 because the upper and lower "
        "fuselage halves are mass-asymmetric.",
        "Steady flight: <b><font name='DejaVu'>v̇</font></b><sub>body</sub> = 0, <b><font name='DejaVu'>ω̇</font></b> = 0; "
        "F and M reduce to zero (the trim condition).",
        "Linearisation around a trim point yields the longitudinal "
        "(u, w, q, θ) and lateral-directional (v, p, r, φ, ψ) "
        "decoupled state-space systems used for stability analysis.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_ext_fluid_mechanics(story):
    story.append(PageBreak())
    heading("Fluid Mechanics Foundations", 0, story)
    story.append(p(
        "All aerodynamic coefficients that JSBSim consumes come from "
        "physics ultimately rooted in the Navier-Stokes equations. This "
        "chapter is the bridge from the continuum equations to the "
        "engineering numbers."))

    heading("Conservation laws", 1, story)
    math("Continuity: &nbsp; ∂ρ/∂t + ∇·(ρ<b>V</b>) = 0")
    math("Momentum: &nbsp; ρ(∂<b>V</b>/∂t + <b>V</b>·∇<b>V</b>) = "
         "−∇p + ∇·τ + ρ<b>g</b>")
    math("Energy: &nbsp; ρ(∂e/∂t + <b>V</b>·∇e) = "
         "−p ∇·<b>V</b> + Φ + ∇·(k∇T) + Q̇")
    story.append(p(
        "with the Newtonian viscous stress "
        "τ<sub>ij</sub> = μ(∂u<sub>i</sub>/∂x<sub>j</sub> + "
        "∂u<sub>j</sub>/∂x<sub>i</sub>) − (2/3)μδ<sub>ij</sub>∇·<b>V</b>. "
        "Closed by an equation of state p = ρRT (calorically perfect gas)."))

    heading("Dimensionless numbers", 1, story)
    table_data = [
        ["Number", "Definition", "Physical meaning"],
        ["Reynolds Re",  "ρVL/μ = VL/ν",
         "Inertial / viscous; controls boundary layer"],
        ["Mach M",
         "V/a, &nbsp; a = √(γRT)",
         "Compressibility; M&lt;0.3 incompressible"],
        ["Knudsen Kn",
         "λ/L",
         "Continuum validity; Kn&lt;0.01 OK"],
        ["Prandtl Pr",
         "μc<sub>p</sub>/k",
         "Momentum vs thermal boundary thickness"],
        ["Strouhal St",
         "fL/V",
         "Unsteady-to-convective time-scale ratio"],
        ["Froude Fr",
         "V/√(gL)",
         "Inertial / gravitational (free-surface)"],
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
        "Typical aerospace ranges: Re for a UAV at low altitude is "
        "10⁵-10⁶, a GA aircraft 10⁶-10⁷, a transport 10⁷-10⁸. Mach "
        "ranges from 0.05 (small UAV) to 2.5+ (fighter); transonic "
        "(0.8-1.2) is the most numerically difficult."))

    heading("Boundary layers", 1, story)
    story.append(p(
        "Prandtl (1904) observed that for high Re, viscosity matters only "
        "in a thin layer of thickness δ next to the surface. The boundary "
        "layer equations are a reduced form of NS:"))
    math("∂u/∂x + ∂v/∂y = 0, &nbsp; "
         "u ∂u/∂x + v ∂u/∂y = −(1/ρ)dp/dx + ν ∂²u/∂y², &nbsp; "
         "∂p/∂y ≈ 0")
    story.append(p(
        "Pressure is impressed from the outer inviscid flow. The Blasius "
        "solution for a flat plate at zero pressure gradient gives the "
        "laminar growth law δ ≈ 5.0 x/√Re<sub>x</sub>, local skin "
        "friction C<sub>f</sub> ≈ 0.664/√Re<sub>x</sub>."))
    story.append(p(
        "<b>Turbulent transition</b> on a smooth flat plate at zero "
        "gradient occurs near Re<sub>x</sub> ≈ 5×10⁵ but is highly "
        "sensitive to freestream turbulence, roughness, and pressure "
        "gradient. UAV-scale airfoils at Re &lt; 5×10⁵ often have "
        "laminar separation bubbles that dominate the polar."))
    story.append(p(
        "<b>Turbulent profile</b>: u<sup>+</sup> = (1/κ) ln y<sup>+</sup>"
        " + B in the log layer, with κ ≈ 0.41 and B ≈ 5.0. RANS CFD "
        "should resolve y<sup>+</sup> &lt; 1 at the first cell for "
        "wall-resolved analysis."))

    heading("Separation, stall, and post-stall", 1, story)
    story.append(p(
        "Flow separates when the wall shear vanishes under an adverse "
        "pressure gradient. On an airfoil this occurs at the stall "
        "angle α<sub>stall</sub>, beyond which lift falls and drag "
        "rises. Three stall mechanisms (depending on airfoil thickness):"))
    for b in [
        "<b>Trailing-edge stall</b> (thick airfoils &gt;15% t/c): "
        "separation creeps upstream from the trailing edge; gentle "
        "lift break.",
        "<b>Leading-edge stall</b> (medium 9-15% t/c): a short laminar "
        "separation bubble bursts; sharp lift break.",
        "<b>Thin-airfoil stall</b> (&lt;8% t/c): long bubble grows and "
        "reattaches further aft; lift curve flattens before breaking.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "JSBSim's <font face='Courier'>&lt;hysteresis_limits&gt;</font> "
        "in <font face='Courier'>&lt;aerodynamics&gt;</font> implements "
        "the post-stall reattachment hysteresis explicitly."))


# ----------------------------------------------------------------------------
def add_ext_lift_theory(story):
    story.append(PageBreak())
    heading("Lift Generation Theory", 0, story)

    heading("Bernoulli is not the answer (and equal-transit-time is wrong)", 1, story)
    story.append(p(
        "Bernoulli's equation along a streamline of incompressible "
        "inviscid steady flow is"))
    math("p + ½ρV² + ρgz = const")
    story.append(p(
        "It is a <b>consequence</b> of momentum conservation, not a "
        "cause of lift. The popular &quot;equal transit time&quot; "
        "explanation — that air over the upper surface must traverse it "
        "in the same time as air below — is empirically wrong; smoke-line "
        "experiments show the upper-surface air arrives at the trailing "
        "edge much earlier. The real cause of pressure asymmetry is "
        "<i>circulation</i>, established by the Kutta condition."))

    heading("Kutta-Joukowski: the right answer", 1, story)
    math("L' = ρ<sub>∞</sub> V<sub>∞</sub> Γ")
    story.append(p(
        "For 2-D inviscid incompressible flow around any closed body, "
        "lift per unit span equals density times freestream velocity "
        "times circulation Γ = ∮<b>V</b>·d<b>s</b>. Drag in this "
        "framework is zero (d'Alembert's paradox); viscosity reintroduces "
        "drag and selects Γ uniquely via the Kutta condition (smooth flow "
        "off the sharp trailing edge)."))

    heading("Thin airfoil theory", 1, story)
    story.append(p(
        "For a thin airfoil, the lift-curve slope is the famous result"))
    math("dC<sub>l</sub>/dα = 2π &nbsp;(per radian) &nbsp;≈ 0.110 /deg")
    story.append(p(
        "and the aerodynamic centre (point of zero pitching moment with α) "
        "is at the quarter-chord. Camber shifts the zero-lift angle "
        "α<sub>L=0</sub> but does not change the slope."))

    heading("Finite wings: Prandtl's lifting line", 1, story)
    story.append(p(
        "A finite wing sheds trailing vorticity that induces a downwash, "
        "tilting the local lift vector backwards (induced drag) and "
        "reducing the effective angle of attack. Prandtl's lifting-line "
        "theory replaces the wing by a bound vortex of strength Γ(y) "
        "and a sheet of trailing vortices. The classical results:"))
    math("C<sub>L</sub> = π · AR · A<sub>1</sub>, &nbsp; "
         "C<sub>D,i</sub> = C<sub>L</sub>² / (π · AR · e)")
    story.append(p(
        "with span efficiency e ≤ 1 (e = 1 for elliptic loading, the "
        "minimum-induced-drag distribution). Modern aircraft use winglets "
        "and span loading optimisation to approach e ≈ 0.9-0.95."))
    story.append(p(
        "The finite-wing lift-curve slope:"))
    math("dC<sub>L</sub>/dα = a<sub>0</sub> / (1 + a<sub>0</sub>/(π·AR·e))")
    story.append(p(
        "with a<sub>0</sub> ≈ 2π the 2-D section slope. For AR=8, "
        "e=0.85 this gives dC<sub>L</sub>/dα ≈ 4.9/rad — about 20% "
        "less than the 2π value an infinite wing would have."))

    heading("Compressibility correction", 1, story)
    math("C<sub>L,M</sub> = C<sub>L,inc</sub> / √(1 − M<sub>∞</sub>²) &nbsp;"
         "(Prandtl-Glauert)")
    story.append(p(
        "Valid up to M ≈ 0.7. Beyond, shock formation and the local "
        "transonic problem dominate; M<sub>crit</sub> (where local Mach "
        "first reaches 1) typically occurs at M<sub>∞</sub> ≈ 0.7-0.8 "
        "for transport airfoils."))


# ----------------------------------------------------------------------------
def add_ext_drag_breakdown(story):
    story.append(PageBreak())
    heading("Drag — A Complete Breakdown", 0, story)
    math("C<sub>D</sub> = C<sub>D,f</sub> + C<sub>D,p</sub> + "
         "C<sub>D,i</sub> + C<sub>D,int</sub> + C<sub>D,w</sub>")
    story.append(p(
        "Five additive sources at subsonic speeds. Each is captured by a "
        "different XML function in JSBSim and each comes from a different "
        "physical mechanism."))

    heading("Skin friction (parasitic)", 1, story)
    story.append(p(
        "Turbulent skin friction on a flat plate (ESDU/Schlichting):"))
    math("C<sub>f</sub> ≈ 0.455 / (log<sub>10</sub> Re<sub>L</sub>)<sup>2.58</sup>")
    story.append(p(
        "Modified by a form factor FF for curvature and an interference "
        "factor Q for component junctions. Summed over wetted area, "
        "D<sub>f</sub> = q ∑ C<sub>f,i</sub> FF<sub>i</sub> Q<sub>i</sub> "
        "S<sub>wet,i</sub>."))

    heading("Form (pressure) drag", 1, story)
    story.append(p(
        "Result of boundary-layer thickening and mild separation that "
        "prevents the rear-body pressure from fully recovering its "
        "stagnation value. Together with skin friction, this is the "
        "<i>profile drag</i>. C<sub>D,f</sub> + C<sub>D,p</sub> are "
        "combined into C<sub>D0</sub> for the polar."))

    heading("Induced drag (lift-induced)", 1, story)
    math("C<sub>D,i</sub> = C<sub>L</sub>² / (π · AR · e)")
    story.append(p(
        "Increases quadratically with C<sub>L</sub>. Span efficiency e "
        "is between 0.7 and 0.95 for conventional wings; Oswald's "
        "efficiency e<sub>0</sub> (which absorbs other C<sub>L</sub>² "
        "effects) is used in the standard parabolic polar."))

    heading("Interference drag", 1, story)
    story.append(p(
        "Junctions between components (wing-fuselage, pylon-wing) create "
        "additional vortical and pressure-induced drag. ESDU and Hoerner "
        "give empirical Q factors typically 1.0-1.3."))

    heading("Wave drag", 1, story)
    story.append(p(
        "Above the critical Mach number M<sub>crit</sub>, the flow "
        "accelerates locally to M=1 and a shock forms. Shock-boundary-"
        "layer interaction yields wave drag that grows rapidly past "
        "the drag-divergence Mach number M<sub>DD</sub>:"))
    math("ΔC<sub>D,wave</sub> ≈ 20(M − M<sub>DD</sub>)<sup>4</sup>")
    story.append(p(
        "(Lock's fourth-power rule). Supersonic minimum wave drag is "
        "achieved by Sears-Haack body of revolution (area rule, "
        "Whitcomb)."))

    heading("The parabolic drag polar and L/D max", 1, story)
    math("C<sub>D</sub> = C<sub>D0</sub> + k C<sub>L</sub>², &nbsp; "
         "k = 1/(π·AR·e)")
    story.append(p(
        "Maximum L/D occurs at C<sub>L</sub><sup>*</sup> = √(C<sub>D0</sub>/k)"
        ", C<sub>D</sub><sup>*</sup> = 2 C<sub>D0</sub>:"))
    math("(L/D)<sub>max</sub> = 1 / (2 √(k · C<sub>D0</sub>))")
    story.append(p(
        "Typical values: sailplane 40-60, jet transport 17-22, small UAV "
        "8-14, Wright Flyer 1903 ≈ 8.3 (Anderson)."))


# ----------------------------------------------------------------------------
def add_ext_stability_control(story):
    story.append(PageBreak())
    heading("Stability &amp; Control — Complete Derivative Table", 0, story)

    heading("Sign conventions and definitions", 1, story)
    for b in [
        "<b>Longitudinal static stability</b>: dC<sub>m</sub>/dα &lt; 0. "
        "Equivalent to the CG forward of the neutral point.",
        "<b>Directional ('weathercock') stability</b>: "
        "dC<sub>n</sub>/dβ &gt; 0. Right sideslip yields nose-right "
        "moment, restoring nose to wind.",
        "<b>Lateral ('dihedral effect')</b>: "
        "dC<sub>l</sub>/dβ &lt; 0. Right sideslip yields left rolling "
        "moment, raising the windward wing.",
    ]:
        story.append(bullet(b))

    heading("Complete derivative table", 1, story)
    table_data = [
        ["Force/Moment", "α / <font name='DejaVu'>α̇</font>", "Rate", "Control"],
        ["C<sub>L</sub>",   "C<sub>Lα</sub>, C<sub>L<font name='DejaVu'>α̇</font></sub>",
         "C<sub>Lq</sub>",  "C<sub>Lδe</sub>, C<sub>Lδf</sub>"],
        ["C<sub>D</sub>",   "C<sub>Dα</sub> (≈2k·C<sub>L</sub>·C<sub>Lα</sub>)",
         "—", "C<sub>Dδe</sub>, C<sub>Dδf</sub>, C<sub>Dgear</sub>"],
        ["C<sub>Y</sub>",   "C<sub>Yβ</sub>",
         "C<sub>Yp</sub>, C<sub>Yr</sub>", "C<sub>Yδa</sub>, C<sub>Yδr</sub>"],
        ["C<sub>l</sub> (roll)", "C<sub>lβ</sub>",
         "C<sub>lp</sub>, C<sub>lr</sub>",
         "C<sub>lδa</sub>, C<sub>lδr</sub>"],
        ["C<sub>m</sub> (pitch)", "C<sub>mα</sub>, C<sub>m<font name='DejaVu'>α̇</font></sub>",
         "C<sub>mq</sub>", "C<sub>mδe</sub>"],
        ["C<sub>n</sub> (yaw)",  "C<sub>nβ</sub>",
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
        "Damping derivatives are non-dimensionalised by b/(2V) (lateral) "
        "or <font name='DejaVu'>c̄</font>/(2V) (longitudinal). The <font name='DejaVu'>α̇</font> derivative captures the downwash "
        "lag between wing and tail. C<sub>nδa</sub> is the &quot;adverse "
        "yaw&quot; — a positive aileron command produces yaw away from "
        "the intended turn direction due to differential drag on the "
        "deflected ailerons."))

    heading("Neutral point and static margin", 1, story)
    math("x<sub>NP</sub> = x<sub>AC,wing</sub> − (<font name='DejaVu'>q̄</font>·S<sub>h</sub>/<font name='DejaVu'>q̄</font>·S) · "
         "(C<sub>Lα,h</sub>/C<sub>Lα</sub>) · l<sub>h</sub> / <font name='DejaVu'>c̄</font>")
    story.append(p(
        "Static margin: SM = (x<sub>NP</sub> − x<sub>CG</sub>) / <font name='DejaVu'>c̄</font>. "
        "Civil transports SM ≈ 5-15%; fighters can run negative SM with "
        "active control law (relaxed static stability)."))

    heading("Maneuver point", 1, story)
    story.append(p(
        "The CG location at which dC<sub>m</sub>/dn<sub>z</sub> = 0 in a "
        "steady pull-up. Aft of x<sub>NP</sub> by approximately "
        "ρ S <font name='DejaVu'>c̄</font> C<sub>mq</sub> / (4 m), which moves x<sub>MP</sub> a few "
        "percent of <font name='DejaVu'>c̄</font> behind x<sub>NP</sub> for typical transports."))


# ----------------------------------------------------------------------------
def add_ext_eigenmodes(story):
    story.append(PageBreak())
    heading("Aircraft Eigenmodes &amp; Linearisation", 0, story)

    heading("Linearisation around trim", 1, story)
    story.append(p(
        "Perturbations Δu, Δw, Δq, Δθ about trim with U<sub>0</sub>, Θ<sub>0</sub>:"))
    code(
        "m Δu̇  = X_u Δu + X_w Δw - m g cosΘ_0 Δθ + ΔX_ctrl\n"
        "m Δẇ  = Z_u Δu + Z_w Δw + (m U_0 + Z_q) Δq - m g sinΘ_0 Δθ + ΔZ_ctrl\n"
        "I_y Δq̇ = M_u Δu + M_w Δw + M_w_dot Δẇ + M_q Δq + ΔM_ctrl\n"
        "Δθ̇   = Δq")
    story.append(p(
        "The lateral-directional subsystem is [Δv, Δp, Δr, Δφ] driven "
        "by Y<sub>v</sub>, Y<sub>p</sub>, Y<sub>r</sub>, L<sub>v</sub>, "
        "L<sub>p</sub>, L<sub>r</sub>, N<sub>v</sub>, N<sub>p</sub>, "
        "N<sub>r</sub>. To first order at symmetric trim the two "
        "subsystems decouple."))

    heading("State-space form", 1, story)
    math("ẋ = Ax + Bu, &nbsp; y = Cx + Du")
    story.append(p(
        "Eigenvalues of A give the modes; eigenvectors give the modal "
        "shape (which states participate in each mode). JSBSim's "
        "<font face='Courier'>simulation/do_linearization</font> "
        "extracts A, B, C, D at a trim point and writes them to log4cpp "
        "output. The Python module exposes the same via "
        "<font face='Courier'>jsbsim.utils.linearize</font>."))

    heading("Longitudinal modes", 1, story)
    story.append(p(
        "<b>Short period</b> — fast pitch oscillation, primarily Δw and "
        "Δq motion, lightly affected by Δu. Heavily damped (ζ ≈ 0.3-0.7), "
        "ω<sub>n</sub> typically 1-5 rad/s for transports, 5-15 rad/s for "
        "fighters."))
    math("ω<sub>n,sp</sub>² ≈ Z<sub>α</sub>M<sub>q</sub>/V<sub>0</sub> − M<sub>α</sub>")
    math("2ζ<sub>sp</sub>ω<sub>n,sp</sub> ≈ −(M<sub>q</sub> + M<sub><font name='DejaVu'>α̇</font></sub> + Z<sub>α</sub>/V<sub>0</sub>)")
    story.append(p(
        "<b>Phugoid</b> — slow exchange of kinetic and potential energy: "
        "Δu and Δθ oscillate, Δw and Δq nearly zero. Lightly damped "
        "(ζ ≈ 0.05) and slow."))
    math("ω<sub>n,ph</sub> ≈ √2 · g / V<sub>0</sub> &nbsp;(Lanchester)")
    math("ζ<sub>ph</sub> ≈ (1/√2) · (C<sub>D</sub>/C<sub>L</sub>)")
    story.append(p(
        "For an airliner at V<sub>0</sub> = 250 m/s, ω<sub>ph</sub> ≈ "
        "0.055 rad/s — period ≈ 115 s. L/D = 17 gives ζ<sub>ph</sub> ≈ "
        "0.041."))

    heading("Lateral-directional modes", 1, story)
    story.append(p(
        "<b>Roll mode</b> — first-order, heavily damped exponential decay "
        "of roll rate:"))
    math("τ<sub>roll</sub> ≈ −I<sub>x</sub> / (<font name='DejaVu'>q̄</font>·S·b·C<sub>lp</sub>·b/(2V))")
    story.append(p(
        "Typical τ<sub>roll</sub> = 0.3-1.5 s. Felt by the pilot as the "
        "&quot;rate response.&quot;"))
    story.append(p(
        "<b>Spiral mode</b> — first-order, very slow, often slightly "
        "unstable. Eigenvalue near zero. Determined by the ratio of "
        "dihedral effect to weathercock stability; "
        "stability requires"))
    math("C<sub>lβ</sub> · C<sub>nr</sub> &gt; C<sub>nβ</sub> · C<sub>lr</sub>")
    story.append(p(
        "<b>Dutch roll</b> — coupled yaw-roll oscillation; the aircraft "
        "&quot;wags its tail&quot; while rocking its wings 90° out of "
        "phase. Moderately damped (ζ ≈ 0.05-0.3), ω<sub>n</sub> ≈ 0.5-3 "
        "rad/s for transports."))
    math("ω<sub>n,DR</sub>² ≈ (<font name='DejaVu'>q̄</font>·S·b/I<sub>z</sub>) C<sub>nβ</sub>")
    math("2 ζ<sub>DR</sub> ω<sub>n,DR</sub> ≈ −(<font name='DejaVu'>q̄</font>·S·b²/(2V·I<sub>z</sub>)) "
         "C<sub>nr</sub>")
    story.append(p(
        "Dutch roll requires a yaw damper on transport aircraft; the "
        "natural mode is typically too lightly damped for pilot comfort. "
        "JSBSim's FCS handles this with a scheduled-gain yaw-damper."))


# ----------------------------------------------------------------------------
def add_ext_airfoil_aerodynamics(story):
    story.append(PageBreak())
    heading("Airfoil Aerodynamics", 0, story)

    heading("The NACA airfoil family", 1, story)
    story.append(p(
        "<b>4-digit</b> (NACA 2412): max camber 2% chord, position of "
        "max camber 0.4c, max thickness 12%."))
    story.append(p(
        "<b>5-digit</b> (NACA 23012): design C<sub>L</sub> = 0.3, position "
        "of max camber 0.15c, max thickness 12%."))
    story.append(p(
        "<b>6-digit</b> (NACA 64<sub>2</sub>-415, &quot;laminar&quot;): "
        "min-pressure position at 0.4c, half-width of low-drag CL bucket "
        "= 0.2, design C<sub>L</sub> = 0.4, thickness 15%."))

    heading("Typical performance", 1, story)
    table_data = [
        ["Airfoil",  "C<sub>L,max</sub>", "α<sub>stall</sub>",
         "C<sub>d,min</sub>", "C<sub>m,ac</sub>"],
        ["NACA 0012",   "1.45 (Re 3×10⁶)", "14°", "0.0060", "0.000"],
        ["NACA 2412",   "1.55",             "15°", "0.0065", "−0.045"],
        ["NACA 23012",  "1.70",             "18°", "0.0070", "−0.014"],
        ["NACA 65-415", "1.50",             "16°", "0.0045", "−0.075"],
        ["Selig S1223 (low-Re)", "2.20 (Re 2×10⁵)", "10°",
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

    heading("Reynolds number effects on UAVs", 1, story)
    story.append(p(
        "Below Re ≈ 5×10⁵ laminar separation bubbles dominate, raising "
        "C<sub>d,min</sub> and lowering C<sub>L,max</sub>. UAVs at Re ≈ "
        "10⁵-3×10⁵ need specialised low-Re airfoils: Eppler 387, SD7037, "
        "Selig S1223. JSBSim aero tables for UAVs should be specific to "
        "the operational Re — do not extrapolate from wind-tunnel Re 10⁶ "
        "to flight Re 10⁵."))

    heading("Critical Mach number", 1, story)
    math("C<sub>p</sub><sup>*</sup> = (2/γM<sub>∞</sub>²)[((1 + (γ−1)/2·M<sub>∞</sub>²)/(1 + (γ−1)/2))<sup>γ/(γ−1)</sup> − 1]")
    story.append(p(
        "M<sub>crit</sub> is solved simultaneously with the Prandtl-Glauert "
        "Cp = Cp,min,inc / √(1 − M<sub>crit</sub>²). Drag divergence "
        "M<sub>DD</sub> &gt; M<sub>crit</sub>, defined where dC<sub>D</sub>"
        "/dM = 0.1."))
    story.append(p(
        "<b>Supercritical airfoils</b> (Whitcomb's NASA SC(2) series) "
        "raise M<sub>DD</sub> by 0.05-0.10 at the same thickness, or "
        "allow 30-60% greater thickness at the same M<sub>DD</sub> — "
        "enabling structurally lighter wings."))


# ----------------------------------------------------------------------------
def add_ext_cfd_methods(story):
    story.append(PageBreak())
    heading("CFD Methods — Theory and Practice", 0, story)

    heading("Panel methods", 1, story)
    story.append(p(
        "For inviscid incompressible flow (or P-G-corrected) over "
        "arbitrary shapes, Hess-Smith distributes sources and doublets "
        "on body panels and enforces flow tangency. O(N²) in panel "
        "count. Doublet-lattice (Albano-Rodden 1969) extends to "
        "unsteady oscillatory flow and is the workhorse of flutter "
        "analysis."))

    heading("Vortex lattice", 1, story)
    story.append(p(
        "Wings represented by horseshoe vortices on a flat camber "
        "surface, trailing legs aligned with freestream. Computes "
        "C<sub>L</sub>, induced drag, span-loading. Mark Drela's AVL "
        "is the canonical open-source tool for preliminary design and "
        "stability-derivative estimation. Limitations: no thickness, no "
        "viscous effects, no compressibility beyond P-G, no separation."))

    heading("RANS turbulence models", 1, story)
    for b in [
        "<b>Spalart-Allmaras (1992)</b>: one transport equation for "
        "modified eddy viscosity ν̃. Widely used in external aerodynamics. "
        "Tolerates higher y<sup>+</sup> via near-wall linearisation.",
        "<b>k-ε</b>: two equations. Poor at adverse pressure gradients "
        "and separation; usually requires wall functions.",
        "<b>k-ω SST (Menter, 1994)</b>: blends k-ω near walls with k-ε "
        "in the far-field via F1 blending. Best general-purpose RANS "
        "model for separated/adverse-pressure flows. Industry default "
        "for high-lift, wings, rotorcraft.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Wall resolution: y<sup>+</sup> &lt; 1 on first cell, 30-40 "
        "cells across boundary layer, wall-normal growth rate &lt; 1.2."))

    heading("LES, DES, hybrid", 1, story)
    story.append(p(
        "<b>LES</b> resolves eddies down to grid scale; y<sup>+</sup> ≈ "
        "1 in all three directions, Δx<sup>+</sup>, Δz<sup>+</sup> ~ 50. "
        "Cost ~ Re<sup>2.5</sup> for wall-resolved LES — prohibitive at "
        "flight Re."))
    story.append(p(
        "<b>DES/DDES/IDDES</b> (Spalart 1997): RANS in attached boundary "
        "layers, LES in separated regions. Affordable for massively "
        "separated flows (high α, post-stall, store separation)."))

    heading("Validation cases", 1, story)
    story.append(p(
        "AGARD AR-303 and AR-138, NASA Turbulence Modeling Resource "
        "(turbmodels.larc.nasa.gov), DLR-F6/F11 high-lift, NASA Common "
        "Research Model (CRM), HiLiftPW workshops, AIAA Drag Prediction "
        "Workshops 1-7. CFL3D, FUN3D and OVERFLOW are the reference codes."))


# ----------------------------------------------------------------------------
def add_ext_forced_oscillation(story):
    story.append(PageBreak())
    heading("Forced Oscillation and Damping Derivatives", 0, story)

    heading("Setup", 1, story)
    story.append(p(
        "Impose a sinusoidal motion at frequency ω. For pitch:"))
    math("α(t) = α<sub>0</sub> + Δα sin(ωt), &nbsp; q(t) = ωΔα cos(ωt)")
    story.append(p(
        "Time-accurate CFD runs ~5 cycles to dissipate startup transients; "
        "data from cycles 3-5. Best practice: ≥100 time steps per cycle, "
        "dual time-stepping with 30-50 inner iterations."))

    heading("Reduced frequency", 1, story)
    math("k = ω L<sub>ref</sub> / (2 V<sub>∞</sub>)")
    story.append(p(
        "Ratio of unsteady to convective time scales. k → 0 is "
        "quasi-steady (static derivatives only); k &gt; 0.05 includes "
        "circulation lag and added-mass effects. Typical CFD forced "
        "oscillation: k = 0.02-0.10."))

    heading("Derivative extraction", 1, story)
    math("C<sub>m</sub>(t) ≈ C<sub>m0</sub> + C<sub>mα</sub>Δα + "
         "(C<sub>mq</sub> + C<sub>m<font name='DejaVu'>α̇</font></sub>)(<font name='DejaVu'>c̄</font>/(2V))Δα·ω·cos(ωt)/sin(ωt)·... ")
    story.append(p(
        "Fourier integration over one cycle:"))
    code(
        "C_mα   ≈ (1/(π Δα)) ∫₀^(2π/ω) C_m(t) sin(ωt) dt\n"
        "C_mq + C_mα̇ ≈ (1/(π k Δα)) ∫₀^(2π/ω) C_m(t) cos(ωt) dt")
    story.append(p(
        "The pure damping C<sub>mq</sub> and <font name='DejaVu'>α̇</font>-lag C<sub>m<font name='DejaVu'>α̇</font></sub> "
        "cannot be separated from a single pitch-only oscillation; one "
        "needs a plunge (varying α at fixed q) or a combined schedule. "
        "Many handbooks publish the sum (C<sub>mq</sub> + C<sub>m<font name='DejaVu'>α̇</font></sub>) "
        "and split it roughly 70/30."))


# ----------------------------------------------------------------------------
def add_ext_geodesy_wgs84(story):
    story.append(PageBreak())
    heading("Geodesy and the WGS-84 Ellipsoid", 0, story)
    story.append(p(
        "JSBSim integrates its equations of motion in the inertial frame "
        "and transforms to the WGS-84 ellipsoid for output. This chapter "
        "is the reference for the geodetic constants and conventions."))

    heading("WGS-84 defining constants", 1, story)
    table_data = [
        ["Symbol", "Value", "Description"],
        ["a", "6 378 137.0 m (exact)", "Semi-major axis"],
        ["1/f", "298.257 223 563 (exact)", "Reciprocal flattening"],
        ["GM",  "3.986 004 418 × 10¹⁴ m³/s²", "Earth gravitational param."],
        ["ω",   "7.292 115 × 10⁻⁵ rad/s", "Earth rotation rate"],
        ["b",   "6 356 752.3142 m", "Semi-minor axis, b = a(1−f)"],
        ["e²",  "6.694 379 990 14 × 10⁻³",
         "First eccentricity² = 2f − f²"],
        ["e'²", "6.739 496 742 28 × 10⁻³",
         "Second eccentricity² = e²/(1−e²)"],
        ["J2",  "1.082 626 7 × 10⁻³",
         "Second zonal harmonic (un-normalised)"],
        ["R<sub>V</sub>", "6 371 000.79 m", "Mean (volumetric) radius"],
        ["γ<sub>e</sub>", "9.780 325 m/s²", "Normal gravity at equator"],
        ["γ<sub>p</sub>", "9.832 185 m/s²", "Normal gravity at pole"],
        ["g<sub>0</sub>", "9.806 65 m/s²", "Standard gravity (definitional)"],
        ["Sidereal day", "86 164.0905 s", "Length of sidereal day"],
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

    heading("Geodetic vs geocentric latitude", 1, story)
    math("tan(φ<sub>c</sub>) = (1 − e²) tan(φ<sub>g</sub>)")
    story.append(p(
        "The two differ by up to 11.55 arc-min ≈ 0.19° near φ = 45° — "
        "equivalent to 21.4 km of north-south distance on Earth's surface. "
        "Aviation always uses geodetic latitude (GPS, charts, autopilots). "
        "JSBSim internal calculations sometimes use geocentric; output is "
        "in both."))

    heading("Altitude definitions", 1, story)
    for b in [
        "<b>Ellipsoidal (geodetic) height h</b> — signed distance to "
        "WGS-84 ellipsoid along the ellipsoid normal. Native GPS output.",
        "<b>Orthometric height H</b> — height above the geoid (mean sea "
        "level equipotential). Water flows from high H to low H. Charts "
        "use this.",
        "<b>Geoid undulation N</b> — h = H + N. Globally N ∈ [−105 m, "
        "+85 m] versus WGS-84. EGM96/EGM2008 give global geoid models.",
        "<b>Pressure altitude</b> — altitude in ISA at which the measured "
        "pressure occurs. Altimeter with 29.92 inHg setting.",
        "<b>Density altitude</b> — same concept for density. Predicts "
        "aircraft and engine performance.",
        "<b>Geopotential altitude</b> — H<sub>geopot</sub> = R·H<sub>geom</sub>/(R + H<sub>geom</sub>). "
        "Used by the standard atmosphere model so that the hydrostatic "
        "equation has constant g.",
    ]:
        story.append(bullet(b))

    heading("Radii of curvature", 1, story)
    math("M(φ) = a(1−e²) / (1 − e² sin²φ)<sup>3/2</sup> &nbsp;(meridian)")
    math("N(φ) = a / √(1 − e² sin²φ) &nbsp;(prime vertical)")
    story.append(p(
        "At equator M = a(1−e²), N = a; at the pole M = N = a/√(1−e²) "
        "≈ 6 399 593.6 m. Distance per radian: north-south M; east-west "
        "N cos φ. One arc-minute of latitude at the equator equals "
        "1843 m; one nautical mile is exactly 1852 m by definition."))


# ----------------------------------------------------------------------------
def add_ext_coord_transforms(story):
    story.append(PageBreak())
    heading("Coordinate Transformations in Detail", 0, story)

    heading("Geodetic → ECEF (closed form)", 1, story)
    code(
        "x = (N + h) cos(φ) cos(λ)\n"
        "y = (N + h) cos(φ) sin(λ)\n"
        "z = (N (1 - e²) + h) sin(φ)\n"
        "where N(φ) = a / sqrt(1 - e² sin²φ)")
    story.append(p(
        "Three multiplications and a square root. JSBSim uses this every "
        "tick to map the integrated inertial position to a geodetic "
        "(lat, lon, alt) triple for output."))

    heading("ECEF → Geodetic (Bowring iteration)", 1, story)
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
        "Convergence in 3 iterations to 10⁻¹¹ rad ≈ 0.06 mm anywhere on "
        "Earth. Heikkinen (1982) and Olson (1996) give iteration-free "
        "closed-form alternatives; Vermeille (2011) is accurate to "
        "nanometres within 5000 km of the ellipsoid."))

    heading("ECEF → ECI rotation", 1, story)
    code(
        "| x_ECI |   |  cos(θ)  -sin(θ)  0 |   | x_ECEF |\n"
        "| y_ECI | = |  sin(θ)   cos(θ)  0 | * | y_ECEF |\n"
        "| z_ECI |   |    0        0     1 |   | z_ECEF |")
    story.append(p(
        "θ is the Greenwich Mean Sidereal Time (GMST). For precision work "
        "you augment with precession P, nutation N, polar motion W: "
        "GCRF = P<sup>T</sup>N<sup>T</sup>R<sup>T</sup>W<sup>T</sup> · "
        "ITRF. For aircraft sim the bare rotation is enough."))

    heading("ECEF → NED at (φ₀, λ₀)", 1, story)
    code(
        "                | -sin(φ₀)cos(λ₀)  -sin(φ₀)sin(λ₀)   cos(φ₀) |\n"
        "R_NED^ECEF =    | -sin(λ₀)           cos(λ₀)            0     |\n"
        "                | -cos(φ₀)cos(λ₀)  -cos(φ₀)sin(λ₀)  -sin(φ₀) |")
    story.append(p(
        "ENU follows by swapping the first two rows and negating the "
        "third. JSBSim caches both NED-from-ECEF and ECEF-from-NED "
        "matrices each tick."))

    heading("NED → Body (3-2-1 Tait-Bryan)", 1, story)
    math("R<sup>b</sup><sub>n</sub> = R<sub>x</sub>(φ) R<sub>y</sub>(θ) R<sub>z</sub>(ψ)")
    story.append(p(
        "Multiplied out:"))
    code(
        "          | cθcψ                    cθsψ                   -sθ    |\n"
        "R_b_n =   | sφsθcψ - cφsψ           sφsθsψ + cφcψ          sφcθ  |\n"
        "          | cφsθcψ + sφsψ           cφsθsψ - sφcψ          cφcθ  |")
    story.append(p(
        "Singularity at θ = ±90° is the canonical gimbal lock — which is "
        "why JSBSim integrates the quaternion form and only exports "
        "Euler angles."))


# ----------------------------------------------------------------------------
def add_ext_earth_gravity(story):
    story.append(PageBreak())
    heading("Earth Rotation and Gravity", 0, story)

    heading("Earth rotation rate and fictitious forces", 1, story)
    story.append(p(
        "The rotating ECEF frame is non-inertial. Newton's law acquires "
        "Coriolis and centrifugal terms:"))
    math("<b>a</b><sub>inertial</sub> = <b>a</b><sub>ECEF</sub> + 2 <b>Ω</b> × <b>v</b> + <b>Ω</b> × (<b>Ω</b> × <b>r</b>)")
    story.append(p(
        "At Mach 0.8 cruise (~250 m/s) at mid-latitudes, Coriolis is "
        "~0.036 m/s² (0.0037 g) — small but accumulates to substantial "
        "heading and track errors over flight-hour timescales if "
        "neglected. The centrifugal term at the equator is ~0.034 m/s² "
        "outward, which is precisely why measured surface gravity at the "
        "equator (9.780 m/s²) is less than the pure gravitational pull "
        "(9.814 m/s²). Centrifugal is conventionally folded into the "
        "gravity model so only Coriolis remains explicit in the EOMs."))

    heading("Spherical gravity (simple)", 1, story)
    math("g(r) = GM / r² &nbsp;(outward radial direction)")
    story.append(p(
        "At sea level r = 6 378 km, g ≈ 9.798 m/s². Adequate for many "
        "aircraft simulations; JSBSim default."))

    heading("Somigliana normal gravity (WGS-84 surface)", 1, story)
    math("γ(φ) = γ<sub>e</sub> (1 + k sin²φ) / √(1 − e² sin²φ)")
    story.append(p(
        "with γ<sub>e</sub> = 9.7803254 m/s² and "
        "k = (b γ<sub>p</sub> − a γ<sub>e</sub>)/(a γ<sub>e</sub>) "
        "≈ 0.001932. Free-air correction for altitude:"))
    math("γ(φ, h) ≈ γ(φ)[1 − (2/a)(1 + f + m − 2f sin²φ) h + (3/a²) h²]")
    story.append(p(
        "with m = ω<sub>E</sub>² a² b / GM ≈ 3.45 × 10⁻³."))

    heading("J2 gravity perturbation", 1, story)
    story.append(p(
        "The leading-order departure of the Earth's gravity field from a "
        "spherical mass:"))
    math("a<sub>J2</sub> = −(3 J2 GM a²)/(2 r⁴) × [(1−5sin²φ<sub>c</sub>)x̂, "
         "(1−5sin²φ<sub>c</sub>)ŷ, (3−5sin²φ<sub>c</sub>)ẑ]")
    story.append(p(
        "For aircraft below 20 km altitude on flights under 24 hours, "
        "Somigliana-with-altitude suffices. For launch vehicles, missiles "
        "and orbital reentry, J2 (and often J3, J4) are required."))


# ----------------------------------------------------------------------------
def add_ext_magnetic_navigation(story):
    story.append(PageBreak())
    heading("Magnetic Field and Navigation", 0, story)

    heading("The World Magnetic Model (WMM 2025)", 1, story)
    story.append(p(
        "The WMM is the joint NCEI / British Geological Survey / NGA "
        "standard for the geomagnetic main field. The current model is "
        "WMM2025, valid through 31 December 2029. The field is a "
        "spherical-harmonic series (degree/order 12 standard, 133 for the "
        "high-resolution WMMHR2025), each Gauss coefficient varying "
        "linearly in time over the model epoch."))
    story.append(p(
        "At a given (φ, λ, h, t) the model outputs the three geocentric "
        "components (X north, Y east, Z down), from which:"))
    for b in [
        "Total intensity F = √(X² + Y² + Z²)",
        "Horizontal intensity H = √(X² + Y²)",
        "Magnetic declination D = atan2(Y, X) — angle from true north to "
        "magnetic north, positive east",
        "Magnetic inclination (dip) I = atan2(Z, H) — angle from horizontal",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Convert true to magnetic heading: ψ<sub>mag</sub> = ψ<sub>true</sub> − D. "
        "Magnetic compasses also need a deviation card (airframe-specific) "
        "and exhibit northerly-turning errors due to dip."))

    heading("GPS in WGS-84", 1, story)
    story.append(p(
        "The GPS constellation broadcasts ephemerides in WGS-84 ECEF and "
        "satellite times in GPST. A receiver solves the four-unknown "
        "system (3 ECEF coords + clock bias) from pseudorange equations"))
    math("ρ<sub>i</sub> = |<b>r</b><sub>sat,i</sub> − <b>r</b><sub>rx</sub>| + c·Δt<sub>rx</sub> + ε<sub>i</sub>")
    story.append(p(
        "via weighted least squares or an extended Kalman filter. The "
        "ECEF solution is then converted to (φ, λ, h) by the closed-form "
        "or iterative algorithms of the previous chapter. Modern "
        "INS-aided GNSS systems achieve sub-meter accuracy in dynamic "
        "operation."))

    heading("Haversine great-circle distance", 1, story)
    code(
        "a = sin²((φ₂-φ₁)/2) + cos(φ₁) cos(φ₂) sin²((λ₂-λ₁)/2)\n"
        "c = 2 atan2(√a, √(1-a))\n"
        "d = R_E · c")
    story.append(p(
        "with R<sub>E</sub> ≈ 6 371 km. Initial bearing:"))
    code(
        "θ_i = atan2(sin(Δλ) cos(φ₂), cos(φ₁) sin(φ₂) - sin(φ₁) cos(φ₂) cos(Δλ))")
    story.append(p(
        "Errors below 0.3% versus the oblate Earth. Vincenty's iterative "
        "method (or Karney's variant) gives geodesic distances to "
        "submillimetre on WGS-84."))


# ----------------------------------------------------------------------------
def add_ext_time_systems(story):
    story.append(PageBreak())
    heading("Time Systems in Aerospace", 0, story)
    story.append(p(
        "Five clocks matter. Getting them straight is the difference "
        "between a sim that ties cleanly to GPS, ephemerides, and "
        "magnetic-field models — and one that doesn't."))

    table_data = [
        ["Scale", "Definition", "Use"],
        ["TAI", "International Atomic Time. Uniform SI seconds.",
            "Foundation; no discontinuities."],
        ["UTC", "= TAI − N leap seconds; |UT1−UTC|&lt;0.9 s.",
            "Civil time. UTC = TAI − 37 s (2026)."],
        ["UT1", "Earth-rotation time (mean sun on meridian → noon).",
            "Drifts; broadcast as DUT1 = UT1−UTC."],
        ["GPST", "Atomic; started at UTC on 1980-01-06.",
            "GPS satellite time; = TAI − 19 s."],
        ["TT",   "= TAI + 32.184 s (definitional).",
            "Solar-system ephemerides."],
        ["GMST", "Greenwich Mean Sidereal Time.",
            "ECEF↔ECI rotation; +3min 56.6 s/day vs UTC."],
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
        "GMST formula (approximate, degrees):"))
    code(
        "GMST = 280.46061837 + 360.98564736629·d + 0.000387933·T² − T³/38710000\n"
        "with d = days from J2000.0, T = centuries from J2000.0.")


# ----------------------------------------------------------------------------
def add_ext_atmosphere_deep(story):
    story.append(PageBreak())
    heading("The Standard Atmosphere in Depth", 0, story)
    story.append(p(
        "JSBSim's <font face='Courier'>FGStandardAtmosphere</font> "
        "implements the 1976 US Standard Atmosphere (NASA-TM-X-74335). "
        "ICAO Standard Atmosphere is identical to 32 km."))

    heading("Sea-level reference", 1, story)
    table_data = [
        ["Quantity", "Symbol", "Value"],
        ["Temperature",      "T<sub>0</sub>",   "288.15 K (15°C)"],
        ["Pressure",         "p<sub>0</sub>",   "101 325 Pa"],
        ["Density",          "ρ<sub>0</sub>",   "1.225 kg/m³"],
        ["Speed of sound",   "a<sub>0</sub>",   "340.294 m/s"],
        ["Dynamic viscosity","μ<sub>0</sub>",  "1.7894 × 10⁻⁵ Pa·s"],
        ["Specific gas const","R",              "287.058 J/(kg·K)"],
        ["Ratio of specific heats","γ",         "1.40"],
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

    heading("Layer structure (0 to 86 km)", 1, story)
    table_data = [
        ["Layer", "Base alt (km)", "Top alt (km)", "Lapse rate L (K/km)"],
        ["Troposphere",   "0",  "11",  "−6.5"],
        ["Tropopause",    "11", "20",  "0"],
        ["Stratosphere 1","20", "32",  "+1.0"],
        ["Stratosphere 2","32", "47",  "+2.8"],
        ["Stratopause",   "47", "51",  "0"],
        ["Mesosphere 1",  "51", "71",  "−2.8"],
        ["Mesosphere 2",  "71", "84.852", "−2.0"],
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
        "Within each non-isothermal layer, the hydrostatic equation"))
    math("dp/dh = −ρ g, &nbsp; p = ρRT, &nbsp; T(h) = T<sub>b</sub> + L(h − h<sub>b</sub>)")
    story.append(p("integrates to"))
    math("p(h) = p<sub>b</sub> · [T<sub>b</sub>/(T<sub>b</sub> + L(h−h<sub>b</sub>))]"
         "<sup>g<sub>0</sub>/(R·L)</sup>")
    story.append(p(
        "For isothermal layers (L = 0), the solution is exponential:"))
    math("p(h) = p<sub>b</sub> · exp[ −g<sub>0</sub>(h − h<sub>b</sub>)/(R T<sub>b</sub>) ]")

    heading("Derived quantities", 1, story)
    math("a = √(γRT) &nbsp;(speed of sound)")
    math("M = V/a &nbsp;(Mach number)")
    math("μ(T) = μ<sub>ref</sub>(T/T<sub>ref</sub>)<sup>1.5</sup>(T<sub>ref</sub> + S)/(T + S)")
    story.append(p(
        "(Sutherland's law, with S = 110.4 K for air). Reynolds number "
        "Re = ρVL/μ. Total/stagnation pressure and temperature:"))
    math("p<sub>t</sub> = p(1 + (γ−1)/2 · M²)<sup>γ/(γ−1)</sup>")
    math("T<sub>t</sub> = T(1 + (γ−1)/2 · M²)")


# ----------------------------------------------------------------------------
def add_ext_wind_turbulence(story):
    story.append(PageBreak())
    heading("Wind, Turbulence, and Gusts", 0, story)

    heading("Wind profile near the surface", 1, story)
    math("u(z) = (u<sub>*</sub>/κ) ln(z/z<sub>0</sub>) &nbsp;(log law, κ ≈ 0.41)")
    math("u(h) = u<sub>ref</sub> (h/h<sub>ref</sub>)<sup>α</sup> &nbsp;(power law, α ≈ 1/7 over open terrain)")

    heading("Discrete gusts (MIL-F-8785C 1-cosine)", 1, story)
    math("V<sub>gust</sub>(t) = (V<sub>m</sub>/2) (1 − cos(πt/T<sub>m</sub>))")
    story.append(p(
        "Used for handling-qualities certification. T<sub>m</sub> ranges "
        "from 0.5 s (small UAV) to several seconds (transports); "
        "V<sub>m</sub> 5-15 m/s typical."))

    heading("Continuous turbulence — Dryden PSD", 1, story)
    math("Φ<sub>u</sub>(ω) = σ<sub>u</sub>² · (2L<sub>u</sub>/V) / (1 + (L<sub>u</sub>ω/V)²)")
    math("Φ<sub>v</sub>(ω) = σ<sub>v</sub>² · (L<sub>v</sub>/V) · "
         "(1 + 3(L<sub>v</sub>ω/V)²) / (1 + (L<sub>v</sub>ω/V)²)²")
    math("Φ<sub>w</sub>(ω) = σ<sub>w</sub>² · (L<sub>w</sub>/V) · "
         "(1 + 3(L<sub>w</sub>ω/V)²) / (1 + (L<sub>w</sub>ω/V)²)²")
    story.append(p(
        "Scale lengths L<sub>u,v,w</sub> and intensities σ<sub>u,v,w</sub> "
        "are specified by altitude band in MIL-F-8785C / MIL-HDBK-1797. "
        "Light/moderate/severe intensity probabilities decrease with "
        "altitude; turbulence above the tropopause is rare."))
    story.append(p(
        "<b>Von Kármán PSD</b> is an alternative (more accurate at high "
        "frequencies) commonly used in flutter analysis."))

    heading("Microburst (Vicroy)", 1, story)
    story.append(p(
        "A microburst is modelled as a three-component flow field: "
        "horizontal outflow + downdraft + vortex ring. Vicroy's analytical "
        "model parameterises the radial outflow profile by core radius, "
        "altitude of the vortex ring, and outflow peak velocity. Used for "
        "wind-shear-recovery training scenarios."))


# ----------------------------------------------------------------------------
def add_ext_propulsion_theory(story):
    story.append(PageBreak())
    heading("Propulsion Theory", 0, story)

    heading("Piston engines — Otto cycle", 1, story)
    story.append(p(
        "Four-stroke engine: intake, compression (adiabatic), combustion "
        "(constant volume), expansion (adiabatic), exhaust. Ideal Otto "
        "efficiency η = 1 − (1/r)<sup>γ−1</sup> with compression ratio r. "
        "BSFC typical 0.4-0.5 lb/(hp·hr) for normally aspirated avgas "
        "engines."))
    story.append(p(
        "Performance scales with manifold absolute pressure (MAP), "
        "RPM, and mixture. <font face='Courier'>FGPiston</font> uses a "
        "parabolic power-vs-MAP relation and linear scaling with throttle/"
        "RPM. Altitude derating accounts for ambient density decrease "
        "(unless supercharged or turbocharged)."))

    heading("Turbine — Brayton cycle", 1, story)
    story.append(p(
        "Continuous-flow cycle: compression, combustion (≈constant "
        "pressure), expansion. Ideal Brayton efficiency η = 1 − (1/π)"
        "<sup>(γ−1)/γ</sup> with pressure ratio π. Modern turbofans π ≈ "
        "30-50, TSFC 0.30-0.50 lb/(lbf·hr) cruise, 1.5-2.5 with AB on."))
    story.append(p(
        "<b>Bypass ratio</b>: pure jet ≈ 0; military low-bypass ≈ 0.3; "
        "commercial high-bypass ≈ 10-12 (GE9X, Trent XWB). High-bypass = "
        "more mass flow at lower velocity = quieter and more efficient at "
        "subsonic speeds."))
    story.append(p(
        "<b>Two-spool architecture</b>: N1 (low-pressure spool, fan) and "
        "N2 (high-pressure spool, compressor + turbine). N1 is the "
        "primary thrust-rating parameter on most commercial engines."))

    heading("Rocket — F = ṁ V<sub>e</sub> + (p<sub>e</sub> − p<sub>a</sub>)A<sub>e</sub>", 1, story)
    math("I<sub>sp</sub> = F / (ṁ · g<sub>0</sub>) &nbsp;(seconds)")
    story.append(p(
        "Specific impulse measures fuel efficiency. Typical values: "
        "solid propellant 250 s, RP-1/LOX 350 s, LH2/LOX 450 s, ion "
        "&gt;3000 s. Tsiolkovsky rocket equation:"))
    math("Δv = I<sub>sp</sub> g<sub>0</sub> ln(m<sub>0</sub>/m<sub>f</sub>)")
    story.append(p(
        "Orbital insertion requires Δv ≈ 9-10 km/s including gravity and "
        "drag losses. Multi-staging is necessary because m<sub>0</sub>/m<sub>f</sub> "
        "is exponential in Δv."))

    heading("Electric motors — BLDC", 1, story)
    story.append(p(
        "Brushless DC motor obeys (per phase):"))
    math("V = K<sub>e</sub>·ω + I·R, &nbsp; τ = K<sub>t</sub>·I, &nbsp; "
         "K<sub>t</sub> = 1/K<sub>v</sub> in SI units")
    story.append(p(
        "with K<sub>v</sub> in rpm/V (hobby convention). Power "
        "P = V·I = ω·τ + I²·R; the second term is resistive loss. "
        "Efficiency η = ω·τ / (V·I) peaks at intermediate loads (~50-70% "
        "rated current)."))
    story.append(p(
        "Battery: LiPo cells nominal 3.7 V (4.2 V max, 3.0 V min); "
        "C-rating limits peak discharge (e.g. 25 C × 5000 mAh = 125 A "
        "max). State-of-charge integrates current over time: "
        "SoC(t) = SoC(0) − ∫I/Q · dt."))


# ----------------------------------------------------------------------------
def add_ext_propeller_rotor(story):
    story.append(PageBreak())
    heading("Propeller and Rotor Theory", 0, story)

    heading("Propeller — momentum + blade element", 1, story)
    story.append(p(
        "Momentum theory (Froude): an ideal disc accelerates the flow "
        "from V to V+2v<sub>i</sub>, producing thrust"))
    math("T = 2 ρ A (V + v<sub>i</sub>) v<sub>i</sub>")
    story.append(p(
        "with v<sub>i</sub> the induced velocity at the disc. Power "
        "P = T (V + v<sub>i</sub>); efficiency η = TV/P → 1 only at zero "
        "v<sub>i</sub> (infinite disc area, the actuator-disc limit)."))
    story.append(p(
        "Blade-element theory analyses each blade element as a 2-D airfoil "
        "with local α and V<sub>resultant</sub>. JSBSim's "
        "<font face='Courier'>FGPropeller</font> uses tabulated C<sub>T</sub>"
        "(J) and C<sub>P</sub>(J) curves where the advance ratio is"))
    math("J = V / (n·D), &nbsp; n in rev/s, D = diameter")
    math("Thrust = C<sub>T</sub>(J) · ρ · n² · D⁴")
    math("Power = C<sub>P</sub>(J) · ρ · n³ · D⁵")
    math("Efficiency η<sub>p</sub> = J · C<sub>T</sub> / C<sub>P</sub>")

    heading("P-factor and prop-induced effects", 1, story)
    for b in [
        "<b>P-factor</b>: at non-zero α the descending blade has a higher "
        "local angle of attack than the ascending blade, producing a "
        "lateral thrust offset that yaws the aircraft.",
        "<b>Slipstream rotation</b>: the prop wash spirals, hitting the "
        "vertical tail asymmetrically and producing a yaw moment.",
        "<b>Gyroscopic precession</b>: a pitching aircraft applies an "
        "input torque about the lateral axis; spinning prop reacts with "
        "a precessional yaw, and vice versa.",
        "<b>Torque reaction</b>: Newton's third law — the engine torquing "
        "the prop one way torques the aircraft the other way. Sense "
        "(clockwise vs counter-clockwise from cockpit) determines which.",
    ]:
        story.append(bullet(b))

    heading("Constant-speed propellers", 1, story)
    story.append(p(
        "A governor adjusts blade pitch to hold a commanded RPM regardless "
        "of throttle setting. JSBSim's <font face='Courier'>&lt;constspeed&gt;1"
        "&lt;/constspeed&gt;</font> in the propeller XML enables this. "
        "Below the governor range, the prop reverts to fixed pitch at "
        "<font face='Courier'>&lt;minpitch&gt;</font>. Beta range (below "
        "flight idle) and reverse (negative pitch) are supported on "
        "turboprops."))

    heading("Helicopter rotor", 1, story)
    story.append(p(
        "A rotor is a propeller that also generates lift. The thrust at "
        "hover (momentum theory):"))
    math("T = 2 ρ A v<sub>i</sub>², &nbsp; v<sub>i</sub> = √(T/(2ρA))")
    story.append(p(
        "<b>Translational lift</b>: in forward flight the inflow becomes "
        "asymmetric; advancing blade sees V + ω·r, retreating sees ω·r − V. "
        "The retreating blade approaches stall at high forward speed — "
        "the helicopter's V<sub>NE</sub> limit."))
    story.append(p(
        "<b>Cyclic pitch</b>: blade pitch varies once per revolution to "
        "tilt the rotor disc, generating forces in any direction. "
        "<b>Collective pitch</b>: all blades change pitch together, "
        "controlling thrust magnitude. JSBSim's "
        "<font face='Courier'>FGRotor</font> implements blade-element + "
        "momentum theory with flapping dynamics; the X-15 and Pterosaur "
        "examples are good starting points."))


# ----------------------------------------------------------------------------
def add_ext_signal_processing(story):
    story.append(PageBreak())
    heading("Signal Processing for FCS", 0, story)

    heading("Continuous-time filters", 1, story)
    math("Lag: &nbsp; H(s) = c<sub>1</sub>/(s + c<sub>1</sub>)")
    math("Lead-lag: &nbsp; H(s) = (c<sub>1</sub>s + c<sub>2</sub>)/(c<sub>3</sub>s + c<sub>4</sub>)")
    math("Washout: &nbsp; H(s) = s/(s + c<sub>1</sub>)")
    math("Second-order: &nbsp; H(s) = (c<sub>1</sub>s² + c<sub>2</sub>s + c<sub>3</sub>)/"
         "(c<sub>4</sub>s² + c<sub>5</sub>s + c<sub>6</sub>)")
    story.append(p(
        "All four are the JSBSim filter components from Chapter 12. "
        "Coefficients c<sub>1..6</sub> are taken directly from the design "
        "in the continuous-time s-plane."))

    heading("Discretisation: bilinear (Tustin) transform", 1, story)
    math("s ← (2/T) · (z − 1)/(z + 1)")
    story.append(p(
        "Tustin maps the entire left half-plane (stable continuous) into "
        "the unit disc (stable discrete) so stability is preserved. "
        "Frequencies are warped: ω<sub>d</sub> = (2/T) tan(ω<sub>a</sub>T/2). "
        "For critical pole/zero frequencies, &quot;prewarping&quot; "
        "(replacing 2/T with ω<sub>0</sub>/tan(ω<sub>0</sub>T/2)) "
        "preserves the location exactly."))

    heading("PID discretisation", 1, story)
    code(
        "u(z) = K_p · e(z)\n"
        "     + K_i · T/2 · (1 + z⁻¹)/(1 − z⁻¹) · e(z)   (trapezoidal)\n"
        "     + K_d · (1 − z⁻¹)/T · e(z)                  (backward Euler)")
    story.append(p(
        "JSBSim's <font face='Courier'>&lt;pid&gt;</font> offers four "
        "integration methods (rect = backward Euler, trap = trapezoidal, "
        "ab2/ab3 = Adams-Bashforth). The "
        "<font face='Courier'>&lt;trigger&gt;</font> element provides "
        "anti-windup: when non-zero the integral is frozen, when "
        "negative it is reset."))

    heading("PID tuning rules", 1, story)
    table_data = [
        ["Method", "Kp", "Ki", "Kd"],
        ["Ziegler-Nichols (oscillation)",
            "0.6·K<sub>u</sub>", "1.2·K<sub>u</sub>/T<sub>u</sub>", "0.075·K<sub>u</sub>·T<sub>u</sub>"],
        ["Lambda tuning (FOPDT, λ = closed-loop τ)",
            "τ/(K(λ+θ))", "Kp/τ", "0 (no D)"],
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
    heading("Linear Complementarity and Contact Friction", 0, story)

    heading("The LCP formulation", 1, story)
    story.append(p(
        "A Linear Complementarity Problem seeks <b>z</b> ∈ ℝⁿ such that"))
    math("<b>w</b> = M<b>z</b> + <b>q</b>, &nbsp; <b>w</b> ≥ 0, &nbsp; <b>z</b> ≥ 0, &nbsp; <b>w</b><sup>T</sup><b>z</b> = 0")
    story.append(p(
        "i.e. for each i, either w<sub>i</sub> = 0 or z<sub>i</sub> = 0. "
        "Contact-with-friction is naturally an LCP: z<sub>i</sub> is the "
        "contact impulse at the i-th contact, w<sub>i</sub> is the relative "
        "velocity normal to the surface; either there is a contact (z &gt; 0, "
        "w = 0) or there is not (z = 0, w &gt; 0)."))

    heading("JSBSim's gear LCP", 1, story)
    story.append(p(
        "Each landing-gear contact contributes:"))
    for b in [
        "A non-penetration constraint normal to the runway.",
        "Coulomb friction constraints tangent to the runway (forward / "
        "side / rolling resistance).",
        "Brake torque from the FCS as an additional friction-cone limit.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "JSBSim's <font face='Courier'>FGAccelerations::"
        "CalculateFrictionForces()</font> solves the resulting LCP with "
        "Projected Gauss-Seidel iteration (Catto 2005), up to 50 inner "
        "iterations per tick. This is the same algorithm used in modern "
        "game-physics engines (Bullet, ODE, Box2D)."))
    story.append(p(
        "<b>Why an LCP and not just an explicit force calculation?</b> "
        "Because the stiff spring-damper-friction system is "
        "unconditionally unstable under explicit integration if you allow "
        "interpenetration. The LCP formulation projects the contact onto "
        "the admissible constraint manifold each tick, which is "
        "implicitly stable regardless of stiffness."))


# ----------------------------------------------------------------------------
def add_ext_trim_algorithm(story):
    story.append(PageBreak())
    heading("The Trim Algorithm Inside Out", 0, story)
    story.append(p(
        "<font face='Courier'>FGTrim</font> finds the aircraft state and "
        "control settings that satisfy a steady-flight condition. It is "
        "implemented as a composition of one-dimensional secant root-"
        "finders coordinated by an outer loop."))

    heading("FGTrimAxis: the unit cell", 1, story)
    story.append(p(
        "Each <font face='Courier'>FGTrimAxis</font> pairs a state "
        "variable to zero out (e.g. <i>ẇ</i>) with a control variable "
        "to vary (e.g. α). Given two control guesses with their "
        "corresponding state values, the secant update is"))
    math("x<sub>n+1</sub> = x<sub>n</sub> − f(x<sub>n</sub>) · (x<sub>n</sub> − x<sub>n−1</sub>) / (f(x<sub>n</sub>) − f(x<sub>n−1</sub>))")
    story.append(p(
        "JSBSim applies a 0.9 relaxation to dampen oscillations:"))
    math("x<sub>n+1</sub> = x<sub>n</sub> − 0.9 f(x<sub>n</sub>) (Δx/Δf)")
    story.append(p(
        "If the secant step leaves the bracket, JSBSim falls back to "
        "bisection on that axis. Each axis converges to a tolerance: "
        "1e-3 for translational ẍ, 1e-4 (10× tighter) for angular <font name='DejaVu'>ω̇</font>."))

    heading("Trim modes", 1, story)
    table_data = [
        ["Mode (TrimMode)", "States zeroed", "Controls varied"],
        ["tLongitudinal",
         "<i>u̇</i>=0, <i>ẇ</i>=0, <i><font name='DejaVu'>q̇</font></i>=0",
         "throttle, α, elevator"],
        ["tFull",
         "+ <i><font name='DejaVu'>v̇</font></i>=0, <i>ṗ</i>=0, <i>ṙ</i>=0, ψ-track",
         "+ φ, aileron, rudder, β"],
        ["tFullWingsLevel", "tFull, but φ=0; β solves <i><font name='DejaVu'>v̇</font></i>=0",
         "throttle, α, elevator, aileron, rudder, β"],
        ["tGround",
         "<i>ẇ</i>=0, <i><font name='DejaVu'>q̇</font></i>=0, <i>ṗ</i>=0",
         "altitude (AGL), θ, φ"],
        ["tPullup",
         "longitudinal, n<sub>z</sub> = target",
         "α, throttle, elevator"],
        ["tTurn",
         "coordinated turn at target bank",
         "throttle, elevator, rudder"],
        ["tTurnFull",
         "coordinated turn + roll/yaw rates",
         "full set"],
        ["tCustom",
         "user-built via AddState/RemoveState",
         "user-chosen"],
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

    heading("Outer loop and convergence", 1, story)
    story.append(p(
        "Defaults: <font face='Courier'>SetMaxCycles(60)</font> passes "
        "through the axis list, <font face='Courier'>SetMaxCyclesPerAxis(100)"
        "</font> iterations per inner axis. Within each cycle, axes are "
        "trimmed in a fixed order. If all axes simultaneously meet their "
        "tolerances after a full cycle, the trim is declared converged "
        "and <font face='Courier'>simulation/trim-completed</font> is set "
        "to 1; otherwise the time history is restored and an error is "
        "raised."))


# ----------------------------------------------------------------------------
def add_ext_nesc_check_cases(story):
    story.append(PageBreak())
    heading("NASA NESC 2015 Verification Check Cases", 0, story)
    story.append(p(
        "JSBSim was the only open-source participant in the NASA "
        "Engineering and Safety Center's 6-DoF verification programme "
        "(NASA/TM-2015-218675). The other six tools were NASA in-house "
        "simulators (LaSRS++, SES, Marvin, POST-II, OSIRIS, MAVERIC). The "
        "NESC concluded that all seven simulators agreed to a publishable "
        "degree on the majority of cases, with the remaining differences "
        "explained and reducible."))

    heading("Atmospheric flight cases", 1, story)
    table_data = [
        ["#", "Case", "Tests"],
        ["1", "Dropped sphere, dragless",
         "Free fall in uniform gravity"],
        ["2", "Tumbling brick, dragless",
         "Newton-Euler equations, inertia tensor"],
        ["3", "Tumbling brick + aero damping",
         "Adds damping moments to rigid-body case 2"],
        ["4", "Dropped sphere, flat Earth",
         "Tests gravity model selection"],
        ["5", "Dropped sphere, rotating spherical Earth",
         "Adds Coriolis"],
        ["6", "Dropped sphere, rotating ellipsoidal Earth",
         "Adds WGS-84 geodesy"],
        ["7-8", "Dropped sphere, steady / varying wind",
         "Wind shear and gust profiles"],
        ["9-10", "Ballistic eastward / northward",
         "Coriolis components"],
        ["11", "F-16 subsonic trim",
         "Trim algorithm, short-period eigenstructure"],
        ["12", "F-16 supersonic trim",
         "Transonic / supersonic aero, M&gt;1 trim"],
        ["13.1-13.4", "F-16 disturbance manoeuvres",
         "Altitude doublet, velocity step, heading step"],
        ["15-16", "F-16 global flights",
         "Over the North Pole, around the equator"],
        ["17", "Two-stage rocket sea-level to orbit",
         "Atmospheric → orbital transition"],
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
        "JSBSim's NASA test-case implementations live at "
        "<font face='Courier'>github.com/open-aerospace/jsbsim-nasa-test-cases</font>; "
        "running them is the recommended way to verify a JSBSim build "
        "against the published reference trajectories. The F-16 short-"
        "period and Dutch-roll eigenvalues match across simulators to the "
        "third significant digit; trim residuals are below the per-axis "
        "tolerances 1e-3 ft/s² and 1e-4 rad/s² that JSBSim defaults to."))


# ----------------------------------------------------------------------------
def add_ext_property_tree_complete(story):
    story.append(PageBreak())
    heading("The Complete Property Tree", 0, story)
    story.append(p(
        "What follows is a near-complete enumeration of the JSBSim "
        "property namespace, distilled from the Doxygen API reference, "
        "the online manual, and the source-code <font face='Courier'>"
        "PropertyManager-&gt;Tie()</font> calls in each model."))

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
    heading("Function Language — Complete Operator Reference", 0, story)
    story.append(p(
        "Every operator usable inside an <font face='Courier'>"
        "&lt;aerodynamics&gt;</font>, <font face='Courier'>"
        "&lt;flight_control&gt;</font>, <font face='Courier'>&lt;system&gt;"
        "</font> or <font face='Courier'>&lt;external_reactions&gt;</font> "
        "<font face='Courier'>&lt;function&gt;</font> block, distilled "
        "from the Doxygen <font face='Courier'>FGFunction</font> reference. "
        "Shortcuts: <font face='Courier'>&lt;v&gt;</font> = "
        "<font face='Courier'>&lt;value&gt;</font>, "
        "<font face='Courier'>&lt;p&gt;</font> = "
        "<font face='Courier'>&lt;property&gt;</font>, "
        "<font face='Courier'>&lt;t&gt;</font> = "
        "<font face='Courier'>&lt;table&gt;</font>."))

    table_data = [
        ["Operator", "Description"],
        ["sum",         "Adds all immediate children."],
        ["difference",  "First child minus sum of remaining children."],
        ["product",     "Multiplies all children."],
        ["quotient",    "First child divided by second."],
        ["pow",         "First child raised to second."],
        ["sqrt",        "Square root."],
        ["exp",         "e raised to child."],
        ["ln, log2, log10", "Natural, base-2, base-10 logarithm."],
        ["abs, sign",   "Absolute value, sign."],
        ["sin, cos, tan", "Trig (arg in radians)."],
        ["asin, acos, atan", "Inverse trig; result in radians."],
        ["atan2",       "atan2(Y, X); range −π..π."],
        ["toradians, todegrees", "Angular unit conversion."],
        ["pi",          "Constant π. Use as <pi/>."],
        ["lt, le, gt, ge, eq, nq",
            "Returns 1 if relation holds else 0."],
        ["and, or, not", "Boolean. and/or take n children."],
        ["ifthen",      "ifthen(cond, true, false). Default false = 0."],
        ["switch",      "switch(index, v0, v1, …); index zero-based."],
        ["min, max, avg", "Aggregate over children."],
        ["floor, ceil, integer, fraction",
            "Rounding operations."],
        ["mod, fmod, roundmultiple",
            "Modulo, floating-point modulo, rounding to multiple."],
        ["random",      "Gaussian; attrs seed, mean, stddev."],
        ["urandom",     "Uniform; attrs seed, lower, upper."],
        ["value, v",    "Literal numeric."],
        ["property, p", "Read property (string body)."],
        ["table, t",    "1-D, 2-D or 3-D table."],
        ["interpolate1d", "1-D inline interpolation."],
        ["rotation_alpha_local, rotation_beta_local, rotation_gamma_local",
            "Specialty rotations (6 args)."],
        ["rotation_bf_to_wf, rotation_wf_to_bf",
            "Body↔wind rotations (7 args)."],
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
    heading("Verification and Validation Procedures", 0, story)

    heading("V&amp;V hierarchy", 1, story)
    for b in [
        "<b>Verification</b>: are we solving the equations correctly? "
        "Test against analytical solutions, against published reference "
        "trajectories (NESC), against the simulator's own previous results "
        "after code change.",
        "<b>Validation</b>: are we solving the correct equations? Compare "
        "with flight test, wind tunnel, real aircraft handbook numbers. "
        "Validation is always against external truth.",
        "<b>Sensitivity analysis</b>: perturb each parameter (CG, "
        "I<sub>yy</sub>, C<sub>mα</sub>, etc.) and quantify the response "
        "shift. Identifies the parameters most worth investing in.",
    ]:
        story.append(bullet(b))

    heading("Verification check list (per release)", 1, story)
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

    heading("Validation against flight data", 1, story)
    story.append(p(
        "When flight-test data exists (Cooper-Harper-rated step responses, "
        "stick-fixed releases, doublets), the procedure is:"))
    for b in [
        "Match the trim condition exactly: weight, CG, altitude, Mach, "
        "fuel state. Document the aircraft configuration (gear, flaps, "
        "stores).",
        "Drive the simulator with the recorded pilot inputs (digital "
        "stick/throttle traces).",
        "Plot p, q, r, α, β, n<sub>z</sub>, altitude, IAS overlaid with "
        "flight-test signals. Compute RMS error per channel.",
        "Update aero coefficients to minimise error using least-squares "
        "system ID — but always against a <i>held-out</i> validation "
        "manoeuvre to avoid overfitting.",
    ]:
        story.append(bullet(b))

    heading("Handling qualities (MIL-F-8785C / MIL-HDBK-1797)", 1, story)
    story.append(p(
        "Modern HQ rating predicts Cooper-Harper pilot rating from "
        "open-loop and closed-loop parameters. Key boundaries:"))
    for b in [
        "Short-period <i>ω<sub>n</sub></i> vs n/α (Category A/B/C, "
        "Level 1/2/3 boundaries).",
        "Phugoid damping ratio (Level 1 ζ &gt; 0.04).",
        "Roll mode time constant τ<sub>roll</sub> (Level 1 &lt; 1 s).",
        "Dutch roll ζ·ω<sub>n</sub> &gt; 0.15 (Level 1).",
        "Bandwidth and dropback (modern criteria; supplements "
        "MIL-F-8785C).",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_ext_further_reading(story):
    story.append(PageBreak())
    heading("Further Reading and Authoritative Sources", 0, story)
    story.append(p(
        "The list below is the curated set of references that this manual "
        "and the JSBSim source code itself cite most often."))

    heading("Aerodynamics &amp; airfoil theory", 1, story)
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
        "Dover, 1959. — the NACA-airfoil reference.",
    ]:
        story.append(bullet(b))

    heading("Flight dynamics &amp; control", 1, story)
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
        "Controls</i>, DARcorp, 2003. Roskam's eight-volume <i>Airplane "
        "Design</i> set is the engineering bible.",
        "USAF Stability and Control DATCOM, AFFDL-TR-79-3032 (1978). "
        "Semi-empirical estimation methods for every derivative.",
    ]:
        story.append(bullet(b))

    heading("CFD &amp; turbulence modelling", 1, story)
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

    heading("Atmosphere &amp; geodesy", 1, story)
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

    heading("Propulsion", 1, story)
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

    heading("Numerical methods", 1, story)
    for b in [
        "Hairer, E., Nørsett, S. P., Wanner, G. <i>Solving Ordinary "
        "Differential Equations I</i> (non-stiff), 2nd ed., Springer, 1993.",
        "Diebel, J. \"Representing Attitude.\" Stanford Univ. report, 2006.",
        "Shoemake, K. \"Animating Rotation with Quaternion Curves.\" "
        "SIGGRAPH 1985.",
        "Buss, S. \"Accurate and Efficient Simulation of Rigid Body "
        "Rotations.\" UCSD, 1999.",
        "Catto, E. \"Iterative Dynamics with Temporal Coherence.\" "
        "Crystal Dynamics tech. report, 2005.",
    ]:
        story.append(bullet(b))

    heading("JSBSim-specific resources", 1, story)
    for b in [
        "Berndt, J. S. \"JSBSim: An Open Source Flight Dynamics Model in "
        "C++.\" AIAA-2004-4923. PDF at jsbsim.sourceforge.net.",
        "Online manual: jsbsim-team.github.io/jsbsim-reference-manual.",
        "Doxygen API: jsbsim-team.github.io/jsbsim.",
        "NASA NESC 6-DoF check-cases: nescacademy.nasa.gov/flightsim/2015.",
        "JSBSim NASA test-case implementations: github.com/open-aerospace/"
        "jsbsim-nasa-test-cases.",
        "DeepWiki summary: deepwiki.com/JSBSim-Team/jsbsim.",
        "FlightGear wiki (lots of practical JSBSim notes): "
        "wiki.flightgear.org/JSBSim.",
    ]:
        story.append(bullet(b))

    heading("OpenFOAM &amp; the CFD-to-FDM workflow", 1, story)
    for b in [
        "OpenFOAM User Guide &mdash; <i>forces</i> and <i>forceCoeffs</i> "
        "function objects: openfoam.com/documentation/guides "
        "(ESI) and cpp.openfoam.org (Foundation).",
        "Greenshields, C. <i>OpenFOAM User Guide</i>, OpenCFD/CFD Direct. The "
        "<font face='Courier'>snappyHexMesh</font>, "
        "<font face='Courier'>simpleFoam</font> and "
        "<font face='Courier'>pimpleFoam</font> tutorials (incl. "
        "<font face='Courier'>RAS/wingMotion</font>) are the canonical "
        "starting points.",
        "Menter, F. R. \"Two-Equation Eddy-Viscosity Turbulence Models for "
        "Engineering Applications.\" AIAA Journal 32(8), 1994 &mdash; the "
        "k-&omega; SST model used for external aerodynamics.",
        "Da Ronch, A., et al. \"Estimation of Dynamic Stability Derivatives "
        "Using Computational Fluid Dynamics.\" &mdash; rotary-frame and "
        "forced-oscillation methods.",
        "Mi, B., et al. \"Estimation and Separation of Longitudinal Dynamic "
        "Stability Derivatives with the Forced Oscillation Method Using CFD.\" "
        "<i>Aerospace</i> 8(11):354, 2021 &mdash; plunging/pitching "
        "separation of C<sub>mq</sub> and C<sub>m" + _g("α̇") + "</sub>.",
        "Tobak, M., Schiff, L. B. \"Aerodynamic Mathematical Modeling &mdash; "
        "Basic Concepts.\" AGARD LS-114, 1981 &mdash; indicial-response theory "
        "behind dynamic derivatives.",
        "NASA Turbulence Modeling Resource (turbmodels.larc.nasa.gov) and the "
        "AIAA Drag Prediction / High-Lift Prediction Workshops &mdash; "
        "validation cases for aircraft CFD.",
        "Roache, P. J. \"Quantification of Uncertainty in Computational Fluid "
        "Dynamics.\" <i>Annu. Rev. Fluid Mech.</i> 29, 1997 &mdash; the Grid "
        "Convergence Index for mesh-independence.",
        "PyFoam, foamlib and the JSBSim Python module &mdash; scripting the "
        "sweep and verifying the generated model.",
    ]:
        story.append(bullet(b))


# ============================================================================
# Part III — The OpenFOAM -> JSBSim CFD workflow
# ============================================================================


def _g(s):
    """Wrap a string in the DejaVu font so non-Latin-1 glyphs (Greek, dots,
    arrows, mathematical operators) render reliably inside Helvetica prose."""
    return f"<font name='DejaVu'>{s}</font>"


def _oftab(data, colWidths):
    """Build a table in the house style used throughout this manual."""
    t = Table(wrap_table(data), colWidths=colWidths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d3b66")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
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
    story.append(Paragraph("Part III", ParagraphStyle(
        "PartLabel3", fontName="Helvetica-Bold", fontSize=18,
        textColor=colors.HexColor("#1d5d9b"), alignment=TA_CENTER,
        spaceAfter=12)))
    story.append(Paragraph(
        "From CFD to a Flying Model:<br/>the OpenFOAM to JSBSim Workflow",
        ParagraphStyle(
            "PartTitle3", fontName="Helvetica-Bold", fontSize=26,
            textColor=colors.HexColor("#0d3b66"), alignment=TA_CENTER,
            leading=32)))
    story.append(Spacer(1, 12 * mm))
    story.append(Paragraph(
        "The most demanding part of building a new aircraft is populating the "
        "<font face='Courier'>&lt;aerodynamics&gt;</font> block with numbers "
        "that are actually true of your airframe. Part III is an end-to-end, "
        "reproducible recipe for generating those numbers with the open-source "
        "CFD toolbox OpenFOAM and pouring them into JSBSim. We cover geometry "
        "preparation and meshing, steady-state extraction of the static force "
        "and moment coefficients, three complementary techniques for the "
        "dynamic (rate) derivatives, the exact mapping of every coefficient "
        "into JSBSim's function/table language, a scriptable pipeline that "
        "automates the whole sweep, and a verification loop that closes CFD "
        "against trim, the eigenmodes, wind-tunnel and flight data. Everything "
        "here builds on the aerodynamics, function/table and trim machinery "
        "documented in Parts I and II.",
        ParagraphStyle("PartIntro3", parent=BODY_STYLE,
                       alignment=TA_CENTER, fontSize=11, leading=15,
                       leftIndent=22 * mm, rightIndent=22 * mm)))


# ----------------------------------------------------------------------------
def add_of_pipeline_overview(story):
    A = _g("α"); B = _g("β")
    story.append(PageBreak())
    heading("The CFD-to-FDM Pipeline: From OpenFOAM to a JSBSim Model", 0,
            story)
    story.append(p(
        "A JSBSim aerodynamic model is, at heart, a table of nondimensional "
        "coefficients as functions of flow state (angle of attack, sideslip, "
        "Mach, control deflections) plus a handful of dynamic derivatives that "
        "capture the unsteady reaction to angular rates. Wind-tunnel data is "
        "the gold standard, but for a new or modified airframe a "
        "Reynolds-Averaged Navier-Stokes (RANS) CFD campaign in OpenFOAM is "
        "the most accessible way to obtain a complete, self-consistent dataset "
        "before any hardware exists. This chapter frames the whole campaign: "
        "what JSBSim needs, how the model is decomposed, and what matrix of "
        "CFD runs produces it."))

    heading("Why build an aerodynamic model from CFD", 1, story)
    for b in [
        "<b>No hardware required.</b> You can characterise an airframe from a "
        "CAD model months before a wind-tunnel slot or first flight.",
        "<b>Full observability.</b> CFD returns the complete pressure and "
        "shear field, so you can decompose forces by component (wing, tail, "
        "fuselage, nacelles) exactly the way JSBSim's build-up model wants.",
        "<b>Arbitrary conditions.</b> High angle of attack, sideslip, control "
        "deflections, ground effect, and flight Reynolds/Mach numbers that are "
        "hard or expensive to reproduce in a tunnel.",
        "<b>Open and reproducible.</b> OpenFOAM is GPL, scriptable, and runs "
        "on a laptop or an HPC cluster with identical dictionaries — a natural "
        "match for JSBSim's open, data-driven philosophy.",
    ]:
        story.append(bullet(b))
    story.append(quote(
        "CFD does not replace the wind tunnel or flight test; it front-loads "
        "the model so that the expensive data you do collect is spent "
        "correcting a model rather than creating one from scratch."))

    heading("What JSBSim needs: the coefficient shopping list", 1, story)
    story.append(p(
        "Every quantity below is a <i>nondimensional</i> coefficient. In "
        "JSBSim each becomes one or more <font face='Courier'>&lt;function&gt;"
        "</font> elements summed into an <font face='Courier'>&lt;axis&gt;"
        "</font> (see the aerodynamics chapter and "
        "<font face='Courier'>FGAerodynamics.cpp:57-69</font> for the axis "
        "name-to-index map). The right-hand column names the CFD experiment "
        "that yields it."))
    data = [
        ["Coefficient", "Physical meaning", "JSBSim axis", "CFD experiment"],
        ["C<sub>L</sub>", "Lift vs " + A + ", flap, Mach", "LIFT (wind)",
         "Steady RANS " + A + "-sweep"],
        ["C<sub>D</sub>", "Drag polar vs " + A + ", Mach", "DRAG (wind)",
         "Steady RANS " + A + "-sweep"],
        ["C<sub>Y</sub>", "Side force vs " + B, "SIDE (wind)",
         "Steady RANS " + B + "-sweep"],
        ["C<sub>l</sub>", "Roll moment vs " + B + ", " + _g("δ") + "a, " +
         _g("δ") + "r", "ROLL (body)", B + "-sweep + control runs"],
        ["C<sub>m</sub>", "Pitch moment vs " + A + ", " + _g("δ") + "e, Mach",
         "PITCH (body)", A + "-sweep + elevator runs"],
        ["C<sub>n</sub>", "Yaw moment vs " + B + ", " + _g("δ") + "a, " +
         _g("δ") + "r", "YAW (body)", B + "-sweep + control runs"],
        ["C<sub>Lq</sub>, C<sub>mq</sub>", "Lift/pitch due to pitch rate q",
         "LIFT, PITCH", "Forced-pitch oscillation / rotary"],
        ["C<sub>lp</sub>, C<sub>np</sub>", "Roll/yaw due to roll rate p",
         "ROLL, YAW", "Forced-roll oscillation / steady roll"],
        ["C<sub>lr</sub>, C<sub>nr</sub>", "Roll/yaw due to yaw rate r",
         "ROLL, YAW", "Forced-yaw oscillation / steady yaw"],
        ["C<sub>L" + _g("α̇") + "</sub>, C<sub>m" + _g("α̇") + "</sub>",
         "Lift/pitch due to " + _g("α̇") + " (downwash lag)", "LIFT, PITCH",
         "Plunging (heave) oscillation"],
        ["&Delta;C<sub>(...)</sub>/" + _g("δ"),
         "Control-power increments", "respective axes",
         "Deflected-geometry runs"],
    ]
    story.append(_oftab(data, [2.6 * cm, 5.0 * cm, 2.7 * cm, 6.0 * cm]))

    heading("The build-up (component) model and the quasi-steady "
            "assumption", 1, story)
    story.append(p(
        "JSBSim sums independent <font face='Courier'>&lt;function&gt;</font> "
        "contributions into each axis, so the natural model is a "
        "<i>build-up</i>: a baseline curve plus additive increments. For pitch "
        "moment, for example:"))
    math("C<sub>m</sub> = C<sub>m0</sub> + C<sub>m</sub>(" + _g("α") +
         ") + C<sub>m" + _g("δ") + "e</sub>·" + _g("δ") +
         "e + C<sub>mq</sub>·(c&#x0304;/2V)·q + C<sub>m" + _g("α̇") +
         "</sub>·(c&#x0304;/2V)·" + _g("α̇"))
    story.append(p(
        "This linear superposition is exact only if the contributions are "
        "independent. In practice the baseline curves are tabulated "
        "nonlinearly (so stall and compressibility are captured), control and "
        "rate terms are treated as increments about the local operating point, "
        "and strong couplings (e.g. " + A + "-dependent control effectiveness) "
        "are carried as 2-D tables. The <i>quasi-steady</i> assumption — that "
        "the instantaneous force depends only on the instantaneous state plus "
        "first-order rate terms — is what makes a finite table sufficient. It "
        "holds for the reduced frequencies of conventional flight; it breaks "
        "down for rapid manoeuvres, dynamic stall, and aeroelastic flutter, "
        "which need unsteady models beyond JSBSim's table framework."))

    heading("The design-of-experiments matrix", 1, story)
    story.append(p(
        "Plan the campaign as a structured sweep so that each CFD run maps to "
        "a known table breakpoint. A practical baseline matrix for a "
        "conventional aircraft:"))
    for b in [
        "<b>" + A + " sweep</b> at " + B + "=0: e.g. -8&deg; to +20&deg; in "
        "2&deg; steps, finer near stall. Yields C<sub>L</sub>(" + A + "), "
        "C<sub>D</sub>(" + A + "), C<sub>m</sub>(" + A + ").",
        "<b>" + B + " sweep</b> at a few representative " + A + ": 0&deg; to "
        "&plusmn;15&deg;. Yields C<sub>Y</sub>(" + B + "), C<sub>l</sub>(" +
        B + "), C<sub>n</sub>(" + B + ") — the static lateral-directional "
        "stability.",
        "<b>Control runs</b>: re-mesh with each surface deflected (elevator, "
        "aileron, rudder, flap) at 2-3 angles to get linear and saturating "
        "increments.",
        "<b>Mach sweep</b> (if compressible/transonic): repeat the " + A +
        " sweep at several Mach numbers to populate the compressibility "
        "table dimension.",
        "<b>Dynamic runs</b>: forced-oscillation or rotary cases at one or a "
        "few operating points to get the rate derivatives (next chapters).",
    ]:
        story.append(bullet(b))
    story.append(p(
        "A minimal conventional dataset is on the order of 20-40 static runs "
        "plus a handful of dynamic ones; a transonic, multi-Mach, "
        "full-control dataset can run to several hundred. Script it (see the "
        "Automation chapter)."))

    heading("Nondimensionalisation: the bridge between CFD and JSBSim", 1,
            story)
    story.append(p(
        "Both worlds speak coefficients, but you must align reference "
        "quantities or the numbers will not transfer. CFD reports "
        "C<sub>F</sub> = F / (&frac12;" + _g("ρ") + "V&sup2; S<sub>ref</sub>) "
        "and C<sub>M</sub> = M / (&frac12;" + _g("ρ") +
        "V&sup2; S<sub>ref</sub> l<sub>ref</sub>). JSBSim reconstructs the "
        "force as <i>coefficient</i> &times; <font face='Courier'>"
        "aero/qbar-area</font> (= " + _g("q̄") + "&middot;S) and the moment "
        "with an extra span or chord factor, where " + _g("q̄") + " = &frac12;"
        + _g("ρ") + "V&sup2; (<font face='Courier'>FGAerodynamics.cpp:163"
        "</font>)."))
    story.append(p(
        "The crucial alignment rules — get these wrong and your model is "
        "silently mis-scaled:"))
    for b in [
        "<b>S<sub>ref</sub> = </b> the wing area you put in "
        "<font face='Courier'>&lt;metrics&gt;&lt;wingarea&gt;</font> "
        "(property <font face='Courier'>metrics/Sw-sqft</font>). Use the same "
        "<font face='Courier'>Aref</font> in OpenFOAM's "
        "<font face='Courier'>forceCoeffs</font>.",
        "<b>l<sub>ref</sub> = </b> mean aerodynamic chord c&#x0304; for "
        "pitch, span b for roll/yaw. JSBSim multiplies pitch by "
        "<font face='Courier'>metrics/cbarw-ft</font> and roll/yaw by "
        "<font face='Courier'>metrics/bw-ft</font>.",
        "<b>Moment reference = </b> OpenFOAM's <font face='Courier'>CofR"
        "</font> must equal JSBSim's <font face='Courier'>&lt;location "
        "name=\"AERORP\"&gt;</font>, or you must transfer the moments (see the "
        "XML-mapping chapter).",
        "<b>Rate nondimensionalisers.</b> JSBSim forms b/(2V) as "
        "<font face='Courier'>aero/bi2vel</font> and c&#x0304;/(2V) as "
        "<font face='Courier'>aero/ci2vel</font> "
        "(<font face='Courier'>FGAerodynamics.cpp:159-160, 618-619</font>); "
        "your CFD rate derivatives must use the <i>same</i> half-chord/"
        "half-span convention.",
    ]:
        story.append(bullet(b))

    heading("Roadmap of Part III", 1, story)
    for b in [
        "<b>Geometry &amp; meshing</b> — watertight STL, domain, "
        "snappyHexMesh, y<sup>+</sup>, control surfaces.",
        "<b>Static coefficients</b> — simpleFoam/rhoSimpleFoam, the "
        "<font face='Courier'>forceCoeffs</font> function object, "
        + A + "/" + B + " sweeps.",
        "<b>Dynamic derivatives</b> — rotary frame, forced oscillation, "
        "plunging, indicial; extracting C<sub>mq</sub>, C<sub>lp</sub>, "
        "C<sub>nr</sub>, &hellip;",
        "<b>XML mapping</b> — turning the dataset into a complete "
        "<font face='Courier'>&lt;aerodynamics&gt;</font> block.",
        "<b>Automation</b> — a Python driver that runs the sweep and emits "
        "JSBSim tables.",
        "<b>Verification</b> — trim, eigenmodes, and comparison to "
        "tunnel/flight.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_of_geometry_meshing(story):
    story.append(PageBreak())
    heading("Geometry and Meshing for Aircraft in OpenFOAM", 0, story)
    story.append(p(
        "The mesh determines whether your coefficients are physics or "
        "numerical noise. This chapter covers preparing watertight geometry, "
        "sizing the domain, generating a body-fitted mesh with "
        "<font face='Courier'>blockMesh</font> + "
        "<font face='Courier'>snappyHexMesh</font>, hitting the right "
        "near-wall resolution for your turbulence model, and the special "
        "problem of deflected control surfaces."))

    heading("Watertight geometry and feature extraction", 1, story)
    story.append(p(
        "Export the airframe as a triangulated surface (STL/OBJ) in a single, "
        "closed, non-self-intersecting shell, with named regions ("
        "<font face='Courier'>wing</font>, <font face='Courier'>fuselage"
        "</font>, <font face='Courier'>elevator</font>, &hellip;) so patches "
        "can be force-integrated separately for the component build-up. Place "
        "the file in <font face='Courier'>constant/triSurface/</font>. Extract "
        "sharp edges (trailing edges, control-surface gaps) so the mesher "
        "snaps to them:"))
    code("""\
# constant/triSurface/ contains aircraft.stl (named solids)
surfaceFeatureExtract       # reads system/surfaceFeatureExtractDict
                            # -> writes aircraft.eMesh (feature edges)
surfaceCheck aircraft.stl   # verify closed & non-degenerate""")
    story.append(p(
        "Keep the geometry in metres and consistent with the reference area "
        "you will declare; OpenFOAM is unit-agnostic but your "
        "<font face='Courier'>Aref</font>/<font face='Courier'>lRef</font> and "
        "the JSBSim metrics must match the same physical sizes."))

    heading("The computational domain", 1, story)
    story.append(p(
        "External-aerodynamics domains must be large enough that the farfield "
        "boundary does not load the solution. Rules of thumb, measured from "
        "the aircraft:"))
    for b in [
        "Upstream inlet: 10-20 mean chords (or &gt;5 body lengths).",
        "Downstream outlet: 20-30 chords to let the wake develop.",
        "Lateral/vertical farfield: 10-20 chords (or 5-10 spans).",
        "For a symmetric case (" + _g("β") + "=0, no roll/yaw asymmetry) cut "
        "the domain on the centre-plane with a <font face='Courier'>symmetry"
        "</font> patch and mesh only half the aircraft — half the cells for "
        "the same resolution.",
    ]:
        story.append(bullet(b))

    heading("Background mesh: blockMesh", 1, story)
    story.append(p(
        "<font face='Courier'>blockMesh</font> builds the rectangular "
        "background hex grid and names the farfield patches. "
        "<font face='Courier'>snappyHexMesh</font> then carves the aircraft "
        "out of it. A skeleton <font face='Courier'>blockMeshDict</font>:"))
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

    heading("Body-fitted mesh: snappyHexMesh", 1, story)
    story.append(p(
        "<font face='Courier'>snappyHexMesh</font> runs in three phases: "
        "<i>castellation</i> (refine and delete cells inside the body), "
        "<i>snapping</i> (move boundary vertices onto the STL and feature "
        "edges), and <i>layer addition</i> (insert prismatic boundary-layer "
        "cells). The essential dictionary knobs:"))
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
        "Run <font face='Courier'>snappyHexMesh -overwrite</font>, then "
        "<font face='Courier'>checkMesh</font>. Demand non-orthogonality "
        "below ~65&deg;, skewness below ~4, and that the requested layers "
        "actually grew (read the <font face='Courier'>snappyHexMesh</font> "
        "log: \"Layer addition\" coverage near 100% on lifting surfaces)."))

    heading("Near-wall resolution and y<sup>+</sup>", 1, story)
    story.append(p(
        "The first-cell height sets the wall coordinate y<sup>+</sup> = "
        "u<sub>" + _g("τ") + "</sub> y / " + _g("ν") + ", and your turbulence "
        "treatment dictates the target:"))
    for b in [
        "<b>Wall-resolved (low-Re) k-" + _g("ω") + " SST</b>: y<sup>+</sup> "
        "&lt; 1 on lifting surfaces, with 30-40 cells across the boundary "
        "layer and growth ratio &lt; 1.2. Required for trustworthy drag, "
        "separation and stall.",
        "<b>Wall functions</b> (high-Re): 30 &lt; y<sup>+</sup> &lt; 300. "
        "Cheaper, acceptable for attached-flow lift and pitching moment, but "
        "unreliable near stall and for drag breakdown.",
    ]:
        story.append(bullet(b))
    story.append(p(
        "Estimate the first-cell height from a flat-plate skin-friction "
        "correlation: C<sub>f</sub> &asymp; 0.026/Re<sub>x</sub><sup>1/7</sup>"
        ", wall shear " + _g("τ") + "<sub>w</sub> = &frac12;C<sub>f</sub>" +
        _g("ρ") + "U&sup2;, friction velocity u<sub>" + _g("τ") + "</sub> = "
        "&radic;(" + _g("τ") + "<sub>w</sub>/" + _g("ρ") + "), then "
        "&Delta;y<sub>1</sub> = y<sup>+</sup>" + _g("ν") + "/u<sub>" + _g("τ") +
        "</sub>. Always confirm the achieved y<sup>+</sup> from the solution "
        "(<font face='Courier'>postProcess -func yPlus</font>) and re-mesh if "
        "it overshoots."))

    heading("Mesh independence", 1, story)
    story.append(p(
        "Run at least three systematically refined meshes (e.g. cell counts "
        "in a ratio near 2) at a fixed condition and confirm C<sub>L</sub>, "
        "C<sub>D</sub>, C<sub>m</sub> converge. Quantify with the Grid "
        "Convergence Index (Roache) and Richardson extrapolation; report the "
        "asymptotic value, not the finest-grid value. Drag is far more "
        "mesh-sensitive than lift, so converge on drag."))

    heading("Control surfaces and moving geometry", 1, story)
    story.append(p(
        "Control-power and dynamic-derivative runs need the geometry in a "
        "deflected or moving state. Three approaches, in increasing cost:"))
    for b in [
        "<b>Separate static meshes</b> — model each deflection as its own STL "
        "and mesh. Simplest and most robust for control increments; just "
        "re-run the sweep with the deflected geometry and difference the "
        "coefficients.",
        "<b>Mesh morphing</b> (<font face='Courier'>displacementLaplacian"
        "</font> / RBF) — deform a single mesh for small deflections or "
        "oscillations; avoids re-meshing but degrades cell quality at large "
        "motion.",
        "<b>Overset (overlapping) or AMI sliding meshes</b> — a body-fitted "
        "component mesh moves through a background grid. Needed for large "
        "rotations (full-surface deflection, propellers) and for "
        "forced-oscillation dynamic runs.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_of_static_coeffs(story):
    A = _g("α"); B = _g("β")
    story.append(PageBreak())
    heading("Static Aerodynamic Coefficients from OpenFOAM", 0, story)
    story.append(p(
        "With a converged mesh, the static coefficients come from a series of "
        "steady-state RANS solutions, one per flow condition, each "
        "post-processed by the <font face='Courier'>forceCoeffs</font> "
        "function object. This chapter pins down solver choice, boundary "
        "conditions, how to impose angle of attack and sideslip, the exact "
        "<font face='Courier'>forceCoeffs</font> dictionary, and how to read "
        "off the sweep."))

    heading("Solver selection", 1, story)
    data = [
        ["Regime", "Solver", "Notes"],
        ["M &lt; 0.3 (incompressible)", "simpleFoam",
         "Steady SIMPLE; density constant; fastest. Most GA/UAV work."],
        ["0.3 &le; M &lt; 0.7", "rhoSimpleFoam",
         "Steady compressible; captures density variation."],
        ["Transonic (M ~ 0.7-1.2)", "rhoSimpleFoam",
         "Compressible with shock capturing; needs finer mesh, careful "
         "relaxation."],
        ["Need time-accuracy", "pimpleFoam / rhoPimpleFoam",
         "Transient; used for the dynamic-derivative runs."],
    ]
    story.append(_oftab(data, [4.0 * cm, 3.4 * cm, 8.8 * cm]))
    story.append(p(
        "For the turbulence model, <b>k-" + _g("ω") + " SST</b> (Menter) is "
        "the workhorse for external aerodynamics: it behaves well in adverse "
        "pressure gradients and separation and integrates to the wall when "
        "y<sup>+</sup>&lt;1. Spalart-Allmaras is a robust one-equation "
        "alternative for attached flow."))

    heading("Boundary conditions", 1, story)
    story.append(p(
        "A typical incompressible setup (fields in <font face='Courier'>0/"
        "</font>):"))
    data = [
        ["Patch", "U", "p", "k / " + _g("ω")],
        ["inlet", "freestreamVelocity", "freestreamPressure /<br/>zeroGradient",
         "fixedValue (turb. inflow)"],
        ["outlet", "freestream / inletOutlet", "freestreamPressure",
         "inletOutlet"],
        ["farfield", "freestream", "freestreamPressure", "inletOutlet"],
        ["aircraft", "noSlip", "zeroGradient",
         "kqRWallFunction / omegaWallFunction"],
        ["symmetry", "symmetryPlane", "symmetryPlane", "symmetryPlane"],
    ]
    story.append(_oftab(data, [2.4 * cm, 4.2 * cm, 4.6 * cm, 5.0 * cm]))
    story.append(p(
        "The <font face='Courier'>freestream</font>/"
        "<font face='Courier'>freestreamVelocity</font> conditions switch "
        "between inlet and outlet behaviour based on the local flux, so the "
        "same farfield works for any flow direction — convenient for "
        + A + "/" + B + " sweeps."))

    heading("Imposing angle of attack and sideslip", 1, story)
    story.append(p(
        "The clean approach is to keep the mesh fixed and <b>rotate the "
        "freestream velocity vector</b>. With body axes x aft-positive along "
        "the fuselage, y to starboard, z up, a freestream of speed V at angle "
        "of attack " + A + " and sideslip " + B + " is:"))
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
        "Crucially, the <font face='Courier'>liftDir</font> and "
        "<font face='Courier'>dragDir</font> in "
        "<font face='Courier'>forceCoeffs</font> must be set to the "
        "<i>same</i> " + A + "/" + B + " so that lift is reported "
        "perpendicular to the relative wind and drag along it. For pitch-plane "
        "sweeps: dragDir = (cos" + _g("α") + ", 0, sin" + _g("α") +
        "), liftDir = (&minus;sin" + _g("α") + ", 0, cos" + _g("α") + ")."))

    heading("The forceCoeffs function object", 1, story)
    story.append(p(
        "Add this to <font face='Courier'>system/controlDict</font> under "
        "<font face='Courier'>functions { }</font> (ESI / openfoam.com "
        "syntax; the openfoam.org fork is nearly identical). It integrates "
        "pressure and viscous forces over the named patches and normalises "
        "them."))
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
        "Outputs land in <font face='Courier'>postProcessing/forceCoeffs1/"
        "&lt;startTime&gt;/</font> as <font face='Courier'>coefficient.dat"
        "</font> (newer) or <font face='Courier'>forceCoeffs.dat</font> "
        "(older), one row per write with columns including "
        "<font face='Courier'>Cd</font> (drag), "
        "<font face='Courier'>Cl</font> (lift), "
        "<font face='Courier'>Cs</font> (side), and the moment coefficients "
        "<font face='Courier'>CmRoll</font>, "
        "<font face='Courier'>CmPitch</font>, "
        "<font face='Courier'>CmYaw</font>. All are normalised by &frac12;"
        + _g("ρ") + "&middot;magUInf&sup2;&middot;Aref (moments &times; lRef)."))
    story.append(p(
        "<b>Sign &amp; axis note.</b> OpenFOAM's moment coefficients are "
        "about <font face='Courier'>CofR</font> in the mesh frame; JSBSim's "
        "ROLL/PITCH/YAW are body-axis moments about the AERORP. Set "
        "<font face='Courier'>CofR=AERORP</font> and verify the sign of each "
        "coefficient against a known case before trusting it — a flipped axis "
        "or a moment-reference offset is the most common error in the whole "
        "pipeline (handled in detail in the XML-mapping chapter)."))

    heading("Convergence and averaging", 1, story)
    for b in [
        "Run to residual stagnation (typically 1e-4 to 1e-6) <i>and</i> "
        "coefficient plateau — monitor <font face='Courier'>coefficient.dat"
        "</font> live, not just residuals.",
        "Near stall or for bluff bodies the steady solver may limit-cycle; "
        "switch to a transient solver and time-average, or average the last "
        "few hundred SIMPLE iterations.",
        "Use consistent under-relaxation and a couple of thousand iterations; "
        "transonic cases need ramped Courant number / relaxation.",
    ]:
        story.append(bullet(b))

    heading("Running the sweeps", 1, story)
    story.append(p(
        "Clone the converged base case per condition, edit the freestream and "
        "<font face='Courier'>liftDir</font>/<font face='Courier'>dragDir"
        "</font>, run, and collect the final coefficient row. The result is "
        "the raw material for JSBSim's tables:"))
    for b in [
        "<b>" + A + "-sweep</b> &rarr; C<sub>L</sub>(" + A + "), C<sub>D</sub>("
        + A + "), C<sub>m</sub>(" + A + "). The C<sub>L</sub>-" + A + " slope "
        "should be near 2" + _g("π") + "&middot;AR/(AR+2) per radian; "
        "C<sub>m</sub>-" + A + " slope must be negative for static stability.",
        "<b>" + B + "-sweep</b> &rarr; C<sub>Y</sub>(" + B + "), C<sub>l</sub>("
        + B + ") (dihedral effect, want &lt;0), C<sub>n</sub>(" + B +
        ") (weathercock, want &gt;0).",
        "<b>Control runs</b> &rarr; &Delta;C per degree of "
        "elevator/aileron/rudder/flap.",
        "<b>Drag polar check</b> &rarr; fit C<sub>D</sub> = C<sub>D0</sub> + "
        "C<sub>L</sub>&sup2;/(" + _g("π") + " e AR) to sanity-check zero-lift "
        "drag and Oswald efficiency.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_of_dynamic_derivatives(story):
    A = _g("α"); B = _g("β")
    adot = _g("α̇")
    story.append(PageBreak())
    heading("Dynamic Stability Derivatives from OpenFOAM", 0, story)
    story.append(p(
        "Static sweeps miss the airframe's reaction to <i>angular rates</i> "
        "and to the <i>rate of change</i> of incidence. These dynamic "
        "(damping) derivatives — C<sub>mq</sub>, C<sub>lp</sub>, "
        "C<sub>nr</sub>, C<sub>lr</sub>, C<sub>np</sub>, C<sub>m" + adot +
        "</sub>, &hellip; — set the short-period, Dutch-roll, roll and spiral "
        "behaviour. They are harder to get from CFD because they require "
        "either a rotating reference frame or genuinely time-accurate motion. "
        "Three methods are in common use."))

    heading("The derivatives and their meaning", 1, story)
    data = [
        ["Derivative", "Couples", "Sign for a stable conventional aircraft"],
        ["C<sub>mq</sub>", "pitch moment &larr; pitch rate q",
         "&lt; 0 (pitch damping)"],
        ["C<sub>m" + adot + "</sub>", "pitch moment &larr; " + adot +
         " (downwash lag)", "&lt; 0"],
        ["C<sub>Lq</sub>", "lift &larr; pitch rate q", "&gt; 0"],
        ["C<sub>lp</sub>", "roll moment &larr; roll rate p",
         "&lt; 0 (roll damping)"],
        ["C<sub>nr</sub>", "yaw moment &larr; yaw rate r",
         "&lt; 0 (yaw damping)"],
        ["C<sub>lr</sub>", "roll moment &larr; yaw rate r", "&gt; 0"],
        ["C<sub>np</sub>", "yaw moment &larr; roll rate p",
         "&lt; 0 (adverse)"],
    ]
    story.append(_oftab(data, [2.6 * cm, 6.4 * cm, 7.2 * cm]))

    heading("Nondimensional rate and reduced frequency", 1, story)
    story.append(p(
        "Rate derivatives are defined against nondimensional rates: q&#x0302; "
        "= q&middot;c&#x0304;/(2V) for pitch, and p&#x0302;, r&#x0302; = "
        "p,r&middot;b/(2V) for roll/yaw — exactly JSBSim's "
        "<font face='Courier'>ci2vel</font> and "
        "<font face='Courier'>bi2vel</font>. For oscillatory tests the key "
        "similarity parameter is the <i>reduced frequency</i>:"))
    math("k = " + _g("ω") + "&middot;c&#x0304; / (2V)")
    story.append(p(
        "Choose k small (~0.01-0.1) and amplitude small (1-2&deg;) so the "
        "extracted derivatives are the quasi-steady values JSBSim's tables "
        "expect; larger k probes genuinely unsteady aerodynamics."))

    heading("Method 1: steady rotation in a non-inertial frame", 1, story)
    story.append(p(
        "Pure rotary derivatives (C<sub>mq</sub> without the " + adot +
        " part, C<sub>lp</sub>, C<sub>nr</sub>) can be obtained from a "
        "<i>steady</i> solution in a rotating reference frame, avoiding any "
        "mesh motion. The aircraft sits in a frame turning at constant "
        "angular velocity " + _g("Ω") + "; for a pitch-rate case the flow "
        "follows a circular arc and the steady moment gives C<sub>mq</sub> "
        "directly. In OpenFOAM this is set up with an MRF zone or an "
        "<font face='Courier'>fvOptions</font> rotation source:"))
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
        "Run two or three rates straddling zero, plot the moment coefficient "
        "against the nondimensional rate, and take the slope:"))
    math("C<sub>mq</sub> = &part;C<sub>m</sub> / &part;q&#x0302;,   "
         "q&#x0302; = q&middot;c&#x0304;/(2V)")
    story.append(p(
        "This is cheap (steady) and clean for the rotary part, but it does "
        "<i>not</i> capture the " + adot + " (downwash-lag) contribution, "
        "which needs motion."))

    heading("Method 2: forced oscillation", 1, story)
    story.append(p(
        "Oscillate the aircraft sinusoidally about the CofR with a transient "
        "solver (<font face='Courier'>pimpleFoam</font> + dynamic mesh) and "
        "extract the derivatives from the phase of the moment response. The "
        "canonical OpenFOAM primitive is "
        "<font face='Courier'>oscillatingRotatingMotion</font> (see the "
        "<font face='Courier'>pimpleFoam/RAS/wingMotion</font> tutorial):"))
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
        "For a pure pitch oscillation about the CG with the freestream fixed, "
        "the angle of attack and the pitch rate are locked together (q = " +
        adot + "), so the quasi-steady moment is:"))
    math("C<sub>m</sub>(t) = C<sub>m0</sub> + C<sub>m" + _g("α") +
         "</sub>&middot;" + _g("α") + "(t) + (C<sub>mq</sub> + C<sub>m" + adot +
         "</sub>)&middot;(c&#x0304;/2V)&middot;" + adot + "(t)")
    story.append(p(
        "With " + _g("α") + "(t) = " + _g("α") + "<sub>0</sub> + &Delta;" +
        _g("α") + "&middot;sin(" + _g("ω") + "t), the in-phase (sine) "
        "component of C<sub>m</sub> gives the static slope C<sub>m" + _g("α") +
        "</sub>, and the out-of-phase (cosine) component gives the combined "
        "damping. Extracting them as the first Fourier coefficients over one "
        "period T:"))
    math("C<sub>m" + _g("α") + "</sub> = (2/(&Delta;" + _g("α") +
         "T)) &#x222B; C<sub>m</sub>(t) sin(" + _g("ω") + "t) dt")
    math("C<sub>mq</sub> + C<sub>m" + adot + "</sub> = (2V/(c&#x0304;&middot;"
         + _g("ω") + "&middot;&Delta;" + _g("α") + "T)) &#x222B; C<sub>m</sub>"
         "(t) cos(" + _g("ω") + "t) dt")
    story.append(p(
        "Equivalently, plot C<sub>m</sub> against " + _g("α") +
        " over a cycle: the loop's area and sense encode the damping. A "
        "loop traversed clockwise (energy removed) means positive damping "
        "(C<sub>mq</sub>+C<sub>m" + adot + "</sub> &lt; 0). Discard the first "
        "1-2 cycles as startup transient and average over several clean "
        "cycles."))

    heading("Method 3: plunging and indicial response", 1, story)
    story.append(p(
        "Forced pitch yields only the <i>sum</i> C<sub>mq</sub> + C<sub>m" +
        adot + "</sub>. To separate them, run a <b>plunging (heave) "
        "oscillation</b>: translate the aircraft vertically so the angle of "
        "attack changes (giving " + adot + ") with <i>zero</i> pitch rate "
        "(q = 0). That isolates C<sub>m" + adot + "</sub>; subtract it from "
        "the forced-pitch sum to recover C<sub>mq</sub>:"))
    math("C<sub>mq</sub> = (C<sub>mq</sub> + C<sub>m" + adot +
         "</sub>)<sub>pitch</sub> &minus; (C<sub>m" + adot +
         "</sub>)<sub>plunge</sub>")
    story.append(p(
        "The <b>indicial (step) method</b> is the third route: impose a step "
        "in " + _g("α") + " or q and record the moment's transient build-up; "
        "the derivatives follow from the indicial response functions "
        "(Tobak/Wagner theory). It is the most general but the most "
        "demanding to post-process."))

    heading("Lateral-directional derivatives", 1, story)
    story.append(p(
        "The same machinery applies to roll and yaw. Forced-roll oscillation "
        "about the body x-axis gives C<sub>lp</sub> (and C<sub>np</sub>); "
        "forced-yaw oscillation about z gives C<sub>nr</sub> (and "
        "C<sub>lr</sub>). The nondimensionaliser switches from c&#x0304;/(2V) "
        "to b/(2V) (JSBSim's <font face='Courier'>bi2vel</font>). Steady "
        "rotation in a non-inertial frame is again the cheap route for the "
        "pure rate parts."))

    heading("Method comparison", 1, story)
    data = [
        ["Method", "Gets", "Cost", "Caveat"],
        ["Steady rotary frame", "pure C<sub>mq</sub>, C<sub>lp</sub>, "
         "C<sub>nr</sub>", "low (steady)", "misses " + adot + " lag"],
        ["Forced oscillation", "C<sub>mq</sub>+C<sub>m" + adot + "</sub> etc.",
         "high (transient + moving mesh)", "needs Fourier separation"],
        ["Plunging", "C<sub>m" + adot + "</sub> alone",
         "high", "pairs with forced pitch"],
        ["Indicial / step", "all, most general",
         "high", "complex post-processing"],
    ]
    story.append(_oftab(data, [3.6 * cm, 5.0 * cm, 4.0 * cm, 3.6 * cm]))
    story.append(quote(
        "Pragmatic recipe: use the steady rotary frame for the bulk of the "
        "rotary derivatives, add one forced-pitch + one plunging case to pin "
        "down C<sub>mq</sub> vs C<sub>m" + adot + "</sub>, and fall back on "
        "DATCOM/AVL estimates for any derivative the budget can't cover."))


# ----------------------------------------------------------------------------
def add_of_xml_mapping(story):
    A = _g("α"); B = _g("β")
    story.append(PageBreak())
    heading("Reducing CFD Data into the JSBSim Aircraft XML", 0, story)
    story.append(p(
        "This is where the campaign pays off: turning the CFD dataset into a "
        "complete <font face='Courier'>&lt;aerodynamics&gt;</font> block. The "
        "good news is that JSBSim's framework maps almost one-to-one onto "
        "nondimensional coefficients — a derivative value drops straight into "
        "a <font face='Courier'>&lt;value&gt;</font>, and a coefficient curve "
        "drops straight into a <font face='Courier'>&lt;table&gt;</font>."))

    heading("Choosing the axis system and reference point", 1, story)
    story.append(p(
        "Match JSBSim's axes to what CFD naturally reports. Forces from "
        "<font face='Courier'>forceCoeffs</font> are lift/drag/side (wind "
        "axes); moments are body-axis roll/pitch/yaw. So:"))
    for b in [
        "Forces &rarr; <font face='Courier'>&lt;axis name=\"LIFT\"&gt;</font>, "
        "<font face='Courier'>\"DRAG\"</font>, <font face='Courier'>\"SIDE\""
        "</font> (wind frame is the default when LIFT/DRAG are used; "
        "<font face='Courier'>FGAerodynamics.cpp:453-460</font>).",
        "Moments &rarr; <font face='Courier'>&lt;axis name=\"ROLL\"&gt;</font>,"
        " <font face='Courier'>\"PITCH\"</font>, <font face='Courier'>\"YAW\""
        "</font> (body frame by default; "
        "<font face='Courier'>FGAerodynamics.cpp:450-452</font>).",
        "Set OpenFOAM's <font face='Courier'>CofR</font> equal to the "
        "<font face='Courier'>&lt;metrics&gt;&lt;location name=\"AERORP\"&gt;"
        "</font> so the moment reference matches; otherwise transfer the "
        "moments (below).",
    ]:
        story.append(bullet(b))

    heading("The master mapping table", 1, story)
    story.append(p(
        "Each CFD coefficient becomes a <font face='Courier'>&lt;function&gt;"
        "</font> = (nondimensionalisers) &times; (coefficient). The "
        "nondimensionalisers are JSBSim properties; the coefficient is your "
        "CFD <font face='Courier'>&lt;table&gt;</font> or "
        "<font face='Courier'>&lt;value&gt;</font>."))
    qa = "<font face='Courier'>aero/qbar-area</font>"
    data = [
        ["Coefficient", "Axis", "JSBSim function = product of"],
        ["C<sub>L</sub>(" + A + ")", "LIFT",
         qa + " &times; table C<sub>L</sub>(" + A + ")"],
        ["C<sub>D</sub>(" + A + ")", "DRAG",
         qa + " &times; table C<sub>D</sub>(" + A + ")"],
        ["C<sub>Y</sub>(" + B + ")", "SIDE",
         qa + " &times; table C<sub>Y</sub>(" + B + ")"],
        ["C<sub>l</sub>(" + B + ")", "ROLL",
         qa + " &times; <font face='Courier'>bw-ft</font> &times; table"],
        ["C<sub>m</sub>(" + A + ")", "PITCH",
         qa + " &times; <font face='Courier'>cbarw-ft</font> &times; table"],
        ["C<sub>n</sub>(" + B + ")", "YAW",
         qa + " &times; <font face='Courier'>bw-ft</font> &times; table"],
        ["C<sub>mq</sub>", "PITCH",
         qa + " &times; <font face='Courier'>cbarw-ft</font> &times; "
         "<font face='Courier'>ci2vel</font> &times; "
         "<font face='Courier'>q-aero-rad_sec</font> &times; value"],
        ["C<sub>lp</sub>", "ROLL",
         qa + " &times; <font face='Courier'>bw-ft</font> &times; "
         "<font face='Courier'>bi2vel</font> &times; "
         "<font face='Courier'>p-aero-rad_sec</font> &times; value"],
        ["C<sub>nr</sub>", "YAW",
         qa + " &times; <font face='Courier'>bw-ft</font> &times; "
         "<font face='Courier'>bi2vel</font> &times; "
         "<font face='Courier'>r-aero-rad_sec</font> &times; value"],
    ]
    story.append(_oftab(data, [2.4 * cm, 1.8 * cm, 12.0 * cm]))

    heading("The key insight: the value IS the derivative", 1, story)
    story.append(p(
        "Because JSBSim builds the nondimensional rate internally (b/2V and "
        "c&#x0304;/2V via <font face='Courier'>bi2vel</font>/"
        "<font face='Courier'>ci2vel</font>, "
        "<font face='Courier'>FGAerodynamics.cpp:159-160</font>) and "
        "re-dimensionalises with " + _g("q̄") + "&middot;S and span/chord, the "
        "constant you place in the rate-derivative <font face='Courier'>"
        "&lt;value&gt;</font> is exactly the textbook nondimensional "
        "derivative. The c172 model makes this concrete — its roll-damping "
        "function is literally " + _g("q̄") + "S&middot;b&middot;(b/2V)"
        "&middot;p&middot;C<sub>lp</sub> with C<sub>lp</sub> = &minus;0.47 "
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
        "So your OpenFOAM-derived C<sub>lp</sub>, C<sub>mq</sub>, "
        "C<sub>nr</sub>, &hellip; go directly into the "
        "<font face='Courier'>&lt;value&gt;</font> slot. No further scaling."))

    heading("Static curves as tables", 1, story)
    story.append(p(
        "Tabulate each baseline coefficient against its primary variable, "
        "adding column/table dimensions for couplings (e.g. " + B + ", Mach, "
        "flap). The lift curve from an " + A + "-sweep, multiplied up to a "
        "force:"))
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
        "For a Mach-dependent dataset, add "
        "<font face='Courier'>&lt;independentVar lookup=\"column\"&gt;"
        "velocities/mach&lt;/independentVar&gt;</font> and supply a matrix; "
        "for " + A + "/" + B + "/Mach add a "
        "<font face='Courier'>lookup=\"table\"</font> third dimension with "
        "<font face='Courier'>&lt;tableData breakPoint=\"&hellip;\"&gt;"
        "</font> blocks."))

    heading("Control increments", 1, story)
    story.append(p(
        "Differencing a deflected-geometry run against the clean baseline "
        "gives &Delta;C per surface; tabulate against deflection so "
        "nonlinearity/saturation is captured:"))
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

    heading("Sign and axis conventions: the pitfalls", 1, story)
    story.append(p(
        "Most failures here are bookkeeping, not physics. Reconcile these "
        "before trusting the model:"))
    for b in [
        "<b>Drag sign.</b> CFD C<sub>D</sub> is positive (force opposing the "
        "wind). JSBSim's DRAG axis already points along the relative wind, so "
        "a positive value is correct drag — do not negate.",
        "<b>Body-axis directions.</b> Confirm your CFD body frame (x, y, z "
        "senses) matches JSBSim's structural-to-body convention; a flipped y "
        "or z silently inverts roll/yaw or pitch.",
        "<b>Moment reference transfer.</b> If <font face='Courier'>CofR &ne; "
        "AERORP</font>, shift the pitching moment. With normal force "
        "C<sub>N</sub>, axial force C<sub>A</sub>, and the AERORP a distance "
        "&Delta;x aft and &Delta;z above the CofR:",
    ]:
        story.append(bullet(b))
    math("C<sub>m,AERORP</sub> = C<sub>m,CofR</sub> + "
         "(C<sub>N</sub>&middot;&Delta;x &minus; C<sub>A</sub>&middot;&Delta;z)"
         " / c&#x0304;")
    for b in [
        "<b>Radians vs degrees.</b> Table independent variables use the "
        "property's native unit — <font face='Courier'>aero/alpha-rad</font> "
        "is radians, <font face='Courier'>aero/alpha-deg</font> degrees, "
        "<font face='Courier'>fcs/elevator-pos-rad</font> radians. Match your "
        "CFD breakpoints to the property you reference.",
        "<b>Reference area/length consistency.</b> The S, b, c&#x0304; in "
        "<font face='Courier'>&lt;metrics&gt;</font> must equal the "
        "<font face='Courier'>Aref</font>/<font face='Courier'>lRef</font> "
        "used in <font face='Courier'>forceCoeffs</font>.",
    ]:
        story.append(bullet(b))

    heading("Worked example: a complete CFD-derived axis set", 1, story)
    story.append(p(
        "Putting it together — a compact but complete "
        "<font face='Courier'>&lt;aerodynamics&gt;</font> skeleton populated "
        "entirely from CFD (baseline curves abbreviated):"))
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
        "Every <font face='Courier'>&lt;value&gt;</font> above is a "
        "nondimensional stability derivative straight from CFD; every "
        "<font face='Courier'>&lt;table&gt;</font> is a CFD sweep. Add control "
        "increments, ground effect and Mach dimensions as the data warrants."))


# ----------------------------------------------------------------------------
def add_of_automation(story):
    story.append(PageBreak())
    heading("Automating the OpenFOAM-to-JSBSim Pipeline", 0, story)
    story.append(p(
        "A real campaign is dozens to hundreds of runs; doing it by hand is "
        "error-prone and unreproducible. This chapter sketches a scriptable "
        "pipeline: template a base case over the condition matrix, run the "
        "solver, parse <font face='Courier'>coefficient.dat</font>, and emit "
        "JSBSim <font face='Courier'>&lt;function&gt;</font>/"
        "<font face='Courier'>&lt;table&gt;</font> XML."))

    heading("Case templating over the condition matrix", 1, story)
    story.append(p(
        "Keep one converged <font face='Courier'>baseCase/</font> and clone "
        "it per condition, rewriting only the freestream and "
        "<font face='Courier'>liftDir</font>/<font face='Courier'>dragDir"
        "</font>. A minimal Python driver:"))
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

    heading("Parsing the coefficients", 1, story)
    story.append(p(
        "Read the last row of <font face='Courier'>coefficient.dat</font> "
        "(skipping the <font face='Courier'>#</font> header) for each case:"))
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

    heading("Emitting JSBSim tables", 1, story)
    story.append(p(
        "Finally, format the parsed sweep as a JSBSim "
        "<font face='Courier'>&lt;function&gt;</font> with a "
        "<font face='Courier'>&lt;table&gt;</font>. Note the conversion of "
        "the " + _g("α") + " breakpoints to radians to match "
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

    heading("Tooling and reproducibility", 1, story)
    for b in [
        "<b>PyFoam</b>, <b>foamlib</b> and <b>openfoamparser</b> read/write "
        "OpenFOAM dictionaries and post-processing files robustly — prefer "
        "them over regex for production pipelines.",
        "<b>pandas</b>/<b>numpy</b> for sweep storage, polar fitting "
        "(C<sub>D0</sub>, Oswald e), and slope estimation "
        "(C<sub>L" + _g("α") + "</sub>, C<sub>m" + _g("α") + "</sub>).",
        "The <b>JSBSim Python module</b> (<font face='Courier'>import jsbsim"
        "</font>) lets the same script trim and exercise the generated model "
        "for immediate verification.",
        "Keep an <font face='Courier'>Allrun</font>/<font face='Courier'>"
        "Allclean</font>, pin the OpenFOAM version, and archive logs and "
        "<font face='Courier'>checkMesh</font> output so the dataset is "
        "auditable and re-runnable.",
    ]:
        story.append(bullet(b))


# ----------------------------------------------------------------------------
def add_of_verification(story):
    story.append(PageBreak())
    heading("Verification: Closing the CFD-JSBSim-Flight Loop", 0, story)
    story.append(p(
        "A model that loads without error is not a validated model. The last "
        "step is to confirm the JSBSim aircraft reproduces the CFD physics, "
        "behaves sensibly in trim and in its dynamic modes, and — where data "
        "exists — agrees with wind tunnel and flight. Treat it as a loop: each "
        "discrepancy points back to a specific table, sign or reference."))

    heading("Static checks: does it trim where CFD says it should", 1, story)
    for b in [
        "Trim the model (<font face='Courier'>FGTrim</font>, longitudinal "
        "mode) and confirm the trim " + _g("α") + " and elevator are physical "
        "and match the CFD operating point.",
        "Recover C<sub>m</sub>(" + _g("α") + ") from JSBSim by sweeping " +
        _g("α") + " with controls fixed and reading "
        "<font face='Courier'>aero/coefficient/*</font> or "
        "<font face='Courier'>moments/m-aero-lbsft</font>; the slope must "
        "match the CFD C<sub>m" + _g("α") + "</sub>.",
        "Locate the <b>neutral point</b> (where dC<sub>m</sub>/dC<sub>L</sub> "
        "= 0) and confirm the <b>static margin</b> (NP minus CG, in % MAC) is "
        "positive and consistent with the CFD-derived value.",
    ]:
        story.append(bullet(b))

    heading("Dynamic checks: linearise and compare the modes", 1, story)
    story.append(p(
        "Trim, apply small perturbations (or use a linearisation utility) and "
        "extract the eigenvalues, then compare against the analytic modes that "
        "the derivatives predict (see the eigenmodes chapter):"))
    for b in [
        "<b>Short-period</b> frequency/damping driven by C<sub>m" +
        _g("α") + "</sub> and C<sub>mq</sub>+C<sub>m" + _g("α̇") + "</sub> — a "
        "direct check on the pitch-damping derivative you extracted.",
        "<b>Phugoid</b> — low frequency, lightly damped; sensitive to drag and "
        "lift, hence to the static polar.",
        "<b>Dutch roll</b> from C<sub>n" + _g("β") + "</sub>, C<sub>nr</sub>, "
        "C<sub>l" + _g("β") + "</sub>; <b>roll subsidence</b> from "
        "C<sub>lp</sub>; <b>spiral</b> from C<sub>l" + _g("β") + "</sub>, "
        "C<sub>nr</sub>, C<sub>lr</sub>, C<sub>n" + _g("β") + "</sub>.",
        "A mode that is unstable when it should not be, or an order-of-"
        "magnitude-wrong frequency, almost always traces to a wrong sign or "
        "missing rate derivative.",
    ]:
        story.append(bullet(b))

    heading("Comparison against independent data", 1, story)
    story.append(p(
        "Rank your confidence: flight test &gt; wind tunnel &gt; high-fidelity "
        "CFD &gt; panel/VLM (AVL, XFLR5) &gt; empirical (DATCOM). Use the "
        "cheaper methods to bracket the CFD and the expensive data to correct "
        "it:"))
    for b in [
        "Cross-check C<sub>L" + _g("α") + "</sub>, C<sub>m" + _g("α") +
        "</sub>, C<sub>l" + _g("β") + "</sub>, C<sub>nr</sub>, &hellip; "
        "against AVL (vortex-lattice) and USAF DATCOM estimates — they should "
        "agree in sign and rough magnitude.",
        "Where wind-tunnel or flight data exists, tune the CFD-derived tables "
        "to match (Reynolds and trim-state corrections first).",
        "Blend sources explicitly: e.g. CFD for the nonlinear high-" +
        _g("α") + " lift, AVL for the linear derivatives, DATCOM for a "
        "derivative no run covered. Document the provenance of each number.",
    ]:
        story.append(bullet(b))

    heading("Extrapolation cautions", 1, story)
    for b in [
        "<b>Reynolds number.</b> Run CFD at flight Re; sub-scale Re shifts "
        "C<sub>D0</sub>, maximum lift and stall " + _g("α") + ".",
        "<b>Mach.</b> Incompressible coefficients are invalid past M~0.3-0.5; "
        "add a Mach table dimension for fast aircraft.",
        "<b>Beyond the data.</b> JSBSim extends tables by holding the end "
        "value flat (no extrapolation); ensure your tables span the full "
        "intended envelope, especially post-stall and large sideslip.",
        "<b>Rigid-body only.</b> CFD-on-CAD ignores aeroelastic deformation "
        "and unsteady/separated effects beyond the quasi-steady model.",
    ]:
        story.append(bullet(b))

    heading("The iteration loop", 1, story)
    story.append(p(
        "Verification is rarely one pass. The healthy workflow is: build "
        "tables from CFD &rarr; trim &rarr; check modes &rarr; compare to "
        "reference data &rarr; identify the worst discrepancy &rarr; add or "
        "correct the responsible CFD run or table &rarr; repeat. Because every "
        "coefficient is an isolated, observable "
        "<font face='Courier'>&lt;function&gt;</font> in the property tree, "
        "JSBSim makes this loop fast: you can watch each contribution "
        "live and pinpoint exactly which term is wrong."))
    story.append(quote(
        "A flight model is never finished, only progressively less wrong. CFD "
        "gets you a credible first model; trim, the eigenmodes, and real data "
        "tell you where to spend the next run."))


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
        title="The Ultimate JSBSim Reference",
        author="JSBSim project — distilled by Claude",
        subject="JSBSim FDM internals, XML schema, aerodynamics, and CFD workflow",
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
    )
    doc.multiBuild(story, canvasmaker=HeaderFooterCanvas)
    size = os.path.getsize(OUT_PATH)
    print(f"[3/3] Wrote {OUT_PATH} ({size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
