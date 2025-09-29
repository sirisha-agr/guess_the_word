import streamlit as st
import requests
from collections import Counter
import json

# API base URL
API_BASE = "http://localhost:5000/api"

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'role' not in st.session_state:
    st.session_state.role = None
if 'current_game' not in st.session_state:
    st.session_state.current_game = None
if 'target_word' not in st.session_state:
    st.session_state.target_word = None
if 'guesses' not in st.session_state:
    st.session_state.guesses = []

def register_user(username, password):
    try:
        response = requests.post(f"{API_BASE}/register", json={
            'username': username,
            'password': password
        })
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {'error': f"Could not connect to server: {e}"}


def login_user(username, password):
    try:
        response = requests.post(f"{API_BASE}/login", json={
            'username': username,
            'password': password
        })
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {'error': f"Could not connect to server: {e}"}


def start_new_game(user_id):
    try:
        response = requests.post(f"{API_BASE}/start-game", json={
            'user_id': user_id
        })
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {'error': f"Could not connect to server: {e}"}


def submit_guess(game_id, guess_word, user_id):
    try:
        response = requests.post(f"{API_BASE}/submit-guess", json={
            'game_id': game_id,
            'guess_word': guess_word,
            'user_id': user_id
        })
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {'error': f"Could not connect to server: {e}"}


def get_daily_report(report_date):
    try:
        response = requests.get(f"{API_BASE}/daily-report?date={report_date}")
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {'error': f"Could not connect to server: {e}"}


def get_user_report(username):
    try:
        response = requests.get(f"{API_BASE}/user-report?username={username}")
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {'error': f"Could not connect to server: {e}"}


def get_game_status(user_id):
    try:
        response = requests.get(f"{API_BASE}/game-status?user_id={user_id}")
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f"Error {response.status_code}: {response.text}"}
    except requests.exceptions.RequestException as e:
        return {'error': f"Could not connect to server: {e}"}


def display_guess_grid(guesses):
    for guess, feedback in guesses:
        cols = st.columns(5)
        for j, (letter, fb) in enumerate(zip(guess, feedback)):
            color = '#4CAF50' if fb == 'green' else '#FF9800' if fb == 'orange' else '#9E9E9E'
            with cols[j]:
                st.markdown(
                    f"""
                    <div style="
                        width: 60px; 
                        height: 60px; 
                        background-color: {color}; 
                        color: white; 
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                        border: 2px solid #333; 
                        font-weight: bold;
                        font-size: 24px;
                        border-radius: 8px;
                        margin: 2px;
                    ">{letter}</div>
                    """,
                    unsafe_allow_html=True
                )

st.set_page_config(page_title="Guess the Word", page_icon="🎯", layout="wide")
st.title("🎯 Guess the Word Game")

# Sidebar for authentication
with st.sidebar:
    st.header("🔐 Authentication")
    
    if st.session_state.user_id is None:
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Login", use_container_width=True):
                result = login_user(username, password)
                if 'error' in result:
                    st.error(result['error'])
                else:
                    st.session_state.user_id = result['user_id']
                    st.session_state.username = result['username']
                    st.session_state.role = result['role']
                    st.success(f"Welcome {result['username']}!")
                    st.rerun()
        
        with tab2:
            new_user = st.text_input("Username (min 5 letters)", key="reg_user")
            new_pass = st.text_input("Password (min 5 chars: alpha, num, $%*@)", 
                                   type="password", key="reg_pass")
            
            if st.button("Register", use_container_width=True):
                result = register_user(new_user, new_pass)
                if 'error' in result:
                    st.error(result['error'])
                else:
                    st.success("Registration successful! Please login.")
    
    else:
        st.success(f"Logged in as: {st.session_state.username}")
        st.info(f"Role: {st.session_state.role}")
        
        # Game status
        status = get_game_status(st.session_state.user_id)
        if 'error' not in status:
            st.metric("Games Played Today", status['games_played_today'])
            st.metric("Games Remaining", status['games_remaining'])
        
        if st.button("Logout", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.role = None
            st.session_state.current_game = None
            st.session_state.target_word = None
            st.session_state.guesses = []
            st.rerun()

# Main content
if st.session_state.user_id is None:
    st.info("Please login or register to play the game.")
    st.stop()

if st.session_state.role == 'player':
    # Player interface
    st.header("🎮 Play Game")
    
    if st.session_state.current_game is None:
        status = get_game_status(st.session_state.user_id)
        if 'error' in status:
            st.error(status['error'])
        else:
            if status['games_remaining'] > 0:
                st.info(f"You have {status['games_remaining']} games remaining today")
                if st.button("Start New Game", type="primary"):
                    result = start_new_game(st.session_state.user_id)
                    if 'error' in result:
                        st.error(result['error'])
                    else:
                        st.session_state.current_game = result['game_id']
                        st.session_state.target_word = result['target_word']
                        st.session_state.guesses = []
                        st.rerun()
            else:
                st.warning("You've reached your daily limit of 3 games. Come back tomorrow!")
    else:
        # Active game
        st.subheader("Make Your Guess")
        st.info("Enter a 5-letter word (A-Z only)")
        
        guess = st.text_input("Your guess:", max_chars=5, key="guess_input").upper()
        
        if st.button("Submit Guess", type="primary", disabled=len(guess) != 5):
            result = submit_guess(st.session_state.current_game, guess, st.session_state.user_id)
            if 'error' in result:
                st.error(result['error'])
            else:
                st.session_state.guesses.append((guess, result['feedback']))
                
                if result['is_correct']:
                    st.balloons()
                    st.success("🎉 Congratulations! You guessed the word correctly!")
                    if st.button("Play Again"):
                        st.session_state.current_game = None
                        st.session_state.target_word = None
                        st.session_state.guesses = []
                        st.rerun()
                elif result['game_completed']:
                    st.error(f"❌ Game over! The word was: {st.session_state.target_word}")
                    if st.button("Try Again"):
                        st.session_state.current_game = None
                        st.session_state.target_word = None
                        st.session_state.guesses = []
                        st.rerun()
                else:
                    st.info(f"Remaining guesses: {result['remaining_guesses']}")
                    st.rerun()
        
        # Display previous guesses
        if st.session_state.guesses:
            st.subheader("Your Guesses")
            display_guess_grid(st.session_state.guesses)

elif st.session_state.role == 'admin':
    # Admin interface
    st.header("📊 Admin Reports")
    
    tab1, tab2 = st.tabs(["Daily Report", "User Report"])
    
    with tab1:
        st.subheader("Daily Statistics")
        report_date = st.date_input("Select date")
        if st.button("Generate Daily Report"):
            result = get_daily_report(report_date.isoformat())
            if 'error' in result:
                st.error(result['error'])
            else:
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Number of Users", result['num_users'])
                with col2:
                    st.metric("Correct Guesses", result['num_correct'])
    
    with tab2:
        st.subheader("User Statistics")
        username = st.text_input("Enter username")
        if st.button("Generate User Report"):
            result = get_user_report(username)
            if 'error' in result:
                st.error(result['error'])
            else:
                st.subheader(f"Report for {result['username']}")
                if result['report']:
                    # Convert to DataFrame for nice display
                    import pandas as pd
                    df = pd.DataFrame(result['report'])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No games recorded for this user.")