from beam import App, Runtime, Image, Volume, QueueDepthAutoscaler
from transformers import AutoTokenizer, OPTForCausalLM

# Beam Volume to store cached models
CACHE_PATH = "./cached_models"

app = App(
    name="high-performance-inference",
    runtime=Runtime(
        cpu=1,
        memory="8Gi",
        gpu="A10G",
        image=Image(
            python_version="python3.9",
            python_packages=[
                "transformers",
                "torch",
            ],  # You can also add a path to a requirements.txt instead
        ),
    ),
    # Storage Volume for model weights
    volumes=[Volume(name="cached_models", path=CACHE_PATH)],
)

# Autoscale by queue depth, up to 5 replicas
autoscaler = QueueDepthAutoscaler(max_tasks_per_replica=5, max_replicas=5)


# This function runs once when the container boots
def load_models():
    model = OPTForCausalLM.from_pretrained("facebook/opt-125m", cache_dir=CACHE_PATH)
    tokenizer = AutoTokenizer.from_pretrained("facebook/opt-125m", cache_dir=CACHE_PATH)

    return model, tokenizer


# Rest API initialized with loader and autoscaler
@app.rest_api(loader=load_models, autoscaler=autoscaler)
def predict(**inputs):
    # Retrieve cached model from loader
    model, tokenizer = inputs["context"]

    try:
        prompt = inputs["prompt"]
    # Use a default prompt if none is provided
    except KeyError:
        prompt = "Q: What is the largest animal?\nA:"

    inputs = tokenizer(prompt, return_tensors="pt")

    # Generate
    generate_ids = model.generate(inputs.input_ids, max_length=30)
    result = tokenizer.batch_decode(
        generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0]

    print(result)

    return {"prediction": result}
