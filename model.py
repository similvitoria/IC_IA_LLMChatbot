from langchain import LLMChain, PromptTemplate
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
from dotenv import load_dotenv

# Carregar variáveis do arquivo .env
load_dotenv()

# Obtenha o token do Hugging Face a partir das variáveis de ambiente
huggingface_token = os.getenv("HUGGINGFACE_TOKEN")

# Inicialize o modelo e o tokenizador
model_name = "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF"  # Troque pelo modelo que você deseja usar
tokenizer = AutoTokenizer.from_pretrained(model_name, use_auth_token=huggingface_token)
model = AutoModelForCausalLM.from_pretrained(model_name, use_auth_token=huggingface_token)

# Crie uma função de chatbot
def chatbot(input_text):
    # Tokenize the input text
    inputs = tokenizer.encode(input_text, return_tensors="pt")
    
    # Generate a response
    outputs = model.generate(inputs, max_length=100, num_return_sequences=1)
    
    # Decode the response
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

# Loop para interação com o usuário
if __name__ == "__main__":
    print("Chatbot: Olá! Como posso ajudar você hoje?")
    while True:
        user_input = input("Você: ")
        if user_input.lower() in ["sair", "exit"]:
            print("Chatbot: Até logo!")
            break
        response = chatbot(user_input)
        print(f"Chatbot: {response}")
