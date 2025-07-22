import requests
import random
import html
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import tkinter as tk
from tkinter import ttk, messagebox
import threading

class APIHandler:
    BASE_URL = "https://opentdb.com/api.php"
    CATEGORIES_URL = "https://opentdb.com/api_category.php"

    def __init__(self):
        self.session = requests.Session()

    def get_categories(self) -> Dict[int, str]:
        try:
            response = self.session.get(self.CATEGORIES_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {cat['id']: cat['name'] for cat in data['trivia_categories']}
        except requests.RequestException as e:
            print(f"Error fetching categories: {e}")
            return {}

    def fetch_questions(self, amount: int = 10, category: Optional[int] = None, 
                        difficulty: Optional[str] = None) -> List[Dict]:
        params = {
            'amount': amount,
            'type': 'multiple'
        }

        if category:
            params['category'] = category
        if difficulty:
            params['difficulty'] = difficulty

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data['response_code'] == 0:
                return self._parse_questions(data['results'])
            else:
                raise Exception(f"API Error: Response code {data['response_code']}")

        except requests.RequestException as e:
            raise Exception(f"Network error: {e}")

    def _parse_questions(self, raw_questions: List[Dict]) -> List[Dict]:
        questions = []
        for q in raw_questions:
            parsed_q = {
                'question': html.unescape(q['question']),
                'correct_answer': html.unescape(q['correct_answer']),
                'incorrect_answers': [html.unescape(ans) for ans in q['incorrect_answers']],
                'category': html.unescape(q['category']),
                'difficulty': q['difficulty']
            }
            questions.append(parsed_q)
        return questions


class QuizEngine:

    def __init__(self):
        self.questions = []
        self.current_question = 0
        self.score = 0
        self.start_time = None
        self.question_times = []
        self.user_answers = []

    def load_questions(self, questions: List[Dict]):

        self.questions = questions
        self.current_question = 0
        self.score = 0
        self.start_time = time.time()
        self.question_times = []
        self.user_answers = []

    def get_current_question(self) -> Optional[Dict]:
        if self.current_question >= len(self.questions):
            return None

        question = self.questions[self.current_question].copy()

        # Shuffle answers
        all_answers = question['incorrect_answers'] + [question['correct_answer']]
        random.shuffle(all_answers)

        question['shuffled_answers'] = all_answers
        question['correct_index'] = all_answers.index(question['correct_answer'])

        return question

    def submit_answer(self, answer_index: int, time_taken: float = 0) -> bool:

        if self.current_question >= len(self.questions):
            return False

        question = self.get_current_question()
        is_correct = answer_index == question['correct_index']

        if is_correct:
            self.score += 1

        # Store answer details
        self.user_answers.append({
            'question': question['question'],
            'user_answer': question['shuffled_answers'][answer_index],
            'correct_answer': question['correct_answer'],
            'is_correct': is_correct,
            'time_taken': time_taken
        })

        self.question_times.append(time_taken)
        self.current_question += 1

        return is_correct

    def get_progress(self) -> Tuple[int, int]:
        return self.current_question, len(self.questions)

    def get_final_results(self) -> Dict:
        total_time = time.time() - self.start_time if self.start_time else 0
        avg_time = sum(self.question_times) / len(self.question_times) if self.question_times else 0

        return {
            'score': self.score,
            'total_questions': len(self.questions),
            'percentage': (self.score / len(self.questions)) * 100 if self.questions else 0,
            'total_time': total_time,
            'average_time_per_question': avg_time,
            'user_answers': self.user_answers
        }


class Utilities:

    @staticmethod
    def validate_number_input(prompt: str, min_val: int, max_val: int) -> int:
        while True:
            try:
                value = int(input(prompt))
                if min_val <= value <= max_val:
                    return value
                else:
                    print(f"Please enter a number between {min_val} and {max_val}")
            except ValueError:
                print("Please enter a valid number")

    @staticmethod
    def validate_choice_input(prompt: str, valid_choices: List[str]) -> str:
        while True:
            choice = input(prompt).strip().lower()
            if choice in valid_choices:
                return choice
            print(f"Please enter one of: {', '.join(valid_choices)}")

    @staticmethod
    def save_score(results: Dict, filename: str = "quiz_scores.json"):
        try:
            # Load existing scores
            try:
                with open(filename, 'r') as f:
                    scores = json.load(f)
            except FileNotFoundError:
                scores = []

            # Add new score
            score_entry = {
                'date': datetime.now().isoformat(),
                'score': results['score'],
                'total_questions': results['total_questions'],
                'percentage': results['percentage'],
                'total_time': results['total_time']
            }
            scores.append(score_entry)

            # Save updated scores
            with open(filename, 'w') as f:
                json.dump(scores, f, indent=2)

            print(f"Score saved to {filename}")

        except Exception as e:
            print(f"Error saving score: {e}")

    @staticmethod
    def display_high_scores(filename: str = "quiz_scores.json", top_n: int = 5):
        try:
            with open(filename, 'r') as f:
                scores = json.load(f)

            if not scores:
                print("No scores found.")
                return

            sorted_scores = sorted(scores, key=lambda x: (x['percentage'], -x['total_time']), reverse=True)

            print(f"\n=== TOP {top_n} SCORES ===")
            for i, score in enumerate(sorted_scores[:top_n], 1):
                date = datetime.fromisoformat(score['date']).strftime('%Y-%m-%d %H:%M')
                print(f"{i}. {score['percentage']:.1f}% ({score['score']}/{score['total_questions']}) - {date}")

        except FileNotFoundError:
            print("No scores file found.")
        except Exception as e:
            print(f"Error loading scores: {e}")


class CLIInterface:

    def __init__(self):
        self.api_handler = APIHandler()
        self.quiz_engine = QuizEngine()
        self.utils = Utilities()

    def run(self):
        """Main CLI game loop"""
        print("🎯 Welcome to the Python Quiz Game! 🎯")
        print("=" * 40)

        while True:
            print("\n📋 MAIN MENU")
            print("1. Start New Quiz")
            print("2. View High Scores")
            print("3. Exit")

            choice = input("\nEnter your choice (1-3): ").strip()

            if choice == '1':
                self._start_quiz()
            elif choice == '2':
                self.utils.display_high_scores()
            elif choice == '3':
                print("Thanks for playing! Goodbye! 👋")
                break
            else:
                print("Invalid choice. Please try again.")

    def _start_quiz(self):

        print("\n⚙️ Quiz Configuration")

        num_questions = self.utils.validate_number_input(
            "Number of questions (1-50): ", 1, 50
        )

        categories = self.api_handler.get_categories()
        if categories:
            print("\nAvailable categories:")
            print("0. Any Category")
            for cat_id, cat_name in categories.items():
                print(f"{cat_id}. {cat_name}")

            category_choice = self.utils.validate_number_input(
                "Choose category (0 for any): ", 0, max(categories.keys())
            )
            category = category_choice if category_choice != 0 else None
        else:
            category = None

        difficulty_choice = self.utils.validate_choice_input(
            "Choose difficulty (easy/medium/hard/any): ",
            ['easy', 'medium', 'hard', 'any']
        )
        difficulty = difficulty_choice if difficulty_choice != 'any' else None

        use_timer = self.utils.validate_choice_input(
            "Use timer per question? (y/n): ", ['y', 'n']
        ) == 'y'

        time_limit = 30
        if use_timer:
            time_limit = self.utils.validate_number_input(
                "Time limit per question (10-60 seconds): ", 10, 60
            )

    
        print("\n🔄 Fetching questions...")
        try:
            questions = self.api_handler.fetch_questions(
                amount=num_questions,
                category=category,
                difficulty=difficulty
            )

            if not questions:
                print("No questions found. Please try different settings.")
                return

            self.quiz_engine.load_questions(questions)
            self._play_quiz(use_timer, time_limit)

        except Exception as e:
            print(f"Error loading questions: {e}")

    def _play_quiz(self, use_timer: bool, time_limit: int):
        """Play the quiz"""
        print(f"\n🎮 Starting Quiz! ({len(self.quiz_engine.questions)} questions)")
        print("=" * 50)

        while True:
            question_data = self.quiz_engine.get_current_question()
            if not question_data:
                break

            current, total = self.quiz_engine.get_progress()
            print(f"\n📊 Question {current + 1}/{total}")
            print(f"Category: {question_data['category']}")
            print(f"Difficulty: {question_data['difficulty'].title()}")

            if use_timer:
                print(f"⏱️ Time limit: {time_limit} seconds")

            print(f"\n❓ {question_data['question']}")
            print()

            for i, answer in enumerate(question_data['shuffled_answers'], 1):
                print(f"{i}. {answer}")

            start_time = time.time()

            if use_timer:
                print(f"\nYou have {time_limit} seconds to answer...")
                user_input = input("Enter your choice (1-4): ").strip()
                elapsed = time.time() - start_time

                if elapsed > time_limit:
                    print("⏰ Time's up!")
                    answer_index = -1  
                else:
                    try:
                        answer_index = int(user_input) - 1
                    except ValueError:
                        answer_index = -1
            else:
                answer_index = self.utils.validate_number_input(
                    "Enter your choice (1-4): ", 1, 4
                ) - 1
                elapsed = time.time() - start_time

            if 0 <= answer_index < 4:
                is_correct = self.quiz_engine.submit_answer(answer_index, elapsed)
                if is_correct:
                    print("✅ Correct!")
                else:
                    print(f"❌ Wrong! The correct answer was: {question_data['correct_answer']}")
            else:
                print("❌ Invalid choice or timeout!")
                self.quiz_engine.submit_answer(-1, elapsed)

            # Show progress
            print(f"Current Score: {self.quiz_engine.score}/{current + 1}")

            if current + 1 < total:
                input("\nPress Enter to continue...")

        self._show_results()

    def _show_results(self):
        """Display final results"""
        results = self.quiz_engine.get_final_results()

        print("\n" + "=" * 50)
        print("🏆 QUIZ COMPLETED! 🏆")
        print("=" * 50)

        print(f"Final Score: {results['score']}/{results['total_questions']}")
        print(f"Percentage: {results['percentage']:.1f}%")
        print(f"Total Time: {results['total_time']:.1f} seconds")
        print(f"Average Time per Question: {results['average_time_per_question']:.1f} seconds")

    
        if results['percentage'] >= 80:
            print("🌟 Excellent! You're a quiz master!")
        elif results['percentage'] >= 60:
            print("👍 Good job! Keep it up!")
        else:
            print("📚 Keep studying! You'll do better next time!")

        show_details = self.utils.validate_choice_input(
            "\nShow detailed results? (y/n): ", ['y', 'n']
        ) == 'y'

        if show_details:
            print("\n📋 Detailed Results:")
            print("-" * 40)
            for i, answer in enumerate(results['user_answers'], 1):
                status = "✅" if answer['is_correct'] else "❌"
                print(f"{i}. {status} {answer['question']}")
                print(f"   Your answer: {answer['user_answer']}")
                if not answer['is_correct']:
                    print(f"   Correct answer: {answer['correct_answer']}")
                print(f"   Time taken: {answer['time_taken']:.1f}s")
                print()

        save_score = self.utils.validate_choice_input(
            "Save your score? (y/n): ", ['y', 'n']
        ) == 'y'

        if save_score:
            self.utils.save_score(results)


class GUIInterface:
    """GUI interface for the quiz game using tkinter"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Python Quiz Game")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        self.api_handler = APIHandler()
        self.quiz_engine = QuizEngine()
        self.utils = Utilities()
        
        self.current_question_data = None
        self.question_start_time = None
        self.selected_answer = tk.IntVar()
        
        self.setup_gui()
    
    def setup_gui(self):
        """Setup the GUI elements"""
        title_label = tk.Label(
            self.root,
            text="🎯 Python Quiz Game 🎯",
            font=("Arial", 24, "bold"),
            bg='#f0f0f0',
            fg='#333'
        )
        title_label.pack(pady=20)
        
        self.main_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        self.show_menu()
    
    def show_menu(self):
        """Show main menu"""
        self.clear_frame()
        
        menu_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
        menu_frame.pack(expand=True)
        
        tk.Button(
            menu_frame,
            text="Start New Quiz",
            font=("Arial", 14),
            bg='#4CAF50',
            fg='white',
            padx=20,
            pady=10,
            command=self.show_quiz_config
        ).pack(pady=10)
        
        tk.Button(
            menu_frame,
            text="View High Scores",
            font=("Arial", 14),
            bg='#2196F3',
            fg='white',
            padx=20,
            pady=10,
            command=self.show_high_scores
        ).pack(pady=10)
        
        tk.Button(
            menu_frame,
            text="Exit",
            font=("Arial", 14),
            bg='#f44336',
            fg='white',
            padx=20,
            pady=10,
            command=self.root.quit
        ).pack(pady=10)
    
    def show_quiz_config(self):
        """Show quiz configuration"""
        self.clear_frame()
        
        config_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
        config_frame.pack(expand=True)
        
        tk.Label(
            config_frame,
            text="Quiz Configuration",
            font=("Arial", 18, "bold"),
            bg='#f0f0f0'
        ).pack(pady=20)
        

        tk.Label(config_frame, text="Number of questions:", bg='#f0f0f0').pack()
        self.num_questions_var = tk.StringVar(value="10")
        tk.Spinbox(
            config_frame,
            from_=1,
            to=50,
            textvariable=self.num_questions_var,
            width=10
        ).pack(pady=5)
        
        tk.Label(config_frame, text="Category:", bg='#f0f0f0').pack(pady=(20, 5))
        self.category_var = tk.StringVar(value="Any Category")
        self.category_combo = ttk.Combobox(
            config_frame,
            textvariable=self.category_var,
            state="readonly",
            width=30
        )
        self.category_combo.pack(pady=5)
        
        threading.Thread(target=self.load_categories, daemon=True).start()
        
        tk.Label(config_frame, text="Difficulty:", bg='#f0f0f0').pack(pady=(20, 5))
        self.difficulty_var = tk.StringVar(value="Any")
        difficulty_combo = ttk.Combobox(
            config_frame,
            textvariable=self.difficulty_var,
            values=["Any", "Easy", "Medium", "Hard"],
            state="readonly",
            width=20
        )
        difficulty_combo.pack(pady=5)
        
    
        self.timer_var = tk.BooleanVar()
        tk.Checkbutton(
            config_frame,
            text="Use timer per question",
            variable=self.timer_var,
            bg='#f0f0f0'
        ).pack(pady=20)
        
        tk.Button(
            config_frame,
            text="Start Quiz",
            font=("Arial", 14),
            bg='#4CAF50',
            fg='white',
            padx=20,
            pady=10,
            command=self.start_quiz
        ).pack(pady=20)
        
     
        tk.Button(
            config_frame,
            text="Back to Menu",
            font=("Arial", 12),
            bg='#757575',
            fg='white',
            padx=15,
            pady=5,
            command=self.show_menu
        ).pack()
    
    def load_categories(self):
        """Load categories from API"""
        try:
            categories = self.api_handler.get_categories()
            category_list = ["Any Category"] + list(categories.values())
            self.category_combo['values'] = category_list
            self.category_combo.set("Any Category")
        except:
            pass
    
    def start_quiz(self):
        """Start the quiz"""
        try:
            num_questions = int(self.num_questions_var.get())
            category_name = self.category_var.get()
            difficulty = self.difficulty_var.get().lower() if self.difficulty_var.get() != "Any" else None
            
            # Get category ID
            category_id = None
            if category_name != "Any Category":
                categories = self.api_handler.get_categories()
                for cat_id, cat_name in categories.items():
                    if cat_name == category_name:
                        category_id = cat_id
                        break
            
           
            self.show_loading()
            
            
            threading.Thread(
                target=self.fetch_and_start_quiz,
                args=(num_questions, category_id, difficulty),
                daemon=True
            ).start()
            
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number of questions")
    
    def fetch_and_start_quiz(self, num_questions, category_id, difficulty):
        """Fetch questions and start quiz"""
        try:
            questions = self.api_handler.fetch_questions(
                amount=num_questions,
                category=category_id,
                difficulty=difficulty
            )
            
            if not questions:
                self.root.after(0, lambda: messagebox.showerror("Error", "No questions found"))
                self.root.after(0, self.show_quiz_config)
                return
            
            self.quiz_engine.load_questions(questions)
            self.root.after(0, self.show_question)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to load questions: {e}"))
            self.root.after(0, self.show_quiz_config)
    
    def show_loading(self):
        """Show loading screen"""
        self.clear_frame()
        
        loading_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
        loading_frame.pack(expand=True)
        
        tk.Label(
            loading_frame,
            text="Loading questions...",
            font=("Arial", 16),
            bg='#f0f0f0'
        ).pack(pady=50)
    
    def show_question(self):
        """Show current question"""
        self.current_question_data = self.quiz_engine.get_current_question()
        
        if not self.current_question_data:
            self.show_results()
            return
        
        self.clear_frame()
        self.question_start_time = time.time()
        
        question_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
        question_frame.pack(fill='both', expand=True)
        
        current, total = self.quiz_engine.get_progress()
        
        
        info_frame = tk.Frame(question_frame, bg='#f0f0f0')
        info_frame.pack(fill='x', pady=10)
        
        tk.Label(
            info_frame,
            text=f"Question {current + 1}/{total}",
            font=("Arial", 12, "bold"),
            bg='#f0f0f0'
        ).pack()
        
        tk.Label(
            info_frame,
            text=f"Category: {self.current_question_data['category']}",
            font=("Arial", 10),
            bg='#f0f0f0'
        ).pack()
        
        tk.Label(
            info_frame,
            text=f"Difficulty: {self.current_question_data['difficulty'].title()}",
            font=("Arial", 10),
            bg='#f0f0f0'
        ).pack()
        
        
        question_label = tk.Label(
            question_frame,
            text=self.current_question_data['question'],
            font=("Arial", 14),
            bg='#f0f0f0',
            wraplength=600,
            justify='center'
        )
        question_label.pack(pady=20)
        
    
        self.selected_answer.set(-1)
        
        answers_frame = tk.Frame(question_frame, bg='#f0f0f0')
        answers_frame.pack(pady=20)
        
        for i, answer in enumerate(self.current_question_data['shuffled_answers']):
            tk.Radiobutton(
                answers_frame,
                text=answer,
                variable=self.selected_answer,
                value=i,
                font=("Arial", 12),
                bg='#f0f0f0',
                wraplength=500,
                justify='left'
            ).pack(anchor='w', pady=5)
        
    
        tk.Button(
            question_frame,
            text="Submit Answer",
            font=("Arial", 14),
            bg='#4CAF50',
            fg='white',
            padx=20,
            pady=10,
            command=self.submit_answer
        ).pack(pady=20)
        
        
        tk.Label(
            question_frame,
            text=f"Current Score: {self.quiz_engine.score}/{current}",
            font=("Arial", 12),
            bg='#f0f0f0'
        ).pack()
    
    def submit_answer(self):
        """Submit the selected answer"""
        if self.selected_answer.get() == -1:
            messagebox.showwarning("Warning", "Please select an answer")
            return
        
        elapsed_time = time.time() - self.question_start_time
        is_correct = self.quiz_engine.submit_answer(self.selected_answer.get(), elapsed_time)
        
        
        result_text = "Correct!" if is_correct else f"Wrong! The correct answer was: {self.current_question_data['correct_answer']}"
        messagebox.showinfo("Result", result_text)
        
        self.show_question()
    
    def show_results(self):
        """Show final results"""
        results = self.quiz_engine.get_final_results()
        
        self.clear_frame()
        
        results_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
        results_frame.pack(expand=True)
        
        tk.Label(
            results_frame,
            text="🏆 Quiz Completed! 🏆",
            font=("Arial", 20, "bold"),
            bg='#f0f0f0'
        ).pack(pady=20)
        
        tk.Label(
            results_frame,
            text=f"Final Score: {results['score']}/{results['total_questions']}",
            font=("Arial", 16),
            bg='#f0f0f0'
        ).pack(pady=5)
        
        tk.Label(
            results_frame,
            text=f"Percentage: {results['percentage']:.1f}%",
            font=("Arial", 16),
            bg='#f0f0f0'
        ).pack(pady=5)
        
        tk.Label(
            results_frame,
            text=f"Total Time: {results['total_time']:.1f} seconds",
            font=("Arial", 12),
            bg='#f0f0f0'
        ).pack(pady=5)
        
    
        if results['percentage'] >= 80:
            message = "🌟 Excellent! You're a quiz master!"
        elif results['percentage'] >= 60:
            message = "👍 Good job! Keep it up!"
        else:
            message = "📚 Keep studying! You'll do better next time!"
        
        tk.Label(
            results_frame,
            text=message,
            font=("Arial", 14),
            bg='#f0f0f0',
            fg='#4CAF50'
        ).pack(pady=20)
        
        
        button_frame = tk.Frame(results_frame, bg='#f0f0f0')
        button_frame.pack(pady=20)
        
        tk.Button(
            button_frame,
            text="Save Score",
            font=("Arial", 12),
            bg='#2196F3',
            fg='white',
            padx=15,
            pady=5,
            command=lambda: self.utils.save_score(results)
        ).pack(side='left', padx=10)

        tk.Button(
            button_frame,
            text="Play Again",
            font=("Arial", 12),
            bg='#4CAF50',
            fg='white',
            padx=15,
            pady=5,
            command=self.show_quiz_config
        ).pack(side='left', padx=10)
        
        tk.Button(
            button_frame,
            text="Main Menu",
            font=("Arial", 12),
            bg='#757575',
            fg='white',
            padx=15,
            pady=5,
            command=self.show_menu
        ).pack(side='left', padx=10)
    
    def clear_frame(self):
        """Clear all widgets from main frame"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def show_high_scores(self):
        """Show high scores screen"""
        self.clear_frame()
        
        scores_frame = tk.Frame(self.main_frame, bg='#f0f0f0')
        scores_frame.pack(expand=True)
        
        tk.Label(
            scores_frame,
            text="🏆 High Scores 🏆",
            font=("Arial", 20, "bold"),
            bg='#f0f0f0'
        ).pack(pady=20)
        
        
        try:
            with open("quiz_scores.json", 'r') as f:
                scores = json.load(f)
            
            if not scores:
                tk.Label(
                    scores_frame,
                    text="No scores yet!",
                    font=("Arial", 14),
                    bg='#f0f0f0'
                ).pack(pady=20)
            else:
                sorted_scores = sorted(
                    scores,
                    key=lambda x: (x['percentage'], -x['total_time']),
                    reverse=True
                )
                
                for i, score in enumerate(sorted_scores[:5], 1):
                    date = datetime.fromisoformat(score['date']).strftime('%Y-%m-%d %H:%M')
                    score_text = f"{i}. {score['percentage']:.1f}% ({score['score']}/{score['total_questions']}) - {date}"
                    tk.Label(
                        scores_frame,
                        text=score_text,
                        font=("Arial", 12),
                        bg='#f0f0f0'
                    ).pack(pady=5)
        
        except FileNotFoundError:
            tk.Label(
                scores_frame,
                text="No scores file found",
                font=("Arial", 14),
                bg='#f0f0f0'
            ).pack(pady=20)
        
        
        tk.Button(
            scores_frame,
            text="Back to Menu",
            font=("Arial", 12),
            bg='#757575',
            fg='white',
            padx=15,
            pady=5,
            command=self.show_menu
        ).pack(pady=20)


if __name__ == "__main__":
    try:
        gui = GUIInterface()
        gui.root.mainloop()
    except Exception as e:
        print(f"Error running quiz game: {e}")