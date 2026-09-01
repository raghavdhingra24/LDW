import PyQt6.QtWidgets as QtW
import PyQt6.QtCore as QtC
import PyQt6.QtGui as QtG
import sys
import os
import subprocess
import time
import json
from PIL import Image, ImageFilter, ImageEnhance
from PIL.ImageQt import ImageQt
from PyQt6 import QtCore

# Force X11 for always on bottom window
os.environ['QT_QPA_PLATFORM'] = 'xcb'

# SAAW - simple and awesome widgets


class MediaInformation:
    album: str
    artist: str
    art: str
    length: int
    player: str
    position: int
    status: str
    title: str

    def __init__(self, album: str = "", artist: str = "", art: str = "", length: int = 0, player: str = "",
                 position: int = 0, status: str = "", title: str = ""):
        self.album = album
        self.artist = artist
        self.art = art
        self.length = length
        self.player = player
        self.position = position
        self.status = status
        self.title = title


class ProgressBar(QtW.QSlider):
    progress_update = QtC.pyqtSignal(float)
    def __init__(self):
        super().__init__()

        self.setOrientation(QtC.Qt.Orientation.Horizontal)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            val = self.pixelPosToRangeValue(event.pos())
            self.setValue(val)

            min_val = self.minimum()
            max_val = self.maximum()
            rv = 0
            if max_val > min_val:
                rv = (val - min_val) / (max_val - min_val)
            print(val, min_val, max_val, rv)
            self.progress_update.emit(rv)
            # print(val, self.value())
        else:
            super().mousePressEvent(event)

    def pixelPosToRangeValue(self, pos):
        # credits: https://stackoverflow.com/questions/52689047/moving-qslider-to-mouse-click-position
        opt = QtW.QStyleOptionSlider()
        self.initStyleOption(opt)
        gr = self.style().subControlRect(QtW.QStyle.ComplexControl.CC_Slider, opt,
                                         QtW.QStyle.SubControl.SC_SliderGroove, self)
        sr = self.style().subControlRect(QtW.QStyle.ComplexControl.CC_Slider, opt,
                                         QtW.QStyle.SubControl.SC_SliderHandle, self)

        if self.orientation() == QtCore.Qt.Orientation.Horizontal:
            sliderLength = sr.width()
            sliderMin = gr.x()
            sliderMax = gr.right() - sliderLength + 1
        else:
            sliderLength = sr.height()
            sliderMin = gr.y()
            sliderMax = gr.bottom() - sliderLength + 1
        pr = pos - sr.center() + sr.topLeft()
        p = pr.x() if self.orientation() == QtCore.Qt.Orientation.Horizontal else pr.y()
        return QtW.QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), p - sliderMin,
                                                        sliderMax - sliderMin, opt.upsideDown)


class Worker(QtC.QObject):
    data_update = QtC.pyqtSignal(list)
    finished = QtC.pyqtSignal()
    stop = QtC.pyqtSignal()
    update = True

    def run(self):
        while self.update:
            d = {}
            with open("format.json", "r") as file:
                f = file.read()
            result = subprocess.run(["playerctl", "metadata", "-a", "-f", f], capture_output=True)
            final = "[" + result.stdout.decode("utf-8").replace("}\n", "},\n") + "{}]"
            data = json.loads(final)
            ls = []
            for i in data:
                current_media: dict = i
                media_information = MediaInformation()
                media_information.album = current_media.get("album", "No album")
                media_information.art = current_media.get("art", "")
                media_information.artist = current_media.get("artist", "No Artist")
                media_information.length = current_media.get("length", 0)
                media_information.player = current_media.get("player", "No Player")
                media_information.position = current_media.get("position", 0)
                media_information.status = current_media.get("status", "N/A")
                media_information.title = current_media.get("title", "No Title")
                ls.append(media_information)
            self.data_update.emit(ls)
            time.sleep(1)
        self.finished.emit()

    def stop_worker(self):
        self.update = False



