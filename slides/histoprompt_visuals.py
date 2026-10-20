from manim import (
    AnnularSector,
    Arc,
    Create,
    Circle,
    CubicBezier,
    Dot,
    FadeIn,
    GrowFromCenter,
    LaggedStart,
    Line,
    MoveAlongPath,
    RoundedRectangle,
    Scene,
    Text,
    VGroup,
    config,
)

from math import pi


config.pixel_width = 1920
config.pixel_height = 1080
config.frame_width = 14.222
config.frame_height = 8.0
config.background_color = "#0B201B"

FONT = "Avenir Next"
WHITE = "#F7F4EF"
MUTED = "#A9BBB5"
GRID = "#24433B"
GREEN = "#39D0B2"
PINK = "#F24A8D"
ORANGE = "#F39A4A"
PURPLE = "#A77BD4"
GOLD = "#F4CD70"
PAPER = "#F8F5F0"
INK = "#12211D"
LIGHT_MUTED = "#5D6B66"
LIGHT_LINE = "#D7DDD8"


def label(text, size, color=WHITE, weight="NORMAL"):
    return Text(text, font=FONT, font_size=size, color=color, weight=weight)


def pill(text, color):
    txt = label(text, 24, WHITE, "BOLD")
    box = RoundedRectangle(
        width=txt.width + 0.42,
        height=0.48,
        corner_radius=0.18,
        stroke_width=0,
        fill_color=color,
        fill_opacity=1,
    )
    return VGroup(box, txt)


class WorkflowPulse(Scene):
    def construct(self):
        self.camera.background_color = PAPER
        title = label("One clinical case. Five traceable stages.", 34, INK, "BOLD")
        title.to_edge([0, 1, 0], buff=0.30)
        subtitle = label(
            "The same traceable chain powers the app, saved demo, and 2,141-case benchmark",
            21,
            LIGHT_MUTED,
        ).next_to(title, [0, -1, 0], buff=0.12)

        stages = [
            ("1", "CASE", "image + findings", GREEN, [-5.25, 0.35, 0]),
            ("2", "RAG", "retrieve evidence", ORANGE, [-2.65, 0.95, 0]),
            ("3", "LUMEN", "candidate prompts", PINK, [0.00, 0.18, 0]),
            ("4", "COMPARE", "four model views", PURPLE, [2.72, -0.78, 0]),
            ("5", "REVIEW", "evidence + action", GREEN, [5.30, -0.12, 0]),
        ]

        paths = VGroup()
        pulses = []
        for i in range(len(stages) - 1):
            p1 = stages[i][4]
            p2 = stages[i + 1][4]
            path = CubicBezier(
                [p1[0] + 0.62, p1[1], 0],
                [p1[0] + 1.20, p1[1] + 0.30, 0],
                [p2[0] - 1.20, p2[1] - 0.30, 0],
                [p2[0] - 0.62, p2[1], 0],
            ).set_stroke("#8CB9AC", width=7, opacity=0.28)
            core = path.copy().set_stroke(stages[i + 1][3], width=2.6, opacity=0.95)
            paths.add(path, core)
            pulses.append((core, Dot(core.get_start(), radius=0.07, color=stages[i + 1][3])))

        nodes = VGroup()
        for number, head, body, color, pos in stages:
            halo = Circle(radius=0.74 if head == "LUMEN" else 0.61, stroke_width=10, stroke_color=color).set_stroke(opacity=0.10).move_to(pos)
            disk = Circle(radius=0.60 if head == "LUMEN" else 0.51, stroke_width=3, stroke_color=color).set_fill("#FFFFFF", opacity=1).move_to(pos)
            num = label(number, 25, color, "BOLD").move_to(pos)
            head_text = label(head, 18, color, "BOLD").move_to([pos[0], pos[1] - 0.84, 0])
            body_text = label(body, 16, LIGHT_MUTED, "BOLD").move_to([pos[0], pos[1] - 1.16, 0])
            nodes.add(VGroup(halo, disk, num, head_text, body_text))

        callout = RoundedRectangle(
            width=10.2,
            height=0.72,
            corner_radius=0.22,
            stroke_color=GREEN,
            stroke_width=2,
            fill_color="#FFFFFF",
            fill_opacity=1,
        ).move_to([0, -2.72, 0])
        callout_text = label(
            "Every score keeps its evidence and review path visible.",
            24,
            INK,
            "BOLD",
        ).move_to([0, -2.72, 0])
        source = label("Ground-truth labels were never sent to Lumen", 15, LIGHT_MUTED, "BOLD").move_to([0, -3.40, 0])

        self.play(FadeIn(title), FadeIn(subtitle))
        self.play(LaggedStart(*[Create(path) for path in paths], lag_ratio=0.06))
        self.play(LaggedStart(*[GrowFromCenter(node) for node in nodes], lag_ratio=0.10))
        for path, pulse in pulses:
            self.add(pulse)
            self.play(MoveAlongPath(pulse, path), run_time=0.22)
        self.play(FadeIn(callout), FadeIn(callout_text), FadeIn(source))
        self.wait(0.2)


