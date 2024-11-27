import os
import json
import re
from datetime import datetime
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any
from twilio.twiml.messaging_response import MessagingResponse
import openai
from dotenv import load_dotenv
import json
from flask import Flask, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


stop_words = ['a', 'o', 'é', 'de', 'que', 'em', 'um', 'para', 'com', 'não', 'por', 'uma']


class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Reuse existing dataclasses and validation logic
@dataclass
class ProfessionalExperience:
    cargo: str
    responsabilidades: str
    habilidades: List[str]
    resultados: str

@dataclass
class Candidate:
    email: Optional[str] = None
    nome_completo: Optional[str] = None
    data_nascimento: Optional[str] = None
    telefone: Optional[str] = None
    experiencias: List[ProfessionalExperience] = None

class ValidationError(Exception):
    pass

class WhatsAppRecruitmentBot:
    def __init__(self):
        # Load or initialize the bot's state
        self.state_file = 'bot_state.json'
        self.candidate_states = {}
        self.vagas_df = pd.read_csv('vagas_tecnologia_atualizado.csv', encoding='utf-8')
        self.vectorizer = TfidfVectorizer(stop_words=stop_words)
        
    def _buscar_vagas_compativeis(self, experiencia: Dict[str, Any], top_n: int = 5) -> List[Dict]:
        """
        Busca vagas compatíveis com a experiência do candidato.
        """
        # Preparar texto de busca
        texto_experiencia = ' '.join([
            experiencia.get('cargo', ''),
            experiencia.get('responsabilidades', ''),
            ' '.join(experiencia.get('habilidades', [])),
            experiencia.get('resultados', '')
        ]).lower()

        # Preparar dados das vagas
        vagas_texto = self.vagas_df.apply(
            lambda row: ' '.join([
                str(row['nome_vaga']),
                str(row['descricao']),
                str(row['skills_necessarias'])
            ]).lower(), 
            axis=1
        )

        # Concatenar texto da experiência e das vagas para treino comum do vectorizer
        textos = [texto_experiencia] + vagas_texto.tolist()
        self.vectorizer.fit(textos)  # Ajusta o vectorizer com todos os textos

        # Vetorização
        experiencia_vetor = self.vectorizer.transform([texto_experiencia])
        vagas_vetores = self.vectorizer.transform(vagas_texto)

        # Calcular similaridade
        similaridades = cosine_similarity(experiencia_vetor, vagas_vetores)[0]

        # Obter top N vagas
        indices_top_n = similaridades.argsort()[-top_n:][::-1]

        # Formatar resultados
        vagas_compativeis = []
        for idx in indices_top_n:
            vaga = self.vagas_df.iloc[idx]
            vagas_compativeis.append({
                'id_vaga': vaga['id_vaga'],
                'nome_vaga': vaga['nome_vaga'],
                'descricao': vaga['descricao'],
                'skills_necessarias': vaga['skills_necessarias'],
                'salario': vaga['salario'],
                'modalidade': vaga['modalidade'],
                'local': vaga['local'],
                'similaridade': similaridades[idx]
            })

        return vagas_compativeis

    def _save_state(self, phone_number: str, state: Dict[str, Any]):
        """Save the conversation state for a specific phone number"""
        try:
            with open(self.state_file, 'r') as f:
                states = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            states = {}
        
        states[phone_number] = state
        
        with open(self.state_file, 'w') as f:
            json.dump(states, f, indent=2, cls=NpEncoder)

    def _load_state(self, phone_number: str) -> Dict[str, Any]:
        """Load the conversation state for a specific phone number"""
        try:
            with open(self.state_file, 'r') as f:
                states = json.load(f)
                return states.get(phone_number, {
                    'current_step': 'email',
                    'candidate_data': {}
                })
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'current_step': 'email',
                'candidate_data': {}
            }

    def _validate_email(self, email: str) -> bool:
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, email))

    def _validate_nome(self, nome: str) -> bool:
        return len(nome.split()) >= 2

    def _validate_data_nascimento(self, data_nascimento: str) -> bool:
        try:
            data = datetime.strptime(data_nascimento, "%d/%m/%Y")
            
            # Check if date is not in the future
            if data > datetime.now():
                return False
                
            # Check if age is reasonable
            idade = (datetime.now() - data).days / 365.25
            return idade <= 120
        except ValueError:
            return False

    def _validate_telefone(self, telefone: str) -> bool:
        numeros = ''.join(filter(str.isdigit, telefone))
        return 10 <= len(numeros) <= 11
    
    def _parse_experience_with_prompt(self, message: str) -> Dict[str, Any]:
        """
        More robust method to parse professional experience using a detailed GPT prompt
        """
        try:
            # Detailed prompt to guide GPT in extracting experience information
            prompt = f"""
Analise a seguinte descrição de experiência profissional e extraia as informações de forma estruturada:

{message}

Por favor, preencha as seguintes informações. Se algum detalhe não estiver claro, faça sua melhor interpretação:

1. Cargo (título do trabalho)
2. Responsabilidades principais (descrição das principais tarefas)
3. Habilidades utilizadas (lista de habilidades técnicas e soft skills)
4. Resultados alcançados (impactos mensuráveis ou conquistas)

Retorne um JSON válido com a seguinte estrutura:
{{
    "cargo": "Título do cargo",
    "responsabilidades": "Descrição das responsabilidades",
    "habilidades": ["Habilidade 1", "Habilidade 2"],
    "resultados": "Resultados e conquistas"
}}

Se não conseguir extrair todas as informações, use valores padrão razoáveis.
"""
            
            # Call OpenAI API with a more flexible approach
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "Você é um assistente especializado em extrair informações estruturadas de descrições de experiência profissional."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=300,  # Limit token usage
                temperature=0.7  # Add some creativity to interpretation
            )
            
            # Extract and clean the JSON response
            response_text = response.choices[0].message['content'].strip()
            
            # Remove code block markers if present
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse the JSON
            experience_data = json.loads(response_text)
            
            # Validate the extracted data
            if not experience_data.get('cargo'):
                raise ValueError("Cargo não identificado")
            
            # Provide default values if some fields are missing
            experience_data['habilidades'] = experience_data.get('habilidades', [])
            experience_data['responsabilidades'] = experience_data.get('responsabilidades', 'Informações não especificadas')
            experience_data['resultados'] = experience_data.get('resultados', 'Resultados não detalhados')
            
            return experience_data
        
        except json.JSONDecodeError:
            # If JSON parsing fails, try a more lenient parsing
            return {
                "cargo": "Cargo não especificado",
                "responsabilidades": message,
                "habilidades": [],
                "resultados": "Informações não estruturadas"
            }
        
        except Exception as e:
            # Fallback method if GPT parsing completely fails
            return {
                "cargo": "Cargo não identificado",
                "responsabilidades": message,
                "habilidades": [],
                "resultados": f"Erro na extração: {str(e)}"
            }

    def process_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Process incoming WhatsApp message and return response"""
        # Load or initialize state for this phone number
        state = self._load_state(phone_number)
        candidate_data = state.get('candidate_data', {})
        current_step = state.get('current_step', 'email')

        # Normalize message input
        message = message.strip()

        try:
            # Reset mechanism for unexpected inputs
            if message.lower() in ['reiniciar', 'resetar', 'começar', 'start']:
                state = {
                    'current_step': 'email',
                    'candidate_data': {}
                }
                self._save_state(phone_number, state)
                return {
                    'reply': "Processo de cadastro reiniciado. Por favor, forneça seu email.",
                    'continue_flow': True
                }

            # Validation and progression logic based on current step
            if current_step == 'email':
                if not self._validate_email(message):
                    return {
                        'reply': "Email inválido. Por favor, forneça um email válido (ex: seu.nome@email.com)",
                        'continue_flow': True
                    }
                candidate_data['email'] = message
                state['current_step'] = 'nome_completo'
                state['candidate_data'] = candidate_data
                self._save_state(phone_number, state)
                return {
                    'reply': "Qual é seu nome completo?",
                    'continue_flow': True
                }

            elif current_step == 'nome_completo':
                if not self._validate_nome(message):
                    return {
                        'reply': "Por favor, forneça seu nome completo com pelo menos nome e sobrenome",
                        'continue_flow': True
                    }
                candidate_data['nome_completo'] = message
                state['current_step'] = 'data_nascimento'
                state['candidate_data'] = candidate_data
                self._save_state(phone_number, state)
                return {
                    'reply': "Qual é sua data de nascimento? (formato: DD/MM/AAAA)",
                    'continue_flow': True
                }

            elif current_step == 'data_nascimento':
                if not self._validate_data_nascimento(message):
                    return {
                        'reply': "Data de nascimento inválida. Por favor, use o formato DD/MM/AAAA e forneça uma data válida",
                        'continue_flow': True
                    }
                candidate_data['data_nascimento'] = message
                state['current_step'] = 'telefone'
                state['candidate_data'] = candidate_data
                self._save_state(phone_number, state)
                return {
                    'reply': "Qual é seu número de telefone?",
                    'continue_flow': True
                }

            elif current_step == 'telefone':
                if not self._validate_telefone(message):
                    return {
                        'reply': "O telefone deve conter entre 10 e 11 dígitos (DDD + número)",
                        'continue_flow': True
                    }
                candidate_data['telefone'] = message
                state['current_step'] = 'experiencia'
                state['candidate_data'] = candidate_data
                self._save_state(phone_number, state)
                return {
                    'reply': """
