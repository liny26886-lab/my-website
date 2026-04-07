from transformers import AutoTokenizer, AutoModel
import torch

model_name = "sentence-transformers/paraphrase-MiniLM-L3-v2"

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

model.eval()

dummy_input = tokenizer("test", return_tensors="pt")

torch.onnx.export(
    model,
    (dummy_input["input_ids"], dummy_input["attention_mask"]),
    "model.onnx",  # ← 會產生這個檔案
    input_names=["input_ids", "attention_mask"],
    output_names=["output"],
    dynamic_axes={
        "input_ids": {0: "batch"},
        "attention_mask": {0: "batch"},
        "output": {0: "batch"}
    },
    opset_version=12
)