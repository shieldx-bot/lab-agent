import argparse
import json
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import threading
import pandas as pd
import requests
import yaml
import os
import subprocess
import csv
DEFAULT_METRIC_QUERIES: Dict[str, str] = {
	# Disk metrics
	"disk_read_latency_ms": "1000 * (rate(node_disk_read_time_seconds_total[5m]) / rate(node_disk_reads_completed_total[5m]))",
	"disk_write_latency_ms": "1000 * (rate(node_disk_write_time_seconds_total[5m]) / rate(node_disk_writes_completed_total[5m]))",
	"disk_await_ms": "1000 * (rate(node_disk_read_time_seconds_total[5m]) + rate(node_disk_write_time_seconds_total[5m])) / (rate(node_disk_reads_completed_total[5m]) + rate(node_disk_writes_completed_total[5m]))",
	"disk_svctm_ms": "1000 * (rate(node_disk_io_time_seconds_total[5m]) / (rate(node_disk_reads_completed_total[5m]) + rate(node_disk_writes_completed_total[5m])))",
	"disk_util_percent": "100 * rate(node_disk_io_time_seconds_total[5m])",
	"io_wait_percent": "100 * (sum by (instance) (rate(node_cpu_seconds_total{mode=\"iowait\"}[5m])) / sum by (instance) (rate(node_cpu_seconds_total[5m])))",
	"queue_length": "node_disk_io_now",
	"avg_qu_sz": "avg_over_time(node_disk_io_now[5m])",
	"disk_read_errors_rate": "rate(node_disk_read_errors_total[5m])",
	"disk_write_errors_rate": "rate(node_disk_write_errors_total[5m])",
	"container_reads_failed_rate": "rate(container_fs_reads_failed_total{namespace=\"monitoring\"}[5m])",
	"container_writes_failed_rate": "rate(container_fs_writes_failed_total{namespace=\"monitoring\"}[5m])",
	"disk_usage_percent": "100 * (sum by (instance) (node_filesystem_size_bytes{fstype!~\"tmpfs|squashfs|overlay|devtmpfs\"} - node_filesystem_free_bytes{fstype!~\"tmpfs|squashfs|overlay|devtmpfs\"}) / sum by (instance) (node_filesystem_size_bytes{fstype!~\"tmpfs|squashfs|overlay|devtmpfs\"}))",
	"free_space": "sum by (instance) (node_filesystem_avail_bytes{fstype!~\"tmpfs|squashfs|overlay|devtmpfs\"})",
	# # Network metrics
	"request_fault": "sum by (instance) (rate(node_netstat_Tcp_RetransSegs[5m]) + rate(node_netstat_Tcp_InErrs[5m]) + rate(node_netstat_Tcp_OutRsts[5m]))",
	# "timeout_total": "sum by (instance) (rate(node_netstat_Tcp_AttemptFails[5m]) + rate(node_netstat_Tcp_EstabResets[5m]))",
	# "zero_traffic": "(sum by (instance) (rate(node_network_receive_bytes_total[5m])) == 0) * (sum by (instance) (rate(node_network_transmit_bytes_total[5m])) == 0)",
	#  "net_latency_p90_ms": "1000 * histogram_quantile(0.90, sum by (le) (rate(probe_http_duration_seconds_bucket[5m])))",
	# "net_latency_p95_ms": "1000 * histogram_quantile(0.95, sum by (le) (rate(probe_http_duration_seconds_bucket[5m])))",
	"net_throughput": "sum by (instance) (rate(node_network_receive_bytes_total[5m]) + rate(node_network_transmit_bytes_total[5m]))",
	"drop_rate": "sum by (instance) (rate(node_network_receive_drop_total[5m]) + rate(node_network_transmit_drop_total[5m]))",
	"packet_loss_percent": "100 * sum by (instance) (rate(node_network_receive_drop_total[5m]) + rate(node_network_transmit_drop_total[5m])) / sum by (instance) (rate(node_network_receive_packets_total[5m]) + rate(node_network_transmit_packets_total[5m]))",
	"retry_rate": "rate(node_netstat_Tcp_RetransSegs[5m])",
	# "net_latency_ms": "avg by (instance) (1000 * node_tcp_rtt_seconds)",
	# "duplicate_ratio_percent": "100 * sum by (instance) (rate(node_netstat_Tcp_DSACKs[5m]) + rate(node_netstat_Tcp_DupAcks[5m])) / sum by (instance) (rate(node_netstat_Tcp_InSegs[5m]) + rate(node_netstat_Tcp_OutSegs[5m]))",
	"request_count": "sum by (instance) (rate(node_netstat_Tcp_InSegs[5m]) + rate(node_netstat_Tcp_OutSegs[5m]))",
	# "checksum_error_rate": "sum by (instance) (rate(node_network_receive_crc_errors_total[5m]) + rate(node_network_receive_frame_errors_total[5m]) + rate(node_netstat_Tcp_InCsumErrors[5m]) + rate(node_netstat_Udp_InCsumErrors[5m]))",
	"bandwidth_util_percent": "100 * sum by (instance) (rate(node_network_receive_bytes_total[5m]) + rate(node_network_transmit_bytes_total[5m])) / 125000000",
	"throughput_plateau": "abs(deriv((sum by (instance) (rate(node_network_receive_bytes_total[5m]) + rate(node_network_transmit_bytes_total[5m])))[5m:30s]))",
	"net_queue_length": "avg by (instance) (node_network_transmit_queue_length + node_network_receive_queue_length)",
	# "tcp_send_queue": "avg by (instance) (node_netstat_Tcp_SendQueueSize)",
	# "net_rtt_ms": "avg by (instance) (1000 * node_tcp_rtt_seconds)",
	# # DNS metrics
	# "dns_probe_success": "probe_success{job=\"blackbox\", probe=\"dns\"}",
	# "dns_failure_rate": "rate(probe_failed_total{job=\"blackbox\", probe=\"dns\"}[5m])",
	# "dns_lookup_time_ms": "1000 * avg(probe_duration_seconds{job=\"blackbox\", probe=\"dns\"})",
}

