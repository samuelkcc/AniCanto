"""One line-icon family for navigation and controls on Windows/Qt."""
from PySide6.QtCore import QByteArray,Qt
from PySide6.QtGui import QIcon,QPixmap,QPainter,QColor
from PySide6.QtSvg import QSvgRenderer
PATHS={
'edit':'<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4M6 8h12M8 6v4M6 12h12M16 10v4"/>',
'roles':'<circle cx="9" cy="8" r="3"/><circle cx="18" cy="9" r="2"/><path d="M2 21v-3a7 7 0 0 1 14 0v3M17 14a5 5 0 0 1 5 5v2"/>',
'review':'<path d="m3 6 1 1 2-3m-3 8 1 1 2-3m-3 8 1 1 2-3M10 6h11M10 12h11M10 18h11"/>',
'export':'<path d="M5 10v10h14V10M12 15V2m-4 4 4-4 4 4"/>',
'queue':'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h2m2 0h8M6 12h2m2 0h8M6 16h2m2 0h8"/>',
'terminal':'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m6 9 3 3-3 3m6 0h5"/>',
'sliders':'<path d="M3 6h18M3 12h18M3 18h18"/><rect x="6" y="4" width="3" height="4" rx="1"/><rect x="14" y="10" width="3" height="4" rx="1"/><rect x="9" y="16" width="3" height="4" rx="1"/>',
'model':'<path d="m12 2 10 5v10l-10 5-10-5V7l10-5Zm-10 5 10 5 10-5M12 12v10M7 4.5l10 5v10"/>',
'settings':'<path d="m9 3 1-2h4l1 2 2 1 3-.2 2 3-1 2v4l1 2-2 3-3-.2-2 1-1 2h-4l-1-2-2-1-3 .2-2-3 1-2V9L2 7l2-3 3 .2 2-1Z"/><circle cx="12" cy="11" r="3"/>',
'folder':'<path d="M2 7V4h7l3 3h10v14H2V7Z"/>',
'plus':'<path d="M12 4v16M4 12h16"/>','close':'<path d="m6 6 12 12M6 18 18 6"/>',
'play':'<path d="m7 4 14 8-14 8V4Z"/>','pause':'<rect x="5" y="4" width="4" height="16"/><rect x="15" y="4" width="4" height="16"/>','stop':'<rect x="5" y="5" width="14" height="14" rx="1"/>',
'undo':'<path d="m8 5-5 5 5 5M3 10h12a5 5 0 0 1 0 10h-3"/>','redo':'<path d="m16 5 5 5-5 5m5-5H9a5 5 0 0 0 0 10h3"/>',
'save':'<path d="M3 3h18v18H3V3Zm4 0v7h10V3M7 21v-7h10v7"/>',
'navigation':'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M8 4v16M4 8h2m-2 4h2m-2 4h2"/>','browser':'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M8 4v16"/>','inspector':'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M16 4v16"/>',
'layout':'<rect x="2" y="3" width="8" height="9" rx="1"/><rect x="14" y="3" width="8" height="9" rx="1"/><rect x="2" y="16" width="20" height="5" rx="1"/>',
'guide':'<circle cx="12" cy="12" r="10"/><path d="M9 8a3 3 0 0 1 6 1c0 2-3 2-3 5m0 3v1"/>','about':'<circle cx="12" cy="12" r="10"/><path d="M12 10v8m0-12v1"/>',
'welcome':'<path d="m2 11 10-9 10 9M5 9v12h5v-7h4v7h5V9"/>',
'sparkles':'<path d="m12 2 2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5L12 2Z"/>',
'volume':'<path d="M3 9h4l5-5v16l-5-5H3V9Zm13-2a7 7 0 0 1 0 10m3-13a11 11 0 0 1 0 16"/>',
'captions':'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M10 9H6v6h4m8-6h-4v6h4"/>',
'wave':'<path d="M2 10v4m4-8v12M10 2v20m4-16v12m4-10v8m4-6v4"/>',
'chevron-left':'<path d="m15 4-8 8 8 8"/>','chevron-right':'<path d="m9 4 8 8-8 8"/>',
'scissors':'<circle cx="5" cy="5" r="3"/><circle cx="5" cy="19" r="3"/><path d="m8 7 13 14M8 17 21 3"/>',
'crop':'<path d="M7 2v15h15M2 7h15v15"/>','zoom-in':'<circle cx="10" cy="10" r="7"/><path d="m15 15 7 7M6 10h8m-4-4v8"/>','zoom-out':'<circle cx="10" cy="10" r="7"/><path d="m15 15 7 7M6 10h8"/>',
'loop':'<path d="M3 8h15l-3-3m3 3-3 3M21 16H6l3 3m-3-3 3-3"/>','trash':'<path d="M3 5h18M8 5V2h8v3M5 5l1 17h12l1-17M10 9v8m4-8v8"/>'}
def icon(name,color='#5d6067',size=20):
    body=PATHS.get(name,PATHS['sliders']);image=QPixmap(size*2,size*2);image.fill(Qt.transparent)
    renderer=QSvgRenderer(QByteArray((f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.55" stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>').encode()))
    painter=QPainter(image);renderer.render(painter);painter.end();image.setDevicePixelRatio(2);return QIcon(image)
