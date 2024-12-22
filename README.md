# SimpliSmart Assignment

## Prerequisites

Ensure the following tools are installed and configured on your system:

1. **kubectl**

   - Installation guide: [Install kubectl on Windows](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/#install-kubectl-on-windows)
   - Verify installation:
     ```bash
     kubectl version
     ```

2. **Docker Desktop**

   - Installation guide: [Install Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/)

3. **Minikube**

   - Installation guide: [Install Minikube](https://minikube.sigs.k8s.io/docs/start/?arch=%2Fwindows%2Fx86-64%2Fstable%2F.exe+download)
   - Verify installation:
     ```bash
     minikube version
     ```

4. **Helm**

   - Installation guide: [Install Helm](https://github.com/helm/helm/releases)
   - Verify installation:
     ```bash
     helm version
     ```

### Note

Add the installation paths for Minikube, Helm, and kubectl to your system’s environment variables for ease of use.

---

## Step 1: Connect to the Kubernetes Cluster

1. **Start Docker Desktop** to enable the container runtime.
2. **Start Minikube Cluster**:
   ```bash
   minikube start
   ```
3. Verify Minikube is running:
   ```bash
   minikube status
   ```
4. Check cluster connectivity:
   ```bash
   kubectl cluster-info
   ```

---

## Step 2: Install Helm and KEDA

1. **Initialize Helm**:

   ```bash
   helm repo add bitnami https://charts.bitnami.com/bitnami
   ```

2. **Install KEDA Using Helm**:

   ```bash
   helm repo add kedacore https://kedacore.github.io/charts
   helm repo update
   helm install keda kedacore/keda --namespace keda --create-namespace
   ```

3. Verify KEDA installation:

   ```bash
   kubectl get pods -n keda
   ```

4. Check the Custom Resource Definitions (CRDs) installed by KEDA:

   ```bash
   kubectl get crds
   ```

---

## Step 3: Deploy NGINX with Autoscaling

1. **Create Namespace**: Apply the namespace configuration:

   ```bash
   kubectl apply -f nginx-namespace.yaml
   ```

2. **Deploy NGINX**:

   - Apply the deployment configuration:
     ```bash
     kubectl apply -f nginx-deployment.yaml
     ```
   - Verify deployment:
     ```bash
     kubectl get pods -n nginx-namespace
     ```

3. **Create NGINX Service**:

   - Apply the service configuration:
     ```bash
     kubectl apply -f nginx-service.yaml
     ```
   - Verify the service:
     ```bash
     kubectl get svc -n nginx-namespace
     ```

4. **Configure Autoscaling with KEDA**:

   - Apply the ScaledObject configuration:
     ```bash
     kubectl apply -f nginx-scaledobject.yaml
     ```
   - Verify the ScaledObject:
     ```bash
     kubectl get scaledobject -n nginx-namespace
     ```
   - Check deployment details:
     ```bash
     kubectl describe deployment nginx-deployment -n nginx-namespace
     ```
   - Check Horizontal Pod Autoscaler (HPA):
     ```bash
     kubectl get hpa -n nginx-namespace
     ```

   - **Public image and tag from DockerHub**: `nginx:1.23.0`

---

## Step 4: Test Autoscaling

1. **Simulate Load with Stress Tool**:

   - Pull a stress-testing image from DockerHub:
     ```bash
     docker pull polinux/stress
     ```

   - Deploy a separate pod that runs the stress workload:
     ```bash
     kubectl apply -f stress-pod.yaml
     ```

2. **Add a Sidecar Container to NGINX Deployment**:

   - Modify the NGINX deployment to include a sidecar container that generates CPU load. Example configuration: Uses one CPU core (--cpu 1) for 60 seconds to generate load.

     ```yaml
     - name: stress
       image: polinux/stress
       command: ["stress"]
       args: ["--cpu", "1", "--timeout", "60s"] # Adjust CPU and duration
       resources:
         requests:
           cpu: "100m"
           memory: "128Mi"
         limits:
           cpu: "200m"
           memory: "256Mi"
     ```
   - Update the nginx-deployment.yaml
     ```bash
     kubectl apply -f nginx-deployment.yaml
     ```

3. **Monitor Autoscaling Behavior**:

   - Watch the pods scale:
     ```bash
     kubectl get pods -n nginx-namespace --watch
     ```
   - Describe the ScaledObject status:
     ```bash
     kubectl describe scaledobject nginx-scaledobject -n nginx-namespace
     ```

---

## Step 5: Check Health Status

1. **Run Health Check Script**:

   - Execute the Python script with the required arguments:
     ```bash
     python check_health.py --namespace nginx-namespace --deployment nginx-deployment
     ```

2. **Example Output**:

   ```json
   Health Status:
   {
       "deployment": {
           "replicas": 4,
           "available_replicas": 2,
           "ready": false,
           "issues": [
               "Mismatch: 2/4 replicas available.",
               "Deployment is not ready."
           ]
       },
       "pods": [
           {
               "name": "nginx-deployment-559d76fc7b-f4ljc",
               "status": "Running",
               "reason": ""
           },
           {
               "name": "nginx-deployment-559d76fc7b-mqcpc",
               "status": "Running",
               "reason": ""
           },
           {
               "name": "nginx-deployment-5c96bb98f8-rpmtr",
               "status": "Pending",
               "reason": "ImagePullBackOff"
           },
           {
               "name": "nginx-deployment-5c96bb98f8-t49jj",
               "status": "Pending",
               "reason": "ImagePullBackOff"
           }
       ],
       "metrics": "Metrics API unavailable",
       "issues": [
           "Mismatch: 2/4 replicas available.",
           "Deployment is not ready.",
           "Pod nginx-deployment-5c96bb98f8-rpmtr is in 'Pending' state. Reason: ImagePullBackOff"
       ]
   }
   ```

3. **Debug Issues**:

   - View logs for problematic pods:
     ```bash
     kubectl logs <pod_name> -n nginx-namespace
     ```
   - Check pod events:
     ```bash
     kubectl describe pod <pod_name> -n nginx-namespace
     ```

---

## Step 6: Access NGINX

1. **Access via Minikube IP**:

   - Get the Minikube IP:
     ```bash
     minikube ip
     ```
   - Get the NodePort:
     ```bash
     kubectl get service -n nginx-namespace
     ```
   - Access NGINX using:
     ```
     curl http://<minikube_ip>:<node_port>
     ```

2. **Create a Tunnel (if necessary)**:

   ```bash
   minikube tunnel
   ```

   - Use port forwarding:
     ```bash
     kubectl port-forward svc/nginx-service 8080:80 -n nginx-namespace
     ```
   - Access at:
     ```
     http://localhost:8080
     ```

