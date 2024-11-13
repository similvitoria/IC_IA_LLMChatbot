import re
import json
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import openai
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Definição das funções disponíveis para o GPT
AVAILABLE_FUNCTIONS = {
    "save_candidate_data": {
        "name": "save_candidate_data",
        "description": "Salva os dados do candidato em um arquivo JSON",
        "parameters": {
            "type": "object",
            "properties": {
                "candidate_data": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "nome_completo": {"type": "string"},
                        "data_nascimento": {"type": "string"},
                        "telefone": {"type": "string"},
                        "experiencias": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "cargo": {"type": "string"},
                                    "responsabilidades": {"type": "string"},
                                    "habilidades": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "resultados": {"type": "string"}
                                },
                                "required": ["cargo", "responsabilidades", "habilidades", "resultados"]
                            }
                        }
                    },
                    "required": ["email", "nome_completo", "data_nascimento", "telefone", "experiencias"]
                },
                "storage_dir": {"type": "string", "default": "candidates"}
            },
            "required": ["candidate_data"]
        }
    }
}

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

    def is_complete(self) -> bool:
        return all([
            self.email, self.nome_completo, self.data_nascimento,
            self.telefone, self.experiencias
        ])

def call_gpt_with_function(messages: List[Dict[str, str]], function_name: str) -> Dict[str, Any]:
    """
    Chama a API do GPT com suporte a function calling
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            functions=[AVAILABLE_FUNCTIONS[function_name]],
            function_call={"name": function_name}
        )
        return response
    except Exception as e:
        raise Exception(f"Erro ao chamar GPT API: {str(e)}")

def execute_function_call(function_name: str, args: Dict[str, Any]) -> str:
    """
    Executa a função especificada com os argumentos fornecidos
    """
    if function_name == "save_candidate_data":
        candidate_data = args["candidate_data"]
        experiencias = [
            ProfessionalExperience(**exp)
            for exp in candidate_data["experiencias"]
        ]
        
        candidate = Candidate(
            email=candidate_data["email"],
            nome_completo=candidate_data["nome_completo"],
            data_nascimento=candidate_data["data_nascimento"],
            telefone=candidate_data["telefone"],
            experiencias=experiencias
        )
        
        storage_dir = args.get("storage_dir", "candidates")
        return save_candidate_data(candidate, storage_dir)
    else:
        raise ValueError(f"Função desconhecida: {function_name}")

def save_candidate_data(candidate: Candidate, storage_dir: str = "candidates") -> str:
    """
    Salva os dados do candidato em um arquivo JSON
    """
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)
    
    candidate_dict = asdict(candidate)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{candidate.email.split('@')[0]}_{timestamp}.json"
    file_path = os.path.join(storage_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(candidate_dict, f, ensure_ascii=False, indent=2)
    
    return file_path

class ValidationError(Exception):
    pass

class RecruitmentChatbot:
    def __init__(self):
        self.candidate = Candidate()
        self.current_field = "email"
        self.conversation_history = []
        
    def add_to_history(self, role: str, content: str):
        """Adiciona mensagem ao histórico da conversa"""
        self.conversation_history.append({"role": role, "content": content})

    def validate_email(self, email: str) -> bool:
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, email):
            raise ValidationError("Email inválido. Por favor, forneça um email válido (ex: seu.nome@email.com)")
        return True

    def validate_nome(self, nome: str) -> bool:
        if len(nome.split()) < 2:
            raise ValidationError("Por favor, forneça seu nome completo com pelo menos nome e sobrenome")
        return True

    def validate_data_nascimento(self, data_nascimento: str) -> bool:
        try:
            # Tentar converter a string para data
            data = datetime.strptime(data_nascimento, "%d/%m/%Y")
            
            # Verificar se a data não é futura
            if data > datetime.now():
                raise ValidationError("A data de nascimento não pode ser uma data futura")
                
            # Verificar se a pessoa tem uma idade razoável (menos de 120 anos)
            idade = (datetime.now() - data).days / 365.25
            if idade > 120:
                raise ValidationError("A data de nascimento resulta em uma idade maior que 120 anos")
                
            return True
        except ValueError:
            raise ValidationError("Por favor, forneça a data de nascimento no formato DD/MM/AAAA")

    def validate_telefone(self, telefone: str) -> bool:
        numeros = ''.join(filter(str.isdigit, telefone))
        if len(numeros) < 10 or len(numeros) > 11:
            raise ValidationError("O telefone deve conter entre 10 e 11 dígitos (DDD + número)")
        return True

    def get_next_prompt(self) -> str:
        if not self.candidate.email:
            return "Por favor, forneça seu email:"
        elif not self.candidate.nome_completo:
            return "Qual é seu nome completo?"
        elif not self.candidate.data_nascimento:
            return "Qual é sua data de nascimento? (formato: DD/MM/AAAA)"
        elif not self.candidate.telefone:
            return "Qual é seu número de telefone?"
        elif not self.candidate.experiencias:
            return """
