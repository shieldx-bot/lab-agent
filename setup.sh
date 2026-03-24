 kubectl port-forward svc/chaos-target-nginx  18080:18080 -n backend
 kubectl port-forward svc/prometheus-operated 9090:9090 -n monitoring
 kubectl port-forward svc/chaos-dashboard 2333:2333 -n chaos-mesh
 kubectl port-forward svc/chaos-target-nginx-frontend 18081:18081 -n frontend