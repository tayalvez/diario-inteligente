# Deploy na nuvem (Render)

Este projeto já está preparado para subir como **um único serviço**:
- Backend FastAPI
- Frontend Angular compilado para `app/static`
- Banco SQLite persistido em disco do Render (`/app/data`)

## 1) Subir código para o GitHub

No diretório do projeto:

```bash
git add .
git commit -m "configura deploy em nuvem com docker e render"
git push
```

## 2) Criar o serviço no Render

1. Acesse [https://render.com](https://render.com) e conecte seu GitHub.
2. Clique em **New +** → **Blueprint**.
3. Selecione o repositório deste projeto.
4. O Render vai ler o arquivo `render.yaml` automaticamente.
5. Confirme a criação.

## 3) Aguardar build e deploy

O Render vai:
- construir a imagem com `Dockerfile`
- compilar o Angular
- iniciar o FastAPI

Quando finalizar, você receberá uma URL pública, por exemplo:

`https://diario-de-eventos.onrender.com`

## 4) Acessar no celular

Abra essa URL no navegador do celular.

## Observações importantes

- **Persistência dos dados**: o SQLite fica em `/app/data` e usa disco persistente do Render.
- **Plano free**: pode hibernar após inatividade; o primeiro acesso pode demorar alguns segundos.
- **Modelo de embedding**: se quiser usar embeddings completos em produção, garanta que o modelo esteja disponível em `models/` ou configure variáveis de ambiente conforme `app/ml/nlp.py`.
