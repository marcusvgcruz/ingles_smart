# Guia completo: PostgreSQL local + deploy na Hostinger (VPS)

> **Deploy no Render (mais simples para começar):** veja **[RENDER.md](RENDER.md)**.  
> **Migrar SQLite → PostgreSQL:** veja **[MIGRAR_POSTGRES.md](MIGRAR_POSTGRES.md)**.

---

Este documento é um passo a passo do zero. O projeto **portal_escola** já lê o banco pelo arquivo `.env` (veja `.env.example`).

---

## Visão geral: onde cada coisa fica

Pense em **três camadas** separadas:

| Camada | O que é | Onde fica |
|--------|---------|-----------|
| **Código** | Python/Django (views, templates, lógica) | Pasta do projeto no seu PC ou no VPS |
| **Banco de dados** | PostgreSQL (tabelas, usuários, notas…) | Serviço rodando no PC (local) ou no VPS (produção) |
| **Arquivos enviados** | Fotos de perfil, áudios em `media/` | Pasta `media/` no disco (local ou VPS) |

O navegador **não** acessa o Postgres diretamente. O fluxo é:

```
Usuário → Nginx (porta 80/443) → Gunicorn (Django) → PostgreSQL
                ↓
         CSS/JS (staticfiles) e uploads (media)
```

**Importante:** na Hostinger, hospedagem compartilhada “só para site PHP” em geral **não roda Django**. Para este projeto você precisa de um **VPS** (máquina Linux com SSH). Você não “sobe a pasta do banco”; você sobe o **código**, instala o **PostgreSQL no servidor** (ou usa banco gerenciado) e configura o **`.env`** para o Django conectar.

---

# PARTE 1 — PostgreSQL no seu Windows (testar antes do deploy)

## 1.1 O que instalar

1. **PostgreSQL** — https://www.postgresql.org/download/windows/  
   - Use o instalador da EDB.  
   - Anote a **senha do usuário `postgres`**.  
   - Porta padrão: **5432**.  
   - Pode instalar o **pgAdmin** junto (interface oficial).

2. **DBeaver** (opcional, recomendado) — https://dbeaver.io/download/

3. **Driver Python** (na pasta do projeto, com venv ativo):

```powershell
cd "D:\Backups Projetos\portal_escola\portal_escola"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 1.2 Criar o banco de dados

Abra **pgAdmin** ou o **SQL Shell (psql)** que veio com o instalador.

Conecte como usuário `postgres` e execute:

```sql
CREATE DATABASE portal_escola;
```

(Opcional, mais seguro que usar `postgres` no dia a dia:)

```sql
CREATE USER portal_user WITH PASSWORD 'uma_senha_forte_aqui';
GRANT ALL PRIVILEGES ON DATABASE portal_escola TO portal_user;
```

No PostgreSQL 15+, pode ser necessário também:

```sql
\c portal_escola
GRANT ALL ON SCHEMA public TO portal_user;
```

## 1.3 Arquivo `.env` no projeto

Na pasta **`portal_escola`** (onde está o `manage.py`), copie o exemplo:

```powershell
copy .env.example .env
```

Edite `.env` para desenvolvimento com Postgres:

```env
DJANGO_SECRET_KEY=qualquer-chave-longa-para-testes-locais
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=postgresql
DB_NAME=portal_escola
DB_USER=postgres
DB_PASSWORD=SUA_SENHA_DO_INSTALADOR
DB_HOST=localhost
DB_PORT=5432
```

Para voltar ao **SQLite** temporariamente, remova ou comente a linha `DB_ENGINE=postgresql`.

## 1.4 Criar tabelas no Postgres

Com o venv ativo:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse http://127.0.0.1:8000/

## 1.5 Trazer dados do SQLite (se você já usava o projeto)

**Só faça isso se tinha dados importantes em `db.sqlite3`.**

```powershell
# Passo A — ainda no SQLite: comente DB_ENGINE no .env ou apague a linha
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > backup.json

