"""Gera o notebook Colab 'Transcrever_Sessao_CMDC.ipynb'.
Executado uma vez para produzir o .ipynb; não precisa rodar de novo."""
import json

def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": [l + "\n" for l in lines]}

def code(*lines):
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": [l + "\n" for l in lines]}

cells = []

cells.append(md(
"# 🎙️ Transcrever Sessão — Câmara Municipal de Duque de Caxias",
"",
"Este notebook pega uma **gravação de sessão** que está no seu Google Drive,",
"transcreve a fala em texto usando o **Whisper** (ótimo em português) e",
"salva a transcrição de volta no Drive, pronta para virar ata.",
"",
"## Como usar (passo a passo)",
"1. No menu de cima, clique em **Ambiente de execução → Alterar o tipo de ambiente de execução** e escolha **GPU** (T4). É de graça e deixa tudo muito mais rápido.",
"2. Rode as células **uma por uma**, de cima para baixo, clicando no ▶ à esquerda de cada uma.",
"3. Na célula de **CONFIGURAÇÃO**, escreva um pedaço do nome do arquivo da sessão (ex.: `10-03-2026`).",
"4. Espere terminar. A transcrição aparece na tela e é salva no seu Drive, na mesma pasta do áudio.",
"",
"> Não precisa saber programar. É só rodar as células na ordem.",
))

cells.append(md("## 1. Verificar se a GPU está ligada", "",
"Se aparecer uma tabela com `Tesla T4`, está tudo certo. Se der erro, volte no passo 1 acima (ligar a GPU) — mesmo sem GPU funciona, só fica mais lento."))
cells.append(code(
"!nvidia-smi || echo 'Sem GPU — vai funcionar mesmo assim, porém mais devagar.'",
))

cells.append(md("## 2. Conectar ao seu Google Drive", "",
"Vai abrir uma janelinha pedindo permissão. Escolha sua conta Google e clique em **Permitir**."))
cells.append(code(
"from google.colab import drive",
"drive.mount('/content/drive')",
"print('\\nDrive conectado! Seus arquivos estão em: /content/drive/MyDrive')",
))

cells.append(md("## 3. Instalar o Whisper", "",
"Só clique em ▶ e espere (~1 a 2 min na primeira vez)."))
cells.append(code(
"!pip install -q faster-whisper python-docx",
"print('Pronto!')",
))

cells.append(md("## 4. CONFIGURAÇÃO — escolha o áudio", "",
"Escreva entre aspas um pedaço do **nome do arquivo** da sessão que você quer transcrever.",
"O notebook procura sozinho no seu Drive inteiro.",
"",
"Exemplos de nome: `10-03-2026`, `Sessão_Ordinária_22_03_2022`, `14-04-2026`."))
cells.append(code(
"# ===================== MUDE AQUI =====================",
"NOME_DO_ARQUIVO = '10-03-2026'   # <-- escreva um pedaço do nome do áudio",
"",
"# Opções (pode deixar como está):",
"MODELO   = 'large-v3'  # melhor qualidade. Se ficar lento, troque por 'medium' ou 'small'.",
"IDIOMA   = 'pt'        # português",
"# =====================================================",
"",
"import glob, os",
"padrao = f'/content/drive/MyDrive/**/*{NOME_DO_ARQUIVO}*'",
"achados = [f for f in glob.glob(padrao, recursive=True)",
"           if f.lower().endswith(('.mp3', '.wav', '.m4a', '.mpeg', '.mp4', '.ogg', '.flac', '.aac'))]",
"",
"if not achados:",
"    print(f'❌ Não achei nenhum áudio com \"{NOME_DO_ARQUIVO}\" no nome.')",
"    print('   Confira o nome (uma parte basta) e rode esta célula de novo.')",
"elif len(achados) > 1:",
"    print('⚠️ Achei mais de um arquivo. Copie o caminho certo para AUDIO abaixo e rode a próxima célula:')",
"    for f in achados:",
"        print('   ', f)",
"    AUDIO = achados[0]",
"    print('\\n(Por padrão vou usar o primeiro:', AUDIO, ')')",
"else:",
"    AUDIO = achados[0]",
"    tam = os.path.getsize(AUDIO) / (1024*1024)",
"    print(f'✅ Áudio selecionado: {AUDIO}')",
"    print(f'   Tamanho: {tam:.0f} MB')",
))

