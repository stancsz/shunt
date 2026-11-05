"""A deliberately narrow System One-shaped adapter for Shunt's fixed classifier."""

from shunt.decision import evaluate

MODEL = 'shunt'
INSTRUCTIONS = 'Classify the coding task by complexity.'
CRITERIA = {
    'T1': 'Small local syntax, formatting, documentation, rename, boilerplate or simple unit test.',
    'T2': 'Standard feature, CRUD, integration test, module refactor or translation of existing patterns.',
    'T3': 'Deep root-cause diagnosis, concurrency, memory corruption, security design or architecture.',
}


def decide(body, scorer, settings):
    if set(body) - {'model', 'state', 'questions', 'shunt'}:
        raise ValueError('unsupported request field')
    if body.get('model') != MODEL:
        raise ValueError('model must be shunt')
    task = body.get('state')
    questions = body.get('questions')
    if not isinstance(questions, dict) or len(questions) != 1:
        raise ValueError('exactly one coding complexity question is supported')
    question_id, question = next(iter(questions.items()))
    if not isinstance(question_id, str) or not question_id:
        raise ValueError('question id must be a nonempty string')
    if question != {'type': 'choice', 'instructions': INSTRUCTIONS, 'criteria': CRITERIA}:
        raise ValueError('only the documented fixed coding complexity choice is supported')
    metadata = body.get('shunt', {})
    if not isinstance(metadata, dict) or set(metadata) - {'file_count', 'ast_lines', 'attempt_count', 'core_interface'}:
        raise ValueError('invalid shunt metadata')
    result = evaluate(task, metadata, scorer, settings)
    probabilities = result['probabilities']
    choice = max(probabilities, key=probabilities.get)
    return {'model': MODEL, 'answers': {question_id: {'type': 'choice', 'choice': choice,
            'probabilities': probabilities}}, 'shunt': result}