# Passo B — ative de novo DB_ENGINE=postgresql no .env
python manage.py migrate
python manage.py loaddata backup.json
```

## 1.6 Conectar o DBeaver

1. **Database** → **New Database Connection** → **PostgreSQL**
2. Host: `localhost`
3. Port: `5432`
4. Database: `portal_escola`
5. Username / Password: iguais ao `.env`
6. **Test Connection** → **Finish**

Você verá tabelas como `accounts_aluno`, `auth_user`, etc. Para aprender, use o DBeaver em **leitura**; alterações manuais podem quebrar o Django.

## 1.7 Pasta `media/`

Uploads (avatar, áudios) ficam em `portal_escola/media/`. Isso **não** vai para dentro do Postgres — são arquivos no disco. No deploy, essa pasta precisa existir no servidor e o Nginx deve servir `/media/` (ver Parte 2).

---

# PARTE 2 — Deploy na Hostinger (VPS)

## 2.1 O que contratar

Na Hostinger, procure **VPS** (KVM), não apenas “hospedagem de sites”.

Sugestão inicial para este projeto:

- **SO:** Ubuntu 22.04 ou 24.04  
- **RAM:** 2 GB ou mais (confortável com Postgres + Django)  
- Você receberá: **IP do servidor**, usuário **root** (ou `ubuntu`) e senha/chave SSH  

Também precisa de um **domínio** (na Hostinger ou outro registrador) apontando para o IP do VPS (registro **A** `@` e `www` → IP do VPS).

## 2.2 Onde o banco fica no servidor

No cenário mais comum (tudo no mesmo VPS):

```
/var/lib/postgresql/   ← dados internos do Postgres (não mexa à mão)
```

Você só interage via:

- `psql` / comandos SQL  
- `python manage.py migrate`  
- DBeaver (conectando por **túnel SSH** — ver seção 2.12)

O Django em produção usa o mesmo `.env`, com `DB_HOST=localhost` se o Postgres estiver **na mesma máquina**.

## 2.3 Primeiro acesso SSH (do seu Windows)

PowerShell:

```powershell
ssh root@SEU_IP_DO_VPS
```

Aceite o fingerprint e digite a senha (ou use chave SSH se configurou).

Atualize o sistema:

```bash
apt update && apt upgrade -y
```

## 2.4 Instalar dependências no Ubuntu

```bash
apt install -y python3 python3-venv python3-pip \
  postgresql postgresql-contrib nginx git
```

> Se `python3-penv` falhar, use só `python3-venv`.

## 2.5 Configurar PostgreSQL no VPS

```bash
sudo -u postgres psql
```

Dentro do `psql`:

```sql
CREATE DATABASE portal_escola;
CREATE USER portal_user WITH PASSWORD 'SENHA_FORTE_PRODUCAO';
ALTER ROLE portal_user SET client_encoding TO 'utf8';
ALTER ROLE portal_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE portal_user SET timezone TO 'America/Sao_Paulo';
GRANT ALL PRIVILEGES ON DATABASE portal_escola TO portal_user;
\q
```

PostgreSQL 15+ no Ubuntu:

```bash
sudo -u postgres psql -d portal_escola -c "GRANT ALL ON SCHEMA public TO portal_user;"
```

## 2.6 Enviar o código para o servidor

**Opção A — Git (recomendado)**

No VPS:

```bash
mkdir -p /var/www
cd /var/www
git clone URL_DO_SEU_REPOSITORIO portal_escola
cd portal_escola/portal_escola
```

(Ajuste o caminho se o `manage.py` estiver em `portal_escola/portal_escola`.)

**Opção B — ZIP**

Compacte a pasta do projeto (sem `venv`, sem `db.sqlite3`, sem `.env`), envie com WinSCP/FileZilla para `/var/www/portal_escola` e descompacte.

## 2.7 Ambiente Python no VPS

```bash
cd /var/www/portal_escola/portal_escola
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2.8 Arquivo `.env` de produção

```bash
nano .env
```

Exemplo (ajuste domínio e senhas):

```env
DJANGO_SECRET_KEY=gere-uma-chave-aleatoria-longa
DEBUG=False
ALLOWED_HOSTS=seudominio.com.br,www.seudominio.com.br,SEU_IP_DO_VPS

DB_ENGINE=postgresql
DB_NAME=portal_escola
DB_USER=portal_user
DB_PASSWORD=SENHA_FORTE_PRODUCAO
DB_HOST=localhost
DB_PORT=5432

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DEFAULT_FROM_EMAIL=noreply@seudominio.com.br
EMAIL_HOST=smtp.hostinger.com
EMAIL_PORT=587
EMAIL_HOST_USER=seu-email@seudominio.com.br
EMAIL_HOST_PASSWORD=senha-do-email
EMAIL_USE_TLS=True
PORTAL_LOGIN_URL=https://seudominio.com.br/login/
```

Gere uma secret key no PC:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 2.9 Migrar banco e arquivos estáticos

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Copie a pasta **`media/`** do seu PC para o mesmo caminho no servidor (WinSCP), se já tiver uploads.

Permissões (usuário comum para rodar o app):

```bash
adduser --disabled-password --gecos "" django
chown -R django:django /var/www/portal_escola
```

