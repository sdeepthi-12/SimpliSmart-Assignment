from kubernetes import client, config
import argparse


def load_kube_config():
    """Load Kubernetes configuration."""
    try:
        config.load_kube_config()
    except Exception as e:
        raise RuntimeError("Failed to load Kubernetes configuration.") from e


def get_deployment_status(namespace, deployment_name):
    """Retrieve deployment status."""
    apps_v1 = client.AppsV1Api()
    deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
    replicas = deployment.status.replicas or 0
    available_replicas = deployment.status.available_replicas or 0
    ready = replicas == available_replicas

    # Check for deployment issues
    issues = []
    if replicas != available_replicas:
        issues.append(f"Mismatch: {available_replicas}/{replicas} replicas available.")
    if not ready:
        issues.append("Deployment is not ready.")

    return {
        "replicas": replicas,
        "available_replicas": available_replicas,
        "ready": ready,
        "issues": issues,
    }


def get_pod_status(namespace, deployment_name):
    """Retrieve pod status."""
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()

    # Fetch the deployment to get the label selector
    deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
    labels = deployment.spec.selector.match_labels
    label_selector = ",".join(f"{key}={value}" for key, value in labels.items())

    # List pods matching the label selector
    pods = core_v1.list_namespaced_pod(namespace, label_selector=label_selector)
    pod_statuses = []
    issues = []

    for pod in pods.items:
        pod_name = pod.metadata.name
        pod_phase = pod.status.phase
        reason = pod.status.reason or ""
        detailed_reason = ""

        # Extract detailed container status if the pod is not running
        if pod.status.container_statuses:
            for container_status in pod.status.container_statuses:
                if container_status.state.waiting:
                    detailed_reason = container_status.state.waiting.reason
                elif container_status.state.terminated:
                    detailed_reason = container_status.state.terminated.reason

        pod_status = {
            "name": pod_name,
            "status": pod_phase,
            "reason": reason or detailed_reason,
        }
        pod_statuses.append(pod_status)

        # Identify pod issues
        if pod_phase != "Running":
            issues.append(f"Pod {pod_name} is in '{pod_phase}' state. Reason: {reason or detailed_reason}")

    return pod_statuses, issues



def get_pod_metrics(namespace, deployment_name):
    """Retrieve CPU and memory usage for pods."""
    try:
        custom_objects_api = client.CustomObjectsApi()
        # Metrics API group and version
        group = "metrics.k8s.io"
        version = "v1beta1"
        resource = "pods"

        # Fetch metrics for pods in the namespace
        metrics = custom_objects_api.list_namespaced_custom_object(
            group, version, namespace, resource
        )

        pod_metrics = []
        for pod in metrics["items"]:
            pod_name = pod["metadata"]["name"]
            containers = pod["containers"]
            total_cpu = sum(
                int(container["usage"]["cpu"].replace("n", "")) for container in containers
            ) / 1e6  # Convert nanocores to millicores
            total_memory = sum(
                int(container["usage"]["memory"].replace("Ki", "")) for container in containers
            ) / 1024  # Convert KiB to MiB
            pod_metrics.append({
                "name": pod_name,
                "cpu_millicores": total_cpu,
                "memory_mib": total_memory,
            })
        return pod_metrics
    except client.exceptions.ApiException as e:
        if e.status == 404:
            return "Metrics API unavailable"
        raise



def check_health(namespace, deployment_name):
    """Check health status of deployment."""
    deployment_status = get_deployment_status(namespace, deployment_name)
    pod_statuses, pod_issues = get_pod_status(namespace, deployment_name)
    pod_metrics = get_pod_metrics(namespace, deployment_name)

    # Aggregate all issues
    issues = deployment_status["issues"] + pod_issues

    return {
        "deployment": deployment_status,
        "pods": pod_statuses,
        "metrics": pod_metrics if pod_metrics else "Metrics API unavailable",
        "issues": issues,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check Kubernetes Deployment Health.")
    parser.add_argument("--namespace", required=True, help="Namespace of the deployment.")
    parser.add_argument("--deployment", required=True, help="Deployment name.")

    args = parser.parse_args()

    try:
        load_kube_config()
        health = check_health(args.namespace, args.deployment)
        print("Health Status:")
        print(health)

        # Display issues
        if health["issues"]:
            print("\nIssues Detected:")
            for issue in health["issues"]:
                print(f"- {issue}")
        else:
            print("\nNo issues detected. Deployment is healthy.")

    except Exception as e:
        print(f"Error: {e}")
