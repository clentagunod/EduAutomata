def stylesheet(dark: bool) -> str:
    if dark:
        background = "#121212"
        surface = "#1d1d1d"
        raised = "#292929"
        text = "#f4f4f4"
        muted = "#aaaaaa"
        border = "#3b3b3b"
        selected = "#dedede"
        selected_text = "#111111"
    else:
        background = "#ffffff"
        surface = "#f5f5f5"
        raised = "#ebebeb"
        text = "#111111"
        muted = "#686868"
        border = "#dedede"
        selected = "#202020"
        selected_text = "#ffffff"

    return f"""
    QWidget {{
        background: {background};
        color: {text};
        font-family: "Segoe UI", Arial;
        font-size: 13px;
    }}
    QMainWindow, QDialog {{ background: {background}; }}
    QLabel {{ background: transparent; }}
    QLabel#eyebrow, QLabel#label {{
        color: {muted};
        font-size: 10px;
        font-weight: 700;
    }}
    QLabel#title {{ font-size: 24px; font-weight: 700; }}
    QLabel#learnerName {{ font-size: 19px; font-weight: 600; }}
    QLabel#muted {{ color: {muted}; }}
    QLabel#footer {{ color: {muted}; font-size: 11px; }}
    QLabel#footer a {{ color: {text}; text-decoration: underline; }}
    QLabel#notification {{
        color: {text};
        background: {surface};
        border-left: 3px solid {border};
        border-radius: 4px;
        padding: 5px 10px;
        font-size: 12px;
    }}
    QLabel#notification[severity="success"] {{ border-left-color: #39866b; }}
    QLabel#notification[severity="warning"] {{ border-left-color: #c88735; }}
    QLabel#notification[severity="error"] {{ border-left-color: #c35c52; }}
    QLineEdit, QComboBox {{
        background: {surface};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 9px 11px;
        selection-background-color: {selected};
        selection-color: {selected_text};
    }}
    QLineEdit:focus, QComboBox:focus {{ border: 1px solid {text}; }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background: {surface};
        color: {text};
        selection-background-color: {raised};
        selection-color: {text};
    }}
    QFrame#learnerCard, QFrame#summarySection {{
        background: {surface};
        border: 1px solid {border};
        border-radius: 7px;
    }}
    QTableView {{
        background: {surface};
        alternate-background-color: {raised};
        color: {text};
        border: 1px solid {border};
        gridline-color: {border};
        selection-background-color: {selected};
        selection-color: {selected_text};
    }}
    QHeaderView::section {{
        background: {raised};
        color: {text};
        border: 0;
        border-right: 1px solid {border};
        border-bottom: 1px solid {border};
        padding: 8px;
        font-weight: 700;
    }}
    QPushButton {{
        background: {surface};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
        padding: 8px 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {raised}; }}
    QPushButton#primary {{
        background: {selected};
        color: {selected_text};
        border-color: {selected};
        font-size: 14px;
        font-weight: 700;
    }}
    QPushButton#primary:hover {{ background: {text}; color: {background}; }}
    QTabWidget::pane {{ border: 1px solid {border}; border-radius: 6px; }}
    QTabBar::tab {{
        background: {surface};
        color: {muted};
        border: 1px solid {border};
        padding: 9px 16px;
        margin-right: 4px;
    }}
    QTabBar::tab:selected {{ background: {background}; color: {text}; }}
    QGroupBox {{
        border: 1px solid {border};
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 12px;
        font-weight: 700;
    }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 5px; }}
    QDialogButtonBox QPushButton {{ min-width: 82px; }}
    """