class ScaleJourney(Scene):
    def construct(self):
        self.camera.background_color = PAPER
        title = label("The final benchmark covered 2,141 cases", 30, INK, "BOLD")
        title.to_edge([0, 1, 0], buff=0.30)
        subtitle = label(
            "Model coverage reached four; cancer coverage reached eight",
            21,
            LIGHT_MUTED,
        ).next_to(title, [0, -1, 0], buff=0.12)

        journey = [
            ("34", "screen", "4 clinical groups", GREEN, [-5.1, 0.60, 0], 0.46),
            ("600", "stress test", "3 balanced classes", ORANGE, [-2.1, 1.02, 0], 0.72),
            ("1,000", "model sweep", "4 hosted models", PURPLE, [1.05, 0.48, 0], 0.88),
            ("2,141", "full workflow", "8 TCGA cancers", PINK, [4.62, -0.10, 0], 1.14),
        ]

        path = CubicBezier([-5.1, 0.6, 0], [-2.6, 2.0, 0], [1.2, 0.30, 0], [4.62, -0.10, 0])
        path.set_stroke("#B4C8C1", width=5, opacity=0.58)
        orbit = path.copy().set_stroke(GREEN, width=2.2, opacity=0.95)

        nodes = VGroup()
        for value, head, body, color, pos, radius in journey:
            glow = Circle(radius=radius + 0.12, stroke_width=14, stroke_color=color).set_stroke(opacity=0.08).move_to(pos)
            disk = Circle(radius=radius, stroke_width=3, stroke_color=color).set_fill("#FFFFFF", opacity=1).move_to(pos)
            value_size = 29 if value != "2,141" else 34
            value_text = label(value, value_size, color, "BOLD").move_to([pos[0], pos[1] + 0.06, 0])
            head_text = label(head.upper(), 14, INK, "BOLD").move_to([pos[0], -1.52, 0])
            body_text = label(body, 14, LIGHT_MUTED, "BOLD").move_to([pos[0], -1.84, 0])
            nodes.add(VGroup(glow, disk, value_text, head_text, body_text))

        dimensions = [
            ("CASES", "34 → 2,141", GREEN),
            ("MODELS", "1 → 4", PURPLE),
            ("COVERAGE", "4 groups → 8 cancers", PINK),
        ]
        cards = VGroup()
        for i, (head, value, color) in enumerate(dimensions):
            x = -4.4 + i * 4.4
            box = RoundedRectangle(
                width=3.65,
                height=0.90,
                corner_radius=0.20,
                stroke_color=color,
                stroke_width=2,
                fill_color="#FFFFFF",
                fill_opacity=1,
            ).move_to([x, -2.68, 0])
            head_text = label(head, 13, color, "BOLD").move_to([x, -2.50, 0])
            value_text = label(value, 19, INK, "BOLD").move_to([x, -2.82, 0])
            cards.add(VGroup(box, head_text, value_text))

        result = label(
            "The full run identified six high-gain model–organ pairings.",
            20,
            GREEN,
            "BOLD",
        ).move_to([0, -3.38, 0])

        self.play(FadeIn(title), FadeIn(subtitle))
        self.play(Create(path), Create(orbit))
        self.play(LaggedStart(*[GrowFromCenter(node) for node in nodes], lag_ratio=0.12))
        marker = Dot(path.get_start(), radius=0.08, color=PINK)
        self.add(marker)
        self.play(MoveAlongPath(marker, path), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(card) for card in cards], lag_ratio=0.10), FadeIn(result))
        self.wait(0.2)


