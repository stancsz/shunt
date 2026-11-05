"""Shared coding classifier and deterministic policy boundary."""
from shunt.policy import route

SCOPE_FIELDS = {'file_count', 'ast_lines', 'attempt_count', 'core_interface'}


def validate(task, scope):
    if not isinstance(scope, dict) or set(scope) - SCOPE_FIELDS:
        raise ValueError('scope accepts file_count, ast_lines, attempt_count, core_interface only')
    args = dict(file_count=scope.get('file_count'), ast_lines=scope.get('ast_lines'),
                attempt_count=scope.get('attempt_count', 0), core_interface=scope.get('core_interface', False))
    route(task, [1.0, 0.0, 0.0], **args)
    return args


def evaluate(task, scope, scorer, settings):
    args = validate(task, scope)
    result = route(task, scorer(task), **args)
    result['target'] = settings.targets[result['route']].public()
    result['calibrated'] = False
    return result
