#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib
import os
import sys
import time
from collections import defaultdict

PAUSA_PRINT = 0.15


# ---------- carregar dicionários de rank (1word_counts > 2top_words) ----------
def carregar_dicionarios_rank():
    combined = {}

    def importar_modulo(nome_modulo, nome_dict):
        try:
            mod = importlib.import_module(nome_modulo)
            if hasattr(mod, nome_dict):
                data = getattr(mod, nome_dict)
                if isinstance(data, dict):
                    return data
                else:
                    print(f"⚠️ {nome_dict} em {nome_modulo} não é um dict.")
            else:
                print(f"⚠️ {nome_dict} não encontrado em {nome_modulo}.")
        except ModuleNotFoundError:
            print(f"⚠️ Módulo {nome_modulo}.py não encontrado.")
        except Exception as e:
            print(f"⚠️ Erro ao carregar {nome_modulo}: {e}")
        return {}

    word_counts = importar_modulo("1word_counts", "word_counts_english_rank")
    top_words = importar_modulo("2top_words", "top_words_english_rank")

    combined.update(top_words)   # prioridade menor
    combined.update(word_counts) # prioridade maior (sobrescreve)
    return combined


# ---------- index por comprimento, por rank ----------
def construir_index_por_len_rank(dicionario_rank):
    por_len = defaultdict(list)
    # ordena por rank ascendente (menor = melhor)
    for word, rank in sorted(dicionario_rank.items(), key=lambda x: x[1]):
        por_len[len(word)].append(word)
    return por_len


# ---------- checar candidato considerando mapeamento por caractere ----------
def candidato_valido_para_token(original, candidate,
                                 char_map, inverse_map):
    """
    Retorna True se candidate é compatível com char_map/inverse_map:
    - posições de caracteres correspondem às restrições já existentes;
    - se original tem caractere repetido, candidate deve repetir o mesmo char nas mesmas posições;
    - não permite que um target char (candidate char) já esteja ligado a outro source char distinto.
    """
    if len(original) != len(candidate):
        return False

    # 1) se um mesmo caractere aparece em múltiplas posições no original,
    #    candidate deve ter os mesmos caracteres nessas posições
    for ch in set(original):
        idxs = [i for i, c in enumerate(original) if c == ch]
        if len(idxs) > 1:
            chars_in_candidate = {candidate[i] for i in idxs}
            if len(chars_in_candidate) != 1:
                # candidate não preserva repetição consistentemente
                return False

    # 2) verificação posição-a-posicao com char_map / inverse_map
    for o_ch, c_ch in zip(original, candidate):
        # se já existe mapeamento definido para o caracter original -> deve coincidir
        if o_ch in char_map:
            if char_map[o_ch] != c_ch:
                return False
        else:
            # se target já foi mapeado por outro source distinto, não pode usar
            if c_ch in inverse_map and inverse_map[c_ch] != o_ch:
                return False

    return True


# ---------- escolher candidata (respeitando char_map/inverse_map e evitando reuse de palavra) ----------
def escolher_candidata_com_chars(original, candidatos, char_map, inverse_map, used_words):
    """
    Retorna a primeira candidata (na ordem de rank) que for compatível.
    Quando encontrada, NÃO atualiza o char_map aqui — quem chama faz isso.
    """
    for cand in candidatos:
        # evita reutilizar a mesma palavra-candidata para múltiplos originais
        if cand in used_words:
            continue
        if candidato_valido_para_token(original, cand, char_map, inverse_map):
            return cand
    return None


# ---------- main: aplica substituições com mapeamento por caractere ----------
def main():
    input_sorted = "encoded_message_sorted.txt"
    map_out = "map_words.py"
    removed_out = "encoded_message_sorted_removed.txt"
    final_out = "message_FINAL.txt"

    if not os.path.exists(input_sorted):
        print(f"❌ ERRO: '{input_sorted}' não encontrado.")
        sys.exit(1)

    rank_dict = carregar_dicionarios_rank()
    if not rank_dict:
        print("⚠️ Nenhum dicionário de rank carregado. Abortando.")
        sys.exit(1)

    top_by_len = construir_index_por_len_rank(rank_dict)
    print("\n📏 disponibilidade por comprimento:")
    for L in sorted(top_by_len.keys()):
        print(f"  {L:2d} letras -> {len(top_by_len[L])} palavras")

    with open(input_sorted, "r", encoding="utf-8") as f:
        linhas = [ln.rstrip("\n") for ln in f.readlines()]

    # estruturas de estado
    token_mapping = {}       # mapping token -> token_substituto (só armazenar se subst. real)
    char_map = {}            # original_char -> substituted_char (fixa)
    inverse_map = {}         # substituted_char -> original_char (para garantir injetividade)
    used_words = set()       # palavras-alvo já usadas
    final_lines = []
    removed_lines = []

    print("\n🚀 iniciando substituições com consistência por letra...\n")
    time.sleep(0.2)

    for idx, token in enumerate(linhas):
        original = token.strip()
        if original == "":
            final_lines.append("")
            removed_lines.append("")
            print(f"{idx+1:03d}: linha vazia (ignorada).")
            continue

        # se esse token já tem mapeamento, reaplica (fixo)
        if original in token_mapping:
            chosen = token_mapping[original]
            print(f"{idx+1:03d}: Reaplicando mapeamento -> {original} -> {chosen}")
            final_lines.append(chosen)
            removed_lines.append("")
            time.sleep(PAUSA_PRINT)
            continue

        L = len(original)
        candidatos = top_by_len.get(L, [])

        # tentar achar candidato compatível com o char_map atual
        cand = escolher_candidata_com_chars(original, candidatos, char_map, inverse_map, used_words)

        if cand is not None and cand != original:
            # aceitar e fixar mapeamentos por caractere
            token_mapping[original] = cand
            used_words.add(cand)
            # criar entradas em char_map / inverse_map para cada caractere novo
            for o_ch, c_ch in zip(original, cand):
                if o_ch not in char_map:
                    char_map[o_ch] = c_ch
                    inverse_map[c_ch] = o_ch
                # se já existia, foi verificado compatibilidade antes
            chosen = cand
            print(f"{idx+1:03d}: Encontrada substituição consistente -> {original} -> {chosen}")
        else:
            # sem candidato consistente => manter original (não gravar em token_mapping)
            chosen = original
            print(f"{idx+1:03d}: Nenhuma substituição consistente para '{original}'. Mantém original.")

        final_lines.append(chosen)
        removed_lines.append("")
        time.sleep(PAUSA_PRINT)

    # escrever map_words.py apenas com substituições reais
    with open(map_out, "w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write("# Dicionário gerado automaticamente (apenas substituições reais)\n")
        f.write("map_words_dict = {\n")
        for i, (orig, sub) in enumerate(token_mapping.items()):
            comma = "," if i < len(token_mapping) - 1 else ""
            f.write(f"    {orig!r}: {sub!r}{comma}\n")
        f.write("}\n")

    # arquivos auxiliares
    with open(removed_out, "w", encoding="utf-8") as f:
        for ln in removed_lines:
            f.write(ln + "\n")
    with open(final_out, "w", encoding="utf-8") as f:
        for ln in final_lines:
            f.write(ln + "\n")

    print("\n✅ finalizado.")
    print(f" - Dicionário salvo em: {map_out}  (total substituições: {len(token_mapping)})")
    print(f" - Mensagem final em: {final_out}")
    print(f" - Linhas removidas em: {removed_out}")


if __name__ == "__main__":
    main()
