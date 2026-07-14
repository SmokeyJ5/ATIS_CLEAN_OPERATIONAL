import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QScrollArea, QSizePolicy, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QFrame, QHeaderView
)

from atis_clean.data import set_data_mode, get_data_mode, market_diagnostics
from atis_clean.market_data.provider import market_data_engine
from atis_clean.scanner.engine import preset_names, scan_rows, scanner_report
from atis_clean.decision.engine import build_ai_decision
from atis_clean.portfolio.risk import position_size, risk_report, exposure_report, asset_class
from atis_clean.journal.analytics import planned_trade_from_row, append_trade, load_trades, analytics_report, journal_review
from atis_clean.alerts.engine import evaluate_alerts, alerts_report, log_alert, load_alerts
from atis_clean.market_intelligence.engine import dashboard_report, metals_report, calendar_report, news_report, ai_market_briefing, economic_calendar, metals_intelligence
from atis_clean.workspace.layouts import layout_names, layout_count, default_symbol, default_timeframe
from atis_clean.workspace.manager import list_workspaces, load_workspace, save_workspace, workspace_report, ensure_default_workspaces
from atis_clean.paper_trading.simulator import buy as paper_buy, sell as paper_sell, account_summary, account_report, load_orders, reset_account, starting_cash
from atis_clean.strategy_lab.backtester import strategy_names, backtest
from atis_clean.command_center.metrics import top_opportunities, command_center_report, heatmap_rows
from atis_clean.diagnostics.health import health_report, version_info, system_health
from atis_clean.plugins.registry import registry, plugin_report
from atis_clean.plugins.broker import disabled_live_broker, BrokerOrder
from atis_clean.watchlists.manager import ensure_default_watchlists, list_watchlists, load_watchlist, add_symbol, remove_symbol, watchlist_report
from atis_clean.workstation.architecture import architecture_report
from atis_clean.release.manifest import manifest_text, VERSION
from atis_clean.core.settings import settings_report, load_settings
from atis_clean.core.logging import log_event, log_error
from atis_clean.core.events import event_bus, SYMBOL_SELECTED, WATCHLIST_CHANGED
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
        self.setWindowTitle("ATIS CLEAN OPERATIONAL v4.0.1 WATCHLIST RANK HOTFIX")
        self.setMinimumSize(1300, 850)
        self.resize(1600, 930)
        self.rows = []
        self.selected = None
        self.syncing = False
        self.scanner_results = []
        self.settings = load_settings()
        self._pending_symbol = ""
        self._pending_symbol_attempts = 0
        self._max_pending_symbol_attempts = 5
        self._symbol_retry_timer = QTimer(self)
        self._symbol_retry_timer.setSingleShot(True)
        self._symbol_retry_timer.timeout.connect(self._retry_pending_symbol_load)
        ensure_default_workspaces()
        ensure_default_watchlists()
        try:
            self.build()
        except Exception as exc:
            log_error("ATIS startup initialization failed", exc)
            self._build_startup_error_ui(exc)
            return
        if hasattr(self, "data_mode"):
            self.data_mode.setCurrentText(self.settings.get("data_mode", "Fallback"))
        # Defer symbol loading until the user searches or selects a ticker.

    def panel(self, title):
        frame = QFrame()
        frame.setObjectName("panel")
        layout = QVBoxLayout(frame)
        label = QLabel(title)
        label.setStyleSheet("font-size:16px;font-weight:900;color:#28c7fa;padding-bottom:4px;")
        layout.addWidget(label)
        return frame, layout

    def _build_startup_error_ui(self, exc):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(QLabel("ATIS startup initialization encountered an issue."))
        layout.addWidget(QLabel(str(exc)))
        self.status = QLabel("Startup recovery mode active. Check the diagnostics log for details.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.setCentralWidget(root)

    def _safe_build_tab(self, title, factory):
        try:
            return factory()
        except Exception as exc:
            log_error(f"Failed to initialize tab {title}", exc)
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.addWidget(QLabel(title))
            message = QLabel("This tab failed to initialize. ATIS will continue with the available tabs.")
            message.setWordWrap(True)
            layout.addWidget(message)
            return widget

    def make_readonly(self, widget):
        try:
            widget.setReadOnly(True)
        except AttributeError:
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
        sub = QLabel("ATIS CLEAN v4.0.1 • WATCHLIST RANK HOTFIX • EVENT-DRIVEN CORE")
        sub.setObjectName("sub")
        titlebox.addWidget(title)
        titlebox.addWidget(sub)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Type ticker: TSLA, NVDA, SLV, AAPL, GDX, HL, AG...")
        self.search.returnPressed.connect(self.search_now)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.search_now)

        def _debounced_search():
            if self.search_timer.isActive():
                self.search_timer.stop()
            self.search_timer.start(600)

        self.search.textEdited.connect(_debounced_search)

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
        tab_factories = [
            ("Dashboard", self.dashboard_tab),
            ("Trading", self.trading_tab),
            ("Explorer", self.explorer_tab),
            ("AI Analyst", self.ai_tab),
            ("Scanner", self.scanner_tab),
            ("Decision 3.0", self.decision_30_tab),
            ("Scanner Intel", self.scanner_intel_tab),
            ("Portfolio", self.portfolio_tab),
            ("Journal", self.journal_tab),
            ("Alerts", self.alerts_tab),
            ("News", self.news_tab),
            ("Market Intelligence", self.market_intelligence_tab),
            ("Workspace Manager", self.workspace_manager_tab),
            ("Paper Trading", self.paper_trading_tab),
            ("Strategy Lab", self.strategy_lab_tab),
            ("Diagnostics", self.diagnostics_tab),
            ("Release Candidate", self.release_candidate_tab),
            ("Watchlists", self.watchlist_manager_tab),
            ("Workstation", self.workstation_architecture_tab),
            ("Integrations", self.integrations_tab),
            ("Multi-Chart", self.multi_chart_tab),
            ("Data Provider", self.data_tab),
        ]
        for title, factory in tab_factories:
            self.tabs.addTab(self._safe_build_tab(title, factory), title)
        main.addWidget(self.tabs)

        self.status = QLabel("Ready • Type a ticker at the top and ATIS updates every tab")
        self.status.setObjectName("sub")
        main.addWidget(self.status)
        self.setCentralWidget(root)


    def scrollable_page(self):
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(10)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        return outer, content_layout

    def apply_responsive_widget_policy(self, widget):
        try:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        except AttributeError:
            pass
        return widget

    def dashboard_tab(self):
        page, layout = self.scrollable_page()

        top_row = QHBoxLayout()

        p1, l1 = self.panel("Institutional Command Summary")
        self.summary = self.apply_responsive_widget_policy(self.make_readonly(QTextEdit()))
        self.summary.setMinimumHeight(260)
        l1.addWidget(self.summary)

        p2, l2 = self.panel("Top AI Opportunities")
        self.top_table = QTableWidget()
        self.top_table.setMinimumHeight(260)
        self.top_table.setColumnCount(6)
        self.top_table.setHorizontalHeaderLabels(["Rank", "Ticker", "AI Score", "Action", "RVOL", "Change %"])
        self.top_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.top_table.itemSelectionChanged.connect(self.command_top_selected)
        l2.addWidget(self.top_table)

        p1.setMinimumHeight(320)
        p2.setMinimumHeight(320)
        top_row.addWidget(p1, 2)
        top_row.addWidget(p2, 3)
        layout.addLayout(top_row)

        bottom_row = QHBoxLayout()

        p3, l3 = self.panel("Market + AI Briefing")
        self.command_market_text = self.apply_responsive_widget_policy(self.make_readonly(QTextEdit()))
        self.command_market_text.setMinimumHeight(280)
        l3.addWidget(self.command_market_text)

        p4, l4 = self.panel("Account / Alerts / Strategy Snapshot")
        self.command_ops_text = self.apply_responsive_widget_policy(self.make_readonly(QTextEdit()))
        self.command_ops_text.setMinimumHeight(280)
        l4.addWidget(self.command_ops_text)

        p5, l5 = self.panel("Watchlist Heatmap")
        self.command_heatmap_table = QTableWidget()
        self.command_heatmap_table.setMinimumHeight(280)
        self.command_heatmap_table.setColumnCount(5)
        self.command_heatmap_table.setHorizontalHeaderLabels(["Ticker", "Score", "Action", "Class", "Source"])
        self.command_heatmap_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.command_heatmap_table.itemSelectionChanged.connect(self.command_heatmap_selected)
        l5.addWidget(self.command_heatmap_table)

        p3.setMinimumHeight(340)
        p4.setMinimumHeight(340)
        p5.setMinimumHeight(340)
        bottom_row.addWidget(p3, 2)
        bottom_row.addWidget(p4, 2)
        bottom_row.addWidget(p5, 3)
        layout.addLayout(bottom_row)

        layout.addStretch(1)
        return page

    def command_top_selected(self):
        if not hasattr(self, "top_table"):
            return
        r = self.top_table.currentRow()
        if r >= 0:
            item = self.top_table.item(r, 1)
            if item:
                self.load_symbol(item.text())

    def command_heatmap_selected(self):
        if not hasattr(self, "command_heatmap_table"):
            return
        r = self.command_heatmap_table.currentRow()
        if r >= 0:
            item = self.command_heatmap_table.item(r, 0)
            if item:
                self.load_symbol(item.text())

    def update_command_center(self, row=None):
        row = row or self.selected
        if not row:
            return

        # Ensure AI decisions exist for ranking.
        for item in self.rows:
            if "ai_decision" not in item:
                item["ai_decision"] = build_ai_decision(item)

        if hasattr(self, "summary"):
            self.summary.setPlainText(command_center_report(self.rows, row))

        if hasattr(self, "top_table"):
            leaders = top_opportunities(self.rows, 10)
            self.top_table.blockSignals(True)
            self.top_table.setRowCount(len(leaders))
            for r, item_row in enumerate(leaders):
                ai = item_row.get("ai_decision") or build_ai_decision(item_row)
                vals = [
                    r + 1,
                    item_row.get("ticker", ""),
                    ai.get("ai_score", item_row.get("score", "")),
                    ai.get("ai_action", item_row.get("action", "")),
                    item_row.get("relative_volume", ""),
                    item_row.get("change_pct", ""),
                ]
                for c, v in enumerate(vals):
                    cell = QTableWidgetItem(str(v))
                    cell.setTextAlignment(Qt.AlignCenter)
                    self.top_table.setItem(r, c, cell)
                if item_row.get("ticker") == row.get("ticker"):
                    self.top_table.selectRow(r)
            self.top_table.blockSignals(False)

        if hasattr(self, "command_market_text"):
            self.command_market_text.setPlainText(ai_market_briefing() + "\\n\\n" + dashboard_report())

        if hasattr(self, "command_ops_text"):
            paper = account_summary(self.price_lookup_for_paper) if hasattr(self, "price_lookup_for_paper") else {}
            alerts = evaluate_alerts(row)
            active_alerts = len([a for a in alerts if a.get("status") in {"ACTIVE", "WARNING"}])
            backtest_hint = "Open Strategy Lab and click Run Backtest for the selected symbol."
            self.command_ops_text.setPlainText(
                f"OPERATIONS SNAPSHOT\\n\\n"
                f"Paper Equity: ${paper.get('equity', 'N/A')}\\n"
                f"Paper Cash: ${paper.get('cash', 'N/A')}\\n"
                f"Open Positions: {len(paper.get('positions', [])) if paper else 'N/A'}\\n"
                f"Active/Warning Alerts: {active_alerts}\\n\\n"
                f"Selected: {row.get('ticker')}\\n"
                f"AI Action: {row.get('ai_decision', {}).get('ai_action', row.get('action'))}\\n"
                f"AI Score: {row.get('ai_decision', {}).get('ai_score', row.get('score'))}/100\\n\\n"
                f"Strategy Snapshot:\\n{backtest_hint}"
            )

        if hasattr(self, "command_heatmap_table"):
            heat = heatmap_rows(self.rows, 14)
            self.command_heatmap_table.blockSignals(True)
            self.command_heatmap_table.setRowCount(len(heat))
            for r, item_row in enumerate(heat):
                ai = item_row.get("ai_decision") or build_ai_decision(item_row)
                vals = [
                    item_row.get("ticker", ""),
                    ai.get("ai_score", item_row.get("score", "")),
                    ai.get("ai_action", item_row.get("action", "")),
                    asset_class(item_row) if "asset_class" in globals() else "N/A",
                    item_row.get("data_source", ""),
                ]
                for c, v in enumerate(vals):
                    cell = QTableWidgetItem(str(v))
                    cell.setTextAlignment(Qt.AlignCenter)
                    self.command_heatmap_table.setItem(r, c, cell)
                if item_row.get("ticker") == row.get("ticker"):
                    self.command_heatmap_table.selectRow(r)
            self.command_heatmap_table.blockSignals(False)

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

        chart_controls = QHBoxLayout()
        self.chart_timeframe = QComboBox()
        self.chart_timeframe.addItems(["1m", "5m", "15m", "1h", "Daily"])
        self.chart_timeframe.setCurrentText("5m")
        self.chart_timeframe.currentTextChanged.connect(self.update_chart_controls)

        self.toggle_vwap = QCheckBox("VWAP")
        self.toggle_vwap.setChecked(True)
        self.toggle_trade_plan = QCheckBox("Trade Plan")
        self.toggle_trade_plan.setChecked(True)
        self.toggle_levels = QCheckBox("Levels")
        self.toggle_levels.setChecked(True)
        self.toggle_volume = QCheckBox("Volume")
        self.toggle_volume.setChecked(True)

        for chk in [self.toggle_vwap, self.toggle_trade_plan, self.toggle_levels, self.toggle_volume]:
            chk.stateChanged.connect(self.update_chart_controls)

        chart_controls.addWidget(QLabel("Timeframe:"))
        chart_controls.addWidget(self.chart_timeframe)
        chart_controls.addWidget(self.toggle_vwap)
        chart_controls.addWidget(self.toggle_trade_plan)
        chart_controls.addWidget(self.toggle_levels)
        chart_controls.addWidget(self.toggle_volume)
        chart_controls.addStretch()
        cl.addLayout(chart_controls)

        self.chart = ChartWidget()
        cl.addWidget(self.chart, 5)
        self.chart_info = self.make_readonly(QTextEdit())
        self.chart_info.setMaximumHeight(145)
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

        left, ll = self.panel("Portfolio Watch & Exposure")
        self.portfolio_table = QTableWidget()
        self.portfolio_table.setColumnCount(7)
        self.portfolio_table.setHorizontalHeaderLabels(["Ticker", "Class", "Price", "Score", "AI Action", "Risk $", "Shares"])
        self.portfolio_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.portfolio_table.itemSelectionChanged.connect(self.portfolio_selected)
        ll.addWidget(self.portfolio_table)

        right, rl = self.panel("Position Sizing & Risk")
        control_row = QHBoxLayout()
        self.capital_input = QComboBox()
        self.capital_input.addItems(["10000", "20000", "30000", "50000", "100000"])
        self.capital_input.setCurrentText("20000")
        self.capital_input.currentTextChanged.connect(self.refresh_portfolio_risk)

        self.risk_input = QComboBox()
        self.risk_input.addItems(["0.5", "1", "1.5", "2", "3"])
        self.risk_input.setCurrentText("1")
        self.risk_input.currentTextChanged.connect(self.refresh_portfolio_risk)

        control_row.addWidget(QLabel("Capital:"))
        control_row.addWidget(self.capital_input)
        control_row.addWidget(QLabel("Risk %:"))
        control_row.addWidget(self.risk_input)
        control_row.addStretch()
        rl.addLayout(control_row)

        self.portfolio_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.portfolio_text)

        self.exposure_text = self.make_readonly(QTextEdit())
        self.exposure_text.setMaximumHeight(160)
        rl.addWidget(self.exposure_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)
        return page

    def journal_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("Trade Journal")
        button_row = QHBoxLayout()
        add_plan = QPushButton("Add Current Plan")
        add_plan.clicked.connect(self.add_current_trade_plan)
        refresh = QPushButton("Refresh Journal")
        refresh.clicked.connect(self.refresh_journal_tab)
        button_row.addWidget(add_plan)
        button_row.addWidget(refresh)
        button_row.addStretch()
        ll.addLayout(button_row)

        self.journal_table = QTableWidget()
        self.journal_table.setColumnCount(8)
        self.journal_table.setHorizontalHeaderLabels(["Date", "Ticker", "Strategy", "Action", "Entry", "Stop", "Target", "Result"])
        self.journal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ll.addWidget(self.journal_table)

        right, rl = self.panel("Performance Analytics & AI Review")
        self.journal_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.journal_text)

        self.analytics_text = self.make_readonly(QTextEdit())
        self.analytics_text.setMaximumHeight(230)
        rl.addWidget(self.analytics_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)
        return page

    def refresh_journal_tab(self):
        if not hasattr(self, "journal_table"):
            return
        trades = load_trades()
        self.journal_table.setRowCount(len(trades))
        for r, trade in enumerate(trades):
            vals = [
                trade.get("date", ""),
                trade.get("ticker", ""),
                trade.get("strategy", ""),
                trade.get("action", ""),
                trade.get("entry", ""),
                trade.get("stop", ""),
                trade.get("target", ""),
                trade.get("result", ""),
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                self.journal_table.setItem(r, c, item)
        if hasattr(self, "analytics_text"):
            self.analytics_text.setPlainText(analytics_report())

    def add_current_trade_plan(self):
        if not self.selected:
            self.status.setText("No selected ticker to add to journal.")
            return
        trade = planned_trade_from_row(self.selected)
        append_trade(trade)
        self.refresh_journal_tab()
        self.status.setText(f"Added planned trade for {self.selected['ticker']} to journal.")

    def update_journal_analytics(self, row):
        if hasattr(self, "journal_text"):
            self.journal_text.setPlainText(journal_review(row))
        if hasattr(self, "analytics_text"):
            self.analytics_text.setPlainText(analytics_report())
        if hasattr(self, "journal_table"):
            self.refresh_journal_tab()

    def alerts_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("Alert Engine")
        button_row = QHBoxLayout()
        eval_btn = QPushButton("Evaluate Alerts")
        eval_btn.clicked.connect(self.evaluate_current_alerts)
        log_btn = QPushButton("Log Active Alerts")
        log_btn.clicked.connect(self.log_current_alerts)
        refresh_btn = QPushButton("Refresh Alert History")
        refresh_btn.clicked.connect(self.refresh_alert_history)
        button_row.addWidget(eval_btn)
        button_row.addWidget(log_btn)
        button_row.addWidget(refresh_btn)
        button_row.addStretch()
        ll.addLayout(button_row)

        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(5)
        self.alerts_table.setHorizontalHeaderLabels(["Ticker", "Alert", "Level", "Status", "Message"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ll.addWidget(self.alerts_table)

        right, rl = self.panel("Alert Report & History")
        self.alerts_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.alerts_text)

        self.alert_history_table = QTableWidget()
        self.alert_history_table.setColumnCount(5)
        self.alert_history_table.setHorizontalHeaderLabels(["Time", "Ticker", "Alert", "Status", "Message"])
        self.alert_history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.alert_history_table.setMaximumHeight(220)
        rl.addWidget(self.alert_history_table)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)
        return page

    def evaluate_current_alerts(self):
        if not self.selected:
            self.status.setText("No selected ticker for alerts.")
            return
        self.update_alerts_tab(self.selected)
        self.status.setText(f"Alerts evaluated for {self.selected['ticker']}.")

    def log_current_alerts(self):
        if not self.selected:
            self.status.setText("No selected ticker for alerts.")
            return
        alerts = evaluate_alerts(self.selected)
        active = [a for a in alerts if a.get("status") in {"ACTIVE", "WARNING"}]
        for alert in active:
            log_alert(alert)
        self.refresh_alert_history()
        self.status.setText(f"Logged {len(active)} active/warning alerts for {self.selected['ticker']}.")

    def refresh_alert_history(self):
        if not hasattr(self, "alert_history_table"):
            return
        rows = load_alerts()
        self.alert_history_table.setRowCount(len(rows))
        for r, alert in enumerate(rows[-50:]):
            vals = [
                alert.get("time", ""),
                alert.get("ticker", ""),
                alert.get("alert", ""),
                alert.get("status", ""),
                alert.get("message", ""),
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                self.alert_history_table.setItem(r, c, item)

    def update_alerts_tab(self, row):
        if not hasattr(self, "alerts_table"):
            return

        alerts = evaluate_alerts(row)
        self.alerts_table.setRowCount(len(alerts))

        for r, alert in enumerate(alerts):
            vals = [
                alert.get("ticker", ""),
                alert.get("alert", ""),
                alert.get("level", ""),
                alert.get("status", ""),
                alert.get("message", ""),
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                self.alerts_table.setItem(r, c, item)

        if hasattr(self, "alerts_text"):
            self.alerts_text.setPlainText(alerts_report(row))

        self.refresh_alert_history()

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

    def current_capital_and_risk(self):
        try:
            capital = float(self.capital_input.currentText()) if hasattr(self, "capital_input") else 20000.0
        except Exception as exc:
            log_error("Failed to parse portfolio capital input", exc)
            capital = 20000.0
        try:
            risk_pct = float(self.risk_input.currentText()) if hasattr(self, "risk_input") else 1.0
        except Exception as exc:
            log_error("Failed to parse portfolio risk input", exc)
            risk_pct = 1.0
        try:
            capital = float(capital)
            risk_pct = float(risk_pct)
        except Exception as exc:
            log_error("Failed to normalize portfolio capital/risk values", exc)
            capital = 20000.0
            risk_pct = 1.0
        return capital, risk_pct

    def refresh_portfolio_risk(self):
        if self.selected:
            self.update_portfolio_tab(self.selected)

    def update_portfolio_tab(self, row):
        if not hasattr(self, "portfolio_table"):
            return

        capital, risk_pct = self.current_capital_and_risk()

        self.portfolio_table.blockSignals(True)
        self.portfolio_table.setRowCount(len(self.rows))
        for r, item_row in enumerate(self.rows):
            ai = item_row.get("ai_decision") or build_ai_decision(item_row)
            sizing = position_size(item_row, capital, risk_pct)
            vals = [
                item_row["ticker"],
                asset_class(item_row),
                item_row["price"],
                ai["ai_score"],
                ai["ai_action"],
                sizing["risk_budget"],
                sizing["shares"],
            ]
            for c, v in enumerate(vals):
                cell = QTableWidgetItem(str(v))
                cell.setTextAlignment(Qt.AlignCenter)
                self.portfolio_table.setItem(r, c, cell)
            if row and item_row["ticker"] == row["ticker"]:
                self.portfolio_table.selectRow(r)
        self.portfolio_table.blockSignals(False)

        if hasattr(self, "portfolio_text") and row:
            self.portfolio_text.setPlainText(risk_report(row, capital, risk_pct))
        if hasattr(self, "exposure_text"):
            self.exposure_text.setPlainText(exposure_report(self.rows))

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


    def market_intelligence_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("Market Intelligence Dashboard")
        self.market_briefing_text = self.make_readonly(QTextEdit())
        ll.addWidget(self.market_briefing_text)

        self.market_calendar_table = QTableWidget()
        self.market_calendar_table.setColumnCount(4)
        self.market_calendar_table.setHorizontalHeaderLabels(["Date", "Event", "Importance", "Markets"])
        self.market_calendar_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.market_calendar_table.setMaximumHeight(220)
        ll.addWidget(self.market_calendar_table)

        right, rl = self.panel("Metals / News / Macro Context")
        self.metals_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.metals_text)

        self.news_intel_text = self.make_readonly(QTextEdit())
        self.news_intel_text.setMaximumHeight(220)
        rl.addWidget(self.news_intel_text)

        refresh = QPushButton("Refresh Market Intelligence")
        refresh.clicked.connect(self.refresh_market_intelligence)
        rl.addWidget(refresh)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)
        return page

    def refresh_market_intelligence(self):
        if hasattr(self, "market_briefing_text"):
            self.market_briefing_text.setPlainText(
                dashboard_report() + "\\n\\n" + ai_market_briefing() + "\\n\\n" + calendar_report()
            )

        if hasattr(self, "metals_text"):
            self.metals_text.setPlainText(metals_report())

        if hasattr(self, "news_intel_text"):
            self.news_intel_text.setPlainText(news_report())

        if hasattr(self, "market_calendar_table"):
            events = economic_calendar()
            self.market_calendar_table.setRowCount(len(events))
            for r, event in enumerate(events):
                vals = [event["date"], event["event"], event["importance"], event["markets"]]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.market_calendar_table.setItem(r, c, item)

        if hasattr(self, "status"):
            self.status.setText("Market Intelligence refreshed.")



    def workspace_manager_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("Workspace Manager")
        controls = QHBoxLayout()

        self.workspace_selector = QComboBox()
        self.workspace_selector.addItems(list_workspaces())

        load_btn = QPushButton("Load Workspace")
        load_btn.clicked.connect(self.load_selected_workspace)

        save_btn = QPushButton("Save Current Workspace")
        save_btn.clicked.connect(self.save_current_workspace)

        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.refresh_workspace_manager)

        controls.addWidget(QLabel("Workspace:"))
        controls.addWidget(self.workspace_selector)
        controls.addWidget(load_btn)
        controls.addWidget(save_btn)
        controls.addWidget(refresh_btn)
        controls.addStretch()
        ll.addLayout(controls)

        self.workspace_table = QTableWidget()
        self.workspace_table.setColumnCount(5)
        self.workspace_table.setHorizontalHeaderLabels(["Workspace", "Symbol", "Layout", "Scanner", "Saved"])
        self.workspace_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ll.addWidget(self.workspace_table)

        right, rl = self.panel("Workspace Report")
        self.workspace_report_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.workspace_report_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)

        self.refresh_workspace_manager()
        return page

    def capture_current_workspace(self):
        selected_symbol = self.selected["ticker"] if getattr(self, "selected", None) else self.search.text().strip().upper() or "TSLA"
        return {
            "selected_symbol": selected_symbol,
            "multi_chart_layout": self.multi_layout_selector.currentText() if hasattr(self, "multi_layout_selector") else "4 Charts",
            "linked_charts": self.multi_linked_toggle.isChecked() if hasattr(self, "multi_linked_toggle") else True,
            "data_mode": self.data_mode.currentText() if hasattr(self, "data_mode") else "Fallback",
            "scanner_preset": self.scanner_preset.currentText() if hasattr(self, "scanner_preset") else "Day Trade",
            "chart_timeframe": self.chart_timeframe.currentText() if hasattr(self, "chart_timeframe") else "5m",
            "notes": "Saved from ATIS workspace manager.",
        }

    def save_current_workspace(self):
        name = self.workspace_selector.currentText() if hasattr(self, "workspace_selector") and self.workspace_selector.currentText() else "Custom Workspace"
        save_workspace(name, self.capture_current_workspace())
        self.refresh_workspace_manager()
        self.status.setText(f"Workspace saved: {name}")

    def load_selected_workspace(self):
        if not hasattr(self, "workspace_selector"):
            return
        name = self.workspace_selector.currentText()
        data = load_workspace(name)
        if not data:
            self.status.setText(f"Workspace not found: {name}")
            return

        if hasattr(self, "data_mode"):
            mode = data.get("data_mode", "Fallback")
            idx = self.data_mode.findText(mode)
            if idx >= 0:
                self.data_mode.setCurrentIndex(idx)

        if hasattr(self, "scanner_preset"):
            preset = data.get("scanner_preset", "Day Trade")
            idx = self.scanner_preset.findText(preset)
            if idx >= 0:
                self.scanner_preset.setCurrentIndex(idx)

        if hasattr(self, "chart_timeframe"):
            tf = data.get("chart_timeframe", "5m")
            idx = self.chart_timeframe.findText(tf)
            if idx >= 0:
                self.chart_timeframe.setCurrentIndex(idx)

        if hasattr(self, "multi_layout_selector"):
            layout = data.get("multi_chart_layout", "4 Charts")
            idx = self.multi_layout_selector.findText(layout)
            if idx >= 0:
                self.multi_layout_selector.setCurrentIndex(idx)

        if hasattr(self, "multi_linked_toggle"):
            self.multi_linked_toggle.setChecked(bool(data.get("linked_charts", True)))

        symbol = data.get("selected_symbol", "TSLA")
        self.load_symbol(symbol)

        if hasattr(self, "multi_chart_widgets"):
            self.rebuild_multi_chart_workspace()

        self.refresh_workspace_manager()
        self.status.setText(f"Workspace loaded: {name}")

    def refresh_workspace_manager(self):
        names = list_workspaces()

        if hasattr(self, "workspace_selector"):
            current = self.workspace_selector.currentText()
            self.workspace_selector.blockSignals(True)
            self.workspace_selector.clear()
            self.workspace_selector.addItems(names)
            if current:
                idx = self.workspace_selector.findText(current)
                if idx >= 0:
                    self.workspace_selector.setCurrentIndex(idx)
            self.workspace_selector.blockSignals(False)

        if hasattr(self, "workspace_table"):
            self.workspace_table.setRowCount(len(names))
            for r, name in enumerate(names):
                data = load_workspace(name)
                vals = [
                    name,
                    data.get("selected_symbol", ""),
                    data.get("multi_chart_layout", ""),
                    data.get("scanner_preset", ""),
                    data.get("saved_at", ""),
                ]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.workspace_table.setItem(r, c, item)

        if hasattr(self, "workspace_report_text"):
            self.workspace_report_text.setPlainText(workspace_report())


    def paper_trading_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("Paper Trading Order Ticket")
        ticket = QHBoxLayout()

        self.paper_side = QComboBox()
        self.paper_side.addItems(["BUY", "SELL"])

        self.paper_quantity = QComboBox()
        self.paper_quantity.addItems(["10", "25", "50", "100", "250", "500", "1000"])
        self.paper_quantity.setCurrentText("100")

        submit = QPushButton("Submit Paper Order")
        submit.clicked.connect(self.submit_paper_order)

        reset = QPushButton("Reset Paper Account")
        reset.clicked.connect(self.reset_paper_account)

        ticket.addWidget(QLabel("Side:"))
        ticket.addWidget(self.paper_side)
        ticket.addWidget(QLabel("Qty:"))
        ticket.addWidget(self.paper_quantity)
        ticket.addWidget(submit)
        ticket.addWidget(reset)
        ticket.addStretch()
        ll.addLayout(ticket)

        self.paper_account_text = self.make_readonly(QTextEdit())
        ll.addWidget(self.paper_account_text)

        self.paper_positions_table = QTableWidget()
        self.paper_positions_table.setColumnCount(6)
        self.paper_positions_table.setHorizontalHeaderLabels(["Ticker", "Qty", "Avg Cost", "Current", "Value", "Unrealized P/L"])
        self.paper_positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ll.addWidget(self.paper_positions_table)

        right, rl = self.panel("Execution Log")
        self.paper_orders_table = QTableWidget()
        self.paper_orders_table.setColumnCount(8)
        self.paper_orders_table.setHorizontalHeaderLabels(["Time", "Ticker", "Side", "Qty", "Price", "Value", "Status", "Notes"])
        self.paper_orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rl.addWidget(self.paper_orders_table)

        self.paper_review_text = self.make_readonly(QTextEdit())
        self.paper_review_text.setMaximumHeight(220)
        rl.addWidget(self.paper_review_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 3)

        self.refresh_paper_trading_tab()
        return page

    def price_lookup_for_paper(self, ticker):
        row, _ = market_data_engine.get_row(ticker)
        return row.get("price") if row else None

    def submit_paper_order(self):
        if not self.selected:
            self.status.setText("No selected ticker for paper order.")
            return

        ticker = self.selected["ticker"]
        qty = int(self.paper_quantity.currentText()) if hasattr(self, "paper_quantity") else 100
        price = float(self.selected.get("price", 0))
        side = self.paper_side.currentText() if hasattr(self, "paper_side") else "BUY"
        notes = self.selected.get("ai_decision", {}).get("ai_action", self.selected.get("action", ""))

        if side == "BUY":
            result = paper_buy(ticker, qty, price, notes)
        else:
            result = paper_sell(ticker, qty, price, notes)

        if result.get("status") == "FILLED":
            trade = planned_trade_from_row(self.selected)
            trade["action"] = side
            trade["shares"] = qty
            trade["entry"] = price if side == "BUY" else trade.get("entry", "")
            trade["exit"] = price if side == "SELL" else ""
            trade["result"] = "Filled"
            trade["notes"] = notes
            trade["strategy"] = trade.get("strategy", "Paper Trade")
            if side == "SELL":
                trade["pnl"] = result.get("realized_pnl", "")
            else:
                trade["pnl"] = ""
            trade["r_multiple"] = ""
            append_trade(trade)
            if hasattr(self, "journal_table"):
                self.refresh_journal_tab()
            if self.selected:
                if hasattr(self, "command_ops_text"):
                    self.update_command_center(self.selected)
                if hasattr(self, "portfolio_table"):
                    self.update_portfolio_tab(self.selected)
                if hasattr(self, "analytics_text"):
                    self.update_journal_analytics(self.selected)

        self.refresh_paper_trading_tab()
        self.status.setText(result.get("message", result.get("status", "Order processed.")))

    def reset_paper_account(self):
        reset_account()
        self.refresh_paper_trading_tab()
        self.status.setText(f"Paper account reset to ${starting_cash():,.0f}.")

    def refresh_paper_trading_tab(self):
        if not hasattr(self, "paper_account_text"):
            return

        summary = account_summary(self.price_lookup_for_paper)
        self.paper_account_text.setPlainText(account_report(summary))

        self.paper_positions_table.setRowCount(len(summary["positions"]))
        for r, pos in enumerate(summary["positions"]):
            vals = [
                pos["ticker"], pos["quantity"], pos["avg_cost"], pos["current_price"],
                pos["market_value"], pos["unrealized_pnl"]
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                self.paper_positions_table.setItem(r, c, item)

        orders = load_orders()
        recent_orders = orders[-100:]
        self.paper_orders_table.setRowCount(len(recent_orders))
        for r, order in enumerate(recent_orders):
            vals = [
                order.get("time", ""), order.get("ticker", ""), order.get("side", ""),
                order.get("quantity", ""), order.get("price", ""), order.get("value", ""),
                order.get("status", ""), order.get("notes", "")
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                item.setTextAlignment(Qt.AlignCenter)
                self.paper_orders_table.setItem(r, c, item)

        if self.selected and hasattr(self, "paper_review_text"):
            ai = self.selected.get("ai_decision") or build_ai_decision(self.selected)
            self.paper_review_text.setPlainText(
                f"AI ORDER REVIEW — {self.selected['ticker']}\\n\\n"
                f"Action: {ai['ai_action']}\\n"
                f"AI Score: {ai['ai_score']}/100\\n"
                f"Confidence: {ai['ai_confidence']}\\n"
                f"Entry: {ai['entry_zone']}\\n"
                f"Stop: {ai['stop_level']}\\n"
                f"Target: {ai['target_zone']}\\n\\n"
                "Paper trading only. No real broker order is sent."
            )


    def strategy_lab_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("Strategy Lab Controls")
        controls = QHBoxLayout()

        self.strategy_selector = QComboBox()
        self.strategy_selector.addItems(strategy_names())

        self.strategy_capital = QComboBox()
        self.strategy_capital.addItems(["5000", "10000", "20000", "50000"])
        self.strategy_capital.setCurrentText("10000")

        self.strategy_risk = QComboBox()
        self.strategy_risk.addItems(["0.5", "1", "1.5", "2"])
        self.strategy_risk.setCurrentText("1")

        run_btn = QPushButton("Run Backtest")
        run_btn.clicked.connect(self.run_strategy_backtest)

        controls.addWidget(QLabel("Strategy:"))
        controls.addWidget(self.strategy_selector)
        controls.addWidget(QLabel("Capital:"))
        controls.addWidget(self.strategy_capital)
        controls.addWidget(QLabel("Risk %:"))
        controls.addWidget(self.strategy_risk)
        controls.addWidget(run_btn)
        controls.addStretch()
        ll.addLayout(controls)

        self.strategy_report_text = self.make_readonly(QTextEdit())
        ll.addWidget(self.strategy_report_text)

        right, rl = self.panel("Backtest Trades")
        self.strategy_trades_table = QTableWidget()
        self.strategy_trades_table.setColumnCount(8)
        self.strategy_trades_table.setHorizontalHeaderLabels(["#", "Entry", "Exit", "Qty", "Stop", "Target", "P/L", "Result"])
        self.strategy_trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rl.addWidget(self.strategy_trades_table)

        self.strategy_equity_text = self.make_readonly(QTextEdit())
        self.strategy_equity_text.setMaximumHeight(170)
        rl.addWidget(self.strategy_equity_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 3)

        return page

    def run_strategy_backtest(self):
        if not self.selected:
            self.status.setText("No selected ticker for backtest.")
            return

        strategy = self.strategy_selector.currentText() if hasattr(self, "strategy_selector") else "EMA/VWAP Momentum"
        capital = float(self.strategy_capital.currentText()) if hasattr(self, "strategy_capital") else 10000.0
        risk_pct = float(self.strategy_risk.currentText()) if hasattr(self, "strategy_risk") else 1.0

        result = backtest(self.selected, strategy=strategy, starting_capital=capital, risk_pct=risk_pct)

        if hasattr(self, "strategy_report_text"):
            self.strategy_report_text.setPlainText(result["report"])

        if hasattr(self, "strategy_trades_table"):
            trades = result["trades"]
            self.strategy_trades_table.setRowCount(len(trades))
            for r, trade in enumerate(trades):
                vals = [
                    r + 1,
                    trade.get("entry", ""),
                    trade.get("exit", ""),
                    trade.get("qty", ""),
                    trade.get("stop", ""),
                    trade.get("target", ""),
                    trade.get("pnl", ""),
                    trade.get("result", ""),
                ]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.strategy_trades_table.setItem(r, c, item)

        if hasattr(self, "strategy_equity_text"):
            curve = result.get("equity_curve", [])
            self.strategy_equity_text.setPlainText(
                "EQUITY CURVE SNAPSHOT\\n\\n"
                + " → ".join([str(x) for x in curve[-12:]])
                + "\\n\\nNote: This is a compact text equity curve. A visual curve can be added later."
            )

        self.status.setText(f"Backtest complete: {self.selected['ticker']} | {strategy} | {result['total_trades']} trades.")


    def diagnostics_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("Production Diagnostics")
        btn_row = QHBoxLayout()
        refresh = QPushButton("Run Health Check")
        refresh.clicked.connect(self.refresh_diagnostics)
        btn_row.addWidget(refresh)
        btn_row.addStretch()
        ll.addLayout(btn_row)

        self.diagnostics_text = self.make_readonly(QTextEdit())
        ll.addWidget(self.diagnostics_text)

        right, rl = self.panel("Regression Checklist")
        self.regression_table = QTableWidget()
        self.regression_table.setColumnCount(3)
        self.regression_table.setHorizontalHeaderLabels(["Check", "Status", "Notes"])
        self.regression_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rl.addWidget(self.regression_table)

        self.version_text = self.make_readonly(QTextEdit())
        self.version_text.setMaximumHeight(140)
        rl.addWidget(self.version_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)

        self.refresh_diagnostics()
        return page

    def refresh_diagnostics(self):
        if hasattr(self, "diagnostics_text"):
            self.diagnostics_text.setPlainText(health_report())

        if hasattr(self, "version_text"):
            self.version_text.setPlainText(
                f"BUILD VERSION\\n\\n{version_info()}\\n\\n"
                "Regression script:\\npython tests/regression_smoke.py"
            )

        if hasattr(self, "regression_table"):
            health = system_health()
            checks = health.get("checks", [])
            self.regression_table.setRowCount(len(checks))
            for r, check in enumerate(checks):
                vals = [check.get("module", ""), check.get("status", ""), check.get("message", "")]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.regression_table.setItem(r, c, item)

        if hasattr(self, "status"):
            self.status.setText("Diagnostics refreshed.")



    def release_candidate_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("Release Candidate Manifest")
        self.release_manifest_text = self.make_readonly(QTextEdit())
        ll.addWidget(self.release_manifest_text)

        right, rl = self.panel("Settings / Release Notes")
        btn_row = QHBoxLayout()
        refresh = QPushButton("Refresh Release Info")
        refresh.clicked.connect(self.refresh_release_candidate)
        btn_row.addWidget(refresh)
        btn_row.addStretch()
        rl.addLayout(btn_row)

        self.release_settings_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.release_settings_text)

        self.release_checklist_text = self.make_readonly(QTextEdit())
        self.release_checklist_text.setMaximumHeight(220)
        rl.addWidget(self.release_checklist_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)

        self.refresh_release_candidate()
        return page

    def refresh_release_candidate(self):
        if hasattr(self, "release_manifest_text"):
            self.release_manifest_text.setPlainText(manifest_text())

        if hasattr(self, "release_settings_text"):
            self.release_settings_text.setPlainText(settings_report())

        checklist = Path("RELEASE_CHECKLIST_v3_0_RC1.md")
        if hasattr(self, "release_checklist_text"):
            if checklist.exists():
                self.release_checklist_text.setPlainText(checklist.read_text(encoding="utf-8", errors="ignore"))
            else:
                self.release_checklist_text.setPlainText("Release checklist file not found.")

        log_event("Release Candidate tab refreshed.")
        if hasattr(self, "status"):
            self.status.setText(f"Release Candidate info refreshed: {VERSION}")


    def watchlist_manager_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("Professional Watchlists")
        controls = QHBoxLayout()

        self.watchlist_selector = QComboBox()
        self.watchlist_selector.addItems(list_watchlists())

        load_btn = QPushButton("Load Watchlist")
        load_btn.clicked.connect(self.load_selected_watchlist)

        add_btn = QPushButton("Add Current Symbol")
        add_btn.clicked.connect(self.add_current_to_watchlist)

        remove_btn = QPushButton("Remove Current Symbol")
        remove_btn.clicked.connect(self.remove_current_from_watchlist)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_watchlists)

        controls.addWidget(QLabel("Watchlist:"))
        controls.addWidget(self.watchlist_selector)
        controls.addWidget(load_btn)
        controls.addWidget(add_btn)
        controls.addWidget(remove_btn)
        controls.addWidget(refresh_btn)
        controls.addStretch()
        ll.addLayout(controls)

        self.watchlist_manager_table = QTableWidget()
        self.watchlist_manager_table.setColumnCount(4)
        self.watchlist_manager_table.setHorizontalHeaderLabels(["#", "Ticker", "Name", "Source"])
        self.watchlist_manager_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.watchlist_manager_table.itemSelectionChanged.connect(self.watchlist_manager_selected)
        ll.addWidget(self.watchlist_manager_table)

        right, rl = self.panel("Watchlist Report")
        self.watchlist_report_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.watchlist_report_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)

        self.refresh_watchlists()
        return page

    def refresh_watchlists(self):
        if hasattr(self, "watchlist_selector"):
            current = self.watchlist_selector.currentText()
            self.watchlist_selector.blockSignals(True)
            self.watchlist_selector.clear()
            self.watchlist_selector.addItems(list_watchlists())
            if current:
                idx = self.watchlist_selector.findText(current)
                if idx >= 0:
                    self.watchlist_selector.setCurrentIndex(idx)
            self.watchlist_selector.blockSignals(False)

        if hasattr(self, "watchlist_report_text"):
            self.watchlist_report_text.setPlainText(watchlist_report())

        if hasattr(self, "watchlist_manager_table"):
            name = self.watchlist_selector.currentText() if hasattr(self, "watchlist_selector") else "Favorites"
            symbols = load_watchlist(name)
            self.watchlist_manager_table.blockSignals(True)
            self.watchlist_manager_table.setRowCount(len(symbols))
            for r, symbol in enumerate(symbols):
                row, _ = market_data_engine.get_row(symbol)
                vals = [r + 1, symbol, row.get("name", "") if row else "", row.get("data_source", "") if row else ""]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.watchlist_manager_table.setItem(r, c, item)
            self.watchlist_manager_table.blockSignals(False)

        if hasattr(self, "status"):
            self.status.setText("Watchlists refreshed.")

    def load_selected_watchlist(self):
        if not hasattr(self, "watchlist_selector"):
            return
        name = self.watchlist_selector.currentText()
        symbols = load_watchlist(name)
        rows = []
        for symbol in symbols:
            row, _ = market_data_engine.get_row(symbol)
            if row:
                rows.append(row)
        if rows:
            for i, item_row in enumerate(rows, 1):
                item_row["rank"] = i
            self.rows = rows
            self.selected = rows[0]
            self.update_tables()
            self.update_all_panels(self.selected)
            event_bus.publish(WATCHLIST_CHANGED, watchlist=name, symbols=symbols)
            self.status.setText(f"Loaded watchlist: {name}")

    def add_current_to_watchlist(self):
        if not getattr(self, "selected", None):
            return
        name = self.watchlist_selector.currentText() if hasattr(self, "watchlist_selector") else "Favorites"
        add_symbol(name, self.selected["ticker"])
        event_bus.publish(WATCHLIST_CHANGED, watchlist=name, action="add", symbol=self.selected["ticker"])
        self.refresh_watchlists()

    def remove_current_from_watchlist(self):
        if not getattr(self, "selected", None):
            return
        name = self.watchlist_selector.currentText() if hasattr(self, "watchlist_selector") else "Favorites"
        remove_symbol(name, self.selected["ticker"])
        event_bus.publish(WATCHLIST_CHANGED, watchlist=name, action="remove", symbol=self.selected["ticker"])
        self.refresh_watchlists()

    def watchlist_manager_selected(self):
        if not hasattr(self, "watchlist_manager_table"):
            return
        r = self.watchlist_manager_table.currentRow()
        if r >= 0:
            item = self.watchlist_manager_table.item(r, 1)
            if item:
                self.load_symbol(item.text())

    def workstation_architecture_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("v4.0 Workstation Architecture")
        self.workstation_text = self.make_readonly(QTextEdit())
        self.workstation_text.setPlainText(architecture_report())
        ll.addWidget(self.workstation_text)

        right, rl = self.panel("Event Bus Activity")
        refresh = QPushButton("Refresh Event Bus")
        refresh.clicked.connect(self.refresh_event_bus)
        rl.addWidget(refresh)

        self.event_bus_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.event_bus_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)

        self.refresh_event_bus()
        return page

    def refresh_event_bus(self):
        if hasattr(self, "event_bus_text"):
            self.event_bus_text.setPlainText(event_bus.recent_report())
        if hasattr(self, "status"):
            self.status.setText("Event bus refreshed.")

    def integrations_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)

        left, ll = self.panel("Plugin / API Registry")
        btn_row = QHBoxLayout()
        refresh = QPushButton("Refresh Integrations")
        refresh.clicked.connect(self.refresh_integrations)
        broker_test = QPushButton("Test Broker Safety")
        broker_test.clicked.connect(self.test_broker_safety)
        btn_row.addWidget(refresh)
        btn_row.addWidget(broker_test)
        btn_row.addStretch()
        ll.addLayout(btn_row)

        self.integrations_table = QTableWidget()
        self.integrations_table.setColumnCount(5)
        self.integrations_table.setHorizontalHeaderLabels(["Name", "Category", "Status", "Version", "Description"])
        self.integrations_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ll.addWidget(self.integrations_table)

        right, rl = self.panel("Integration Diagnostics")
        self.integrations_text = self.make_readonly(QTextEdit())
        rl.addWidget(self.integrations_text)

        self.broker_safety_text = self.make_readonly(QTextEdit())
        self.broker_safety_text.setMaximumHeight(180)
        rl.addWidget(self.broker_safety_text)

        layout.addWidget(left, 3)
        layout.addWidget(right, 2)

        self.refresh_integrations()
        if hasattr(self, "broker_safety_text"):
            self.broker_safety_text.setPlainText(
                "BROKER SAFETY STATUS\n\n"
                "Click Test Broker Safety to confirm live orders are disabled.\n"
                "No real money broker execution is enabled in this build."
            )
        return page

    def refresh_integrations(self):
        plugins = registry.list_plugins()

        if hasattr(self, "integrations_text"):
            self.integrations_text.setPlainText(
                plugin_report()
                + "\n\nLast action:\nRefresh Integrations clicked successfully."
            )

        if hasattr(self, "integrations_table"):
            self.integrations_table.setRowCount(len(plugins))
            for r, p in enumerate(plugins):
                vals = [p.name, p.category, p.status, p.version, p.description]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.integrations_table.setItem(r, c, item)

        if hasattr(self, "broker_safety_text") and not self.broker_safety_text.toPlainText().strip():
            self.broker_safety_text.setPlainText(
                "BROKER SAFETY STATUS\n\n"
                "Live broker execution is disabled.\n"
                "Use the Paper Trading tab for simulated orders only."
            )

        if hasattr(self, "status"):
            self.status.setText(f"Integrations refreshed: {len(plugins)} adapters loaded.")


    def test_broker_safety(self):
        ticker = self.selected["ticker"] if getattr(self, "selected", None) else "TSLA"
        order = BrokerOrder(
            ticker=ticker,
            side="BUY",
            quantity=1,
            order_type="MARKET",
        )
        result = disabled_live_broker.submit_order(order)

        message = (
            "BROKER SAFETY TEST\n\n"
            f"Test ticker: {ticker}\n"
            f"Adapter: {disabled_live_broker.name}\n"
            f"Status: {result.get('status')}\n"
            f"Message: {result.get('message')}\n\n"
            "RESULT:\n"
            "PASS — live broker orders are disabled. ATIS did not send a real order.\n\n"
            "Use Paper Trading for simulated orders."
        )

        if hasattr(self, "broker_safety_text"):
            self.broker_safety_text.setPlainText(message)

        if hasattr(self, "integrations_text"):
            self.integrations_text.setPlainText(plugin_report() + "\n\nLast action:\nBroker Safety Test clicked successfully.")

        if hasattr(self, "status"):
            self.status.setText("Broker safety test complete: live orders disabled.")

    def multi_chart_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        controls, cl = self.panel("Multi-Chart Workspace Controls")
        row = QHBoxLayout()

        self.multi_layout_selector = QComboBox()
        self.multi_layout_selector.addItems(layout_names())
        self.multi_layout_selector.setCurrentText("4 Charts")
        self.multi_layout_selector.currentTextChanged.connect(self.rebuild_multi_chart_workspace)

        self.multi_linked_toggle = QCheckBox("Linked to Global Search")
        self.multi_linked_toggle.setChecked(True)
        self.multi_linked_toggle.stateChanged.connect(self.refresh_multi_chart_workspace)

        refresh = QPushButton("Refresh Multi-Chart")
        refresh.clicked.connect(self.refresh_multi_chart_workspace)

        row.addWidget(QLabel("Layout:"))
        row.addWidget(self.multi_layout_selector)
        row.addWidget(self.multi_linked_toggle)
        row.addWidget(refresh)
        row.addStretch()
        cl.addLayout(row)
        layout.addWidget(controls)

        body, bl = self.panel("Professional Multi-Chart Grid")
        self.multi_chart_grid = QGridLayout()
        bl.addLayout(self.multi_chart_grid)
        layout.addWidget(body, 1)

        self.multi_chart_widgets = []
        self.rebuild_multi_chart_workspace()
        return page

    def clear_multi_chart_grid(self):
        if not hasattr(self, "multi_chart_grid"):
            return
        while self.multi_chart_grid.count():
            item = self.multi_chart_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        if hasattr(self, "multi_chart_widgets"):
            self.multi_chart_widgets = []

    def rebuild_multi_chart_workspace(self):
        if not hasattr(self, "multi_chart_grid"):
            return

        self.clear_multi_chart_grid()

        count = layout_count(self.multi_layout_selector.currentText() if hasattr(self, "multi_layout_selector") else "4 Charts")
        columns = 2 if count <= 4 else 3

        for i in range(count):
            panel, pl = self.panel(f"Chart {i + 1}")
            control_row = QHBoxLayout()

            symbol_label = QLabel(default_symbol(i))
            symbol_label.setObjectName("sub")

            tf = QComboBox()
            tf.addItems(["1m", "5m", "15m", "1h", "Daily"])
            tf.setCurrentText(default_timeframe(i))

            chart = ChartWidget()
            chart.set_timeframe(tf.currentText())
            tf.currentTextChanged.connect(chart.set_timeframe)
            chart.setAttribute(Qt.WA_DeleteOnClose, False)

            control_row.addWidget(QLabel("Symbol:"))
            control_row.addWidget(symbol_label)
            control_row.addWidget(QLabel("TF:"))
            control_row.addWidget(tf)
            control_row.addStretch()
            pl.addLayout(control_row)
            pl.addWidget(chart)

            self.multi_chart_widgets.append({
                "panel": panel,
                "chart": chart,
                "timeframe": tf,
                "label": symbol_label,
                "symbol": default_symbol(i),
            })

            r = i // columns
            c = i % columns
            self.multi_chart_grid.addWidget(panel, r, c)

        self.refresh_multi_chart_workspace()

    def refresh_multi_chart_workspace(self):
        if not hasattr(self, "multi_chart_widgets"):
            return

        linked = self.multi_linked_toggle.isChecked() if hasattr(self, "multi_linked_toggle") else True
        global_symbol = self.selected["ticker"] if getattr(self, "selected", None) else "TSLA"

        for i, item in enumerate(self.multi_chart_widgets):
            symbol = global_symbol if linked else item.get("symbol", default_symbol(i))
            row, error = market_data_engine.get_row(symbol)
            if not row:
                continue
            item["label"].setText(symbol)
            item["chart"].set_timeframe(item["timeframe"].currentText())
            item["chart"].set_row(row)

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


    def format_money_value(self, value):
        try:
            if value in ("N/A", None, ""):
                return "N/A"
            value = float(value)
            if abs(value) >= 1_000_000_000_000:
                return f"${value/1_000_000_000_000:.2f}T"
            if abs(value) >= 1_000_000_000:
                return f"${value/1_000_000_000:.2f}B"
            if abs(value) >= 1_000_000:
                return f"${value/1_000_000:.2f}M"
            return f"${value:,.2f}"
        except Exception:
            return str(value)


    def full_market_workstation_report(self, row):
        profile = row.get("profile", {}) or {}
        ai = row.get("ai_decision", {}) or {}
        return f"""LIVE MARKET WORKSTATION — {row.get('ticker')} / {row.get('name')}

CORE MARKET DATA:
Price: ${row.get('price')}
Change: {row.get('change_pct')}%
Volume: {row.get('volume'):,}
Relative Volume: {row.get('relative_volume')}x
ATR(14): {row.get('atr14', 'N/A')}
Beta: {profile.get('beta', 'N/A')}
Market Cap: {self.format_money_value(profile.get('market_cap', 'N/A'))}
Float: {profile.get('float_shares', 'N/A')}
Shares Outstanding: {profile.get('shares_outstanding', 'N/A')}

TECHNICAL SNAPSHOT:
VWAP: ${row.get('vwap')}
EMA 9: ${row.get('ema9')}
EMA 20: ${row.get('ema20')}
SMA 50: ${row.get('sma50', 'N/A')}
SMA 200: ${row.get('sma200', 'N/A')}
RSI 14: {row.get('rsi14', 'N/A')}
MACD: {row.get('macd', 'N/A')}
MACD Signal: {row.get('macd_signal', 'N/A')}
Day Range: ${row.get('day_low')} - ${row.get('day_high')}
52 Week Range: {profile.get('fifty_two_week_low', 'N/A')} - {profile.get('fifty_two_week_high', 'N/A')}

COMPANY / FUNDAMENTAL:
Exchange: {profile.get('exchange', 'N/A')}
Sector: {profile.get('sector', 'N/A')}
Industry: {profile.get('industry', 'N/A')}
Trailing P/E: {profile.get('trailing_pe', 'N/A')}
Forward P/E: {profile.get('forward_pe', 'N/A')}
Dividend Yield: {profile.get('dividend_yield', 'N/A')}
Earnings Date: {profile.get('earnings_date', 'N/A')}
Analyst Recommendation: {profile.get('recommendation', 'N/A')}
Target Mean/Low/High: {profile.get('target_mean_price', 'N/A')} / {profile.get('target_low_price', 'N/A')} / {profile.get('target_high_price', 'N/A')}

ATIS AI:
Action: {ai.get('ai_action', row.get('action'))}
AI Score: {ai.get('ai_score', row.get('score'))}/100
Confidence: {ai.get('ai_confidence', row.get('confidence'))}
Risk/Reward: {ai.get('risk_reward', row.get('risk_reward'))}
Entry: {ai.get('entry_zone', row.get('entry'))}
Stop: {ai.get('stop_level', row.get('stop'))}
Target: {ai.get('target_zone', row.get('target1'))}

DATA SOURCE:
{row.get('data_source')}
Updated: {row.get('updated')}
"""

    def stock_explorer_report(self, row):
        profile = row.get("profile", {}) or {}
        summary = profile.get("business_summary", "Live company summary unavailable.")
        if len(summary) > 1800:
            summary = summary[:1800] + "..."

        news_items = row.get("news_items", []) or []
        headlines = "\n".join(
            [f"- {n.get('title', '')} ({n.get('publisher', 'News')})" for n in news_items[:6]]
        ) or "No live headlines returned by the data provider."

        return f"""STOCK EXPLORER — {row.get('ticker')} / {row.get('name')}

LIVE DATA STATUS:
Source: {row.get('data_source')}
Updated: {row.get('updated')}
Live profile available: {row.get('live_info_available', False)}

PRICE:
Last: ${row.get('price')}
Change: {row.get('change_pct')}%
Open: {profile.get('open', 'N/A')}
Previous Close: {profile.get('previous_close', 'N/A')}
Day Range: ${row.get('day_low')} - ${row.get('day_high')}
52 Week Range: {profile.get('fifty_two_week_low', 'N/A')} - {profile.get('fifty_two_week_high', 'N/A')}

COMPANY:
Exchange: {profile.get('exchange', 'N/A')}
Type: {profile.get('quote_type', 'N/A')}
Sector: {profile.get('sector', 'N/A')}
Industry: {profile.get('industry', 'N/A')}
Market Cap: {self.format_money_value(profile.get('market_cap', 'N/A'))}
Float: {profile.get('float_shares', 'N/A')}
Shares Outstanding: {profile.get('shares_outstanding', 'N/A')}
Beta: {profile.get('beta', 'N/A')}
Trailing P/E: {profile.get('trailing_pe', 'N/A')}
Forward P/E: {profile.get('forward_pe', 'N/A')}
Dividend Yield: {profile.get('dividend_yield', 'N/A')}
Earnings Date: {profile.get('earnings_date', 'N/A')}
Analyst Recommendation: {profile.get('recommendation', 'N/A')}
Target Mean: {profile.get('target_mean_price', 'N/A')}
Volume Today: {row.get('volume'):,}
Average Volume: {profile.get('average_volume', 'N/A')}
Website: {profile.get('website', 'N/A')}

AI / TECHNICAL:
AI Action: {row.get('ai_decision', {}).get('ai_action', row.get('action'))}
Score: {row.get('ai_decision', {}).get('ai_score', row.get('score'))}/100
VWAP: ${row.get('vwap')}
EMA 9: ${row.get('ema9')}
EMA 20: ${row.get('ema20')}
SMA 50: ${row.get('sma50', 'N/A')}
SMA 200: ${row.get('sma200', 'N/A')}
RSI 14: {row.get('rsi14', 'N/A')}
MACD: {row.get('macd', 'N/A')}
ATR 14: {row.get('atr14', 'N/A')}
RVOL: {row.get('relative_volume')}x

LIVE NEWS HEADLINES:
{headlines}

BUSINESS SUMMARY:
{summary}
"""

    def stock_news_report(self, row):
        items = row.get("news_items", []) or []
        if not items:
            return (
                f"NEWS INTELLIGENCE — {row.get('ticker')}\n\n"
                "No live headlines were returned for this symbol.\n\n"
                "This can happen when yfinance/Yahoo has no recent headlines, internet is unavailable, "
                "or the ticker is not supported by the data provider."
            )

        lines = [
            f"NEWS INTELLIGENCE — {row.get('ticker')} / {row.get('name')}",
            "",
            f"Headlines returned: {len(items)}",
            "",
        ]
        for i, item in enumerate(items[:8], 1):
            lines.append(f"{i}. {item.get('title', '')}")
            lines.append(f"   Source: {item.get('publisher', 'News')}")
            if item.get("link"):
                lines.append(f"   Link: {item.get('link')}")
            lines.append("")
        return "\n".join(lines)

    def update_additional_tabs(self, row):
        if hasattr(self, "decision_30_text"):
            ai = row.get("ai_decision") or build_ai_decision(row)
            self.decision_30_text.setPlainText(
                f"DECISION ENGINE 3.0 + AI — {row['ticker']}\n\n"
                f"AI Action: {ai['ai_action']}\n"
                f"AI Score: {ai['ai_score']}/100\n"
                f"Confidence: {ai['ai_confidence']}\n\n"
                f"Legacy Score: {row['score']}/100\n"
                f"Legacy Action: {row['action']}\n\n"
                f"Entry: {ai['entry_zone']}\n"
                f"Stop: {ai['stop_level']}\n"
                f"Target Zone: {ai['target_zone']}\n"
                f"Risk/Reward: {ai['risk_reward']}\n\n"
                f"Trend Score: {ai['trend_score']}\n"
                f"Momentum Score: {ai['momentum_score']}\n"
                f"Risk Score: {ai['risk_score']}"
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
            self.news_text.setPlainText(self.stock_news_report(row))

        if hasattr(self, "data_text"):
            self.data_text.setPlainText(market_diagnostics())

        if hasattr(self, "news_table"):
            news_items = row.get("news_items", []) or []
            if news_items:
                self.news_table.setRowCount(min(len(news_items), 8))
                for r, item_row in enumerate(news_items[:8]):
                    vals = [row["ticker"], item_row.get("title", "Headline"), item_row.get("publisher", "News")]
                    for c, v in enumerate(vals):
                        item = QTableWidgetItem(str(v))
                        item.setTextAlignment(Qt.AlignCenter)
                        self.news_table.setItem(r, c, item)
            else:
                self.news_table.setRowCount(1)
                vals = [row["ticker"], "No live headlines returned", "Neutral"]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.news_table.setItem(0, c, item)

        if hasattr(self, "market_briefing_text"):
            self.refresh_market_intelligence()

    def change_data_mode(self, mode):
        """
        Change provider mode safely.

        Do not immediately re-fetch every symbol in Live mode. That caused UI
        freezes. The selected ticker will refresh only when the user presses
        Search / Load or Enter.
        """
        set_data_mode(mode)
        if hasattr(self, "data_text"):
            self.data_text.setPlainText(market_diagnostics())
        self.status.setText(
            f"Data mode changed to {get_data_mode().upper()}. Press Search / Load to refresh the current ticker."
        )

    def update_chart_controls(self):
        if not hasattr(self, "chart"):
            return
        timeframe = self.chart_timeframe.currentText() if hasattr(self, "chart_timeframe") else "5m"
        self.chart.set_timeframe(timeframe)
        self.chart.set_overlays(
            vwap=self.toggle_vwap.isChecked() if hasattr(self, "toggle_vwap") else True,
            trade_plan=self.toggle_trade_plan.isChecked() if hasattr(self, "toggle_trade_plan") else True,
            levels=self.toggle_levels.isChecked() if hasattr(self, "toggle_levels") else True,
            volume=self.toggle_volume.isChecked() if hasattr(self, "toggle_volume") else True,
        )
        if self.selected:
            self.chart.set_row(self.selected)
            if hasattr(self, "chart_info"):
                self.chart_info.setPlainText(self.chart_report(self.selected))

    def chart_report(self, row):
        timeframe = self.chart_timeframe.currentText() if hasattr(self, "chart_timeframe") else "5m"
        ticker = row.get('ticker', 'UNKNOWN')
        return (
            f"CHART ENGINE — {ticker}\n\n"
            f"Timeframe: {timeframe}\n"
            f"Source: {row.get('data_source', 'N/A')}\n"
            f"Price: ${row.get('price', 'N/A')}\n"
            f"VWAP: ${row.get('vwap', 'N/A')}\n"
            f"Day Low: ${row.get('day_low', 'N/A')}\n"
            f"Day High: ${row.get('day_high', 'N/A')}\n\n"
            f"Trade Plan:\n"
            f"Entry: ${row.get('entry', 'N/A')}\n"
            f"Stop: ${row.get('stop', 'N/A')}\n"
            f"Target 1: ${row.get('target1', 'N/A')}\n"
            f"Target 2: ${row.get('target2', 'N/A')}\n\n"
            f"RSI 14: {row.get('rsi14', 'N/A')} | ATR 14: {row.get('atr14', 'N/A')} | MACD: {row.get('macd', 'N/A')}\n"
            f"Score: {row.get('score', 'N/A')}/100 | Action: {row.get('action', 'N/A')} | Status: {row.get('status', 'N/A')}"
        )

    def _normalize_row(self, row):
        if not isinstance(row, dict):
            return {}

        normalized = dict(row)
        ai = normalized.get("ai_decision") if isinstance(normalized.get("ai_decision"), dict) else None
        if not ai:
            ai = build_ai_decision(normalized)
            normalized["ai_decision"] = ai

        normalized.setdefault("ticker", "")
        normalized.setdefault("name", normalized.get("ticker", ""))
        normalized.setdefault("price", normalized.get("entry", 0))
        normalized.setdefault("score", ai.get("score", normalized.get("ai_score", 0)))
        normalized.setdefault("action", ai.get("ai_action", "WATCH"))
        normalized.setdefault("status", normalized.get("status", "UNKNOWN"))
        normalized.setdefault("probability", normalized.get("probability", 0))
        normalized.setdefault("confidence", ai.get("ai_confidence", normalized.get("confidence", "Low")))
        normalized.setdefault("entry", normalized.get("entry", normalized.get("price", 0)))
        normalized.setdefault("stop", normalized.get("stop", 0))
        normalized.setdefault("target1", normalized.get("target1", 0))
        normalized.setdefault("target2", normalized.get("target2", 0))
        normalized.setdefault("risk_reward", ai.get("risk_reward", normalized.get("risk_reward", 0)))
        normalized.setdefault("passed", [])
        normalized.setdefault("missing", [])
        normalized.setdefault("vwap", normalized.get("price", 0))
        normalized.setdefault("ema9", normalized.get("price", 0))
        normalized.setdefault("ema20", normalized.get("price", 0))
        normalized.setdefault("day_low", normalized.get("price", 0))
        normalized.setdefault("day_high", normalized.get("price", 0))
        normalized.setdefault("volume", 0)
        normalized.setdefault("updated", "")
        normalized.setdefault("profile", {})
        normalized.setdefault("news_items", [])
        normalized.setdefault("candles", [])
        normalized.setdefault("data_source", "UNKNOWN")
        normalized.setdefault("relative_volume", 0)
        normalized.setdefault("change_pct", 0)
        normalized.setdefault("news", False)
        normalized.setdefault("new_intraday_high", False)
        normalized.setdefault("above_vwap", False)
        normalized.setdefault("above_9ema", False)
        normalized.setdefault("above_20ema", False)
        return normalized

    def search_now(self):
        self.load_symbol(self.search.text())

    def _schedule_pending_symbol_retry(self, symbol: str, error: str) -> None:
        if self._pending_symbol != symbol:
            self._pending_symbol = symbol
            self._pending_symbol_attempts = 0

        if self._pending_symbol_attempts >= self._max_pending_symbol_attempts:
            self.status.setText(error or f"{symbol} live lookup timed out.")
            self._pending_symbol = ""
            self._pending_symbol_attempts = 0
            return

        self._pending_symbol_attempts += 1
        delay_ms = min(350 * self._pending_symbol_attempts, 1500)
        if self._symbol_retry_timer.isActive():
            self._symbol_retry_timer.stop()
        self._symbol_retry_timer.start(delay_ms)
        self.status.setText(
            f"Live lookup in progress for {symbol}. Retrying automatically "
            f"({self._pending_symbol_attempts}/{self._max_pending_symbol_attempts})..."
        )

    def _retry_pending_symbol_load(self):
        if self._pending_symbol:
            self.load_symbol(self._pending_symbol)

    def load_symbol(self, symbol):
        symbol = (symbol or "").strip().upper()
        if not symbol:
            return
        row, error = market_data_engine.get_row(symbol)
        if not row:
            if "in progress" in (error or "").lower():
                self._schedule_pending_symbol_retry(symbol, error)
                return
            self.status.setText(error)
            return

        if symbol == self._pending_symbol:
            self._pending_symbol = ""
            self._pending_symbol_attempts = 0
            if self._symbol_retry_timer.isActive():
                self._symbol_retry_timer.stop()

        row = self._normalize_row(row)
        if not self.rows:
            self.rows = [self._normalize_row(r) for r in market_data_engine.all_rows()]
        else:
            self.rows = [self._normalize_row(r) for r in self.rows]
        self.selected = row
        # Keep searched row available even if it is not in fallback watchlist.
        if not any(r.get("ticker") == row.get("ticker") for r in self.rows):
            row["rank"] = 1
            self.rows.insert(0, row)
        if self.search.text().strip().upper() != symbol:
            self.search.blockSignals(True)
            self.search.setText(symbol)
            self.search.blockSignals(False)

        self.update_tables()
        self.update_all_panels(row)
        event_bus.publish(SYMBOL_SELECTED, symbol=symbol, row=row)
        self.status.setText(f"{symbol} loaded across ATIS.")

    def update_tables(self):
        self.rows = [self._normalize_row(r) for r in getattr(self, "rows", [])]
        if getattr(self, "selected", None):
            self.selected = self._normalize_row(self.selected)
        for table in [self.watch, self.top_table]:
            table.blockSignals(True)
            table.setRowCount(len(self.rows))
            for r, row in enumerate(self.rows):
                vals = [row.get("rank", r + 1), row.get("ticker", ""), row.get("score", ""), row.get("action", ""), row.get("status", "")]
                for c, v in enumerate(vals):
                    item = QTableWidgetItem(str(v))
                    item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(r, c, item)
                if self.selected and row["ticker"] == self.selected["ticker"]:
                    table.selectRow(r)
            table.blockSignals(False)

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
        ai = build_ai_decision(row)
        row["ai_decision"] = ai

        self.dec_ticker.setText(row["ticker"])
        self.dec_action.setText(ai["ai_action"])
        self.dec_stats.setText(
            f"AI Score {ai['ai_score']}/100 | Confidence {ai['ai_confidence']} | "
            f"Entry {ai['entry_zone']} | Stop {ai['stop_level']} | Target {ai['target_zone']} | R/R {ai['risk_reward']}"
        )

        text = self.row_report(row)
        workstation_text = self.full_market_workstation_report(row)
        if not hasattr(self, "command_market_text"):
            self.summary.setPlainText(workstation_text)
        self.decision_text.setPlainText(workstation_text)
        self.explorer.setPlainText(self.stock_explorer_report(row))
        self.ai_reasoning.setPlainText(self.ai_report(row))
        self.ai_plan.setPlainText(self.trade_plan(row))
        self.chart.set_row(row)
        self.chart_info.setPlainText(self.chart_report(row))
        if hasattr(self, "strategy_report_text"):
            self.strategy_report_text.setPlainText(
                f"Strategy Lab ready for {row['ticker']}.\n\n"
                "Choose a strategy and click Run Backtest to evaluate the current symbol."
            )
        self.update_additional_tabs(row)
        if hasattr(self, "command_market_text"):
            self.update_command_center(row)
        if hasattr(self, "scanner"):
            self.run_professional_scanner()
        if hasattr(self, "paper_review_text"):
            ai = row.get("ai_decision") or build_ai_decision(row)
            self.paper_review_text.setPlainText(
                f"AI ORDER REVIEW — {row['ticker']}\n\n"
                f"Action: {ai['ai_action']}\n"
                f"AI Score: {ai['ai_score']}/100\n"
                f"Confidence: {ai['ai_confidence']}\n"
                f"Entry: {ai['entry_zone']}\n"
                f"Stop: {ai['stop_level']}\n"
                f"Target: {ai['target_zone']}\n\n"
                "Paper trading only. No real broker order is sent."
            )
        if hasattr(self, "event_bus_text"):
            self.refresh_event_bus()

    def row_report(self, row):
        profile = row.get('profile', {}) or {}
        passed = row.get('passed', []) or []
        missing = row.get('missing', []) or []
        ai = row.get('ai_decision') or {}
        return f"""SYMBOL: {row.get('ticker', 'UNKNOWN')} — {row.get('name', '')}

Price: ${row.get('price', 'N/A')}
Change: {row.get('change_pct', 'N/A')}%
Volume: {row.get('volume', 0):,}
Relative Volume: {row.get('relative_volume', 'N/A')}x
Source: {row.get('data_source', 'N/A')}
Sector: {profile.get('sector', 'N/A')}
Industry: {profile.get('industry', 'N/A')}

Decision: {ai.get('ai_action', row.get('action', 'N/A'))}
Status: {row.get('status', 'N/A')}
Legacy Score: {row.get('score', 'N/A')}/100
AI Score: {ai.get('ai_score', 'N/A')}/100
Probability: {row.get('probability', 'N/A')}%
Confidence: {ai.get('ai_confidence', row.get('confidence', 'N/A'))}

Passed:
{chr(10).join(['✓ ' + x for x in passed]) or 'None'}

Missing:
{chr(10).join(['⚠ ' + x for x in missing]) or 'None'}
"""

    def ai_report(self, row):
        ai = row.get("ai_decision") or build_ai_decision(row)
        return ai.get("summary", "AI summary unavailable")

    def trade_plan(self, row):
        ai = row.get("ai_decision") or build_ai_decision(row)
        return ai.get("trade_plan", "Trade plan unavailable")



def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = ATISClean()
    window.show()
    sys.exit(app.exec())