class Controls(QtW.QWidget):
    def __init__(self):
        super().__init__()

        self.controls_layout = QtW.QGridLayout()
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.controls_layout)

        self.prev_btn = QtW.QPushButton("Prev")
        self.prev_btn.clicked.connect(self.play_previous)
        self.controls_layout.addWidget(self.prev_btn, 1, 0, 1, 1)
        self.play_btn = QtW.QPushButton("Pause")
        self.play_btn.clicked.connect(self.play_pause)
        self.play_state = 1
        # self.play_btn.clicked.connect(self.play_pause)
        self.controls_layout.addWidget(self.play_btn, 1, 1, 1, 1)
        self.next_btn = QtW.QPushButton("Next")
        self.next_btn.clicked.connect(self.play_next)
        self.controls_layout.addWidget(self.next_btn, 1, 2, 1, 1)

        self.current_time = QtW.QLabel("00:00:00")
        self.current_time.setAlignment(QtC.Qt.AlignmentFlag.AlignCenter)
        self.controls_layout.addWidget(self.current_time, 2, 0, 1, 1)

        self.progress_bar = ProgressBar()
        self.progress_bar.progress_update.connect(self.update_progress)
        self.controls_layout.addWidget(self.progress_bar, 2, 1, 1, 1)

        self.full_time = QtW.QLabel("00:00:00")
        self.full_time.setAlignment(QtC.Qt.AlignmentFlag.AlignCenter)
        self.controls_layout.addWidget(self.full_time, 2, 2, 1, 1)

        self.song_length = 0

    def play_previous(self):
        try:
            result = subprocess.run(["playerctl", "previous"], capture_output=True)
            print(result.stdout.decode("utf-8"))
        except Exception as e:
            print("prev", e)

    def update_data(self, event):
        if len(event) > 1:
            info: MediaInformation = event[0]
            self.song_length = int(info.length) / 1_000_000
            ct = time.strftime("%H:%M:%S", time.gmtime(int(info.position) / 1_000_000))
            self.current_time.setText(ct)
            ft = time.strftime("%H:%M:%S", time.gmtime(int(info.length) / 1_000_000))
            self.full_time.setText(ft)
            self.progress_bar.setValue(int(100 - (int(info.length) - int(info.position)) / int(info.length) * 100))

    def update_progress(self, progress):
        if self.song_length:
            pv = self.song_length * progress
            print(pv, self.song_length, progress)
            try:
                result = subprocess.run(["playerctl", "position", str(int(pv))], capture_output=True)
            except Exception as e:
                print("progress_update", e)


    def play_pause(self):
        try:
            result = subprocess.run(["playerctl", "status"], capture_output=True)
            # print(result.stdout.decode("utf-8"))
            state = result.stdout.decode("utf-8").strip()
            if state == "Paused":
                self.play_state = 1
                self.play_btn.setText("Pause")
                res = subprocess.run(["playerctl", "play"], capture_output=True)
            elif state == "Playing":
                self.play_state = 0
                self.play_btn.setText("Play")
                res = subprocess.run(["playerctl", "pause"], capture_output=True)
        except Exception as e:
            print("play_pause", e)

    def set_state(self, state):
        if state == "Paused":
            self.play_state = 0
            self.play_btn.setText("Play")
        elif state == "Playing":
            self.play_state = 1
            self.play_btn.setText("Pause")

    def play_next(self):
        try:
            result = subprocess.run(["playerctl", "next"], capture_output=True)
            print(result.stdout.decode("utf-8"))
        except Exception as e:
            print("prev", e)


