from flask import Flask, render_template, request
import requests
import base64
import os
import json
import random 

template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)


#spotify credentials to log in
client_id = "71f9f7c00a514322b5181c8c1520875b"
client_secret = "4b667db6f2414349ad279662f05eb739"


def get_token():
    """Authenticates the application with Spotify using Client Credentials."""
    auth_string = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_string.encode()).decode()
    
    headers = {"Authorization": f"Basic {b64_auth}"}
    data = {"grant_type": "client_credentials"}
    
    res = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    
    return res.json().get("access_token")

def get_tracks_fallback(token, mood, genre):
    """Simple track search fallback using the existing logic, used if no playlists are found."""
    headers = {"Authorization": f"Bearer {token}"}
    query = f"{mood} {genre}" 
    params = {"q": query, "type": "track", "limit": 10}
    res = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)

    if res.status_code != 200: return []
    data = res.json()
    tracks = data.get("tracks", {}).get("items", [])
    
    playlist = []
    for track in tracks:
        name = track["name"]
        artist = track["artists"][0]["name"]
        url = track["external_urls"]["spotify"]
        image_url = track["album"]["images"][1]["url"] if track["album"]["images"] and len(track["album"]["images"]) > 1 else None
        playlist.append({"name": name, "artist": artist, "url": url, "image": image_url})
    return playlist

def get_playlist(mood, genre):
    """Searches Spotify for a relevant playlist and pulls tracks from it for better relevance."""
    token = get_token()
    if token is None:
        return []

    headers = {"Authorization": f"Bearer {token}"}
    query = f"{mood} {genre} playlist" 

    # Step 1: Search for a public Playlist
    params = {"q": query, "type": "playlist", "limit": 10} 
    res = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)

    if res.status_code != 200:
        print(f"Playlist Search Failed. Status: {res.status_code}")
        return get_tracks_fallback(token, mood, genre)

    data = res.json()
    playlists = data.get("playlists", {}).get("items", [])
    
    # Filter out any playlists without valid IDs
    valid_playlists = [p for p in playlists if p is not None and 'id' in p]

    if not valid_playlists:
        print("No specific playlists found or valid IDs found, falling back to simple track search.")
        return get_tracks_fallback(token, mood, genre)
    
    # Choose a random valid playlist
    playlist_id = random.choice(valid_playlists)['id'] 
    
    # Step 2: Get Tracks from the Chosen Playlist
    tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    params = {"limit": 20, "fields": "items(track(name,artists,external_urls,album))"} # Requesting 20 to ensure 10 are returned
    
    res = requests.get(tracks_url, headers=headers, params=params)

    if res.status_code != 200:
        print(f"Playlist Tracks Fetch Failed. Status: {res.status_code}")
        return []

    data = res.json()
    tracks_data = data.get("items", [])
    
    playlist = []
    # Take the first 10 tracks
    for item in tracks_data:
        track = item.get('track')
        if not track: continue 
        
        name = track.get("name")
        artist = track["artists"][0]["name"]
        url = track["external_urls"]["spotify"]
        
        # Pull the album cover URL
        image_url = track["album"]["images"][1]["url"] if track["album"]["images"] and len(track["album"]["images"]) > 1 else None
        
        playlist.append({"name": name, "artist": artist, "url": url, "image": image_url})
        
        if len(playlist) >= 10: # <--- CHANGED TO 10
            break
            
    return playlist

@app.route("/", methods=["GET", "POST"])
def home():
    playlist = []
    
    if request.method == "POST":
        mood = request.form.get("mood")
        genre = request.form.get("genre")
        playlist = get_playlist(mood, genre)
        
    return render_template("index.html", playlist=playlist)

if __name__ == "__main__":
    app.run(debug=True)