Me conte sobre sua experiência profissional mais recente:
- Cargo
- Principais responsabilidades
- Habilidades utilizadas
- Resultados alcançados
"""
        return "Todas as informações foram coletadas! Deseja adicionar mais uma experiência profissional? (sim/não)"

    def parse_experience(self, experience_text: str) -> ProfessionalExperience:
        prompt = f"""
        Analise a seguinte experiência profissional e extraia as informações no formato JSON:
        
        {experience_text}
        
        Retorne um JSON válido com exatamente esta estrutura:
        {{
            "cargo": "cargo da pessoa",
            "responsabilidades": "principais responsabilidades",
            "habilidades": ["habilidade1", "habilidade2"],
            "resultados": "resultados alcançados"
        }}
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "Você deve retornar apenas o JSON válido, sem nenhum texto adicional."
                },
                {
                    "role": "user",
                    "content": prompt
                }]
            )
            
            json_str = response.choices[0].message['content'].strip()
            json_str = json_str.replace('```json', '').replace('```', '').strip()
            
            experience_data = json.loads(json_str)
            
            return ProfessionalExperience(
                cargo=experience_data['cargo'],
                responsabilidades=experience_data['responsabilidades'],
                habilidades=experience_data['habilidades'],
                resultados=experience_data['resultados']
            )
            
        except json.JSONDecodeError as e:
            raise ValidationError(f"Erro ao processar experiência profissional. Por favor, tente novamente com mais detalhes.")
        except KeyError as e:
            raise ValidationError(f"Dados incompletos na experiência profissional. Certifique-se de incluir todas as informações solicitadas.")
        except Exception as e:
            raise ValidationError(f"Erro ao processar experiência: {str(e)}")

    def process_input(self, user_input: str) -> str:
        try:
            # Adicionar input do usuário ao histórico
            self.add_to_history("user", user_input)
            
            if not self.candidate.email:
                if self.validate_email(user_input):
                    self.candidate.email = user_input
                    return f"Email registrado: {user_input}\n\n{self.get_next_prompt()}"
                
            elif not self.candidate.nome_completo:
                if self.validate_nome(user_input):
                    self.candidate.nome_completo = user_input
                    return f"Nome registrado: {user_input}\n\n{self.get_next_prompt()}"
                
            elif not self.candidate.data_nascimento:
                    if self.validate_data_nascimento(user_input):
                        self.candidate.data_nascimento = user_input
                        return f"Data de nascimento registrada: {user_input}\n\n{self.get_next_prompt()}"
                
            elif not self.candidate.telefone:
                if self.validate_telefone(user_input):
                    self.candidate.telefone = user_input
                    return f"Telefone registrado: {user_input}\n\n{self.get_next_prompt()}"
                
            elif not self.candidate.experiencias:
                self.candidate.experiencias = []
                experience = self.parse_experience(user_input)
                self.candidate.experiencias.append(experience)
                
                return f"""
Experiência registrada com sucesso!

Cargo: {experience.cargo}
Responsabilidades: {experience.responsabilidades}
Habilidades: {', '.join(experience.habilidades)}
Resultados: {experience.resultados}

Deseja adicionar mais uma experiência profissional? (sim/não)
"""
            
            else:
                if user_input.lower() == 'sim':
                    return """
Me conte sobre sua próxima experiência profissional:
- Cargo
- Principais responsabilidades
- Habilidades utilizadas
- Resultados alcançados
"""
                elif user_input.lower() == 'não':
                    return self.finalize_registration()
                else:
                    experience = self.parse_experience(user_input)
                    self.candidate.experiencias.append(experience)
                    return f"""
Experiência registrada com sucesso!

Cargo: {experience.cargo}
Responsabilidades: {experience.responsabilidades}
Habilidades: {', '.join(experience.habilidades)}
Resultados: {experience.resultados}

Deseja adicionar mais uma experiência profissional? (sim/não)
"""
                
        except ValidationError as e:
            return f"{str(e)}\n\n{self.get_next_prompt()}"
        
        except Exception as e:
            return f"Ocorreu um erro: {str(e)}\n\nPor favor, tente novamente."

    def finalize_registration(self) -> str:
        try:
            # Preparar mensagem para o GPT
            self.add_to_history("system", "Você deve converter os dados do candidato para o formato JSON adequado para salvamento.")
            
            # Criar uma representação textual estruturada dos dados
            candidate_text = f"""
            Dados do candidato para conversão em JSON:
            Email: {self.candidate.email}
            Nome Completo: {self.candidate.nome_completo}
            Data de Nascimento: {self.candidate.data_nascimento}
            Telefone: {self.candidate.telefone}
            
            Experiências Profissionais:
            {' '.join([f'''
            Experiência {i+1}:
            - Cargo: {exp.cargo}
            - Responsabilidades: {exp.responsabilidades}
            - Habilidades: {', '.join(exp.habilidades)}
            - Resultados: {exp.resultados}
            ''' for i, exp in enumerate(self.candidate.experiencias)])}
            """
            
            self.add_to_history("user", candidate_text)
            
            # Chamar GPT com function calling
            response = call_gpt_with_function(self.conversation_history, "save_candidate_data")
            
            if response.choices[0].message.get("function_call"):
                # Extrair argumentos da chamada de função
                function_args = json.loads(response.choices[0].message["function_call"]["arguments"])
                
                # Executar a função
                saved_file = execute_function_call("save_candidate_data", function_args)
                
                return f"""
Cadastro finalizado com sucesso!
Dados salvos em: {saved_file}

Resumo das informações:
- Email: {self.candidate.email}
- Nome: {self.candidate.nome_completo}
- Data de Nascimento: {self.candidate.data_nascimento}
- Telefone: {self.candidate.telefone}
- Número de experiências: {len(self.candidate.experiencias)}

Experiências profissionais:
{''.join([f'''
Experiência {i+1}:
- Cargo: {exp.cargo}
- Responsabilidades: {exp.responsabilidades}
- Habilidades: {', '.join(exp.habilidades)}
- Resultados: {exp.resultados}
''' for i, exp in enumerate(self.candidate.experiencias)])}

Baseado no seu perfil, vou buscar vagas compatíveis...
[Aqui você pode adicionar a lógica de matching com vagas disponíveis]
"""
            else:
                raise Exception("GPT não retornou uma chamada de função válida")
                
        except Exception as e:
            return f"""
Cadastro finalizado com sucesso, mas houve um erro ao salvar os dados: {str(e)}

Resumo das informações:
- Email: {self.candidate.email}
- Nome: {self.candidate.nome_completo}
- Data de Nascimento: {self.candidate.data_nascimento}
- Telefone: {self.candidate.telefone}
- Número de experiências: {len(self.candidate.experiencias)}
"""

def main():
    chatbot = RecruitmentChatbot()
    print("Bem-vindo ao nosso processo seletivo!")
    print(chatbot.get_next_prompt())
    
    while True:
        try:
            user_input = input("Você: ")
            if user_input.lower() == 'sair':
                print("Chatbot: Até logo!")
                break
                
            response = chatbot.process_input(user_input)
            print(f"Chatbot: {response}")
            
            if "Cadastro finalizado com sucesso!" in response:
                print("\nProcesso de cadastro concluído. Obrigado por participar!")
                break
                
        except KeyboardInterrupt:
            print("\nChatbot: Processo interrompido pelo usuário. Até logo!")
            break
        except Exception as e:
            print(f"\nChatbot: Ocorreu um erro inesperado: {str(e)}")
            print("Por favor, tente novamente ou digite 'sair' para encerrar.")

if __name__ == "__main__":
    try:
        # Verificar configurações necessárias
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente!")
        
        # Criar diretório de candidatos se não existir
        if not os.path.exists("candidates"):
            os.makedirs("candidates")
            
        main()
    except Exception as e:
        print(f"Erro ao iniciar o chatbot: {str(e)}")
        print("Verifique se todas as configurações necessárias estão corretas.")