class MainWidget(QtW.QWidget):
    def __init__(self):
        super().__init__()

        self.main_layout = QtW.QGridLayout()
        self.setLayout(self.main_layout)
        self.bg = QtW.QLabel()
        self.bg.setScaledContents(True)
        self.bg.setFixedSize(180, 180)
        try:
            result = subprocess.run(["playerctl", "metadata", "mpris:artUrl"], capture_output=True)
            img = '/' + result.stdout.decode("utf-8").lstrip(r"file:/").strip()

            self.pixmap = self.get_rounded_pixmap(QtG.QPixmap(img), 32*1.25)
            print(img)
            self.bg.setPixmap(self.pixmap)
        except Exception:
            print("EROOR")
        # bg.setAlignment()
        self.main_layout.addWidget(self.bg, 0, 0, 3, 1, QtC.Qt.AlignmentFlag.AlignVCenter)

        result = subprocess.run(["playerctl", "metadata", "xesam:title"], capture_output=True)
        self.title = QtW.QLabel(result.stdout.decode("utf-8"))
        self.title.setSizePolicy(QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding)
        self.title.setAlignment(QtC.Qt.AlignmentFlag.AlignCenter)
        font = self.title.font()
        font.setPointSize(16)
        self.title.setFont(font)
        self.title.setWordWrap(True)
        self.main_layout.addWidget(self.title, 0, 1, 1, 1)

        result = subprocess.run(["playerctl", "metadata", "xesam:album"], capture_output=True)
        self.album = QtW.QLabel(result.stdout.decode("utf-8"))
        self.album.setSizePolicy(QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding)
        self.album.setAlignment(QtC.Qt.AlignmentFlag.AlignCenter)
        self.album.setWordWrap(True)
        self.main_layout.addWidget(self.album, 1, 1, 1, 1)

        result = subprocess.run(["playerctl", "metadata", "xesam:artist"], capture_output=True)
        self.artist = QtW.QLabel(result.stdout.decode("utf-8"))
        self.artist.setSizePolicy(QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding)
        self.artist.setAlignment(QtC.Qt.AlignmentFlag.AlignCenter)
        self.artist.setWordWrap(True)
        self.main_layout.addWidget(self.artist, 2, 1, 1, 1)

        self.controls = Controls()
        self.main_layout.addWidget(self.controls, 3, 0, 1, 3)

    def update_data(self, event):
        if len(event) > 0:
            info: MediaInformation = event[0]
            self.controls.set_state(info.status)
            self.controls.update_data(event)
            self.title.setText(info.title)
            self.album.setText(info.album)
            self.artist.setText(info.artist)
            if info.art == "":
                fallback_pixmap = QtG.QPixmap(self.bg.height(), self.bg.width())
                fallback_pixmap.fill(QtG.QColor(110, 110, 110, 40))
                self.pixmap = self.get_rounded_pixmap(fallback_pixmap, 12 * 1.25)
                self.bg.setPixmap(self.pixmap)
            else:
                try:
                    pm = QtG.QPixmap(info.art.replace("file:/", ""))
                    pm = pm.scaled(self.bg.height(), self.bg.width(), QtC.Qt.AspectRatioMode.KeepAspectRatio)
                    self.pixmap = self.get_rounded_pixmap(pm, 10*1.25)
                    self.bg.setPixmap(self.pixmap)
                except Exception as e:
                    print("LMAO", e)
            

    @staticmethod
    def get_rounded_pixmap(source_pixmap, radius):
        """Creates a new QPixmap with rounded corners."""
        # FIXME: different sized images have different radii.
        if source_pixmap.isNull(): return QtG.QPixmap()

        # Create target pixmap with transparency
        target = QtG.QPixmap(source_pixmap.size())
        target.fill(QtC.Qt.GlobalColor.transparent)

        # Draw rounded image
        painter = QtG.QPainter(target)
        painter.setRenderHint(QtG.QPainter.RenderHint.Antialiasing)
        path = QtG.QPainterPath()
        path.addRoundedRect(QtC.QRectF(source_pixmap.rect()), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, source_pixmap)
        painter.end()
        return target



