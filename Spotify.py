import requests
import base64
import webbrowser
import json
import urllib.parse as url


class Spotify(object):
    def __init__(self, json_file):
        # Client Properties
        self.json_data = json_file

        # Authorization code
        self.auth_str_64 = base64.urlsafe_b64encode("{}:{}".format(self.json_data["spotify"]["client_id"],
                                                                   self.json_data["spotify"]["client_secret"]).encode()).decode()
        self.token_header = {"Authorization": "Basic {}".format(self.auth_str_64)}

        # URIs
        self.token_uri = "{}{}".format(self.json_data["spotify"]["account_uri"], "api/token")
        self.auth_uri = "{}{}{}".format(self.json_data["spotify"]["account_uri"], "authorize?",
                                        url.unquote(url.urlencode({"client_id": self.json_data["spotify"]["client_id"],
                                                                   "response_type": self.json_data["spotify"]["response_type"],
                                                                   "redirect_uri": self.json_data["spotify"]["redirect_uri"],
                                                                   "scope": self.json_data["spotify"]["scope"],
                                                                   "state": self.json_data["spotify"]["state"]})))
        self.songs_to_add = {}

        # self.get_tokens()
        self.update_access_token()

    # Gets access and refresh tokens, updates them
    def get_tokens(self):
        # if tokens expire, get auth code
        webbrowser.open(self.auth_uri, autoraise=True)

        self.json_data["spotify"]["code"] = input("Enter the code you receive here: ")
        with open("config.json", "w") as json_file:
            json.dump(self.json_data, json_file, indent=4, sort_keys=True)

        access_token_post_body = {
            "code": self.json_data["spotify"]["code"],
            "grant_type": "authorization_code",
            "redirect_uri": self.json_data["spotify"]["redirect_uri"]
        }

        request = requests.post(self.token_uri, data=access_token_post_body, headers=self.token_header)
        response = json.loads(request.text)

        self.json_data["spotify"]["access_token"] = response["access_token"]
        self.json_data["spotify"]["refresh_token"] = response["refresh_token"]

        with open("config.json", "w") as json_file:
            json.dump(self.json_data, json_file, indent=4, sort_keys=True)

    # Updates access token using refresh token
    def update_access_token(self):
        refresh_token_post_body = {
            "grant_type": "refresh_token",
            "refresh_token": self.json_data["spotify"]["refresh_token"]
        }

        request = requests.post(self.token_uri, data=refresh_token_post_body, headers=self.token_header)
        response = json.loads(request.text)

        self.json_data["spotify"]["access_token"] = response["access_token"]
        with open("config.json", "w") as json_file:
            json.dump(self.json_data, json_file, indent=4, sort_keys=True)

    def get_recommended_songs(self):
        request_body = {
            "seed_genres": self.json_data["spotify"]["seed_genres"],
            "limit": "100",
        }

        uri = self.json_data["spotify"]["api_uri"] + "recommendations"
        request_header = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(self.json_data["spotify"]["access_token"])
        }
        request = requests.get(uri, params=request_body, headers=request_header)

        response = request.json()
        for song in response["tracks"]:
            self.songs_to_add[song["name"]] = {
                "song": song["name"],
                "artist": song["artists"][0]["name"],
                "spotify_uri": song["uri"]
            }

    def create_playlist(self):
        query_string = "{}users/{}/playlists".format(self.json_data["spotify"]["api_uri"], self.json_data["spotify"]["user_id"])
        request_header = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(self.json_data["spotify"]["access_token"])
        }
        request = requests.get(query_string, headers=request_header)
        response = request.json()

        for item in response["items"]:
            if item["name"] == "Generated Playlist":
                return item

        request_body = json.dumps({"name": "Generated Playlist", "description": "Generated Playlist", "public": True})
        request = requests.post(query_string, data=request_body, headers=request_header)
        response = request.json()

        return response

    def populate_playlist(self):

        for i in range(len(self.songs_to_add) - 100):
            self.songs_to_add.pop(next(iter(self.songs_to_add)))

        song_uris = [info["spotify_uri"] for song, info in self.songs_to_add.items()]
        request_body = json.dumps(song_uris)
        query = "{}playlists/{}/tracks".format(self.json_data["spotify"]["api_uri"], self.create_playlist()["id"])
        request_header = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(self.json_data["spotify"]["access_token"])
        }
        requests.post(query, data=request_body, headers=request_header)

    def number_of_songs_added(self):
        return len(self.songs_to_add)