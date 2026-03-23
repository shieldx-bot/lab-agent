# Huong Dan Su Dung Chaos Mesh Va Python Metrics (Realtime Labeling)

Tai lieu nay mo ta co che moi:

1. Chay collector theo stream (lien tuc).
2. Khi apply fault chaos, runtime state duoc ghi ngay.
3. CSV duoc append moi window va duoc gan label ngay trong thoi gian fault dang active.

Khac voi co che cu: khong doi den luc ket thuc moi export va label.

## 1) Dieu kien tien quyet

- Da co Kubernetes cluster va truy cap duoc bang `kubectl` hoac `sudo k3s kubectl`.
- Da cai Chaos Mesh (`chaos-mesh` namespace).
- Da co Prometheus (vi du `http://localhost:9090`).
- Namespace `backend` co pod target label `chaos-target=true`.
- Python env da co `pandas`, `requests`, `pyyaml`.

Kiem tra nhanh:

```bash
sudo k3s kubectl get ns | grep -E "chaos-mesh|monitoring|backend" || true
sudo k3s kubectl get pods -n chaos-mesh
sudo k3s kubectl get pods -n backend -l chaos-target=true
```

## 2) Kien truc van hanh moi

Thanh phan chinh:

- `main.py`: collector + labeling engine, chay stream mode.
- `23-chaos-custom.sh`: apply/delete fault va ghi `chaos_runtime_state.json`.
- `chaos_runtime_state.json`: state active/inactive de override label realtime.

Nguyen tac:

1. Luon start stream collector truoc.
2. Apply fault bang custom script de state duoc cap nhat dung.
3. Khi delete/delete-all, state phai ve inactive.
4. State cu qua han se bi bo qua nhờ TTL (`--state-max-age`).

## 3) Chay stream collector (bat buoc)

Tu thu muc `LAB_CENTER/web/agent`:

```bash
source /home/shieldx/Documents/Github/lab-mechine-learning/env/bin/activate

python ./main.py \
  --prom-url http://localhost:9090 \
  --mode stream \
  --step 30s \
  --window-time 30s \
  --state-file ./chaos_runtime_state.json \
  --state-max-age 20m \
  --rules ./chaos-labeling-rules.yaml \
  --output ./chaos_labeled_30s.csv
```

Y nghia tham so quan trong:

- `--mode stream`: append lien tuc, moi window mot batch.
- `--state-file`: file state do script chaos cap nhat.
- `--state-max-age`: state active qua han se bi ignore (chong state treo).
- `--window-time`: nhip lap stream.

## 4) Apply/Delete chaos dung luong realtime

Dung script custom de dam bao state runtime duoc ghi/clear dung luc.

Vi du apply fault net-delay:

```bash
cd ./chaos-mesh-manifests
chmod +x 23-chaos-custom.sh

./23-chaos-custom.sh --fault net-delay --duration 10m --apply
```

Kiem tra state:

```bash
cat ../chaos_runtime_state.json
```

Delete fault:

```bash
./23-chaos-custom.sh --fault net-delay --delete
cat ../chaos_runtime_state.json
```

Delete tat ca fault dang ton tai:

```bash
./23-chaos-custom.sh --delete-all
cat ../chaos_runtime_state.json
```

## 5) Cac fault ID ho tro

```text
disk-latency
disk-read-fault
disk-write-fault
disk-saturation
net-delay
net-loss
net-duplicate
net-corrupt
net-bandwidth
net-partition
dns-error
dns-timeout
```

## 6) Kiem tra ket qua labeling realtime

Xem du lieu moi nhat trong CSV:

```bash
python - <<'PY'
import pandas as pd
p='chaos_labeled_30s.csv'
df=pd.read_csv(p)
print(df[['timestamp','instance','label_root_cause','label_severity','label_confidence','matched_rules']].tail(20).to_string(index=False))
PY
```

Dau hieu da override realtime dung:

- Trong thoi gian fault active, `label_root_cause` = label fault runtime.
- `matched_rules` co `R_RUNTIME_EVENT`.

Sau khi delete fault:

- Label quay lai rule-based.
- `matched_rules` khong con `R_RUNTIME_EVENT`.

## 7) Chay one-shot range mode (chi de backfill)

Neu can xuat theo khoang thoi gian cu:

```bash
python ./main.py \
  --prom-url http://localhost:9090 \
  --mode range \
  --start now-2h \
  --end now \
  --step 30s \
  --rules ./chaos-labeling-rules.yaml \
  --output ./chaos_labeled_30s.csv
```

Luu y: mode nay khong phai luong realtime van hanh chinh.

## 8) Su co thuong gap va cach xu ly

### 8.1 `unable to set tcs` hoac `unable to flush ip sets`

Nguyen nhan: network chaos chong len nhau hoac ket finalizer.

```bash
sudo k3s kubectl delete networkchaos --all -n backend --ignore-not-found
for r in $(sudo k3s kubectl get networkchaos -n backend -o name); do
  sudo k3s kubectl patch -n backend "$r" --type=json -p='[{"op":"remove","path":"/metadata/finalizers"}]' || true
done
sudo k3s kubectl rollout restart ds/chaos-daemon -n chaos-mesh
sudo k3s kubectl rollout status ds/chaos-daemon -n chaos-mesh --timeout=120s
```

### 8.2 `path is the root`

Nguyen nhan: IOChaos inject vao root filesystem.
Can giu `volumePath` va `path` o vung an toan (vi du `/mnt/chaos/*`).

### 8.3 `no pod is selected`

Kiem tra target pod:

```bash
sudo k3s kubectl get pods -n backend -l chaos-target=true
```

Neu khong co pod nao, apply lai target workload.

## 9) Quy trinh van hanh khuyen nghi

1. Start stream collector.
2. Apply fault bang `23-chaos-custom.sh`.
3. Theo doi CSV realtime.
4. Delete fault khi ket thuc.
5. Xac nhan state inactive.

Checklist ket thuc:

- `chaos_runtime_state.json` dang `active: false`.
- CSV tiep tuc append binh thuong.
- Khong con `R_RUNTIME_EVENT` sau khi fault da delete.
