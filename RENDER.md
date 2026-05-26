# Deploy no Render.com

O projeto está preparado para o [Render](https://render.com): PostgreSQL gerenciado, build automático e Gunicorn.

## O que o Render faz por você

| Peça | No Render |
|------|-----------|
| **Código** | Conecta ao GitHub/GitLab; a cada push faz deploy |
| **Banco PostgreSQL** | Serviço separado; URL em `DATABASE_URL` |
| **App Django** | Web Service roda `gunicorn` |
| **HTTPS** | Certificado automático em `*.onrender.com` |

Você **não** envia pasta de banco. O Render cria o Postgres na nuvem e o Django conecta via `DATABASE_URL`.

## Arquivos adicionados ao projeto

| Arquivo | Função |
|---------|--------|
| `render.yaml` | Blueprint (cria Web + Postgres de uma vez) |
| `portal_escola/build.sh` | Instala deps, `collectstatic`, `migrate` |
| `requirements.txt` | `gunicorn`, `psycopg`, `whitenoise`, `dj-database-url` |
| `settings.py` | Lê `DATABASE_URL`, WhiteNoise, host do Render |

## Passo a passo no Render (primeira vez)

### 1. Código no GitHub

O Render precisa do código em um repositório Git (GitHub é o mais comum).

```powershell
cd "D:\Backups Projetos\portal_escola"
git add .
git commit -m "Preparar deploy Render"
git push origin main
```

### 2. Conta no Render

1. Acesse https://render.com e crie conta (pode usar login GitHub).
2. **New** → **PostgreSQL**
   - Name: `portal-escola-db`
   - Plan: **Free** (para testes; tem limites de espaço/tempo)
   - Region: perto de você (ex.: Oregon)
   - Crie o banco e **anote** — não precisa copiar senha manualmente depois.

### 3. Web Service (aplicação Django)

**Opção A — Blueprint (mais fácil)**

1. **New** → **Blueprint**
2. Conecte o repositório `portal_escola`
3. O Render lê o `render.yaml` na raiz e propõe Web + Database
4. Confirme o deploy

**Opção B — Manual**

1. **New** → **Web Service** → conecte o repo
2. Configurações:

| Campo | Valor |
|-------|--------|
| **Root Directory** | `portal_escola` |
| **Runtime** | Python 3 |
| **Build Command** | `bash ./build.sh` |
| **Start Command** | `bash ./start.sh` |

3. **Environment** → adicione variáveis:

| Key | Value |
|-----|--------|
| `DJANGO_SECRET_KEY` | gere uma chave longa (ver abaixo) |
| `DEBUG` | `False` |
| `PYTHON_VERSION` | `3.12.3` |
| `SECURE_SSL_REDIRECT` | `False` |

4. **Add Database** → escolha o Postgres `portal-escola-db` criado antes  
   → o Render define `DATABASE_URL` sozinho.

5. **Create Web Service** e aguarde o build (5–15 min na primeira vez).

### 4. Gerar SECRET_KEY

No seu PC, na pasta do `manage.py`:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Cole o resultado em `DJANGO_SECRET_KEY` no painel do Render.

### 5. Criar usuário admin no Render (plano Free — sem Shell)

No plano **Free**, a aba **Shell** exige upgrade. Use variáveis de ambiente; o `build.sh` roda `ensure_superuser` a cada deploy.

No Web Service → **Environment**, adicione:

| Key | Value |
|-----|--------|
| `DJANGO_SUPERUSER_USERNAME` | ex.: `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | senha forte |
| `DJANGO_SUPERUSER_EMAIL` | e-mail do admin (opcional) |

Salve → redeploy. Nos **Build Logs**, procure por `Superusuário 'admin' criado.`

Faça login em `https://SEU-SERVICO.onrender.com/login/` com esse usuário e senha.

**Esqueceu a senha?** Altere `DJANGO_SUPERUSER_PASSWORD` no Environment e salve (redeploy atualiza a senha).

**Plano pago:** também pode usar Shell → `python manage.py createsuperuser`.

### 6. Acessar o portal

URL tipo: `https://portal-escola-xxxx.onrender.com`

Login admin: `/admin/`

### 7. Variáveis extras (e-mail e escola)

No painel **Environment** do Web Service:

```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=...
PORTAL_LOGIN_URL=https://SEU-SERVICO.onrender.com/login/
SCHOOL_DISPLAY_NAME=Nome da Escola
```

Após alterar variáveis, o Render faz **redeploy** automático.

### 8. Domínio próprio (opcional)

Web Service → **Settings** → **Custom Domain** → siga o DNS da escola.

Adicione em Environment:

```
ALLOWED_HOSTS=portal.suaescola.com.br,SEU-SERVICO.onrender.com
CSRF_TRUSTED_ORIGINS=https://portal.suaescola.com.br
```

## Uploads (`media/`) — importante

No plano free, o disco do container é **efêmero**: fotos e áudios enviados pelo site **podem sumir** após um redeploy.

Para produção séria com uploads:

- [Render Disk](https://render.com/docs/disks) (disco persistente no mesmo serviço), ou
- Armazenamento em nuvem (S3, Cloudinary) — evolução futura.

Para o primeiro teste, você pode copiar a pasta `media/` do PC via **Shell** + SCP, ou fazer upload de novo pelo admin.

## Atualizar o site depois

1. `git push` na branch conectada ao Render  
2. Build roda `build.sh` → `migrate` + `collectstatic`  
3. Site reinicia sozinho

## Problemas comuns

| Erro | Solução |
|------|---------|
| Build falha em `collectstatic` | Veja logs; confira `STATIC_ROOT` |
| `DisallowedHost` | Inclua `*.onrender.com` via `RENDER_EXTERNAL_HOSTNAME` (automático) ou `ALLOWED_HOSTS` |
| 502 / app não sobe | Logs → **Events**; teste `gunicorn portal_escola.wsgi:application` no Shell |
| Banco vazio após deploy | Normal na primeira vez; `createsuperuser` ou importe dados (ver `MIGRAR_POSTGRES.md`) |
| CSRF ao logar | Adicione `CSRF_TRUSTED_ORIGINS` com `https://` do seu domínio |

## Migração SQLite → PostgreSQL

Guia detalhado no arquivo **`MIGRAR_POSTGRES.md`** (local e dados para o Render).