class RoutingMap(Scene):
    def construct(self):
        title = label("Six cancer contexts. Three model routes.", 32, WHITE, "BOLD")
        title.to_edge([0, 1, 0], buff=0.30)
        subtitle = label(
            "Each cancer context connects to the model with the largest observed gain",
            22,
            MUTED,
        ).next_to(title, [0, -1, 0], buff=0.12)

        stars = VGroup(*[
            Dot([x, y, 0], radius=r, color=GRID).set_opacity(0.55)
            for x, y, r in [
                (-6.6, 2.55, 0.025), (-5.8, -2.7, 0.035), (-3.7, 2.45, 0.020),
                (-2.9, -2.55, 0.024), (-1.8, 2.15, 0.030), (-0.8, -2.75, 0.022),
                (0.7, 2.35, 0.026), (1.8, -2.50, 0.034), (2.7, 2.30, 0.022),
                (4.0, -2.60, 0.026), (5.6, 2.38, 0.032), (6.5, -2.35, 0.022),
            ]
        ])

        left_head = label("CANCER CONTEXT", 17, MUTED, "BOLD").move_to([-5.05, 2.35, 0])
        right_head = label("ROUTE", 17, MUTED, "BOLD").move_to([5.02, 2.35, 0])

        organ_rows = [
            ("Colon", 1.92, "CONCH", "+28.4", GREEN),
            ("Prostate", 1.18, "CONCH", "+12.0", GREEN),
            ("Breast", 0.44, "QuiltNet", "+24.1", ORANGE),
            ("Lung squamous", -0.30, "QuiltNet", "+14.1", ORANGE),
            ("Rectal", -1.04, "MUSK", "+15.4", PINK),
            ("Kidney clear cell", -1.78, "MUSK", "+10.7", PINK),
        ]
        model_y = {"CONCH": 1.50, "QuiltNet": 0.05, "MUSK": -1.40}
        model_color = {"CONCH": GREEN, "QuiltNet": ORANGE, "MUSK": PINK}

        ribbons = VGroup()
        pulses = []
        for organ, y, model, gain, color in organ_rows:
            target_y = model_y[model]
            curve = CubicBezier(
                [-3.42, y, 0],
                [-1.55, y, 0],
                [1.65, target_y, 0],
                [3.92, target_y, 0],
            ).set_stroke(color, width=11, opacity=0.42)
            core = curve.copy().set_stroke(color, width=1.8, opacity=0.95)
            ribbons.add(curve, core)
            pulses.append((core, Dot([-3.42, y, 0], radius=0.065, color=WHITE)))

        hub_glow = VGroup(
            Circle(radius=0.92, stroke_width=1.5, stroke_color="#31584F").set_fill("#123129", opacity=0.75),
            Circle(radius=0.72, stroke_width=2.0, stroke_color=GOLD).set_fill("#0B201B", opacity=0.95),
            Circle(radius=0.55, stroke_width=0).set_fill("#173E35", opacity=1),
        ).move_to([0.15, 0.02, 0])
        hub_text = VGroup(
            label("HISTO", 22, WHITE, "BOLD"),
            label("PROMPT", 22, GOLD, "BOLD"),
        ).arrange([0, -1, 0], buff=0.02).move_to([0.15, 0.02, 0])

        organ_nodes = VGroup()
        for organ, y, model, gain, color in organ_rows:
            box = RoundedRectangle(
                width=3.00,
                height=0.52,
                corner_radius=0.18,
                stroke_color=color,
                stroke_width=1.8,
                fill_color="#123129",
                fill_opacity=1,
            ).move_to([-5.05, y, 0])
            txt = label(organ, 18, WHITE, "BOLD")
            if txt.width > 1.82:
                txt.scale_to_fit_width(1.82)
            txt.move_to([-5.42, y, 0])
            gain_text = label(gain, 17, color, "BOLD").move_to([-4.05, y, 0])
            organ_nodes.add(VGroup(box, txt, gain_text))

        model_nodes = VGroup()
        for model, y in model_y.items():
            color = model_color[model]
            glow = Circle(radius=0.65, stroke_width=10, stroke_color=color).set_stroke(opacity=0.12).move_to([5.02, y, 0])
            disk = Circle(radius=0.55, stroke_width=3, stroke_color=color).set_fill("#102A24", opacity=1).move_to([5.02, y, 0])
            txt = label(model, 22 if model != "QuiltNet" else 19, color, "BOLD").move_to(disk)
            model_nodes.add(VGroup(glow, disk, txt))

        source = label(
            "2,141 PathGen cases · eight TCGA projects · four hosted pathology models",
            17,
            MUTED,
        ).move_to([0, -3.32, 0])

        self.add(stars)
        self.play(FadeIn(title), FadeIn(subtitle), FadeIn(left_head), FadeIn(right_head))
        self.play(LaggedStart(*[Create(r) for r in ribbons], lag_ratio=0.04))
        self.play(GrowFromCenter(hub_glow), FadeIn(hub_text))
        self.play(LaggedStart(*[FadeIn(node) for node in organ_nodes], lag_ratio=0.08))
        self.play(LaggedStart(*[FadeIn(node) for node in model_nodes], lag_ratio=0.12))
        for path, pulse in pulses:
            self.add(pulse)
            self.play(MoveAlongPath(pulse, path), run_time=0.18)
        self.play(FadeIn(source))
        self.wait(0.2)


