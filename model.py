import subprocess


def gerar_resposta(prompt):
    comando = ["ollama", "run", "llama3.2"]
    processo = subprocess.Popen(comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    stdout, stderr = processo.communicate(input=prompt.encode())
    
    if stderr:
        print(f"Erro: {stderr.decode()}")
    
    return stdout.decode()


def conversar_com_assistente():
    prompt = """
    Assistente: Olá! Bem-vindo ao nosso assistente de vagas. Para começar, poderia me informar seu nome e e-mail?
    """
    print("Assistente: Olá! Bem-vindo ao nosso assistente de vagas. Para começar, poderia me informar seu nome e e-mail?")

    while True:
        
        resposta_usuario = input("Usuário: ")
        prompt += f"Usuário: {resposta_usuario}\n"
        resposta_assistente = gerar_resposta(prompt)
        print("Assistente:", resposta_assistente)
        prompt += f"Assistente: {resposta_assistente}\n"
        if "Posso ajudar com mais alguma coisa?" in resposta_assistente or "Tenha um ótimo dia" in resposta_assistente:
            break


conversar_com_assistente()
