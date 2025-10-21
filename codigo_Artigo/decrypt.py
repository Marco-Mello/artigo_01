#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
decrypt.py
Pipeline principal — passos 1..14 conforme especificado.
Comentários em cada passo no formato pedido.
"""

import string
import re
import os
import json
import unicodedata
from collections import Counter

from caracteres_printaveis import caracteres_printaveis
from funcoes_decodificador import (
    padronizar_para_8bits,
    buscar_e_substituir_por_dicionario,
    associar_palavras_com_posicao,
    ordenar_palavras_por_tamanho_em_blocos,
    gerar_mapeamentos_para_primeira_palavra,
    aplicar_um_mapeamento_em_posicoes,
    aplicar_mapeamentos_em_posicoes,
    calcular_impacto_por_bloco,
    encontrar_candidata_compatível,
    restaurar_por_posicao,
    aplicar_mapeamento_em_texto,
)
from top_words import top_words

# =====================================================================
# Configurações principais
# =====================================================================
DEBUG = False                     # Ativar/desativar prints detalhados
arquivo_entrada = "encoded_EXIST.txt"   # Nome do arquivo de entrada
passo_threshold = 2               # decremento em pontos percentuais para thresholds
limite_threshold = 34             # limite mínimo inclusivo para thresholds
# =====================================================================

# ------------------------
# Normalização / utilitários
# ------------------------
def _normalizar_token(t: str) -> str:
    if not isinstance(t, str):
        return ""
    s = t.strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()

top_set_normalized = {_normalizar_token(w) for w in top_words.keys()}
top_sorted = sorted(top_words.items(), key=lambda item: item[1])

### ================================================================== ###
### Passo 1 - Separando cada caractere por linha                       ###
### ================================================================== ###
# lê o arquivo, filtra apenas sequências de caracteres printáveis
# usa string.printable (sem o whitespace final) e re.escape para montar regex
# gera lista 'sequencias' contendo cada sequência encontrada
# útil para etapas seguintes (padronizar/decodificar)
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 1: Separando caracteres printáveis...")

with open(arquivo_entrada, "r", encoding="utf-8") as f:
    data = f.read()

# regex para caracteres printáveis (sem whitespace final)
chars_regex = re.escape(string.printable.strip())
sequencias = re.findall(f"[{chars_regex}]+", data)

if DEBUG:
    print(f"[DEBUG] {len(sequencias)} sequências encontradas:")
    for seq in sequencias:
        print(seq)

### =================================================================== ###
### =================================================================== ###
### =================================================================== ###


### ================================================================== ###
### Passo 2 - Padronizando o conteúdo para binário de 8 bits           ###
### ================================================================== ###
# remove espaços das sequências, completa com zeros à esquerda até múltiplos de 8
# retorna 'sequencias_padronizadas' para decodificação no passo 3
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 2: Padronizando conteúdo para 8 bits...")

sequencias_padronizadas = padronizar_para_8bits(sequencias)

if DEBUG:
    print(f"[DEBUG] {len(sequencias_padronizadas)} sequências padronizadas:")
    for seq in sequencias_padronizadas:
        print(seq)

### =================================================================== ###
### =================================================================== ###
### =================================================================== ###


### ================================================================== ###
### Passo 3 - Busca e substituição no dicionário                       ###
### ================================================================== ###
# converte cada byte (8 bits) em caractere usando o dicionário bin->char
# resultado: lista 'decodificadas' com linhas de texto decodificadas
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 3: Substituindo binário por caracteres...")

decodificadas = buscar_e_substituir_por_dicionario(sequencias_padronizadas, caracteres_printaveis)

if DEBUG:
    print(f"[DEBUG] {len(decodificadas)} sequências decodificadas:")
    for seq in decodificadas:
        print(seq)

### =================================================================== ###
### =================================================================== ###
### =================================================================== ###


### ================================================================== ###
### Passo 4 - Associar cada linha a uma palavra e lembrar a posição     ###
### ================================================================== ###
# limpa tokens, trata apóstrofo/traço/--, remove acentos e pontuação
# guarda original_lines_by_pos para reconstrução posterior (passo 13)
# retorna palavras_pos = [(pos, palavra_limpa), ...]
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 4: Associando cada linha a uma palavra e lembrando posição (limpeza: apenas letras, trata apóstrofos/traço/--)...")

palavras_pos, original_lines_by_pos = associar_palavras_com_posicao(decodificadas)

if DEBUG:
    print(f"[DEBUG] Total de palavras com posição (após limpeza): {len(palavras_pos)}")
    for pos, p in palavras_pos:
        print(f"{pos}: {p}")

### =================================================================== ###
### =================================================================== ###
### =================================================================== ###


### ================================================================== ###
### Passo 5 - Ordenando palavras por comprimento (modo em blocos)      ###
### ================================================================== ###
# cria 'blocos' (rodadas) com no máximo 1 palavra por tamanho por rodada
# também retorna 'palavras_ordenadas_pos' = flat (lista única intercalada)
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 5: Ordenando palavras por comprimento (em blocos)...")

blocos, palavras_ordenadas_pos = ordenar_palavras_por_tamanho_em_blocos(palavras_pos)

if DEBUG:
    total = sum(len(b) for b in blocos)
    print(f"[DEBUG] Total de blocos (rodadas): {len(blocos)}")
    print(f"[DEBUG] Total de palavras no resultado: {total}\n")
    for i, bloco in enumerate(blocos, start=1):
        print(f"--- Bloco {i} — {len(bloco)} palavras ---")
        for pos, p in bloco:
            print(f"{pos}: {p}")
        print()

### =================================================================== ###
### =================================================================== ###
### =================================================================== ###


### ================================================================== ###
### Preparação: estado global para mapeamentos e controle de top_words ###
### ================================================================== ###
# used_top_words: palavras já usadas do top_words (não reutilizar)
# mapa_substituicao: acumulador de mapeamentos cifrado -> claro (minúsculo)
# palavras_substituidas_pos: estado corrente do flat (lista de (pos,palavra))
used_top_words = set()
mapa_substituicao = {}
palavras_substituidas_pos = palavras_ordenadas_pos.copy()
### ================================================================== ###


### ================================================================== ###
### Passo 6 - Aplicar PRIMEIRO mapeamento do Bloco 1 (apenas um mapeamento) ###
### ================================================================== ###
# Gera mapeamentos apenas para a primeira palavra válida do bloco 1 e aplica 1º mapeamento
# Atualiza mapa_substituicao e marca candidata como usada (se válida)
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 6 (primeira palavra apenas): Gerando mapeamentos da primeira palavra do primeiro bloco...")

if len(blocos) == 0:
    if DEBUG:
        print("[DEBUG] Nenhum bloco disponível. Pulando Passo 6.")
else:
    bloco0 = blocos[0]
    mapeamentos_primeira, candidata_primeira = gerar_mapeamentos_para_primeira_palavra(
        bloco0,
        top_words,
        used_top_words=used_top_words
    )

    if DEBUG:
        print(f"[DEBUG] {len(mapeamentos_primeira)} mapeamentos possíveis gerados a partir da primeira palavra do bloco.")
        for i, (cif, claro) in enumerate(mapeamentos_primeira[:30], start=1):
            print(f"  {i}: {cif} -> {claro}")

    palavras_ordenadas_pos_before = palavras_ordenadas_pos.copy()

    if not mapeamentos_primeira:
        if DEBUG:
            print("[DEBUG] Nenhum mapeamento gerado a partir da primeira palavra do bloco.")
    else:
        primeiro_map = mapeamentos_primeira[0]
        pos_alvo = {pos for pos, _ in bloco0}

        palavras_substituidas_pos = aplicar_um_mapeamento_em_posicoes(
            palavras_ordenadas_pos,
            primeiro_map,
            pos_alvo
        )

        c0, v0 = primeiro_map
        if c0 != v0 and v0 not in set(mapa_substituicao.values()):
            mapa_substituicao[c0] = v0

        if candidata_primeira:
            if _normalizar_token(candidata_primeira) in top_set_normalized:
                used_top_words.add(candidata_primeira)
            else:
                if DEBUG:
                    print(f"[DEBUG] AVISO: candidata '{candidata_primeira}' não pertence ao top_words (após normalização). Não marcada.")

        if DEBUG:
            print(f"\n[DEBUG] Aplicado 1º mapeamento (da primeira palavra): {c0} -> {v0}")
            print("\n[DEBUG] Resultado parcial (apenas posições do primeiro bloco mostradas):")
            for pos, pw in palavras_substituidas_pos:
                if pos in pos_alvo:
                    print(f"{pos}: {pw}")

        if DEBUG:
            input("\n[DEBUG] Pausa após 1ª substituição: pressione Enter para continuar...")

### =================================================================== ###
### =================================================================== ###
### =================================================================== ###


### ================================================================== ###
### Passo 7 - Iterativo no Bloco 1                                      ###
### ================================================================== ###
# Itera dentro do bloco 1, recalcula impacto, encontra candidata compatível,
# aplica mapeamentos válidos (respeitando mapa existente e letras reservadas)
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 7 iterativo: aplicar mapeamentos no primeiro bloco até exaurir candidatos...")

if len(blocos) == 0:
    if DEBUG:
        print("[DEBUG] Nenhum bloco para iterar no Passo 7.")
else:
    bloco0 = blocos[0]
    primeira_pos = next((pos for pos, pw in bloco0 if not pw.islower()), None)
    exclude = {primeira_pos} if primeira_pos is not None else set()
    flat_current = palavras_substituidas_pos.copy()
    iteration = 0

    while True:
        iteration += 1
        if DEBUG:
            print(f"\n[DEBUG] --- Iteration {iteration} — recalculando impactos ---")

        impactos = calcular_impacto_por_bloco(bloco0, palavras_ordenadas_pos_before, flat_current, exclude_positions=exclude)

        if not impactos:
            if DEBUG:
                print("[DEBUG] Não há palavras elegíveis (após exclusões) para avaliar impacto. Fim do loop.")
            break

        top = impactos[0]
        pos_top = top["pos"]
        palavra_top_before = top["before"]
        palavra_top_after = top["after"]

        if DEBUG:
            print(f"[DEBUG] Palavra mais impactada nesta iteração: pos {pos_top} | antes: '{palavra_top_before}' | depois: '{palavra_top_after}'")
            print(f"[DEBUG] Diferenças: {top['diff_count']} / {len(palavra_top_before)} ({top['diff_frac']:.2%})")

        mapa_existente = mapa_substituicao.copy()
        letras_usadas = set(mapa_existente.values())

        candidata_word, novos_mapeamentos = encontrar_candidata_compatível(
            palavra_top_after, top_sorted, mapa_existente, letras_usadas, used_top_words=used_top_words
        )

        if candidata_word is None or not novos_mapeamentos:
            if DEBUG:
                print("[DEBUG] Nenhuma candidata compatível encontrada para a palavra mais impactada. Fim do loop.")
            break

        if DEBUG:
            print(f"[DEBUG] Candidata escolhida para pos {pos_top}: {candidata_word}")
            print("[DEBUG] Novos mapeamentos gerados (potenciais):")
            for mm in novos_mapeamentos:
                print(f"  {mm[0]} -> {mm[1]}")

        novos_mapeamentos = [(c, v) for c, v in novos_mapeamentos if c != v]
        destinos_usados = set(mapa_existente.values())
        mapeamentos_validos = []
        for c, v in novos_mapeamentos:
            if c in mapa_existente:
                continue
            if v in destinos_usados:
                continue
            mapeamentos_validos.append((c, v))
            destinos_usados.add(v)

        if not mapeamentos_validos:
            if DEBUG:
                print("[DEBUG] Nenhum mapeamento válido permaneceu após filtragem. Rotina encerra.")
            break

        if _normalizar_token(candidata_word) in top_set_normalized:
            used_top_words.add(candidata_word)
        else:
            if DEBUG:
                print(f"[DEBUG] AVISO: candidata '{candidata_word}' não pertence a top_words (após normalização). Não marcada.")

        pos_alvo = {pos for pos, _ in bloco0}
        flat_current = aplicar_mapeamentos_em_posicoes(flat_current, mapeamentos_validos, pos_alvo)
        mapa_substituicao.update({c: v for c, v in mapeamentos_validos})

        if DEBUG:
            print(f"\n[DEBUG] Após aplicar mapeamentos da iteração {iteration}, resultado parcial no bloco:")
            for pos, pw in flat_current:
                if pos in pos_alvo:
                    print(f"{pos}: {pw}")

        if DEBUG:
            resp = input("\n[DEBUG] Pressione Enter para continuar para a próxima iteração, ou digite 'q' para parar: ")
            if resp.strip().lower() in ('q', 'quit', 'sair'):
                if DEBUG:
                    print("[DEBUG] Interrompido pelo usuário.")
                break

    palavras_substituidas_pos = flat_current.copy()

if DEBUG:
    print("\n[DEBUG] Processo iterativo concluído. Mapeamento final acumulado:")
    for k, v in sorted(mapa_substituicao.items()):
        print(f"  {k} -> {v}")

### =================================================================== ###
### =================================================================== ###
### =================================================================== ###


### ================================================================== ###
### Passo 8 - Salvar mapeamento acumulado e palavras candidatas usadas ###
### ================================================================== ###
# salva final_map.py e candidatas_encolhidas.py (checkpoint)
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 8: Salvando resultados...")

final_map_path = "final_map.py"
candidatas_path = "candidatas_encolhidas.py"

def _salvar_checkpoints(mapa_subst, used_words):
    with open(final_map_path, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write("# Dicionário de mapeamento final gerado automaticamente\n")
        f.write("final_map = ")
        json.dump(mapa_subst, f, ensure_ascii=False, indent=4)
    with open(candidatas_path, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write("# Palavras do top_words já utilizadas\n")
        f.write("candidatas_encolhidas = ")
        json.dump(sorted(list(used_words)), f, ensure_ascii=False, indent=4)

_salvar_checkpoints(mapa_substituicao, used_top_words)
if DEBUG:
    print(f"[DEBUG] Mapeamento inicial salvo em {final_map_path} ({len(mapa_substituicao)} entradas).")
    print(f"[DEBUG] Palavras candidatas salvas em {candidatas_path} ({len(used_top_words)} palavras).")

### =================================================================== ###
### =================================================================== ###
### =================================================================== ###


### ================================================================== ###
### Passo 10 - Varrer blocos por múltiplos thresholds (dinâmico)       ###
### ================================================================== ###
# Gera thresholds dinâmicos e percorre todos os blocos para cada threshold
# Em cada bloco:
#  A) aplica final_map existente a todas as palavras do bloco
#  B) calcula ratio por palavra (substituídas/comprimento)
#  C) tenta achar candidatas para palavras com ratio >= threshold
# Atualiza mapa_substituicao e used_top_words conforme aplica mapeamentos válidos
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 10: varrer blocos com múltiplos thresholds...")

thresholds = list(range(100, limite_threshold - 1, -passo_threshold))
if DEBUG:
    print(f"[DEBUG] Thresholds gerados dinamicamente (passo={passo_threshold}, limite={limite_threshold}): {thresholds}")

# Carrega checkpoints se existirem
if os.path.exists(final_map_path):
    try:
        from final_map import final_map as loaded_final_map
        if DEBUG:
            print(f"[DEBUG] final_map carregado com {len(loaded_final_map)} entradas.")
    except Exception as e:
        loaded_final_map = {}
        if DEBUG:
            print(f"[DEBUG] Erro ao importar final_map.py ({e}) — inicializando final_map vazio.")
else:
    loaded_final_map = {}
    if DEBUG:
        print("[DEBUG] final_map.py não encontrado — inicializando final_map vazio.")

if os.path.exists(candidatas_path):
    try:
        from candidatas_encolhidas import candidatas_encolhidas as loaded_candidatas
        if DEBUG:
            print(f"[DEBUG] candidatas_encolhidas carregadas ({len(loaded_candidatas)} palavras).")
    except Exception as e:
        loaded_candidatas = []
        if DEBUG:
            print(f"[DEBUG] Erro ao importar candidatas_encolhidas.py ({e}) — inicializando lista vazia.")
else:
    loaded_candidatas = []
    if DEBUG:
        print("[DEBUG] candidatas_encolhidas.py não encontrado — inicializando lista vazia.")

mapa_substituicao = loaded_final_map.copy()
used_top_words = set(loaded_candidatas)

try:
    flat_current_global = palavras_substituidas_pos.copy()
except NameError:
    flat_current_global = palavras_ordenadas_pos.copy()

def _salvar_checkpoints_local(mapa_subst, used_words):
    _salvar_checkpoints(mapa_subst, used_words)

for ti, thr_percent in enumerate(thresholds):
    RATIO_THRESHOLD = thr_percent / 100.0
    if DEBUG:
        print(f"\n[DEBUG] ================= Threshold {thr_percent}% (idx {ti}) =================")
        print(f"[DEBUG] Iterando blocos com ratio >= {RATIO_THRESHOLD:.0%}")

    bloco_range = range(0, len(blocos))

    for bloco_index in bloco_range:
        bloco = blocos[bloco_index]
        pos_alvo = {pos for pos, _ in bloco}

        if DEBUG:
            print(f"\n[DEBUG] ----- Processando Bloco {bloco_index + 1} (index {bloco_index}) para threshold {thr_percent}% -----")
            print(f"[DEBUG] Posições do bloco: {sorted(pos_alvo)}")
            print(f"[DEBUG] Estado inicial do mapa: {len(mapa_substituicao)} entradas; candidatas usadas: {len(used_top_words)}")

        # A) aplicar mapa_substituicao a todas as palavras do bloco
        if mapa_substituicao:
            if DEBUG:
                print(f"[DEBUG] Aplicando final_map ({len(mapa_substituicao)} pares) a todas as palavras do bloco {bloco_index + 1}...")
            pares_mapa = list(mapa_substituicao.items())
            flat_current_global = aplicar_mapeamentos_em_posicoes(flat_current_global, pares_mapa, pos_alvo)
        else:
            if DEBUG:
                print("[DEBUG] final_map vazio — nada a aplicar antes da busca para este bloco.")

        if DEBUG:
            print("\n[DEBUG] Estado do bloco após aplicar final_map (parcial):")
            for p, pw in flat_current_global:
                if p in pos_alvo:
                    print(f"{p}: {pw}")

        # B) calcular ratio e exibir
        if DEBUG:
            print("\n[DEBUG] Passo Intermediário: calculando ratio de letras substituídas por palavra no bloco...")
        ratios = []
        for p, original in bloco:
            palavra_atual = next((pw for pp, pw in flat_current_global if pp == p), original)
            length = len(palavra_atual) if palavra_atual else 0
            if length == 0:
                substituted = 0
                ratio = 0.0
            else:
                substituted = sum(1 for ch in palavra_atual if ch.islower())
                ratio = substituted / length
            ratios.append((p, palavra_atual, substituted, length, ratio))
        if DEBUG:
            print(f"[DEBUG] Ratios para Bloco {bloco_index + 1}: (pos | palavra | substituted/length | ratio%)")
            for p, pw, sub_cnt, length, ratio in ratios:
                print(f"  {p}: '{pw}' | {sub_cnt}/{length} | {ratio:.2%}")

        if DEBUG:
            input(f"\n[DEBUG] Pausa: revisão de ratios concluída para Bloco {bloco_index + 1}. Pressione Enter para iniciar busca (threshold {thr_percent}%)...")

        # C) palavra-a-palavra: somente para palavras com ratio >= RATIO_THRESHOLD
        letras_reservadas = set(mapa_substituicao.values())

        for pos, palavra_original in bloco:
            if DEBUG:
                print(f"\n[DEBUG] Avaliando posição {pos} | palavra atual (flat): ", end="")
            palavra_flat_atual = next((pw for p, pw in flat_current_global if p == pos), palavra_original)
            if DEBUG:
                print(f"'{palavra_flat_atual}'")

            if palavra_flat_atual.islower():
                if DEBUG:
                    print("[DEBUG] Palavra já totalmente minúscula — ignorando.")
                continue

            length = len(palavra_flat_atual) if palavra_flat_atual else 0
            substituted = sum(1 for ch in palavra_flat_atual if ch.islower()) if length > 0 else 0
            ratio = substituted / length if length > 0 else 0.0

            if DEBUG:
                print(f"[DEBUG] Ratio desta palavra: {substituted}/{length} = {ratio:.2%} (limiar atual: {RATIO_THRESHOLD:.0%})")

            if ratio < RATIO_THRESHOLD:
                if DEBUG:
                    print(f"[DEBUG] Ratio abaixo de {RATIO_THRESHOLD:.0%} — pulando tentativa de candidata para esta palavra.")
                continue

            candidata_word, novos_mapeamentos = encontrar_candidata_compatível(
                palavra_flat_atual,
                top_sorted,
                mapa_substituicao.copy(),
                letras_reservadas,
                used_top_words=used_top_words
            )

            if candidata_word is None or not novos_mapeamentos:
                if DEBUG:
                    print("[DEBUG] Nenhuma candidata compatível encontrada para esta palavra; pulando para a próxima.")
                continue

            if DEBUG:
                print(f"[DEBUG] Candidata escolhida para pos {pos}: {candidata_word}")
                print("[DEBUG] Novos mapeamentos gerados (potenciais):")
                for mm in novos_mapeamentos:
                    print(f"  {mm[0]} -> {mm[1]}")

            novos_mapeamentos = [(c, v) for c, v in novos_mapeamentos if c != v]
            mapeamentos_validos = []
            for c, v in novos_mapeamentos:
                if v in letras_reservadas:
                    if DEBUG:
                        print(f"[DEBUG] Ignorando {c}->{v}: destino '{v}' já reservado em final_map.")
                    continue
                if c in mapa_substituicao and mapa_substituicao[c] != v:
                    if DEBUG:
                        print(f"[DEBUG] Ignorando {c}->{v}: cifrado '{c}' já mapeado para '{mapa_substituicao[c]}'.")
                    continue
                mapeamentos_validos.append((c, v))
                letras_reservadas.add(v)

            if not mapeamentos_validos:
                if DEBUG:
                    print("[DEBUG] Após filtragem não restaram mapeamentos válidos para aplicar; pulando esta palavra.")
                continue

            if DEBUG:
                print(f"[DEBUG] Aplicando {len(mapeamentos_validos)} mapeamentos válidos ao bloco {bloco_index + 1}...")
            flat_current_global = aplicar_mapeamentos_em_posicoes(flat_current_global, mapeamentos_validos, pos_alvo)

            for c, v in mapeamentos_validos:
                if c not in mapa_substituicao:
                    mapa_substituicao[c] = v
                    if DEBUG:
                        print(f"[DEBUG] Atualizado mapa_substituicao: {c} -> {v}")
                else:
                    if mapa_substituicao[c] != v and DEBUG:
                        print(f"[DEBUG] Não sobrescrevendo {c}: já mapeado para {mapa_substituicao[c]}")

            if _normalizar_token(candidata_word) in top_set_normalized:
                used_top_words.add(candidata_word)
                if DEBUG:
                    print(f"[DEBUG] Marcada candidata como usada: {candidata_word}")
            else:
                if DEBUG:
                    print(f"[DEBUG] AVISO: candidata '{candidata_word}' não pertence a top_words (após normalização). Não marcada.")

            if DEBUG:
                print("\n[DEBUG] Resultado parcial do bloco após aplicação:")
                for p, pw in flat_current_global:
                    if p in pos_alvo:
                        print(f"{p}: {pw}")

            if DEBUG:
                resp = input("\n[DEBUG] Pressione Enter para continuar para a próxima palavra, ou digite 'q' para parar: ")
                if resp.strip().lower() in ('q', 'quit', 'sair'):
                    if DEBUG:
                        print("[DEBUG] Interrompido pelo usuário durante Passo 10 (word-by-word).")
                    break

        if DEBUG:
            print(f"\n[DEBUG] Concluído processamento do Bloco {bloco_index + 1} para threshold {thr_percent}%. Mapa atual tem {len(mapa_substituicao)} entradas; candidatas usadas: {len(used_top_words)}")

        if DEBUG:
            resp_block = input(f"\n[DEBUG] Pausa: pressione Enter para continuar para o próximo bloco, ou digite 'q' para parar: ")
            if resp_block.strip().lower() in ('q', 'quit', 'sair'):
                if DEBUG:
                    print("[DEBUG] Usuário interrompeu o processamento de blocos (Passo 10).")
                break

    # checkpoint após cada threshold
    if DEBUG:
        print(f"\n[DEBUG] Checkpoint: salvando final_map.py e candidatas_encolhidas.py após threshold {thr_percent}%...")
    _salvar_checkpoints(mapa_substituicao, used_top_words)
    if DEBUG:
        print(f"[DEBUG] Checkpoint salvo. Mapa tem {len(mapa_substituicao)} entradas; candidatas usadas: {len(used_top_words)}")

    if DEBUG:
        resp_thr = input(f"\n[DEBUG] Threshold {thr_percent}% concluído. Pressione Enter para continuar para o próximo threshold, ou digite 'q' para parar: ")
        if resp_thr.strip().lower() in ('q', 'quit', 'sair'):
            if DEBUG:
                print(f"[DEBUG] Processamento interrompido pelo usuário após threshold {thr_percent}%.")
            break

# fim loop thresholds
if DEBUG:
    print("\n[DEBUG] Finalizando Passo 10: salvando arquivos finais...")
_salvar_checkpoints(mapa_substituicao, used_top_words)
if DEBUG:
    print(f"[DEBUG] Passo 10 concluído. final_map.py ({len(mapa_substituicao)} mapeamentos) e candidatas_encolhidas.py ({len(used_top_words)} palavras) salvos.")

### ================================================================== ###
### Passo 11 - Exibir mapeamento acumulado e sequência de palavras por posição
### ================================================================== ###
# Restaura flat por posição e imprime sequência única (sempre)
try:
    mapa_exibir = mapa_substituicao
except NameError:
    mapa_exibir = {}

flat_para_exibir = None
if 'flat_current_global' in globals():
    flat_para_exibir = flat_current_global
elif 'palavras_substituidas_pos' in globals():
    flat_para_exibir = palavras_substituidas_pos
elif 'palavras_ordenadas_pos' in globals():
    flat_para_exibir = palavras_ordenadas_pos

restaurado = []
if flat_para_exibir is not None:
    try:
        restaurado = restaurar_por_posicao(flat_para_exibir)
    except Exception:
        try:
            pos_to_word = {pos: pw for pos, pw in flat_para_exibir}
            max_pos = max(pos_to_word.keys()) if pos_to_word else -1
            restaurado = [pos_to_word.get(i, "") for i in range(max_pos + 1)]
        except Exception:
            restaurado = []

sequencia_por_pos = " ".join((val if val is not None else "") for val in restaurado)

# imprime sempre a sequência final por posição (não depende de DEBUG)
print("\n[RESULT] Sequência de palavras na ordem das posições (campos vazios preservam lacunas):")
print(sequencia_por_pos)

if DEBUG:
    print("\n[DEBUG] Mapeamento acumulado (cifrado -> claro):")
    if not mapa_exibir:
        print("[DEBUG] (vazio)")
    else:
        for k in sorted(mapa_exibir.keys()):
            print(f"  {k} -> {mapa_exibir[k]}")

    print("\n[DEBUG] Palavras no estado atual (posição : palavra):")
    if not flat_para_exibir:
        print("[DEBUG] (nenhum flat disponível)")
    else:
        for pos, pw in flat_para_exibir:
            print(f"{pos}: {pw}")

print("\n[RESULT] Passo 11 concluído.")

'''
### ================================================================== ###
### Passo 12 - Percentual de palavras do texto final presentes em top_words
### ================================================================== ###

palavras_lista = [w for w in restaurado if w and w.strip()]
top_set_lower = top_set_normalized

total_words = len(palavras_lista)
if total_words == 0:
    print("\n[RESULT] Passo 12: nenhum token/palavra encontrada para análise (total = 0).")
else:
    freq = Counter(w for w in palavras_lista)
    palavras_lista_norm = [_normalizar_token(w) for w in palavras_lista]

    matched = [orig for orig, norm in zip(palavras_lista, palavras_lista_norm) if norm in top_set_lower]
    unmatched = [orig for orig, norm in zip(palavras_lista, palavras_lista_norm) if norm not in top_set_lower]

    matched_count = len(matched)
    pct = (matched_count / total_words) * 100.0

    print("\n[RESULT] Passo 12 — Cobertura top_words")
    print(f"[RESULT] Total de palavras (contando repetições): {total_words}")
    print(f"[RESULT] Palavras encontradas em top_words: {matched_count} ({pct:.2f}%)")

    unique_total = len(set(w.lower() for w in palavras_lista))
    unique_matched = len(set(_normalizar_token(w) for w in matched))
    unique_unmatched = len(set(_normalizar_token(w) for w in unmatched))
    print(f"[RESULT] Palavras únicas: {unique_total} | únicas em top_words: {unique_matched} | únicas não em top_words: {unique_unmatched}")

    print("\n[RESULT] Todas as palavras encontradas em top_words (por frequência):")
    for w, c in freq.most_common():
        if _normalizar_token(w) in top_set_lower:
            print(f"  {w} — {c}")

    print("\n[RESULT] Todas as palavras NÃO encontradas em top_words (por frequência):")
    unmatched_freq = Counter(w for w in unmatched)
    for w, c in unmatched_freq.most_common():
        print(f"  {w} — {c}")

print("\n[RESULT] Passo 12 concluído.")
'''

### ================================================================== ###
### Passo 13 - Reconstruir texto com pontuação e sufixos (apóstrofo/traço/--) ###
### ================================================================== ###
# Reconstrói usando original_lines_by_pos e restaurado
# Reinsere sufixos (como "'S", "-ING" ou "--X") preservando a parte antes do símbolo
# Salva em final_reconstructed.txt
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 13: reconstruindo texto com pontuação e sufixos de apóstrofo/traço/--...")

reconstructed_by_pos = []
max_pos = max(len(restaurado), max(original_lines_by_pos.keys())+1 if original_lines_by_pos else 0)
apostrofo_pattern = re.compile(r"[\'\u2019`-]")

for i in range(max_pos):
    dec_word = ""
    if i < len(restaurado):
        dec_word = restaurado[i] or ""
    orig_line = original_lines_by_pos.get(i, "")

    if not dec_word:
        reconstructed_by_pos.append(orig_line)
        continue

    if not orig_line:
        reconstructed_by_pos.append(dec_word)
        continue

    m = apostrofo_pattern.search(orig_line)
    if m and m.start() + 1 < len(orig_line) and re.match(r"[A-Za-z\u00C0-\u017F]", orig_line[m.start()+1]):
        prefix = orig_line[:m.start()]
        suffix = orig_line[m.start():]
        new_prefix = re.sub(r"([A-Za-z\u00C0-\u017F]+)(?!.*[A-Za-z\u00C0-\u017F])", lambda mo: dec_word, prefix, count=1)
        reconstructed = new_prefix + suffix
        reconstructed_by_pos.append(reconstructed)
        continue

    reconstructed = re.sub(r"[A-Za-z\u00C0-\u017F]+", dec_word, orig_line, count=1)
    reconstructed_by_pos.append(reconstructed)

final_text = " ".join(item if item is not None else "" for item in reconstructed_by_pos)
out_path = "final_reconstructed.txt"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(final_text)

print(f"\n[RESULT] Passo 13 — Texto final reconstruído com pontuação e sufixos (arquivo salvo): {out_path}")
if DEBUG:
    print("\n[DEBUG] Trecho (até 2000 chars) do texto reconstruído:")
    print(final_text[:2000])

print("\n[RESULT] Passo 13 concluído.")

### ================================================================== ###
### PASSO 14 - Aplicar mapeamento às maiúsculas remanescentes e imprimir
### ================================================================== ###
# Carrega final_map.py (se existir) com segurança, filtra pares 1-char->1-char
# Percorre cada caractere MAIÚSCULO do final_text e aplica substituição se existir
# Conta e imprime quantas substituições foram feitas por par e imprime o texto final
if DEBUG:
    print("\n[DEBUG] Iniciando Passo 14: aplicando final_map.py às maiúsculas remanescentes no texto final...")

# carregar final_map.py dinamicamente (fallback para mapa_substituicao em memória)
mapa_atual = {}
if os.path.exists(final_map_path):
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("final_map_module", final_map_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mapa_atual = getattr(mod, "final_map", {}).copy() if hasattr(mod, "final_map") else {}
        if DEBUG:
            print(f"[DEBUG] final_map.py carregado com {len(mapa_atual)} entradas.")
    except Exception as e:
        mapa_atual = mapa_substituicao.copy() if 'mapa_substituicao' in globals() else {}
        if DEBUG:
            print(f"[DEBUG] Erro ao carregar final_map.py ({e}). Usando mapa_substituicao em memória ({len(mapa_atual)} entradas).")
else:
    mapa_atual = mapa_substituicao.copy() if 'mapa_substituicao' in globals() else {}
    if DEBUG:
        print(f"[DEBUG] final_map.py não encontrado. Usando mapa_substituicao em memória ({len(mapa_atual)} entradas).")

# filtrar pares inválidos, mantemos apenas mapeamentos 1-char->1-char
mapa_clean = {}
for k, v in mapa_atual.items():
    if not (isinstance(k, str) and isinstance(v, str)):
        continue
    if len(k) != 1 or len(v) != 1:
        continue
    mapa_clean[k] = v

if DEBUG:
    print(f"[DEBUG] Mapa filtrado para substituições de caractere único: {len(mapa_clean)} pares.")

# aplicar substituições SOMENTE para caracteres maiúsculos do texto final
from collections import Counter
sub_counter = Counter()
out_chars = []
total_subs = 0

for ch in final_text:
    if ch.isupper():
        replaced = False
        if ch in mapa_clean:
            out_chars.append(mapa_clean[ch]); sub_counter[(ch, mapa_clean[ch])] += 1; total_subs += 1; replaced = True
        else:
            if ch.upper() in mapa_clean:
                out_chars.append(mapa_clean[ch.upper()]); sub_counter[(ch, mapa_clean[ch.upper()])] += 1; total_subs += 1; replaced = True
            elif ch.lower() in mapa_clean:
                out_chars.append(mapa_clean[ch.lower()]); sub_counter[(ch, mapa_clean[ch.lower()])] += 1; total_subs += 1; replaced = True
        if not replaced:
            out_chars.append(ch)
    else:
        out_chars.append(ch)

final_text_mapped = "".join(out_chars)

# salvar resultado mapeado
out_path_mapped = "final_reconstructed_mapped.txt"
with open(out_path_mapped, "w", encoding="utf-8") as f:
    f.write(final_text_mapped)

# relatório + imprimir resultado mapeado (sempre)
print("\n[RESULT] Passo 14 — Texto final MAPEADO (aplicado mapa_substituicao às maiúsculas remanescentes):")
print(f"[RESULT] Arquivo salvo: {out_path_mapped}\n")

if total_subs == 0:
    print("[RESULT] Nenhuma substituição aplicada (nenhuma letra maiúscula mapeável encontrada).")
else:
    print(f"[RESULT] Total de substituições aplicadas: {total_subs}\n")
    print("[RESULT] Substituições por par (ORIG -> DEST):")
    for (orig, dest), cnt in sub_counter.most_common():
        print(f"  {orig} -> {dest}  : {cnt}")

print("\n[RESULT] --- INÍCIO DO TEXTO MAPEADO ---\n")
print(final_text_mapped)
print("\n[RESULT] --- FIM DO TEXTO MAPEADO ---\n")

if DEBUG:
    print("[DEBUG] Passo 14 concluído.")
else:
    print("[RESULT] Passo 14 concluído.")
# Fim do pipeline
