from PyQt6.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """全局信号总线。"""
    


# 单例
signalBus = SignalBus()