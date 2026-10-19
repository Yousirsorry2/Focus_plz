"""Music and Settings destinations for the shared desktop navigation."""

import json
import shutil
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from PySide6.QtCore import QSettings, Qt, Signal, QUrl
from PySide6.QtGui import QFontMetrics
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QRadioButton, QScrollArea, QSlider,
                               QStackedWidget, QSizePolicy, QVBoxLayout, QWidget)
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.media_store import (PLAYABLE_MEDIA_EXTENSIONS, ensure_default_track,
                              music_directory)
from core.config import load_config
from ui.mochi import MochiCat
from ui.navigation import BottomNavigation
from ui.sound_effects import play_sound_effect
from ui.tasks_theme import FULL_QSS
from ui.theme import MOBILE_MINIMUM_WINDOW_SIZE, MOBILE_WINDOW_SIZE, make_paw_icon


class _NavigationPage(QWidget):
    navigation_requested = Signal(str)

    def __init__(self, active):
        super().__init__()
        self.setObjectName("TasksWindow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle(f"Pawse - {active}")
        self.setWindowIcon(make_paw_icon())
        self.setStyleSheet(FULL_QSS)
        self.resize(*MOBILE_WINDOW_SIZE)
        self.setMinimumSize(*MOBILE_MINIMUM_WINDOW_SIZE)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        page = QWidget()
        page.setObjectName("mobilePage")
        self.root = QVBoxLayout(page)
        self.root.setContentsMargins(18, 20, 18, 18)
        self.root.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        outer.addWidget(scroll, 1)
        self.navigation = BottomNavigation(active, self)
        self.navigation.selected.connect(self.navigation_requested.emit)
        outer.addWidget(self.navigation)


class MusicView(_NavigationPage):
    def __init__(self, parent=None):
        super().__init__("Music")
        self.settings = QSettings("Pawse", "Pawse")
        self.status = QLabel("")
        self.status.setObjectName("musicStatus")
        self.now_playing = QLabel("Choose a saved link to play it here.")
        self.now_playing.setObjectName("musicHint")
        self.media_dir = music_directory()
        self.current_media_path = None

        eyebrow = QLabel("YOUR CALM LITTLE CORNER / MUSIC")
        eyebrow.setObjectName("sectionEyebrow")
        title = QLabel("Cozy Sounds")
        title.setObjectName("sectionTitle")
        note = QLabel("A softer soundtrack for your day.")
        note.setObjectName("subtitle")
        eyebrow.setWordWrap(True)
        note.setWordWrap(True)
        self.root.addWidget(eyebrow)
        self.root.addSpacing(8)
        self.root.addWidget(title)
        self.root.addSpacing(4)
        self.root.addWidget(note)
        self.root.addSpacing(24)

        content = QVBoxLayout()
        content.setSpacing(14)
        player_card = QFrame()
        player_card.setObjectName("softCard")
        player = QVBoxLayout(player_card)
        player.setContentsMargins(16, 14, 16, 14)
        player.setSpacing(8)
        self.player_stack = QStackedWidget()
        self.player_stack.setMinimumHeight(190)
        self.player_stack.setMaximumHeight(250)
        self.player_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.player_placeholder = QWidget()
        placeholder = QVBoxLayout(self.player_placeholder)
        placeholder.addStretch(1)
        placeholder.addWidget(MochiCat("sleeping", width=250), 0, Qt.AlignHCenter)
        placeholder.addStretch(1)
        self.web_player = QWebEngineView()
        self.web_player.setMinimumSize(0, 190)
        self.web_player.setMaximumHeight(210)
        self.web_player.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.web_player.loadFinished.connect(self._on_player_load_finished)
        self.local_player_view = QWidget()
        local_player = QVBoxLayout(self.local_player_view)
        local_player.setContentsMargins(0, 0, 0, 0)
        local_player.setSpacing(4)
        self.local_video = QVideoWidget()
        self.local_video.setMinimumHeight(100)
        self.local_video.setMaximumHeight(140)
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.local_video)
        
        self.media_player.positionChanged.connect(self._on_media_position)
        self.media_player.durationChanged.connect(self._on_media_duration)
        self.media_player.playbackStateChanged.connect(self._on_media_state)
        self.media_player.errorOccurred.connect(self._on_media_error)
        local_player.addWidget(self.local_video)
        self.local_track_label = QLabel("Choose a local track")
        self.local_track_label.setObjectName("musicHint")
        self.local_track_label.setWordWrap(True)
        local_player.addWidget(self.local_track_label)
        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.local_play_button = QPushButton("Play")
        self.local_play_button.setObjectName("providerButton")
        self.local_play_button.clicked.connect(self._toggle_local_playback)
        self.local_stop_button = QPushButton("Stop")
        self.local_stop_button.setObjectName("providerButton")
        self.local_stop_button.clicked.connect(self.media_player.stop)
        controls.addWidget(self.local_play_button)
        controls.addWidget(self.local_stop_button)
        self.media_progress = QSlider(Qt.Horizontal)
        self.media_progress.setRange(0, 0)
        self.media_progress.sliderMoved.connect(self.media_player.setPosition)
        controls.addWidget(self.media_progress, 1)
        local_player.addLayout(controls)
        audio_controls = QHBoxLayout()
        self.volume_button = QPushButton("Mute")
        self.volume_button.setObjectName("providerButton")
        self.volume_button.setCheckable(True)
        self.volume_button.toggled.connect(self._toggle_mute)
        audio_controls.addWidget(self.volume_button)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setObjectName("musicVolume")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setMinimumWidth(60)
        self.volume_slider.setToolTip("Volume")
        try:
            volume = max(0, min(100, int(self.settings.value("music_volume", 70))))
        except (TypeError, ValueError):
            volume = 70
        self.volume_slider.setValue(volume)
        self.audio_output.setVolume(volume / 100)
        self.volume_slider.valueChanged.connect(self._set_volume)
        audio_controls.addWidget(self.volume_slider, 1)
        self.loop_button = QPushButton("Loop track")
        self.loop_button.setObjectName("providerButton")
        self.loop_button.setCheckable(True)
        self.loop_button.toggled.connect(self._toggle_loop)
        audio_controls.addWidget(self.loop_button)
        local_player.addLayout(audio_controls)
        self.player_stack.addWidget(self.player_placeholder)
        self.player_stack.addWidget(self.web_player)
        self.player_stack.addWidget(self.local_player_view)
        player.addWidget(self.player_stack)
        player_caption = QLabel("A LITTLE BACKGROUND CALM")
        player_caption.setWordWrap(False)
        player.addWidget(player_caption, 0, Qt.AlignHCenter)
        self.player_title = QLabel("Made for your quiet moments")
        self.player_title.setObjectName("cardTitle")
        self.player_title.setAlignment(Qt.AlignCenter)
        self.player_title.setWordWrap(True)
        player.addWidget(self.player_title)
        self.now_playing.setWordWrap(True)
        self.now_playing.setAlignment(Qt.AlignCenter)
        player.addWidget(self.now_playing)
        content.addWidget(player_card)

        library = QFrame()
        library.setObjectName("musicCard")
        library_col = QVBoxLayout(library)
        library_col.setContentsMargins(16, 16, 16, 16)
        library_col.setSpacing(10)
        eyebrow = QLabel("YOUR MUSIC LIBRARY")
        eyebrow.setObjectName("sectionEyebrow")
        library_col.addWidget(eyebrow)
        library_title = QLabel("Local media & playlists")
        library_title.setObjectName("cardTitle")
        library_title.setWordWrap(True)
        library_col.addWidget(library_title)
        self.upload_button = QPushButton("+  Upload Media")
        self.upload_button.setObjectName("capsulePrimary")
        self.upload_button.setCursor(Qt.PointingHandCursor)
        self.upload_button.clicked.connect(self.upload_media)
        library_col.addWidget(self.upload_button)
        self.media_list = QVBoxLayout()
        self.media_list.setContentsMargins(0, 4, 0, 4)
        self.media_list.setSpacing(8)
        library_col.addLayout(self.media_list)
        online_title = QLabel("Online playlists")
        online_title.setObjectName("fieldTitle")
        library_col.addWidget(online_title)
        self.link_input = QLineEdit()
        self.link_input.setObjectName("musicLink")
        self.link_input.setPlaceholderText("Paste a YouTube or Spotify playlist link")
        self.link_input.returnPressed.connect(self.add_playlist)
        library_col.addWidget(self.link_input)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self.youtube_button = QPushButton("YouTube")
        self.spotify_button = QPushButton("Spotify")
        for button, provider in ((self.youtube_button, "YouTube"),
                                 (self.spotify_button, "Spotify")):
            button.setObjectName("providerButton")
            button.setProperty("provider", provider)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _=False, name=provider: self._set_provider(name))
            add_row.addWidget(button, 1)
        library_col.addLayout(add_row)
        self.add_button = QPushButton("+  Save playlist")
        self.add_button.setObjectName("capsulePrimary")
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.add_playlist)
        library_col.addWidget(self.add_button)

        hint = QLabel("Playback is embedded here. Sign-in or full playback may depend on your provider and account.")
        hint.setObjectName("musicHint")
        hint.setWordWrap(True)
        library_col.addWidget(hint)
        self.status.setWordWrap(True)
        library_col.addWidget(self.status)

        playlist_host = QWidget()
        self.playlist_list = QVBoxLayout(playlist_host)
        self.playlist_list.setContentsMargins(0, 4, 0, 4)
        self.playlist_list.setSpacing(8)
        playlist_scroll = QScrollArea()
        playlist_scroll.setWidgetResizable(True)
        playlist_scroll.setFrameShape(QFrame.NoFrame)
        playlist_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        playlist_scroll.setWidget(playlist_host)
        library_col.addWidget(playlist_scroll)
        content.addWidget(library)
        self.root.addLayout(content)
        try:
            ensure_default_track()
        except OSError as error:
            self.status.setText(f"Could not prepare the local music library: {error}")
        self._render_media()
        self._render_playlists()

    def upload_media(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Upload music or video", "",
            "Media files (*.mp3 *.mp4);;MP3 audio (*.mp3);;MP4 video (*.mp4)")
        if not files:
            return

        copied = 0
        failures = []
        try:
            self.media_dir.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.status.setText(f"Could not access the local music library: {error}")
            return
        for filename in files:
            source = Path(filename)
            if source.suffix.lower() not in PLAYABLE_MEDIA_EXTENSIONS:
                failures.append(f"{source.name}: unsupported file type")
                continue
            try:
                if not source.is_file():
                    raise OSError("The selected file is no longer available.")
                target = self._available_media_path(source)
                if target.resolve() == source.resolve():
                    continue
                shutil.copy2(source, target)
                copied += 1
            except OSError as error:
                failures.append(f"{source.name}: {error}")

        if not self._render_media():
            return
        if failures:
            self.status.setText("Uploaded " + str(copied) + " file(s). " + "; ".join(failures))
        elif copied:
            self.status.setText(f"Uploaded {copied} file(s) to your local music library.")
        else:
            self.status.setText("Those files are already in your local music library.")

    def _available_media_path(self, source):
        target = self.media_dir / source.name
        if not target.exists():
            return target
        if target.resolve() == source.resolve():
            return target
        index = 2
        while True:
            target = self.media_dir / f"{source.stem} ({index}){source.suffix}"
            if not target.exists():
                return target
            index += 1

    def _render_media(self):
        while self.media_list.count():
            item = self.media_list.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        try:
            self.media_dir.mkdir(parents=True, exist_ok=True)
            files = sorted(
                (path for path in self.media_dir.iterdir()
                 if path.is_file() and path.stat().st_size > 0
                 and path.suffix.lower() in PLAYABLE_MEDIA_EXTENSIONS),
                key=lambda path: path.name.lower())
        except OSError as error:
            self.status.setText(f"Could not read the local music library: {error}")
            return False
        if not files:
            empty = QLabel("Upload an MP3 or MP4 to start your offline library.")
            empty.setObjectName("musicHint")
            empty.setWordWrap(True)
            self.media_list.addWidget(empty)
            return True

        for path in files:
            row = QFrame()
            row.setObjectName("dashboardCard")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(8, 6, 6, 6)
            layout.setSpacing(6)
            label = QLabel(path.name)
            label.setObjectName("fieldTitle")
            label.setWordWrap(True)
            label.setToolTip(str(path))
            layout.addWidget(label, 1)
            play = QPushButton("Play")
            play.setObjectName("playlistPlay")
            play.setCursor(Qt.PointingHandCursor)
            play.setFixedWidth(64)
            play.clicked.connect(lambda _=False, media=path: self._play_local_media(media))
            layout.addWidget(play)
            self.media_list.addWidget(row)
        return True

    def _play_local_media(self, path, autoplay=True):
        path = Path(path)
        if not path.is_file():
            self.status.setText(f"Could not find local media: {path}")
            return
        self.current_media_path = path
        is_video = path.suffix.lower() == ".mp4"
        self.local_video.setVisible(is_video)
        self.local_track_label.setText(path.name)
        self.now_playing.setText("Playing from your offline library.")
        self.player_title.setText("Local playback")
        self.player_stack.setCurrentWidget(self.local_player_view)
        self.media_player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        if autoplay:
            self.media_player.play()
            self.status.setText(f"Playing {path.name}.")
        else:
            self.status.setText(f"{path.name} is ready to play.")

    def _set_volume(self, value):
        self.audio_output.setVolume(value / 100)
        self.settings.setValue("music_volume", value)
        self.settings.sync()

    def _toggle_mute(self, muted):
        self.audio_output.setMuted(muted)
        self.volume_button.setText("Unmute" if muted else "Mute")

    def _toggle_loop(self, enabled):
        loops = QMediaPlayer.Loops.Infinite if enabled else QMediaPlayer.Loops.Once
        self.media_player.setLoops(loops)

    def _toggle_local_playback(self):
        if self.media_player.playbackState() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        elif self.current_media_path is not None:
            self.media_player.play()
        else:
            files = sorted(
                (path for path in self.media_dir.iterdir()
                 if path.is_file() and path.stat().st_size > 0
                 and path.suffix.lower() in PLAYABLE_MEDIA_EXTENSIONS),
                key=lambda path: path.name.lower())
            if files:
                self._play_local_media(files[0])

    def _on_media_position(self, position):
        if not self.media_progress.isSliderDown():
            self.media_progress.setValue(position)

    def _on_media_duration(self, duration):
        self.media_progress.setRange(0, duration)

    def _on_media_state(self, state):
        self.local_play_button.setText(
            "Pause" if state == QMediaPlayer.PlayingState else "Play")

    def _on_media_error(self, _error, message):
        self.status.setText(f"Could not play this media file: {message}")

    def _set_provider(self, provider):
        example = ("https://www.youtube.com/playlist?list=" if provider == "YouTube"
                   else "https://open.spotify.com/playlist/")
        self.link_input.setText(example)
        self.link_input.setFocus()
        self.link_input.setCursorPosition(len(example))

    @staticmethod
    def _provider_for_url(value):
        try:
            parsed = urlsplit(value)
            host = (parsed.hostname or "").lower()
        except ValueError:
            return None
        if parsed.scheme != "https" or parsed.username or parsed.password:
            return None
        if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
            query = parse_qs(parsed.query)
            if (parsed.path == "/playlist" and query.get("list")) or (
                    parsed.path == "/watch" and query.get("list")):
                return "YouTube"
        if host == "youtu.be" and parsed.path.strip("/"):
            return "YouTube"
        if host == "open.spotify.com":
            parts = parsed.path.strip("/").split("/")
            if any(part in {"playlist", "track"} and index + 1 < len(parts)
                   and parts[index + 1] for index, part in enumerate(parts)):
                return "Spotify"
        if host == "spotify.link" and parsed.path.strip("/"):
            return "Spotify"
        return None

    @staticmethod
    def _embed_url(value):
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
            query = parse_qs(parsed.query)
            playlist_ids = query.get("list")
            if playlist_ids:
                return QUrl("https://www.youtube-nocookie.com/embed/videoseries?list="
                            + quote(playlist_ids[0], safe=""))
            video_ids = query.get("v")
            if video_ids:
                return QUrl("https://www.youtube-nocookie.com/embed/" +
                            quote(video_ids[0], safe=""))
        if host == "youtu.be":
            video_id = parsed.path.strip("/").split("/", 1)[0]
            return QUrl("https://www.youtube-nocookie.com/embed/" + quote(video_id, safe=""))
        if host == "open.spotify.com":
            parts = parsed.path.strip("/").split("/")
            for index, part in enumerate(parts[:-1]):
                if part in {"playlist", "track"}:
                    return QUrl(f"https://open.spotify.com/embed/{part}/"
                                f"{quote(parts[index + 1], safe='')}?theme=0")
        return QUrl(value)

    def add_playlist(self):
        value = self.link_input.text().strip()
        provider = self._provider_for_url(value)
        if provider is None:
            self.status.setText("Paste a valid YouTube or Spotify playlist link (https://).")
            return

        playlists = self._playlists()
        if playlists is None:
            return
        if value in playlists:
            self.status.setText("That playlist is already in your library.")
            return
        playlists.append(value)
        self.settings.setValue("music_playlists", json.dumps(playlists, ensure_ascii=False))
        self.settings.sync()
        if self.settings.status() != QSettings.NoError:
            self.status.setText("Could not save the playlist. Check your app settings storage.")
            return
        self.link_input.clear()
        self.status.setText(f"{provider} link saved. Press Play to open it.")
        self._render_playlists(playlists)

    def _playlists(self):
        try:
            playlists = json.loads(self.settings.value("music_playlists", "[]"))
        except (TypeError, ValueError):
            self.status.setText("Saved playlist data could not be read.")
            return None
        if not isinstance(playlists, list) or any(not isinstance(item, str) for item in playlists):
            self.status.setText("Saved playlist data has an invalid format.")
            return None
        return playlists

    def _render_playlists(self, playlists=None):
        while self.playlist_list.count():
            item = self.playlist_list.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        playlists = self._playlists() if playlists is None else playlists
        if playlists is None:
            return
        if not playlists:
            empty = QLabel("Your saved playlists will appear here.")
            empty.setObjectName("musicHint")
            empty.setWordWrap(True)
            self.playlist_list.addWidget(empty)
            return

        for index, url in enumerate(playlists):
            provider = self._provider_for_url(url)
            row = QFrame()
            row.setObjectName("dashboardCard")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(8, 6, 6, 6)
            layout.setSpacing(6)
            info = QVBoxLayout()
            label = QLabel(provider or "Unsupported link")
            label.setObjectName("fieldTitle")
            label.setWordWrap(True)
            url_label = QLabel(url)
            url_label.setObjectName("musicHint")
            url_label.setText(QFontMetrics(url_label.font()).elidedText(
                urlsplit(url).path, Qt.ElideMiddle, 110))
            url_label.setToolTip(url)
            info.addWidget(label)
            info.addWidget(url_label)
            layout.addLayout(info, 1)
            play = QPushButton("Play")
            play.setObjectName("playlistPlay")
            play.setCursor(Qt.PointingHandCursor)
            play.setEnabled(provider is not None)
            play.setFixedWidth(64)
            play.clicked.connect(lambda _=False, link=url: self._open_playlist(link))
            layout.addWidget(play)
            remove = QPushButton("×")
            remove.setObjectName("playlistRemove")
            remove.setFixedWidth(28)
            remove.setToolTip("Remove playlist")
            remove.setCursor(Qt.PointingHandCursor)
            remove.clicked.connect(lambda _=False, i=index: self._remove_playlist(i))
            layout.addWidget(remove)
            self.playlist_list.addWidget(row)

    def _open_playlist(self, url):
        provider = self._provider_for_url(url)
        if provider is None:
            self.status.setText("This saved link is not a supported YouTube or Spotify link.")
            return
        self.now_playing.setText(
            f"{provider} player selected. Use its embedded controls to start playback.")
        self.player_title.setText("Now playing")
        self.player_stack.setCurrentWidget(self.web_player)
        self.web_player.setUrl(self._embed_url(url))
        self.status.setText(f"Loading the {provider} player...")

    def _on_player_load_finished(self, success):
        if success:
            self.status.setText("Player ready. Press Play in the player to start listening.")
        else:
            self.status.setText(
                "The player could not load. Check your internet connection or open the link with its provider.")

    def _remove_playlist(self, index):
        playlists = self._playlists()
        if playlists is None:
            return
        if not 0 <= index < len(playlists):
            self.status.setText("The selected playlist is no longer available.")
            return
        playlists.pop(index)
        self.settings.setValue("music_playlists", json.dumps(playlists, ensure_ascii=False))
        self.settings.sync()
        if self.settings.status() != QSettings.NoError:
            self.status.setText("Could not remove the playlist from your library.")
            return
        self.status.setText("Playlist removed.")
        self._render_playlists(playlists)


