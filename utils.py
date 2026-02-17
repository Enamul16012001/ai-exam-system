"""
Utility classes and functions for the AI-based Exam System
"""

import secrets
import json
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pydantic import BaseModel

from gemini_analyzer import GeminiAnalyzer


# --- Constants ---

BANGLADESH_TZ = pytz.timezone('Asia/Dhaka')

PERFORMANCE_THRESHOLDS = {
    'excellent': 85,
    'good': 70,
    'average': 50,
}


# --- Data Models ---

class ExamSession(BaseModel):
    session_id: str
    candidate_name: str
    candidate_id: str
    exam_id: str
    started_at: datetime
    time_limit: int  # in minutes


class AdminSession(BaseModel):
    session_id: str
    created_at: datetime
    expires_at: datetime


# --- Exam Evaluation ---

class ExamEvaluator:
    """Handles exam evaluation using AI for subjective questions and auto-grading for MCQs"""

    def __init__(self, api_key: str, backup_api_key: str = None):
        self.analyzer = GeminiAnalyzer(api_key, backup_api_key)

    def generate_exam_questions_by_sections(self, department: str, position: str,
                                            sections_structure: Dict,
                                            exam_language: str = 'english',
                                            difficulty_level: str = 'medium',
                                            custom_instructions: str = '',
                                            mcq_options_count: int = 4) -> Dict:
        """Generate exam questions organized by sections"""
        return self.analyzer.generate_questions_by_sections(
            department, position, sections_structure, exam_language,
            difficulty_level=difficulty_level,
            custom_instructions=custom_instructions,
            mcq_options_count=mcq_options_count
        )

    def regenerate_section_questions(self, department: str, position: str,
                                     section_type: str, section_config: Dict,
                                     exam_language: str = 'english',
                                     difficulty_level: str = 'medium',
                                     custom_instructions: str = '') -> Dict:
        """Regenerate questions for a single section"""
        return self.analyzer.generate_single_section(
            department, position, section_type, section_config, exam_language,
            difficulty_level=difficulty_level,
            custom_instructions=custom_instructions
        )

    def evaluate_exam(self, questions: List[Dict], candidate_answers: Dict,
                      negative_marking_config: Dict = None,
                      multi_select_scoring_mode: str = 'partial') -> Dict:
        """Evaluate candidate answers and return detailed results"""
        total_marks = 0
        obtained_marks = 0
        negative_marks = 0
        question_results = []

        for question in questions:
            question_id = str(question['id'])
            candidate_answer = candidate_answers.get(question_id, "")
            section_type = question.get('section_type', 'technical')

            if question['type'] == 'mcq':
                result = evaluate_mcq_answer(question, candidate_answer,
                                             negative_marking_config, section_type,
                                             multi_select_scoring_mode)
                negative_marks += result.get('negative_marks_applied', 0)
            else:
                result = self._evaluate_subjective(question, candidate_answer)

            total_marks += question['marks']
            obtained_marks += result['marks_obtained']
            question_results.append(result)

        final_score = obtained_marks - negative_marks
        percentage = (final_score / total_marks) * 100 if total_marks > 0 else 0

        return {
            'total_marks': total_marks,
            'obtained_marks': final_score,
            'negative_marks': negative_marks,
            'percentage': percentage,
            'question_results': question_results,
            'overall_feedback': _generate_overall_feedback(percentage, question_results, negative_marks),
            'performance_level': get_performance_level(percentage)
        }

    def _evaluate_subjective(self, question: Dict, candidate_answer: str) -> Dict:
        """Evaluate short/essay answer using AI"""
        if not candidate_answer.strip():
            return {
                'question_id': question['id'],
                'question_type': question['type'],
                'question_text': question['question'],
                'candidate_answer': candidate_answer,
                'marks_total': question['marks'],
                'marks_obtained': 0,
                'negative_marks_applied': 0,
                'feedback': 'No answer provided.',
                'evaluation_details': 'Answer was not provided by the candidate.',
                'ai_evaluated': True,
                'needs_manual_review': False
            }

        try:
            evaluation = self.analyzer.evaluate_subjective_answer(question, candidate_answer)
            return {
                'question_id': question['id'],
                'question_type': question['type'],
                'question_text': question['question'],
                'candidate_answer': candidate_answer,
                'marks_total': question['marks'],
                'marks_obtained': evaluation['marks_awarded'],
                'negative_marks_applied': 0,
                'feedback': evaluation.get('feedback', 'Evaluation completed'),
                'strengths': evaluation.get('strengths', ''),
                'improvements': evaluation.get('improvements', ''),
                'evaluation_details': f"AI Evaluation: {evaluation.get('feedback', '')}",
                'ai_evaluated': evaluation.get('ai_evaluated', True),
                'needs_manual_review': evaluation.get('needs_manual_review', False)
            }

        except Exception as e:
            print(f"Error evaluating subjective answer: {str(e)}")
            return {
                'question_id': question['id'],
                'question_type': question['type'],
                'question_text': question['question'],
                'candidate_answer': candidate_answer,
                'marks_total': question['marks'],
                'marks_obtained': 0,
                'negative_marks_applied': 0,
                'feedback': 'AI evaluation failed. This answer needs manual review by admin.',
                'evaluation_details': 'Automatic evaluation failed.',
                'ai_evaluated': False,
                'needs_manual_review': True
            }


