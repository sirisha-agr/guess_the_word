from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from collections import Counter
import random
from datetime import date

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///game.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='player')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(5), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_word = db.Column(db.String(5), nullable=False)
    game_date = db.Column(db.Date, nullable=False)
    won = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    user = db.relationship('User', backref='games')

class Guess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    guess_word = db.Column(db.String(5), nullable=False)
    feedback = db.Column(db.String(5), nullable=False)  # e.g., 'GOYGG'
    guess_number = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    game = db.relationship('Game', backref='guesses')

def init_db():
    with app.app_context():
        db.create_all()
        
        # Insert initial words if empty
        if Word.query.count() == 0:
            word_list = [
                'CRANE', 'SLOTH', 'TRACE', 'SNOUT', 'STARE', 'SLEPT', 'SPLIT', 'TRASH',
                'PLANT', 'FLASK', 'STORM', 'CLOUD', 'RIVER', 'OCEAN', 'MOUNT', 'PEAKS',
                'FLAME', 'SPARK', 'BLADE', 'SWORD'
            ]
            for word in word_list:
                new_word = Word(word=word.upper())
                db.session.add(new_word)
            db.session.commit()
        
        # Create default admin if not exists
        if not User.query.filter_by(username='admin').first():
            hashed_pwd = generate_password_hash('adminpass@123')
            admin = User(username='admin', password=hashed_pwd, role='admin')
            db.session.add(admin)
            db.session.commit()

# Initialize database
init_db()

# Helper function
def get_feedback(secret, guess):
    feedback = ['gray'] * 5
    s_count = Counter(secret)
    
    # Mark greens
    for i in range(5):
        if guess[i] == secret[i]:
            feedback[i] = 'green'
            s_count[guess[i]] -= 1
    
    # Mark oranges
    for i in range(5):
        if feedback[i] == 'gray' and s_count[guess[i]] > 0:
            feedback[i] = 'orange'
            s_count[guess[i]] -= 1
    
    return feedback

# Routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if len(username) < 5 or not username.isalpha():
        return jsonify({'error': 'Username must be at least 5 letters (A-Z, a-z only)'}), 400
    
    if len(password) < 5:
        return jsonify({'error': 'Password must be at least 5 characters'}), 400
    
    if not any(c.isalpha() for c in password):
        return jsonify({'error': 'Password must contain at least one letter'}), 400
    
    if not any(c.isdigit() for c in password):
        return jsonify({'error': 'Password must contain at least one digit'}), 400
    
    if not any(c in '$%*@' for c in password):
        return jsonify({'error': 'Password must contain at least one special character ($, %, *, @)'}), 400
    
    try:
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'Registration successful', 'user_id': new_user.id})
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Username already exists'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):
        return jsonify({
            'message': 'Login successful',
            'user_id': user.id,
            'username': username,
            'role': user.role
        })
    
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/api/start-game', methods=['POST'])
def start_game():
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User  ID required'}), 400
    
    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    today = date.today()  # Use date object, not isoformat() string
    
    # Check daily limit
    games_today = Game.query.filter_by(user_id=user_id, game_date=today).count()
    
    if games_today >= 3:
        return jsonify({'error': 'Daily limit reached (3 games per day)'}), 400
    
    # Get random word
    all_words = Word.query.all()
    if not all_words:
        return jsonify({'error': 'No words available'}), 500
    target_word = random.choice(all_words).word
    
    # Create game
    new_game = Game(user_id=user_id, target_word=target_word, game_date=today)
    db.session.add(new_game)
    db.session.commit()
    
    return jsonify({
        'game_id': new_game.id,
        'target_word': target_word,
        'remaining_guesses': 5
    })

@app.route('/api/submit-guess', methods=['POST'])
def submit_guess():
    data = request.get_json()
    game_id = data.get('game_id')
    guess_word = data.get('guess_word', '').strip().upper()
    user_id = data.get('user_id')
    
    if not game_id or not guess_word or not user_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        game_id = int(game_id)
        user_id = int(user_id)
    except ValueError:
        return jsonify({'error': 'Invalid game ID or user ID'}), 400
    
    if len(guess_word) != 5 or not guess_word.isalpha():
        return jsonify({'error': 'Guess must be exactly 5 uppercase letters'}), 400
    
    game = Game.query.filter_by(id=game_id, user_id=user_id).first()
    
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    if game.won:
        return jsonify({'error': 'Game already completed'}), 400
    
    # Get current guess count
    guess_count = Guess.query.filter_by(game_id=game_id).count()
    
    if guess_count >= 5:
        return jsonify({'error': 'Maximum guesses reached'}), 400
    
    # Calculate feedback
    feedback = get_feedback(game.target_word, guess_word)
    feedback_str = ''.join(['G' if f == 'green' else 'O' if f == 'orange' else 'Y' for f in feedback])
    
    # Save guess
    new_guess = Guess(
        game_id=game_id,
        guess_word=guess_word,
        feedback=feedback_str,
        guess_number=guess_count + 1
    )
    db.session.add(new_guess)
    
    # Check if game is won
    is_correct = guess_word == game.target_word
    remaining_guesses = 4 - guess_count
    
    if is_correct:
        game.won = True
        remaining_guesses = 0
    
    db.session.commit()
    
    return jsonify({
        'feedback': feedback,
        'is_correct': is_correct,
        'remaining_guesses': remaining_guesses,
        'game_completed': is_correct or (guess_count + 1 == 5)
    })

@app.route('/api/daily-report', methods=['GET'])
def daily_report():
    report_date_str = request.args.get('date', date.today().isoformat())
    
    try:
        report_date = date.fromisoformat(report_date_str)  # Parse string to date object
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    num_users = db.session.query(Game.user_id).filter(Game.game_date == report_date).distinct().count()
    
    num_correct = Game.query.filter(Game.game_date == report_date, Game.won == True).count()
    
    return jsonify({
        'date': report_date.isoformat(),  # Serialize back to string for JSON
        'num_users': num_users,
        'num_correct': num_correct
    })

@app.route('/api/user-report', methods=['GET'])
def user_report():
    username = request.args.get('username')
    
    if not username:
        return jsonify({'error': 'Username required'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({'error': 'User  not found'}), 404
    
    results = db.session.query(
        Game.game_date,
        db.func.count(Game.id).label('words_tried'),
        db.func.sum(Game.won).label('correct_guesses')
    ).filter(Game.user_id == user.id)\
     .group_by(Game.game_date)\
     .order_by(Game.game_date.desc())\
     .all()
    
    report_data = []
    for row in results:
        report_data.append({
            'date': row.game_date.isoformat(),
            'words_tried': row.words_tried,
            'correct_guesses': row.correct_guesses or 0
        })
    
    return jsonify({
        'username': username,
        'report': report_data
    })

@app.route('/api/game-status', methods=['GET'])
def game_status():
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User  ID required'}), 400
    
    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({'error': 'Invalid user ID'}), 400
    
    today = date.today()  # Use date object, not isoformat() string
    
    games_today = Game.query.filter_by(user_id=user_id, game_date=today).count()
    
    return jsonify({
        'games_played_today': games_today,
        'games_remaining': max(0, 3 - games_today)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