## 2.10 Gunicorn (Django rodando o tempo todo)

Teste manual:

```bash
cd /var/www/portal_escola/portal_escola
source venv/bin/activate
gunicorn --bind 127.0.0.1:8001 portal_escola.wsgi:application
```

Se não der erro, crie o serviço systemd:

```bash
nano /etc/systemd/system/portal_escola.service
```

Conteúdo:

```ini
[Unit]
Description=Portal Escola Gunicorn
After=network.target

[Service]
User=django
Group=django
WorkingDirectory=/var/www/portal_escola/portal_escola
Environment="PATH=/var/www/portal_escola/portal_escola/venv/bin"
ExecStart=/var/www/portal_escola/portal_escola/venv/bin/gunicorn \
  --workers 3 \
  --bind unix:/var/www/portal_escola/portal_escola/portal.sock \
  portal_escola.wsgi:application

[Install]
WantedBy=multi-user.target
```

Ativar:

```bash
systemctl daemon-reload
systemctl enable portal_escola
systemctl start portal_escola
systemctl status portal_escola
```

## 2.11 Nginx (site público no ar)

```bash
nano /etc/nginx/sites-available/portal_escola
```

```nginx
server {
    listen 80;
    server_name seudominio.com.br www.seudominio.com.br;

    client_max_body_size 50M;

    location /static/ {
        alias /var/www/portal_escola/portal_escola/staticfiles/;
    }

    location /media/ {
        alias /var/www/portal_escola/portal_escola/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/portal_escola/portal_escola/portal.sock;
    }
}
```

Ativar site e reiniciar:

```bash
ln -s /etc/nginx/sites-available/portal_escola /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

Firewall (se usar UFW):

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

## 2.12 HTTPS (certificado gratuito)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d seudominio.com.br -d www.seudominio.com.br
```

Siga o assistente. O site passará a usar `https://`.

## 2.13 DBeaver apontando para o banco de produção

Por segurança, o Postgres no VPS **não** deve ficar aberto na internet. Use **túnel SSH** no DBeaver:

1. Na conexão PostgreSQL → aba **SSH**  
2. Host: IP do VPS, usuário `root` (ou seu usuário), senha/chave  
3. Aba **Main**: Host `localhost`, Port `5432`, Database `portal_escola`, User `portal_user`

Assim você gerencia o banco como se estivesse “dentro” do servidor.

## 2.14 Atualizar o site depois de mudanças no código

No VPS:

```bash
cd /var/www/portal_escola/portal_escola
source venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart portal_escola
```

---

# Checklist rápido

## Local (Windows)

- [ ] PostgreSQL instalado  
- [ ] Banco `portal_escola` criado  
- [ ] `.env` com `DB_ENGINE=postgresql`  
- [ ] `pip install -r requirements.txt`  
- [ ] `migrate` + `createsuperuser`  
- [ ] DBeaver conectado (opcional)  

## Produção (Hostinger VPS)

- [ ] VPS contratado (não só hospedagem PHP)  
- [ ] Domínio com DNS apontando para o IP  
- [ ] Postgres + usuário criados no servidor  
- [ ] Código em `/var/www/...`  
- [ ] `.env` com `DEBUG=False` e senhas fortes  
- [ ] `migrate`, `collectstatic`, pasta `media/`  
- [ ] systemd + Gunicorn  
- [ ] Nginx + Certbot (HTTPS)  

---

# Problemas comuns

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| `ModuleNotFoundError: psycopg` | Driver não instalado | `pip install psycopg[binary]` |
| `connection refused` | Postgres parado ou host/porta errados | `sudo systemctl status postgresql` |
| `password authentication failed` | Senha no `.env` diferente do Postgres | Alinhar senha ou `ALTER USER` |
| Site 502 Bad Gateway | Gunicorn parado | `systemctl status portal_escola` |
| CSS quebrado | Estáticos não coletados | `collectstatic` + bloco `location /static/` no Nginx |
| Imagens/áudios 404 | `media/` | Copiar pasta e configurar `location /media/` |
| `DisallowedHost` | Domínio não listado | Incluir em `ALLOWED_HOSTS` no `.env` |

---

# Ordem sugerida de estudo

1. Concluir **Parte 1** inteira no Windows.  
2. Usar o portal alguns dias no Postgres local.  
3. Contratar VPS e seguir **Parte 2** em um fim de semana.  
4. Só depois apontar o domínio real dos alunos/professores.

Se quiser, no próximo passo podemos fazer juntos a **Parte 1** comando por comando (você cola os erros que aparecerem) ou revisar o plano da Hostinger que você está considerando comprar.
