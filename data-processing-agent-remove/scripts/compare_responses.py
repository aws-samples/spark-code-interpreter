import requests
import json
import time

def test_execution(engine, prompt):
    payload = {
        "prompt": prompt,
        "session_id": f"test-compare-{engine}-{int(time.time())}",
        "execution_engine": engine
    }
    
    print(f"\n{'='*80}")
    print(f"Testing {engine.upper()}")
    print(f"{'='*80}")
    
    timeout = 600 if engine == "emr" else 180
    response = requests.post(
        "http://localhost:8000/spark/generate",
        json=payload,
        timeout=timeout
    )
    
    result = response.json()
    
    if result.get("success"):
        agent_result = result.get("result", {})
        
        print(f"\nTop-level keys in result:")
        print(f"  {list(agent_result.keys())}")
        
        print(f"\nactual_results field:")
        actual_results = agent_result.get("actual_results")
        if actual_results:
            print(f"  Type: {type(actual_results)}")
            print(f"  Length: {len(actual_results) if isinstance(actual_results, list) else 'N/A'}")
            print(f"  Sample: {actual_results[:2] if isinstance(actual_results, list) else actual_results}")
        else:
            print(f"  None or missing")
        
        print(f"\nexecution_output field:")
        execution_output = agent_result.get("execution_output")
        if execution_output:
            print(f"  Type: {type(execution_output)}")
            print(f"  Length: {len(execution_output) if isinstance(execution_output, list) else 'N/A'}")
            print(f"  Sample: {execution_output[:3] if isinstance(execution_output, list) else execution_output}")
        else:
            print(f"  None or missing")
        
        print(f"\nFull response structure:")
        print(json.dumps(result, indent=2, default=str)[:1000])
        
        return result
    else:
        print(f"Failed: {result.get('error')}")
        return None

# Test both
prompt = "Generate a DataFrame with 3 rows: id (1,2,3) and value (10,20,30), write to S3"

lambda_result = test_execution("lambda", prompt)
time.sleep(5)  # Brief pause
emr_result = test_execution("emr", prompt)

print(f"\n{'='*80}")
print("COMPARISON")
print(f"{'='*80}")

if lambda_result and emr_result:
    lambda_data = lambda_result.get("result", {})
    emr_data = emr_result.get("result", {})
    
    print(f"\nLambda has actual_results: {lambda_data.get('actual_results') is not None}")
    print(f"EMR has actual_results: {emr_data.get('actual_results') is not None}")
    
    print(f"\nLambda actual_results type: {type(lambda_data.get('actual_results'))}")
    print(f"EMR actual_results type: {type(emr_data.get('actual_results'))}")
