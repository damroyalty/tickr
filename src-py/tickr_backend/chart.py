from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

class ChartWidget(QWidget):
    def __init__(self, data, title=""):
        super().__init__()
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        
        self.update_chart(data, title)
    
    def update_chart(self, data, title):
        self.ax.clear()
        
        if data:
            self.ax.plot(data, color='#1f77b4')
            self.ax.set_title(title, fontsize=12)
            self.ax.set_xlabel("Days", fontsize=10)
            self.ax.set_ylabel("Price (USD)", fontsize=10)
            self.ax.grid(True, linestyle='--', alpha=0.7)
        
        self.canvas.draw()