def prometheus_query_range(
	prom_url: str,
	query: str,
	start: datetime,
	end: datetime,
	step: str,
	timeout: int,
) -> List[Dict[str, Any]]:
	url = prom_url.rstrip("/") + "/api/v1/query_range"
	params = {
		"query": query,
		"start": f"{start.timestamp():.0f}",
		"end": f"{end.timestamp():.0f}",
		"step": step,
	}
	response = requests.get(url, params=params, timeout=timeout)
	response.raise_for_status()
	payload = response.json()
	if payload.get("status") != "success":
		raise RuntimeError(f"Prometheus API error: {payload}")
	payload = payload.get("data", {}).get("result", [])
	if len(payload) == 0: 
		return 0
	i = payload[0]["values"][0]
	return i[1]
 

def prometheus_query_all(
	prom_url: str,
	start: datetime,
	end: datetime,
	step: str,
	timeout: int,
) -> List[Dict[str, Any]]:
	array =  {}
	label = ""
	cmd = ["kubectl", "create", "token", "account-cluster-manager-mlukp"]
	result = subprocess.run(cmd, capture_output=True, text=True)
	token = result.stdout.strip()
	print("TOKEN:", token)
	response_label = requests.get("http://localhost:2333/api/experiments", headers={"Authorization": f"Bearer {token}"})
	response_label = response_label.json()
	for i in response_label: 
		print(i["name"])
		if i["status"] == "running":
			label = i["name"]

	if label == "": 
		label = "normal"
	array["time_stamp"] = f"{end.timestamp():.0f}"	
	array["label"] = label

	for i in DEFAULT_METRIC_QUERIES: 
		query = DEFAULT_METRIC_QUERIES[i]
		response = prometheus_query_range(prom_url=prom_url, query=query, start=start, end=end,step=step, timeout=timeout)
		array[i] = response
	metrix_backend_network = requests.get("http://localhost:18080/metrics")
	payload = metrix_backend_network.json()
	print(payload)
	targets_payload = payload.get("targets", {})
	preferred_target = os.getenv("METRIX_TARGET_URL", "http://chaos-target-nginx.backend.svc.cluster.local:18080")
	selected_target = preferred_target if preferred_target in targets_payload else next(iter(targets_payload), None)
	if selected_target:
		for i in targets_payload[selected_target]:
			array[i] = targets_payload[selected_target][i]
		array["selected_target"] = selected_target
	else:
		array["selected_target"] = ""
	# print(array)
	file_path = "data.csv"
	df = pd.DataFrame([array])
	if os.path.isfile(file_path):
		df.to_csv(file_path, mode='a', header=False, index=False)
	else:
		df.to_csv(file_path, index=False)
def main():
	prom_url = "http://localhost:9090"
	step = "30s"
	timeout = 3
	while True:
		end = datetime.now()
		start = end - timedelta(seconds=30)
		threading.Thread(target=prometheus_query_all, args=(prom_url, start , end, step, timeout), daemon=True).start()

		time.sleep(30)
	

if __name__ == "__main__":
	main()