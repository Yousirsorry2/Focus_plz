"""Mochi the cat, drawn as pure vector art with QPainter (no image assets)."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ui.theme import COCOA, MINT, PEACH

FUR = QColor("#FFF6EE")
FUR_PATCH = QColor(PEACH)
INNER_EAR = QColor("#FFC2A6")
LINE = QColor(COCOA)

ART_W, ART_H = 220.0, 170.0   # logical drawing canvas


class MochiCat(QWidget):
    """mode='sleeping' (Focus Mode) or mode='alert' (Focus Guard popup)."""

    def __init__(self, mode="sleeping", width=220, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.setFixedSize(int(width), int(width * ART_H / ART_W))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    # ---- helpers ------------------------------------------------------
    @staticmethod
    def _outline(p, w=2.6):
        pen = QPen(LINE, w)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)

    @staticmethod
    def _tri(a, b, c):
        path = QPainterPath(QPointF(*a))
        path.lineTo(*b)
        path.lineTo(*c)
        path.closeSubpath()
        return path

    def _ears(self, p, left, right):
        """left/right: (base1, tip, base2) triangles."""
        for tri in (left, right):
            self._outline(p)
            p.setBrush(FUR)
            p.drawPath(self._tri(*tri))
            (x1, y1), (tx, ty), (x2, y2) = tri
            inner = self._tri(((x1 * 2 + tx) / 3 + 1, (y1 * 2 + ty) / 3),
                              (tx, ty + (y1 - ty) * 0.35),
                              ((x2 * 2 + tx) / 3 - 1, (y2 * 2 + ty) / 3))
            p.setPen(Qt.NoPen)
            p.setBrush(INNER_EAR)
            p.drawPath(inner)

    # ---- painting -----------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = min(self.width() / ART_W, self.height() / ART_H)
        p.translate((self.width() - ART_W * s) / 2, (self.height() - ART_H * s) / 2)
        p.scale(s, s)

        # soft halo behind the cat
        halo = QColor(MINT if self.mode == "sleeping" else PEACH)
        halo.setAlpha(110)
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QRectF(24, 12, 172, 150))

        (self._draw_sleeping if self.mode == "sleeping" else self._draw_alert)(p)
        p.end()

    def _draw_sleeping(self, p):
        # tail curling around the back
        tail = QPainterPath(QPointF(160, 128))
        tail.cubicTo(196, 130, 206, 100, 186, 92)
        p.setBrush(Qt.NoBrush)
        pen = QPen(LINE, 17)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawPath(tail)
        pen = QPen(FUR, 12.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawPath(tail)

        # body (loaf) with a peach patch clipped inside
        body = QPainterPath()
        body.addEllipse(QRectF(40, 80, 128, 78))
        p.save()
        p.setClipPath(body)
        p.fillPath(body, FUR)
        patch = QPainterPath()
        patch.addEllipse(QRectF(104, 70, 70, 44))
        p.fillPath(patch, FUR_PATCH)
        p.restore()
        self._outline(p)
        p.setBrush(Qt.NoBrush)
        p.drawPath(body)

        # ears, then head
        self._ears(p, ((50, 88), (54, 52), (78, 74)), ((88, 72), (112, 52), (116, 90)))
        self._outline(p)
        p.setBrush(FUR)
        p.drawEllipse(QRectF(44, 70, 78, 70))

        # sleeping face
        self._outline(p, 2.4)
        p.setBrush(Qt.NoBrush)
        for x in (62, 92):
            eye = QPainterPath(QPointF(x, 104))
            eye.quadTo(x + 8, 112, x + 16, 104)
            p.drawPath(eye)
        p.setPen(Qt.NoPen)
        p.setBrush(INNER_EAR)
        p.drawPath(self._tri((79, 113), (87, 113), (83, 118)))
        blush = QColor(PEACH)
        blush.setAlpha(190)
        p.setBrush(blush)
        p.drawEllipse(QRectF(52, 111, 13, 8))
        p.drawEllipse(QRectF(100, 111, 13, 8))
        self._outline(p, 2.0)
        mouth = QPainterPath(QPointF(76, 120))
        mouth.quadTo(80, 124, 83, 119)
        mouth.quadTo(86, 124, 90, 120)
        p.setBrush(Qt.NoBrush)
        p.drawPath(mouth)

        # front paws tucked under the chin
        self._outline(p, 2.2)
        p.setBrush(FUR)
        p.drawEllipse(QRectF(58, 130, 26, 16))
        p.drawEllipse(QRectF(88, 130, 26, 16))

        # floating z's
        for txt, x, y, size, a in (("z", 128, 62, 15, 190), ("Z", 144, 44, 20, 150)):
            f = QFont("Segoe UI", 1)
            f.setPixelSize(size)
            f.setBold(True)
            p.setFont(f)
            c = QColor(COCOA)
            c.setAlpha(a)
            p.setPen(c)
            p.drawText(QPointF(x, y), txt)

    def _draw_alert(self, p):
        # tail
        tail = QPainterPath(QPointF(138, 140))
        tail.cubicTo(184, 146, 192, 104, 170, 100)
        p.setBrush(Qt.NoBrush)
        for w, col in ((17, LINE), (12.5, FUR)):
            pen = QPen(col, w)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawPath(tail)

        # sitting body
        self._outline(p)
        p.setBrush(FUR)
        p.drawEllipse(QRectF(66, 98, 88, 66))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(94, 120, 32, 40))       # belly
        self._outline(p, 2.2)
        p.setBrush(FUR)
        p.drawEllipse(QRectF(80, 146, 26, 16))       # paws
        p.drawEllipse(QRectF(114, 146, 26, 16))

        # ears + head
        self._ears(p, ((70, 58), (74, 18), (98, 40)), ((122, 40), (146, 18), (150, 58)))
        self._outline(p)
        p.setBrush(FUR)
        p.drawEllipse(QRectF(64, 30, 92, 82))

        # forehead patch
        p.setPen(Qt.NoPen)
        p.setBrush(FUR_PATCH)
        p.drawChord(QRectF(92, 32, 36, 26), 0 * 16, 180 * 16)

        # wide-open curious eyes with highlights
        p.setBrush(LINE)
        for x in (88, 120):
            p.drawEllipse(QRectF(x, 62, 13, 17))
        p.setBrush(QColor("#FFFFFF"))
        for x in (92, 124):
            p.drawEllipse(QRectF(x, 65, 5, 6))
        # one raised brow for the gentle "hey…?"
        self._outline(p, 2.0)
        p.setBrush(Qt.NoBrush)
        brow = QPainterPath(QPointF(116, 57))
        brow.quadTo(126, 51, 136, 57)
        p.drawPath(brow)

        # nose, mouth, blush, whiskers
        p.setPen(Qt.NoPen)
        p.setBrush(INNER_EAR)
        p.drawPath(self._tri((105, 86), (115, 86), (110, 92)))
        blush = QColor(PEACH)
        blush.setAlpha(190)
        p.setBrush(blush)
        p.drawEllipse(QRectF(74, 84, 13, 8))
        p.drawEllipse(QRectF(133, 84, 13, 8))
        self._outline(p, 2.0)
        p.setBrush(Qt.NoBrush)
        mouth = QPainterPath(QPointF(104, 96))
        mouth.quadTo(107, 100, 110, 94)
        mouth.quadTo(113, 100, 116, 96)
        p.drawPath(mouth)
        thin = QColor(COCOA)
        thin.setAlpha(150)
        p.setPen(QPen(thin, 1.4, Qt.SolidLine, Qt.RoundCap))
        for dy, d2 in ((0, -3), (6, 3)):
            p.drawLine(QPointF(70, 90 + dy), QPointF(52, 90 + dy + d2))
            p.drawLine(QPointF(150, 90 + dy), QPointF(168, 90 + dy + d2))
