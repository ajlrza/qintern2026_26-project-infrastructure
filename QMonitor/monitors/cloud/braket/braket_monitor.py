import boto3, os, sys
from braket.aws import AwsSession

def experiment_braket_monitor(config, run_result):

    usage_results = {}
    infra_results = {}

    task_arn = getattr(run_result, "task_metadata", run_result).id if hasattr(run_result, "task_metadata") else getattr(run_result, "id", "")
    device_arn = getattr(run_result, "task_metadata", run_result).deviceId if hasattr(run_result, "task_metadata") else ""
    job_arn = None

    tasks = {
        "get_quantum_task": config.creds['braket_client'].get_quantum_task,
        "search_quantum_tasks": config.creds['braket_client'].search_quantum_tasks,
        "get_job": config.creds['braket_client'].get_job,
    }

    tasks_config = {
        "get_quantum_task": lambda: {"quantumTaskArn": task_arn},
        "search_quantum_tasks": lambda: {
            "filters": [
                {
                    "name": "quantumTaskArn",
                    "values": [task_arn],
                    "operator": "EQUAL",
                }
            ]
        },
        "get_job": lambda: {"jobArn": job_arn},
    }

    if (task_arn != ""):

        tasks.pop("get_job")
        tasks_config.pop("get_job")

    elif (task_arn == ""):

        tasks.pop("get_quantum_task")
        tasks.pop("search_quantum_tasks")

        tasks_config.pop("get_quantum_task")
        tasks_config.pop("search_quantum_tasks")

        try:
            job_arn = getattr(run_result, "task_metadata", run_result).jobArn if hasattr(run_result, "task_metadata") else getattr(run_result, "arn", "")
            if (job_arn == ""):
                tasks.pop("get_job")
                tasks_config.pop("get_job")
        except:
            tasks.pop("get_job")
            tasks_config.pop("get_job")

    try:
        for task, task_value in tasks.items():
            try:
                result = task_value(**tasks_config[task]())
                infra_results[task] = result
                infra_results["encountered_error"] = False
            except Exception as e:
                print({"Error": str(e)})
    except:
        print("Cannot retrieve braket attributes at the moment.")
        infra_results["run_result"] = run_result
        infra_results["encountered_error"] = True 


    braket_usage = config.creds['braket_client'].search_spending_limits(
        maxResults=5,
        filters=[{"name": "deviceArn", "values": [device_arn], "operator": "EQUAL"}],
    )

    limits_list = braket_usage.get("spendingLimits", [])

    if (len(limits_list) >= 1):
        for limit in limits_list:
            usage_results["spending_limit"] = limit["spendingLimitArn"]
            usage_results["device_arn"] = limit["deviceArn"]
            usage_results["created_at"] = limit["createdAt"]
            max_budget = float(limit["spendingLimit"])
            queued_cost = float(limit["queuedSpend"])
            actual_spent = float(limit["totalSpend"])
            remaining_budget = max_budget - (actual_spent + queued_cost)
            if remaining_budget <= max_budget - 100:
                usage_results["Warning"] = True
                usage_results["remaining_budget"] = remaining_budget
            usage_results["remaining_budget"] = remaining_budget
            braket_usage["tracking_period"] = (limit["timePeriod"]["startAt"], limit["timePeriod"]["endAt"])
    else:
        print("Limits list does not exist")

    print(infra_results, usage_results)
    
    return {
        "Braket Infrastructure Metrics": infra_results,
        "Braket Usage Metrics": usage_results
    }