# Decrypt Pipeline — README

Este documento descreve o funcionamento do pipeline contido em `decrypt.py` e nas funções auxiliares em `funcoes_decodificador.py`, organizado por passos (1..14). Use este arquivo como referência rápida para entender o fluxo, parâmetros, arquivos gerados e decisões importantes.

---

## Arquivos principais

- `decrypt.py` — script principal que conduz o pipeline (Passos 1..14).
- `funcoes_decodificador.py` — funções utilitárias chamadas pelo pipeline.
- `caracteres_printaveis.py` — dicionário binário (8 bits) -> caractere.
- `top_words.py` — dicionário de palavras frequentes com ranking.
- `encoded.txt` — entrada de exemplo (texto a ser processado).
- `final_map.py` — arquivo gerado contendo o mapeamento acumulado (checkpoint).
- `candidatas_encolhidas.py` — arquivo gerado contendo palavras do `top_words` já usadas.
- `final_reconstructed.txt` — saída reconstruída com pontuação/sufixos (Passo 13).
- `final_reconstructed_mapped.txt` — saída final com aplicação do mapa (Passo 14).

---

## Execução

```bash
python decrypt.py
```

Parâmetros principais (no topo de `decrypt.py`):
- `DEBUG` — True/False para prints detalhados e pausas interativas.
- `arquivo_entrada` — nome do arquivo de entrada (default: `encoded.txt`).
- `passo_threshold` — passo para geração dinâmica de thresholds (ex.: 2).
- `limite_threshold` — limite inferior para thresholds (inclusive).

---

## Descrição por passos

### ================================================================== ###
### Passo 1 - Separando cada caractere por linha
### ================================================================== ###

- Lê `encoded.txt` inteiro.
- Usa `string.printable` (sem whitespace final) para montar uma expressão regular.
- Captura todas as sequências contínuas de caracteres "printáveis" e salva em `sequencias`.
- Objetivo: extrair blocos relevantes de texto/bytes que serão padronizados.

### =================================================================== ###
### Passo 2 - Padronizando o conteúdo para binário de 8 bits
### =================================================================== ###

- Remove espaços internos nas sequências e completa com zeros à esquerda até que o comprimento seja múltiplo de 8.
- Resultado: `sequencias_padronizadas` (cada item representa uma série de bytes alinhada a 8 bits).
- Função: `padronizar_para_8bits` em `funcoes_decodificador.py`.

### =================================================================== ###
### Passo 3 - Busca e substituição no dicionário
### =================================================================== ###

- Converte cada sequência 8-bit em caracteres usando `caracteres_printaveis` (map bin->char).
- Produz a lista `decodificadas` com as linhas de texto decodificadas.
- Função: `buscar_e_substituir_por_dicionario`.

### =================================================================== ###
### Passo 4 - Associar cada linha a uma palavra e lembrar a posição
### =================================================================== ###

