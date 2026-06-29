import sys
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QFrame, QHeaderView
)

from atis_clean.data import make_row, all_rows, SAMPLE, set_data_mode, get_data_mode, market_diagnostics
from atis_clean.market_data.provider import market_data_engine
from atis_clean.scanner.engine import preset_names, scan_rows, scanner_report
from atis_clean.chart_widget import ChartWidget

STYLE = """
QMainWindow{background:#070d14;}
QWidget{background:#070d14;color:white;font-family:Segoe UI;}
QFrame#panel{background:#0f1a25;border:1px solid #30465d;border-radius:10px;}
QFrame#decision{background:#0d1924;border:2px solid #28c7fa;border-radius:12px;}
QLabel#title{font-size:30px;font-weight:900;letter-spacing:1px;}
QLabel#sub{color:#9fb2c3;font-size:12px;font-weight:600;}
QLabel#decisionTicker{font-size:31px;font-weight:900;}
QLabel#decisionAction{font-size:25px;font-weight:900;color:#28c7fa;}
QLineEdit{background:#02070c;border:2px solid #28c7fa;color:white;padding:10px;font-size:17px;border-radius:8px;}
QPushButton{background:#1c2d3e;color:white;border:1px solid #3a526b;border-radius:8px;padding:9px 13px;font-weight:800;}
QPushButton:hover{background:#2a4055;border:1px solid #28c7fa;}
QTextEdit{background:#03080d;border:1px solid #30465d;color:white;padding:10px;font-size:13px;border-radius:8px;}
QTableWidget{background:#07101a;gridline-color:#26384a;border:1px solid #30465d;border-radius:8px;font-size:12px;}
QHeaderView::section{background:#162537;color:white;font-weight:800;padding:6px;border:1px solid #30465d;}
QTabWidget::pane{border:1px solid #30465d;border-radius:8px;}
QTabBar::tab{background:#101b27;color:white;padding:10px 16px;border:1px solid #30465d;min-width:118px;font-weight:700;}
QTabBar::tab:selected{background:#1f2e3d;color:#28c7fa;border-bottom:2px solid #28c7fa;}
"""

