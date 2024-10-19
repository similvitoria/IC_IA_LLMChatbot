import re
import json
import subprocess

# Funções para simular ações text-to-action
def armazenar_dados_usuario(dados):
    print(f"Armazenando dados do usuário: {dados}")
    return "Dados armazenados com sucesso."

def montar_curriculo(dados):
    print(f"Montando currículo com os dados fornecidos: {dados}")
    return "Currículo criado e armazenado no sistema."

def buscar_vagas(criterios):
    print(f"Buscando vagas com os critérios: {criterios}")
    return ["Desenvolvedor de Software - Empresa X (Remoto)", "Engenheiro de Dados - Empresa Y (Remoto)"]

def registrar_candidatura(vaga, usuario):
    print(f"Registrando candidatura para a vaga '{vaga}' para o usuário {usuario}")
    return f"Candidatura enviada com sucesso para a vaga {vaga}."

def adicionar_notificacoes(usuario):
    print(f"Adicionando {usuario} à lista de distribuição de alertas de novas vagas.")
    return "Notificações ativadas."

# Função para gerar resposta usando ollama
def gerar_resposta(prompt):
    comando = ["ollama", "run", "llama3.2"]
    processo = subprocess.Popen(comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = processo.communicate(input=prompt.encode())
    if stderr:
        print(f"Erro: {stderr.decode()}")
    return stdout.decode()

# Função para detectar text-to-action e executar as ações apropriadas
def detectar_text_to_action_e_executar(texto, contexto_usuario):
    padroes_acoes = [
        (r'\barmazene\b', lambda dados: armazenar_dados_usuario(dados)),
        (r'\bencaminhe\b', lambda dados: montar_curriculo(dados)),
        (r'\bbusque\b', lambda criterios: buscar_vagas(criterios)),
        (r'\bregistre\b', lambda vaga: registrar_candidatura(vaga, contexto_usuario["nome"])),
        (r'\badicione\b', lambda _: adicionar_notificacoes(contexto_usuario["nome"]))
    ]
    for padrao, acao in padroes_acoes:
        if re.search(padrao, texto, flags=re.IGNORECASE):
            if "dados" in contexto_usuario:
                resultado = acao(contexto_usuario["dados"])
            elif "vaga" in contexto_usuario:
                resultado = acao(contexto_usuario["vaga"])
            else:
                resultado = acao(None)
            print(f"Ação executada: {resultado}")

# Função para obter o contexto do Ollama
def obter_contexto_ollama(prompt):
    comando = ["ollama", "run", "llama3.2"]
    processo = subprocess.Popen(comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = processo.communicate(input=prompt.encode())
    if stderr:
        print(f"Erro ao chamar o Ollama: {stderr.decode()}")
        return None
    try:
        contexto_usuario = json.loads(stdout.decode())
        print(contexto_usuario)
        return contexto_usuario
    except json.JSONDecodeError:
        print("Erro ao decodificar a resposta do Ollama.")
        return None

# Exemplo de prompt com text-to-action
prompt_exemplo = """Você é um assistente virtual especializado em auxiliar candidatos na busca por vagas de emprego. Sua função é simular uma conversa com os usuários para coletar informações de cadastro, montar currículos, e ajudar a encontrar vagas adequadas ao perfil do candidato. Sua abordagem deve ser amigável e profissional.
Responda e execute ações conforme os cenários descritos abaixo:
1. Inicie a conversa pedindo ao usuário para informar seu nome e e-mail de forma clara.
2. Pergunte se o usuário já está cadastrado no banco de currículos. Caso a resposta seja "não", solicite informações adicionais como modalidade de trabalho desejada, cargos de interesse, data de nascimento, telefone e cidade de residência.
3. Pergunte se o usuário deseja fornecer uma descrição textual ou um áudio para a montagem do currículo. Se optar por áudio, forneça tópicos específicos a serem abordados.
4. Reúna todas as informações e direcione-as para o módulo de montagem de currículos.
5. Realize uma busca de vagas de emprego com base nas especificações do usuário e retorne uma lista.
6. Pergunte se o usuário deseja se candidatar a alguma das vagas sugeridas. Registre a candidatura conforme a escolha do usuário.
7. Pergunte se o usuário gostaria de receber notificações sobre futuras vagas.
8. Finalize perguntando se o usuário precisa de mais alguma coisa e agradeça ao término da conversa.
Limite suas respostas ao escopo dessas interações e ao contexto específico da simulação de cadastro, montagem de currículos, busca e candidatura a vagas de emprego."""

# Obter o contexto do Ollama
contexto_usuario = obter_contexto_ollama(prompt_exemplo)

# Definir o estado inicial
prompt = prompt_exemplo  # Inicia o prompt de conversa com o exemplo

# Loop de interação com o usuário
while True:
    resposta_usuario = input("Usuário: ")
    prompt += f'Usuário: {resposta_usuario}\n'
    resposta_assistente = gerar_resposta(prompt)
    print("Assistente:", resposta_assistente)
    prompt = f"Assistente: {resposta_assistente}\n"
    
    
    
