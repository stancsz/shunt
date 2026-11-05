"""Execute independently reviewed current-policy fixtures without model calls."""
import json
from pathlib import Path
from shunt.policy import route


def evaluate(case_id, inputs, expected):
    result=route(inputs['task'],inputs['probabilities'],inputs['file_count'],
                 inputs['ast_lines'],inputs['attempt_count'],inputs['core_interface'])
    assert result['route']==expected['route'], (case_id,'route',result['route'],expected['route'])
    for key in ('lexical_risk','ambiguity_bump','circuit_breaker','blast_radius',
                'core_interface','unknown_scope','structural_floor'):
        assert result['overrides'][key]==expected[key], (case_id,key)


def main():
    paths=[Path('data/candidates/operational-six-reviewed.jsonl'),
           Path('data/candidates/operational-three-reviewed.jsonl')]
    rows=[json.loads(line) for path in paths for line in path.read_text(encoding='utf-8').splitlines()]
    assert len(rows)==9 and len({r['id'] for r in rows})==9
    checks=0
    for row in rows:
        if row.get('expected_error'):
            assert row['expected_error']=='ValueError'
            try:
                route(**row['input'])
            except ValueError:
                pass
            else:
                raise AssertionError((row['id'],'expected ValueError'))
        else:
            evaluate(row['id'],row['input'],row['policy_expected'])
        checks+=1
        for counterfactual in row.get('counterfactuals',[]):
            evaluate(row['id']+':'+counterfactual['name'],counterfactual['input'],
                     counterfactual['current_policy_expected']); checks+=1
    print(f'{len(rows)} reviewed cases, {checks} current-policy inputs passed; proposed semantic outcomes not executed')


if __name__=='__main__': main()
