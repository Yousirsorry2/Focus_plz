"""Music and Settings destinations for the shared desktop navigation."""

import json
from urllib.parse import parse_qs, quote, urlsplit

from PySide6.QtCore import QSettings, Qt, Signal, QUrl
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QRadioButton, QScrollArea, QStackedWidget, QVBoxLayout,
                               QWidget)
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.config import load_config
from ui.mochi import MochiCat
from ui.navigation import BottomNavigation
from ui.tasks_theme import FULL_QSS
from ui.theme import make_paw_icon


class _NavigationPage(QWidget):
    navigation_requested = Signal(str)

    def __init__(self, active):
        super().__init__()
        self.setObjectName("TasksWindow")
        self.setWindowTitle(f"Pawse - {active}")
        self.setWindowIcon(make_paw_icon())
        self.setStyleSheet(FULL_QSS)
        self.setFixedSize(1200, 760)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.navigation = BottomNavigation(active, self)
        self.navigation.selected.connect(self.navigation_requested.emit)
        outer.addWidget(self.navigation)
        content = QWidget()
        self.root = QVBoxLayout(content)
        self.root.setContentsMargins(38, 28, 38, 26)
        self.root.setSpacing(0)
        outer.addWidget(content, 1)


class MusicView(_NavigationPage):
    def __init__(self, parent=None):
        super().__init__("Music")
        self.settings = QSettings("Pawse", "Pawse")
        self.status = QLabel("")
        self.status.setObjectName("musicStatus")
        self.now_playing = QLabel("Choose a saved link to play it here.")
        self.now_playing.setObjectName("musicHint")

        eyebrow = QLabel("YOUR CALM LITTLE CORNER / MUSIC")
        eyebrow.setObjectName("sectionEyebrow")
        title = QLabel("Cozy Sounds")
        title.setObjectName("sectionTitle")
        note = QLabel("A softer soundtrack for your day.")
        note.setObjectName("subtitle")
        self.root.addWidget(eyebrow)
        self.root.addSpacing(8)
        self.root.addWidget(title)
        self.root.addSpacing(4)
        self.root.addWidget(note)
        self.root.addSpacing(24)

        content = QHBoxLayout()
        content.setSpacing(20)
        player_card = QFrame()
        player_card.setObjectName("softCard")
        player = QVBoxLayout(player_card)
        player.setContentsMargins(28, 28, 28, 28)
        player.setSpacing(16)
        self.player_stack = QStackedWidget()
        self.player_stack.setMinimumHeight(300)
        self.player_placeholder = QWidget()
        placeholder = QVBoxLayout(self.player_placeholder)
        placeholder.addStretch(1)
        placeholder.addWidget(MochiCat("sleeping", width=250), 0, Qt.AlignHCenter)
        placeholder.addStretch(1)
        self.web_player = QWebEngineView()
        self.web_player.setMinimumHeight(300)
        self.web_player.loadFinished.connect(self._on_player_load_finished)
        self.player_stack.addWidget(self.player_placeholder)
        self.player_stack.addWidget(self.web_player)
        player.addWidget(self.player_stack, 1)
        player.addWidget(QLabel("A LITTLE BACKGROUND CALM"), 0, Qt.AlignHCenter)
        self.player_title = QLabel("Made for your quiet moments")
        self.player_title.setObjectName("cardTitle")
        self.player_title.setAlignment(Qt.AlignCenter)
        player.addWidget(self.player_title)
        self.now_playing.setWordWrap(True)
        self.now_playing.setAlignment(Qt.AlignCenter)
        player.addWidget(self.now_playing)
        player.addStretch(1)
        content.addWidget(player_card, 1)

        library = QFrame()
        library.setObjectName("musicCard")
        library_col = QVBoxLayout(library)
        library_col.setContentsMargins(22, 22, 22, 22)
        library_col.setSpacing(12)
        eyebrow = QLabel("YOUR PLAYLISTS")
        eyebrow.setObjectName("sectionEyebrow")
        library_col.addWidget(eyebrow)
        library_title = QLabel("Bring your own music")
        library_title.setObjectName("cardTitle")
        library_col.addWidget(library_title)
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
            add_row.addWidget(button)
        add_row.addStretch(1)
        self.add_button = QPushButton("+  Save playlist")
        self.add_button.setObjectName("capsulePrimary")
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.add_playlist)
        add_row.addWidget(self.add_button)
        library_col.addLayout(add_row)

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
        library_col.addWidget(playlist_scroll, 1)
        content.addWidget(library, 1)
        self.root.addLayout(content, 1)
        self._render_playlists()

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
            layout.setContentsMargins(12, 8, 8, 8)
            layout.setSpacing(8)
            info = QVBoxLayout()
            label = QLabel(f"{provider} link" if provider else "Unsupported saved link")
            label.setObjectName("fieldTitle")
            url_label = QLabel(url)
            url_label.setObjectName("musicHint")
            url_label.setWordWrap(True)
            url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            info.addWidget(label)
            info.addWidget(url_label)
            layout.addLayout(info, 1)
            play = QPushButton("▶  Play")
            play.setObjectName("playlistPlay")
            play.setCursor(Qt.PointingHandCursor)
            play.setEnabled(provider is not None)
            play.clicked.connect(lambda _=False, link=url: self._open_playlist(link))
            layout.addWidget(play)
            remove = QPushButton("×")
            remove.setObjectName("playlistRemove")
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
        note.setAlignment(Qt.AlignCenter)
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
        except OSError as error:
            self.status.setText(f"Could not save the rule: {error}")
            return
        self.rule_input.clear()
        self.status.setText("Rule saved locally and applied immediately.")
        self._refresh_rules()

    def _refresh_rules(self):
        cfg = load_config()
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
