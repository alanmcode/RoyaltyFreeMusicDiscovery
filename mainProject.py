import requests
import json
import sys
import random
from PyQt5.QtWidgets import *
from PyQt5 import uic, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl
from pprint import pprint
from dotenv import load_dotenv
import os

load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
API_KEY = os.getenv("API_KEY")

auth_url = 'https://accounts.spotify.com/api/token'
auth_response = requests.post(auth_url, {
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
})
auth_response_data = auth_response.json()
access_token = auth_response_data['access_token']

#pyqtui
Ui_MainWindow, QtBaseClass = uic.loadUiType("firstwindow.ui")

class Project(QtWidgets.QMainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.findsong.clicked.connect(self.generate)
        self.ui.playbutton.clicked.connect(self.get_url)
        self.setWindowTitle("Spotify to Jamendo")

    #spotify
    def get_track_id(self, track_name):
        query = track_name.replace(' ', '%20')
        search_url = f'https://api.spotify.com/v1/search?q={query}&type=track&limit=1'
        search_response = requests.get(search_url, headers={
            'Authorization': f'Bearer {access_token}'
        })
        search_response_data = search_response.json()
        print("Spotify search response:", search_response_data)
        items = search_response_data['tracks']['items']
        if not items:
            print("No track found for:", track_name)
            return None
        track_id = items[0]['id']
        return track_id

    def get_recommended_tracks(self, track_id, access_token):
        url = f"https://api.spotify.com/v1/recommendations?seed_tracks={track_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers)
        print("Status code:", response.status_code)
        print("Response text:", response.text)
        if response.status_code != 200:
            print(f"Error: Spotify API returned status code {response.status_code}")
            return []
        data = response.json()
        tracks = data["tracks"]
        recommended_tracks = []
        for track in tracks:
            track_name = track["name"]
            artist_name = track["artists"][0]["name"]
            recommended_tracks.append((track_name, artist_name))
        return recommended_tracks

    def get_audio_analysis(self, track_id, access_token):
        url = f"https://api.spotify.com/v1/audio-analysis/{track_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers)
        data = response.json()
        return data

    def get_genre(self, track_id, access_token):
        url = f"https://api.spotify.com/v1/tracks/{track_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers)
        data = response.json()

        artist_id = [artist["id"] for artist in data["artists"]]

        url = "https://api.spotify.com/v1/artists"
        params = {"ids": ",".join(artist_id)}
        artist_response = requests.get(url, params=params, headers=headers)
        artist_data = artist_response.json()
        #pprint (artist_data)
        
        genres = [] 
        for artist in artist_data["artists"]:
            genres += artist["genres"]
        genres_string = '+'.join(genres)
        return genres_string

    #jamendo
    def get_royaltyfree_tracks(self, tempo, key, mode, genre, API_KEY):
        url = "https://api.jamendo.com/v3.0/tracks/"
        speed_string = '' 
        if tempo in range(0,59):
            speed_string = 'verylow'
        elif tempo in range(60,99):
            speed_string = 'low'
        elif tempo in range(100,139):
            speed_string = 'medium'
        elif tempo in range(140,179):
            speed_string = 'high'
        elif tempo in range(180,999):
            speed_string = 'veryhigh'
        
        params = {
            "client_id": API_KEY,
            "speed": speed_string,
            #"musicinfo": key,
            "vocalinstrumental": "instrumental" if mode == 0 else "vocal",
            "fuzzytags": genre,
            "groupby": "artist_id"
        }
        response = requests.get(url, params=params)
        data = response.json()
        results = data["results"]
        similar_tracks = []
        for track in results:
            track_name = track["name"]
            artist_name = track["artist_name"]
            track_id = track["id"]
            similar_tracks.append((track_name, artist_name, track_id))
        return similar_tracks
        
    def generate(self):
        song_name = self.ui.inputsong.text()
        artist_name = self.ui.inputartist.text()
        song_request = song_name+" "+artist_name
        song_id = self.get_track_id(song_request)
        if not song_id:
            print("Could not find track ID for:", song_request)
            self.ui.jamendooutput.setText("Track not found on Spotify.")
            return
        print(song_id)
        print(self.get_recommended_tracks(song_id, access_token))

        audio_analysis = self.get_audio_analysis(song_id, access_token)
        genre = self.get_genre(song_id, access_token)
        tempo = audio_analysis["track"]["tempo"]
        key = audio_analysis["track"]["key"]
        mode = audio_analysis["track"]["mode"]
        print(tempo, key, mode, genre)
        similar_tracks = self.get_royaltyfree_tracks(tempo, key, mode, genre, API_KEY)
        print(similar_tracks)

        print("Recommended Jamendo track:")
        track = random.choice(similar_tracks)
        print(track)
        self.ui.jamendooutput.setEnabled(True)
        self.ui.playbutton.setEnabled(True)
        self.ui.jamendooutput.setText(track[0] + " - " + track[1]) 
        track_url_id = track[2]
        self.url = f"https://www.jamendo.com/track/{track_url_id}"

    def get_url(self):
        track_url_id = self.url
        QDesktopServices.openUrl(QUrl(track_url_id))
    
def main():
    app = QApplication(sys.argv)
    window = Project() #initialise UI
    window.show() #shows window
    sys.exit(app.exec_())

main()
