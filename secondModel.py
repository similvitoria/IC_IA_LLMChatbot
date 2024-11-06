import re
import json
from dataclasses import dataclass, asdict
from typing import List, Optional
import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

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
    idade: Optional[int] = None
    telefone: Optional[str] = None
    experiencias: List[ProfessionalExperience] = None

    def is_complete(self) -> bool:
        return all([
            self.email, self.nome_completo, self.idade,
            self.telefone, self.experiencias
        ])

class ValidationError(Exception):
    pass

class RecruitmentChatbot:
    def __init__(self):
        self.candidate = Candidate()
        self.current_field = "email"
        
    def validate_email(self, email: str) -> bool:
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(pattern, email):
            raise ValidationError("Email inválido. Por favor, forneça um email válido (ex: seu.nome@email.com)")
        return True

    def validate_nome(self, nome: str) -> bool:
        if len(nome.split()) < 2:
            raise ValidationError("Por favor, forneça seu nome completo com pelo menos nome e sobrenome")
        return True

    def validate_idade(self, idade: str) -> bool:
        try:
            idade_int = int(idade)
            if not (0 <= idade_int <= 120):
                raise ValidationError("A idade deve estar entre 0 e 120 anos")
            return True
        except ValueError:
            raise ValidationError("Por favor, forneça apenas números para a idade")

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
        elif not self.candidate.idade:
            return "Qual é sua idade?"
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
            
            # Extrair e validar o JSON da resposta
            json_str = response.choices[0].message['content'].strip()
            # Remover possíveis markdown code blocks
            json_str = json_str.replace('```json', '').replace('```', '').strip()
            
            # Parse do JSON
            experience_data = json.loads(json_str)
            
            # Criar objeto ProfessionalExperience
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
            if not self.candidate.email:
                if self.validate_email(user_input):
                    self.candidate.email = user_input
                    return f"Email registrado: {user_input}\n\n{self.get_next_prompt()}"
                
            elif not self.candidate.nome_completo:
                if self.validate_nome(user_input):
                    self.candidate.nome_completo = user_input
                    return f"Nome registrado: {user_input}\n\n{self.get_next_prompt()}"
                
            elif not self.candidate.idade:
                if self.validate_idade(user_input):
                    self.candidate.idade = int(user_input)
                    return f"Idade registrada: {user_input}\n\n{self.get_next_prompt()}"
                
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
                    experience = self.parse_experience(user_input)
                    self.candidate.experiencias.append(experience)
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
        # Aqui você pode adicionar a lógica para conectar com o módulo de candidatura
        # e sugerir vagas baseadas no perfil
        return f"""
Cadastro finalizado com sucesso!

Resumo das informações:
- Email: {self.candidate.email}
- Nome: {self.candidate.nome_completo}
- Idade: {self.candidate.idade}
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

def main():
    chatbot = RecruitmentChatbot()
    print("Bem-vindo ao nosso processo seletivo!")
    print(chatbot.get_next_prompt())
    
    while True:
        user_input = input("Você: ")
        if user_input.lower() == 'sair':
            print("Chatbot: Até logo!")
            break
            
        response = chatbot.process_input(user_input)
        print(f"Chatbot: {response}")
        
        if "Cadastro finalizado com sucesso!" in response:
            break

if __name__ == "__main__":
    main()