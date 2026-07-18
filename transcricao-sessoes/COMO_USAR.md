# 🎙️ Transcrever Sessões da Câmara — passo a passo

Este robô transcreve as **gravações de sessão** que estão no seu Google Drive.
Ele lê o áudio, transforma a fala em texto (com o Whisper, que é ótimo em
português) e salva a transcrição de volta no Drive — pronta para virar ata.

Você **não precisa saber programar**. É só seguir os passos abaixo.

---

## 1. Abrir o robô no Google Colab

1. Entre em **https://colab.research.google.com**
2. Clique em **Arquivo → Fazer upload de notebook**
3. Envie o arquivo **`Transcrever_Sessao_CMDC.ipynb`** (o que está nesta pasta).

> O Colab é gratuito e roda no navegador. Nada é instalado no seu computador.

## 2. Ligar a GPU (deixa muito mais rápido e é de graça)

No menu de cima: **Ambiente de execução → Alterar o tipo de ambiente de
execução → Acelerador de hardware: GPU (T4) → Salvar**.

## 3. Rodar as células, uma por uma

Cada bloco tem um botão ▶ à esquerda. Clique de cima para baixo, esperando
cada um terminar antes de ir para o próximo:

| Célula | O que faz |
|--------|-----------|
| 1 | Confere se a GPU está ligada |
| 2 | Conecta ao seu Google Drive (vai pedir permissão — clique em *Permitir*) |
| 3 | Instala o Whisper |
| 4 | **Aqui você escolhe o áudio** — escreva um pedaço do nome do arquivo |
| 5 | Transcreve e salva no Drive |

Na **célula 4**, no lugar de `NOME_DO_ARQUIVO`, escreva um pedaço do nome do
arquivo da sessão. Exemplos:

```python
NOME_DO_ARQUIVO = '10-03-2026'                    # sessão de 10/03/2026
NOME_DO_ARQUIVO = 'Sessão_Ordinária_22_03_2022'   # sessão de 22/03/2022
```

## 4. Pegar a transcrição

Quando a célula 5 terminar, a transcrição é salva **no seu Drive, na mesma
pasta do áudio**, em três formatos:

- `... - transcricao.docx` — para abrir no Word e revisar
- `... - transcricao.txt` — texto puro
- `... - transcricao.md` — com marcação de tempo (útil para achar trechos)

---

## Perguntas comuns

**Quanto tempo demora?**
Uma sessão de ~2 horas leva cerca de 10 a 25 minutos com a GPU ligada.

**Ficou lento / deu erro de memória.**
Na célula 4, troque `MODELO = 'large-v3'` por `'medium'` ou `'small'`. Fica
mais rápido (a qualidade cai um pouquinho, mas continua boa).

**A transcrição erra alguns nomes de vereadores.**
É normal em qualquer transcrição automática. O texto sai muito bom, mas
sempre confira os nomes próprios na revisão — foi para isso que existe o
Setor de Atas. 🙂

**Precisa fazer tudo de novo para outra sessão?**
Não. É só voltar na **célula 4**, trocar o nome do arquivo, e rodar a **4** e
a **5** de novo.

---

## Depois da transcrição: virar ata

Com o `.docx` transcrito em mãos, você pode usar as suas skills de ata no
Claude (revisão, padronização e formatação) para transformar a transcrição
bruta na versão final do Setor de Atas.