Me conte sobre sua experiência profissional mais recente:
- Cargo
- Principais responsabilidades
- Habilidades utilizadas
- Resultados alcançados
""",
                    'continue_flow': True
                }

            elif current_step == 'experiencia':
                try:
                    # Use the improved parsing method
                    experience_data = self._parse_experience_with_prompt(message)
                    
                    # Initialize experiences list if not exists
                    if 'experiencias' not in candidate_data:
                        candidate_data['experiencias'] = []
                    
                    candidate_data['experiencias'].append(experience_data)
                    state['current_step'] = 'confirmar_experiencia'
                    state['candidate_data'] = candidate_data
                    self._save_state(phone_number, state)
                    
                    
                    return {
                        'reply': f"""
    Experiência registrada com sucesso!

    Cargo: {experience_data['cargo']}
    Responsabilidades: {experience_data['responsabilidades']}
    Habilidades: {', '.join(experience_data['habilidades']) or 'Nenhuma especificada'}
    Resultados: {experience_data['resultados']}

    Deseja adicionar mais uma experiência profissional? (sim/não)
    """,
                        'continue_flow': True,
                        'next_step': 'confirmar_experiencia'
                    }
                
                except Exception as e:
                    return {
                        'reply': f"""
    Erro ao processar experiência. {str(e)}

    Por favor, forneça os detalhes da sua experiência profissional de forma mais clara:
    - Qual foi o seu cargo?
    - Quais eram suas principais responsabilidades?
    - Que habilidades você utilizou?
    - Quais resultados você alcançou?
    """,
                        'continue_flow': True
                    }

            if current_step == 'confirmar_experiencia':
                if message == 'sim':
                    return {
                        'reply': "Me conte sobre sua próxima experiência profissional.",
                        'continue_flow': True
                    }
                elif message == 'não':
                    # Pegar a última experiência
                    ultima_experiencia = candidate_data['experiencias'][-1]
                    
                    # Buscar vagas compatíveis
                    vagas_compativeis = self._buscar_vagas_compativeis(ultima_experiencia)
                    print(vagas_compativeis)
                    
                    # Formatar resposta
                    if vagas_compativeis:
                        resposta = "🏢 Vagas Compatíveis Encontradas:\n\n"
                        for i, vaga in enumerate(vagas_compativeis, 1):
                            resposta += f"*Vaga {i}:*\n"
                            resposta += f"📋 *Título:* {vaga['nome_vaga']}\n"
                            resposta += f"💰 *Salário:* {vaga['salario']}\n"
                            resposta += f"🌍 *Modalidade:* {vaga['modalidade']}\n"
                            resposta += f"📍 *Local:* {vaga['local']}\n"
                            resposta += f"🔧 *Habilidades:* {vaga['skills_necessarias']}\n\n"
                        
                        resposta += "Gostaria de se candidatar a alguma dessas vagas? (Digite o número da vaga)"
                        
                        # Atualizar estado para próximo passo de candidatura
                        state['current_step'] = 'selecionar_vaga'
                        state['vagas_compativeis'] = vagas_compativeis
                        self._save_state(phone_number, state)
                        
                        return {
                            'reply': resposta,
                            'continue_flow': True
                        }
                    else:
                        saved_file = self._save_candidate(candidate_data)
                        return {
                            'reply': f"Cadastro finalizado! Dados salvos em: {saved_file}\nNenhuma vaga compatível encontrada no momento.",
                            'continue_flow': False
                        }

            # Novo passo para seleção de vaga
            if current_step == 'selecionar_vaga':
                try:
                    numero_vaga = int(message) - 1
                    vagas_compativeis = state.get('vagas_compativeis', [])
                    
                    if 0 <= numero_vaga < len(vagas_compativeis):
                        vaga_selecionada = vagas_compativeis[numero_vaga]
                        
                        # Lógica para candidatura à vaga (pode ser expandida)
                        return {
                            'reply': f"Você se candidatou à vaga: {vaga_selecionada['nome_vaga']}!\n"
                                "Em breve entraremos em contato.",
                            'continue_flow': False
                        }
                    else:
                        return {
                            'reply': "Número de vaga inválido. Por favor, escolha um número da lista.",
                            'continue_flow': True
                        }
                except ValueError:
                    return {
                        'reply': "Por favor, digite apenas o número da vaga.",
                        'continue_flow': True
                    }

        except Exception as e:
            # Comprehensive error handling
            print(f"Error processing message: {e}")  # Log the error
            return {
                'reply': f"""
    Ocorreu um erro inesperado. {str(e)}
    Vamos recomeçar. Por favor, forneça seu email novamente.
    Se o problema persistir, entre em contato com o suporte.
    """,
                'continue_flow': True,
                'current_step': 'email'
            }

    def _save_candidate(self, candidate_data: Dict[str, Any]) -> str:
        """Save candidate data to a JSON file"""
        storage_dir = "candidates"
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{candidate_data.get('email', 'unknown').split('@')[0]}_{timestamp}.json"
        file_path = os.path.join(storage_dir, filename)
        candidate_data = self.convert_int64_to_int(candidate_data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(candidate_data, f, ensure_ascii=False, indent=2)
        
        return file_path

# Flask API setup
app = Flask(__name__)
bot = WhatsAppRecruitmentBot()

@app.route('/', methods=['POST'])
def webhook():
    try:
        # Dados recebidos do Twilio
        phone_number = request.form.get('From')  # Número do usuário
        message = request.form.get('Body')      # Mensagem do usuário
        
        # Processar a mensagem com o bot
        response_data = bot.process_message(phone_number, message)
        
        # Criar uma resposta para enviar ao Twilio
        reply = response_data.get('reply', 'Desculpe, ocorreu um erro no processamento da sua mensagem.')
        resp = MessagingResponse()
        resp.message(reply)
        
        return str(resp)
    except Exception as e:
        # Responder com erro em caso de falha
        resp = MessagingResponse()
        resp.message("Desculpe, ocorreu um erro inesperado. Por favor, tente novamente.")
        return str(resp), 500

if __name__ == '__main__':
    # Validar configuração inicial
    if not os.getenv('OPENAI_API_KEY'):
        raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente!")
    app.run(debug=True, port=5000)