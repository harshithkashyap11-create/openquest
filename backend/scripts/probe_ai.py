"""Opt-in bounded provider smoke test. Uses only embedded synthetic examples."""
import argparse
import json
from pathlib import Path
from time import perf_counter
import httpx
from app.core.config import get_settings
from app.services.diagnosis_provider import create_diagnosis_provider
from app.schemas.diagnosis import validate_evidence_quotes
from app.subject_taxonomy import get_taxonomy

EXAMPLES = [
 {'subject':'Mathematics','topic':'Fractions','question':'Add 1/2 + 1/3.','answer':'2/5','explanation':'I added the numerators and denominators.','correct_answer':'5/6'},
 {'subject':'Science','topic':'Force and motion','question':'A cart moves on a frictionless track with zero net force. What happens to its velocity?','answer':'It stops.','explanation':'A moving object needs a continuing forward force to keep moving.','correct_answer':'Its velocity stays constant.'},
 {'subject':'English','topic':'Subject-verb agreement','question':'Choose: The box of pencils (is/are) here.','answer':'are','explanation':'Pencils is plural, so I choose are even though box is the subject.','correct_answer':'is'},
 {'subject':'Mathematics','topic':'Fractions','question':'Add 1/2 + 1/3.','answer':'5/6','explanation':'I used equal parts: 1/2 = 3/6 and 1/3 = 2/6, so the sum is 5/6.','correct_answer':'5/6'},
]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--live', action='store_true', help='Permit four external inference calls using synthetic examples')
    args=parser.parse_args(); settings=get_settings()
    report={'provider':settings.ai_provider, 'requested_model': settings.gemini_model if settings.ai_provider=='gemini' else settings.openrouter_model,
        'credentials_configured': bool(settings.gemini_api_key if settings.ai_provider=='gemini' else settings.openrouter_api_key),
        'dataset':'embedded synthetic smoke cases; NOT independently labeled evaluation', 'cases':[]}
    if not args.live:
        report['status']='NOT TESTED: pass --live to make bounded external requests'
    else:
        try:
            provider=create_diagnosis_provider(settings)
            for context in EXAMPLES:
                start=perf_counter()
                try:
                    result=provider.diagnose(**context)
                    validate_evidence_quotes(result,context['answer'],context['explanation'])
                    assert result.misconception_code in {m.code for m in get_taxonomy(context['subject'],context['topic'])} | {'CORRECT','FOLLOW_UP'}
                    record={'subject':context['subject'], 'topic':context['topic'], 'status':'PASS', 'result':result.model_dump(), 'latency_ms':round((perf_counter()-start)*1000)}
                except Exception as error:
                    record={'subject':context['subject'], 'topic':context['topic'], 'status':'FAIL', 'error_type':type(error).__name__, 'latency_ms':round((perf_counter()-start)*1000)}
                report['cases'].append(record)
            report['status']='PASS' if all(c['status']=='PASS' for c in report['cases']) else 'FAIL'
        except Exception as error:
            report.update(status='FAIL', error_type=type(error).__name__)
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text+'\n')
    print(text)

if __name__=='__main__':main()