class MainWindow(QtW.QMainWindow):
    def __init__(self):
        super().__init__()

        # QtC.Qt.WindowType.WindowStaysOnBottomHint
        self.setWindowFlag(self.windowFlags() | QtC.Qt.WindowType.FramelessWindowHint |
                           QtC.Qt.WindowType.Tool)

        central_widget = QtW.QWidget()
        central_layout = QtW.QGridLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central_widget)
        self.resize(500, 280)

        result = subprocess.run(["playerctl", "metadata", "mpris:artUrl"], capture_output=True)
        self.bg = QtW.QLabel()
        self.bg.setAttribute(QtC.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # self.bg.setScaledContents(True)
        try:
            img = '/' + result.stdout.decode("utf-8").lstrip(r"file:/").strip()
            pil_image = Image.open(img)
            pil_image = pil_image.filter(ImageFilter.GaussianBlur(25))
            enhancer = ImageEnhance.Brightness(pil_image)
            pil_image = enhancer.enhance(0.5)
            self.qt_image = ImageQt(pil_image)
            pixmap = QtG.QPixmap.fromImage(self.qt_image)
            self.bg.setPixmap(pixmap)
        except Exception:
            print("LOOL")
        self.bg.setFixedSize(self.width(), self.height())

        central_layout.addWidget(self.bg, 0, 0, 1, 1)

        self.widget = MainWidget()
        central_layout.addWidget(self.widget, 0, 0, 1, 1)
        # central_layout.addWidget(btn, 0, 0, 1, 1)

        self.player_thread = QtC.QThread()
        self.player_worker = Worker()
        self.player_worker.moveToThread(self.player_thread)
        self.player_worker.data_update.connect(self.on_data_update)
        self.player_thread.finished.connect(self.player_worker.stop_worker)
        self.player_thread.started.connect(self.player_worker.run)
        self.player_worker.data_update.connect(self.widget.update_data)
        self.player_thread.start()

        self.close_button = QtW.QPushButton("X")
        self.close_button.resize(30, 30)
        self.close_button.clicked.connect(self.close)
        self.close_button.setParent(self)

        self.close_hide_timer = QtC.QTimer()
        self.close_hide_timer.setSingleShot(True)
        self.close_hide_timer.timeout.connect(self.close_button.hide)

    def paintEvent(self, event):
        super().paintEvent(event)

    def on_data_update(self, event: list):
        if (len(event) > 0):
            info: MediaInformation = event[0]
            # print(info.artist, info.title, info.album)
            try:
                pil_image = Image.open(info.art.replace("file:/", ""))
                pil_image.thumbnail((300, 300), Image.Resampling.LANCZOS)
                pil_image = pil_image.filter(ImageFilter.GaussianBlur(25))
                enhancer = ImageEnhance.Brightness(pil_image)
                pil_image = enhancer.enhance(0.5)
                self.qt_image = ImageQt(pil_image)
                pixmap = QtG.QPixmap.fromImage(self.qt_image)
                scaled_pixmap = pixmap.scaled(self.bg.size(), QtC.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                              QtC.Qt.TransformationMode.SmoothTransformation)
                self.bg.setPixmap(scaled_pixmap)
            except Exception as e:
                # print("LOOL", e, info.art)
                fallback_pixmap = QtG.QPixmap(1, 1)
                fallback_pixmap.fill(QtG.QColor(0, 0, 0, 0)) # Fill with transparent pixels
                self.bg.setPixmap(fallback_pixmap)

        # painter = QtG.QPainter(self)
        # img = "/home/raghav/Downloads/1mj5Mnf.jpg"
        # painter.drawPixmap(self.rect(), pixmap)
        # painter.end()

    def resizeEvent(self, event: QtG.QResizeEvent):
        x = event.size().width() - 10 - self.close_button.width()
        y = 10
        self.close_button.move(x, y)
        super().resizeEvent(event)

    def closeEvent(self, event: QtG.QCloseEvent):
        QtW.QApplication.quit()

    def enterEvent(self, event: QtG.QEnterEvent):
        self.close_button.show()
        self.close_hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event: QtG.QEnterEvent):
        self.close_hide_timer.start(1000)
        super().leaveEvent(event)


if __name__ == '__main__':
    with open("format.json", "r") as file:
        f = file.read()
    test = subprocess.run(["playerctl", "metadata", "-a", "-f", f], capture_output=True)
    final = "[" + test.stdout.decode("utf-8").replace("}\n", "},\n") + "{}]"
    print(final)
    data = json.loads(final)
    print(data)
    app = QtW.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.exec()
