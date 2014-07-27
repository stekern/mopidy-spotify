from __future__ import unicode_literals

import logging
import os
import threading

from mopidy import backend

import pykka

import spotify


logger = logging.getLogger(__name__)


class SpotifyBackend(pykka.ThreadingActor, backend.Backend):

    _logged_in = threading.Event()
    _logged_out = threading.Event()
    _logged_out.set()

    def __init__(self, config, audio):
        super(SpotifyBackend, self).__init__()

        self._config = config
        self._audio = audio

        spotify_config = spotify.Config()
        spotify_config.load_application_key_file(
            os.path.join(os.path.dirname(__file__), 'spotify_appkey.key'))
        spotify_config.cache_location = self._config['spotify']['cache_dir']
        spotify_config.settings_location = (
            self._config['spotify']['settings_dir'])
        self._session = spotify.Session(spotify_config)
        self._event_loop = spotify.EventLoop(self._session)

        self.library = None
        self.playback = None
        self.playlists = None

        self.uri_schemes = ['spotify']

    def on_start(self):
        self._session.on(
            spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            SpotifyBackend.on_connection_state_changed)

        self._event_loop.start()

        self._session.login(
            self._config['spotify']['username'],
            self._config['spotify']['password'])

    def on_stop(self):
        # TODO Wait for the logout to complete
        logger.debug('Logging out of Spotify')
        self._session.logout()
        self._logged_out.wait()
        self._event_loop.stop()

    @classmethod
    def on_connection_state_changed(cls, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            logger.info('Connected to Spotify')
            cls._logged_in.set()
            cls._logged_out.clear()
        elif session.connection.state is spotify.ConnectionState.LOGGED_OUT:
            logger.debug('Logged out of Spotify')
            cls._logged_in.clear()
            cls._logged_out.set()
