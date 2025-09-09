import torch
import time
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import uvicorn

MODEL_PATH = "NousResearch/Hermes-2-Pro-Llama-3-8B"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

ml_models = {}
app = FastAPI()

@app.on_event("startup")
async def startup_event():
    logging.info("Loading model and tokenizer...")
    ml_models["tokenizer"] = AutoTokenizer.from_pretrained(MODEL_PATH)
    ml_models["model"] = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )
    logging.info("Model and tokenizer loaded successfully.")

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutdown event: Cleaning up and shutting down.")
    ml_models.clear()


class D3Request(BaseModel):
    raw_data: str
    chart_type: str
    data_type: str

class ChatRequest(BaseModel):
    messages: list

def create_d3_prompt(raw_data: str, chart_type: str, data_type: str) -> str:
    tokenizer = ml_models.get("tokenizer")
    if not tokenizer:
        raise RuntimeError("Tokenizer not loaded. The application might not have started correctly.")

    system_prompt = (
        "You are an expert D3.js developer. Your task is to generate a complete, "
        "self-contained D3.js script (without the script tags) to visualize the provided data. "
        "The script must handle its own data parsing and rendering."
    )
    
    user_prompt = ""
    data_block = ""
    
    if data_type == "CSV":
        data_block = f"const csvData = `\n{raw_data}\n`;"
    else:
        data_block = f"const jsonData = `{raw_data}`;"


    if chart_type == "Bar Chart":
        data_handling_steps = ""
        if data_type == "CSV":
            data_handling_steps = (
                "1. The CSV data is provided in a constant named `csvData`. Parse it using `d3.csvParse()`.\n"
                "2. **MOST IMPORTANT STEP:** After parsing, convert the 'value' strings to numbers using this exact code: `data.forEach(d => { d.value = +d.value; });`.\n"
            )
        else:
            data_handling_steps = (
                "1. The JSON data is provided in a constant named `jsonData`. Parse it using `JSON.parse()`.\n"
            )

        user_prompt = (
            f"Generate a D3.js script to create a {chart_type}. The script must be self-contained and perform these exact steps:\n"
            f"// Data Definition:\n{data_block}\n\n"
            "// D3.js Implementation Steps:\n"
            f"{data_handling_steps}"
            "3. Define margins, and an inner `width` and `height`.\n"
            "4. Select `d3.select('#d3-container')` and append an SVG.\n"
            "5. **CRITICAL: You MUST set the SVG's dimensions to include the margins.** Use this exact code: `.attr('width', width + margin.left + margin.right).attr('height', height + margin.top + margin.bottom)`.\n"
            "6. After setting the dimensions, append a `<g>` element and `transform` it by the margins.\n"
            "7. Create scales. The `yScale`'s range MUST be `[height, 0]`.\n"
            "8. Render the x-axis and y-axis.\n"
            "9. Bind the data and append rectangles with the correct `x`, `y`, `width`, and `height` attributes, where height is `height - yScale(d.value)`.\n"
            "Do not include any HTML or CSS, only the standalone Javascript code."
        )

    elif chart_type == "Pie Chart":
        data_format_instructions = ""
        if data_type == "CSV":
             data_format_instructions = (
                "The data is provided as a single CSV string.\n"
                "The script must perform these initial data-loading steps:\n"
                "1. Parse the provided CSV string into an array of objects. **You MUST use `d3.csvParse()` for this.**\n"
                "2. After parsing, you MUST iterate through the data and convert the numeric 'value' column to a number, for example: `data.forEach(d => { d.value = +d.value; });` This is a critical step.\n\n"
            )
        else:
            data_format_instructions = "The data is provided as a single JSON string. The script should parse it before use.\n\n"

        user_prompt = (
            f"Generate a D3.js script to create an advanced {chart_type} from the following data:\n"
            f"{data_block}\n"
            f"{data_format_instructions}"
            "The script must then follow these exact rendering instructions:\n"
            "1. Define width and height.\n"
            "2. Create a `d3.pie()` layout. Define it exactly like this: `const pie = d3.pie().sort(null).value(d => d.value);`\n"
            "3. Create the SVG and set its viewBox exactly like this: `.attr('viewBox', [-width / 2, -height / 2, width, height])`.\n"
            "4. Create two arc generators: `arc` for slices and `arcLabel` for label positions.\n"
            "5. First, append a `<g>` for slices and append paths to it. Do not use a transform on this group.\n"
            "6. Second, append a NEW, SEPARATE `<g>` for labels with `text-anchor: 'middle'`.\n"
            "7. In this label group, join data and append `<text>` elements with the transform `d => `translate(${arcLabel.centroid(d)})`.\n"
            "8. Use `.call()` to append two `<tspan>` elements with the following exact attributes:\n"
            "   a. The first tspan for the category: `.append('tspan').attr('y', '-0.4em').attr('font-weight', 'bold').text(d => d.data.category)`\n"
            "   b. The second tspan for the value: `.append('tspan').attr('x', 0).attr('y', '0.7em').attr('fill-opacity', 0.7).text(d => d.data.value)`\n"
            "Do not include any HTML or CSS, only the standalone Javascript code."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    return prompt


@app.post("/generate_d3")
def generate_d3(request: D3Request):
    model = ml_models.get("model")
    tokenizer = ml_models.get("tokenizer")
    if not model or not tokenizer:
        return {"error": "Model not loaded. Please check server logs."}, 503

    total_time = 0
    gpu_time = 0
    total_start_time = time.perf_counter()
    try:
        prompt = create_d3_prompt(request.raw_data, request.chart_type, request.data_type)
        
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        input_length = inputs.input_ids.shape[1]

        gpu_start_time = time.perf_counter()
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=True,
            temperature=0.3,
            top_p=0.9,
        )
        gpu_end_time = time.perf_counter()

        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
        assistant_response = response_text.split("<|im_start|>assistant\n")[-1]

        if "```javascript" in assistant_response:
            assistant_response = assistant_response.split("```javascript\n")[1]
        if "```" in assistant_response:
            assistant_response = assistant_response.split("```")[0]
        
        total_end_time = time.perf_counter()

        total_time = total_end_time - total_start_time
        gpu_time = gpu_end_time - gpu_start_time
        num_generated_tokens = outputs.shape[1] - input_length
        tokens_per_second = num_generated_tokens / gpu_time if gpu_time > 0 else 0
        
        logging.info(f"--- INFERENCE METRICS ---")
        logging.info(f"Total Request Time: {total_time:.2f} seconds")
        logging.info(f"GPU Generation Time: {gpu_time:.2f} seconds")
        logging.info(f"Tokens Generated: {num_generated_tokens}")
        logging.info(f"Tokens/Second (GPU Speed): {tokens_per_second:.2f}")
        logging.info(f"-------------------------")
            
        return {"d3_code": assistant_response.strip()}

    except Exception as e:
        logging.error(f"An error occurred during D3 generation: {e}", exc_info=True)
        return {"error": str(e)}

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Handles generic chat requests with the Hermes model.
    """
    model = ml_models.get("model")
    tokenizer = ml_models.get("tokenizer")
    if not model or not tokenizer:
        return {"error": "Model not loaded. Please check server logs."}, 503

    try:
        prompt = tokenizer.apply_chat_template(
            request.messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        outputs = model.generate(**inputs, max_new_tokens=512)
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        assistant_response = response_text.split("<|im_start|>assistant\n")[-1].strip()

        return {"response": assistant_response}

    except Exception as e:
        logging.error(f"An error occurred during chat generation: {e}", exc_info=True)
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