# --- MCQ Evaluation ---

def evaluate_mcq_answer(question: Dict, candidate_answer,
                        negative_marking_config: Dict = None,
                        section_type: str = 'technical',
                        multi_select_scoring_mode: str = 'partial') -> Dict:
    """
    Evaluate a single MCQ answer with negative marking support.
    Supports both single-select and multi-select MCQs.
    """
    is_multi_select = question.get('is_multi_select', False)

    if is_multi_select:
        return _evaluate_multi_select_mcq(question, candidate_answer,
                                          negative_marking_config, section_type,
                                          multi_select_scoring_mode)
    else:
        return _evaluate_single_select_mcq(question, candidate_answer,
                                           negative_marking_config, section_type)


def _evaluate_multi_select_mcq(question: Dict, candidate_answer,
                                negative_marking_config: Dict,
                                section_type: str,
                                multi_select_scoring_mode: str) -> Dict:
    """Evaluate a multi-select MCQ answer"""
    correct_answers = question.get('correct_answers', [])
    if isinstance(correct_answers, str):
        try:
            correct_answers = json.loads(correct_answers)
        except (json.JSONDecodeError, ValueError):
            correct_answers = []

    # Parse candidate selections
    candidate_selections = _parse_candidate_selections(candidate_answer)
    correct_set = set(correct_answers)

    marks_obtained = 0
    negative_marks_applied = 0
    is_correct = False

    if candidate_selections:
        if candidate_selections == correct_set:
            is_correct = True
            marks_obtained = question['marks']
        else:
            correct_selected = len(candidate_selections & correct_set)
            incorrect_selected = len(candidate_selections - correct_set)

            if multi_select_scoring_mode == 'strict':
                marks_obtained = 0
            else:
                # Partial scoring
                if correct_selected > incorrect_selected:
                    partial_ratio = (correct_selected - incorrect_selected) / len(correct_set)
                    marks_obtained = round(max(0, question['marks'] * partial_ratio), 2)

            negative_marks_applied = _calculate_negative_marks(
                negative_marking_config, section_type, incorrect_selected
            )
    else:
        negative_marks_applied = _calculate_unanswered_penalty(
            negative_marking_config, section_type
        )

    # Format display text
    options = question.get('options', [])
    selected_option_text = _format_selected_options(candidate_selections, options)
    correct_answers_text = _format_selected_options(correct_set, options)

    return {
        'question_id': question['id'],
        'question_type': 'mcq',
        'is_multi_select': True,
        'question_text': question['question'],
        'candidate_answer': list(candidate_selections) if candidate_selections else [],
        'correct_answer': correct_answers,
        'correct_answer_text': correct_answers_text,
        'is_correct': is_correct,
        'marks_total': question['marks'],
        'marks_obtained': marks_obtained,
        'negative_marks_applied': negative_marks_applied,
        'feedback': question.get('explanation', 'No explanation provided'),
        'selected_option': selected_option_text
    }


