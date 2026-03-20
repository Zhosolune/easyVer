from enum import Enum
from pathlib import Path

from qfluentwidgets import StyleSheetBase, Theme, qconfig


class StyleSheet(StyleSheetBase, Enum):
    """ Style sheet  """

    WELCOME_PAGE = "welcome_page"
    REPO_PAGE = "repo_page"
    SETTING_PAGE = "setting_page"

    def path(self, theme=Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme
        res_path = f":/easyVer/qss/{theme.value.lower()}/{self.value}.qss"
        
        # 检查资源文件是否已编译，如果没有编译则回退到读取本地文件（方便开发调试）
        from PyQt6.QtCore import QFile
        if QFile.exists(res_path):
            return res_path
            
        qss_path = Path(__file__).parent.parent / "resources" / "qss" / theme.value.lower() / f"{self.value}.qss"
        return str(qss_path.absolute()).replace("\\", "/")