from transformers import AutoModelForCausalLM, AutoTokenizer
import os

DATA_DRIVE_PATH = '/data/model-store'
HF_CACHE_PATH = os.path.join(DATA_DRIVE_PATH, 'huggingface')

os.environ['HF_HOME'] = HF_CACHE_PATH
os.environ['HUGGINGFACE_HUB_CACHE'] = HF_CACHE_PATH
os.environ['TRANSFORMERS_CACHE'] = HF_CACHE_PATH

os.makedirs(HF_CACHE_PATH, exist_ok=True)


MODEL_PATH = "NousResearch/Hermes-2-Pro-Llama-3-8B"
print(f"Downloading model to: {HF_CACHE_PATH}")

AutoTokenizer.from_pretrained(MODEL_PATH)
AutoModelForCausalLM.from_pretrained(MODEL_PATH)

print("Download complete!")
