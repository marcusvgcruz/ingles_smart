# 🎓 Inglês Smart — Sistema de Gestão Escolar & Plataforma de Ensino

![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-Ready-5A0FC8?style=for-the-badge&logo=pwa&logoColor=white)
![Deploy](https://img.shields.io/badge/Deploy-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)

> **Inglês Smart** é uma solução web completa (SaaS / Portal de Ensino) desenvolvida para a gestão administrativa, acadêmica e pedagógica de escolas de idiomas. O sistema integra controle de turmas, gestão financeira, gamificação, controle de presenças/reposições e um feed interativo de conteúdos.

---

## 📸 Demonstração & Recursos Principais

### 🚀 Funcionalidades para Administradores & Professores
- 👥 **Gestão de Alunos & Professores**: Cadastro, perfis detalhados, controle de acessos e primeiro acesso com troca de senha obrigatória.
- 📅 **Agendamento & Turmas**: Controle de agenda diária/mensal, horários de aula, períodos bloqueados e controle de turmas.
- 📝 **Presença & Reposições**: Chamada online, agendamento automatizado de aulas de reposição e histórico por aluno.
- 📊 **Avaliações & Desempenho**: Sistema de avaliações por competência/nível com relatórios completos e prontos para impressão.
- 💰 **Gestão Financeira & Contratos**: Controle de mensalidades, histórico de entradas financeiras e gestão de contratos.
- 📢 **Feed de Avisos & Material Pedagógico**: Publicação de avisos com imagens/anexos e estratégias de estudo contendo áudios e arquivos PDF.

### 🎮 Funcionalidades para Alunos (Portal do Aluno & PWA)
- 🏆 **Gamificação**: Desafios, pontuação e ranking para engajamento no aprendizado.
- 🎧 **Central de Estratégias**: Acesso a materiais em PDF e players de áudio integrados (`MP3`).
- 📲 **PWA (Progressive Web App)**: Instalável em dispositivos móveis (Android/iOS) com suporte offline básico e navegação responsiva.

---

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.12, Django 6.0, Gunicorn, WhiteNoise, `dj-database-url`.
- **Frontend**: HTML5, CSS3 Custom, JavaScript Vanilla, Bootstrap, CKEditor, Select2.
- **Banco de Dados**: PostgreSQL (Produção) / SQLite (Desenvolvimento).
- **Armazenamento de Mídia**: AWS S3 / Cloudinary (Suporte configurável).
- **Hospedagem & CI/CD**: Render.com com deploy automatizado via `render.yaml`.

---

## 📁 Arquitetura da Aplicação

```text
ingles_smart/
├── ingles_smart/              # Projeto Django (Settings, URLs, WSGI, ASGI)
│   ├── accounts/              # App Principal (Models, Views, Forms, Signals, Templates)
│   │   ├── static/            # CSS, JS, Ícones PWA, Select2
│   │   └── templates/         # Interface Web (HTML/Jinja)
│   ├── templates/             # Templates globais
│   ├── build.sh               # Script de build para Render.com
│   ├── start.sh               # Script de inicialização (Migrate + Gunicorn)
│   └── manage.py              # CLI do Django
├── render.yaml                # Infraestrutura como Código (Render Blueprint)
├── DEPLOY.md                  # Manual completo de Deploy Nginx/Systemd/VPS
├── RENDER.md                  # Guia de Deploy no Render.com
└── MIGRAR_POSTGRES.md         # Guia de migração SQLite -> PostgreSQL
```

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- Python 3.12+ instalados
- Git

### Passo a Passo

1. **Clonar o repositório**:
   ```bash
   git clone https://github.com/marcusvgcruz/ingles_smart.git
   cd ingles_smart
   ```

2. **Criar e ativar o ambiente virtual**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instalar as dependências**:
   ```bash
   pip install -r ingles_smart/requirements.txt
   ```

4. **Configurar as Variáveis de Ambiente**:
   Copie o arquivo `.env.example` para `.env` dentro da pasta `ingles_smart/`:
   ```bash
   cp ingles_smart/.env.example ingles_smart/.env
   ```

5. **Executar as migrações do banco de dados**:
   ```bash
   cd ingles_smart
   python manage.py migrate
   ```

6. **Criar um Superusuário (Admin)**:
   ```bash
   python manage.py createsuperuser
   ```

7. **Iniciar o servidor de desenvolvimento**:
   ```bash
   python manage.py runserver
   ```
   Acesse a aplicação no navegador em `http://127.0.0.1:8000/`.

---

## 🌐 Deploy em Produção

O projeto conta com infraestrutura como código pré-configurada para o **Render.com**:
- Blueprint pronto através do arquivo `render.yaml`.
- Build automatizado executando `collectstatic` e `migrate`.
- Documentações completas incluídas no repositório:
  - 📖 [Guia de Deploy no Render.com](RENDER.md)
  - 📖 [Guia de Migração SQLite → PostgreSQL](MIGRAR_POSTGRES.md)
  - 📖 [Manual de Deploy VPS (Nginx + Gunicorn)](DEPLOY.md)

---

## 📄 Licença & Autor

Desenvolvido por **Marcus Vinícius** 👋

- **GitHub**: [@marcusvgcruz](https://github.com/marcusvgcruz)
- **Projeto**: Criado como solução real de gestão e exibido como projeto de portfólio.
