import onnxruntime as ort
from transformers import AutoTokenizer

# 1️⃣ Tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    "sentence-transformers/paraphrase-MiniLM-L3-v2",
    use_fast=True
)

# 2️⃣ ONNX 模型路徑
onnx_path = "model.onnx"

# 3️⃣ 建立 ONNX Session
session = ort.InferenceSession(onnx_path)

# 4️⃣ 測試文字
text = "測試文字"

# 5️⃣ 編碼文字
inputs = tokenizer(text, return_tensors="np")

# 6️⃣ 只保留 ONNX 模型需要的輸入（移除多餘欄位）
allowed_keys = {inp.name for inp in session.get_inputs()}  # ONNX 模型真正需要的欄位
ort_inputs = {k: v for k, v in inputs.items() if k in allowed_keys}

# 7️⃣ 推理
outputs = session.run(None, ort_inputs)

# 8️⃣ 結果
print("模型輸出向量形狀:", outputs[0].shape)