def _evaluate_single_select_mcq(question: Dict, candidate_answer,
                                  negative_marking_config: Dict,
                                  section_type: str) -> Dict:
    """Evaluate a single-select MCQ answer"""
    is_correct = False
    marks_obtained = 0
    negative_marks_applied = 0

    if candidate_answer and str(candidate_answer).isdigit():
        selected_option = int(candidate_answer)
        is_correct = selected_option == question['correct_answer']
        if is_correct:
            marks_obtained = question['marks']
        else:
            negative_marks_applied = _calculate_negative_marks(
                negative_marking_config, section_type, 1
            )
    else:
        negative_marks_applied = _calculate_unanswered_penalty(
            negative_marking_config, section_type
        )

    # Format display text
    options = question.get('options', [])
    selected_option_text = 'No answer'
    if candidate_answer and str(candidate_answer).isdigit():
        idx = int(candidate_answer)
        if 0 <= idx < len(options):
            selected_option_text = options[idx]

    return {
        'question_id': question['id'],
        'question_type': 'mcq',
        'is_multi_select': False,
        'question_text': question['question'],
        'candidate_answer': candidate_answer,
        'correct_answer': question['correct_answer'],
        'is_correct': is_correct,
        'marks_total': question['marks'],
        'marks_obtained': marks_obtained,
        'negative_marks_applied': negative_marks_applied,
        'feedback': question.get('explanation', 'No explanation provided'),
        'selected_option': selected_option_text
    }


# --- MCQ Helper Functions ---

def _parse_candidate_selections(candidate_answer) -> set:
    """Parse candidate answer into a set of selected indices"""
    if not candidate_answer:
        return set()
    if isinstance(candidate_answer, list):
        return set(int(a) for a in candidate_answer if str(a).isdigit())
    if isinstance(candidate_answer, str):
        if ',' in candidate_answer:
            return set(int(a.strip()) for a in candidate_answer.split(',') if a.strip().isdigit())
        if candidate_answer.isdigit():
            return {int(candidate_answer)}
    return set()


def _calculate_negative_marks(negative_marking_config: Dict, section_type: str,
                               incorrect_count: int) -> float:
    """Calculate negative marks for incorrect answers"""
    if not negative_marking_config or section_type not in negative_marking_config:
        return 0
    section_config = negative_marking_config[section_type]
    if section_config.get('enabled', False):
        return section_config.get('mcq_negative_marks', 0) * incorrect_count
    return 0


def _calculate_unanswered_penalty(negative_marking_config: Dict, section_type: str) -> float:
    """Calculate negative marks for unanswered questions"""
    if not negative_marking_config or section_type not in negative_marking_config:
        return 0
    section_config = negative_marking_config[section_type]
    if section_config.get('enabled', False) and section_config.get('apply_to_unanswered', False):
        return section_config.get('mcq_negative_marks', 0)
    return 0


def _format_selected_options(indices: set, options: list) -> str:
    """Format selected option indices as readable text"""
    if not indices:
        return 'No answer'
    texts = []
    for idx in sorted(indices):
        if 0 <= idx < len(options):
            texts.append(f"{chr(65 + idx)}) {options[idx]}")
    return '; '.join(texts) if texts else 'No answer'


# --- Feedback & Performance ---

def get_performance_level(percentage: float) -> str:
    """Get performance level based on percentage"""
    if percentage >= PERFORMANCE_THRESHOLDS['excellent']:
        return "Excellent"
    elif percentage >= PERFORMANCE_THRESHOLDS['good']:
        return "Good"
    elif percentage >= PERFORMANCE_THRESHOLDS['average']:
        return "Average"
    else:
        return "Poor"


