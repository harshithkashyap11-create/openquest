"""Transparent classification accounting; CLI refuses unadjudicated labels."""
import argparse
from collections import Counter
import json
from pathlib import Path
from app.subject_taxonomy import all_misconception_codes


def metrics(rows):
    labels=sorted({r['expected'] for r in rows})
    valid=all_misconception_codes()
    abstain={'M06','FOLLOW_UP'}
    matrix={label:dict(Counter(r['predicted'] for r in rows if r['expected']==label)) for label in labels}
    per_label={}
    for label in labels:
        tp=sum(r['expected']==label and r['predicted']==label for r in rows)
        fp=sum(r['expected']!=label and r['predicted']==label for r in rows)
        fn=sum(r['expected']==label and r['predicted']!=label for r in rows)
        precision=tp/(tp+fp) if tp+fp else 0
        recall=tp/(tp+fn) if tp+fn else 0
        per_label[label]={'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0,'support':tp+fn}
    count=len(rows)
    return {'sample_count':count,'subject_counts':dict(sorted(Counter(r['subject'] for r in rows).items())),
        'label_order':labels,'per_label':per_label,'macro_f1':sum(x['f1'] for x in per_label.values())/len(labels) if labels else None,
        'abstention_rate':sum(r['predicted'] in abstain for r in rows)/count if count else None,
        'unsupported_output_rate':sum(r['predicted'] not in valid for r in rows)/count if count else None,
        'confusion_matrix':matrix,'method':'Exact label precision/recall/F1; zero division=0; abstentions and unsupported labels retain false negatives.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path,help='JSON list of subject, expected, predicted, review_status, reviewer fields')
    parser.add_argument('--allow-synthetic-regression',action='store_true')
    args=parser.parse_args();rows=json.loads(args.input.read_text())
    independent=bool(rows) and all(r.get('review_status')=='adjudicated' and r.get('reviewer') for r in rows)
    if not independent and not args.allow_synthetic_regression:
        parser.error('Independent evaluation NOT TESTED: all reference labels require documented human adjudication')
    print(json.dumps({'evaluation_kind':'human-adjudicated references (provenance must be audited)' if independent else 'synthetic regression only; NOT independent accuracy',**metrics(rows)},indent=2))

if __name__=='__main__':main()