class SettingsView(_NavigationPage):
    def __init__(self, tracker, parent=None):
        super().__init__("Settings")
        self.tracker = tracker
        title = QLabel("Settings \u2699")
        title.setObjectName("title")
        note = QLabel("Manage Focus Guard allow and block rules.\nMajor entertainment apps can only be allowed here.")
        note.setObjectName("subtitle")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignLeft)
        self.root.insertWidget(0, title)
        self.root.insertWidget(1, note)
        self.root.insertSpacing(2, 20)

        card = QFrame()
        card.setObjectName("settingsCard")
        col = QVBoxLayout(card)
        col.setContentsMargins(18, 18, 18, 18)
        col.setSpacing(10)
        self.allow = QRadioButton("Always allow as work")
        self.allow.setChecked(True)
        self.block = QRadioButton("Always block as a distraction")
        col.addWidget(self.allow)
        col.addWidget(self.block)
        self.rule_input = QLineEdit()
        self.rule_input.setPlaceholderText("App name (.exe) or site / keyword")
        self.rule_input.setMaxLength(100)
        col.addWidget(self.rule_input)
        save = QPushButton("Save rule")
        save.setObjectName("capsulePrimary")
        save.clicked.connect(self._save_rule)
        col.addWidget(save)
        self.status = QLabel("")
        self.status.setObjectName("fieldHint")
        self.status.setWordWrap(True)
        col.addWidget(self.status)
        self.root.insertWidget(3, card)
        self.root.insertSpacing(4, 12)
        self.rules = QLabel()
        self.rules.setObjectName("settingsRules")
        self.rules.setWordWrap(True)
        self.root.insertWidget(5, self.rules)
        self.fish_count = QLabel()
        self.fish_count.setObjectName("fieldHint")
        self.root.insertWidget(6, self.fish_count)
        self.root.insertStretch(7, 1)
        self._refresh_rules()

    def _save_rule(self):
        value = self.rule_input.text().strip()
        if not value:
            self.status.setText("Enter an app name or site first.")
            return
        try:
            self.tracker.add_manual_target(value, blocked=self.block.isChecked())
        except (OSError, sqlite3.Error) as error:
            self.status.setText(f"Could not save the rule: {error}")
            return
        self.rule_input.clear()
        self.status.setText("Rule saved locally and applied immediately.")
        self._refresh_rules()

    def _refresh_rules(self):
        cfg = (self.tracker.rule_store.focus_rules()
               if hasattr(self.tracker, "rule_store") else load_config())
        allowed = cfg.get("productive_processes", []) + cfg.get("productive_keywords", [])
        blocked = (cfg.get("custom_distraction_processes", []) +
                   cfg.get("custom_distraction_sites", []))
        allowed_text = ", ".join(allowed) if allowed else "None"
        blocked_text = ", ".join(blocked) if blocked else "None"
        self.rules.setText(f"Always allowed: {allowed_text}\n\nCustom blocked: {blocked_text}")
        fish = int(QSettings("Pawse", "Pawse").value("canned_fish", 0))
        self.fish_count.setText(f"Canned Fish earned: {fish} \U0001F96B")

    def showEvent(self, event):
        self._refresh_rules()
        super().showEvent(event)