- Une as linhas decodificadas em um único texto e substitui espaços por quebras de linha.
- Para cada linha/tokens:
  - Guarda a linha original em `original_lines_by_pos` (útil para reconstrução posterior).
  - Aplica regras de limpeza:
    - Prioridade de símbolos: `--`, apóstrofos (`'`, `’`, `` ` ``), traço `-`.
    - Se o símbolo for seguido de letra, corta o token no símbolo e guarda o sufixo (ex.: `HAHS'S` -> `HAHS` + `"'S"`).
    - Remove acentos e qualquer caractere que não seja letra.
  - Armazena `(posicao, palavra_limpa)` em `palavras_pos`.
- Função: `associar_palavras_com_posicao` (retorna `palavras_pos`, `original_lines_by_pos`).

### =================================================================== ###
### Passo 5 - Ordenando palavras por comprimento (modo em blocos)
### =================================================================== ###

- Agrupa palavras por comprimento e cria `blocos` (rodadas) intercaladas com no máximo 1 palavra de cada tamanho por rodada.
- Também gera `palavras_ordenadas_pos` (flat) — lista única intercalada usada pelo pipeline.
- Função: `ordenar_palavras_por_tamanho_em_blocos`.

### =================================================================== ###
### Passo 6 - Aplicar PRIMEIRO mapeamento do Bloco 1 (apenas um mapeamento)
### =================================================================== ###

- Gera mapeamentos somente para a primeira palavra válida do bloco 1, usando `top_words` (maior rank disponível com mesmo comprimento).
- Aplica apenas o **primeiro** mapeamento gerado neste bloco (para evitar aplicar tudo de uma vez).
- Atualiza `mapa_substituicao` e marca a candidata como usada (em `used_top_words`) se válida.
- Função: `gerar_mapeamentos_para_primeira_palavra` + `aplicar_um_mapeamento_em_posicoes`.

### =================================================================== ###
### Passo 7 - Iterativo no Bloco 1
### =================================================================== ###

- Itera dentro do Bloco 1:
  - Recalcula impacto por palavra (`calcular_impacto_por_bloco`) com base no estado antes/depois.
  - Escolhe a palavra mais "impactada" (maior `diff_frac`).
  - Busca a primeira candidata compatível em `top_words` com `encontrar_candidata_compatível`.
  - Filtra mapeamentos conflitantes (não sobrescrever mapeamentos existentes; não usar destinos já reservados).
  - Aplica mapeamentos válidos somente dentro do bloco e atualiza `mapa_substituicao`.
  - Marca a candidata como usada.
- O loop para quando não há candidatas compatíveis restantes.

### =================================================================== ###
### Passo 8 - Salvar mapeamento acumulado e palavras candidatas usadas
### =================================================================== ###

- Salva `mapa_substituicao` em `final_map.py` e `used_top_words` em `candidatas_encolhidas.py` (checkpoints JSON-like).
- Função interna: `_salvar_checkpoints`.

### =================================================================== ###
### Passo 10 - Varrer blocos por múltiplos thresholds (dinâmico)
### =================================================================== ###

- Gera `thresholds` dinamicamente (100 -> `limite_threshold`, passo = `passo_threshold`).
- Para cada threshold, percorre **todos** os blocos (inclui o bloco 1 na primeira rodada):
  1. Aplica o `final_map` (checkpoint atual) a todas as palavras do bloco.
  2. Calcula `ratio` por palavra (nº letras minúsculas / comprimento).
  3. Para palavras com `ratio >= threshold`, tenta encontrar candidata compatível e aplicar mapeamentos válidos.
- Regras importantes:
  - Nunca substitui uma letra já minúscula.
  - Não reutiliza palavras do `top_words` já marcadas em `used_top_words`.
  - Não permite que duas chaves diferentes mapeiem para o mesmo destino (evita conflito de destino).
  - Atualiza checkpoints após terminar cada threshold.
- Observação: thresholds podem ser parametrizados (ex.: `passo_threshold=2`, `limite_threshold=34`).

### =================================================================== ###
### Passo 11 - Exibir mapeamento acumulado e sequência de palavras por posição
### =================================================================== ###

- Restaura a lista por posição (`restaurar_por_posicao`) e imprime a sequência de palavras na ordem correta (sempre, independente de `DEBUG`).
- Em modo `DEBUG`, imprime também o mapa acumulado e o flat detalhado.

### =================================================================== ###
### Passo 12 - Percentual de palavras do texto final presentes em top_words
### =================================================================== ###

- Calcula quantos tokens do texto final (contando repetições) existem em `top_words`.
- Imprime totais, porcentagem, e listas (todas as palavras encontradas e não encontradas, por frequência).
- Usa normalização (remoção de acentos e lower) para comparar com `top_words`.

### =================================================================== ###
### Passo 13 - Reconstruir texto com pontuação e sufixos (apóstrofo/traço/--)
### =================================================================== ###

- Usa `original_lines_by_pos` (armazenado no Passo 4) para reinserir:
  - a pontuação original ao redor da palavra;
  - o sufixo cortado no Passo 4 (ex.: `"HAHS'S"` -> `"HAHS"` na etapa de limpeza; aqui devolve `"HAHS'S"` ou forma compatível);
- Salva resultado em `final_reconstructed.txt`.

### =================================================================== ###
### Passo 14 - Aplicar mapeamento às maiúsculas remanescentes e imprimir
### =================================================================== ###

- Carrega `final_map.py` (se existir) ou usa `mapa_substituicao` em memória.
- Aplica substituição **apenas** em caracteres MAIÚSCULOS do `final_text` — substitui se houver mapeamento.
- Salva `final_reconstructed_mapped.txt` e imprime o conteúdo e um resumo de substituições.
- Função utilitária: `aplicar_mapeamento_em_texto` (disponível em `funcoes_decodificador.py`).

---

## Notas e regras importantes

- Nunca reatribuir um destino (letra clara) que já esteja reservado no mapa acumulado.
- Não criar mapeamentos para caracteres que já são minúsculos.
- Ao buscar candidatas, se uma posição já tiver letras reveladas (minúsculas), a candidata deve ter exatamente essas letras nas mesmas posições.
- Palavras não pertencentes ao `top_words` (após normalização) não podem ser marcadas como usadas.
- O pipeline é interativo quando `DEBUG = True` (pausas `input()` entre iterações); pode ser automatizado definindo `DEBUG = False`.

---

## Exemplos de saída / artefatos gerados

- `final_map.py` — contém algo como:

```py
# -*- coding: utf-8 -*-
final_map = {
    "T": "a",
    "V": "t",
    "C": "h",
    ...
}
```

- `candidatas_encolhidas.py` — lista JSON das palavras do `top_words` já utilizadas.
- `final_reconstructed.txt` — texto reconstruído com pontuação e sufixos (antes do mapeamento final).
- `final_reconstructed_mapped.txt` — texto final com aplicação de `final_map` às maiúsculas remanescentes.

---

## Dicas para depuração e ajustes

- Se o pipeline estiver substituindo palavras que não pertencem ao `top_words`, verifique a normalização e o conteúdo de `top_words.py`.
- Ajuste `passo_threshold` e `limite_threshold` para controlar sensibilidade das iterações.
- Use `DEBUG = True` para inspecionar iterações passo-a-passo e pausar quando desejar.

---

## Histórico

Documentação gerada automaticamente com base na versão atual do pipeline solicitada pelo usuário.
