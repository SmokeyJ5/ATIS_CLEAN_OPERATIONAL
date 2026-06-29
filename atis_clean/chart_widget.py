from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
from PySide6.QtWidgets import QWidget

class ChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.row = None
        self.setMinimumHeight(430)

    def set_row(self, row):
        self.row = row
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(3, 8, 13))

        if not self.row:
            painter.setPen(QPen(Qt.white))
            painter.drawText(self.rect(), Qt.AlignCenter, "Search a ticker to load chart")
            return

        candles = self.row.get("candles", [])
        if not candles:
            painter.setPen(QPen(Qt.white))
            painter.drawText(self.rect(), Qt.AlignCenter, "No chart data")
            return

        area = QRectF(64, 42, max(10, self.width() - 135), max(10, self.height() - 105))
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        lo, hi = min(lows), max(highs)
        pad = max((hi - lo) * 0.08, 0.01)
        lo -= pad
        hi += pad
        rng = max(hi - lo, 0.01)
        n = len(candles)

        def y(value):
            return area.bottom() - ((value - lo) / rng) * area.height()

        def x(i):
            return area.left() + i * area.width() / max(n - 1, 1)

        painter.setPen(QPen(QColor(42, 61, 80), 1))
        for i in range(6):
            yy = area.top() + i * area.height() / 5
            painter.drawLine(QPointF(area.left(), yy), QPointF(area.right(), yy))

        candle_w = max(4, area.width() / max(n, 1) * 0.65)
        for i, c in enumerate(candles):
            xx = x(i)
            up = c["close"] >= c["open"]
            color = QColor(46, 230, 107) if up else QColor(255, 77, 77)
            painter.setPen(QPen(color, 1))
            painter.drawLine(QPointF(xx, y(c["high"])), QPointF(xx, y(c["low"])))
            top = min(y(c["open"]), y(c["close"]))
            h = max(abs(y(c["close"]) - y(c["open"])), 2)
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(xx - candle_w / 2, top, candle_w, h))

        used_slots = set()

        def line(label, value, color):
            if not value:
                return
            yy = y(value)
            painter.setPen(QPen(color, 2, Qt.DashLine))
            painter.drawLine(QPointF(area.left(), yy), QPointF(area.right(), yy))
            slot = int((yy - area.top()) / 20)
            while slot in used_slots:
                slot += 1
            used_slots.add(slot)
            label_y = max(int(area.top()) + 14, min(int(area.top()) + slot * 20 + 14, int(area.bottom()) - 4))
            painter.drawText(int(area.right() - 175), label_y, f"{label}: {value}")

        line("VWAP", self.row.get("vwap"), QColor(255, 216, 77))
        line("Entry", self.row.get("entry"), QColor(255, 255, 255))
        line("Stop", self.row.get("stop"), QColor(255, 77, 77))
        line("Target", self.row.get("target1"), QColor(40, 199, 250))

        painter.setPen(QPen(Qt.white))
        painter.drawText(64, 26, f"{self.row['ticker']} Candlestick Chart  •  Source: {self.row.get('data_source')}")
        painter.drawText(64, self.height() - 16, f"Low {lo:.2f}    High {hi:.2f}    Price {self.row['price']}    VWAP {self.row.get('vwap')}")
