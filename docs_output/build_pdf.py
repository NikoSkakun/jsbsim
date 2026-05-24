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
    fontName="Courier", fontSize=8.2, leading=10.5,
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