cells.append(md("## 5. Transcrever e salvar", "",
"Agora é só rodar e esperar. Uma sessão de ~2 horas leva por volta de **10 a 25 minutos** com GPU.",
"A transcrição aparece na tela e é salva no Drive, na mesma pasta do áudio, em três formatos:",
"`.txt`, `.md` e `.docx`."))
cells.append(code(
"import os, time, torch",
"from faster_whisper import WhisperModel",
"from docx import Document",
"",
"def hms(seg):",
"    seg = int(seg); h = seg//3600; m = (seg%3600)//60; s = seg%60",
"    return f'{h:02d}:{m:02d}:{s:02d}'",
"",
"tem_gpu = torch.cuda.is_available()",
"device = 'cuda' if tem_gpu else 'cpu'",
"compute = 'float16' if tem_gpu else 'int8'",
"modelo_usar = MODELO if tem_gpu else 'small'  # sem GPU, usa modelo leve p/ não travar",
"print(f'Dispositivo: {device} | Modelo: {modelo_usar}')",
"print('Carregando o Whisper (primeira vez baixa o modelo)...')",
"model = WhisperModel(modelo_usar, device=device, compute_type=compute)",
"",
"print('Transcrevendo... pode ir tomar um café ☕')",
"t0 = time.time()",
"segments, info = model.transcribe(AUDIO, language=IDIOMA, vad_filter=True, beam_size=5)",
"",
"linhas_txt = []       # texto corrido",
"linhas_ts  = []       # com marcação de tempo",
"for seg in segments:",
"    txt = seg.text.strip()",
"    linhas_txt.append(txt)",
"    linhas_ts.append(f'[{hms(seg.start)}] {txt}')",
"    print(f'[{hms(seg.start)}] {txt}')   # mostra o progresso ao vivo",
"",
"texto_corrido = ' '.join(linhas_txt)",
"texto_ts = '\\n'.join(linhas_ts)",
"dur = time.time() - t0",
"print(f'\\n✅ Terminou em {dur/60:.1f} minutos.')",
"",
"# ---- salvar no Drive, ao lado do áudio ----",
"base = os.path.splitext(AUDIO)[0]",
"cabecalho = f'TRANSCRIÇÃO — {os.path.basename(AUDIO)}\\n' + '='*60 + '\\n\\n'",
"",
"with open(base + ' - transcricao.txt', 'w', encoding='utf-8') as f:",
"    f.write(cabecalho + texto_corrido)",
"",
"with open(base + ' - transcricao.md', 'w', encoding='utf-8') as f:",
"    f.write(f'# Transcrição — {os.path.basename(AUDIO)}\\n\\n')",
"    f.write('## Texto corrido\\n\\n' + texto_corrido + '\\n\\n')",
"    f.write('## Com marcação de tempo\\n\\n```\\n' + texto_ts + '\\n```\\n')",
"",
"doc = Document()",
"doc.add_heading(f'Transcrição — {os.path.basename(AUDIO)}', level=1)",
"for linha in linhas_txt:",
"    if linha:",
"        doc.add_paragraph(linha)",
"doc.save(base + ' - transcricao.docx')",
"",
"print('\\nArquivos salvos no seu Drive, na mesma pasta do áudio:')",
"print('  •', os.path.basename(base) + ' - transcricao.txt')",
"print('  •', os.path.basename(base) + ' - transcricao.md')",
"print('  •', os.path.basename(base) + ' - transcricao.docx')",
))

cells.append(md("## Pronto! 🎉", "",
"A transcrição está no seu Drive. Agora você pode:",
"- Abrir o `.docx` e revisar;",
"- Usar o texto como base para a **ata** (inclusive com as skills de ata que você já tem no Claude);",
"- Repetir para outra sessão: volte na célula **4**, troque o nome do arquivo e rode a **4** e a **5** de novo.",
"",
"### Dicas",
"- **Qualidade:** `large-v3` é o melhor. Se estiver muito lento (sem GPU), troque `MODELO` para `medium` ou `small` na célula 4.",
"- **Nomes de vereadores:** o Whisper acerta bem, mas confira nomes próprios na revisão — nenhuma transcrição automática é perfeita.",
"- **Marcação de tempo:** o arquivo `.md` traz a fala com o minuto/segundo, útil para localizar trechos na gravação.",
))

nb = {
    "cells": cells,
    "metadata": {
        "colab": {"provenance": [], "toc_visible": True},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
        "accelerator": "GPU",
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

with open("/home/user/Trial/transcricao-sessoes/Transcrever_Sessao_CMDC.ipynb", "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("Notebook gerado com", len(cells), "células.")