class ATISClean(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ATIS CLEAN OPERATIONAL v1.4.1 - Phase 4 Startup Hotfix")
        self.resize(1600, 930)
        self.rows = market_data_engine.all_rows()
        self.selected = None
        self.syncing = False
        self.scanner_results = []
        self.build()
        self.load_symbol("NVDA")

    def panel(self, title):
        frame = QFrame()
        frame.setObjectName("panel")
        layout = QVBoxLayout(frame)
        label = QLabel(title)
        label.setStyleSheet("font-size:16px;font-weight:900;color:#28c7fa;padding-bottom:4px;")
        layout.addWidget(label)
        return frame, layout

    def make_readonly(self, widget):
        try:
            widget.setReadOnly(True)
        except Exception:
            pass
        return widget

    def build(self):
        root = QWidget()
        main = QVBoxLayout(root)
        main.setContentsMargins(12, 10, 12, 10)

        top = QHBoxLayout()
        titlebox = QVBoxLayout()
        title = QLabel("ATIS PRO")
        title.setObjectName("title")
        sub = QLabel("ATIS CLEAN v1.4.1 • PHASE 4 STARTUP HOTFIX • ONE SEARCH CONTROLS EVERYTHING")
        sub.setObjectName("sub")
        titlebox.addWidget(title)
        titlebox.addWidget(sub)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Type ticker: TSLA, NVDA, SLV, AAPL, GDX, HL, AG...")
        self.search.returnPressed.connect(self.search_now)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.search_now)
        self.search.textEdited.connect(lambda _: self.search_timer.start(600))

        search_btn = QPushButton("Search / Load")
        search_btn.clicked.connect(self.search_now)

        self.data_mode = QComboBox()
        self.data_mode.addItems(["Fallback", "Live"])
        self.data_mode.currentTextChanged.connect(self.change_data_mode)

        top.addLayout(titlebox, 2)
        top.addWidget(QLabel("Symbol:"))
        top.addWidget(self.search, 5)
        top.addWidget(QLabel("Data:"))
        top.addWidget(self.data_mode)
        top.addWidget(search_btn)
        main.addLayout(top)

        self.decision = QFrame()
        self.decision.setObjectName("decision")
        dl = QHBoxLayout(self.decision)
        self.dec_ticker = QLabel("NO SYMBOL")
        self.dec_ticker.setObjectName("decisionTicker")
        self.dec_action = QLabel("WAITING")
        self.dec_action.setObjectName("decisionAction")
        self.dec_stats = QLabel("--")
        self.dec_stats.setStyleSheet("font-size:15px;font-weight:700;")
        dl.addWidget(self.dec_ticker, 2)
        dl.addWidget(self.dec_action, 2)
        dl.addWidget(self.dec_stats, 5)
        main.addWidget(self.decision)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.dashboard_tab(), "Dashboard")
        self.tabs.addTab(self.trading_tab(), "Trading")
        self.tabs.addTab(self.explorer_tab(), "Explorer")
        self.tabs.addTab(self.ai_tab(), "AI Analyst")
        self.tabs.addTab(self.scanner_tab(), "Scanner")
        self.tabs.addTab(self.decision_30_tab(), "Decision 3.0")
        self.tabs.addTab(self.scanner_intel_tab(), "Scanner Intel")
        self.tabs.addTab(self.portfolio_tab(), "Portfolio")
        self.tabs.addTab(self.journal_tab(), "Journal")
        self.tabs.addTab(self.alerts_tab(), "Alerts")
        self.tabs.addTab(self.news_tab(), "News")
        self.tabs.addTab(self.data_tab(), "Data Provider")
        main.addWidget(self.tabs)

        self.status = QLabel("Ready • Type a ticker at the top and ATIS updates every tab")
        self.status.setObjectName("sub")
        main.addWidget(self.status)
        self.setCentralWidget(root)

    def dashboard_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        p1, l1 = self.panel("Global Symbol Command Summary")
        self.summary = self.make_readonly(QTextEdit())
        l1.addWidget(self.summary)
        p2, l2 = self.panel("Ranked Opportunity Queue")
        self.top_table = QTableWidget()
        self.top_table.setColumnCount(5)
        self.top_table.setHorizontalHeaderLabels(["Rank", "Ticker", "Score", "Action", "Status"])
        self.top_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.top_table.itemSelectionChanged.connect(self.table_selected)
        l2.addWidget(self.top_table)
        layout.addWidget(p1, 2)
        layout.addWidget(p2, 3)
        return page

    def trading_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        left, ll = self.panel("Watchlist")
        self.watch = QTableWidget()
        self.watch.setColumnCount(5)
        self.watch.setHorizontalHeaderLabels(["Rank", "Ticker", "Score", "Action", "Status"])
        self.watch.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.watch.itemSelectionChanged.connect(self.table_selected)
        ll.addWidget(self.watch)
        center, cl = self.panel("Professional Chart Workspace")
        self.chart = ChartWidget()
        cl.addWidget(self.chart, 5)
        self.chart_info = self.make_readonly(QTextEdit())
        self.chart_info.setMaximumHeight(160)
        cl.addWidget(self.chart_info)
        right, rl = self.panel("AI Decision Details")
        self.decision_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.decision_text)
        layout.addWidget(left, 2)
        layout.addWidget(center, 5)
        layout.addWidget(right, 3)
        return page

    def explorer_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        p, l = self.panel("Explorer")
        self.explorer = self.make_readonly(QTextEdit())
        l.addWidget(self.explorer)
        layout.addWidget(p)
        return page

    def ai_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        p1, l1 = self.panel("AI Reasoning")
        self.ai_reasoning = self.make_readonly(QTextEdit())
        l1.addWidget(self.ai_reasoning)
        p2, l2 = self.panel("AI Trade Plan")
        self.ai_plan = self.make_readonly(QTextEdit())
        l2.addWidget(self.ai_plan)
        layout.addWidget(p1, 2)
        layout.addWidget(p2, 2)
        return page


    def decision_30_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        left, ll = self.panel("Decision Engine 3.0")
        self.decision_30_text = self.make_readonly(QTextEdit())
        ll.addWidget(self.decision_30_text)

        right, rl = self.panel("Decision Checklist")
        self.decision_checklist = QTableWidget()
        self.decision_checklist.setColumnCount(3)
        self.decision_checklist.setHorizontalHeaderLabels(["Rule", "Status", "Weight"])
        self.decision_checklist.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rl.addWidget(self.decision_checklist)

        layout.addWidget(left, 2)
        layout.addWidget(right, 2)
        return page

    def scanner_intel_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        left, ll = self.panel("Scanner Intelligence Report")
        self.scanner_intel_text = self.make_readonly(QTextEdit())
        ll.addWidget(self.scanner_intel_text)

        right, rl = self.panel("Opportunity Buckets")
        self.scanner_intel_table = QTableWidget()
        self.scanner_intel_table.setColumnCount(5)
        self.scanner_intel_table.setHorizontalHeaderLabels(["Rank", "Ticker", "Score", "Bucket", "Action"])
        self.scanner_intel_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.scanner_intel_table.itemSelectionChanged.connect(self.scanner_intel_selected)
        rl.addWidget(self.scanner_intel_table)

        layout.addWidget(left, 2)
        layout.addWidget(right, 3)
        return page

    def portfolio_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        left, ll = self.panel("Portfolio Watch")
        self.portfolio_table = QTableWidget()
        self.portfolio_table.setColumnCount(5)
        self.portfolio_table.setHorizontalHeaderLabels(["Ticker", "Name", "Price", "Action", "Status"])
        self.portfolio_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.portfolio_table.itemSelectionChanged.connect(self.portfolio_selected)
        ll.addWidget(self.portfolio_table)

        right, rl = self.panel("Position Intelligence")
        self.portfolio_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.portfolio_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)
        return page

    def journal_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        left, ll = self.panel("Paper Trade Journal")
        self.journal_table = QTableWidget()
        self.journal_table.setColumnCount(5)
        self.journal_table.setHorizontalHeaderLabels(["Ticker", "Decision", "Entry", "Stop", "Target"])
        self.journal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ll.addWidget(self.journal_table)

        right, rl = self.panel("Journal Notes")
        self.journal_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.journal_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)
        return page

    def alerts_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        left, ll = self.panel("Alerts")
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(4)
        self.alerts_table.setHorizontalHeaderLabels(["Ticker", "Alert", "Level", "Status"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ll.addWidget(self.alerts_table)

        right, rl = self.panel("Alert Explanation")
        self.alerts_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.alerts_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)
        return page

    def news_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        left, ll = self.panel("News Intelligence")
        self.news_text = self.make_readonly(QTextEdit())
        ll.addWidget(self.news_text)

        right, rl = self.panel("Catalyst Checklist")
        self.news_table = QTableWidget()
        self.news_table.setColumnCount(3)
        self.news_table.setHorizontalHeaderLabels(["Ticker", "Catalyst", "Signal"])
        self.news_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rl.addWidget(self.news_table)

        layout.addWidget(left, 2)
        layout.addWidget(right, 2)
        return page

    def scanner_intel_selected(self):
        if not hasattr(self, "scanner_intel_table"):
            return
        r = self.scanner_intel_table.currentRow()
        if r >= 0:
            item = self.scanner_intel_table.item(r, 1)
            if item:
                self.load_symbol(item.text())

    def portfolio_selected(self):
        if not hasattr(self, "portfolio_table"):
            return
        r = self.portfolio_table.currentRow()
        if r >= 0:
            item = self.portfolio_table.item(r, 0)
            if item:
                self.load_symbol(item.text())


    def scanner_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        controls, ctl = self.panel("Professional Scanner Controls")
        row = QHBoxLayout()
        self.scanner_preset = QComboBox()
        self.scanner_preset.addItems(preset_names())
        self.scanner_preset.currentTextChanged.connect(self.run_professional_scanner)

        self.scanner_min_score = QComboBox()
        self.scanner_min_score.addItems(["Preset", "0", "40", "55", "70", "85"])
        self.scanner_min_score.currentTextChanged.connect(self.run_professional_scanner)

        self.scanner_min_rvol = QComboBox()
        self.scanner_min_rvol.addItems(["Preset", "0", "1", "2", "3"])
        self.scanner_min_rvol.currentTextChanged.connect(self.run_professional_scanner)

        scan_btn = QPushButton("Run Scanner")
        scan_btn.clicked.connect(self.run_professional_scanner)

        row.addWidget(QLabel("Preset:"))
        row.addWidget(self.scanner_preset)
        row.addWidget(QLabel("Min Score:"))
        row.addWidget(self.scanner_min_score)
        row.addWidget(QLabel("Min RVOL:"))
        row.addWidget(self.scanner_min_rvol)
        row.addWidget(scan_btn)
        row.addStretch()
        ctl.addLayout(row)
        layout.addWidget(controls)

        body = QHBoxLayout()
        left, ll = self.panel("Scanner Results")
        self.scanner = QTableWidget()
        self.scanner.setColumnCount(8)
        self.scanner.setHorizontalHeaderLabels(["Rank", "Ticker", "Name", "Score", "Change %", "RVOL", "Bucket", "Action"])
        self.scanner.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.scanner.itemSelectionChanged.connect(self.scanner_selected)
        ll.addWidget(self.scanner)

        right, rl = self.panel("Scanner Intelligence")
        self.scanner_report_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.scanner_report_text)

        body.addWidget(left, 4)
        body.addWidget(right, 2)
        layout.addLayout(body)
        return page


    def run_professional_scanner(self):
        if not hasattr(self, "scanner"):
            return

        preset = self.scanner_preset.currentText() if hasattr(self, "scanner_preset") else "Day Trade"
        custom = {}

        if hasattr(self, "scanner_min_score") and self.scanner_min_score.currentText() != "Preset":
            custom["min_score"] = float(self.scanner_min_score.currentText())

        if hasattr(self, "scanner_min_rvol") and self.scanner_min_rvol.currentText() != "Preset":
            custom["min_rvol"] = float(self.scanner_min_rvol.currentText())

        self.scanner_results = scan_rows(self.rows, preset=preset, custom=custom)
        self.scanner.blockSignals(True)
        self.scanner.setRowCount(len(self.scanner_results))

        for r, row in enumerate(self.scanner_results):
            vals = [
                row.get("scanner_rank", r + 1),
                row.get("ticker", ""),
                row.get("name", ""),
                row.get("score", ""),
                row.get("change_pct", ""),
                row.get("relative_volume", ""),
                row.get("scanner_bucket", ""),
                row.get("action", ""),
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                self.scanner.setItem(r, c, item)

            if self.selected and row.get("ticker") == self.selected.get("ticker"):
                self.scanner.selectRow(r)

        self.scanner.blockSignals(False)

        if hasattr(self, "scanner_report_text"):
            self.scanner_report_text.setPlainText(scanner_report(self.scanner_results, preset))

        self.status.setText(f"Scanner complete: {len(self.scanner_results)} matches using {preset} preset.")

    def data_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        p, l = self.panel("Data Provider")
        self.data_text = self.make_readonly(QTextEdit())
        self.data_text.setPlainText(market_diagnostics())
        l.addWidget(self.data_text)
        layout.addWidget(p)
        return page


    def bucket_for_row(self, row):
        score = row.get("score", 0)
        if score >= 85:
            return "High Conviction"
        if score >= 70:
            return "Momentum"
        if score >= 55:
            return "Watch"
        return "Avoid"

    def update_additional_tabs(self, row):
        if hasattr(self, "decision_30_text"):
            self.decision_30_text.setPlainText(
                f"DECISION ENGINE 3.0 — {row['ticker']}\n\n"
                f"Action: {row['action']}\nProbability: {row['probability']}%\n"
                f"Confidence: {row['confidence']}\nScore: {row['score']}/100\n\n"
                f"Entry: ${row['entry']}\nStop: ${row['stop']}\n"
                f"Target 1: ${row['target1']}\nTarget 2: ${row['target2']}\n"
                f"Risk/Reward: {row['risk_reward']}"
            )

        if hasattr(self, "decision_checklist"):
            rules = [
                ("Momentum", row["change_pct"] >= 1, 12),
                ("RVOL 2x+", row["relative_volume"] >= 2, 15),
                ("Above VWAP", row["above_vwap"], 15),
                ("Above 9 EMA", row["above_9ema"], 12),
                ("Above 20 EMA", row["above_20ema"], 12),
                ("News catalyst", row["news"], 8),
                ("New intraday high", row["new_intraday_high"], 13),
            ]
            self.decision_checklist.setRowCount(len(rules))
            for r, (rule, passed, weight) in enumerate(rules):
                for c, v in enumerate([rule, "PASS" if passed else "WAIT", weight]):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.decision_checklist.setItem(r, c, item)

        if hasattr(self, "scanner_intel_text"):
            self.scanner_intel_text.setPlainText(
                f"SCANNER INTELLIGENCE — {row['ticker']}\n\n"
                f"Bucket: {self.bucket_for_row(row)}\nScore: {row['score']}/100\nScanner Preset: {self.scanner_preset.currentText() if hasattr(self, 'scanner_preset') else 'N/A'}\n"
                f"Change: {row['change_pct']}%\nRVOL: {row['relative_volume']}x\n\n"
                f"Passed:\n{chr(10).join(['✓ ' + x for x in row['passed']]) or 'None'}\n\n"
                f"Missing:\n{chr(10).join(['⚠ ' + x for x in row['missing']]) or 'None'}"
            )

        if hasattr(self, "scanner_intel_table"):
            rows = sorted(self.rows, key=lambda x: x["score"], reverse=True)
            self.scanner_intel_table.blockSignals(True)
            self.scanner_intel_table.setRowCount(len(rows))
            for r, item_row in enumerate(rows):
                vals = [r + 1, item_row["ticker"], item_row["score"], self.bucket_for_row(item_row), item_row["action"]]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.scanner_intel_table.setItem(r, c, item)
                if item_row["ticker"] == row["ticker"]:
                    self.scanner_intel_table.selectRow(r)
            self.scanner_intel_table.blockSignals(False)

        if hasattr(self, "portfolio_table"):
            self.portfolio_table.blockSignals(True)
            self.portfolio_table.setRowCount(len(self.rows))
            for r, item_row in enumerate(self.rows):
                vals = [item_row["ticker"], item_row["name"], item_row["price"], item_row["action"], item_row["status"]]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.portfolio_table.setItem(r, c, item)
                if item_row["ticker"] == row["ticker"]:
                    self.portfolio_table.selectRow(r)
            self.portfolio_table.blockSignals(False)

        if hasattr(self, "portfolio_text"):
            self.portfolio_text.setPlainText(
                f"POSITION INTELLIGENCE — {row['ticker']}\n\n"
                f"Current price: ${row['price']}\nAction: {row['action']}\n"
                f"Status: {row['status']}\nRisk/Reward: {row['risk_reward']}"
            )

        if hasattr(self, "journal_table"):
            self.journal_table.setRowCount(1)
            for c, v in enumerate([row["ticker"], row["action"], row["entry"], row["stop"], row["target1"]]):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                self.journal_table.setItem(0, c, item)

        if hasattr(self, "journal_text"):
            self.journal_text.setPlainText(
                f"JOURNAL READY — {row['ticker']}\n\n"
                f"Decision: {row['action']}\nEntry: ${row['entry']}\n"
                f"Stop: ${row['stop']}\nTarget: ${row['target1']}"
            )

        if hasattr(self, "alerts_table"):
            alerts = [
                ("Entry", row["entry"], "Watching"),
                ("Stop", row["stop"], "Risk"),
                ("Target 1", row["target1"], "Target"),
                ("VWAP", row["vwap"], "Context"),
            ]
            self.alerts_table.setRowCount(len(alerts))
            for r, (name, level, status) in enumerate(alerts):
                for c, v in enumerate([row["ticker"], name, level, status]):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.alerts_table.setItem(r, c, item)

        if hasattr(self, "alerts_text"):
            self.alerts_text.setPlainText(
                f"ALERTS — {row['ticker']}\n\n"
                f"Entry: ${row['entry']}\nStop: ${row['stop']}\n"
                f"Target 1: ${row['target1']}\nVWAP: ${row['vwap']}"
            )

        if hasattr(self, "news_text"):
            catalyst = "News catalyst detected" if row["news"] else "No major catalyst in fallback data"
            self.news_text.setPlainText(f"NEWS INTELLIGENCE — {row['ticker']}\n\n{catalyst}")

        if hasattr(self, "data_text"):
            self.data_text.setPlainText(market_diagnostics())

        if hasattr(self, "news_table"):
            self.news_table.setRowCount(1)
            vals = [row["ticker"], "Catalyst" if row["news"] else "No catalyst", "Bullish" if row["news"] else "Neutral"]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                self.news_table.setItem(0, c, item)

    def scanner_intel_selected(self):
        r = self.scanner_intel_table.currentRow()
        if r >= 0:
            item = self.scanner_intel_table.item(r, 1)
            if item:
                self.load_symbol(item.text())

    def portfolio_selected(self):
        r = self.portfolio_table.currentRow()
        if r >= 0:
            item = self.portfolio_table.item(r, 0)
            if item:
                self.load_symbol(item.text())

    def change_data_mode(self, mode):
        """
        Change provider mode safely.

        Do not immediately re-fetch every symbol in Live mode. That caused UI
        freezes. The selected ticker will refresh only when the user presses
        Search / Load or Enter.
        """
        set_data_mode(mode)
        self.rows = market_data_engine.all_rows()
        self.update_tables()
        if hasattr(self, "data_text"):
            self.data_text.setPlainText(market_diagnostics())
        self.status.setText(
            f"Data mode changed to {get_data_mode().upper()}. Press Search / Load to refresh the current ticker."
        )

    def search_now(self):
        self.load_symbol(self.search.text())

    def load_symbol(self, symbol):
        symbol = (symbol or "").strip().upper()
        if not symbol:
            return
        row, error = market_data_engine.get_row(symbol)
        if not row:
            self.status.setText(error)
            return

        self.rows = market_data_engine.all_rows()
        self.selected = row
        # Keep searched row available even if it is not in fallback watchlist.
        if not any(r["ticker"] == row["ticker"] for r in self.rows):
            row["rank"] = 1
            self.rows.insert(0, row)
        if self.search.text().strip().upper() != symbol:
            self.search.blockSignals(True)
            self.search.setText(symbol)
            self.search.blockSignals(False)

        self.update_tables()
        self.update_all_panels(row)
        self.status.setText(f"{symbol} loaded across ATIS.")

    def update_tables(self):
        for table in [self.watch, self.top_table]:
            table.blockSignals(True)
            table.setRowCount(len(self.rows))
            for r, row in enumerate(self.rows):
                vals = [row["rank"], row["ticker"], row["score"], row["action"], row["status"]]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(r, c, item)
                if self.selected and row["ticker"] == self.selected["ticker"]:
                    table.selectRow(r)
            table.blockSignals(False)

        if hasattr(self, "scanner"):
            self.run_professional_scanner()

    def table_selected(self):
        table = self.sender()
        r = table.currentRow()
        if 0 <= r < len(self.rows):
            ticker = table.item(r, 1).text()
            self.load_symbol(ticker)

    def scanner_selected(self):
        r = self.scanner.currentRow()
        if 0 <= r < len(getattr(self, "scanner_results", [])):
            ticker = self.scanner_results[r]["ticker"]
            self.load_symbol(ticker)

    def update_all_panels(self, row):
        self.dec_ticker.setText(row["ticker"])
        self.dec_action.setText(row["action"])
        self.dec_stats.setText(
            f"Probability {row['probability']}% | Confidence {row['confidence']} | "
            f"Entry ${row['entry']} | Stop ${row['stop']} | Target ${row['target1']} | R/R {row['risk_reward']}"
        )

        text = self.row_report(row)
        self.summary.setPlainText(text)
        self.decision_text.setPlainText(text)
        self.explorer.setPlainText(text)
        self.ai_reasoning.setPlainText(self.ai_report(row))
        self.ai_plan.setPlainText(self.trade_plan(row))
        self.chart.set_row(row)
        self.chart_info.setPlainText(
            f"{row['ticker']} chart loaded.\n"
            f"Price: ${row['price']}\nVWAP: ${row['vwap']}\n"
            f"Entry: ${row['entry']} | Stop: ${row['stop']} | Target 1: ${row['target1']}"
        )
        self.update_additional_tabs(row)

    def row_report(self, row):
        return f"""SYMBOL: {row['ticker']} — {row['name']}

Price: ${row['price']}
Change: {row['change_pct']}%
Volume: {row['volume']:,}
Relative Volume: {row['relative_volume']}x
Source: {row['data_source']}

Decision: {row['action']}
Status: {row['status']}
Score: {row['score']}/100
Probability: {row['probability']}%
Confidence: {row['confidence']}

Passed:
{chr(10).join(['✓ ' + x for x in row['passed']]) or 'None'}

Missing:
{chr(10).join(['⚠ ' + x for x in row['missing']]) or 'None'}
"""

    def ai_report(self, row):
        return f"""AI REASONING — {row['ticker']}

ATIS says: {row['action']}

Why:
{chr(10).join(['✓ ' + x for x in row['passed']]) or 'None'}

What is missing:
{chr(10).join(['⚠ ' + x for x in row['missing']]) or 'None'}

Guidance:
Use this as a paper-trading support tool. Do not chase entries. Wait for confirmation.
"""

    def trade_plan(self, row):
        return f"""TRADE PLAN — {row['ticker']}

Entry: ${row['entry']}
Stop: ${row['stop']}
Target 1: ${row['target1']}
Target 2: ${row['target2']}

Risk/Reward: {row['risk_reward']}

Operational note:
This clean version is focused on making the platform functional and synchronized.
"""

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = ATISClean()
    window.show()
    sys.exit(app.exec())
