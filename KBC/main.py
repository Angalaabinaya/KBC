from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import base64
import os
import random
import tkinter as tk

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_key')

Base = declarative_base()

# Define the Question model
class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_text = Column(String, nullable=False)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    correct_option = Column(String, nullable=False)  # Store the correct option (e.g., 'A')

# Database setup
def setup_database():
    engine = create_engine('sqlite:///quiz.db', connect_args={'check_same_thread': False})  # Using SQLite for simplicity
    Base.metadata.create_all(engine)
    return engine

engine = setup_database()
Session = sessionmaker(bind=engine)
db_session = Session()

@app.route('/')
def index():
    session.clear()  # Clears all session data
    return render_template('index1.html')

@app.route('/instruction')
def instruction():

    return render_template('instruction.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        photo_data = request.form['captured_photo']

        if photo_data:
            # Save the captured photo
            photo_data = photo_data.split(",")[1]  # Remove the data URL prefix
            photo_path = f'static/{name}.png'
            with open(photo_path, "wb") as fh:
                fh.write(base64.b64decode(photo_data))
            session['photo'] = f'{name}.png'
        else:
            # No photo was captured or skipped, use default or blank image
            session['photo'] = 'avatar.jpg'  # Or another fallback image

        session['name'] = name
        session['score'] = 0
        session['current_question_index'] = 0
        session['clue_used'] = False
        session['questions_answered'] = 0  # Initialize the number of questions answered

        # Fetch and shuffle questions
        question_ids = [q.id for q in db_session.query(Question).all()]
        if not question_ids:
            return "No questions available. Please contact the administrator."
        random.shuffle(question_ids)
        session['question_ids'] = question_ids

        return redirect(url_for('question'))
    return render_template('register.html')
@app.route('/question', methods=['GET', 'POST'])
def question():
    if 'current_question_index' not in session:
        return redirect(url_for('register'))

    # Check if the question index is valid
    if not session.get('question_ids') or session['current_question_index'] >= len(session['question_ids']):
        return redirect(url_for('result'))  # Redirect if no more questions

    # Get the current question
    question_id = session['question_ids'][session['current_question_index']]
    question = db_session.query(Question).filter_by(id=question_id).first()

    if not question:
        return redirect(url_for('result'))  # Redirect to result if the question doesn't exist

    question_scores = [100000, 200000, 500000, 1000000, 2000000, 3000000, 3200000]
    current_question_score = question_scores[session['questions_answered']]

    if request.method == 'POST':
        selected_option = request.form['option']
        if selected_option == question.correct_option:
            session['score'] += current_question_score
            session['correct_answer'] = True  # Flag to show correct answer modal
        else:
            return redirect(url_for('result'))  # End the game on incorrect answer

        session['current_question_index'] += 1
        session['questions_answered'] += 1

        if session['questions_answered'] >= 7:
            return redirect(url_for('result'))  # Redirect to result if all questions are answered
        else:
            session['clue_used'] = False  # Reset clue used flag for the next question
            session.pop('reduced_options', None)  # Clear reduced options for the next question
            return redirect(url_for('question'))  # Redirect to next question

    options = {
        'A': question.option_a,
        'B': question.option_b,
        'C': question.option_c,
        'D': question.option_d
    }

    if session.get('clue_used') and 'reduced_options' in session:
        options = session['reduced_options']

    return render_template('question.html', question=question, options=options, clue_used=session.get('clue_used', False))
@app.route('/use_clues')
def use_clues():
    if 'current_question_index' not in session:
        return redirect(url_for('register'))

    # Check if all questions are answered (i.e., 7 questions answered)
    if session.get('questions_answered', 0) >= 7:
        return redirect(url_for('result'))  # No more clues after all questions are answered

    question_id = session['question_ids'][session['current_question_index']]
    question = db_session.query(Question).filter_by(id=question_id).first()

    if not question:
        return redirect(url_for('result'))

    # Ensure clue is only used once per question
    if session.get('clue_used', False):
        return redirect(url_for('question'))  # Clue already used, redirect to question

    # Mark clue as used for the current question
    session['clue_used'] = True

    # Reduce the score only if it's greater than 0
    if session['score'] > 0:
        session['score'] = session['score'] // 2  # Use integer division for whole number scores

    # Prepare reduced options
    options = {
        'A': question.option_a,
        'B': question.option_b,
        'C': question.option_c,
        'D': question.option_d
    }
    incorrect_options = [key for key, value in options.items() if key != question.correct_option]
    random_incorrect = random.choice(incorrect_options)
    reduced_options = {
        question.correct_option: options[question.correct_option],
        random_incorrect: options[random_incorrect]
    }

    # Store reduced options in the session
    session['reduced_options'] = reduced_options

    # Clear any existing 'correct_answer' flag to avoid showing the correct answer modal
    session.pop('correct_answer', None)

    return redirect(url_for('question'))

@app.route('/result')
def result():
    if session['score']>0:
        return render_template('result.html', name=session['name'], photo=session['photo'], score=session['score'])
    else:
        return render_template('result_fail.html',name=session['name'], photo=session['photo'], score=session['score'])

@app.route('/timeout')
def timeout():
    # End the current question and move to result page
    return redirect(url_for('result'))

if __name__ == '__main__':
    app.run(debug=True)
