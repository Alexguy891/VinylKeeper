# Author: Alex Ely
# Program Details:
# 1. User chooses whether to start session or display data
# 2. When session started:
#   a. Microphone is accessed and begins recording
#   b. Microphone continuously records until user ends session.
#   c. Audio file is saved
#   d. Audio file is accessed by Echo Nest API
#   e. When song is recognized:
#       i. Echo Nest API pulls song name, artist, album, genre.
#       ii. SQLite database checks for existing song table, creates if it doesn't exist
#       iii. SQLite inserts song into database
# 3. When display data chosen
#   a. User given sort options:
#       i. Sort by song name
#       ii. Sort by artist name
#       iii. Sort by album name
#       iv. Sort by genre
#       v. Sort by song plays
#       vi. Sort by artist plays
#       vii. Sort by album plays
#       viii. Sort by genre plays

import pyaudio
import wave
import acoustid
import musicbrainzngs
import sqlite3
import time
from pydub import AudioSegment

# SQLite Settings
connection = sqlite3.connect("test.db")
cursor = connection.cursor()

# PyAudio settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
WAVE_OUTPUT_FILENAME = "session.wav"

# PyDub Segment Length
SEGMENT_LENGTH = 1_000 # 10s

# PyAudio object
audioObject = pyaudio.PyAudio()

# Start audio recording session
def startSession():
    # Audio stream object
    audioStream = audioObject.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    # Print for user
    print("Session started, press any key to end...")

    # Initialize frames list
    audioFrames = []

    # Recording loop
    try:
        while True:
            # Record audio data
            audioData = audioStream.read(CHUNK)
            audioFrames.append(audioData)
    except KeyboardInterrupt:
        pass

    # Write to wav file
    audioData = b''.join(audioFrames)
    waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    waveFile.setnchannels(CHANNELS)
    waveFile.setsampwidth(audioObject.get_sample_size(FORMAT))
    waveFile.setframerate(RATE)
    waveFile.writeframes(audioData)
    waveFile.close()
    
    # Calling audio read function
    readAudio()

# Send song data to database
def sendToDatabase(songName, artistName, albumName, genreName):
    # Create table if it doesn't exist
    if cursor.execute("""
        SELECT tableName FROM 
        sqlite_master WHERE
        type='table' AND 
        tableName'SONGS';""").fetchall() == []:
            cursor.execute("""CREATE TABLE SONGS(
                TIMESTAMP TEXT, 
                NAME VARCHAR(255),
                ARTIST VARCHAR(255),
                ALBUM VARCHAR(255),
                GENRE VARCHAR(255));""")
            print("table SONGS did not exist, creating...")

    # Insert data into database
    cursor.execute("INSERT INTO SONGS VALUES(?,?,?,?,?)",
        (time.time(), songName, artistName, albumName, genreName))
    print("song inserted.")

# Read songs from wav file
def readAudio():
    # Open and check audio file
    waveFile = AudioSegment.from_wav(WAVE_OUTPUT_FILENAME)
    audioSegments = waveFile[::SEGMENT_LENGTH]

    # Used for checking if segment is the same song
    previousSongName = None
    previousSongArtist = None

    # Loop through all created segments
    for audioSegment in audioSegments:
        print("Fingerprinting audio segment...")
        audioFingerprint = acoustid.fingerprint(audioSegment.raw_data, audioSegment.frame_rate, audioSegment.sample_width)
        print("Looking up fingerprint...")
        songResults = acoustid.lookup(audioFingerprint)

        print("Audio segment looked up...")

        # Loop through all results and end on first
        for songResult in songResults:
            print("Going through song results...")

            recordingID = songResult["id"]
            recording = musicbrainzngs.get_area_by_id(
                recordingID, 
                includes = [
                    "artists", "releases", "genres"
                ]
            )

            # Get song details
            songName = recording["recording"]["title"]
            artistName = recording["recording"]["artist-credit"][0]["name"]
            albumName = recording["recording"]["release-list"][0]["title"]
            genreName = recording["genre-list"][0]["name"]
            break
    
        # Send to database if segment is not the same song
        if not (previousSongName == songName and previousSongArtist == artistName):
            previousSongName = songName
            previousSongArtist = artistName
            sendToDatabase(songName, artistName, albumName, genreName)

# User choice for session or data display
def userChoice():
    userChoice = None

    # Check user input and call function
    while(userChoice != "q"):
        userChoice = input("start [s]ession | [d]isplay data | [q]uit? ")

        if userChoice == "s":
            readAudio()
        elif userChoice == "d":
            displayData()
        elif userChoice == 'q':
            print("quitting...")
            break
        else:
            print("Invalid input, please try again.")

def main():
    userChoice()

if __name__ == "__main__":
    main()