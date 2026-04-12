import onnxruntime as ort

session = ort.InferenceSession("model.onnx")

for inp in session.get_inputs():
    print(inp.name, inp.shape)