python -m venv sii
source sii/bin/activate
# pip install -r baseline/requirements.txt
export CUDA_VISIBLE_DEVICES=0
export MODEL_PATH=/inspire/hdd/project/mianxiangdayuyanmoxing/public/Qwen2.5-14B-Instruct
RESULT_ROOT="${RESULT_ROOT:-/inspire/hdd/project/mianxiangdayuyanmoxing/261130003/results}"
MODEL_TAG="${MODEL_TAG:-14b}"
RESULT_DIR="${RESULT_DIR:-$RESULT_ROOT/baseline/$MODEL_TAG}"
mkdir -p "$RESULT_DIR"
# 单条推理
python3 baseline/baseline_inference.py --model_path "$MODEL_PATH"
# 性能基线
python3 baseline/benchmark.py --model_path "$MODEL_PATH" --output "$RESULT_DIR/results_baseline.json"
# 精度基线
python3 baseline/evaluate_accuracy.py --model_path "$MODEL_PATH" --eval_file baseline/ceval_subset.jsonl --output "$RESULT_DIR/accuracy_baseline.json"
