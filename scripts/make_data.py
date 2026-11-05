"""Small authored policy corpus; held-out intents use separate templates."""
import json
from pathlib import Path

TRAIN = [
['Fix a missing closing parenthesis in {x}.','Normalize whitespace in {x}.','Add a docstring explaining {x}.','Rename a local variable in {x}.','Remove an unused import from {x}.','Write a simple test for a pure getter in {x}.','Correct a misspelled comment in {x}.','Extract a repeated literal into a local constant in {x}.','Add type annotations to a trivial helper in {x}.','Generate a dataclass for a plain record in {x}.','Fix indentation in {x}.','Apply lint formatting to {x}.'],
['Implement paginated CRUD endpoints for {x}.','Add repository and service layers for {x}.','Refactor {x} into cohesive modules preserving behavior.','Write integration tests using the API documentation for {x}.','Translate the existing {x} feature from JavaScript to Python.','Add form validation and persistence for {x}.','Connect the frontend view to the backend endpoint for {x}.','Extend the existing search feature with filters for {x}.','Implement an adapter following existing patterns for {x}.','Move {x} helpers into a shared module and update callers.','Add CSV import and export workflows for {x}.','Implement cache invalidation for the standard {x} CRUD flow.'],
['Find the root cause of nondeterministic failures in {x}.','Diagnose a race condition affecting {x}.','Design a distributed consensus protocol for {x}.','Investigate memory corruption in {x}.','Analyze a deadlock in {x}.','Design authentication boundaries for {x}.','Resolve a circular dependency involving {x}.','Investigate state corruption after recovery in {x}.','Identify why {x} leaks memory under sustained load.','Design cryptographic key rotation for {x}.','Explain an intermittent production crash in {x}.','Determine why {x} tests fail only under parallel execution.']]
HELD = [
['Replace a tab with spaces in {x}.','Document the return value of a small function in {x}.','Change a local identifier from tmp to result in {x}.','Add a basic assertion for a string utility in {x}.','Delete a duplicate semicolon in {x}.','Add a small enum declaration for {x}.'],
['Build the controller, database access and client page for {x}.','Port the current {x} implementation to the new SDK using its guide.','Split the {x} package into modules and fix importing callers.','Test the {x} HTTP endpoint against its real database fixture.','Add sorting across the UI and service layer for {x}.','Implement a standard webhook receiver for {x} following the existing design.'],
['Determine why acknowledgements disappear during a failover in {x}.','Find how an interleaving of two writers corrupts {x}.','Propose trust boundaries for an untrusted plugin in {x}.','Investigate an unexplained growth in resident memory for {x}.','Design recovery guarantees for replicated {x} state.','Trace the source of flaky assertions after process restart in {x}.']]


def main():
    out=Path('data'); out.mkdir(exist_ok=True)
    for split, templates, subjects in [
        ('train',TRAIN,['inventory','reports','catalog','profiles','notifications','bookmarks']),
        ('validation',HELD,['invoices','reservations']),
    ]:
        rows=[{'task':t.format(x=s), 'label':tier, 'family':f'{split}-{tier}-{i}',
               'source':'authored synthetic policy supervision'}
              for tier,ts in enumerate(templates) for i,t in enumerate(ts) for s in subjects]
        (out/f'{split}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
        print(split,len(rows))


if __name__=='__main__': main()
