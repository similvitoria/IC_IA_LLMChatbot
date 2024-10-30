import streamlit as st
import openai
import json
import pandas as pd
from datetime import datetime
from config import OPENAI_API_KEY

class RecruitmentChatbot:
    def __init__(self):
        # Configura a API do OpenAI
        openai.api_key = OPENAI_API_KEY
        
        # Base de vagas disponíveis (exemplo)
        self.available_positions = {
            "dev_backend": {
                "title": "Desenvolvedor Backend Python",
                "requirements": ["Python", "Django/Flask", "SQL", "Git"],
                "level": "Pleno",
                "description": "Desenvolvimento de APIs e microsserviços"
            },
            "dev_frontend": {
                "title": "Desenvolvedor Frontend",
                "requirements": ["React", "JavaScript", "HTML/CSS"],
                "level": "Júnior",
                "description": "Desenvolvimento de interfaces web responsivas"
            }
        }
        
        # Estado da conversa
        self.conversation_state = "initial"
        self.candidate_info = {}
        self.conversation_history = []

    def get_chatgpt_response(self, prompt, temperature=0.7):
        """Obtém resposta do ChatGPT"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Erro ao chamar ChatGPT: {e}")
            return None

    def extract_cv_info(self, text):
        """Extrai informações estruturadas do CV usando ChatGPT"""
        prompt = f"""
        Analise o CV a seguir e extraia as informações em formato JSON com as seguintes chaves:
        - nome
        - email
        - telefone
        - experiencia (lista de dicionários com: empresa, cargo, periodo)
        - habilidades (lista de tecnologias e competências)
        - formacao (lista de dicionários com: curso, instituicao, ano)
        
        Mantenha apenas as informações mais relevantes e retorne APENAS o JSON, sem comentários adicionais.
        
        CV: {text}
        """
        
        response = self.get_chatgpt_response(prompt, temperature=0.3)
        try:
            return json.loads(response)
        except:
            return None

    def analyze_fit(self, candidate_skills, position):
        """Analisa adequação do candidato para a vaga usando ChatGPT"""
        prompt = f"""
        Analise a compatibilidade entre o candidato e a vaga com base nas informações abaixo.
        Retorne um JSON com as chaves: match_percentage (0-100), reasons_for (lista), reasons_against (lista)

        Requisitos da vaga:
        {json.dumps(position, indent=2)}

        Habilidades do candidato:
        {json.dumps(candidate_skills, indent=2)}
        """

        response = self.get_chatgpt_response(prompt, temperature=0.3)
        try:
            return json.loads(response)
        except:
            return {
                "match_percentage": 0,
                "reasons_for": [],
                "reasons_against": ["Erro na análise"]
            }

    def suggest_positions(self):
        """Sugere vagas compatíveis com o perfil do candidato"""
        matches = []
        
        for pos_id, position in self.available_positions.items():
            analysis = self.analyze_fit(self.candidate_info["habilidades"], position)
            if analysis["match_percentage"] >= 60:
                matches.append({
                    **position,
                    "match": analysis
                })
        
        return sorted(matches, key=lambda x: x["match"]["match_percentage"], reverse=True)

    def process_message(self, message):
        """Processa a mensagem do usuário e retorna uma resposta apropriada"""
        # Adiciona mensagem ao histórico
        self.conversation_history.append({"role": "user", "content": message})
        
        if self.conversation_state == "initial":
            self.conversation_state = "waiting_cv"
            response = """
            Olá! Sou o assistente de recrutamento virtual. 
            Por favor, me conte sobre sua experiência profissional, formação e habilidades.
            Você pode compartilhar seu CV de forma livre, como se estivesse conversando comigo.
            """
            
        elif self.conversation_state == "waiting_cv":
            cv_info = self.extract_cv_info(message)
            
            if cv_info:
                self.candidate_info = cv_info
                self.conversation_state = "cv_received"
                
                matches = self.suggest_positions()
                
                if matches:
                    response = f"""
                    Obrigado, {cv_info['nome']}! Analisei seu perfil e encontrei algumas vagas interessantes:
                    
                    """
                    
                    for i, match in enumerate(matches, 1):
                        response += f"\n{i}. {match['title']} ({match['level']}) - {match['match']['match_percentage']}% de compatibilidade"
                        response += f"\n   Descrição: {match['description']}"
                        response += "\n   Pontos positivos:"
                        for reason in match['match']['reasons_for'][:2]:
                            response += f"\n   - {reason}"
                        
                    response += "\n\nGostaria de se candidatar a alguma dessas vagas? Digite o número da vaga ou 'não' para encerrar."
                else:
                    response = """
                    Obrigado pelo seu CV! No momento não temos vagas que correspondam ao seu perfil,
                    mas manteremos seus dados em nosso banco de talentos. 
                    Deseja receber notificações sobre futuras vagas compatíveis?
                    """
            else:
                response = """
                Desculpe, tive dificuldade em processar seu CV. Pode tentar enviar novamente?
                Por favor, inclua informações sobre:
                - Sua formação acadêmica
                - Experiências profissionais
                - Habilidades técnicas
                - Dados de contato
                """
                
        elif self.conversation_state == "cv_received":
            if message.lower() == "não":
                response = """
                Ok! Seus dados foram salvos em nosso banco de talentos.
                Quando surgirem vagas compatíveis, entraremos em contato através do email cadastrado.
                Boa sorte em sua jornada profissional!
                """
                self.conversation_state = "finished"
            else:
                try:
                    position_index = int(message) - 1
                    matches = self.suggest_positions()
                    selected_position = matches[position_index]
                    
                    self.save_application(selected_position["title"])
                    
                    response = f"""
                    Ótimo! Sua candidatura para a vaga de {selected_position['title']} foi registrada com sucesso.
                    
                    Próximos passos:
                    1. Você receberá um email de confirmação em {self.candidate_info['email']}
                    2. Nossa equipe de RH fará uma análise detalhada do seu perfil
                    3. Em caso de compatibilidade, entraremos em contato para agendar uma entrevista
                    
                    Boa sorte no processo seletivo!
                    """
                    self.conversation_state = "finished"
                except:
                    response = "Por favor, digite apenas o número da vaga ou 'não' para encerrar."
        
        else:  # finished
            response = "Posso ajudar com mais alguma coisa?"
            self.conversation_state = "initial"
        
        # Adiciona resposta ao histórico
        self.conversation_history.append({"role": "assistant", "content": response})
        return response

    def save_application(self, position):
        """Salva a candidatura em um CSV"""
        application = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "position": position,
            "candidate_name": self.candidate_info["nome"],
            "candidate_email": self.candidate_info["email"],
            "candidate_phone": self.candidate_info["telefone"]
        }
        
        df = pd.DataFrame([application])
        df.to_csv("applications.csv", mode='a', header=False, index=False)

# Interface Streamlit
def main():
    st.title("Chatbot de Recrutamento")
    
    # Inicializa o estado da sessão
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = RecruitmentChatbot()
        st.session_state.messages = []
    
    # Mostra histórico de mensagens
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Digite sua mensagem..."):
        # Adiciona mensagem do usuário ao histórico
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Processa resposta do chatbot
        response = st.session_state.chatbot.process_message(prompt)
        
        # Adiciona resposta do chatbot ao histórico
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Recarrega a página para mostrar novas mensagens

if __name__ == "__main__":
    main()