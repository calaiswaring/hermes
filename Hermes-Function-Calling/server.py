import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import uvicorn

# --- Model Configuration ---
MODEL_PATH = "NousResearch/Hermes-2-Pro-Llama-3-8B"
CHAT_TEMPLATE = "chatml"
LOAD_IN_4BIT = False 

# --- FastAPI App Initialization ---
app = FastAPI()

# --- Load Model and Tokenizer ---
print("Loading model and tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.bfloat16,
    load_in_4bit=LOAD_IN_4BIT,
    device_map="auto"
)
print("Model and tokenizer loaded successfully.")

# --- Pydantic Model for Request Body ---
class D3Request(BaseModel):
    raw_data: str
    chart_type: str
    data_type: str # "JSON" or "CSV"

# --- Helper Function for Prompting ---
def create_d3_prompt(raw_data: str, chart_type: str, data_type: str) -> str:
    """Creates the prompt for the model to generate D3.js code."""
    system_prompt = (
        "You are an expert D3.js developer. Your task is to generate a complete, "
        "self-contained D3.js script (without the script tags) to visualize the provided data. "
        "The script must handle its own data parsing and rendering."
    )
    
    user_prompt = "" 
    data_block = ""
    
    # Define data block based on type
    if data_type == "CSV":
        data_block = f"const csvData = `\n{raw_data}\n`;"
    else: # JSON
        data_block = f"const jsonData = `{raw_data}`;"


    if chart_type == "Bar Chart":
        data_handling_steps = ""
        if data_type == "CSV":
            data_handling_steps = (
                "1. The CSV data is provided in a constant named `csvData`. Parse it using `d3.csvParse()`.\n"
                "2. **MOST IMPORTANT STEP:** After parsing, convert the 'value' strings to numbers using this exact code: `data.forEach(d => { d.value = +d.value; });`.\n"
            )
        else: # JSON
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
        # Pie chart prompt remains the same as it was already robust
        data_format_instructions = ""
        if data_type == "CSV":
             data_format_instructions = (
                "The data is provided as a single CSV string.\n"
                "The script must perform these initial data-loading steps:\n"
                "1. Parse the provided CSV string into an array of objects. **You MUST use `d3.csvParse()` for this.**\n"
                "2. After parsing, you MUST iterate through the data and convert the numeric 'value' column to a number, for example: `data.forEach(d => { d.value = +d.value; });` This is a critical step.\n\n"
            )
        else: # JSON
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
    
    # Apply the ChatML template
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

# API Endpoint
@app.post("/generate_d3")
def generate_d3(request: D3Request):
    """
    Generates D3.js code from raw data using the Hermes model.
    """
    try:
        # Create the prompt
        prompt = create_d3_prompt(request.raw_data, request.chart_type, request.data_type)
        
        # Tokenize the input
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        # Generate the output
        outputs = model.generate(
            **inputs,
            max_new_tokens=2048,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=True,
            temperature=0.3,
            top_p=0.9,
        )
        
        # Decode the response and clean it up
        response_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract the code part from the model's response
        assistant_response = response_text.split("<|im_start|>assistant\n")[-1]

        # Clean up common code block markers
        if "```javascript" in assistant_response:
            assistant_response = assistant_response.split("```javascript\n")[1]
        if "```" in assistant_response:
            assistant_response = assistant_response.split("```")[0]
            
        return {"d3_code": assistant_response.strip()}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)