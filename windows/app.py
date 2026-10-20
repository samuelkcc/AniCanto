"""AniCanto Windows test desktop. UI never loads an AI model on its event thread."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SHARED = HERE / 'shared' if (HERE / 'shared').is_dir() else HERE.parent / 'Resources'
sys.path.insert(0, str(SHARED))
from worker import parse_srt, atomic_json
from gpu import data_root
from install import env_python
from PySide6.QtCore import QProcess, QUrl, Qt
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QPushButton, QLabel, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QPlainTextEdit,
    QFileDialog, QMessageBox, QSplitter, QProgressBar)


def entry_args(script, args):
    return ['--child-script', str(HERE / script), *map(str, args)] if getattr(sys, 'frozen', False) else [str(HERE / script), *map(str, args)]


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.root = data_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.cues = []
        self.active_action = None
        self.output_buffer = ''
        self.job_buttons = []
        version_file=HERE/'VERSION.json'
        if not version_file.is_file():version_file=HERE.parent/'VERSION.json'
        version=json.loads(version_file.read_text(encoding='utf-8'))['version']
        self.setWindowTitle(f'AniCanto Windows · {version} · Architecture preview')
        self.resize(1440, 1000)
        self.setMinimumSize(1000, 760)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.workspace()
        self.settings()
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        self.restore()

    def button(self, label, callback, layout, job=False):
        button = QPushButton(label)
        button.clicked.connect(callback)
        layout.addWidget(button)
        if job:
            self.job_buttons.append(button)
        return button

    def file_row(self, label, layout, save=False, filter='All files (*)'):
        row = QHBoxLayout()
        edit = QLineEdit()
        edit.setPlaceholderText(label)
        row.addWidget(edit)
        def choose():
            value, _ = (QFileDialog.getSaveFileName if save else QFileDialog.getOpenFileName)(self, label, '', filter)
            if value:
                edit.setText(value)
        self.button('Browse…', choose, row)
        layout.addRow(label, row)
        return edit

    def workspace(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.tabs.addTab(widget, 'Dubbing workspace')
        notice = QLabel('Windows test edition · Review translated words, role references and generated voices before accepting a movie.')
        notice.setWordWrap(True)
        layout.addWidget(notice)
        form = QFormLayout()
        self.movie = self.file_row('Source movie', form, filter='Movies (*.mp4 *.mkv *.mov *.avi);;All files (*)')
        self.output = self.file_row('New output movie', form, save=True, filter='MP4 (*.mp4)')
        layout.addLayout(form)
        tools = QHBoxLayout()
        self.button('Import SRT…', self.import_srt, tools, True)
        self.button('Extract embedded SRT', self.extract_srt, tools, True)
        self.button('Open project…', self.open_project, tools, True)
        self.button('Save project…', self.save_project, tools)
        self.button('Translate draft', lambda: self.start_job('translate'), tools, True)
        self.button('Generate & export', lambda: self.start_job('render'), tools, True)
        layout.addLayout(tools)
        splitter = QSplitter(Qt.Vertical)
        self.video = QVideoWidget()
        self.video.setMinimumHeight(180)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        splitter.addWidget(self.video)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['Start (s)', 'End (s)', 'Japanese / source', 'Approved Cantonese / English', 'Role'])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 95)
        self.table.setColumnWidth(1, 95)
        self.table.setColumnWidth(4, 80)
        self.table.setWordWrap(True)
        self.table.setFont(QFont('', 14))
        self.table.setMinimumHeight(200)
        self.table.itemDoubleClicked.connect(self.seek_line)
        splitter.addWidget(self.table)
        splitter.setSizes([240, 350])
        layout.addWidget(splitter, 1)
        playback = QHBoxLayout()
        self.button('Play source', self.play_source, playback)
        self.button('Pause', self.player.pause, playback)
        self.button('Play new output', self.play_output, playback)
        self.button('Open data / reports', lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.root))), playback)
        self.cancel = self.button('Cancel & keep recordings', self.stop_job, playback)
        self.cancel.setEnabled(False)
        layout.addLayout(playback)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1500)
        self.log.setMaximumHeight(130)
        layout.addWidget(self.log)

    def settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.tabs.addTab(widget, 'Hardware & voices')
        form = QFormLayout()
        self.backend = QComboBox()
        for label, value in [('Automatic hardware selection', 'auto'), ('NVIDIA · CUDA / RTX 4090', 'nvidia'),
                             ('Supported AMD Radeon · ROCm', 'amd'), ('Intel Arc · XPU for Qwen', 'intel'), ('CPU compatibility', 'cpu')]:
            self.backend.addItem(label, value)
        form.addRow('Install runtime for', self.backend)
        preferred = self.backend.findData(os.environ.get('CANTOSYNC_SETUP_BACKEND', 'auto'))
        self.backend.setCurrentIndex(max(0, preferred))
        self.engine = QComboBox()
        for label, value in [('CosyVoice 3 · Cantonese / English', 'cosy'), ('GPT-SoVITS V4 · Cantonese / English', 'gpt'),
                             ('Qwen3-TTS · English / experimental Cantonese', 'qwen')]:
            self.engine.addItem(label, value)
        form.addRow('Voice engine', self.engine)
        self.render_mode=QComboBox()
        self.render_mode.addItem('Detailed (default)',32)
        self.render_mode.addItem('Balanced (faster)',16)
        form.addRow('V4 rendering quality',self.render_mode)
        self.qwen_model = QComboBox()
        self.qwen_model.addItem('1.7B Base · RTX 4090 / larger GPUs', 'qwen-large')
        self.qwen_model.addItem('0.6B Base · lower memory', 'qwen-small')
        form.addRow('Qwen model size', self.qwen_model)
        self.language = QComboBox()
        self.language.addItem('廣東話 · Cantonese', 'yue')
        self.language.addItem('English', 'en')
        form.addRow('Target language', self.language)
        self.device = QComboBox()
        for value in ['auto', 'cuda', 'xpu', 'cpu']:
            self.device.addItem(value)
        form.addRow('Inference device (auto recommended)', self.device)
        self.gpu_index = QSpinBox()
        self.gpu_index.setRange(0, 8)
        form.addRow('Compute GPU index', self.gpu_index)
        self.encoder = QComboBox()
        for label, value in [('Automatic GPU encoder', 'auto'), ('NVIDIA NVENC', 'nvidia'), ('AMD AMF', 'amd'), ('Intel Quick Sync', 'intel'), ('Software', 'software')]:
            self.encoder.addItem(label, value)
        form.addRow('Video export', self.encoder)
        self.text_model = QLineEdit('qwen3:8b')
        form.addRow('Installed Ollama translation model', self.text_model)
        self.start = QDoubleSpinBox()
        self.start.setRange(0, 86400)
        self.start.setDecimals(2)
        self.length = QDoubleSpinBox()
        self.length.setRange(0, 86400)
        self.length.setValue(30)
        self.length.setSpecialValueText('Full movie')
        form.addRow('Test clip start (seconds)', self.start)
        form.addRow('Test clip length (0 = full movie)', self.length)
        self.background = self.file_row('Optional isolated background WAV', form, filter='Audio (*.wav *.flac)')
        layout.addLayout(form)
        self.capabilities = QLabel('NVIDIA: native CUDA voices + NVENC. Supported AMD: native ROCm voices + AMF.\nIntel: Qwen XPU; GPT/Cosy CPU + Quick Sync. ONNX voice tokenizers use CPU in this beta.\nImport text SRT or embedded text subtitles. Automatic ASR, visual cast identity, separation,\nseven-track export and the full Mac timeline editor are not yet ported. Supply an isolated\nbackground WAV to retain music/effects; without it the dubbed track contains dialogue only.')
        self.capabilities.setWordWrap(True)
        layout.addWidget(self.capabilities)
        row = QHBoxLayout()
        self.button('Install selected voice engine', self.setup_voice, row, True)
        self.button('Test selected GPU runtime', self.probe_gpu, row, True)
        self.button('Detect graphics cards', self.detect_gpu, row, True)
        self.button('Ollama setup guide', lambda: QDesktopServices.openUrl(QUrl('https://docs.ollama.com/windows')), row)
        layout.addLayout(row)
        layout.addWidget(QLabel('Role references · assign these IDs in the last subtitle column. Use clean 3–10 s recordings.'))
        self.roles = QTableWidget(1, 4)
        self.roles.setHorizontalHeaderLabels(['Role ID', 'Reference recording path', 'Recording transcript (GPT)', 'Language: ja / yue / en'])
        self.roles.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.roles.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.roles.setColumnWidth(0, 95)
        self.roles.setColumnWidth(3, 210)
        self.roles.setItem(0, 0, QTableWidgetItem('A'))
        self.roles.setItem(0, 3, QTableWidgetItem('ja'))
        layout.addWidget(self.roles, 1)
        row = QHBoxLayout()
        self.button('Add role', lambda: self.roles.insertRow(self.roles.rowCount()), row)
        self.button('Choose reference for role', self.choose_reference, row)
        layout.addLayout(row)

    def fill_cues(self, cues):
        self.cues = cues
        self.table.setRowCount(len(cues))
        for i, cue in enumerate(cues):
            for j, value in enumerate([cue['start'], cue['end'], cue['text'], cue.get('target', ''), cue.get('role', 'A')]):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))
            self.table.setRowHeight(i, 74)

    def read_table(self):
        def value(table, row, column):
            item = table.item(row, column)
            return item.text().strip() if item else ''
        cues = [dict(start=float(value(self.table, i, 0)), end=float(value(self.table, i, 1)), text=value(self.table, i, 2),
                     target=value(self.table, i, 3), role=value(self.table, i, 4) or 'A') for i in range(self.table.rowCount())]
        profiles = [dict(id=value(self.roles, i, 0), name=value(self.roles, i, 0), reference=value(self.roles, i, 1),
                         promptText=value(self.roles, i, 2), language=value(self.roles, i, 3) or 'ja') for i in range(self.roles.rowCount()) if value(self.roles, i, 0)]
        ids = [p['id'] for p in profiles]
        if len(ids) != len(set(ids)):
            raise ValueError('Each role needs a unique ID.')
        return dict(input=self.movie.text(), output=self.output.text(), cues=cues, profiles=profiles,
                    engine=self.engine.currentData(), gsvSampleSteps=self.render_mode.currentData(), qwenModel=self.qwen_model.currentData(), language=self.language.currentData(), device=self.device.currentText(),
                    gpuIndex=self.gpu_index.value(), videoAcceleration=self.encoder.currentData(),
                    textModel=self.text_model.text(), startOffset=self.start.value(), duration=self.length.value(),
                    background=self.background.text(), backend=self.backend.currentData())

    def apply_project(self, cfg):
        self.movie.setText(cfg.get('input', ''))
        self.output.setText(cfg.get('output', ''))
        self.background.setText(cfg.get('background', ''))
        self.text_model.setText(cfg.get('textModel', 'qwen3:8b'))
        for widget, key in [(self.render_mode,'gsvSampleSteps'),(self.engine, 'engine'), (self.qwen_model, 'qwenModel'), (self.language, 'language'), (self.backend, 'backend'), (self.encoder, 'videoAcceleration')]:
            index = widget.findData(cfg.get(key))
            if index >= 0:
                widget.setCurrentIndex(index)
        self.device.setCurrentText(cfg.get('device', 'auto'))
        self.gpu_index.setValue(cfg.get('gpuIndex', 0))
        self.start.setValue(cfg.get('startOffset', 0))
        self.length.setValue(cfg.get('duration', 30))
        self.fill_cues(cfg.get('cues', []))
        profiles = cfg.get('profiles', [dict(id='A', language='ja')])
        self.roles.setRowCount(len(profiles))
        for i, p in enumerate(profiles):
            for j, key in enumerate(['id', 'reference', 'promptText', 'language']):
                self.roles.setItem(i, j, QTableWidgetItem(p.get(key, '')))

    def restore(self):
        path = self.root / 'last-workspace.json'
        try:
            if path.is_file():
                self.apply_project(json.loads(path.read_text(encoding='utf-8')))
        except (ValueError, OSError, KeyError) as error:
            self.log.appendPlainText('Saved workspace could not be restored: '+str(error))

    def import_srt(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import subtitles', '', 'SubRip (*.srt)')
        if path:
            try:
                self.fill_cues(parse_srt(Path(path).read_text(encoding='utf-8-sig')))
            except Exception as error:
                self.show_error(error)

    def open_project(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open Windows project', '', 'AniCanto Windows (*.anicantowin.json)')
        if path:
            try:
                self.apply_project(json.loads(Path(path).read_text(encoding='utf-8')))
            except Exception as error:
                self.show_error(error)

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Save Windows project', '', 'AniCanto Windows (*.anicantowin.json)')
        if path:
            try:
                atomic_json(path, self.read_table())
            except Exception as error:
                self.show_error(error)

    def choose_reference(self):
        row = max(0, self.roles.currentRow())
        if not self.roles.rowCount():
            self.roles.insertRow(0)
        path, _ = QFileDialog.getOpenFileName(self, 'Clean 3–10 second role reference', '', 'Audio (*.wav *.flac *.mp3 *.m4a)')
        if path:
            self.roles.setItem(row, 1, QTableWidgetItem(path))

    def play_source(self):
        self.player.setSource(QUrl.fromLocalFile(self.movie.text()))
        self.player.play()

    def play_output(self):
        self.player.setSource(QUrl.fromLocalFile(self.output.text()))
        self.player.play()

    def seek_line(self, item):
        try:
            if self.player.source() != QUrl.fromLocalFile(self.movie.text()):
                self.player.setSource(QUrl.fromLocalFile(self.movie.text()))
            self.player.setPosition(round(float(self.table.item(item.row(), 0).text())*1000))
            self.player.play()
        except ValueError as error:
            self.show_error(error)

    def launch(self, program, args, action):
        if self.process.state() != QProcess.NotRunning:
            return
        self.active_action = action
        self.output_buffer = ''
        self.progress.setValue(0)
        self.log.appendPlainText('Starting '+action+'…')
        self.tabs.setCurrentIndex(0)
        self.cancel.setEnabled(True)
        for button in self.job_buttons:
            button.setEnabled(False)
        self.process.start(str(program), list(map(str, args)))

    def start_job(self, action):
        try:
            cfg = self.read_table()
            cfg['result'] = str(self.root / f'draft-{time.time_ns()}.json')
            self.result_path = Path(cfg['result'])
            request = self.root / f'request-{time.time_ns()}.json'
            atomic_json(request, cfg)
            atomic_json(self.root / 'last-workspace.json', cfg)
            self.launch(sys.executable, entry_args('jobs.py', [action, request]), action)
        except Exception as error:
            self.show_error(error)

    def extract_srt(self):
        self.result_path = self.root / f'embedded-{time.time_ns()}.srt'
        request = self.root / f'request-{time.time_ns()}.json'
        atomic_json(request, dict(input=self.movie.text(), result=str(self.result_path)))
        self.launch(sys.executable, entry_args('jobs.py', ['extract-subtitles', request]), 'extract-subtitles')

    def setup_voice(self):
        self.launch(sys.executable, entry_args('install.py', [self.engine.currentData(), '--backend', self.backend.currentData(), '--qwen-model', self.qwen_model.currentData()]), 'setup')

    def probe_gpu(self):
        python = env_python(self.engine.currentData())
        if not python.is_file():
            self.show_error('Install the selected voice engine first.')
            return
        self.launch(python, [HERE / 'gpu.py', '--probe', self.engine.currentData(), '--device', self.device.currentText(), '--index', str(self.gpu_index.value())], 'GPU test')

    def detect_gpu(self):
        self.launch(sys.executable, entry_args('gpu.py', []), 'graphics detection')

    def read_output(self):
        self.output_buffer += bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace')
        while '\n' in self.output_buffer:
            line, self.output_buffer = self.output_buffer.split('\n', 1)
            self.handle_line(line)

    def handle_line(self, line):
        try:
            obj = json.loads(line)
            if obj.get('hardware'):
                self.log.appendPlainText(json.dumps(obj['hardware'], ensure_ascii=False))
            self.log.appendPlainText(obj.get('message', json.dumps(obj, ensure_ascii=False)))
            if isinstance(obj.get('progress'), (int, float)):
                self.progress.setValue(round(obj['progress']*100))
        except ValueError:
            if line.strip():
                self.log.appendPlainText(line.strip())
        self.session_log.write(line+'\n') if hasattr(self, 'session_log') else None

    def finished(self, code, status):
        if self.output_buffer:
            self.handle_line(self.output_buffer)
            self.output_buffer = ''
        action = self.active_action
        if code == 0:
            try:
                if action == 'translate':
                    self.fill_cues(json.loads(self.result_path.read_text(encoding='utf-8'))['cues'])
                elif action == 'extract-subtitles':
                    self.fill_cues(parse_srt(self.result_path.read_text(encoding='utf-8-sig')))
            except Exception as error:
                self.show_error(error)
            self.log.appendPlainText(action+' finished.')
        else:
            self.log.appendPlainText(action+' stopped or failed. See diagnostics above; recordings remain saved.')
        self.active_action = None
        self.cancel.setEnabled(False)
        for button in self.job_buttons:
            button.setEnabled(True)

    def process_error(self, error):
        if error == QProcess.FailedToStart:
            self.log.appendPlainText('Could not start runtime: '+self.process.errorString())
            self.finished(1, QProcess.CrashExit)

    def stop_job(self):
        if self.process.state() == QProcess.NotRunning:
            return
        if sys.platform == 'win32':
            subprocess.run(['taskkill.exe', '/PID', str(self.process.processId()), '/T', '/F'], capture_output=True)
        else:
            import signal
            try:
                os.killpg(self.process.processId(), signal.SIGTERM)
            except ProcessLookupError:
                pass
        self.process.kill()

    def show_error(self, error):
        QMessageBox.warning(self, 'AniCanto Windows', str(error))

    def closeEvent(self, event):
        try:
            atomic_json(self.root / 'last-workspace.json', self.read_table())
        except Exception as error:
            self.show_error(error)
            event.ignore()
            return
        self.stop_job()
        self.player.stop()
        if hasattr(self, 'session_log'):
            self.session_log.close()
        event.accept()


def configure_app(app):
    app.setStyle('Fusion')
    app.setFont(QFont('', 11))
    app.setStyleSheet('QMainWindow,QWidget { background:#182234; color:#eef2ff; } QPushButton { background:#32466a; border:1px solid #5872a1; border-radius:5px; padding:8px; } QPushButton:disabled { color:#8893a8; } QLineEdit,QTableWidget,QPlainTextEdit,QComboBox,QSpinBox,QDoubleSpinBox { background:#111a2a; selection-background-color:#416293; padding:4px; } QHeaderView::section { background:#283955; padding:8px; } QTabBar::tab { padding:10px 24px; }')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--child-script':
        import runpy
        script = sys.argv[2]
        sys.argv = sys.argv[2:]
        runpy.run_path(script, run_name='__main__')
    else:
        app = QApplication(sys.argv)
        configure_app(app)
        from studio import StudioWindow, studio_theme
        window = StudioWindow()
        studio_theme(app, window.dark)
        logs = window.root / 'logs'
        logs.mkdir(exist_ok=True)
        window.session_log = (logs / f'windows-{time.time_ns()}.log').open('a', encoding='utf-8', buffering=1)
        window.show()
        sys.exit(app.exec())
