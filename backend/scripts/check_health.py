"""Check local API/database/configuration without consuming inference tokens."""
import argparse,json
import httpx

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--base-url',default='http://127.0.0.1:8018');args=parser.parse_args()
    result={}
    with httpx.Client(timeout=5) as client:
        for path in ['/health','/health/ready','/health/ai']:
            try:
                response=client.get(args.base_url+path);result[path]={'http_status':response.status_code,'response':response.json()}
            except Exception as error:result[path]={'status':'FAIL','error_type':type(error).__name__}
    print(json.dumps(result,indent=2))
    if any(r.get('http_status')!=200 for r in result.values()):raise SystemExit(1)

if __name__=='__main__':main()
