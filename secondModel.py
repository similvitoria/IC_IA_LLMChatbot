import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Education:
    institution: str
    course: str
    period: str
    status: str = "Em andamento"

@dataclass
class Experience:
    company: str
    role: str
    period: str
    description: str

@dataclass
class Candidate:
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    educations: List[Education] = field(default_factory=list)
    experiences: List[Experience] = field(default_factory=list)

class LLMRecruitmentChatbot:
    def __init__(self):
        self.candidates = {}
        self.current_candidate = None
        self.state = "INITIAL"
        self.conversation_history = []
        self.TIMEOUT = 15  # timeout em segundos

    def run_command_with_timeout(self, command):
        """Executa um comando com timeout"""
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            stdout, stderr = process.communicate(timeout=self.TIMEOUT)
            if process.returncode == 0:
                return stdout.strip()
            return f"Erro: {stderr.strip()}"
        except subprocess.TimeoutExpired:
            process.kill()
            return "Tempo de resposta excedido. Usando resposta padrão."
        except Exception as e:
            return f"Erro: {str(e)}"

    def get_llm_response(self, prompt):
        # Prompt simplificado para melhor performance
        system_prompt = (
            "Você é um assistente de recrutamento. "
            "Estado atual: " + self.state + ". "
            "Última mensagem do usuário: " + prompt
        )
        
        # Se não houver resposta do modelo em tempo hábil, use respostas padrão
        try:
            command = ["ollama", "run", "llama2", system_prompt]
            response = self.run_command_with_timeout(command)
            
            # Se houver timeout ou erro, use respostas padrão baseadas no estado
            if "Tempo de resposta excedido" in response or "Erro" in response:
                return self.get_default_response()
            
            return response
        except Exception as e:
            return self.get_default_response()

    def get_default_response(self):
        """Retorna respostas padrão baseadas no estado atual"""
        responses = {
            "INITIAL": "Bem-vindo! Por favor, informe seu nome completo:",
            "WAITING_NAME": "Qual é seu telefone para contato?",
            "WAITING_PHONE": "Qual é sua formação acadêmica? (Formato: Instituição - Curso - Período)",
            "WAITING_EDUCATION": "Educação registrada. Você possui experiência profissional? (Sim/Não)",
            "WAITING_EXPERIENCE": "Por favor, informe sua experiência: Empresa - Cargo - Período - Descrição",
            "WAITING_MORE_EXPERIENCE": "Deseja adicionar mais uma experiência? (Sim/Não)",
            "SHOWING_RESUME": "Deseja ver vagas disponíveis? (Sim/Não)"
        }
        return responses.get(self.state, "Como posso ajudar?")

    def process_input(self, user_input):
        """Processa a entrada do usuário e atualiza o estado"""
        if self.state == "INITIAL":
            email = user_input.lower().strip()
            if '@' in email:
                if email not in self.candidates:
                    self.candidates[email] = Candidate(email=email)
                self.current_candidate = self.candidates[email]
                self.state = "WAITING_NAME"
                return "Bem-vindo! Por favor, informe seu nome completo:"
            return "Por favor, forneça um email válido."

        elif self.state == "WAITING_NAME":
            self.current_candidate.name = user_input
            self.state = "WAITING_PHONE"
            return "Qual é seu telefone para contato?"

        elif self.state == "WAITING_PHONE":
            self.current_candidate.phone = user_input
            self.state = "WAITING_EDUCATION"
            return "Qual é sua formação acadêmica? (Formato: Instituição - Curso - Período)"

        elif self.state == "WAITING_EDUCATION":
            try:
                parts = user_input.split('-')
                if len(parts) >= 3:
                    education = Education(
                        institution=parts[0].strip(),
                        course=parts[1].strip(),
                        period=parts[2].strip()
                    )
                    self.current_candidate.educations.append(education)
                    self.state = "WAITING_HAS_EXPERIENCE"
                    return "Educação registrada. Você possui experiência profissional? (Sim/Não)"
                return "Por favor, use o formato: Instituição - Curso - Período"
            except:
                return "Formato inválido. Use: Instituição - Curso - Período"

        return self.get_default_response()

    def get_response(self, user_input):
        """Método principal para processar entrada e retornar resposta"""
        # Primeiro tenta processar com lógica básica
        response = self.process_input(user_input)
        
        # Se não houver resposta da lógica básica, tenta usar o modelo
        if not response:
            response = self.get_llm_response(user_input)
        
        return response

def main():
    print("=== Sistema de Recrutamento com IA ===")
    print("Assistente: Olá! Sou seu assistente de recrutamento. Por favor, me informe seu email para começarmos:")
    
    chatbot = LLMRecruitmentChatbot()
    
    while True:
        user_input = input("\nVocê: ")
        if user_input.lower() in ['sair', 'exit']:
            print("Assistente: Até logo!")
            break
            
        response = chatbot.get_response(user_input)
        print(f"\nAssistente: {response}")

if __name__ == "__main__":
    main()