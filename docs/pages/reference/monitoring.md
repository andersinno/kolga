# Monitoring

If you have application that uses Prometheus to instrument the application you can use these settings to make those metrics discoverable by Prometheus Operator

## Configuration

### Variables

| Variable                      | Default    | Description                                                                                         |
|-------------------------------|------------|-----------------------------------------------------------------------------------------------------|
| `K8S_MONITORING_ENABLED`      | false      | Enable Prometheus Operator to discover application                                                  |
| `K8S_MONITORING_NAMESPACE`    | monitoring | Kubernetes namespace where the Prometheus is deployed                                               |
| `K8S_MONITORING_PATH`         | /metrics   | Path to metrics in application                                                                      |
| `K8S_MONITORING_PORT`         | None       | Used when metrics are not available in the application's service port                               |

### Usage

When `K8S_MONITORING_ENABLED` is true Kólga will create ServiceMonitor manifest to the applications namespace and configures NetworkPolicy whichs allows traffic from `monitoring` namespace to the applications namespace. Traffic is also restricted only to the applications `service_port` or `K8S_MONITORING_PORT` if it is defined.
