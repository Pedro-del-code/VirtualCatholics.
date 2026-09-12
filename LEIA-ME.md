# Fé & Caminho — Passo 4: recuperação de senha completa (tela de login pronta)

## Correção importante (deploy falhando)
Se o deploy no Render falhou com um erro tipo `ImportError ... psycopg2 ... undefined symbol: _PyInterpreterState_Get`,
é porque o Render escolheu automaticamente uma versão muito nova do Python (3.14), incompatível com o driver do Postgres.
Este pacote já vem com a correção: um arquivo `runtime.txt` fixando o Python em `3.11.9`. Basta atualizar o repositório
no GitHub com estes arquivos e o Render vai sincronizar e rodar o deploy de novo sozinho (você viu essa mensagem:
"All future updates to your Blueprint file will be synced automatically").

## O que mudou desde o passo 3
- **E-mail de recuperação de verdade**, enviado via [Resend](https://resend.com) (tem plano gratuito).
- **Tela de "Criar nova senha"** (`/redefinir-senha?token=...`), que é a página que abre a partir do link do e-mail.
- Nova rota de API `/api/redefinir-senha`, que confere o token (validade de 1 hora, uso único) e troca a senha.
- CSS compartilhado movido para `static/css/estilo.css`, usado tanto na tela de login quanto na de redefinir senha (evita duplicar código).

Com isso, o fluxo de login/cadastro/recuperação está **completo de ponta a ponta**: criar conta → entrar → esquecer a senha → receber e-mail → redefinir → entrar de novo.

## Estrutura da pasta
```
app.py                        -> backend Flask (rotas + modelos + envio de e-mail)
requirements.txt              -> dependências Python
render.yaml                   -> cria o Web Service + Postgres no Render automaticamente
templates/index.html          -> tela de login / criar conta / recuperar acesso
templates/redefinir-senha.html -> tela de criar nova senha (aberta a partir do e-mail)
static/css/estilo.css         -> visual compartilhado entre as duas telas
static/assets/                -> imagem de fundo (São Miguel Arcanjo)
```

## Configurando o envio de e-mail (Resend)
1. Crie uma conta gratuita em https://resend.com
2. Gere uma **API Key** no painel do Resend.
3. No Render, no seu Web Service, vá em **Environment** e defina:
   - `RESEND_API_KEY` → a chave gerada
   - `APP_URL` → a URL pública do seu site no Render (ex: `https://fe-e-caminho.onrender.com`), para o link do e-mail apontar pro lugar certo
   - `EMAIL_REMETENTE` → já vem com `onboarding@resend.dev` (funciona para testes; para enviar do seu próprio domínio, verifique o domínio no Resend e troque esse valor)

Sem essas variáveis configuradas (por exemplo, rodando na sua máquina), o link de recuperação só aparece no console/log — não trava o app, só não manda e-mail de verdade.

## Rodando localmente
```bash
pip install -r requirements.txt
python app.py
```
Acesse http://localhost:5000

## Publicando no Render.com
1. Suba esta pasta para um repositório no GitHub.
2. No Render: **New > Blueprint** → conecte o repositório → "Apply". Isso cria o Web Service e o banco Postgres, já conectados.
3. Depois do primeiro deploy, configure `RESEND_API_KEY` e `APP_URL` manualmente (o Render não pode gerar isso sozinho, veja acima).

## O que já está pronto (fim do trabalho de hoje)
- Tela de login, criar conta e recuperar acesso — visual final, mobile-first.
- Cadastro e login reais, com senha protegida (hash) no Postgres.
- Recuperação de senha ponta a ponta: pedir → e-mail → redefinir → entrar com a senha nova.

## Próximos passos (começar amanhã)
1. Construir a página inicial de verdade: orações, leituras do dia, santo do dia — o conteúdo católico em si.
2. Decidir a navegação principal do app (menu, seções, categorias de conteúdo).
3. Perfil do usuário (nome, foto, preferências, favoritos salvos).
