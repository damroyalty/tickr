from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel,
    QLineEdit, QPushButton, QHBoxLayout, QFormLayout,
    QTabWidget, QGroupBox, QGridLayout, QSizePolicy, QMessageBox,
    QComboBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject, QPropertyAnimation, QEasingCurve, QUrl
from PySide6.QtGui import QFont, QColor, QPalette, QLinearGradient, QBrush
from .data import get_stock_data, get_crypto_data
import os
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineWidgets import QWebEngineView


class DataLoader(QObject):
    finished = Signal(dict, bool, str)
    error = Signal(str)

    def __init__(self, query, is_crypto, force_refresh, time_range="1d"):
        super().__init__()
        self.query = query
        self.is_crypto = is_crypto
        self.force_refresh = force_refresh
        self.time_range = time_range

    def run(self):
        try:
            if not self.query:
                self.error.emit("Please enter a valid symbol")
                return

            data = get_crypto_data(self.query, self.force_refresh, self.time_range) if self.is_crypto else get_stock_data(self.query, self.force_refresh, self.time_range)
            
            if data:
                self.finished.emit(data, self.is_crypto, "")
            else:
                self.error.emit(f"No data found for {self.query}. Try a different symbol.")
        except Exception as e:
            self.error.emit(f"Error fetching data: {str(e)}")

def initiate_data_load(self, query, labels_dict, chart_widget, is_crypto, force_refresh=False):
    """Start data loading in a separate thread"""
    if self.data_thread and self.data_thread.isRunning():
        self.data_thread.quit()
        self.data_thread.wait()

    self.data_thread = QThread()
    self.data_loader = DataLoader(query, is_crypto, force_refresh, self.current_time_range)
    self.data_loader.moveToThread(self.data_thread)
    
    self.data_thread.started.connect(self.data_loader.run)
    self.data_loader.finished.connect(self.handle_data_loaded)
    self.data_loader.error.connect(self.handle_data_error)
    self.data_loader.finished.connect(self.data_thread.quit)
    self.data_loader.error.connect(self.data_thread.quit)
    
    self.data_thread.start()

class PriceChangeVisualization(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(50, 50)
        self.setMaximumSize(50, 50)
        self.setAlignment(Qt.AlignCenter)
        self.current_value = 0
        self.previous_value = 0
        self.setStyleSheet("border-radius: 25px;")
        
    def update_value(self, new_value):
        self.previous_value = self.current_value
        self.current_value = new_value
        self.update_visualization()
        
    def update_visualization(self):
        if self.current_value > self.previous_value:
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0, QColor(0, 200, 0))
            gradient.setColorAt(1, QColor(0, 150, 0))
            self.setStyleSheet(f"""
                border-radius: 25px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                stop:0 #00C853, stop:1 #007E33);
            """)
            self.setText("▲")
        elif self.current_value < self.previous_value:
            self.setStyleSheet(f"""
                border-radius: 25px;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                stop:0 #FF5252, stop:1 #B71C1C);
            """)
            self.setText("▼")
        else:
            # Gray for no change
            self.setStyleSheet("""
                border-radius: 25px;
                background-color: #616161;
            """)
            self.setText("━")
            
        self.animate_change()
        
    def animate_change(self):
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(300)
        animation.setEasingCurve(QEasingCurve.OutBack)
        
        start_rect = self.geometry()
        target_rect = start_rect
        
        if self.current_value > self.previous_value:
            target_rect.adjust(-5, -5, 5, 5)
        elif self.current_value < self.previous_value:
            target_rect.adjust(5, 5, -5, -5)
            
        animation.setStartValue(start_rect)
        animation.setEndValue(target_rect)
        animation.start()

class TickrUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ticker")
        self.setMinimumSize(1200, 900)
        self.setWindowIcon(QIcon(r"C:\Users\Loaded.ico"))
        self.current_symbols = {}
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_interval = 10000
        self.data_thread = None
        self.data_loader = None
        self.current_time_range = "1d"

        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        header = QLabel("🥀")
        header.setAlignment(Qt.AlignCenter)
        header_font = QFont("Segoe UI", 24, QFont.Bold)
        header.setFont(header_font)
        header.setStyleSheet("color: #E0E0E0;")
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        
        self.stock_tab = self.build_tab(is_crypto=False)
        self.crypto_tab = self.build_tab(is_crypto=True)

        self.tabs.addTab(self.stock_tab, "Stocks")
        self.tabs.addTab(self.crypto_tab, "Crypto")

        main_layout.addWidget(self.tabs)
        self.refresh_timer.start(self.refresh_interval)

    def apply_dark_theme(self):
        dark_stylesheet = """
            QMainWindow {
                background-color: #121212;
            }
            QTabBar::tab {
                padding: 10px 20px;
                background: #1E1E1E;
                border: 1px solid #444;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 5px;
                color: #E0E0E0;
            }
            QTabBar::tab:selected {
                background: #2A2A2A;
                border-color: #555;
                color: #FFFFFF;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background: #2A2A2A;
                border-radius: 0 5px 5px 5px;
            }
            QGroupBox {
                border: 1px solid #444;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 20px;
                font-size: 14px;
                color: #E0E0E0;
                background-color: #1E1E1E;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: #BB86FC;
            }
            QLabel {
                color: #E0E0E0;
                font-size: 14px;
            }
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 1px solid #555;
                border-radius: 6px;
                background-color: #1E1E1E;
                color: #E0E0E0;
            }
            QLineEdit:focus {
                border: 2px solid #BB86FC;
            }
            QPushButton {
                padding: 10px 15px;
                font-size: 14px;
                background-color: #3700B3;
                color: white;
                border: none;
                border-radius: 6px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #6200EE;
            }
            QPushButton:pressed {
                background-color: #03DAC6;
                color: black;
            }
            QComboBox {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #555;
                border-radius: 6px;
                background-color: #1E1E1E;
                color: #E0E0E0;
                min-width: 120px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E1E;
                color: #E0E0E0;
                selection-background-color: #3700B3;
                selection-color: white;
            }
            QFormLayout {
                color: #E0E0E0;
            }
        """
        self.setStyleSheet(dark_stylesheet)

    def build_tab(self, is_crypto=False):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)

        search_group = QGroupBox("Search")
        search_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(15, 15, 15, 15)
        search_layout.setSpacing(15)
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Enter stock ticker" if not is_crypto else "Enter crypto")
        search_input.setMinimumHeight(40)
        
        search_button = QPushButton("🔍 Search")
        search_button.setMinimumHeight(40)
        search_button.setCursor(Qt.PointingHandCursor)
        
        time_range_combo = QComboBox()
        time_range_combo.addItems(["1h", "1d", "1w", "1m", "3m", "1y", "5y"])
        time_range_combo.setCurrentText("1d")
        time_range_combo.setMinimumHeight(40)
        
        search_layout.addWidget(search_input, stretch=2)
        search_layout.addWidget(time_range_combo)
        search_layout.addWidget(search_button)
        search_group.setLayout(search_layout)

        info_group = QGroupBox("Market Data")
        info_layout = QGridLayout()
        info_layout.setContentsMargins(15, 15, 15, 15)
        info_layout.setSpacing(20)
        
        price_section = self.create_price_section()
        stats_section = self.create_stats_section()
        volume_section = self.create_volume_section()
        
        info_layout.addWidget(price_section, 0, 0)
        info_layout.addWidget(stats_section, 0, 1)
        info_layout.addWidget(volume_section, 1, 0, 1, 2)
        info_group.setLayout(info_layout)

        # Replace ChartWidget with TradingView QWebEngineView
        chart = QWebEngineView()
        chart.setMinimumHeight(350)
        chart.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Set default chart
        if is_crypto:
            chart.setUrl(QUrl("https://www.tradingview.com/chart/?symbol=BINANCE:BTCUSDT"))
        else:
            chart.setUrl(QUrl("https://www.tradingview.com/chart/?symbol=NASDAQ:AAPL"))

        def initiate_search():
            symbol = search_input.text().strip().upper()
            self.current_time_range = time_range_combo.currentText()
            # Update TradingView chart
            if is_crypto:
                chart.setUrl(QUrl(f"https://www.tradingview.com/chart/?symbol=BINANCE:{symbol}USDT"))
            else:
                # Guess exchange for TradingView (improve as needed)
                nasdaq = {"AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", "NVDA", "META", "QQQ"}
                if symbol == "SPY":
                    tvsym = f"AMEX:{symbol}"
                elif symbol in nasdaq:
                    tvsym = f"NASDAQ:{symbol}"
                else:
                    tvsym = f"NYSE:{symbol}"
                chart.setUrl(QUrl(f"https://www.tradingview.com/chart/?symbol={tvsym}"))
            # ...existing code to fetch and update market data...
            self.initiate_data_load(
                symbol,
                {
                    'price_labels': price_section.property('labels'),
                    'stats_labels': stats_section.property('labels'),
                    'volume_labels': volume_section.property('labels')
                },
                chart,
                is_crypto
            )

        search_button.clicked.connect(initiate_search)
        search_input.returnPressed.connect(initiate_search)

        tab_layout.addWidget(search_group)
        tab_layout.addWidget(info_group)
        tab_layout.addWidget(chart, stretch=1)

        tab.info_group = info_group
        tab.chart = chart
        tab.is_crypto = is_crypto
        tab.search_input = search_input
        tab.price_section = price_section
        tab.stats_section = stats_section
        tab.volume_section = volume_section
        tab.time_range_combo = time_range_combo

        return tab

    def initiate_data_load(self, query, labels_dict, chart_widget, is_crypto, force_refresh=False):
        """Start data loading in a separate thread"""
        if self.data_thread and self.data_thread.isRunning():
            self.data_thread.quit()
            self.data_thread.wait()

        self.data_thread = QThread()
        self.data_loader = DataLoader(query, is_crypto, force_refresh, self.current_time_range)
        self.data_loader.moveToThread(self.data_thread)
        
        self.data_thread.started.connect(self.data_loader.run)
        self.data_loader.finished.connect(self.handle_data_loaded)
        self.data_loader.error.connect(self.handle_data_error)
        self.data_loader.finished.connect(self.data_thread.quit)
        self.data_loader.error.connect(self.data_thread.quit)
        
        self.data_thread.start()

    def handle_data_loaded(self, data, is_crypto, error_message):
        """Handle successfully loaded data"""
        tab = self.crypto_tab if is_crypto else self.stock_tab
        self.update_display(
            data,
            {
                'price_labels': tab.price_section.property('labels'),
                'stats_labels': tab.stats_section.property('labels'),
                'volume_labels': tab.volume_section.property('labels')
            },
            tab.chart
        )

    def handle_data_error(self, error_message):
        """Handle data loading errors"""
        QMessageBox.warning(self, "Error", error_message)

    def create_price_section(self):
        group = QGroupBox("Price Information")
        layout = QHBoxLayout()
        form_layout = QFormLayout()
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(10)
        
        labels = {
            'current': QLabel("$--"),
            'open': QLabel("$--"),
            'prev_close': QLabel("$--"),
            'change': QLabel("+0.00 (0.00%)"),
            'visualization': PriceChangeVisualization()
        }
        
        labels['current'].setFont(QFont("Segoe UI", 18, QFont.Bold))
        labels['current'].setStyleSheet("color: #BB86FC;")
        
        form_layout.addRow(QLabel("<b>Current Price:</b>"), labels['current'])
        form_layout.addRow(QLabel("<b>Today's Open:</b>"), labels['open'])
        form_layout.addRow(QLabel("<b>Previous Close:</b>"), labels['prev_close'])
        form_layout.addRow(QLabel("<b>Change:</b>"), labels['change'])
        
        layout.addLayout(form_layout)
        layout.addWidget(labels['visualization'], alignment=Qt.AlignRight | Qt.AlignVCenter)
        
        group.setLayout(layout)
        group.setProperty('labels', labels)
        return group

    def create_stats_section(self):
        group = QGroupBox("Statistics")
        layout = QFormLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        labels = {
            'high': QLabel("$--"),
            'low': QLabel("$--"),
            'pe_ratio': QLabel("--"),
            'market_cap': QLabel("$--")
        }
        
        layout.addRow(QLabel("<b>52W High:</b>"), labels['high'])
        layout.addRow(QLabel("<b>52W Low:</b>"), labels['low'])
        layout.addRow(QLabel("<b>P/E Ratio:</b>"), labels['pe_ratio'])
        layout.addRow(QLabel("<b>Market Cap:</b>"), labels['market_cap'])
        
        group.setLayout(layout)
        group.setProperty('labels', labels)
        return group

    def create_volume_section(self):
        group = QGroupBox("Volume & Liquidity")
        layout = QFormLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        labels = {
            'volume': QLabel("--"),
            'avg_volume': QLabel("--"),
            'bid_ask': QLabel("-- / --")
        }
        
        layout.addRow(QLabel("<b>Current Volume:</b>"), labels['volume'])
        layout.addRow(QLabel("<b>Avg. Volume:</b>"), labels['avg_volume'])
        layout.addRow(QLabel("<b>Bid/Ask:</b>"), labels['bid_ask'])
        
        group.setLayout(layout)
        group.setProperty('labels', labels)
        return group

    def update_display(self, data, labels_dict, chart_widget):
        try:
            price_labels = labels_dict['price_labels']
            stats_labels = labels_dict['stats_labels']
            volume_labels = labels_dict['volume_labels']

            def format_value(value, prefix='', suffix='', default='--'):
                try:
                    if value is None or str(value).lower() == 'nan':
                        return default
                    if isinstance(value, (int, float)):
                        return f"{prefix}{value:,.2f}{suffix}"
                    return f"{prefix}{value}{suffix}"
                except:
                    return default

            change = data.get('change', 0)
            change_color = "#03DAC6" if change >= 0 else "#CF6679"
            
            current_price = format_value(data.get('current'), '$')
            price_labels['current'].setText(current_price)
            
            try:
                current_price_num = float(data.get('current', 0))
                price_labels['visualization'].update_value(current_price_num)
            except (ValueError, TypeError):
                pass
            
            price_labels['open'].setText(format_value(data.get('open'), '$'))
            price_labels['prev_close'].setText(format_value(data.get('prev_close'), '$'))
            
            change_text = (
                f"<span style='color:{change_color}'>"
                f"{'+' if change >= 0 else ''}"
                f"{format_value(change, '', '')} "
                f"({format_value(data.get('change_percent'), '', '%')})"
                f"</span>"
            )
            price_labels['change'].setText(change_text)

            stats_labels['high'].setText(format_value(data.get('high'), '$'))
            stats_labels['low'].setText(format_value(data.get('low'), '$'))
            stats_labels['pe_ratio'].setText(format_value(data.get('pe_ratio')))
            stats_labels['market_cap'].setText(format_value(data.get('market_cap'), '$'))

            volume_labels['volume'].setText(format_value(data.get('volume'), default='0'))
            volume_labels['avg_volume'].setText(format_value(data.get('avg_volume')))
            bid = format_value(data.get('bid'), '$')
            ask = format_value(data.get('ask'), '$')
            volume_labels['bid_ask'].setText(f"{bid} / {ask}")

            chart_data = data.get('data', [])
            symbol = data.get('symbol', '')
            if chart_data and isinstance(chart_data, list) and len(chart_data) > 0:
                chart_widget.update_chart(chart_data, f"{symbol} Price History - {self.current_time_range}")
            else:
                chart_widget.update_chart([], "")

        except Exception as e:
            print(f"Error in update_display: {str(e)}")
            import traceback
            traceback.print_exc()

    def refresh_data(self):
        """Refresh data for all active tabs"""
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'search_input') and tab.search_input.text():
                self.current_time_range = tab.time_range_combo.currentText()
                self.initiate_data_load(
                    tab.search_input.text().strip(),
                    {
                        'price_labels': tab.price_section.property('labels'),
                        'stats_labels': tab.stats_section.property('labels'),
                        'volume_labels': tab.volume_section.property('labels')
                    },
                    tab.chart,
                    tab.is_crypto,
                    force_refresh=True
                )

    def closeEvent(self, event):
        """Clean up threads when closing the window"""
        if self.data_thread and self.data_thread.isRunning():
            self.data_thread.quit()
            self.data_thread.wait()
        event.accept()