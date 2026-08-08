# Migrar de SQLite para PostgreSQL

Siga na ordem. Faça primeiro **no seu Windows**; depois use o mesmo backup no Render se quiser.

---

## Parte A — PostgreSQL no Windows

### A1. Instalar PostgreSQL

1. https://www.postgresql.org/download/windows/
2. Instale com porta **5432**
3. Defina senha do usuário **`postgres`** e anote

### A2. Criar o banco

Abra **pgAdmin** (vem com o instalador) ou **SQL Shell (psql)**:

```sql
CREATE DATABASE ingles_smart;
```

### A3. Dependências Python

```powershell
cd "D:\Projetos\ingles_smart"
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Parte B — Exportar dados do SQLite

Enquanto ainda usa SQLite, o `.env` **não** pode ter `DB_ENGINE=postgresql` nem `DATABASE_URL`.

1. Se existir `.env`, abra e **comente ou apague** as linhas `DB_ENGINE`, `DB_*` e `DATABASE_URL`.

2. Confirme que existe `db.sqlite3` na pasta do `manage.py`.

3. Exporte:

```powershell
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > backup.json
```

Se der erro de encoding no Windows:

```powershell
$env:PYTHONUTF8=1
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > backup.json
```

Guarde `backup.json` — é a cópia dos seus dados.

---

## Parte C — Conectar ao PostgreSQL local

1. Copie o exemplo de ambiente:

```powershell
copy .env.example .env
```

2. Edite `.env` e **descomente** a opção B:

```env
DB_ENGINE=postgresql
DB_NAME=ingles_smart
DB_USER=postgres
DB_PASSWORD=SUA_SENHA_DO_INSTALADOR
DB_HOST=localhost
DB_PORT=5432
```

3. Crie tabelas vazias no Postgres:

```powershell
python manage.py migrate
```

4. Importe os dados:

```powershell
python manage.py loaddata backup.json
```

5. Teste:

```powershell
python manage.py runserver
```

Acesse http://127.0.0.1:8000/ e faça login com um usuário que já existia.

6. (Opcional) Novo superusuário se precisar:

```powershell
python manage.py createsuperuser
```

---

## Parte D — Enviar dados para o PostgreSQL do Render

O banco do Render começa **vazio** após o primeiro deploy. Para levar os dados do PC:

### D1. Deploy no Render concluído

Siga o `RENDER.md` até o Web Service estar **Live**.

### D2. Importar pelo Shell do Render

1. No painel Render → seu **Web Service** → **Shell**
2. O Shell já tem `DATABASE_URL` configurado.

No seu PC, envie o backup (se o arquivo for pequeno, pode colar em partes; para arquivos grandes use outra abordagem abaixo).

**Método simples (arquivo pequeno):**

1. No PC, abra `backup.json`
2. No Shell do Render:

```bash
cat > backup.json
```

3. Cole o conteúdo do JSON, Enter, depois **Ctrl+D** para fechar.

4. Importe:

```bash
python manage.py loaddata backup.json
```

**Método alternativo (recomendado se `backup.json` for grande):**

1. Suba `backup.json` para um repositório Git temporário ou use `scp`/ferramenta de upload
2. No Shell: baixe o arquivo e rode `loaddata`

### D3. Pasta `media/`

O `loaddata` **não** copia arquivos de imagem/áudio. Copie a pasta `media/` do PC:

- Via Git (se não estiver no `.gitignore` para esses arquivos — hoje `media/` pode estar fora do repo)
- Ou upload manual pelo admin após o deploy

---

## Parte E — Começar do zero no Postgres (sem migrar SQLite)

Se não precisa dos dados antigos:

1. Configure Postgres (local ou Render)
2. Apenas:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

No Render, o `build.sh` já roda `migrate`; você só faz `createsuperuser` no Shell.

---

## Como saber qual banco está em uso?

No Shell Python:

```powershell
python manage.py shell
```

```python
from django.conf import settings
print(settings.DATABASES["default"]["ENGINE"])
```

- `...sqlite3` → SQLite  
- `...postgresql` → PostgreSQL  

---

## Erros frequentes

| Mensagem | O que fazer |
|----------|-------------|
| `ModuleNotFoundError: psycopg` | `pip install -r requirements.txt` |
| `password authentication failed` | Senha no `.env` diferente do Postgres |
| `database "ingles_smart" does not exist` | Rode `CREATE DATABASE ingles_smart;` |
| `IntegrityError` no loaddata | Banco não estava vazio; use DB novo ou `flush` (apaga tudo!) |
| `No such file: backup.json` | Rode o comando na pasta do `manage.py` |

---

## Checklist

- [ ] Postgres instalado e banco `ingles_smart` criado  
- [ ] `backup.json` gerado do SQLite  
- [ ] `.env` com `DB_ENGINE=postgresql`  
- [ ] `migrate` + `loaddata` local OK  
- [ ] Render deploy OK  
- [ ] `loaddata` no Render (se quiser os mesmos dados)  
- [ ] `createsuperuser` no Render (se começou do zero)  
- [ ] `media/` copiada se tiver uploads importantes  