def _generate_overall_feedback(percentage: float, question_results: List[Dict],
                                negative_marks: float = 0) -> str:
    """Generate overall feedback for the candidate"""
    if percentage >= 85:
        feedback = "Excellent performance! You have demonstrated strong knowledge and understanding."
    elif percentage >= 70:
        feedback = "Good performance overall. You have shown solid understanding with room for improvement."
    elif percentage >= 50:
        feedback = "Average performance. You have basic understanding but need to strengthen your knowledge."
    else:
        feedback = "Below average performance. Significant improvement needed in your preparation."

    mcq_correct = len([r for r in question_results if r['question_type'] == 'mcq' and r.get('is_correct', False)])
    mcq_total = len([r for r in question_results if r['question_type'] == 'mcq'])

    if mcq_total > 0 and (mcq_correct / mcq_total) * 100 < 60:
        feedback += " Focus on improving your theoretical knowledge for multiple choice questions."

    if negative_marks > 0:
        feedback += (f" Note: {negative_marks} marks were deducted due to incorrect answers "
                     "in sections with negative marking.")

    return feedback


# --- Session Management ---

def create_admin_session(timeout_minutes: int = 30) -> str:
    """Create a new admin session and return its ID"""
    return secrets.token_urlsafe(32)


def verify_admin_session(session_id: str, admin_sessions: Dict,
                         timeout_minutes: int = 30, lock=None) -> bool:
    """Verify if admin session is valid and not expired"""
    def _verify():
        if session_id not in admin_sessions:
            return False
        session = admin_sessions[session_id]
        if datetime.now() > session.expires_at:
            del admin_sessions[session_id]
            return False
        session.expires_at = datetime.now() + timedelta(minutes=timeout_minutes)
        return True

    if lock:
        with lock:
            return _verify()
    return _verify()


# --- Time & Formatting Utilities ---

def convert_utc_to_bangladesh(utc_time_str: str) -> Optional[str]:
    """Convert UTC time string to Bangladesh time"""
    if not utc_time_str or utc_time_str == 'None':
        return None
    try:
        utc_time = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
        utc_time = pytz.utc.localize(utc_time)
        bd_time = utc_time.astimezone(BANGLADESH_TZ)
        return bd_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error converting time: {e}")
        return utc_time_str


def order_questions_by_type(questions: List[Dict]) -> List[Dict]:
    """Order questions by type: MCQ first, then Short, then Essay"""
    mcq = [q for q in questions if q.get('type') == 'mcq']
    short = [q for q in questions if q.get('type') == 'short']
    essay = [q for q in questions if q.get('type') == 'essay']
    return mcq + short + essay


def group_questions_by_section_for_navigation(questions: List[Dict]) -> Dict[str, List[Dict]]:
    """Group questions by section type for navigation"""
    sections = {}
    for question in questions:
        section_type = question.get('section_type', 'technical')
        if section_type not in sections:
            sections[section_type] = []
        sections[section_type].append(question)
    return sections


# --- Form Validation ---

def validate_form_data(form_data: Dict) -> tuple[bool, str]:
    """Validate exam creation form data"""
    for field in ['department', 'position', 'title']:
        if not form_data.get(field, '').strip():
            return False, f"Please fill in the required field: {field.title()}"
    try:
        time_limit = int(form_data.get('time_limit', 120))
        if time_limit <= 0:
            return False, "Time limit must be greater than 0"
    except (ValueError, TypeError):
        return False, "Invalid time limit format"
    return True, ""


def generate_safe_filename(candidate_name: str, result_id: str,
                           extension: str = 'html') -> str:
    """Generate a safe filename for downloads"""
    safe_name = "".join(c for c in candidate_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    return f"exam_result_{safe_name}_{result_id[:8]}.{extension}"
