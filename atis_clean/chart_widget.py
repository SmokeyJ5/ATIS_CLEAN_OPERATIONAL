from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import QWidget


class ChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.row = None
        self.timeframe = "5m"
        self.show_vwap = True
        self.show_trade_plan = True
        self.show_levels = True
        self.show_volume = True
        self.setMinimumHeight(460)

    def set_row(self, row):
        self.row = row
        self.update()

    def set_timeframe(self, timeframe):
        self.timeframe = timeframe or "5m"
        self.update()

    def set_overlays(self, *, vwap=True, trade_plan=True, levels=True, volume=True):
        self.show_vwap = bool(vwap)
        self.show_trade_plan = bool(trade_plan)
        self.show_levels = bool(levels)
        self.show_volume = bool(volume)
        self.update()

    def _price_to_y(self, value, area, low, high):
        rng = max(high - low, 0.01)
        return area.bottom() - ((value - low) / rng) * area.height()

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

        try:
            candles = [
                {
                    "open": float(c.get("open", 0.0)),
                    "high": float(c.get("high", 0.0)),
                    "low": float(c.get("low", 0.0)),
                    "close": float(c.get("close", 0.0)),
                    "volume": int(c.get("volume", 0)),
                }
                for c in candles
                if isinstance(c, dict)
            ]
        except (TypeError, ValueError):
            painter.setPen(QPen(Qt.white))
            painter.drawText(self.rect(), Qt.AlignCenter, "Chart data unavailable")
            return

        header_h = 34
        footer_h = 22
        volume_h = 70 if self.show_volume else 0
        chart_area = QRectF(64, header_h + 16, max(10, self.width() - 145), max(10, self.height() - header_h - footer_h - volume_h - 34))
        vol_area = QRectF(chart_area.left(), chart_area.bottom() + 12, chart_area.width(), max(0, volume_h - 16))

        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        low, high = min(lows), max(highs)
        pad = max((high - low) * 0.10, 0.01)
        low -= pad
        high += pad

        n = len(candles)

        def x(i):
            return chart_area.left() + i * chart_area.width() / max(n - 1, 1)

        def y(v):
            return self._price_to_y(v, chart_area, low, high)

        # Header
        painter.setPen(QPen(QColor(220, 235, 245)))
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(64, 25, f"{self.row['ticker']} Professional Chart  •  {self.timeframe}  •  {self.row.get('data_source', '')}")

        # Grid and price scale
        painter.setFont(QFont())
        painter.setPen(QPen(QColor(38, 57, 76), 1))
        for i in range(6):
            yy = chart_area.top() + i * chart_area.height() / 5
            painter.drawLine(QPointF(chart_area.left(), yy), QPointF(chart_area.right(), yy))
            price_label = high - i * (high - low) / 5
            painter.setPen(QPen(QColor(138, 160, 180)))
            painter.drawText(int(chart_area.right() + 6), int(yy + 4), f"{price_label:.2f}")
            painter.setPen(QPen(QColor(38, 57, 76), 1))

        for i in range(0, n, max(1, n // 8)):
            xx = x(i)
            painter.drawLine(QPointF(xx, chart_area.top()), QPointF(xx, chart_area.bottom()))

        # Candles
        candle_w = max(4, min(12, chart_area.width() / max(n, 1) * 0.64))
        for i, c in enumerate(candles):
            xx = x(i)
            up = c["close"] >= c["open"]
            color = QColor(51, 226, 126) if up else QColor(255, 82, 82)
            painter.setPen(QPen(color, 1))
            painter.drawLine(QPointF(xx, y(c["high"])), QPointF(xx, y(c["low"])))
            top = min(y(c["open"]), y(c["close"]))
            body_h = max(abs(y(c["close"]) - y(c["open"])), 2)
            painter.setBrush(QBrush(color))
            painter.drawRect(QRectF(xx - candle_w / 2, top, candle_w, body_h))

        # Volume bars
        if self.show_volume and vol_area.height() > 0:
            max_vol = max([c.get("volume", 0) for c in candles] or [1])
            painter.setPen(Qt.NoPen)
            for i, c in enumerate(candles):
                xx = x(i)
                up = c["close"] >= c["open"]
                color = QColor(51, 226, 126, 130) if up else QColor(255, 82, 82, 130)
                h = (c.get("volume", 0) / max_vol) * vol_area.height() if max_vol else 0
                painter.setBrush(QBrush(color))
                painter.drawRect(QRectF(xx - candle_w / 2, vol_area.bottom() - h, candle_w, h))

        # Overlay line helper with label collision prevention
        used_slots = set()

        def draw_level(label, value, color, dashed=True):
            if value in (None, 0, ""):
                return
            try:
                value = float(value)
            except Exception:
                return
            yy = y(value)
            if yy < chart_area.top() or yy > chart_area.bottom():
                return
            pen = QPen(color, 2, Qt.DashLine if dashed else Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(QPointF(chart_area.left(), yy), QPointF(chart_area.right(), yy))
            slot = int((yy - chart_area.top()) / 19)
            while slot in used_slots:
                slot += 1
            used_slots.add(slot)
            label_y = max(int(chart_area.top()) + 14, min(int(chart_area.top()) + slot * 19 + 14, int(chart_area.bottom()) - 4))
            painter.setPen(QPen(color))
            painter.drawText(int(chart_area.right() - 175), label_y, f"{label}: {value:.2f}")

        if self.show_vwap:
            draw_level("VWAP", self.row.get("vwap"), QColor(255, 216, 77), dashed=False)
        if self.show_trade_plan:
            draw_level("Entry", self.row.get("entry"), QColor(240, 245, 255))
            draw_level("Stop", self.row.get("stop"), QColor(255, 82, 82))
            draw_level("Target 1", self.row.get("target1"), QColor(40, 199, 250))
            draw_level("Target 2", self.row.get("target2"), QColor(95, 220, 255))
        if self.show_levels:
            draw_level("Low", self.row.get("day_low"), QColor(160, 170, 185))
            draw_level("High", self.row.get("day_high"), QColor(160, 170, 185))

        # Current price marker
        price = self.row.get("price")
        if price:
            yy = y(price)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawLine(QPointF(chart_area.right() - 55, yy), QPointF(chart_area.right(), yy))
            painter.drawText(int(chart_area.right() - 55), int(yy - 6), f"{price:.2f}")

        # Footer
        painter.setPen(QPen(QColor(175, 190, 205)))
        painter.drawText(
            64,
            self.height() - 12,
            f"Price {self.row.get('price')}    Change {self.row.get('change_pct')}%    RVOL {self.row.get('relative_volume')}x    Score {self.row.get('score')}/100"
        )
