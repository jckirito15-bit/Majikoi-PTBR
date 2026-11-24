# Majikoi! Love Me Seriously! — Tradução PT-BR (Steam) / Brazilian Portuguese translation

**Tradução feita por Professor Dazai** · *Translation by Professor Dazai* · **Versão / Version 1.0**

Tradução completa do roteiro de *Majikoi! Love Me Seriously!* (Minato Soft, versão Steam, motor NeXAS) para o
português do Brasil: falas, nomes, escolhas e textos de menu, com acentos.

> Este repositório **não contém o jogo nem nenhum arquivo dele**: só o texto traduzido e o instalador. Você usa a sua
> própria cópia do jogo e o que faz com ela é por sua conta e liberdade.

## O que tem aqui

- `traducao/majikoi-ptbr.json`: a tradução (157 mil linhas do roteiro + 386 textos de menu), com o número de cada linha.
- `aplicar.py`: instala a tradução no seu jogo (faz backup e dá para voltar ao original).
- `majikoi_ptbr/`: o código que lê e grava os `.pac` do NeXAS e instala a fonte com acentos.
- `tools/extrair_traducao.py`: ferramenta do autor que gerou o JSON a partir do jogo já traduzido.

## Como instalar (passo a passo)

1. Instale o **Python 3.10+** (python.org) e, num terminal, `pip install fonttools` (para a fonte com acentos).
2. Baixe este repositório (botão verde **Code** > **Download ZIP**) e extraia.
3. Descubra a pasta do jogo: na Steam, botão direito em *Majikoi! Love Me Seriously!* > **Gerenciar** > **Ver arquivos locais**.
   Dentro dela estão `Majikoi.exe` e `Script.pac`.
4. **Feche o jogo.** Abra um terminal na pasta extraída e rode (com as aspas):

   ```
   python aplicar.py "C:\caminho\da\pasta\do\jogo"
   ```

5. Abra o jogo pela Steam. As falas aparecem em português.

**Voltar ao inglês:** `python aplicar.py "C:\caminho\da\pasta\do\jogo" --restaurar`
(os originais ficam guardados em `PTBR_backup` dentro da pasta do jogo).

**Sem a fonte com acentos:** adicione `--sem-fonte` (os textos ficam em português, mas sem acento).

### Observações

- A tradução foi feita para o jogo da Steam original; se o número de linhas de um script não bater, o instalador para
  e avisa, sem estragar nada.
- A fonte "TraduVN Maru" é gerada a partir da fonte do próprio jogo e instalada só para o seu usuário do Windows
  (sem administrador). Ela só existe para desenhar os acentos.
- **Imagens traduzidas (telas de menu em PNG) ainda não estão incluídas** na 1.0: só texto.
- Windows. Se a Steam atualizar o jogo e desfizer a tradução, rode o `aplicar.py` de novo.

---

## English

Full Brazilian Portuguese translation of *Majikoi! Love Me Seriously!* (Steam, NeXAS engine) by **Professor Dazai**.
No game files are included: only the translated text (`traducao/majikoi-ptbr.json`) and an installer.

1. Install Python 3.10+ and run `pip install fonttools`.
2. Download this repository and unzip it.
3. Find the game folder (Steam: right click the game > Manage > Browse local files).
4. **Close the game**, then run `python aplicar.py "<game folder>"`.
5. Start the game. To undo: `python aplicar.py "<game folder>" --restaurar` (originals are kept in `PTBR_backup`).

Add `--sem-fonte` to skip the accent font. Translated menu images are not part of 1.0.

## Créditos / Credits

- Tradução e projeto / Translation and project: **Professor Dazai**.
- Leitura e gravação de `.pac` do NeXAS: código próprio, baseado no formato público do motor.
- *Majikoi! Love Me Seriously!* é da Minato Soft. Projeto de fãs, não oficial.

## Licença / License

MIT (código e tradução). O jogo não faz parte deste repositório.
