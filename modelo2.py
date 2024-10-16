import subprocess
import json

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
    print(prompt)
    
    nome = input("Usuário: Meu nome é ")
    email = input("Usuário: Meu e-mail é ")
    
    prompt += f"Usuário: Meu nome é {nome} e meu e-mail é {email}.\n"
    prompt += "Assistente: Obrigado, " + nome + "! Você já está cadastrado no nosso banco de currículos?\n"
    
    cadastrado = input("Usuário (Sim/Não): ").strip().lower()
    prompt += f"Usuário: {cadastrado}.\n"

    if cadastrado == "não" or cadastrado == "nao":
        prompt += "Assistente: Sem problemas! Vamos começar. Qual é a modalidade de trabalho que você deseja? Presencial, remoto, ou híbrido?\n"
        print("Assistente: Sem problemas! Vamos começar. Qual é a modalidade de trabalho que você deseja? Presencial, remoto, ou híbrido?")
        
        modalidade = input("Usuário: ").strip().capitalize()
        prompt += f"Usuário: {modalidade}.\n"
        
        prompt += "Assistente: E quais cargos você está interessado em ocupar?\n"
        print("Assistente: E quais cargos você está interessado em ocupar?")
        cargos = input("Usuário: ").strip()
        prompt += f"Usuário: {cargos}.\n"
        
        prompt += "Assistente: Agora, por favor, me forneça algumas informações pessoais para completar o cadastro: data de nascimento, telefone e cidade onde reside.\n"
        print("Assistente: Agora, por favor, me forneça algumas informações pessoais para completar o cadastro: data de nascimento, telefone e cidade onde reside.")
        
        data_nascimento = input("Usuário: Data de nascimento: ")
        telefone = input("Usuário: Telefone: ")
        cidade = input("Usuário: Cidade: ")
        prompt += f"Usuário: Data de nascimento {data_nascimento}, telefone {telefone}, cidade {cidade}.\n"

        resposta = gerar_resposta(prompt)
        print("Assistente:", resposta)

        prompt += resposta + "\n"
    
    prompt += "Assistente: Agora vou verificar se temos vagas disponíveis que atendem ao seu perfil. Um momento, por favor...\n"
    print("Assistente: Agora vou verificar se temos vagas disponíveis que atendem ao seu perfil. Um momento, por favor...")
    
    import time
    time.sleep(2)
    
    prompt += "Assistente: Encontrei algumas vagas que podem ser do seu interesse!\n"
    prompt += "1. Desenvolvedor de Software - Empresa X (Remoto)\n"
    prompt += "2. Engenheiro de Dados - Empresa Y (Remoto)\n"
    
    print("Assistente: Encontrei algumas vagas que podem ser do seu interesse!")
    print("1. Desenvolvedor de Software - Empresa X (Remoto)")
    print("2. Engenheiro de Dados - Empresa Y (Remoto)")
    
    print("Assistente: Você gostaria de se candidatar a alguma dessas vagas?")
    vaga_escolhida = input("Usuário (1/2): ")
    prompt += f"Usuário: {vaga_escolhida}.\n"

    if vaga_escolhida == "1":
        prompt += "Assistente: Candidatura enviada com sucesso para a vaga de Desenvolvedor de Software na Empresa X!\n"
    elif vaga_escolhida == "2":
        prompt += "Assistente: Candidatura enviada com sucesso para a vaga de Engenheiro de Dados na Empresa Y!\n"
    else:
        prompt += "Assistente: Desculpe, não reconheci a vaga. Por favor, tente novamente mais tarde.\n"

    resposta = gerar_resposta(prompt)
    print("Assistente:", resposta)

    print("Assistente: Você gostaria de receber notificações sobre futuras vagas que correspondam ao seu perfil?")
    receber_notificacoes = input("Usuário (Sim/Não): ").strip().lower()
    prompt += f"Usuário: {receber_notificacoes}.\n"

    if receber_notificacoes == "sim":
        prompt += "Assistente: Notificações ativadas! Você será informado assim que novas vagas estiverem disponíveis.\n"
    else:
        prompt += "Assistente: Tudo bem! Não enviaremos notificações.\n"
    
    resposta = gerar_resposta(prompt)
    print("Assistente:", resposta)

    print("Assistente: Posso ajudar com mais alguma coisa?")
    mais_alguma_coisa = input("Usuário (Sim/Não): ").strip().lower()
    
    if mais_alguma_coisa == "sim":
        print("Assistente: Estou à disposição! O que mais posso fazer por você?")
    else:
        print("Assistente: De nada! Tenha um ótimo dia e boa sorte com sua candidatura!")


conversar_com_assistente()