class GainTrajectories(Scene):
    def construct(self):
        title = label("Three pairings delivered the largest gains", 31, WHITE, "BOLD")
        title.to_edge([0, 1, 0], buff=0.30)
        subtitle = label(
            "Outer ring: case-specific accuracy · inner ring: baseline accuracy",
            20,
            MUTED,
        ).next_to(title, [0, -1, 0], buff=0.12)

        data = [
            ("Colon", "CONCH", 18.2, 46.7, "+28.4", "77 → 197 correct", GREEN),
            ("Breast", "QuiltNet", 11.6, 35.6, "+24.1", "25 → 77 correct", ORANGE),
            ("Rectal", "MUSK", 55.8, 71.2, "+15.4", "87 → 111 correct", PINK),
        ]

        legend_outer = VGroup(
            Line([-0.30, 0, 0], [0.18, 0, 0], stroke_width=12, color=GOLD),
            label("case-specific", 16, MUTED, "BOLD").next_to([0.22, 0, 0], [1, 0, 0], buff=0.08),
        )
        legend_inner = VGroup(
            Line([-0.30, 0, 0], [0.18, 0, 0], stroke_width=8, color="#67847B"),
            label("baseline", 16, MUTED, "BOLD").next_to([0.22, 0, 0], [1, 0, 0], buff=0.08),
        )
        legend = VGroup(legend_inner, legend_outer).arrange([1, 0, 0], buff=0.45).move_to([0, 2.40, 0])

        panels = VGroup()
        arcs_to_draw = []
        for i, (organ, model, before, after, gain, counts, color) in enumerate(data):
            x = -4.55 + i * 4.55
            y = -0.12
            halo = Circle(radius=1.58, stroke_width=1.5, stroke_color=GRID).set_fill("#102A24", opacity=0.52).move_to([x, y, 0])
            outer_bg = Arc(radius=1.26, start_angle=-pi / 2, angle=2 * pi, stroke_width=18, color=GRID).move_arc_center_to([x, y, 0])
            inner_bg = Arc(radius=0.94, start_angle=-pi / 2, angle=2 * pi, stroke_width=11, color="#29483F").move_arc_center_to([x, y, 0])
            outer_glow = Arc(radius=1.26, start_angle=-pi / 2, angle=2 * pi * after / 100, stroke_width=30, color=color).set_stroke(opacity=0.13).move_arc_center_to([x, y, 0])
            outer = Arc(radius=1.26, start_angle=-pi / 2, angle=2 * pi * after / 100, stroke_width=18, color=color).move_arc_center_to([x, y, 0])
            inner = Arc(radius=0.94, start_angle=-pi / 2, angle=2 * pi * before / 100, stroke_width=11, color="#7E9990").move_arc_center_to([x, y, 0])
            heading = label(f"{organ} · {model}", 23, WHITE, "BOLD").move_to([x, 1.78, 0])
            gain_txt = label(gain, 35, color, "BOLD").move_to([x, y + 0.15, 0])
            gain_cap = label("POINT LIFT", 15, MUTED, "BOLD").move_to([x, y - 0.35, 0])
            percentages = label(f"{before:.1f}%  →  {after:.1f}%", 20, WHITE, "BOLD").move_to([x, -1.95, 0])
            count_txt = label(counts, 17, MUTED, "BOLD").move_to([x, -2.34, 0])
            panels.add(VGroup(halo, outer_bg, inner_bg, heading, gain_txt, gain_cap, percentages, count_txt))
            arcs_to_draw.append((outer_glow, outer, inner))

        takeaway = label(
            "Colon → CONCH   ·   Breast → QuiltNet   ·   Rectal → MUSK",
            24,
            GOLD,
            "BOLD",
        ).move_to([0, -2.95, 0])
        source = label(
            "Saved 2,141-case clinician-workflow benchmark",
            18,
            MUTED,
        ).move_to([0, -3.40, 0])

        self.play(FadeIn(title), FadeIn(subtitle), FadeIn(legend))
        self.play(LaggedStart(*[FadeIn(panel) for panel in panels], lag_ratio=0.12))
        for outer_glow, outer, inner in arcs_to_draw:
            self.play(Create(inner), Create(outer_glow), Create(outer), run_time=0.50)
        self.play(FadeIn(takeaway), FadeIn(source))
        self.wait(0.2)
